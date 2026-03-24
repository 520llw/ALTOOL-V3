# -*- coding: utf-8 -*-
"""
提取性能与费用测试脚本
测试20份PDF的提取速度、API调用次数和费用估算
"""

import sys
import os
import time
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor

# 配置
PDF_DIR = Path("尚阳通规格书")
PROCESSED_LOG = Path("optimized_pdfs.log")
TEST_COUNT = 20

# DeepSeek API 费用（参考价格，实际以官方为准）
# 输入: $0.14 / 1M tokens, 输出: $0.28 / 1M tokens
INPUT_COST_PER_MILLION = 0.14  # USD
OUTPUT_COST_PER_MILLION = 0.28  # USD

# Token估算（粗略：1 token ≈ 0.75 中文字符 ≈ 4 英文字符）
def estimate_tokens(text: str) -> int:
    """粗略估算token数量"""
    if not text:
        return 0
    # 中文字符按1.3倍计算，英文按0.25倍
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.3 + other_chars * 0.25)


async def test_one_pdf(ai: AIProcessor, parser: PDFParser, pdf_path: Path) -> Dict[str, Any]:
    """测试单份PDF的提取性能"""
    pdf_name = pdf_path.name
    start_time = time.time()
    
    # 解析PDF
    parse_start = time.time()
    pdf_content = parser.parse_pdf(str(pdf_path))
    parse_time = time.time() - parse_start
    
    device_type = pdf_content.metadata.get('device_type', 'Si MOSFET')
    structured_content = parser.get_structured_content(pdf_content)
    
    # 获取参数分组数量（用于估算API调用次数）
    param_groups = ai._get_param_groups(device_type)
    group_count = len([g for g in param_groups.values() if g])  # 非空分组数
    
    # 估算输入token（prompt长度）
    notes = ai._load_extraction_notes(device_type)
    notes_text = '\n'.join([n.get('rule', '') for n in notes])
    
    # 构建一个示例prompt来估算长度
    sample_group = list(param_groups.values())[0] if param_groups else []
    sample_prompt = ai._build_prompt(structured_content[:1000], "示例组", sample_group[:5], notes[:3])
    
    # 实际prompt会更长（完整PDF内容），这里用比例估算
    avg_prompt_length = len(sample_prompt) * (len(structured_content) / 1000) if structured_content else len(sample_prompt)
    estimated_input_tokens = estimate_tokens(structured_content) + estimate_tokens(notes_text) + estimate_tokens(sample_prompt)
    
    # 执行提取
    extract_start = time.time()
    try:
        extraction = await ai.extract_params_parallel(pdf_content, [])
        extract_time = time.time() - extract_start
        total_time = time.time() - start_time
        
        # 估算输出token（返回的JSON）
        output_text = json.dumps([{
            'standard_name': p.standard_name,
            'value': p.value,
            'test_condition': p.test_condition
        } for p in extraction.params], ensure_ascii=False)
        estimated_output_tokens = estimate_tokens(output_text) * group_count  # 每个分组一次输出
        
        # 计算费用（USD）
        input_cost = (estimated_input_tokens / 1_000_000) * INPUT_COST_PER_MILLION * group_count
        output_cost = (estimated_output_tokens / 1_000_000) * OUTPUT_COST_PER_MILLION
        total_cost = input_cost + output_cost
        
        return {
            'pdf_name': pdf_name,
            'device_type': device_type,
            'success': True,
            'parse_time': round(parse_time, 2),
            'extract_time': round(extract_time, 2),
            'total_time': round(total_time, 2),
            'group_count': group_count,
            'extracted_count': len(extraction.params),
            'estimated_input_tokens': estimated_input_tokens,
            'estimated_output_tokens': estimated_output_tokens,
            'estimated_cost_usd': round(total_cost, 6),
            'error': extraction.error if extraction.error else None
        }
    except Exception as e:
        extract_time = time.time() - extract_start
        total_time = time.time() - start_time
        return {
            'pdf_name': pdf_name,
            'device_type': device_type,
            'success': False,
            'parse_time': round(parse_time, 2),
            'extract_time': round(extract_time, 2),
            'total_time': round(total_time, 2),
            'group_count': group_count,
            'extracted_count': 0,
            'estimated_input_tokens': estimated_input_tokens if 'estimated_input_tokens' in locals() else 0,
            'estimated_output_tokens': 0,
            'estimated_cost_usd': 0,
            'error': str(e)
        }


async def main():
    """主测试流程"""
    # 加载已优化的PDF列表（这些PDF已经提取过，排除）
    processed = set()
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG, 'r', encoding='utf-8') as f:
            processed = {line.strip() for line in f if line.strip()}
    
    # 选择完全未提取过的PDF（排除所有已优化的）
    pdf_files = sorted([p for p in PDF_DIR.iterdir() if p.suffix.lower() == '.pdf'])
    unprocessed = [p for p in pdf_files if p.name not in processed]
    
    if not unprocessed:
        print("❌ 错误: 没有找到未提取过的PDF！")
        print(f"   已优化的PDF数量: {len(processed)}")
        print(f"   总PDF数量: {len(pdf_files)}")
        return
    
    if len(unprocessed) < TEST_COUNT:
        print(f"⚠️  未优化的PDF只有 {len(unprocessed)} 份，将测试全部")
        test_pdfs = unprocessed
    else:
        test_pdfs = unprocessed[:TEST_COUNT]
    
    print(f"{'='*80}")
    print(f"提取性能与费用测试")
    print(f"测试PDF数量: {len(test_pdfs)}")
    print(f"{'='*80}\n")
    
    parser = PDFParser()
    ai = AIProcessor()
    ai.timeout = 180
    
    results = []
    total_start = time.time()
    
    for i, pdf_path in enumerate(test_pdfs, 1):
        print(f"[{i}/{len(test_pdfs)}] 处理: {pdf_path.name}")
        result = await test_one_pdf(ai, parser, pdf_path)
        results.append(result)
        
        if result['success']:
            print(f"  ✅ 成功 | 耗时: {result['total_time']}s | "
                  f"提取: {result['extracted_count']}个 | "
                  f"分组: {result['group_count']}个 | "
                  f"费用: ${result['estimated_cost_usd']:.6f}")
        else:
            print(f"  ❌ 失败 | 耗时: {result['total_time']}s | 错误: {result['error']}")
        print()
    
    total_time = time.time() - total_start
    
    # 统计汇总
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    if successful:
        avg_time = sum(r['total_time'] for r in successful) / len(successful)
        avg_extract_time = sum(r['extract_time'] for r in successful) / len(successful)
        avg_parse_time = sum(r['parse_time'] for r in successful) / len(successful)
        avg_group_count = sum(r['group_count'] for r in successful) / len(successful)
        avg_extracted = sum(r['extracted_count'] for r in successful) / len(successful)
        total_cost = sum(r['estimated_cost_usd'] for r in successful)
        avg_cost = total_cost / len(successful)
        
        print(f"{'='*80}")
        print(f"📊 测试结果汇总")
        print(f"{'='*80}")
        print(f"总PDF数: {len(test_pdfs)}")
        print(f"成功: {len(successful)} | 失败: {len(failed)}")
        print(f"\n⏱️  速度统计:")
        print(f"  总耗时: {total_time:.2f}s ({total_time/60:.2f}分钟)")
        print(f"  平均每份总耗时: {avg_time:.2f}s")
        print(f"  平均解析耗时: {avg_parse_time:.2f}s")
        print(f"  平均提取耗时: {avg_extract_time:.2f}s")
        print(f"\n📈 提取统计:")
        print(f"  平均分组数: {avg_group_count:.1f}")
        print(f"  平均提取参数数: {avg_extracted:.1f}")
        print(f"\n💰 费用估算 (USD):")
        print(f"  总费用: ${total_cost:.6f}")
        print(f"  平均每份: ${avg_cost:.6f}")
        print(f"  平均每份 (人民币, 按7.2汇率): ¥{avg_cost * 7.2:.4f}")
        print(f"{'='*80}")
        
        # 按器件类型分组统计
        by_device = {}
        for r in successful:
            dt = r['device_type']
            if dt not in by_device:
                by_device[dt] = []
            by_device[dt].append(r)
        
        if len(by_device) > 1:
            print(f"\n📋 按器件类型统计:")
            for dt, rs in sorted(by_device.items()):
                avg_t = sum(r['total_time'] for r in rs) / len(rs)
                avg_c = sum(r['estimated_cost_usd'] for r in rs) / len(rs)
                print(f"  {dt}: {len(rs)}份 | 平均耗时: {avg_t:.2f}s | 平均费用: ${avg_c:.6f}")
    
    # 保存详细结果
    report_path = Path(f"extraction_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'total_pdfs': len(test_pdfs),
            'successful': len(successful),
            'failed': len(failed),
            'total_time_seconds': round(total_time, 2),
            'results': results,
            'summary': {
                'avg_time_per_pdf': round(avg_time, 2) if successful else 0,
                'avg_extract_time': round(avg_extract_time, 2) if successful else 0,
                'avg_parse_time': round(avg_parse_time, 2) if successful else 0,
                'avg_group_count': round(avg_group_count, 1) if successful else 0,
                'avg_extracted_count': round(avg_extracted, 1) if successful else 0,
                'total_cost_usd': round(total_cost, 6) if successful else 0,
                'avg_cost_per_pdf_usd': round(avg_cost, 6) if successful else 0,
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
