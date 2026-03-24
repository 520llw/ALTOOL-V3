# -*- coding: utf-8 -*-
"""
参数提取测试脚本
测试5份PDF的提取时间和准确率
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 强制无缓冲输出
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

def log(msg):
    """带刷新的打印"""
    print(msg, flush=True)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import config
from backend.db_manager import DatabaseManager
from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor

# 测试用的PDF文件列表
PDF_FILES = [
    "LSGT10R011_V1.0.pdf",
    "LSGT10R013_V1.1(1).pdf",
    "LSGT10R016_V1.0.pdf",
    "LSGT20R089HCF _V1.3.pdf",
    "快捷芯KJ06N20T.pdf"
]

def init_params_if_needed(db_manager):
    """检查并初始化参数库"""
    params = db_manager.get_all_params_with_variants()
    if not params:
        print("⚠️  参数库为空，正在初始化...")
        # 简化版参数初始化
        from main import initialize_params_from_excel
        count = initialize_params_from_excel()
        print(f"✅ 初始化了 {count} 个参数")
        return db_manager.get_all_params_with_variants()
    return params

def test_single_pdf(pdf_path: str, parser: PDFParser, ai_processor: AIProcessor, 
                    params_info: list) -> dict:
    """
    测试单个PDF的提取效果
    
    Returns:
        包含时间、结果等信息的字典
    """
    result = {
        'pdf_name': os.path.basename(pdf_path),
        'pdf_parse_time': 0,
        'ai_extract_time': 0,
        'total_time': 0,
        'success': False,
        'error': None,
        'device_type': '',
        'manufacturer': '',
        'opn': '',
        'extracted_params_count': 0,
        'extracted_params': [],
        'unrecognized_params': []
    }
    
    total_start = time.time()
    
    # 1. PDF解析阶段
    print(f"\n{'='*60}")
    print(f"📄 正在处理: {result['pdf_name']}")
    print(f"{'='*60}")
    
    parse_start = time.time()
    pdf_content = parser.parse_pdf(pdf_path)
    result['pdf_parse_time'] = round(time.time() - parse_start, 2)
    
    if pdf_content.error:
        result['error'] = f"PDF解析失败: {pdf_content.error}"
        result['total_time'] = round(time.time() - total_start, 2)
        print(f"❌ PDF解析失败: {pdf_content.error}")
        return result
    
    print(f"  📖 PDF解析完成 ({result['pdf_parse_time']}s)")
    print(f"     - 页数: {pdf_content.page_count}")
    print(f"     - 表格数: {len(pdf_content.tables)}")
    print(f"     - 预识别OPN: {pdf_content.metadata.get('opn', '无')}")
    print(f"     - 预识别厂家: {pdf_content.metadata.get('manufacturer', '无')}")
    print(f"     - 预识别类型: {pdf_content.metadata.get('device_type', '无')}")
    
    # 2. AI提取阶段
    print(f"\n  🤖 正在调用AI提取参数...")
    ai_start = time.time()
    extraction_result = ai_processor.extract_params(pdf_content, params_info)
    result['ai_extract_time'] = round(time.time() - ai_start, 2)
    
    if extraction_result.error:
        result['error'] = f"AI提取失败: {extraction_result.error}"
        result['total_time'] = round(time.time() - total_start, 2)
        print(f"❌ AI提取失败: {extraction_result.error}")
        return result
    
    # 3. 整理结果
    result['success'] = True
    result['device_type'] = extraction_result.device_type
    result['manufacturer'] = extraction_result.manufacturer
    result['opn'] = extraction_result.opn
    result['extracted_params_count'] = len(extraction_result.params)
    result['unrecognized_params'] = extraction_result.unrecognized_params
    
    # 收集提取的参数
    for param in extraction_result.params:
        result['extracted_params'].append({
            'name': param.standard_name,
            'value': param.value,
            'condition': param.test_condition
        })
    
    result['total_time'] = round(time.time() - total_start, 2)
    
    print(f"  ✅ AI提取完成 ({result['ai_extract_time']}s)")
    print(f"     - 器件类型: {result['device_type']}")
    print(f"     - 厂家: {result['manufacturer']}")
    print(f"     - OPN: {result['opn']}")
    print(f"     - 提取参数数: {result['extracted_params_count']}")
    
    return result

def print_extracted_params(params: list, limit: int = 20):
    """打印提取的参数"""
    print(f"\n  📋 提取的参数 (前{min(limit, len(params))}项):")
    print(f"  {'参数名':<25} {'参数值':<20} {'测试条件':<30}")
    print(f"  {'-'*75}")
    
    for i, param in enumerate(params[:limit]):
        name = param['name'][:24] if len(param['name']) > 24 else param['name']
        value = param['value'][:19] if len(param['value']) > 19 else param['value']
        condition = param['condition'][:29] if len(param['condition']) > 29 else param['condition']
        print(f"  {name:<25} {value:<20} {condition:<30}")
    
    if len(params) > limit:
        print(f"  ... 还有 {len(params) - limit} 项未显示")

def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("⚡ 功率器件参数提取 - 后端测试")
    print("="*70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试文件数: {len(PDF_FILES)}")
    
    # 初始化组件
    print("\n🔧 正在初始化组件...")
    db_manager = DatabaseManager()
    parser = PDFParser()
    ai_processor = AIProcessor()
    
    # 检查AI配置
    print(f"   AI提供商: {ai_processor.provider}")
    print(f"   AI模型: {ai_processor.model}")
    
    # 初始化参数库
    params_info = init_params_if_needed(db_manager)
    print(f"   参数库: {len(params_info)} 个参数")
    
    # 测试每个PDF
    all_results = []
    project_root = Path(__file__).parent
    
    for pdf_file in PDF_FILES:
        pdf_path = project_root / pdf_file
        
        if not pdf_path.exists():
            print(f"\n⚠️  文件不存在: {pdf_file}")
            continue
        
        result = test_single_pdf(str(pdf_path), parser, ai_processor, params_info)
        all_results.append(result)
        
        # 打印提取的参数
        if result['success'] and result['extracted_params']:
            print_extracted_params(result['extracted_params'])
    
    # 汇总报告
    print("\n" + "="*70)
    print("📊 测试汇总报告")
    print("="*70)
    
    success_count = sum(1 for r in all_results if r['success'])
    total_pdf_time = sum(r['pdf_parse_time'] for r in all_results)
    total_ai_time = sum(r['ai_extract_time'] for r in all_results)
    total_time = sum(r['total_time'] for r in all_results)
    
    print(f"\n📈 整体统计:")
    print(f"   成功/总数: {success_count}/{len(all_results)}")
    print(f"   PDF解析总耗时: {total_pdf_time:.2f}s")
    print(f"   AI提取总耗时: {total_ai_time:.2f}s")
    print(f"   总耗时: {total_time:.2f}s")
    print(f"   平均每份PDF: {total_time/len(all_results):.2f}s")
    
    print(f"\n📋 各文件详情:")
    print(f"{'文件名':<35} {'PDF解析':<10} {'AI提取':<10} {'总时间':<10} {'参数数':<8} {'状态'}")
    print("-" * 90)
    
    for r in all_results:
        name = r['pdf_name'][:34] if len(r['pdf_name']) > 34 else r['pdf_name']
        status = "✅" if r['success'] else "❌"
        print(f"{name:<35} {r['pdf_parse_time']:<10.2f} {r['ai_extract_time']:<10.2f} {r['total_time']:<10.2f} {r['extracted_params_count']:<8} {status}")
    
    # 保存详细结果到JSON
    output_path = project_root / "test_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 详细结果已保存到: {output_path}")
    
    # 打印每个PDF的关键参数对比
    print("\n" + "="*70)
    print("📊 关键参数提取对比")
    print("="*70)
    
    key_params = ['OPN', '厂家', 'VDS', 'Ron 10V_type', 'Ron 10V_max', 'ID Tc=25℃', 'Qg', 'Ciss', 'Coss']
    
    print(f"\n{'文件名':<30}", end="")
    for param in key_params[:6]:  # 只显示前6个关键参数
        print(f"{param:<15}", end="")
    print()
    print("-" * 120)
    
    for r in all_results:
        if not r['success']:
            continue
        
        name = r['pdf_name'][:29] if len(r['pdf_name']) > 29 else r['pdf_name']
        print(f"{name:<30}", end="")
        
        # 查找关键参数的值
        param_dict = {p['name']: p['value'] for p in r['extracted_params']}
        
        for param in key_params[:6]:
            if param == 'OPN':
                value = r['opn'][:14] if r['opn'] else '-'
            elif param == '厂家':
                value = r['manufacturer'][:14] if r['manufacturer'] else '-'
            else:
                value = param_dict.get(param, '-')
                if len(value) > 14:
                    value = value[:14]
            print(f"{value:<15}", end="")
        print()
    
    print("\n✅ 测试完成!")
    return all_results

if __name__ == "__main__":
    main()

