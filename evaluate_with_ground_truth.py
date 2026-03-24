#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用标准答案评估软件提取准确率
标准答案由AI人工分析PDF得到
"""

import json
import re

def extract_number(val):
    """提取数值部分"""
    if val is None:
        return None
    val = str(val).strip()
    match = re.search(r'[-+]?\d*\.?\d+', val)
    return match.group() if match else None

def compare_values(gt_val, ai_val):
    """比较两个值是否一致"""
    if gt_val is None and ai_val is None:
        return 'both_null'
    if gt_val is None:
        return 'extra'  # AI提取了但标准答案没有
    if ai_val is None:
        return 'missing'  # 标准答案有但AI没提取
    
    gt_num = extract_number(gt_val)
    ai_num = extract_number(ai_val)
    
    if gt_num and ai_num:
        # 数值比较
        try:
            if abs(float(gt_num) - float(ai_num)) < 0.01:
                return 'correct'
            # 允许小数点误差
            if gt_num == ai_num:
                return 'correct'
        except:
            pass
        return 'wrong'
    else:
        # 字符串比较
        gt_clean = re.sub(r'\s+', '', str(gt_val).lower())
        ai_clean = re.sub(r'\s+', '', str(ai_val).lower())
        if gt_clean == ai_clean or gt_clean in ai_clean or ai_clean in gt_clean:
            return 'correct'
        return 'wrong'

def main():
    # 读取标准答案
    with open('ground_truth.json', 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    # 读取软件提取结果
    with open('test_results.json', 'r', encoding='utf-8') as f:
        ai_results = json.load(f)
    
    # 参数名映射（处理命名差异）
    name_mapping = {
        'ID TA=25℃': 'ID Tc=25℃.1',
        'Vplateau': 'Vplateau ',
        'Qg(sync)': 'Qg(sync) ',
    }
    
    print('='*100)
    print('📊 软件提取准确率评估报告（基于标准答案）')
    print('='*100)
    
    total_stats = {
        'correct': 0,
        'wrong': 0,
        'missing': 0,
        'extra': 0,
        'both_null': 0,
        'total_params': 0
    }
    
    for ai_result in ai_results:
        pdf_name = ai_result['pdf_name']
        
        # 查找对应的标准答案
        gt_data = ground_truth['pdfs'].get(pdf_name)
        if not gt_data:
            print(f'\n⚠️ 未找到 {pdf_name} 的标准答案')
            continue
        
        print(f'\n{"="*100}')
        print(f'📄 {pdf_name}')
        print('='*100)
        
        # 将AI结果转为字典
        ai_params = {p['name']: p['value'] for p in ai_result['extracted_params']}
        
        # 统计
        stats = {'correct': 0, 'wrong': 0, 'missing': 0, 'extra': 0}
        details = {'correct': [], 'wrong': [], 'missing': [], 'extra': []}
        
        # 遍历标准答案的所有参数
        for param_name, gt_val in gt_data.items():
            # 处理名称映射
            ai_param_name = param_name
            for ai_name, gt_name in name_mapping.items():
                if param_name == gt_name:
                    ai_param_name = ai_name
                    break
            
            ai_val = ai_params.get(ai_param_name) or ai_params.get(param_name)
            
            result = compare_values(gt_val, ai_val)
            
            if result == 'correct':
                stats['correct'] += 1
                details['correct'].append(param_name)
            elif result == 'wrong':
                stats['wrong'] += 1
                details['wrong'].append((param_name, gt_val, ai_val))
            elif result == 'missing':
                stats['missing'] += 1
                details['missing'].append((param_name, gt_val))
            elif result == 'extra':
                stats['extra'] += 1
            # both_null 不计入
        
        # 显示统计
        total_expected = stats['correct'] + stats['wrong'] + stats['missing']
        
        print(f'\n  📊 统计结果:')
        print(f'     标准答案有效参数: {total_expected}')
        print(f'     ✅ 提取正确: {stats["correct"]}')
        print(f'     ❌ 提取错误: {stats["wrong"]}')
        print(f'     ⚠️ 漏提取: {stats["missing"]}')
        
        if total_expected > 0:
            accuracy = stats['correct'] / total_expected * 100
            completeness = (stats['correct'] + stats['wrong']) / total_expected * 100
            print(f'\n     🎯 准确率: {stats["correct"]}/{stats["correct"]+stats["wrong"]} = {stats["correct"]/(stats["correct"]+stats["wrong"])*100:.1f}%' if stats["correct"]+stats["wrong"] > 0 else '')
            print(f'     📈 完整性: {stats["correct"]+stats["wrong"]}/{total_expected} = {completeness:.1f}%')
        
        # 显示错误详情
        if details['wrong']:
            print(f'\n  ❌ 错误详情:')
            for param, gt, ai in details['wrong']:
                print(f'     • {param}: 标准={gt} vs AI={ai}')
        
        if details['missing']:
            print(f'\n  ⚠️ 漏提取:')
            for param, gt in details['missing'][:10]:  # 只显示前10个
                print(f'     • {param}: {gt}')
            if len(details['missing']) > 10:
                print(f'     ... 还有 {len(details["missing"])-10} 个')
        
        # 累计
        total_stats['correct'] += stats['correct']
        total_stats['wrong'] += stats['wrong']
        total_stats['missing'] += stats['missing']
        total_stats['total_params'] += total_expected
    
    # 总体统计
    print(f'\n\n{"="*100}')
    print('📈 总体评估结果')
    print('='*100)
    
    total_expected = total_stats['total_params']
    total_extracted = total_stats['correct'] + total_stats['wrong']
    
    print(f'''
  📊 汇总统计:
     标准答案参数总数: {total_expected}
     ✅ 提取正确: {total_stats['correct']}
     ❌ 提取错误: {total_stats['wrong']}
     ⚠️ 漏提取: {total_stats['missing']}
''')
    
    if total_extracted > 0:
        accuracy = total_stats['correct'] / total_extracted * 100
        print(f'  ╔══════════════════════════════════════════════════════╗')
        print(f'  ║  🎯 提取准确率: {total_stats["correct"]}/{total_extracted} = {accuracy:.1f}%                   ║')
        print(f'  ║  📈 提取完整性: {total_extracted}/{total_expected} = {total_extracted/total_expected*100:.1f}%                   ║')
        print(f'  ╚══════════════════════════════════════════════════════╝')
    
    # 生成详细报告
    report = {
        'summary': {
            'total_params': total_expected,
            'correct': total_stats['correct'],
            'wrong': total_stats['wrong'],
            'missing': total_stats['missing'],
            'accuracy': total_stats['correct'] / total_extracted * 100 if total_extracted > 0 else 0,
            'completeness': total_extracted / total_expected * 100 if total_expected > 0 else 0
        }
    }
    
    with open('evaluation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f'\n  📄 详细报告已保存到 evaluation_report.json')

if __name__ == '__main__':
    main()

