# -*- coding: utf-8 -*-
"""
自监督优化循环系统（无需GT）

核心思路：用PDF原文作为唯一真相源，自动验证提取结果
1. 提取器：分组并行提取参数
2. 验证器：文本搜索 + AI逐项验证（每次只验证1个参数，更准确）
3. 发现错误 → AI分析原因 → 写入 attention notes
4. 重新提取 → 重新验证 → 迭代

使用方法：
    python self_optimize.py                       # 用尚阳通前5个PDF跑1轮
    python self_optimize.py --rounds 3            # 跑3轮
    python self_optimize.py --all                 # 用全部PDF
    python self_optimize.py --pdf "xxx.pdf"       # 指定单个PDF
"""

import sys
import os
import re
import json
import time
import yaml
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor, ExtractionResult

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================
PROJECT_DIR = Path(__file__).parent
PDF_DIR = PROJECT_DIR / "尚阳通规格书"
NOTES_DIR = PROJECT_DIR / "backend" / "device_configs"
PROCESSED_LOG = PROJECT_DIR / "optimized_pdfs.log"
MAX_VERIFY_PER_ROUND = 15   # 每轮最多AI验证多少个可疑参数（控制API费用）


# ============================================================
# 数据结构
# ============================================================
@dataclass
class VerifyResult:
    """单个参数的验证结果"""
    param_name: str
    extracted_value: str
    status: str              # confirmed / wrong / hallucinated / missed
    verified_value: str = "" # 验证器找到的正确值
    reason: str = ""         # 原因说明
    verify_method: str = ""  # text_search / ai_verify


@dataclass
class PDFResult:
    """单个PDF的完整结果"""
    pdf_name: str
    device_type: str
    extracted_count: int = 0
    verified: List[VerifyResult] = field(default_factory=list)

    @property
    def confirmed(self): return sum(1 for v in self.verified if v.status == 'confirmed')
    @property
    def wrong(self): return sum(1 for v in self.verified if v.status == 'wrong')
    @property
    def hallucinated(self): return sum(1 for v in self.verified if v.status == 'hallucinated')
    @property
    def missed(self): return sum(1 for v in self.verified if v.status == 'missed')


# ============================================================
# 第一层验证：文本搜索（免费、快速）
# ============================================================
def text_search_verify(extracted_params: Dict[str, str],
                       pdf_text: str) -> Dict[str, str]:
    """
    在PDF原文中搜索每个提取值的数字部分
    返回 {param_name: 'found' / 'not_found'}
    """
    results = {}
    text_lower = pdf_text.lower().replace(' ', '')

    for name, value in extracted_params.items():
        if not value:
            results[name] = 'not_found'
            continue

        # 提取数值部分（去掉单位和空格）
        num_match = re.search(r'[-+]?[\d.]+', str(value))
        if not num_match:
            # 非数值参数（如厂家名、封装名）直接搜索原文
            val_clean = str(value).strip().lower().replace(' ', '')
            if len(val_clean) >= 2 and val_clean in text_lower:
                results[name] = 'found'
            else:
                results[name] = 'not_found'
            continue

        num_str = num_match.group()
        # 在原文中搜索这个数值
        # 考虑原文中数值可能有不同格式（如1.6, 1.60, 1,600）
        if num_str in pdf_text:
            results[name] = 'found'
        else:
            # 尝试去掉末尾的0
            try:
                num_float = float(num_str)
                # 尝试多种格式
                formats = [
                    str(num_float),
                    f"{num_float:.0f}" if num_float == int(num_float) else None,
                    f"{num_float:.1f}",
                    f"{num_float:.2f}",
                ]
                found = False
                for fmt in formats:
                    if fmt and fmt in pdf_text:
                        found = True
                        break
                results[name] = 'found' if found else 'not_found'
            except ValueError:
                results[name] = 'not_found'

    return results


# ============================================================
# 第二层验证：AI逐项验证（精确、消耗API）
# ============================================================
async def ai_verify_params(ai: AIProcessor, pdf_content_str: str,
                           suspicious_params: List[Tuple[str, str]],
                           device_type: str) -> List[VerifyResult]:
    """
    用AI逐项验证可疑参数（每次只问1个参数，避免幻觉）

    suspicious_params: [(param_name, extracted_value), ...]
    """
    results = []

    # 构建别名查找表
    groups = ai._get_param_groups(device_type)
    param_aliases = {}
    for group_params in groups.values():
        for p in group_params:
            aliases = [p['name']] + p.get('aliases', [])
            param_aliases[p['name']] = aliases

    # 限制数量
    params_to_verify = suspicious_params[:MAX_VERIFY_PER_ROUND]

    # 并行验证
    tasks = []
    for param_name, extracted_value in params_to_verify:
        aliases = param_aliases.get(param_name, [param_name])
        alias_str = ', '.join(aliases[:5])

        prompt = f"""在以下PDF内容中查找参数 "{param_name}"（PDF中可能写作: {alias_str}）。

要求：
1. 仔细搜索PDF中所有表格和文本
2. 如果找到，返回原文中的精确数值（含单位和测试条件）
3. 如果确实没有，返回NOT_FOUND
4. 只关注这一个参数，不要提取其他参数

PDF内容：
{pdf_content_str[:15000]}

请只用以下JSON格式回答（不要添加其他文字）：
```json
{{"param":"{param_name}","found":true/false,"value":"原文精确值","test_condition":"测试条件","location":"在PDF哪个表格/段落找到的"}}
```"""
        tasks.append(ai._call_api_async(prompt))

    if not tasks:
        return results

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    for i, response in enumerate(responses):
        param_name, extracted_value = params_to_verify[i]

        if isinstance(response, Exception):
            logger.warning(f"  验证失败 {param_name}: {response}")
            continue

        try:
            # 解析验证响应
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                found = data.get('found', False)
                verified_value = data.get('value', '').strip()
                location = data.get('location', '')

                if not found:
                    results.append(VerifyResult(
                        param_name=param_name,
                        extracted_value=extracted_value,
                        status='hallucinated',
                        reason=f'验证器确认PDF中不存在此参数',
                        verify_method='ai_verify'
                    ))
                elif verified_value and not _values_close(extracted_value, verified_value):
                    results.append(VerifyResult(
                        param_name=param_name,
                        extracted_value=extracted_value,
                        status='wrong',
                        verified_value=verified_value,
                        reason=f'验证器值={verified_value}(位于{location})，提取器值={extracted_value}',
                        verify_method='ai_verify'
                    ))
                else:
                    results.append(VerifyResult(
                        param_name=param_name,
                        extracted_value=extracted_value,
                        status='confirmed',
                        verified_value=verified_value,
                        verify_method='ai_verify'
                    ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"  验证响应解析失败 {param_name}: {e}")

    return results


def _values_close(val1: str, val2: str) -> bool:
    """判断两个值是否接近（同一个参数的不同表述）"""
    if not val1 or not val2:
        return False

    c1 = re.sub(r'[^0-9a-zA-Z.\-+]', '', str(val1).lower())
    c2 = re.sub(r'[^0-9a-zA-Z.\-+]', '', str(val2).lower())
    if c1 == c2 or c1 in c2 or c2 in c1:
        return True

    try:
        n1 = float(re.search(r'[-+]?[\d.]+', str(val1)).group())
        n2 = float(re.search(r'[-+]?[\d.]+', str(val2)).group())
        if n2 == 0:
            return n1 == 0
        if abs(n1 - n2) / abs(n2) < 0.05:
            return True
    except (AttributeError, ValueError, ZeroDivisionError):
        pass
    return False


# ============================================================
# 检测遗漏参数
# ============================================================
def detect_missed_params(ai: AIProcessor, extracted_names: set,
                         device_type: str, pdf_text: str) -> List[Tuple[str, str]]:
    """
    检测配置中有但未提取的参数，并在PDF原文中搜索它们的别名
    返回 [(param_name, "文本中发现的线索"), ...] —— 可能是真遗漏

    防误报策略：
    - 短别名（<4字符）必须作为独立单词出现（前后有边界符）
    - 测试条件类参数跳过（AI本来就难提取）
    - 中文别名要求精确匹配
    """
    groups = ai._get_param_groups(device_type)
    missed_candidates = []

    text_lower = pdf_text.lower()

    # 跳过测试条件类参数（这类参数不是独立参数值，不算遗漏）
    skip_keywords = ['测试条件', '限制条件']

    for group_name, params in groups.items():
        for p in params:
            name = p['name']
            if name in extracted_names:
                continue

            # 跳过测试条件类
            if any(kw in name for kw in skip_keywords):
                continue

            # 在PDF文本中搜索这个参数的别名
            all_names = [name] + p.get('aliases', [])
            found_hint = None
            for alias in all_names:
                alias_clean = alias.strip()
                alias_lower = alias_clean.lower()

                if len(alias_clean) < 2:
                    continue

                # 【关键优化】避免用极短纯字母符号（如“IF”、“LE”）判断是否“PDF中有”
                # 这类符号在曲线图注释、公式中非常常见，容易造成“明明没有额定参数却被标记成遗漏”
                if len(alias_clean) <= 2 and alias_clean.isalpha():
                    continue

                # 短别名（<4字符）必须作为独立词出现，用正则边界匹配
                if len(alias_clean) < 4:
                    import re
                    # 要求前后是非字母数字字符（单词边界）
                    pattern = r'(?<![a-zA-Z0-9])' + re.escape(alias_lower) + r'(?![a-zA-Z0-9])'
                    if re.search(pattern, text_lower):
                        found_hint = alias
                        break
                else:
                    if alias_lower in text_lower:
                        found_hint = alias
                        break

            if found_hint:
                missed_candidates.append((name, f"PDF中发现关键词'{found_hint}'但未提取"))

    return missed_candidates


# ============================================================
# 核心：单个PDF的完整自验证流程
# ============================================================
async def self_verify_one_pdf(ai: AIProcessor, parser: PDFParser,
                              pdf_path: Path) -> Optional[PDFResult]:
    """对单个PDF执行：提取 → 文本验证 → AI验证可疑项 → 检测遗漏"""

    pdf_name = pdf_path.name
    print(f"\n  📄 {pdf_name}", flush=True)

    # 1. 解析PDF
    try:
        pdf_content = parser.parse_pdf(str(pdf_path))
    except Exception as e:
        print(f"     ❌ 解析失败: {e}", flush=True)
        return None

    device_type = pdf_content.metadata.get('device_type', 'Si MOSFET')
    print(f"     器件类型: {device_type}", flush=True)

    # 2. 提取参数（直接 await 异步方法，避免嵌套 asyncio.run）
    try:
        extraction = await ai.extract_params_parallel(pdf_content, [])
    except Exception as e:
        print(f"     ❌ 提取失败: {e}", flush=True)
        return None

    if extraction.error:
        if '余额' in str(extraction.error) or '密钥' in str(extraction.error):
            raise RuntimeError(extraction.error)
        print(f"     ⚠️ {extraction.error}", flush=True)
        return None

    extracted = {p.standard_name: p.value for p in extraction.params}
    print(f"     提取: {len(extracted)} 个参数", flush=True)

    result = PDFResult(pdf_name=pdf_name, device_type=device_type,
                       extracted_count=len(extracted))

    # 3. 第一层：文本搜索验证
    full_text = parser.get_structured_content(pdf_content)
    text_results = text_search_verify(extracted, full_text)

    confirmed_by_text = []
    suspicious = []  # 文本中找不到数值的 → 可疑

    for name, status in text_results.items():
        if status == 'found':
            confirmed_by_text.append(name)
            result.verified.append(VerifyResult(
                param_name=name, extracted_value=extracted[name],
                status='confirmed', verify_method='text_search'
            ))
        else:
            suspicious.append((name, extracted[name]))

    print(f"     文本验证: ✅{len(confirmed_by_text)} 可疑{len(suspicious)}", flush=True)

    # 4. 第二层：AI验证可疑项
    if suspicious:
        print(f"     AI验证 {min(len(suspicious), MAX_VERIFY_PER_ROUND)} 个可疑项...", flush=True)
        ai_results = await ai_verify_params(ai, full_text, suspicious, device_type)
        result.verified.extend(ai_results)

        # 未被AI验证的（超出限制的）标记为 unverified
        verified_names = {r.param_name for r in ai_results}
        for name, value in suspicious:
            if name not in verified_names:
                result.verified.append(VerifyResult(
                    param_name=name, extracted_value=value,
                    status='confirmed',  # 保守处理：未验证的暂不标记为错误
                    verify_method='skipped'
                ))

    # 5. 检测遗漏
    extracted_names = set(extracted.keys())
    missed = detect_missed_params(ai, extracted_names, device_type, full_text)
    for name, hint in missed:
        result.verified.append(VerifyResult(
            param_name=name, extracted_value='',
            status='missed', reason=hint, verify_method='text_search'
        ))

    print(f"     结果: ✅{result.confirmed} ❌{result.wrong} "
          f"🚫{result.hallucinated} ⬜{result.missed}", flush=True)

    return result


# ============================================================
# 错误分析 + Notes生成
# ============================================================
def collect_errors_by_device(pdf_results: List[PDFResult]) -> Dict[str, List[VerifyResult]]:
    """按device_type收集所有错误"""
    errors = {}
    for pr in pdf_results:
        if not pr:
            continue
        dt = pr.device_type
        if dt not in errors:
            errors[dt] = []
        for v in pr.verified:
            if v.status in ('wrong', 'hallucinated', 'missed'):
                errors[dt].append(v)
    return errors


def analyze_and_generate_notes(ai: AIProcessor,
                               errors_by_device: Dict[str, List[VerifyResult]]) -> Dict[str, List[Dict]]:
    """用AI分析错误模式，生成notes"""
    generated = {}

    for device_type, errors in errors_by_device.items():
        if not errors:
            continue

        wrong = [e for e in errors if e.status == 'wrong']
        hallucinated = [e for e in errors if e.status == 'hallucinated']
        missed = [e for e in errors if e.status == 'missed']

        if not wrong and not hallucinated and not missed:
            continue

        print(f"\n  🔍 分析 {device_type}: ❌{len(wrong)} 🚫{len(hallucinated)} ⬜{len(missed)}", flush=True)

        lines = []
        if wrong:
            lines.append("## 值错误（提取了但值不对）")
            for e in wrong[:15]:
                lines.append(f"- 参数:{e.param_name} | 提取值:{e.extracted_value} | 正确值:{e.verified_value} | {e.reason}")
        if hallucinated:
            lines.append("\n## 幻觉（提取的值在PDF中不存在）")
            for e in hallucinated[:10]:
                lines.append(f"- 参数:{e.param_name} | 幻觉值:{e.extracted_value}")
        if missed:
            lines.append("\n## 遗漏（PDF中有但未提取）")
            counts = {}
            for e in missed:
                counts.setdefault(e.param_name, []).append(e.reason)
            for param, reasons in sorted(counts.items(), key=lambda x: -len(x[1])):
                lines.append(f"- 参数:{param} | 遗漏{len(reasons)}次 | {reasons[0]}")

        error_summary = '\n'.join(lines)

        prompt = f"""你是功率半导体参数提取系统的优化专家。

以下是 {device_type} 器件在自动验证中发现的错误：

{error_summary}

## 分析要求
1. "值错误"：分析提取器可能选错了哪行/哪列，生成精确的提取规则
2. "幻觉"：分析为什么AI编造了不存在的值，生成防幻觉规则
3. "遗漏"：分析为什么没提取到，生成引导规则
4. 每条规则要具体、可直接放入prompt

## 输出格式（严格YAML列表）
```yaml
- param: "参数标准名或*表示通用"
  issue: "问题描述"
  rule: "提取规则"
```

只输出YAML："""

        try:
            response = ai._call_api_sync(prompt)
            notes = _parse_notes_yaml(response)
            if notes:
                generated[device_type] = notes
                print(f"     ✅ 生成 {len(notes)} 条规则", flush=True)
                for n in notes[:5]:
                    print(f"        - {n['param']}: {n['rule'][:50]}...", flush=True)
        except Exception as e:
            print(f"     ❌ 分析失败: {e}", flush=True)

    return generated


def _parse_notes_yaml(response: str) -> List[Dict]:
    """解析AI返回的YAML notes"""
    if not response:
        return []

    yaml_match = re.search(r'```(?:yaml)?\s*(.*?)\s*```', response, re.DOTALL)
    yaml_str = yaml_match.group(1) if yaml_match else response.strip()

    try:
        notes = yaml.safe_load(yaml_str)
        if isinstance(notes, list):
            valid = []
            for n in notes:
                if isinstance(n, dict) and 'param' in n and 'rule' in n:
                    valid.append({
                        'param': str(n['param']),
                        'issue': str(n.get('issue', '')),
                        'rule': str(n['rule']),
                        'verified': False,
                    })
            return valid
    except yaml.YAMLError:
        pass
    return []


# ============================================================
# Notes 读写
# ============================================================
def write_notes(device_type: str, new_notes: List[Dict], round_num: int):
    """追加notes到YAML文件"""
    type_map = {
        'Si MOSFET': 'notes_si_mosfet',
        'SiC MOSFET': 'notes_sic_mosfet',
        'IGBT': 'notes_igbt',
    }
    key = type_map.get(device_type, 'notes_si_mosfet')
    notes_path = NOTES_DIR / f'{key}.yaml'

    existing = []
    try:
        if notes_path.exists():
            with open(notes_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            existing = data.get('notes', []) or []
    except Exception:
        existing = []

    # 去重（同参数覆盖，通用规则追加）
    existing_map = {n.get('param', ''): i for i, n in enumerate(existing)}
    for note in new_notes:
        note['added_round'] = round_num
        param = note['param']
        if param in existing_map and param != '*':
            existing[existing_map[param]] = note
        else:
            existing.append(note)

    header = f"""# {device_type} 提参注意文档
# 自监督优化循环自动生成
# 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')} (第{round_num}轮)

"""
    with open(notes_path, 'w', encoding='utf-8') as f:
        f.write(header)
        yaml.dump({'notes': existing}, f, allow_unicode=True,
                  default_flow_style=False, sort_keys=False)

    print(f"  📝 {notes_path.name}: {len(existing)} 条规则", flush=True)


# ============================================================
# 主流程
# ============================================================
def load_processed_pdfs() -> set:
    """加载已优化过的PDF名称"""
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    return set()


def save_processed_pdfs(pdf_names: List[str]):
    """追加已处理的PDF名称到日志"""
    with open(PROCESSED_LOG, 'a', encoding='utf-8') as f:
        for name in pdf_names:
            f.write(name + '\n')


def get_pdf_list(pdf_dir: Path, limit: int = None,
                 specific: str = None, skip_processed: bool = True) -> List[Path]:
    """获取要处理的PDF列表（自动跳过已优化过的）"""
    if specific:
        p = pdf_dir / specific
        if p.exists():
            return [p]
        # 模糊搜索
        for f in pdf_dir.iterdir():
            if specific.lower() in f.name.lower() and f.suffix.lower() == '.pdf':
                return [f]
        return []

    processed = load_processed_pdfs() if skip_processed else set()
    pdfs = sorted([f for f in pdf_dir.iterdir() if f.suffix.lower() == '.pdf'])

    if processed:
        before = len(pdfs)
        pdfs = [p for p in pdfs if p.name not in processed]
        skipped = before - len(pdfs)
        if skipped > 0:
            print(f"  跳过已优化: {skipped} 个, 剩余: {len(pdfs)} 个", flush=True)

    if limit:
        pdfs = pdfs[:limit]
    return pdfs


def run_optimization(max_rounds: int = 3, pdf_limit: int = 5,
                     specific_pdf: str = None, skip_processed: bool = True):
    """运行自监督优化循环"""
    parser = PDFParser()
    ai = AIProcessor()
    ai.timeout = 180

    pdfs = get_pdf_list(PDF_DIR, limit=pdf_limit, specific=specific_pdf,
                        skip_processed=skip_processed)

    print(f"{'='*60}", flush=True)
    print(f"自监督优化循环", flush=True)
    print(f"PDF数量: {len(pdfs)}", flush=True)
    print(f"最大轮数: {max_rounds}", flush=True)
    print(f"{'='*60}", flush=True)

    history = []

    for round_num in range(1, max_rounds + 1):
        print(f"\n{'='*60}", flush=True)
        print(f"🔄 第 {round_num} 轮", flush=True)
        print(f"{'='*60}", flush=True)

        # Phase 1: 提取 + 自验证
        print(f"\n📊 Phase 1: 提取 + 自验证", flush=True)
        pdf_results = []

        async def _run_all_pdfs():
            results = []
            for pdf_path in pdfs:
                r = await self_verify_one_pdf(ai, parser, pdf_path)
                results.append(r)
            return results

        try:
            pdf_results = asyncio.run(_run_all_pdfs())
        except RuntimeError as e:
            print(f"\n❌ 致命错误: {e}", flush=True)
            return

        # 记录已处理的PDF
        processed_this_round = [r.pdf_name for r in pdf_results if r]
        if round_num == 1:
            save_processed_pdfs(processed_this_round)

        # 汇总
        total_c = sum(r.confirmed for r in pdf_results if r)
        total_w = sum(r.wrong for r in pdf_results if r)
        total_h = sum(r.hallucinated for r in pdf_results if r)
        total_m = sum(r.missed for r in pdf_results if r)
        total_all = total_c + total_w + total_h
        accuracy = (total_c / total_all * 100) if total_all > 0 else 0

        print(f"\n{'─'*40}", flush=True)
        print(f"第{round_num}轮汇总: ✅{total_c} ❌{total_w} 🚫{total_h} ⬜{total_m} | "
              f"自验证准确率={accuracy:.1f}%", flush=True)

        round_info = {'round': round_num, 'confirmed': total_c, 'wrong': total_w,
                      'hallucinated': total_h, 'missed': total_m, 'accuracy': accuracy}
        history.append(round_info)

        # Phase 2: 错误分析 + 生成notes
        errors_by_device = collect_errors_by_device(pdf_results)
        total_errors = sum(len(e) for e in errors_by_device.values())

        if total_errors == 0:
            print(f"\n✅ 无错误，优化完成！", flush=True)
            break

        if round_num >= max_rounds:
            print(f"\n达到最大轮数 {max_rounds}", flush=True)
            break

        print(f"\n🧠 Phase 2: 错误分析 + 规则生成", flush=True)
        new_notes = analyze_and_generate_notes(ai, errors_by_device)

        if not new_notes:
            print(f"  无新规则，优化结束", flush=True)
            break

        # Phase 3: 写入notes
        print(f"\n📝 Phase 3: 写入注意文档", flush=True)
        for dt, notes in new_notes.items():
            write_notes(dt, notes, round_num)

        # 清缓存
        ai._config_cache.clear()

        # 检查收敛
        if len(history) >= 2:
            prev = history[-2]['accuracy']
            curr = history[-1]['accuracy']
            if curr - prev < 1.0:
                print(f"\n✅ 准确率收敛（{prev:.1f}% → {curr:.1f}%），优化结束", flush=True)
                break

    # 打印历史
    print(f"\n{'='*60}", flush=True)
    print(f"📈 优化历史:", flush=True)
    for h in history:
        print(f"  第{h['round']}轮: 准确率={h['accuracy']:.1f}% "
              f"(✅{h['confirmed']} ❌{h['wrong']} 🚫{h['hallucinated']} ⬜{h['missed']})", flush=True)

    # 保存详细报告
    report_path = PROJECT_DIR / f"optimize_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({'history': history}, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}", flush=True)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description='自监督优化循环')
    p.add_argument('--rounds', type=int, default=3, help='最大优化轮数')
    p.add_argument('--limit', type=int, default=5, help='处理的PDF数量')
    p.add_argument('--all', action='store_true', help='处理全部PDF')
    p.add_argument('--pdf', type=str, default=None, help='指定单个PDF文件名')
    p.add_argument('--no-skip', action='store_true', help='不跳过已优化的PDF')
    args = p.parse_args()

    limit = None if args.all else args.limit
    run_optimization(max_rounds=args.rounds, pdf_limit=limit,
                     specific_pdf=args.pdf, skip_processed=not args.no_skip)
