# -*- coding: utf-8 -*-
"""
完整准确度验证脚本
从PDF原始表格提取所有参数，与AI提取结果逐一对比
"""

import json
import re
import pdfplumber
from pathlib import Path
from typing import Dict, List, Tuple

def extract_all_params_from_pdf(pdf_path: str) -> Dict[str, Dict]:
    """
    从PDF中提取所有参数的真实值
    
    Returns:
        {参数名: {value: 值, typ: typ值, max: max值, min: min值, condition: 测试条件}}
    """
    truth = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # 提取所有页面的表格
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # 分析表格结构
                    # 找到表头行
                    header_row = None
                    header_idx = 0
                    
                    for idx, row in enumerate(table):
                        row_text = ' '.join([str(c) if c else '' for c in row]).lower()
                        if any(kw in row_text for kw in ['parameter', 'symbol', 'min', 'max', 'typ', 'unit']):
                            header_row = row
                            header_idx = idx
                            break
                    
                    if not header_row:
                        continue
                    
                    # 解析表头，找到各列索引
                    col_indices = {
                        'param': -1,
                        'symbol': -1,
                        'min': -1,
                        'typ': -1,
                        'max': -1,
                        'unit': -1,
                        'condition': -1
                    }
                    
                    for col_idx, cell in enumerate(header_row):
                        if not cell:
                            continue
                        cell_lower = str(cell).lower().strip()
                        
                        if 'parameter' in cell_lower:
                            col_indices['param'] = col_idx
                        elif 'symbol' in cell_lower:
                            col_indices['symbol'] = col_idx
                        elif cell_lower == 'min' or cell_lower == 'min.':
                            col_indices['min'] = col_idx
                        elif cell_lower == 'typ' or cell_lower == 'typ.':
                            col_indices['typ'] = col_idx
                        elif cell_lower == 'max' or cell_lower == 'max.':
                            col_indices['max'] = col_idx
                        elif 'unit' in cell_lower:
                            col_indices['unit'] = col_idx
                        elif 'condition' in cell_lower or 'test' in cell_lower:
                            col_indices['condition'] = col_idx
                    
                    # 解析数据行
                    for row in table[header_idx + 1:]:
                        if not row or len(row) < 3:
                            continue
                        
                        # 获取参数名/符号
                        symbol = ''
                        if col_indices['symbol'] >= 0 and col_indices['symbol'] < len(row):
                            symbol = str(row[col_indices['symbol']] or '').strip()
                        
                        param_name = ''
                        if col_indices['param'] >= 0 and col_indices['param'] < len(row):
                            param_name = str(row[col_indices['param']] or '').strip()
                        
                        if not symbol and not param_name:
                            continue
                        
                        # 使用symbol作为key，如果没有则用param_name
                        key = symbol if symbol else param_name
                        if not key or key == '---' or key == '-':
                            continue
                        
                        # 获取各列值
                        def get_cell(col_name):
                            idx = col_indices[col_name]
                            if idx >= 0 and idx < len(row):
                                val = row[idx]
                                if val and str(val).strip() not in ['---', '-', '']:
                                    return str(val).strip()
                            return None
                        
                        min_val = get_cell('min')
                        typ_val = get_cell('typ')
                        max_val = get_cell('max')
                        unit = get_cell('unit')
                        condition = get_cell('condition')
                        
                        # 存储结果
                        if key not in truth:
                            truth[key] = {
                                'param_name': param_name,
                                'min': min_val,
                                'typ': typ_val,
                                'max': max_val,
                                'unit': unit,
                                'condition': condition
                            }
                        
            # 提取第一页的基本信息
            first_page_text = pdf.pages[0].extract_text() if pdf.pages else ""
            
            # 提取VDS
            vds_match = re.search(r'VDSS?\s+(\d+)\s*V', first_page_text)
            if vds_match:
                truth['VDSS_header'] = {'typ': vds_match.group(1), 'unit': 'V'}
            
            # 提取RDS(on)
            rds_match = re.search(r'RDS\(on\)[^\d]*([\d.]+)\s*mΩ', first_page_text)
            if rds_match:
                truth['RDS(on)_header'] = {'typ': rds_match.group(1), 'unit': 'mΩ'}
            
            # 提取ID
            id_match = re.search(r'ID\s+(\d+)\s*A', first_page_text)
            if id_match:
                truth['ID_header'] = {'typ': id_match.group(1), 'unit': 'A'}
                
    except Exception as e:
        print(f"  ⚠️ 提取PDF失败: {e}")
    
    return truth


def normalize_value(val: str) -> str:
    """标准化数值用于对比"""
    if not val:
        return ""
    val = str(val).strip()
    # 移除多余空格
    val = re.sub(r'\s+', ' ', val)
    # 统一单位格式
    val = val.replace('℃', '°C').replace('Ω', 'Ohm')
    return val.lower()


def extract_number(val: str) -> str:
    """提取数值部分"""
    if not val:
        return ""
    # 提取数字（包括小数和负号）
    match = re.search(r'[-+]?[\d.]+', str(val))
    return match.group(0) if match else ""


def compare_param_values(extracted_val: str, pdf_val: str) -> Tuple[bool, str]:
    """
    对比提取值和PDF原值
    
    Returns:
        (是否匹配, 匹配类型: exact/numeric/partial/mismatch)
    """
    if not extracted_val or not pdf_val:
        return False, "missing"
    
    ext = normalize_value(extracted_val)
    pdf = normalize_value(pdf_val)
    
    # 完全匹配
    if ext == pdf:
        return True, "exact"
    
    # 数值匹配（忽略单位格式差异）
    ext_num = extract_number(extracted_val)
    pdf_num = extract_number(pdf_val)
    
    if ext_num and pdf_num and ext_num == pdf_num:
        return True, "numeric"
    
    # 部分匹配（一个包含另一个）
    if ext in pdf or pdf in ext:
        return True, "partial"
    
    return False, "mismatch"


def map_standard_name_to_symbol(standard_name: str) -> List[str]:
    """将标准参数名映射到PDF中可能的符号名"""
    mapping = {
        'VDS': ['BVDSS', 'VDSS', 'VDS', 'V(BR)DSS'],
        'Ron 10V_type': ['RDS(on)'],
        'Ron 10V_max': ['RDS(on)'],
        'Vth type': ['VGS(th)', 'Vth'],
        'Vth min': ['VGS(th)'],
        'Vth max': ['VGS(th)'],
        'ID Tc=25℃': ['ID'],
        'ID TA=25℃': ['ID'],
        'ID Tc=100℃': ['ID'],
        'ID puls Tc=25℃': ['IDM'],
        'Ciss': ['Ciss'],
        'Coss': ['Coss'],
        'Crss': ['Crss'],
        'Qg': ['Qg'],
        'Qg_10V': ['Qg'],
        'Qgs': ['Qgs'],
        'Qgd': ['Qgd'],
        'Qoss': ['Qoss'],
        'Qrr': ['Qrr'],
        'td-on': ['td(on)'],
        'tr': ['tr'],
        'td-off': ['td(off)'],
        'tf': ['tf'],
        'trr': ['trr'],
        'Idss': ['IDSS'],
        'Igss': ['IGSSF', 'IGSS'],
        'Vgs min': ['VGS'],
        'Vgs max': ['VGS'],
        'Is': ['IS'],
        'Ism': ['ISM'],
        '反二极管压降Vsd': ['VSD'],
        'Irrm': ['Irrm'],
        'gfs': ['gfs'],
        'Rg': ['Rg'],
        'Vplateau': ['Vplateau'],
        'RthJC max': ['RθJC', 'RthJC'],
        'RthJA max': ['RθJA', 'RthJA'],
        'EAS L=0.1mH': ['EAS'],
        'PD Tc=25℃': ['PD'],
    }
    
    return mapping.get(standard_name, [standard_name])


def main():
    print("="*100)
    print("📊 完整参数准确度验证报告")
    print("="*100)
    
    # 加载测试结果
    with open('test_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    pdf_files = [
        "LSGT10R011_V1.0.pdf",
        "LSGT10R013_V1.1(1).pdf",
        "LSGT10R016_V1.0.pdf",
        "LSGT20R089HCF _V1.3.pdf",
        "快捷芯KJ06N20T.pdf"
    ]
    
    overall_stats = {
        'total_params': 0,
        'verified': 0,
        'correct': 0,
        'mismatch': 0,
        'unverifiable': 0
    }
    
    for result in results:
        pdf_name = result['pdf_name']
        
        print(f"\n{'='*100}")
        print(f"📄 {pdf_name}")
        print(f"{'='*100}")
        
        # 从PDF提取真实值
        print(f"\n  📖 正在从PDF提取原始参数值...")
        pdf_truth = extract_all_params_from_pdf(pdf_name)
        print(f"     找到 {len(pdf_truth)} 个参数定义")
        
        # AI提取的参数
        extracted_params = result['extracted_params']
        print(f"     AI提取了 {len(extracted_params)} 个参数")
        
        # 逐个对比
        pdf_stats = {
            'total': len(extracted_params),
            'verified': 0,
            'correct': 0,
            'mismatch': 0,
            'unverifiable': 0
        }
        
        mismatches = []
        correct_list = []
        unverifiable_list = []
        
        print(f"\n  {'参数名':<22} {'提取值':<18} {'PDF原值':<18} {'结果':<8} {'备注'}")
        print(f"  {'-'*90}")
        
        for param in extracted_params:
            param_name = param['name']
            extracted_value = param['value']
            
            # 跳过元信息类参数
            if param_name in ['PDF文件名', '厂家', 'OPN', '厂家封装名', '技术', '封装', 
                             '特殊功能', '极性', 'Product Status', '认证', '安装', 'ESD',
                             '预算价格€/1k']:
                pdf_stats['unverifiable'] += 1
                unverifiable_list.append(param_name)
                continue
            
            # 查找对应的PDF原值
            possible_symbols = map_standard_name_to_symbol(param_name)
            pdf_value = None
            pdf_entry = None
            matched_symbol = None
            
            for symbol in possible_symbols:
                if symbol in pdf_truth:
                    pdf_entry = pdf_truth[symbol]
                    matched_symbol = symbol
                    
                    # 根据参数名判断取typ/min/max
                    if 'min' in param_name.lower():
                        pdf_value = pdf_entry.get('min')
                    elif 'max' in param_name.lower():
                        pdf_value = pdf_entry.get('max')
                    elif 'type' in param_name.lower() or 'typ' in param_name.lower():
                        pdf_value = pdf_entry.get('typ')
                    else:
                        # 默认取typ，如果没有取max
                        pdf_value = pdf_entry.get('typ') or pdf_entry.get('max')
                    
                    if pdf_value:
                        # 加上单位
                        unit = pdf_entry.get('unit', '')
                        if unit and unit not in pdf_value:
                            pdf_value = f"{pdf_value} {unit}"
                        break
            
            # 对比
            if pdf_value:
                is_match, match_type = compare_param_values(extracted_value, pdf_value)
                pdf_stats['verified'] += 1
                
                if is_match:
                    pdf_stats['correct'] += 1
                    status = "✅"
                    correct_list.append((param_name, extracted_value, pdf_value))
                else:
                    pdf_stats['mismatch'] += 1
                    status = "❌"
                    mismatches.append((param_name, extracted_value, pdf_value, matched_symbol))
                
                # 截断显示
                ext_disp = extracted_value[:17] if len(extracted_value) > 17 else extracted_value
                pdf_disp = pdf_value[:17] if len(pdf_value) > 17 else pdf_value
                
                print(f"  {param_name:<22} {ext_disp:<18} {pdf_disp:<18} {status:<8} {match_type}")
            else:
                pdf_stats['unverifiable'] += 1
                unverifiable_list.append(param_name)
        
        # PDF统计
        accuracy = pdf_stats['correct'] / pdf_stats['verified'] * 100 if pdf_stats['verified'] > 0 else 0
        
        print(f"\n  📊 统计:")
        print(f"     总参数: {pdf_stats['total']}")
        print(f"     可验证: {pdf_stats['verified']}")
        print(f"     正确: {pdf_stats['correct']} ({accuracy:.1f}%)")
        print(f"     不匹配: {pdf_stats['mismatch']}")
        print(f"     无法验证: {pdf_stats['unverifiable']}")
        
        if mismatches:
            print(f"\n  ⚠️ 不匹配项目:")
            for name, ext, pdf, sym in mismatches:
                print(f"     - {name} (PDF符号: {sym})")
                print(f"       提取: '{ext}'")
                print(f"       PDF:  '{pdf}'")
        
        # 累计统计
        overall_stats['total_params'] += pdf_stats['total']
        overall_stats['verified'] += pdf_stats['verified']
        overall_stats['correct'] += pdf_stats['correct']
        overall_stats['mismatch'] += pdf_stats['mismatch']
        overall_stats['unverifiable'] += pdf_stats['unverifiable']
    
    # 总体报告
    print("\n" + "="*100)
    print("📈 总体评估报告")
    print("="*100)
    
    overall_accuracy = overall_stats['correct'] / overall_stats['verified'] * 100 if overall_stats['verified'] > 0 else 0
    
    print(f"\n  📊 整体统计:")
    print(f"     总提取参数: {overall_stats['total_params']}")
    print(f"     可验证参数: {overall_stats['verified']}")
    print(f"     验证正确: {overall_stats['correct']}")
    print(f"     不匹配: {overall_stats['mismatch']}")
    print(f"     无法验证: {overall_stats['unverifiable']}")
    print(f"\n  🎯 验证准确率: {overall_stats['correct']}/{overall_stats['verified']} = {overall_accuracy:.1f}%")
    
    print("\n" + "="*100)
    print("✅ 完整验证完成")
    print("="*100)


if __name__ == "__main__":
    main()

