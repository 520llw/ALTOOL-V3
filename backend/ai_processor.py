# -*- coding: utf-8 -*-
"""
AI处理模块（重构版 v2）

核心设计：
1. 按器件类型加载专属参数配置（YAML）
2. 按类别分组，每组 ≤ 15 个参数，精简 Prompt
3. 加载器件类型专属的"提参注意文档"作为经验沉淀
4. 删除所有硬编码规则，prompt 只保留最小必要信息
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
import aiohttp
import yaml

from .config import config
from .pdf_parser import PDFContent

logger = logging.getLogger(__name__)

# 配置目录
DEVICE_CONFIGS_DIR = Path(__file__).parent / 'device_configs'

# 易漏参数：主流程未提取时，按需做一次补充提取（仅在有遗漏时触发）
# 必须使用 YAML 中的标准参数名，与 si_mosfet/sic_mosfet/igbt.yaml 严格一致
HIGH_RECALL_PARAMS = {
    'IGBT': [
        'tdon 25℃（ns）', 'tr 25℃（ns）', 'tdoff 25℃（ns）', 'tf 25℃（ns）',
        'Eon 25℃（uJ）', 'Eoff（uJ）', 'Ets 25℃（uJ）',
        'Erec 25℃',
    ],
    'Si MOSFET': [
        'Igss', 'PD Tc=25℃',
        'td-on', 'tr', 'td-off', 'tf',
        'EAS L=0.1mH',
    ],
    'SiC MOSFET': [
        'Igss', 'PD Tc=25℃',
        'td-on', 'tr', 'td-off', 'tf',
        'Eon', 'Eoff', 'Etot', 'Erec', 'EAS',
    ],
}


@dataclass
class ExtractedParam:
    """提取的参数"""
    standard_name: str
    value: str
    test_condition: str = ""
    variant_name: str = ""
    unit: str = ""
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    """提取结果"""
    pdf_name: str
    device_type: str = ""
    manufacturer: str = ""
    opn: str = ""
    params: List[ExtractedParam] = field(default_factory=list)
    unrecognized_params: List[str] = field(default_factory=list)
    error: str = None
    raw_response: str = ""


class AIProcessor:
    """
    AI处理器（重构版）
    - 按器件类型加载参数配置
    - 分组并行提取
    - 注意文档经验沉淀
    """

    def __init__(self):
        self.provider = config.ai.provider
        self.model = config.ai.model
        self.api_key = config.ai.api_key
        self.api_base = config.ai.api_base
        self.timeout = config.ai.timeout
        self.max_retries = config.ai.max_retries
        self._config_cache = {}  # 缓存已加载的设备配置

    def update_config(self, provider: str = None, model: str = None,
                      api_key: str = None, api_base: str = None):
        """更新AI配置"""
        if provider: self.provider = provider
        if model: self.model = model
        if api_key: self.api_key = api_key
        if api_base: self.api_base = api_base

    # ==================== 配置加载 ====================

    def _get_device_config_path(self, device_type: str) -> Path:
        """根据器件类型获取配置文件路径"""
        type_map = {
            'Si MOSFET': 'si_mosfet',
            'SiC MOSFET': 'sic_mosfet',
            'IGBT': 'igbt',
        }
        key = type_map.get(device_type, 'si_mosfet')
        return DEVICE_CONFIGS_DIR / f'{key}.yaml'

    def _get_notes_path(self, device_type: str) -> Path:
        """根据器件类型获取注意文档路径"""
        type_map = {
            'Si MOSFET': 'notes_si_mosfet',
            'SiC MOSFET': 'notes_sic_mosfet',
            'IGBT': 'notes_igbt',
        }
        key = type_map.get(device_type, 'notes_si_mosfet')
        return DEVICE_CONFIGS_DIR / f'{key}.yaml'

    def _load_device_config(self, device_type: str) -> Dict[str, Any]:
        """加载器件类型专属参数配置"""
        if device_type in self._config_cache:
            return self._config_cache[device_type]

        config_path = self._get_device_config_path(device_type)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            self._config_cache[device_type] = data
            logger.info(f"加载器件配置: {config_path.name}")
            return data
        except Exception as e:
            logger.error(f"加载器件配置失败 {config_path}: {e}")
            return {'groups': {}}

    def _load_extraction_notes(self, device_type: str) -> List[Dict]:
        """加载提参注意文档"""
        notes_path = self._get_notes_path(device_type)
        try:
            if notes_path.exists():
                with open(notes_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                return data.get('notes', []) or []
        except Exception as e:
            logger.warning(f"加载注意文档失败 {notes_path}: {e}")
        return []

    def _get_param_groups(self, device_type: str) -> Dict[str, List[Dict]]:
        """获取按类别分好的参数组"""
        device_config = self._load_device_config(device_type)
        return device_config.get('groups', {})

    # ==================== 名称归一化 ====================

    def _build_name_normalizer(self, device_type: str) -> Dict[str, str]:
        """
        构建 别名→标准名 映射表（用于归一化AI输出的参数名）
        
        映射策略：
        1. 精确匹配：aliases 中的原始文本
        2. 归一化匹配：统一大小写、温度符号、括号、空格等
        3. 常见变体：跨器件别名（如 OPN↔Part Number）
        """
        normalizer = {}  # normalized_key → standard_name
        param_groups = self._get_param_groups(device_type)
        
        for group_name, params in param_groups.items():
            for p in params:
                std_name = p['name']
                # 标准名本身也加入映射
                normalizer[self._normalize_key(std_name)] = std_name
                # 所有别名
                for alias in p.get('aliases', []):
                    normalizer[self._normalize_key(alias)] = std_name
        
        return normalizer

    @staticmethod
    def _normalize_key(name: str) -> str:
        """
        将参数名归一化为统一的 key，用于模糊匹配
        
        规则：
        - 全部小写
        - ℃ → °c → c（温度符号统一）
        - 移除多余空格
        - 全角括号→半角
        - 统一常见变体
        """
        if not name:
            return ''
        key = name.strip().lower()
        # 温度符号统一
        key = key.replace('℃', '°c').replace('°c', 'c').replace('°', '')
        # 全角→半角
        key = key.replace('（', '(').replace('）', ')').replace('：', ':')
        # 统一连字符和空格
        key = key.replace('—', '-').replace('–', '-')
        # 移除多余空格
        key = ' '.join(key.split())
        return key

    def _normalize_param_name(self, name: str, normalizer: Dict[str, str]) -> str:
        """
        用 normalizer 映射表将AI输出的参数名归一化为标准名
        
        匹配策略（按优先级）：
        1. 精确归一化匹配
        2. 去除温度后缀后匹配
        3. 子串包含匹配（短名→长名）
        """
        if not name:
            return name
        
        key = self._normalize_key(name)
        
        # 1. 精确归一化匹配
        if key in normalizer:
            return normalizer[key]
        
        # 2. 尝试去掉常见修饰词后匹配
        # 比如 AI 返回 "VCE(sat) typ" 但配置里是 "VCE(sat)-type (Tj=25℃)"
        for norm_key, std_name in normalizer.items():
            # 双向包含检查（要求至少4字符避免误匹配）
            if len(key) >= 4 and len(norm_key) >= 4:
                if key in norm_key or norm_key in key:
                    return std_name
        
        # 未匹配，原样返回
        return name

    def _normalize_results(self, result: 'ExtractionResult', device_type: str) -> 'ExtractionResult':
        """
        对提取结果的所有参数名进行归一化
        """
        normalizer = self._build_name_normalizer(device_type)
        
        seen = {}  # 去重：同一标准名只保留第一个
        normalized_params = []
        
        for p in result.params:
            original_name = p.standard_name
            normalized_name = self._normalize_param_name(original_name, normalizer)
            
            if normalized_name != original_name:
                logger.info(f"名称归一化: '{original_name}' → '{normalized_name}'")
                p.variant_name = p.variant_name or original_name  # 保留原始名
            
            p.standard_name = normalized_name
            
            # 去重
            if normalized_name not in seen:
                seen[normalized_name] = p
                normalized_params.append(p)
            else:
                # 如果重复，保留 value 更长的那个（通常更完整）
                existing = seen[normalized_name]
                if len(p.value) > len(existing.value):
                    normalized_params.remove(existing)
                    seen[normalized_name] = p
                    normalized_params.append(p)
        
        result.params = normalized_params
        return result

    # ==================== Prompt 构建（精简版） ====================

    def _build_prompt(self, pdf_content: str, group_name: str,
                      params: List[Dict], notes: List[Dict]) -> str:
        """
        构建精简 Prompt
        只包含：PDF内容 + 参数清单（名称+别称）+ 相关注意事项
        """
        # 1. 构建参数清单表格
        param_lines = []
        for p in params:
            name = p['name']
            aliases = p.get('aliases', [])
            alias_str = ', '.join(aliases) if aliases else ''
            param_lines.append(f"| {name} | {alias_str} |")
        param_table = '\n'.join(param_lines)

        # 2. 构建注意事项（只取与当前参数组相关的）
        param_names = {p['name'] for p in params}
        relevant_notes = []
        for note in notes:
            note_param = note.get('param', '')
            # 如果注意事项关联的参数在当前组中，或者是通用注意事项
            if note_param in param_names or note_param == '*':
                rule = note.get('rule', '')
                if rule:
                    relevant_notes.append(f"- {note_param}: {rule}")

        notes_section = ""
        if relevant_notes:
            notes_section = "\n## 提取注意事项\n" + '\n'.join(relevant_notes)

        # 3. 组装 Prompt
        prompt = f"""你是功率半导体参数提取专家。从以下PDF内容中提取【{group_name}】相关参数。

## 需要提取的参数（共{len(params)}项）
| 标准参数名 | PDF中可能的写法 |
|---|---|
{param_table}

## 提取要求
1. standard_name必须严格使用上表第一列的【标准参数名】原文，不要自创名字
2. value只写纯数值+单位（如"1.15mΩ"），测试条件写在test_condition
3. PDF中确实没有的参数必须跳过，严禁编造
4. 表格中"---"或空白表示该值不存在，不要用相邻列替代
5. 保留数值正负号
{notes_section}

## PDF内容
{pdf_content}

## 输出格式（严格JSON，不要添加任何其他文字）
```json
{{"params":[{{"standard_name":"标准参数名","value":"纯数值+单位","test_condition":"测试条件","variant_name":"PDF原始名"}}]}}
```

请逐项检查参数清单，提取所有能找到的参数："""

        return prompt

    # ==================== API 调用 ====================

    @staticmethod
    def _parse_api_error(status_code: int, error_text: str) -> str:
        """解析API错误"""
        try:
            error_json = json.loads(error_text)
            error_msg = error_json.get('message', '') or error_json.get('error', {}).get('message', '')
        except (json.JSONDecodeError, AttributeError):
            error_msg = error_text

        if status_code == 402 or 'insufficient' in error_msg.lower() or 'quota' in error_msg.lower():
            return f"API余额不足，请充值。"
        if status_code == 401:
            return f"API密钥无效，请检查设置。"
        if status_code == 429:
            return f"API限流，请稍后重试。"
        return f"API调用失败（状态码{status_code}）: {error_msg[:200]}"

    async def _call_api_async(self, prompt: str) -> str:
        """异步调用AI API"""
        base_url = self.api_base or "https://api.deepseek.com/v1"
        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是功率半导体参数提取专家。只提取PDF中明确存在的参数，不编造数据。输出严格JSON格式。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 4096
        }

        last_error = None
        async with aiohttp.ClientSession() as session:
            for retry in range(self.max_retries):
                try:
                    async with session.post(url, headers=headers, json=payload,
                                            timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result['choices'][0]['message']['content']
                        else:
                            error_text = await response.text()
                            friendly_error = self._parse_api_error(response.status, error_text)
                            logger.error(f"API调用失败 (状态码 {response.status}): {error_text}")
                            if response.status in (401, 402, 403):
                                raise RuntimeError(friendly_error)
                            last_error = friendly_error
                            if retry < self.max_retries - 1:
                                await asyncio.sleep(2 ** retry)
                except RuntimeError:
                    raise
                except asyncio.TimeoutError:
                    last_error = f"API调用超时（{self.timeout}秒）"
                    logger.warning(f"API超时，重试 {retry + 1}/{self.max_retries}")
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(2 ** retry)
                except Exception as e:
                    last_error = f"API异常: {e}"
                    logger.error(f"API异常: {e}")
                    if retry < self.max_retries - 1:
                        await asyncio.sleep(2 ** retry)

        if last_error:
            raise RuntimeError(last_error)
        return None

    def _call_api_sync(self, prompt: str) -> str:
        """同步调用AI API"""
        try:
            return asyncio.run(self._call_api_async(prompt))
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"调用AI失败: {e}")

    # ==================== 响应解析 ====================

    def _parse_response(self, response: str, pdf_name: str) -> ExtractionResult:
        """解析AI响应"""
        result = ExtractionResult(pdf_name=pdf_name, raw_response=response)

        if not response:
            result.error = "AI响应为空"
            return result

        try:
            # 提取JSON
            json_str = None
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            if not json_str:
                json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
            if not json_str:
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end > start:
                    json_str = response[start:end + 1]
            if not json_str:
                json_str = response

            data = json.loads(json_str.strip())

            # 提取元数据（如果有）
            result.device_type = data.get('device_type', '')
            result.manufacturer = data.get('manufacturer', '')
            result.opn = data.get('opn', '')

            # 解析参数
            seen = set()
            for p in data.get('params', []):
                name = p.get('standard_name', '').strip()
                value = p.get('value', '').strip() if p.get('value') else ''
                if not name or not value:
                    continue
                if name in seen:
                    continue
                seen.add(name)

                # 清洗：分离 value 中混入的测试条件
                test_cond = p.get('test_condition', '') or ''
                value, test_cond = self._separate_value_condition(value, test_cond)

                result.params.append(ExtractedParam(
                    standard_name=name,
                    value=value,
                    test_condition=test_cond.strip(),
                    variant_name=p.get('variant_name', '').strip(),
                ))

        except json.JSONDecodeError as e:
            result.error = f"JSON解析失败: {e}"
        except Exception as e:
            result.error = f"响应解析失败: {e}"

        return result

    @staticmethod
    def _separate_value_condition(value: str, test_condition: str) -> tuple:
        """分离 value 中混入的测试条件"""
        if not value or not isinstance(value, str):
            return value, test_condition

        value = value.strip()

        # "值 @条件"
        m = re.match(r'^([\d.\-+]+\s*[a-zA-ZμΩ℃°/²]*)\s*@\s*(.+)$', value)
        if m:
            cond = m.group(2).strip()
            value = m.group(1).strip()
            test_condition = f"{test_condition}, {cond}".strip(', ') if test_condition else cond
            return value, test_condition

        # "值 (条件)"
        m = re.match(r'^([\d.\-+]+\s*[a-zA-ZμΩ℃°/²]*)\s*[（(]\s*(.+?)\s*[）)]$', value)
        if m and '=' in m.group(2):
            cond = m.group(2).strip()
            value = m.group(1).strip()
            test_condition = f"{test_condition}, {cond}".strip(', ') if test_condition else cond
            return value, test_condition

        # "值; 条件"
        m = re.match(r'^([\d.\-+]+\s*[a-zA-ZμΩ℃°/²]*)\s*[;；]\s*(.+)$', value)
        if m and '=' in m.group(2):
            cond = m.group(2).strip()
            value = m.group(1).strip()
            test_condition = f"{test_condition}, {cond}".strip(', ') if test_condition else cond
            return value, test_condition

        return value, test_condition

    # ==================== 核心提取流程 ====================

    async def extract_params_parallel(self, pdf_content: PDFContent,
                                      params_info: List[Dict[str, Any]]) -> ExtractionResult:
        """
        并行分组提取参数（重构版核心流程）

        流程：
        1. 识别器件类型（正则，不需要AI）
        2. 加载对应的参数配置和注意文档
        3. 按类别分组，每组独立调用AI
        4. 合并结果
        """
        from .pdf_parser import PDFParser
        parser = PDFParser()

        # 1. 识别器件类型
        device_type = (pdf_content.metadata.get('device_type')
                       if getattr(pdf_content, 'metadata', None) else None)
        if not device_type:
            device_type = 'Si MOSFET'  # 默认

        # 2. 获取结构化PDF内容（不截断）
        structured_content = parser.get_structured_content(pdf_content)

        # 3. 加载配置和注意文档
        param_groups = self._get_param_groups(device_type)
        notes = self._load_extraction_notes(device_type)

        if not param_groups:
            logger.warning(f"未找到 {device_type} 的参数配置，降级使用数据库参数")
            return await self._extract_with_db_params(pdf_content, params_info, structured_content, device_type)

        # 4. 拆分大组为 ≤15 参数的小组，提升提取质量
        BATCH_SIZE = 15
        split_groups = {}
        for group_name, params in param_groups.items():
            if not params:
                continue
            for i in range(0, len(params), BATCH_SIZE):
                batch = params[i:i + BATCH_SIZE]
                key = f"{group_name}_{i // BATCH_SIZE + 1}" if len(params) > BATCH_SIZE else group_name
                split_groups[key] = batch

        # 5. 为每个分组创建并行任务
        tasks = []
        group_names = []
        for group_name, params in split_groups.items():
            group_names.append(group_name)
            prompt = self._build_prompt(structured_content, group_name, params, notes)
            tasks.append(self._call_api_async(prompt))

        logger.info(f"[{device_type}] 共 {len(tasks)} 个分组并行提取")

        # 6. 并行执行
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 7. 合并结果
        final_result = ExtractionResult(pdf_name=pdf_content.file_name, device_type=device_type)
        seen_params = {}

        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"分组 [{group_names[i]}] 失败: {response}")
                if not final_result.error:
                    final_result.error = str(response)
                continue
            if not response:
                continue

            res = self._parse_response(response, pdf_content.file_name)
            if res.error:
                logger.warning(f"分组 [{group_names[i]}] 解析警告: {res.error}")

            # 合并元数据
            if res.manufacturer:
                final_result.manufacturer = res.manufacturer
            if res.opn:
                final_result.opn = res.opn

            # 合并参数（去重）
            for p in res.params:
                if p.standard_name not in seen_params:
                    seen_params[p.standard_name] = p
                    final_result.params.append(p)

        # 补充元数据
        if not final_result.manufacturer and pdf_content.metadata.get('manufacturer'):
            final_result.manufacturer = pdf_content.metadata['manufacturer']
        if not final_result.opn and pdf_content.metadata.get('opn'):
            final_result.opn = pdf_content.metadata['opn']

        # 8. 名称归一化（将AI输出的变体名映射回配置标准名）
        final_result = self._normalize_results(final_result, device_type)

        # 9. 易漏参数补充：仅在有遗漏时做一次小型补充提取，尽量不增加耗时
        high_recall = HIGH_RECALL_PARAMS.get(device_type, [])
        if high_recall:
            extracted_names = {p.standard_name for p in final_result.params}
            missing = [n for n in high_recall if n not in extracted_names]
            if 0 < len(missing) <= 12:  # 仅少量遗漏时补充，避免大 prompt
                logger.info(f"易漏补充: 检测到 {len(missing)} 个遗漏，开始补充提取")
                try:
                    supplement = await self._extract_high_recall_pass(
                        structured_content, pdf_content.file_name,
                        device_type, param_groups, notes, missing
                    )
                    if supplement:
                        seen = {p.standard_name for p in final_result.params}
                        for p in supplement.params:
                            if p.standard_name not in seen:
                                seen.add(p.standard_name)
                                final_result.params.append(p)
                        if supplement.params:
                            final_result = self._normalize_results(final_result, device_type)
                            logger.info(f"易漏补充: +{len(supplement.params)} 个参数")
                except Exception as e:
                    logger.warning(f"易漏补充失败: {e}")

        logger.info(f"提取完成: {pdf_content.file_name} → {len(final_result.params)} 个参数")
        return final_result

    def _get_high_recall_extra_hint(self, device_type: str) -> str:
        """按器件类型返回易漏补充的搜索提示，与 YAML 参数表一致"""
        hints = {
            'Si MOSFET': "td-on、tr、td-off、tf、EAS L=0.1mH、Igss、PD Tc=25℃ 等",
            'SiC MOSFET': "td-on、tr、td-off、tf、Eon、Eoff、Etot、Erec、EAS、Igss、PD Tc=25℃ 等",
            'IGBT': "tdon 25℃、tr、tdoff、tf、Eon 25℃（uJ）、Eoff（uJ）、Ets、Erec 等",
        }
        return hints.get(device_type, "Rise time→tr、Fall time→tf 等")

    async def _extract_high_recall_pass(self, structured_content: str, pdf_name: str,
                                        device_type: str, param_groups: Dict,
                                        notes: List, missing_names: List[str]) -> Optional['ExtractionResult']:
        """对易漏参数做一次聚焦提取，仅在有遗漏时调用"""
        params_to_extract = []
        for gname, params in param_groups.items():
            for p in params:
                if p['name'] in missing_names:
                    params_to_extract.append(p)
        if not params_to_extract:
            return None
        group_name = "易漏参数补充"
        prompt = self._build_prompt(structured_content, group_name, params_to_extract, notes)
        hint = self._get_high_recall_extra_hint(device_type)
        extra = f"\n\n【重要】以上参数常在 Dynamic characteristics、Switching characteristics、Electrical characteristics 等表格中被遗漏，请逐行逐列搜索（如 {hint}），务必提取表格中存在的数值。"
        prompt = prompt.replace("请逐项检查参数清单，提取所有能找到的参数：", "请逐项检查参数清单，提取所有能找到的参数：" + extra)
        response = await self._call_api_async(prompt)
        if not response:
            return None
        return self._parse_response(response, pdf_name)

    async def _extract_with_db_params(self, pdf_content: PDFContent,
                                       params_info: List[Dict[str, Any]],
                                       structured_content: str,
                                       device_type: str) -> ExtractionResult:
        """降级方案：用数据库参数列表提取（当YAML配置缺失时）"""
        # 将DB参数转为YAML格式
        params = [{'name': p['param_name'], 'aliases': p.get('variants', [])} for p in params_info]

        # 每15个一组
        groups = {}
        for i in range(0, len(params), 15):
            groups[f"批次_{i // 15 + 1}"] = params[i:i + 15]

        tasks = []
        group_names = []
        for name, group in groups.items():
            group_names.append(name)
            prompt = self._build_prompt(structured_content, name, group, [])
            tasks.append(self._call_api_async(prompt))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        final_result = ExtractionResult(pdf_name=pdf_content.file_name, device_type=device_type)
        seen = {}
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                if not final_result.error:
                    final_result.error = str(response)
                continue
            if not response:
                continue
            res = self._parse_response(response, pdf_content.file_name)
            for p in res.params:
                if p.standard_name not in seen:
                    seen[p.standard_name] = p
                    final_result.params.append(p)
        return final_result

    # ==================== 对外接口（保持兼容） ====================

    def extract_params(self, pdf_content: PDFContent, params_info: List[Dict[str, Any]],
                       fast_mode: bool = False, parallel: bool = True) -> ExtractionResult:
        """
        从PDF内容中提取参数（对外主接口，保持兼容）
        """
        try:
            result = asyncio.run(self.extract_params_parallel(pdf_content, params_info))
            if result and result.error and ('余额' in result.error or '密钥' in result.error):
                return result
            return result
        except RuntimeError as e:
            return ExtractionResult(pdf_name=pdf_content.file_name, error=str(e))
        except Exception as e:
            logger.error(f"提取异常: {e}")
            return ExtractionResult(pdf_name=pdf_content.file_name, error=f"提取失败: {e}")

    async def extract_params_async(self, pdf_content: PDFContent,
                                   params_info: List[Dict[str, Any]]) -> ExtractionResult:
        """异步提取参数"""
        try:
            return await self.extract_params_parallel(pdf_content, params_info)
        except Exception as e:
            return ExtractionResult(pdf_name=pdf_content.file_name, error=str(e))

    async def batch_extract_async(self, pdf_contents: List[PDFContent],
                                  params_info: List[Dict[str, Any]],
                                  max_concurrent: int = 3,
                                  progress_callback=None) -> List[ExtractionResult]:
        """批量并行提取"""
        from asyncio import Semaphore

        semaphore = Semaphore(max_concurrent)
        completed = 0
        total = len(pdf_contents)

        async def extract_one(pdf_content):
            nonlocal completed
            async with semaphore:
                try:
                    result = await self.extract_params_parallel(pdf_content, params_info)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, pdf_content.file_name)
                    return result
                except Exception as e:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, pdf_content.file_name)
                    return ExtractionResult(pdf_name=pdf_content.file_name, error=str(e))

        tasks = [extract_one(pdf) for pdf in pdf_contents]
        return list(await asyncio.gather(*tasks))

    def batch_extract(self, pdf_contents: List[PDFContent],
                      params_info: List[Dict[str, Any]],
                      max_concurrent: int = 3,
                      progress_callback=None) -> List[ExtractionResult]:
        """批量并行提取（同步接口）"""
        return asyncio.run(
            self.batch_extract_async(pdf_contents, params_info, max_concurrent, progress_callback)
        )

    def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        try:
            response = self._call_api_sync("请回复'连接成功'四个字。")
            if response:
                return {'success': True, 'message': '连接成功', 'response': response[:100]}
            return {'success': False, 'message': 'API响应为空', 'response': None}
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}', 'response': None}
