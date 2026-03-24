# -*- coding: utf-8 -*-
"""
详细对比检查：YAML要求 vs PDF原文 vs 实际提取
找出遗漏和不准确的参数
"""
import os, sys, time, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import config
from backend.db_manager import DatabaseManager
from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor

PDF_PATHS = [
    ("Si MOSFET", "/home/gjw/AITOOL/尚阳通规格书/SRT15N050HDatasheetV1.pdf"),
    ("SiC MOSFET", "/home/gjw/AITOOL/尚阳通规格书/SRC60R030BSDatasheetV1.pdf"),
    ("IGBT", "/home/gjw/AITOOL/尚阳通规格书/SRE100N065FSU2DBT-G2 Datasheet V1.3.pdf"),
]


def main():
    db_manager = DatabaseManager()
    params_info = db_manager.get_all_params_with_variants()
    parser = PDFParser()
    ai = AIProcessor()

    for label, pdf_path in PDF_PATHS:
        if not os.path.exists(pdf_path):
            print(f"\n❌ 文件不存在: {pdf_path}")
            continue

        fname = os.path.basename(pdf_path)
        print(f"\n{'='*80}")
        print(f"  [{label}] {fname}")
        print(f"{'='*80}")

        # 1. 解析 PDF
        pdf_content = parser.parse_pdf(pdf_path)
        if pdf_content.error:
            print(f"  ❌ 解析失败: {pdf_content.error}")
            continue

        # 2. 获取结构化文本（用于人工核查）
        structured = parser.get_structured_content(pdf_content)

        # 3. AI 提取
        extraction = ai.extract_params(pdf_content, params_info)
        if extraction.error:
            print(f"  ❌ 提取失败: {extraction.error}")
            continue

        extracted_map = {p.standard_name: p.value for p in extraction.params}
        extracted_cond = {p.standard_name: p.test_condition for p in extraction.params}

        # 4. 加载该器件类型的 YAML 参数列表
        param_groups = ai._get_param_groups(extraction.device_type)
        yaml_params = []
        for gname, plist in param_groups.items():
            for p in plist:
                yaml_params.append(p['name'])

        # 5. 分析
        extracted_set = set(extracted_map.keys())
        yaml_set = set(yaml_params)

        # 5a. YAML 要求但未提取的
        missing = [p for p in yaml_params if p not in extracted_set]
        # 5b. 提取了但不在 YAML 中的（额外的）
        extra = [p for p in extracted_map if p not in yaml_set]

        print(f"\n  识别类型: {extraction.device_type} | OPN: {extraction.opn}")
        print(f"  YAML要求: {len(yaml_params)} 个参数 | 实际提取: {len(extracted_map)} 个参数")
        print(f"  覆盖率: {len(extracted_set & yaml_set)}/{len(yaml_set)} = "
              f"{len(extracted_set & yaml_set)/len(yaml_set)*100:.1f}%")

        # 打印所有提取结果
        print(f"\n  --- 已提取参数 ({len(extracted_map)}) ---")
        for p in yaml_params:
            if p in extracted_map:
                cond = extracted_cond.get(p, '')
                cond_str = f"  [{cond}]" if cond else ""
                print(f"    ✅ {p}: {extracted_map[p]}{cond_str}")
        for p in extra:
            cond = extracted_cond.get(p, '')
            cond_str = f"  [{cond}]" if cond else ""
            print(f"    ➕ {p}: {extracted_map[p]}{cond_str}  (不在YAML中)")

        print(f"\n  --- 未提取参数 ({len(missing)}) ---")
        # 在结构化文本中搜索线索
        for p in missing:
            # 看看PDF文本中有没有相关关键词
            hints = []
            search_terms = [p]
            # 用aliases也搜
            for gname, plist in param_groups.items():
                for item in plist:
                    if item['name'] == p:
                        search_terms.extend(item.get('aliases', [])[:3])
                        break
            for term in search_terms:
                if term.lower() in structured.lower():
                    hints.append(term)
            if hints:
                print(f"    ❌ {p}  ← PDF中可能存在 (匹配: {', '.join(hints[:3])})")
            else:
                print(f"    ⚪ {p}  ← PDF中可能不存在")

        print()


if __name__ == "__main__":
    main()
