#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速模式测试脚本
对比普通模式和快速模式的提取速度和效果
"""

import time
import sys
sys.path.insert(0, '/home/gjw/AITOOL')

from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor
from backend.db_manager import DatabaseManager

def test_prompt_size():
    """对比两种模式的提示词大小"""
    print("=" * 60)
    print("📊 提示词大小对比")
    print("=" * 60)
    
    pdf_parser = PDFParser()
    ai_processor = AIProcessor()
    db_manager = DatabaseManager()
    params_info = db_manager.get_all_params_with_variants()
    
    # 解析PDF
    content = pdf_parser.parse_pdf('/home/gjw/AITOOL/LSGT10R011_V1.0.pdf')
    
    # 普通模式
    device_type = content.metadata.get('device_type', 'Si MOSFET')
    normal_content = pdf_parser.get_structured_content(content, fast_mode=False)
    param_groups = ai_processor._get_param_groups(device_type)
    notes = ai_processor._load_extraction_notes(device_type)
    first_group = list(param_groups.keys())[0] if param_groups else "预览"
    first_params = list(param_groups.values())[0] if param_groups else []
    normal_prompt = ai_processor._build_prompt(normal_content, first_group, first_params, notes)
    
    # 快速模式
    fast_content = pdf_parser.get_structured_content(content, fast_mode=True)
    fast_prompt = ai_processor._build_prompt(fast_content, first_group, first_params, notes)
    
    print(f"\n普通模式:")
    print(f"  PDF内容长度: {len(normal_content)} 字符")
    print(f"  提示词总长度: {len(normal_prompt)} 字符")
    
    print(f"\n快速模式:")
    print(f"  PDF内容长度: {len(fast_content)} 字符")
    print(f"  提示词总长度: {len(fast_prompt)} 字符")
    
    reduction = (1 - len(fast_prompt) / len(normal_prompt)) * 100
    print(f"\n📉 提示词减少: {reduction:.1f}%")
    print()
    
    return reduction

def test_extraction_speed():
    """测试两种模式的提取速度"""
    print("=" * 60)
    print("⏱️ 提取速度对比")
    print("=" * 60)
    
    pdf_parser = PDFParser()
    ai_processor = AIProcessor()
    db_manager = DatabaseManager()
    params_info = db_manager.get_all_params_with_variants()
    
    pdf_file = '/home/gjw/AITOOL/LSGT10R011_V1.0.pdf'
    
    # 解析PDF
    content = pdf_parser.parse_pdf(pdf_file)
    
    # 测试快速模式
    print("\n🚀 测试快速模式...")
    start = time.time()
    fast_result = ai_processor.extract_params(content, params_info, fast_mode=True)
    fast_time = time.time() - start
    print(f"  耗时: {fast_time:.1f}秒")
    print(f"  提取参数: {len(fast_result.params)}个")
    
    # 测试普通模式
    print("\n📋 测试普通模式...")
    start = time.time()
    normal_result = ai_processor.extract_params(content, params_info, fast_mode=False)
    normal_time = time.time() - start
    print(f"  耗时: {normal_time:.1f}秒")
    print(f"  提取参数: {len(normal_result.params)}个")
    
    # 对比
    print("\n" + "=" * 60)
    print("📈 对比结果")
    print("=" * 60)
    print(f"普通模式: {normal_time:.1f}秒, {len(normal_result.params)}个参数")
    print(f"快速模式: {fast_time:.1f}秒, {len(fast_result.params)}个参数")
    
    speedup = normal_time / fast_time if fast_time > 0 else 0
    time_saved = normal_time - fast_time
    print(f"\n⚡ 速度提升: {speedup:.2f}x")
    print(f"⏱️ 节省时间: {time_saved:.1f}秒")
    
    # 检查参数差异
    normal_params = set(p.param_name for p in normal_result.params)
    fast_params = set(p.param_name for p in fast_result.params)
    
    missing = normal_params - fast_params
    if missing:
        print(f"\n⚠️ 快速模式缺少的参数 ({len(missing)}个):")
        for p in sorted(missing)[:10]:  # 只显示前10个
            print(f"  - {p}")
        if len(missing) > 10:
            print(f"  ... 还有{len(missing)-10}个")
    else:
        print(f"\n✅ 快速模式提取的参数与普通模式相同!")
    
    # 计算参数覆盖率
    coverage = len(fast_params & normal_params) / len(normal_params) * 100 if normal_params else 0
    print(f"\n📊 参数覆盖率: {coverage:.1f}%")

if __name__ == '__main__':
    test_prompt_size()
    test_extraction_speed()

