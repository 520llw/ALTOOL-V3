# -*- coding: utf-8 -*-
"""
精确的完整性和准确率评估
使用严格的一对一参数映射
"""

import json
import re
import pdfplumber

def extract_number(val: str) -> str:
    """提取数值"""
    if not val:
        return ""
    match = re.search(r'[-+]?[\d.]+', str(val))
    return match.group(0) if match else ""

def values_match(v1: str, v2: str) -> bool:
    """判断两个值是否匹配"""
    if not v1 or not v2:
        return False
    n1 = extract_number(v1)
    n2 = extract_number(v2)
    return n1 == n2 if n1 and n2 else False

def extract_pdf_params_strict(pdf_path: str) -> dict:
    """
    从PDF严格提取参数
    返回标准化的参数字典
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
                    headers = []
                    
                    for idx, row in enumerate(table):
                        row_text = ' '.join([str(c).lower() if c else '' for c in row])
                        if 'symbol' in row_text and ('min' in row_text or 'max' in row_text or 'typ' in row_text):
                            header_idx = idx
                            headers = [str(c).lower().strip() if c else '' for c in row]
                            break
                    
                    if header_idx < 0:
                        continue
                    
                    # 找列索引
                    col_map = {}
                    for i, h in enumerate(headers):
                        h = h.replace('\n', ' ')
                        if 'symbol' in h:
                            col_map['symbol'] = i
                        elif h in ['min', 'min.']:
                            col_map['min'] = i
                        elif h in ['typ', 'typ.']:
                            col_map['typ'] = i
                        elif h in ['max', 'max.']:
                            col_map['max'] = i
                        elif 'unit' in h:
                            col_map['unit'] = i
                    
                    if 'symbol' not in col_map:
                        continue
                    
                    # 解析数据
                    for row in table[header_idx + 1:]:
                        if not row:
                            continue
                        
                        sym_idx = col_map['symbol']
                        if sym_idx >= len(row) or not row[sym_idx]:
                            continue
                        
                        symbol = re.sub(r'\s+', '', str(row[sym_idx]))
                        if not symbol or len(symbol) < 2:
                            continue
                        
                        def get_val(key):
                            if key not in col_map:
                                return None
                            idx = col_map[key]
                            if idx < len(row) and row[idx]:
                                v = str(row[idx]).strip().split('\n')[0]
                                if v and v not in ['---', '-']:
                                    return v
                            return None
                        
                        min_v = get_val('min')
                        typ_v = get_val('typ')
                        max_v = get_val('max')
                        unit = get_val('unit')
                        
                        params[symbol] = {
                            'min': min_v,
                            'typ': typ_v,
                            'max': max_v,
                            'unit': unit
                        }
    except Exception as e:
        print(f"  Error: {e}")
    
    return params

# 严格的一对一映射：AI参数名 -> (PDF符号, 取值类型)
STRICT_MAPPING = {
    # 基本电气参数
    'VDS': ('BVDSS', 'min'),
    'Ron 10V_type': ('RDS(on)', 'typ'),
    'Ron 10V_max': ('RDS(on)', 'max'),
    'Vth type': ('VGS(th)', 'typ'),
    'Vth min': ('VGS(th)', 'min'),
    'Vth max': ('VGS(th)', 'max'),
    
    # 电容
    'Ciss': ('Ciss', 'typ'),
    'Coss': ('Coss', 'typ'),
    'Crss': ('Crss', 'typ'),
    
    # 电荷
    'Qg': ('Qg', 'typ'),
    'Qg_10V': ('Qg', 'typ'),
    'Qgs': ('Qgs', 'typ'),
    'Qgd': ('Qgd', 'typ'),
    'Qoss': ('Qoss', 'typ'),
    'Qrr': ('Qrr', 'typ'),
    
    # 开关时间
    'td-on': ('td(on)', 'typ'),
    'tr': ('tr', 'typ'),
    'td-off': ('td(off)', 'typ'),
    'tf': ('tf', 'typ'),
    'trr': ('trr', 'typ'),
    
    # 二极管
    'Is': ('IS', 'max'),
    'Ism': ('ISM', 'max'),
    '反二极管压降Vsd': ('VSD', 'max'),
    'Irrm': ('Irrm', 'typ'),
    
    # 其他
    'gfs': ('gfs', 'typ'),
    'Rg': ('Rg', 'typ'),
    'Vplateau': ('Vplateau', 'typ'),
    'Idss': ('IDSS', 'max'),
    'Igss': ('IGSSF', 'max'),
    'RthJC max': ('RθJC', 'typ'),
    'RthJA max': ('RθJA', 'typ'),
    'EAS L=0.1mH': ('EAS', 'typ'),
    'PD Tc=25℃': ('PD', 'typ'),
}

def main():
    print("="*100)
    print("📊 精确参数提取评估报告")
    print("="*100)
    
    with open('test_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    all_stats = []
    
    for result in results:
        pdf_name = result['pdf_name']
        
        print(f"\n{'='*100}")
        print(f"📄 {pdf_name}")
        print(f"{'='*100}")
        
        # 从PDF提取参数
        pdf_params = extract_pdf_params_strict(pdf_name)
        print(f"\n  PDF中找到 {len(pdf_params)} 个参数")
        
        # AI提取的参数
        ai_params = {p['name']: p['value'] for p in result['extracted_params']}
        print(f"  AI提取了 {len(ai_params)} 个参数")
        
        # 统计
        stats = {
            'pdf': pdf_name,
            'matched': 0,      # 提取正确
            'mismatched': 0,   # 提取错误
            'missed': 0,       # PDF有但AI没提取
            'pdf_total': 0,    # PDF中可验证的参数数
        }
        
        matched = []
        mismatched = []
        missed = []
        
        print(f"\n  {'AI参数':<20} {'PDF符号':<15} {'AI值':<18} {'PDF值':<18} {'状态'}")
        print(f"  {'-'*85}")
        
        # 逐个检查映射
        for ai_name, (pdf_symbol, val_type) in STRICT_MAPPING.items():
            # 检查PDF中是否有这个参数
            if pdf_symbol not in pdf_params:
                continue
            
            stats['pdf_total'] += 1
            pdf_entry = pdf_params[pdf_symbol]
            pdf_value = pdf_entry.get(val_type) or pdf_entry.get('typ') or pdf_entry.get('max')
            
            if not pdf_value:
                continue
            
            unit = pdf_entry.get('unit', '')
            pdf_full = f"{pdf_value} {unit}".strip() if unit else pdf_value
            
            # 检查AI是否提取了这个参数
            if ai_name in ai_params:
                ai_value = ai_params[ai_name]
                
                if values_match(ai_value, pdf_value):
                    stats['matched'] += 1
                    status = "✅ 正确"
                    matched.append((ai_name, pdf_symbol, ai_value, pdf_full))
                else:
                    stats['mismatched'] += 1
                    status = "❌ 错误"
                    mismatched.append((ai_name, pdf_symbol, ai_value, pdf_full))
                
                ai_disp = ai_value[:17] if len(ai_value) > 17 else ai_value
                pdf_disp = pdf_full[:17] if len(pdf_full) > 17 else pdf_full
                print(f"  {ai_name:<20} {pdf_symbol:<15} {ai_disp:<18} {pdf_disp:<18} {status}")
            else:
                stats['missed'] += 1
                missed.append((ai_name, pdf_symbol, pdf_full))
                print(f"  {ai_name:<20} {pdf_symbol:<15} {'未提取':<18} {pdf_full:<18} ⚠️ 遗漏")
        
        # 计算
        total_verifiable = stats['matched'] + stats['mismatched'] + stats['missed']
        extracted = stats['matched'] + stats['mismatched']
        
        if total_verifiable > 0:
            completeness = extracted / total_verifiable * 100
        else:
            completeness = 0
        
        if extracted > 0:
            accuracy = stats['matched'] / extracted * 100
        else:
            accuracy = 0
        
        stats['completeness'] = completeness
        stats['accuracy'] = accuracy
        all_stats.append(stats)
        
        print(f"\n  📊 统计:")
        print(f"     PDF中可验证参数: {total_verifiable}")
        print(f"     ✅ 提取正确: {stats['matched']}")
        print(f"     ❌ 提取错误: {stats['mismatched']}")
        print(f"     ⚠️ 遗漏: {stats['missed']}")
        print(f"\n     📈 完整性: {extracted}/{total_verifiable} = {completeness:.1f}%")
        print(f"     🎯 准确率: {stats['matched']}/{extracted} = {accuracy:.1f}%")
    
    # 总结
    print("\n" + "="*100)
    print("📈 总体评估")
    print("="*100)
    
    total_matched = sum(s['matched'] for s in all_stats)
    total_mismatched = sum(s['mismatched'] for s in all_stats)
    total_missed = sum(s['missed'] for s in all_stats)
    total_verifiable = total_matched + total_mismatched + total_missed
    total_extracted = total_matched + total_mismatched
    
    overall_completeness = total_extracted / total_verifiable * 100 if total_verifiable > 0 else 0
    overall_accuracy = total_matched / total_extracted * 100 if total_extracted > 0 else 0
    
    print(f"\n  {'文件名':<35} {'完整性':<12} {'准确率':<12} {'正确':<8} {'错误':<8} {'遗漏'}")
    print(f"  {'-'*85}")
    
    for s in all_stats:
        name = s['pdf'][:34] if len(s['pdf']) > 34 else s['pdf']
        print(f"  {name:<35} {s['completeness']:.1f}%{'':<6} {s['accuracy']:.1f}%{'':<6} {s['matched']:<8} {s['mismatched']:<8} {s['missed']}")
    
    print(f"\n  📊 整体汇总:")
    print(f"     可验证参数总数: {total_verifiable}")
    print(f"     ✅ 提取正确: {total_matched}")
    print(f"     ❌ 提取错误: {total_mismatched}")
    print(f"     ⚠️ 遗漏: {total_missed}")
    
    print(f"\n  ╔════════════════════════════════════════╗")
    print(f"  ║  🎯 整体完整性: {overall_completeness:>5.1f}%                  ║")
    print(f"  ║  🎯 整体准确率: {overall_accuracy:>5.1f}%                  ║")
    print(f"  ╚════════════════════════════════════════╝")
    
    print("\n" + "="*100)

if __name__ == "__main__":
    main()

