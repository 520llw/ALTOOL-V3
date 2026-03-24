# -*- coding: utf-8 -*-
"""
验证猜想（v2）：关注"最终写入表格的数据质量"

核心指标：
- 表格准确率 = 正确值的数量 / 实际写入表格的数量
- 表格污染率 = 错误值的数量 / 实际写入表格的数量
- 召回率 = 实际写入表格的数量 / PDF中应有的数量

重点：只看会被写入表格的参数（即 DB标准名 ∩ GT中有的 ∩ AI提出来的）
"""
import sys
import time
import json
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent))

from backend.db_manager import DatabaseManager
from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor


def normalize_for_compare(val):
    if not val:
        return ""
    s = str(val).lower().strip()
    s = s.replace('ω', 'ohm').replace('Ω', 'ohm').replace('º', '°')
    s = re.sub(r'\s+', '', s)
    return s


def values_match(extracted, ground_truth):
    if not extracted or not ground_truth:
        return False
    e = normalize_for_compare(extracted)
    g = normalize_for_compare(ground_truth)
    if e == g:
        return True
    e_nums = re.findall(r'[-+]?\d*\.?\d+', e)
    g_nums = re.findall(r'[-+]?\d*\.?\d+', g)
    if e_nums and g_nums:
        try:
            ev = float(e_nums[0])
            gv = float(g_nums[0])
            if gv != 0 and abs(ev - gv) / abs(gv) < 0.05:
                return True
            if gv == 0 and ev == 0:
                return True
        except:
            pass
    if e in g or g in e:
        return True
    return False


def run_table_quality_test():
    db = DatabaseManager()
    parser = PDFParser()
    ai = AIProcessor()
    ai.timeout = 180

    with open("shanyangtong_ground_truth.json", "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    pdf_name = "Sanrise-SRE50N120FSUS7(1).pdf"
    gt = gt_data[pdf_name]
    gt_keys = set(gt.keys())

    pdf_path = f"/home/gjw/AITOOL/尚阳通规格书/{pdf_name}"
    pdf_content = parser.parse_pdf(pdf_path)
    all_params = db.get_all_params_with_variants()
    db_param_names = set(p['param_name'] for p in all_params)

    # 会被写入表格的参数 = DB标准名 ∩ GT中有的
    table_target_params = db_param_names & gt_keys

    levels = [
        ("1. 极简 (10项)",    all_params[:10]),
        ("2. 轻量 (30项)",    all_params[:30]),
        ("3. 中等 (60项)",    all_params[:60]),
        ("4. 重负载 (100项)", all_params[:100]),
        ("5. 全量 (143项)",   all_params),
    ]

    all_results = []

    print("=" * 90, flush=True)
    print("  实验v2：参数规模 vs 最终表格数据质量", flush=True)
    print(f"  测试文件: {pdf_name}", flush=True)
    print(f"  PDF中会写入表格的参数: {len(table_target_params)} 项", flush=True)
    print("=" * 90, flush=True)

    structured_content = parser.get_structured_content(pdf_content)

    for level_name, params_subset in levels:
        print(f"\n{'─'*90}", flush=True)
        print(f"🚀 {level_name}", flush=True)
        print(f"{'─'*90}", flush=True)

        start_time = time.time()
        subset_names = set(p['param_name'] for p in params_subset)

        # 这轮请求中，哪些参数是"会写入表格"的目标
        target_this_round = subset_names & table_target_params
        noise_this_round = len(subset_names) - len(target_this_round)

        print(f"   请求: {len(subset_names)} | 目标(会入表): {len(target_this_round)} | 噪声(不会入表): {noise_this_round}", flush=True)

        # 构建prompt：将params_subset转为YAML格式的参数列表
        yaml_params = [{'name': p['param_name'], 'aliases': p.get('variants', [])} for p in params_subset]
        notes = ai._load_extraction_notes('IGBT')
        prompt = ai._build_prompt(structured_content, f"批次_{level_name}", yaml_params, notes)
        print(f"   Prompt: {len(prompt)} 字符 → 调用API...", flush=True)

        try:
            response = ai._call_api_sync(prompt)
            extract_result = ai._parse_response(response, pdf_name)
            elapsed = time.time() - start_time

            extracted_map = {}
            for p in extract_result.params:
                extracted_map[p.standard_name] = p.value

            # ====== 只看"会写入表格"的参数 ======
            written_correct = []    # 写入表格且值正确
            written_wrong = []      # 写入表格但值错误 ← 用户最关心的！
            not_written = []        # 应该写入但AI没提取到

            for param_name in target_this_round:
                gt_val = gt[param_name]
                if param_name in extracted_map:
                    ai_val = extracted_map[param_name]
                    if not ai_val or str(ai_val).strip() in ['---', 'N/A', '']:
                        not_written.append(param_name)
                    elif values_match(ai_val, gt_val):
                        written_correct.append((param_name, ai_val))
                    else:
                        written_wrong.append((param_name, ai_val, gt_val))
                else:
                    not_written.append(param_name)

            total_written = len(written_correct) + len(written_wrong)
            table_accuracy = (len(written_correct) / total_written * 100) if total_written > 0 else 0
            table_error_rate = (len(written_wrong) / total_written * 100) if total_written > 0 else 0
            recall = (total_written / len(target_this_round) * 100) if target_this_round else 0

            result = {
                "level": level_name,
                "requested": len(subset_names),
                "target": len(target_this_round),
                "noise": noise_this_round,
                "written_total": total_written,
                "correct": len(written_correct),
                "wrong": len(written_wrong),
                "missed": len(not_written),
                "accuracy": table_accuracy,
                "error_rate": table_error_rate,
                "recall": recall,
                "elapsed": elapsed,
                "wrong_details": written_wrong,
            }
            all_results.append(result)

            print(f"\n   📋 写入表格: {total_written} 项 (目标 {len(target_this_round)} 项)", flush=True)
            print(f"   ✅ 正确: {len(written_correct)} 项", flush=True)
            print(f"   ❌ 错误(会污染表格): {len(written_wrong)} 项", flush=True)
            print(f"   ⬜ 未提取(表格留空): {len(not_written)} 项", flush=True)
            print(f"   📊 表格准确率: {table_accuracy:.1f}% | 污染率: {table_error_rate:.1f}% | 召回率: {recall:.1f}%", flush=True)
            print(f"   ⏱️  耗时: {elapsed:.1f}s", flush=True)

            if written_wrong:
                print(f"\n   🔴 【表格错误数据详情】—— 这些值会被错误地写入表格：", flush=True)
                for pname, ai_val, gt_val in written_wrong:
                    print(f"      ❌ {pname}: AI写入=\"{ai_val}\" → 正确应为=\"{gt_val}\"", flush=True)

            if not_written:
                print(f"\n   ⬜ [未提取清单] {', '.join(sorted(not_written)[:8])}{'...' if len(not_written)>8 else ''}", flush=True)

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ 出错({elapsed:.1f}s): {e}", flush=True)
            all_results.append({
                "level": level_name, "requested": len(subset_names),
                "target": len(target_this_round), "noise": noise_this_round,
                "written_total": 0, "correct": 0, "wrong": 0,
                "missed": len(target_this_round), "accuracy": 0,
                "error_rate": 0, "recall": 0, "elapsed": elapsed,
                "wrong_details": [],
            })

    # ========== 汇总 ==========
    print("\n\n" + "=" * 110, flush=True)
    print("  📊 最终表格质量 — 汇总对比表", flush=True)
    print("=" * 110, flush=True)
    header = f"{'负载等级':<18} | {'请求':>4} | {'目标':>4} | {'噪声':>4} | {'入表':>4} | {'正确':>4} | {'❌错误':>5} | {'留空':>4} | {'表格准确率':>8} | {'污染率':>6} | {'召回率':>6} | {'耗时':>6}"
    print(header, flush=True)
    print("─" * 110, flush=True)
    for r in all_results:
        row = (
            f"{r['level']:<18} | "
            f"{r['requested']:>4} | "
            f"{r['target']:>4} | "
            f"{r['noise']:>4} | "
            f"{r['written_total']:>4} | "
            f"{r['correct']:>4} | "
            f"{r['wrong']:>5} | "
            f"{r['missed']:>4} | "
            f"{r['accuracy']:>7.1f}% | "
            f"{r['error_rate']:>5.1f}% | "
            f"{r['recall']:>5.1f}% | "
            f"{r['elapsed']:>5.1f}s"
        )
        print(row, flush=True)
    print("=" * 110, flush=True)

    # ========== 趋势 ==========
    valid = [r for r in all_results if r['written_total'] > 0]
    if len(valid) >= 2:
        print("\n📈 趋势分析:", flush=True)
        print(f"   表格准确率: {valid[0]['accuracy']:.1f}% → {valid[-1]['accuracy']:.1f}% (Δ = {valid[-1]['accuracy']-valid[0]['accuracy']:+.1f}%)", flush=True)
        print(f"   污染率:     {valid[0]['error_rate']:.1f}% → {valid[-1]['error_rate']:.1f}% (Δ = {valid[-1]['error_rate']-valid[0]['error_rate']:+.1f}%)", flush=True)
        print(f"   召回率:     {valid[0]['recall']:.1f}% → {valid[-1]['recall']:.1f}% (Δ = {valid[-1]['recall']-valid[0]['recall']:+.1f}%)", flush=True)

        err_trend = valid[-1]['error_rate'] - valid[0]['error_rate']
        if err_trend > 10:
            print("\n   ⚠️  结论：参数增多导致表格污染率显著上升！写入表格的错误数据变多了。", flush=True)
        elif err_trend > 3:
            print("\n   🔶 结论：污染率有所上升，部分参数值会出错。", flush=True)
        else:
            print("\n   ✅ 结论：表格数据质量稳定。", flush=True)

    # ========== 汇总所有级别的错误数据 ==========
    print("\n\n" + "=" * 90, flush=True)
    print("  🔴 所有级别中出现的错误数据汇总（会污染表格的）", flush=True)
    print("=" * 90, flush=True)
    all_wrong = {}
    for r in all_results:
        for pname, ai_val, gt_val in r.get('wrong_details', []):
            if pname not in all_wrong:
                all_wrong[pname] = []
            all_wrong[pname].append((r['level'], ai_val, gt_val))

    if all_wrong:
        for pname, occurrences in sorted(all_wrong.items()):
            print(f"\n   📌 {pname}:", flush=True)
            for level, ai_val, gt_val in occurrences:
                print(f"      {level}: AI=\"{ai_val}\" vs GT=\"{gt_val}\"", flush=True)
        
        # 统计哪些参数最容易出错
        print(f"\n   📊 易错参数排行（出现错误的级别数）:", flush=True)
        for pname, occurrences in sorted(all_wrong.items(), key=lambda x: -len(x[1])):
            print(f"      {pname}: 在 {len(occurrences)}/{len(valid)} 个级别中出错", flush=True)
    else:
        print("   无错误数据！", flush=True)


if __name__ == "__main__":
    run_table_quality_test()
