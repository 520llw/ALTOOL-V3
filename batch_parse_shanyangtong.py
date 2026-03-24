# -*- coding: utf-8 -*-
"""
尚阳通规格书 - 后端直接批量解析并生成三份表格

用法：在项目根目录执行
  python batch_parse_shanyangtong.py

流程：
  1. 批量解析「尚阳通规格书」文件夹内所有 PDF（带缓存与 MD5）
  2. AI 提取参数并写入数据库（user_id=None，与前端隔离）
  3. 按器件类型生成三份 Excel：Si MOSFET、SiC MOSFET、IGBT
"""

import sys
import time
from pathlib import Path
from collections import defaultdict

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import config
from backend.db_manager import DatabaseManager
from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor
from backend.data_writer import DataWriter

# 尚阳通规格书目录（项目根下）
PDF_DIR = PROJECT_ROOT / "尚阳通规格书"

# 三份表格对应的器件类型（与系统一致）
DEVICE_TYPES = ["Si MOSFET", "SiC MOSFET", "IGBT"]


def main():
    print("=" * 60)
    print("  尚阳通规格书 · 后端批量解析并生成三份表格")
    print("=" * 60)
    print(f"  PDF 目录: {PDF_DIR}")
    print(f"  模型: {config.ai.model} | {config.ai.provider}")
    print("=" * 60)

    if not PDF_DIR.exists():
        print(f"\n❌ 目录不存在: {PDF_DIR}")
        print("   请将尚阳通规格书 PDF 放入该目录后重试。")
        return 1

    db = DatabaseManager()
    pdf_parser = PDFParser()
    ai_processor = AIProcessor()
    data_writer = DataWriter(db)

    # 参数库检查
    params_info = db.get_all_params_with_variants()
    if not params_info:
        print("\n❌ 参数库为空，请先在系统「参数管理」中初始化参数库后再运行。")
        return 1
    print(f"\n✓ 参数库: {len(params_info)} 个标准参数")

    # ---------- 阶段 1：批量解析 PDF（带缓存） ----------
    print("\n[1/3] 批量解析 PDF（含 MD5 缓存）...")
    start_parse = time.time()

    def on_parse_progress(idx, total, name, status):
        if total:
            print(f"  解析进度: {idx + 1}/{total} - {name or ''}", end="\r")

    pdf_contents = pdf_parser.batch_parse(
        str(PDF_DIR),
        progress_callback=on_parse_progress,
        use_cache=True,
    )
    parse_elapsed = time.time() - start_parse

    pdf_ok = [c for c in pdf_contents if not c.error]
    parse_failed = len(pdf_contents) - len(pdf_ok)
    print(f"\n✓ 解析完成: 成功 {len(pdf_ok)}，失败 {parse_failed}，耗时 {parse_elapsed:.1f}s")

    if not pdf_ok:
        print("\n❌ 没有可用的 PDF 内容，无法继续。")
        return 1

    # ---------- 阶段 2：AI 批量提取并写入数据库 ----------
    print("\n[2/3] AI 参数提取并写入数据库...")
    start_extract = time.time()

    def on_extract_progress(completed, total, pdf_name):
        if total:
            print(f"  AI 提取: {completed}/{total} - {pdf_name or ''}", end="\r")

    results = ai_processor.batch_extract(
        pdf_ok,
        params_info,
        max_concurrent=config.parser.max_workers,
        progress_callback=on_extract_progress,
    )
    extract_elapsed = time.time() - start_extract

    success_count = sum(1 for r in results if not r.error)
    print(f"\n✓ 提取完成: 成功 {success_count}/{len(results)}，耗时 {extract_elapsed:.1f}s")

    data_writer.write_to_database(results, user_id=None)
    print("✓ 结果已写入数据库（user_id=None）")

    # ---------- 阶段 3：按器件类型生成三份表格 ----------
    print("\n[3/3] 按器件类型生成三份表格...")
    by_type = defaultdict(list)
    for r in results:
        if r.error:
            continue
        dtype = r.device_type or "Si MOSFET"
        by_type[dtype].append(r.pdf_name)

    generated = []
    for device_type in DEVICE_TYPES:
        pdf_list = by_type.get(device_type, [])
        if not pdf_list:
            print(f"  跳过 {device_type}: 无该类型解析结果")
            continue
        out = data_writer.generate_table_by_conditions(
            device_type,
            pdf_list,
            created_by="batch_parse_shanyangtong",
            user_id=None,
        )
        if out.get("success"):
            generated.append((device_type, out["file_path"], out["pdf_count"]))
            print(f"  ✓ {device_type}: {out['file_path']}（{out['pdf_count']} 个 PDF）")
        else:
            print(f"  ✗ {device_type}: {out.get('error', '生成失败')}")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    if generated:
        print("  生成的三份表格文件：")
        for dtype, path, count in generated:
            print(f"    · {dtype}: {path} （{count} 个 PDF）")
    else:
        print("  未生成任何表格（可能没有对应器件类型的解析结果）。")
    print("=" * 60)
    return 0 if generated else 1


if __name__ == "__main__":
    sys.exit(main())
