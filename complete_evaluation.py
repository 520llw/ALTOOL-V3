#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""完整版参数提取评估 - 验证所有参数"""

import json
import re
from backend.pdf_parser import PDFParser

def normalize_value(val):
    """标准化值用于比较"""
    if val is None:
        return None
    val = str(val).strip()
    val = re.sub(r'\s+', ' ', val)
    # 提取数值
    match = re.search(r'[-+]?\d*\.?\d+', val)
    if match:
        return match.group()
    return val

def extract_all_pdf_params(pdf_path: str) -> dict:
    """从PDF表格中提取所有参数"""
    parser = PDFParser()
    content = parser.parse_pdf(pdf_path)
    
    params = {}
    
    for table in content.tables:
        if len(table) < 2:
            continue
        
        # 分析表头
        header = table[0]
        header_lower = [str(h).lower().strip() for h in header]
        
        # 找各列索引
        symbol_idx = None
        min_idx = None
        typ_idx = None
        max_idx = None
        unit_idx = None
        
        for i, h in enumerate(header_lower):
            if 'symbol' in h or '符号' in h or 'parameter' in h or h == 'symbol':
                symbol_idx = i
            elif h in ['min', 'min.', 'minimum']:
                min_idx = i
            elif h in ['typ', 'typ.', 'typical']:
                typ_idx = i
            elif h in ['max', 'max.', 'maximum']:
                max_idx = i
            elif 'unit' in h or '单位' in h:
                unit_idx = i
        
        if symbol_idx is None:
            # 尝试用第一列作为符号
            symbol_idx = 0
            for i, h in enumerate(header_lower):
                if h in ['min', 'min.']:
                    min_idx = i
                elif h in ['typ', 'typ.']:
                    typ_idx = i
                elif h in ['max', 'max.']:
                    max_idx = i
                elif h in ['unit', 'units', '单位']:
                    unit_idx = i
        
        # 提取数据行
        for row in table[1:]:
            if len(row) <= symbol_idx:
                continue
            
            symbol = str(row[symbol_idx]).strip()
            # 清理多行符号
            symbol = symbol.replace('\n', '').replace(' ', '')
            
            if not symbol or symbol in ['Symbol', 'Parameter', '参数', '符号', '-', '–']:
                continue
            
            # 提取min/typ/max值
            val_min = row[min_idx] if min_idx and len(row) > min_idx else None
            val_typ = row[typ_idx] if typ_idx and len(row) > typ_idx else None
            val_max = row[max_idx] if max_idx and len(row) > max_idx else None
            unit = row[unit_idx] if unit_idx and len(row) > unit_idx else ''
            
            # 存储
            if symbol:
                params[symbol] = {
                    'min': str(val_min).strip() if val_min and str(val_min).strip() not in ['-', '–', '', 'None'] else None,
                    'typ': str(val_typ).strip() if val_typ and str(val_typ).strip() not in ['-', '–', '', 'None'] else None,
                    'max': str(val_max).strip() if val_max and str(val_max).strip() not in ['-', '–', '', 'None'] else None,
                    'unit': str(unit).strip() if unit else ''
                }
    
    return params


# 完整的参数映射（AI参数名 -> PDF符号列表）
COMPLETE_MAPPING = {
    # 电压参数
    'VDS': (['BVDSS', 'V(BR)DSS', 'VDSS', 'VDS'], 'typ', 'max'),
    'Vgs min': (['VGS'], 'min', None),
    'Vgs max': (['VGS'], None, 'max'),
    
    # 导通电阻
    'Ron 10V_type': (['RDS(on)', 'Rdson', 'RDS(ON)'], 'typ', None),
    'Ron 10V_max': (['RDS(on)', 'Rdson', 'RDS(ON)'], None, 'max'),
    'Ron 6V_type': (['RDS(on)', 'Rdson'], 'typ', None),  # 需要条件判断
    'Ron 6V_max': (['RDS(on)', 'Rdson'], None, 'max'),
    
    # 阈值电压
    'Vth type': (['VGS(th)', 'Vth', 'VGS(TH)'], 'typ', None),
    'Vth min': (['VGS(th)', 'Vth', 'VGS(TH)'], 'min', None),
    'Vth max': (['VGS(th)', 'Vth', 'VGS(TH)'], None, 'max'),
    
    # 电容
    'Ciss': (['Ciss', 'CISS'], 'typ', None),
    'Coss': (['Coss', 'COSS'], 'typ', None),
    'Crss': (['Crss', 'CRSS'], 'typ', None),
    
    # 电荷
    'Qg': (['Qg', 'QG'], 'typ', None),
    'Qg_10V': (['Qg', 'QG'], 'typ', None),
    'Qgs': (['Qgs', 'QGS'], 'typ', None),
    'Qgd': (['Qgd', 'QGD'], 'typ', None),
    'Qoss': (['Qoss', 'QOSS'], 'typ', None),
    'Qrr': (['Qrr', 'QRR'], 'typ', None),
    
    # 开关时间
    'td-on': (['td(on)', 'tdon', 'TD(ON)'], 'typ', None),
    'tr': (['tr', 'TR'], 'typ', None),
    'td-off': (['td(off)', 'tdoff', 'TD(OFF)'], 'typ', None),
    'tf': (['tf', 'TF'], 'typ', None),
    'trr': (['trr', 'TRR'], 'typ', None),
    
    # 电流
    'ID Tc=25℃': (['ID', 'Id'], 'typ', 'max'),
    'ID Tc=100℃': (['ID', 'Id'], 'typ', 'max'),
    'ID TA=25℃': (['ID', 'Id'], 'typ', 'max'),
    'ID puls Tc=25℃': (['IDM', 'IdM', 'Idm'], 'typ', 'max'),
    'Is': (['IS', 'Is'], 'typ', 'max'),
    'Ism': (['ISM', 'Ism'], 'typ', 'max'),
    'Idss': (['IDSS', 'Idss'], None, 'max'),
    'Igss': (['IGSS', 'IGSSF', 'Igss'], None, 'max'),
    'Irrm': (['Irrm', 'IRRM'], 'typ', None),
    
    # 二极管
    '反二极管压降Vsd': (['VSD', 'Vsd', 'VF'], 'typ', 'max'),
    
    # 其他
    'gfs': (['gfs', 'GFS', 'gm'], 'typ', None),
    'Rg': (['Rg', 'RG'], 'typ', None),
    'Vplateau': (['Vplateau', 'VPLATEAU', 'Vp'], 'typ', None),
    'RthJC max': (['RθJC', 'RthJC', 'RTHJC', 'Rth(JC)'], None, 'max'),
    'RthJA max': (['RθJA', 'RthJA', 'RTHJA', 'Rth(JA)'], None, 'max'),
    'EAS L=0.1mH': (['EAS', 'Eas'], 'typ', 'max'),
    'PD Tc=25℃': (['PD', 'Pd', 'PTOT'], 'typ', 'max'),
}


def evaluate_complete():
    """完整验证所有参数"""
    
    with open('test_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    pdf_dir = './PDF/功率器件'
    
    print('='*100)
    print('📊 完整参数提取评估报告')
    print('='*100)
    
    total_stats = {
        'total_ai_params': 0,
        'meta_params': 0,
        'spec_params': 0,
        'verifiable': 0,
        'correct': 0,
        'wrong': 0,
        'not_in_pdf': 0
    }
    
    # 元信息参数（不需要验证）
    META_PARAMS = ['PDF文件名', '厂家', 'OPN', '厂家封装名', '技术', '封装', 
                  '特殊功能', '极性', 'Product Status', '认证', '安装', 'ESD',
                  '预算价格€/1k', '工作温度min', '工作温度max']
    
    for result in results:
        pdf_name = result['pdf_name']
        pdf_path = f'{pdf_dir}/{pdf_name}'
        
        print(f'\n{"="*100}')
        print(f'📄 {pdf_name}')
        print('='*100)
        
        # 提取PDF参数
        try:
            pdf_params = extract_all_pdf_params(pdf_path)
        except Exception as e:
            print(f'  ⚠️ PDF解析失败: {e}')
            continue
        
        # AI提取的参数
        ai_params = {p['name']: p['value'] for p in result['extracted_params']}
        
        total_ai = len(ai_params)
        meta_count = sum(1 for name in ai_params if name in META_PARAMS)
        spec_count = total_ai - meta_count
        
        print(f'\n  AI提取: {total_ai}个参数 (元信息: {meta_count}, 规格参数: {spec_count})')
        print(f'  PDF中找到: {len(pdf_params)}个符号')
        
        stats = {'correct': 0, 'wrong': 0, 'verifiable': 0, 'not_in_pdf': 0}
        
        print(f'\n  {"AI参数":<25} {"AI值":<20} {"PDF符号":<15} {"PDF值":<20} {"状态":<10}')
        print('  ' + '-'*90)
        
        for ai_name, ai_value in ai_params.items():
            if ai_name in META_PARAMS:
                continue  # 跳过元信息
            
            # 查找对应的PDF参数
            found = False
            pdf_symbol = None
            pdf_value = None
            
            if ai_name in COMPLETE_MAPPING:
                symbols, typ_field, max_field = COMPLETE_MAPPING[ai_name]
                
                for sym in symbols:
                    # 直接匹配
                    if sym in pdf_params:
                        pdf_symbol = sym
                        p = pdf_params[sym]
                        if typ_field == 'typ' and p.get('typ'):
                            pdf_value = p['typ']
                        elif typ_field == 'min' and p.get('min'):
                            pdf_value = p['min']
                        elif max_field == 'max' and p.get('max'):
                            pdf_value = p['max']
                        elif p.get('typ'):
                            pdf_value = p['typ']
                        elif p.get('max'):
                            pdf_value = p['max']
                        found = True
                        break
                    
                    # 模糊匹配
                    for ps in pdf_params:
                        if sym.lower() in ps.lower() or ps.lower() in sym.lower():
                            pdf_symbol = ps
                            p = pdf_params[ps]
                            if typ_field == 'typ' and p.get('typ'):
                                pdf_value = p['typ']
                            elif typ_field == 'min' and p.get('min'):
                                pdf_value = p['min']
                            elif max_field == 'max' and p.get('max'):
                                pdf_value = p['max']
                            elif p.get('typ'):
                                pdf_value = p['typ']
                            elif p.get('max'):
                                pdf_value = p['max']
                            found = True
                            break
                    if found:
                        break
            
            if found and pdf_value:
                stats['verifiable'] += 1
                ai_num = normalize_value(ai_value)
                pdf_num = normalize_value(pdf_value)
                
                if ai_num == pdf_num:
                    status = '✅ 正确'
                    stats['correct'] += 1
                else:
                    status = '❌ 错误'
                    stats['wrong'] += 1
                
                print(f'  {ai_name:<25} {str(ai_value)[:18]:<20} {pdf_symbol:<15} {str(pdf_value)[:18]:<20} {status}')
            else:
                stats['not_in_pdf'] += 1
        
        print(f'\n  📊 规格参数统计:')
        print(f'     规格参数总数: {spec_count}')
        print(f'     可验证: {stats["verifiable"]} (在PDF表格中找到对应)')
        print(f'     ✅ 正确: {stats["correct"]}')
        print(f'     ❌ 错误: {stats["wrong"]}')
        print(f'     ⚠️ 无法验证: {stats["not_in_pdf"]} (PDF中无对应符号)')
        
        if stats['verifiable'] > 0:
            acc = stats['correct'] / stats['verifiable'] * 100
            print(f'\n     🎯 可验证参数准确率: {stats["correct"]}/{stats["verifiable"]} = {acc:.1f}%')
        
        # 累计
        total_stats['total_ai_params'] += total_ai
        total_stats['meta_params'] += meta_count
        total_stats['spec_params'] += spec_count
        total_stats['verifiable'] += stats['verifiable']
        total_stats['correct'] += stats['correct']
        total_stats['wrong'] += stats['wrong']
        total_stats['not_in_pdf'] += stats['not_in_pdf']
    
    # 总体统计
    print(f'\n{"="*100}')
    print('📈 总体统计')
    print('='*100)
    print(f'''
  AI提取参数总数: {total_stats['total_ai_params']}
  ├── 元信息参数: {total_stats['meta_params']} (厂家、OPN、封装等，不需验证)
  └── 规格参数: {total_stats['spec_params']}
      ├── 可验证: {total_stats['verifiable']} (在PDF表格中找到对应)
      │   ├── ✅ 正确: {total_stats['correct']}
      │   └── ❌ 错误: {total_stats['wrong']}
      └── ⚠️ 无法验证: {total_stats['not_in_pdf']} (PDF中无对应符号)
''')
    
    if total_stats['verifiable'] > 0:
        acc = total_stats['correct'] / total_stats['verifiable'] * 100
        print(f'  ╔══════════════════════════════════════════╗')
        print(f'  ║  🎯 规格参数准确率: {total_stats["correct"]}/{total_stats["verifiable"]} = {acc:.1f}%     ║')
        print(f'  ╚══════════════════════════════════════════╝')


if __name__ == '__main__':
    evaluate_complete()

