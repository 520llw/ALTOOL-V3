# -*- coding: utf-8 -*-
"""
准确度评估脚本
对比PDF原始内容与AI提取结果
"""

import json
import re
import pdfplumber
from pathlib import Path

# 加载测试结果
with open('test_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# 关键参数验证规则（从PDF中提取正确值）
def extract_ground_truth(pdf_path):
    """从PDF中提取真实值用于对比"""
    truth = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages[:3]:  # 只读前3页
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            # 提取VDS
            vds_match = re.search(r'VD[S]?S?\s+(\d+)\s*V', full_text)
            if vds_match:
                truth['VDS'] = vds_match.group(1) + ' V'
            
            # 提取RDS(on) typ
            rds_typ_match = re.search(r'RDS\(on\)[^\d]*typ[^\d]*([\d.]+)\s*mΩ', full_text, re.IGNORECASE)
            if not rds_typ_match:
                rds_typ_match = re.search(r'VGS\s*=\s*10V[^\d]*([\d.]+)\s+([\d.]+)', full_text)
                if rds_typ_match:
                    truth['Ron 10V_type'] = rds_typ_match.group(1) + ' mΩ'
            
            # 提取Ciss
            ciss_match = re.search(r'Ciss[^\d]*([\d]+)\s*pF', full_text, re.IGNORECASE)
            if ciss_match:
                truth['Ciss'] = ciss_match.group(1) + ' pF'
            
            # 提取Qg
            qg_match = re.search(r'Qg[^\d]*([\d.]+)\s*nC', full_text)
            if qg_match:
                truth['Qg'] = qg_match.group(1) + ' nC'
                
    except Exception as e:
        print(f"Error extracting truth from {pdf_path}: {e}")
    
    return truth

def normalize_value(val):
    """标准化数值用于对比"""
    if not val:
        return ""
    # 移除空格，统一小写
    val = str(val).strip().lower()
    # 移除单位前的空格
    val = re.sub(r'\s+', '', val)
    return val

def compare_values(extracted, expected):
    """对比两个值是否相等"""
    ext = normalize_value(extracted)
    exp = normalize_value(expected)
    
    if not exp:
        return None  # 无法验证
    
    return ext == exp

print("="*80)
print("📊 参数提取准确度评估报告")
print("="*80)

# 定义每个PDF的关键参数真实值（从PDF手工核对）
ground_truth = {
    "LSGT10R011_V1.0.pdf": {
        "OPN": "LSGT10R011",
        "厂家": "Lonten",
        "VDS": "100 V",
        "Ron 10V_type": "0.98 mΩ",
        "Ron 10V_max": "1.15 mΩ",
        "ID Tc=25℃": "478 A",  # Silicon limit
        "Vth type": "3.18 V",
        "Vth min": "2 V",
        "Vth max": "4 V",
        "Ciss": "14838 pF",
        "Coss": "3458 pF",
        "Crss": "73 pF",
        "Qg": "260.1 nC",
        "Qgs": "69.1 nC",
        "Qgd": "78.0 nC",
        "td-on": "160.5 ns",
        "tr": "183.1 ns",
        "td-off": "322.5 ns",
        "tf": "135.1 ns",
        "trr": "83.9 ns",
        "Qrr": "191.4 nC",
        "RthJC max": "0.26 ℃/W",
        "RthJA max": "62 ℃/W",
        "工作温度min": "-55 ℃",
        "工作温度max": "+175 ℃",
        "封装": "TOLL",
        "极性": "N-channel"
    },
    "LSGT10R013_V1.1(1).pdf": {
        "OPN": "LSGT10R013",
        "厂家": "Lonten",
        "VDS": "100 V",
        "Ron 10V_type": "1.05 mΩ",
        "Ron 10V_max": "1.35 mΩ",
        "Ciss": "16020 pF",
        "Qg": "252.9 nC",
        "封装": "TOLL",
        "极性": "N-channel"
    },
    "LSGT10R016_V1.0.pdf": {
        "OPN": "LSGT10R016",
        "厂家": "Lonten",
        "VDS": "100 V",
        "Ron 10V_type": "1.44 mΩ",
        "Ron 10V_max": "1.65 mΩ",
        "Ciss": "10017 pF",
        "Qg": "175.4 nC",
        "封装": "TOLL",
        "极性": "N-channel"
    },
    "LSGT20R089HCF _V1.3.pdf": {
        "OPN": "LSGT20R089HCF",
        "厂家": "Lonten",
        "VDS": "200 V",
        "Ron 10V_type": "7.8 mΩ",
        "Ron 10V_max": "8.95 mΩ",
        "Ciss": "4947 pF",
        "Qg": "63.5 nC",
        "封装": "TOLL",
        "极性": "N-channel"
    },
    "快捷芯KJ06N20T.pdf": {
        "OPN": "KJ06N20T",
        "厂家": "快捷芯",
        "VDS": "200 V",
        "Ron 10V_type": "5 mΩ",
        "Ron 10V_max": "6 mΩ",
        "Ciss": "13200 pF",
        "Qg": "212 nC",
        "封装": "TOLL-8L",
        "极性": "N-channel"
    }
}

total_correct = 0
total_checked = 0
pdf_accuracies = []

for result in results:
    pdf_name = result['pdf_name']
    print(f"\n{'='*60}")
    print(f"📄 {pdf_name}")
    print(f"{'='*60}")
    
    if pdf_name not in ground_truth:
        print("  ⚠️  无法验证（缺少真实值）")
        continue
    
    truth = ground_truth[pdf_name]
    extracted = {p['name']: p['value'] for p in result['extracted_params']}
    
    # 添加顶层字段
    extracted['OPN'] = result['opn']
    extracted['厂家'] = result['manufacturer']
    
    correct = 0
    checked = 0
    errors = []
    
    print(f"\n  {'参数名':<20} {'期望值':<20} {'提取值':<20} {'结果'}")
    print(f"  {'-'*75}")
    
    for param_name, expected_value in truth.items():
        extracted_value = extracted.get(param_name, '未提取')
        
        # 标准化对比
        exp_norm = normalize_value(expected_value)
        ext_norm = normalize_value(extracted_value)
        
        is_correct = (exp_norm == ext_norm)
        checked += 1
        
        if is_correct:
            correct += 1
            status = "✅"
        else:
            status = "❌"
            errors.append((param_name, expected_value, extracted_value))
        
        # 截断显示
        exp_display = expected_value[:18] if len(expected_value) > 18 else expected_value
        ext_display = extracted_value[:18] if len(extracted_value) > 18 else extracted_value
        
        print(f"  {param_name:<20} {exp_display:<20} {ext_display:<20} {status}")
    
    accuracy = correct / checked * 100 if checked > 0 else 0
    pdf_accuracies.append({
        'pdf': pdf_name,
        'accuracy': accuracy,
        'correct': correct,
        'total': checked,
        'errors': errors
    })
    
    total_correct += correct
    total_checked += checked
    
    print(f"\n  📊 准确率: {correct}/{checked} = {accuracy:.1f}%")
    
    if errors:
        print(f"\n  ⚠️  错误项目:")
        for param, exp, ext in errors:
            print(f"     - {param}: 期望 '{exp}', 实际 '{ext}'")

# 总结报告
print("\n" + "="*80)
print("📈 总体评估报告")
print("="*80)

overall_accuracy = total_correct / total_checked * 100 if total_checked > 0 else 0

print(f"\n整体准确率: {total_correct}/{total_checked} = {overall_accuracy:.1f}%")

print(f"\n各文件准确率:")
print(f"{'文件名':<40} {'准确率':<15} {'正确/总数'}")
print("-"*70)

for item in pdf_accuracies:
    name = item['pdf'][:38] if len(item['pdf']) > 38 else item['pdf']
    print(f"{name:<40} {item['accuracy']:.1f}%{'':<10} {item['correct']}/{item['total']}")

# 时间统计
print(f"\n⏱️  性能统计:")
total_time = sum(r['total_time'] for r in results)
total_ai_time = sum(r['ai_extract_time'] for r in results)
total_pdf_time = sum(r['pdf_parse_time'] for r in results)

print(f"  PDF解析总耗时: {total_pdf_time:.2f}s (平均 {total_pdf_time/len(results):.2f}s/文件)")
print(f"  AI提取总耗时: {total_ai_time:.2f}s (平均 {total_ai_time/len(results):.2f}s/文件)")
print(f"  总耗时: {total_time:.2f}s (平均 {total_time/len(results):.2f}s/文件)")

# 问题分析
print(f"\n🔍 问题分析:")
all_errors = []
for item in pdf_accuracies:
    all_errors.extend(item['errors'])

if all_errors:
    error_params = {}
    for param, exp, ext in all_errors:
        if param not in error_params:
            error_params[param] = []
        error_params[param].append((exp, ext))
    
    print(f"  共发现 {len(all_errors)} 处错误，涉及 {len(error_params)} 个参数:")
    for param, cases in error_params.items():
        print(f"    - {param}: {len(cases)} 处")
        for exp, ext in cases[:2]:  # 最多显示2个例子
            print(f"      期望 '{exp}' vs 实际 '{ext}'")
else:
    print("  🎉 所有验证参数全部正确!")

print("\n" + "="*80)
print("✅ 评估完成")
print("="*80)

