# -*- coding: utf-8 -*-
"""
完整性和准确率评估脚本
1. 完整性：PDF中存在的参数，程序是否都提取到了
2. 准确率：提取的值是否与PDF原值一致
"""

import json
import re
import pdfplumber
from pathlib import Path
from typing import Dict, List, Tuple, Set

def clean_text(text: str) -> str:
    """清理文本"""
    if not text:
        return ""
    return re.sub(r'\s+', '', str(text)).lower()

def extract_number(val: str) -> str:
    """提取数值"""
    if not val:
        return ""
    match = re.search(r'[-+]?[\d.]+', str(val))
    return match.group(0) if match else ""

def extract_pdf_params(pdf_path: str) -> Dict[str, Dict]:
    """
    从PDF中提取所有参数及其值
    返回: {符号: {param_name, min, typ, max, unit, condition}}
    """
    params = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # 找表头
                    header_idx = -1
                    col_map = {}
                    
                    for idx, row in enumerate(table):
                        row_lower = [str(c).lower() if c else '' for c in row]
                        row_text = ' '.join(row_lower)
                        
                        if any(kw in row_text for kw in ['parameter', 'symbol', 'min', 'max', 'typ']):
                            header_idx = idx
                            for col_idx, cell in enumerate(row_lower):
                                cell = cell.replace('\n', ' ').strip()
                                if 'symbol' in cell:
                                    col_map['symbol'] = col_idx
                                elif 'parameter' in cell:
                                    col_map['param'] = col_idx
                                elif cell in ['min', 'min.']:
                                    col_map['min'] = col_idx
                                elif cell in ['typ', 'typ.']:
                                    col_map['typ'] = col_idx
                                elif cell in ['max', 'max.']:
                                    col_map['max'] = col_idx
                                elif 'unit' in cell:
                                    col_map['unit'] = col_idx
                                elif 'condition' in cell or 'test' in cell:
                                    col_map['condition'] = col_idx
                                elif 'value' in cell:
                                    col_map['value'] = col_idx
                            break
                    
                    if header_idx < 0:
                        continue
                    
                    # 解析数据行
                    for row in table[header_idx + 1:]:
                        if not row or all(not c for c in row):
                            continue
                        
                        def get_val(key):
                            if key not in col_map:
                                return None
                            idx = col_map[key]
                            if idx < len(row) and row[idx]:
                                v = str(row[idx]).strip()
                                if v not in ['---', '-', 'None', '']:
                                    # 处理换行
                                    v = v.split('\n')[0]
                                    return v
                            return None
                        
                        symbol = get_val('symbol')
                        if symbol:
                            # 清理符号中的换行
                            symbol = re.sub(r'\s+', '', symbol)
                        
                        if not symbol:
                            continue
                        
                        # 获取值
                        val = get_val('value')
                        min_v = get_val('min') or val
                        typ_v = get_val('typ')
                        max_v = get_val('max') or val
                        unit = get_val('unit')
                        condition = get_val('condition')
                        
                        params[symbol] = {
                            'param_name': get_val('param') or '',
                            'min': min_v,
                            'typ': typ_v,
                            'max': max_v,
                            'unit': unit,
                            'condition': condition
                        }
    except Exception as e:
        print(f"  ⚠️ PDF解析错误: {e}")
    
    return params

def values_match(extracted: str, pdf_val: str) -> bool:
    """判断两个值是否匹配"""
    if not extracted or not pdf_val:
        return False
    
    # 提取数值对比
    ext_num = extract_number(extracted)
    pdf_num = extract_number(pdf_val)
    
    if ext_num and pdf_num:
        return ext_num == pdf_num
    
    # 文本对比（忽略空格和大小写）
    return clean_text(extracted) == clean_text(pdf_val)

# 标准参数名到PDF符号的映射
PARAM_TO_SYMBOL = {
    'VDS': ['BVDSS', 'VDSS', 'VDS'],
    'Ron 10V_type': ['RDS(on)'],
    'Ron 10V_max': ['RDS(on)'],
    'Vth type': ['VGS(th)'],
    'Vth min': ['VGS(th)'],
    'Vth max': ['VGS(th)'],
    'ID Tc=25℃': ['ID'],
    'ID puls Tc=25℃': ['IDM'],
    'Vgs min': ['VGS', 'VGSS'],
    'Vgs max': ['VGS', 'VGSS'],
    'Ciss': ['Ciss'],
    'Coss': ['Coss'],
    'Crss': ['Crss'],
    'Qg': ['Qg'],
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
    'Is': ['IS'],
    'Ism': ['ISM'],
    '反二极管压降Vsd': ['VSD'],
    'Irrm': ['Irrm'],
    'gfs': ['gfs'],
    'Rg': ['Rg'],
    'Vplateau': ['Vplateau'],
    'RthJC max': ['RθJC'],
    'RthJA max': ['RθJA'],
    'EAS L=0.1mH': ['EAS'],
    'PD Tc=25℃': ['PD'],
}

def main():
    print("="*100)
    print("📊 参数提取 完整性 & 准确率 评估报告")
    print("="*100)
    
    # 加载AI提取结果
    with open('test_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    all_stats = []
    
    for result in results:
        pdf_name = result['pdf_name']
        
        print(f"\n{'='*100}")
        print(f"📄 {pdf_name}")
        print(f"{'='*100}")
        
        # 1. 从PDF提取原始参数
        print(f"\n  📖 步骤1: 从PDF提取原始参数表...")
        pdf_params = extract_pdf_params(pdf_name)
        print(f"     PDF中找到 {len(pdf_params)} 个参数定义")
        
        # 2. AI提取的参数
        ai_params = {p['name']: p['value'] for p in result['extracted_params']}
        print(f"     AI提取了 {len(ai_params)} 个参数")
        
        # 3. 统计
        # 排除元信息类参数（这些不在PDF表格中）
        meta_params = {'PDF文件名', '厂家', 'OPN', '厂家封装名', '技术', '封装', 
                      '特殊功能', '极性', 'Product Status', '认证', '安装', 'ESD',
                      '预算价格€/1k', '工作温度min', '工作温度max'}
        
        # 可比较的AI参数（排除元信息）
        comparable_ai_params = {k: v for k, v in ai_params.items() if k not in meta_params}
        
        # 统计变量
        stats = {
            'pdf_name': pdf_name,
            'pdf_total': len(pdf_params),
            'ai_total': len(ai_params),
            'ai_comparable': len(comparable_ai_params),
            'matched': 0,        # AI提取且值正确
            'mismatched': 0,     # AI提取但值错误
            'missed': 0,         # PDF有但AI没提取
            'extra': 0,          # AI提取但PDF没有
        }
        
        matched_list = []
        mismatched_list = []
        missed_list = []
        
        # 4. 逐个检查PDF参数是否被正确提取
        print(f"\n  📋 步骤2: 逐个参数对比...")
        print(f"\n  {'PDF符号':<15} {'PDF值':<18} {'AI参数名':<20} {'AI提取值':<18} {'状态'}")
        print(f"  {'-'*95}")
        
        checked_ai_params = set()
        
        for symbol, pdf_data in pdf_params.items():
            # 确定PDF中的值（优先typ，其次max）
            pdf_value = pdf_data.get('typ') or pdf_data.get('max') or pdf_data.get('min')
            if not pdf_value:
                continue
            
            unit = pdf_data.get('unit', '')
            if unit:
                pdf_value_with_unit = f"{pdf_value} {unit}"
            else:
                pdf_value_with_unit = pdf_value
            
            # 查找对应的AI参数
            found = False
            for ai_name, ai_value in comparable_ai_params.items():
                # 检查是否匹配
                possible_symbols = PARAM_TO_SYMBOL.get(ai_name, [ai_name])
                
                symbol_match = False
                for ps in possible_symbols:
                    if ps.lower() == symbol.lower() or ps.lower() in symbol.lower() or symbol.lower() in ps.lower():
                        symbol_match = True
                        break
                
                if symbol_match:
                    checked_ai_params.add(ai_name)
                    
                    # 检查值是否匹配
                    if values_match(ai_value, pdf_value):
                        stats['matched'] += 1
                        matched_list.append((symbol, pdf_value_with_unit, ai_name, ai_value))
                        status = "✅ 正确"
                    else:
                        stats['mismatched'] += 1
                        mismatched_list.append((symbol, pdf_value_with_unit, ai_name, ai_value))
                        status = "❌ 值不匹配"
                    
                    sym_disp = symbol[:14] if len(symbol) > 14 else symbol
                    pdf_disp = pdf_value_with_unit[:17] if len(pdf_value_with_unit) > 17 else pdf_value_with_unit
                    ai_name_disp = ai_name[:19] if len(ai_name) > 19 else ai_name
                    ai_val_disp = ai_value[:17] if len(ai_value) > 17 else ai_value
                    
                    print(f"  {sym_disp:<15} {pdf_disp:<18} {ai_name_disp:<20} {ai_val_disp:<18} {status}")
                    found = True
                    break
            
            if not found:
                stats['missed'] += 1
                missed_list.append((symbol, pdf_value_with_unit))
        
        # 5. 计算完整性和准确率
        total_in_pdf = stats['matched'] + stats['mismatched'] + stats['missed']
        
        if total_in_pdf > 0:
            completeness = (stats['matched'] + stats['mismatched']) / total_in_pdf * 100
        else:
            completeness = 0
        
        if stats['matched'] + stats['mismatched'] > 0:
            accuracy = stats['matched'] / (stats['matched'] + stats['mismatched']) * 100
        else:
            accuracy = 0
        
        stats['completeness'] = completeness
        stats['accuracy'] = accuracy
        all_stats.append(stats)
        
        # 6. 打印统计
        print(f"\n  📊 统计结果:")
        print(f"     PDF中可验证参数: {total_in_pdf}")
        print(f"     ✅ 提取且正确: {stats['matched']}")
        print(f"     ❌ 提取但值错: {stats['mismatched']}")
        print(f"     ⚠️ 未提取: {stats['missed']}")
        print(f"\n     📈 完整性: {stats['matched'] + stats['mismatched']}/{total_in_pdf} = {completeness:.1f}%")
        print(f"     🎯 准确率: {stats['matched']}/{stats['matched'] + stats['mismatched']} = {accuracy:.1f}%")
        
        if mismatched_list:
            print(f"\n  ❌ 值不匹配的参数:")
            for sym, pdf_v, ai_n, ai_v in mismatched_list[:10]:
                print(f"     - {sym}: PDF='{pdf_v}', AI='{ai_v}'")
        
        if missed_list and len(missed_list) <= 20:
            print(f"\n  ⚠️ PDF有但未提取的参数:")
            for sym, val in missed_list[:10]:
                print(f"     - {sym}: {val}")
    
    # 总体报告
    print("\n" + "="*100)
    print("📈 总体评估报告")
    print("="*100)
    
    total_matched = sum(s['matched'] for s in all_stats)
    total_mismatched = sum(s['mismatched'] for s in all_stats)
    total_missed = sum(s['missed'] for s in all_stats)
    total_in_pdf = total_matched + total_mismatched + total_missed
    
    overall_completeness = (total_matched + total_mismatched) / total_in_pdf * 100 if total_in_pdf > 0 else 0
    overall_accuracy = total_matched / (total_matched + total_mismatched) * 100 if (total_matched + total_mismatched) > 0 else 0
    
    print(f"\n  📋 各文件统计:")
    print(f"  {'文件名':<35} {'完整性':<12} {'准确率':<12} {'正确':<8} {'错误':<8} {'遗漏'}")
    print(f"  {'-'*90}")
    
    for s in all_stats:
        name = s['pdf_name'][:34] if len(s['pdf_name']) > 34 else s['pdf_name']
        print(f"  {name:<35} {s['completeness']:.1f}%{'':<6} {s['accuracy']:.1f}%{'':<6} {s['matched']:<8} {s['mismatched']:<8} {s['missed']}")
    
    print(f"\n  📊 整体汇总:")
    print(f"     PDF可验证参数总数: {total_in_pdf}")
    print(f"     ✅ 提取且正确: {total_matched}")
    print(f"     ❌ 提取但值错: {total_mismatched}")
    print(f"     ⚠️ 未提取: {total_missed}")
    
    print(f"\n  🎯 整体完整性: {total_matched + total_mismatched}/{total_in_pdf} = {overall_completeness:.1f}%")
    print(f"  🎯 整体准确率: {total_matched}/{total_matched + total_mismatched} = {overall_accuracy:.1f}%")
    
    print("\n" + "="*100)
    print("✅ 评估完成")
    print("="*100)

if __name__ == "__main__":
    main()

