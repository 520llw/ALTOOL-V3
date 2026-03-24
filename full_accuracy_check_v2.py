# -*- coding: utf-8 -*-
"""
完整准确度验证脚本 V2
修复了表格格式差异问题
"""

import json
import re
import pdfplumber
from pathlib import Path
from typing import Dict, List, Tuple

def clean_symbol(symbol: str) -> str:
    """清理符号名中的换行符和空格"""
    if not symbol:
        return ""
    # 移除换行符和多余空格
    symbol = re.sub(r'\s+', '', str(symbol))
    # 常见替换
    symbol = symbol.replace('（', '(').replace('）', ')')
    return symbol

def extract_all_params_from_pdf(pdf_path: str) -> Dict[str, Dict]:
    """从PDF中提取所有参数的真实值"""
    truth = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # 分析表头
                    header_row = None
                    header_idx = 0
                    
                    for idx, row in enumerate(table):
                        row_text = ' '.join([str(c) if c else '' for c in row]).lower()
                        if any(kw in row_text for kw in ['parameter', 'symbol', 'min', 'max', 'typ', 'unit', 'conditions']):
                            header_row = [str(c).lower().strip() if c else '' for c in row]
                            header_idx = idx
                            break
                    
                    if not header_row:
                        continue
                    
                    # 解析表头列索引
                    col_indices = {}
                    for col_idx, cell in enumerate(header_row):
                        cell = cell.replace('\n', ' ').strip()
                        if 'parameter' in cell:
                            col_indices['param'] = col_idx
                        elif 'symbol' in cell:
                            col_indices['symbol'] = col_idx
                        elif cell in ['min', 'min.']:
                            col_indices['min'] = col_idx
                        elif cell in ['typ', 'typ.']:
                            col_indices['typ'] = col_idx
                        elif cell in ['max', 'max.']:
                            col_indices['max'] = col_idx
                        elif 'unit' in cell:
                            col_indices['unit'] = col_idx
                        elif 'condition' in cell:
                            col_indices['condition'] = col_idx
                        elif 'value' in cell:
                            col_indices['value'] = col_idx
                    
                    # 解析数据行
                    for row in table[header_idx + 1:]:
                        if not row or all(not c for c in row):
                            continue
                        
                        def get_cell(col_name, default=''):
                            if col_name not in col_indices:
                                return default
                            idx = col_indices[col_name]
                            if idx < len(row) and row[idx]:
                                val = str(row[idx]).strip()
                                if val not in ['---', '-', 'None', '']:
                                    return val
                            return default
                        
                        symbol = clean_symbol(get_cell('symbol'))
                        param_name = get_cell('param', '').replace('\n', ' ')
                        
                        if not symbol:
                            continue
                        
                        # 处理Value列（某些表格只有Value，没有Min/Typ/Max）
                        value = get_cell('value')
                        min_val = get_cell('min') or (value if 'value' in col_indices else None)
                        typ_val = get_cell('typ')
                        max_val = get_cell('max') or (value if 'value' in col_indices else None)
                        unit = get_cell('unit')
                        condition = get_cell('condition')
                        
                        # 处理多行数值（如 "159\n360\n100"）
                        if min_val and '\n' in min_val:
                            min_val = min_val.split('\n')[0]
                        if max_val and '\n' in max_val:
                            max_val = max_val.split('\n')[0]
                        if unit and '\n' in unit:
                            unit = unit.split('\n')[0]
                        
                        truth[symbol] = {
                            'param_name': param_name,
                            'min': min_val,
                            'typ': typ_val,
                            'max': max_val,
                            'unit': unit,
                            'condition': condition
                        }
                        
    except Exception as e:
        print(f"  ⚠️ 提取PDF失败: {e}")
    
    return truth


def normalize_value(val: str) -> str:
    """标准化数值"""
    if not val:
        return ""
    val = str(val).strip().lower()
    val = re.sub(r'\s+', '', val)
    val = val.replace('℃', '°c').replace('ω', 'ohm')
    return val


def extract_number(val: str) -> str:
    """提取数值部分"""
    if not val:
        return ""
    match = re.search(r'[-+]?[\d.]+', str(val))
    return match.group(0) if match else ""


def compare_param_values(extracted_val: str, pdf_val: str) -> Tuple[bool, str]:
    """对比提取值和PDF原值"""
    if not extracted_val or not pdf_val:
        return False, "missing"
    
    ext = normalize_value(extracted_val)
    pdf = normalize_value(pdf_val)
    
    if ext == pdf:
        return True, "exact"
    
    ext_num = extract_number(extracted_val)
    pdf_num = extract_number(pdf_val)
    
    if ext_num and pdf_num and ext_num == pdf_num:
        return True, "numeric"
    
    if ext in pdf or pdf in ext:
        return True, "partial"
    
    return False, "mismatch"


# 扩展的参数映射
PARAM_MAPPING = {
    'VDS': ['BVDSS', 'VDSS', 'VDS', 'V(BR)DSS'],
    'Ron 10V_type': ['RDS(on)'],
    'Ron 10V_max': ['RDS(on)'],
    'Ron 4.5V_type': ['RDS(on)'],
    'Ron 4.5V_max': ['RDS(on)'],
    'Vth type': ['VGS(th)', 'Vth'],
    'Vth min': ['VGS(th)'],
    'Vth max': ['VGS(th)'],
    'ID Tc=25℃': ['ID'],
    'ID TA=25℃': ['ID'],
    'ID Tc=100℃': ['ID'],
    'ID puls Tc=25℃': ['IDM'],
    'Vgs min': ['VGS', 'VGSS'],
    'Vgs max': ['VGS', 'VGSS'],
    'Ciss': ['Ciss', 'CISS'],
    'Coss': ['Coss', 'COSS'],
    'Crss': ['Crss', 'CRSS'],
    'Qg': ['Qg', 'QG'],
    'Qg_10V': ['Qg', 'QG'],
    'Qgs': ['Qgs', 'QGS'],
    'Qgd': ['Qgd', 'QGD'],
    'Qoss': ['Qoss', 'QOSS'],
    'Qrr': ['Qrr', 'QRR'],
    'td-on': ['td(on)', 'tdon', 'td-on'],
    'tr': ['tr', 'tR'],
    'td-off': ['td(off)', 'tdoff', 'td-off'],
    'tf': ['tf', 'tF'],
    'trr': ['trr', 'tRR'],
    'Idss': ['IDSS'],
    'Igss': ['IGSSF', 'IGSS', 'IGSSR'],
    'Is': ['IS'],
    'Ism': ['ISM'],
    '反二极管压降Vsd': ['VSD', 'Vsd'],
    'Irrm': ['Irrm', 'IRRM'],
    'gfs': ['gfs', 'GFS'],
    'Rg': ['Rg', 'RG'],
    'Vplateau': ['Vplateau', 'VGP'],
    'RthJC max': ['RθJC', 'RthJC', 'RTHJC'],
    'RthJA max': ['RθJA', 'RthJA', 'RTHJA'],
    'EAS L=0.1mH': ['EAS'],
    'PD Tc=25℃': ['PD', 'Ptot'],
    'Qsw': ['Qsw', 'QSW'],
    'Qg（th）': ['Qg(th)', 'QG(TH)'],
    'Qg(sync)': ['Qg(sync)'],
}


def main():
    print("="*100)
    print("📊 完整参数准确度验证报告 V2")
    print("="*100)
    
    with open('test_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    overall_stats = {
        'total_params': 0,
        'verified': 0,
        'correct': 0,
        'mismatch': 0,
        'unverifiable': 0
    }
    
    all_mismatches = []
    
    for result in results:
        pdf_name = result['pdf_name']
        
        print(f"\n{'='*100}")
        print(f"📄 {pdf_name}")
        print(f"{'='*100}")
        
        print(f"\n  📖 正在从PDF提取原始参数值...")
        pdf_truth = extract_all_params_from_pdf(pdf_name)
        print(f"     找到 {len(pdf_truth)} 个参数定义")
        
        # 打印找到的符号
        if pdf_truth:
            symbols = list(pdf_truth.keys())[:15]
            print(f"     符号示例: {', '.join(symbols)}")
        
        extracted_params = result['extracted_params']
        print(f"     AI提取了 {len(extracted_params)} 个参数")
        
        pdf_stats = {
            'total': len(extracted_params),
            'verified': 0,
            'correct': 0,
            'mismatch': 0,
            'unverifiable': 0
        }
        
        mismatches = []
        
        # 不可验证的元信息参数
        meta_params = ['PDF文件名', '厂家', 'OPN', '厂家封装名', '技术', '封装', 
                      '特殊功能', '极性', 'Product Status', '认证', '安装', 'ESD',
                      '预算价格€/1k', '工作温度min', '工作温度max']
        
        print(f"\n  {'参数名':<22} {'提取值':<20} {'PDF原值':<20} {'结果':<6} {'备注'}")
        print(f"  {'-'*95}")
        
        for param in extracted_params:
            param_name = param['name']
            extracted_value = param['value']
            
            if param_name in meta_params:
                pdf_stats['unverifiable'] += 1
                continue
            
            # 查找对应的PDF原值
            possible_symbols = PARAM_MAPPING.get(param_name, [param_name])
            pdf_value = None
            pdf_entry = None
            matched_symbol = None
            
            for symbol in possible_symbols:
                # 尝试精确匹配和模糊匹配
                for pdf_sym, entry in pdf_truth.items():
                    if symbol.lower() == pdf_sym.lower() or symbol.lower() in pdf_sym.lower():
                        pdf_entry = entry
                        matched_symbol = pdf_sym
                        
                        # 根据参数名判断取typ/min/max
                        if 'min' in param_name.lower():
                            pdf_value = pdf_entry.get('min')
                        elif 'max' in param_name.lower():
                            pdf_value = pdf_entry.get('max')
                        elif 'type' in param_name.lower() or 'typ' in param_name.lower():
                            pdf_value = pdf_entry.get('typ')
                        else:
                            pdf_value = pdf_entry.get('typ') or pdf_entry.get('max') or pdf_entry.get('min')
                        
                        if pdf_value:
                            unit = pdf_entry.get('unit', '')
                            if unit and unit not in pdf_value:
                                pdf_value = f"{pdf_value} {unit}"
                            break
                
                if pdf_value:
                    break
            
            if pdf_value:
                is_match, match_type = compare_param_values(extracted_value, pdf_value)
                pdf_stats['verified'] += 1
                
                if is_match:
                    pdf_stats['correct'] += 1
                    status = "✅"
                else:
                    pdf_stats['mismatch'] += 1
                    status = "❌"
                    mismatches.append((param_name, extracted_value, pdf_value, matched_symbol))
                
                ext_disp = extracted_value[:19] if len(extracted_value) > 19 else extracted_value
                pdf_disp = pdf_value[:19] if len(pdf_value) > 19 else pdf_value
                
                print(f"  {param_name:<22} {ext_disp:<20} {pdf_disp:<20} {status:<6} {match_type}")
            else:
                pdf_stats['unverifiable'] += 1
        
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
            all_mismatches.extend([(pdf_name, *m) for m in mismatches])
        
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
    
    if all_mismatches:
        print(f"\n  ⚠️ 所有不匹配项目汇总 ({len(all_mismatches)}处):")
        for pdf, name, ext, pdf_val, sym in all_mismatches:
            print(f"     [{pdf[:20]}] {name}: '{ext}' vs '{pdf_val}'")
    
    print("\n" + "="*100)
    print("✅ 完整验证完成")
    print("="*100)


if __name__ == "__main__":
    main()

