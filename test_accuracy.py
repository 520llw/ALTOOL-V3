# -*- coding: utf-8 -*-
"""
DeepSeek 提取精度测试脚本
以人工从PDF中提取的参数作为标准答案(Ground Truth)，
运行软件提取后计算 Precision 和 Recall。
"""

import os
import sys
import re
import shutil
import time
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import config, DATA_DIR
from backend.db_manager import DatabaseManager
from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor

# ===================== 标准答案（Ground Truth）=====================
# 从PDF中人工逐项核对的参数值
# key = 标准参数名, value = 参数值（纯数值+单位字符串）

GROUND_TRUTH = {
    "LSGT10R011_V1.0.pdf": {
        # 基本信息
        "PDF文件名": "LSGT10R011_V1.0.pdf",
        "厂家": "Lonten",
        "OPN": "LSGT10R011",
        "封装": "TOLL",
        "厂家封装名": "TOLL",
        "极性": "N-channel",
        "技术": "Shielded Gate Trench DMOS",
        "特殊功能": "Fast switching",
        "认证": "Green device",
        "安装": "SMD",
        # 电压
        "VDS": "100V",
        "Vgs min": "-20V",
        "Vgs max": "20V",
        "Vth min": "2V",
        "Vth type": "3.18V",
        "Vth max": "4V",
        "Vplateau": "4.9V",
        # 电阻
        "Ron 10V_type": "0.98mΩ",
        "Ron 10V_max": "1.15mΩ",
        "RDS(on) 10V TJ=175℃": "2.16mΩ",
        "Rg": "1.49Ω",
        # 电流
        "ID Tc=25℃": "478A",
        "ID TA=25℃": "420A",
        "ID Tc=100℃": "338A",
        "ID puls Tc=25℃": "1680A",
        "Idss": "1μA",
        "IDSS TJ=175℃": "300μA",
        "Igss": "100nA",
        "IGSSF": "100nA",
        "IGSSR": "100nA",
        "Is": "420A",
        "Ism": "1680A",
        "Irrm": "3.62A",
        "gfs": "176S",
        # 电容
        "Ciss": "14838pF",
        "Coss": "3458pF",
        "Crss": "73pF",
        # 电荷
        "Qg": "260.1nC",
        "Qg_10V": "260.1nC",
        "Qgs": "69.1nC",
        "Qgd": "78.0nC",
        "Qoss": "302.5nC",
        "Qrr": "191.4nC",
        # 时间
        "td-on": "160.5ns",
        "tr": "183.1ns",
        "td-off": "322.5ns",
        "tf": "135.1ns",
        "trr": "83.9ns",
        # 二极管
        "反二极管压降Vsd": "1.1V",
        # 热特性与其他
        "EAS L=0.1mH": "1764mJ",
        "PD Tc=25℃": "577W",
        "RthJC max": "0.26℃/W",
        "RthJA max": "62℃/W",
        "工作温度min": "-55",
        "工作温度max": "175",
        "TSTG min": "-55",
        "TSTG max": "175",
        "Tsold": "260℃",
        # 测试条件
        "Qg测试条件": "VDS=50V, ID=50A, VGS=10V",
        "Ciss测试条件": "VDS=50V, VGS=0V, f=250kHz",
        "开关时间测试条件": "VDD=50V, VGS=10V, ID=50A, Rg=10Ω",
        "Qrr测试条件": "IS=50A, di/dt=100A/us, TJ=25℃",
        "EAS测试条件": "VDD=50V, VGS=10V, L=0.5mH, IAS=84A",
        "IDM限制条件": "Pulse width limited by maximum junction temperature",
    },
    "LSGT10R016_V1.0.pdf": {
        "PDF文件名": "LSGT10R016_V1.0.pdf",
        "厂家": "Lonten",
        "OPN": "LSGT10R016",
        "封装": "TOLL",
        "厂家封装名": "TOLL",
        "极性": "N-channel",
        "技术": "Shielded Gate Trench DMOS",
        "特殊功能": "Fast switching",
        "认证": "Green device",
        "安装": "SMD",
        "VDS": "100V",
        "Vgs min": "-20V",
        "Vgs max": "20V",
        "Vth min": "2V",
        "Vth type": "3.3V",
        "Vth max": "4V",
        "Vplateau": "5.5V",
        "Ron 10V_type": "1.44mΩ",
        "Ron 10V_max": "1.65mΩ",
        "RDS(on) 10V TJ=175℃": "3.08mΩ",
        "Rg": "2.17Ω",
        "ID Tc=25℃": "348A",
        "ID TA=25℃": "300A",
        "ID Tc=100℃": "246A",
        "ID puls Tc=25℃": "1200A",
        "Idss": "1μA",
        "IDSS TJ=175℃": "300μA",
        "Igss": "100nA",
        "IGSSF": "100nA",
        "IGSSR": "100nA",
        "Is": "300A",
        "Ism": "1200A",
        "Irrm": "3.15A",
        "gfs": "160S",
        "Ciss": "10017pF",
        "Coss": "2332pF",
        "Crss": "70pF",
        "Qg": "175.4nC",
        "Qg_10V": "175.4nC",
        "Qgs": "52.2nC",
        "Qgd": "55nC",
        "Qoss": "210nC",
        "Qrr": "138.7nC",
        "td-on": "139.6ns",
        "tr": "161.5ns",
        "td-off": "201.3ns",
        "tf": "93.2ns",
        "trr": "70.6ns",
        "反二极管压降Vsd": "1.1V",
        "EAS L=0.1mH": "1190mJ",
        "PD Tc=25℃": "429W",
        "RthJC max": "0.35℃/W",
        "RthJA max": "62℃/W",
        "工作温度min": "-55",
        "工作温度max": "175",
        "TSTG min": "-55",
        "TSTG max": "175",
        "Tsold": "260℃",
        "Qg测试条件": "VDS=50V, ID=50A, VGS=10V",
        "Ciss测试条件": "VDS=50V, VGS=0V, f=250kHz",
        "开关时间测试条件": "VDD=50V, VGS=10V, ID=50A, Rg=10Ω",
        "Qrr测试条件": "IS=50A, di/dt=100A/us, TJ=25℃",
        "EAS测试条件": "VDD=50V, VGS=10V, L=0.5mH, IAS=69A",
        "IDM限制条件": "Pulse width limited by maximum junction temperature",
    },
    "LSGT10R013_V1.1(1).pdf": {
        "PDF文件名": "LSGT10R013_V1.1(1).pdf",
        "厂家": "Lonten",
        "OPN": "LSGT10R013",
        "封装": "TOLL",
        "厂家封装名": "TOLL",
        "极性": "N-channel",
        "技术": "Shielded Gate Trench DMOS",
        "特殊功能": "Fast switching",
        "认证": "Green device",
        "安装": "SMD",
        "VDS": "100V",
        "Vgs min": "-20V",
        "Vgs max": "20V",
        "Vth min": "2V",
        "Vth type": "2.87V",
        "Vth max": "4V",
        "Vplateau": "4.6V",
        "Ron 10V_type": "1.05mΩ",
        "Ron 10V_max": "1.35mΩ",
        "RDS(on) 10V TJ=175℃": "2.29mΩ",
        "Rg": "1.34Ω",
        "ID Tc=25℃": "445A",
        "ID TA=25℃": "420A",
        "ID Tc=100℃": "314A",
        "ID puls Tc=25℃": "1680A",
        "Idss": "1μA",
        "IDSS TJ=175℃": "300μA",
        "Igss": "100nA",
        "IGSSF": "100nA",
        "IGSSR": "100nA",
        "Is": "420A",
        "Ism": "1680A",
        "Irrm": "4.29A",
        "gfs": "161.8S",
        "Ciss": "16020pF",
        "Coss": "1980pF",
        "Crss": "72.6pF",
        "Qg": "252.9nC",
        "Qg_10V": "252.9nC",
        "Qgs": "67.4nC",
        "Qgd": "65.2nC",
        "Qoss": "258nC",
        "Qrr": "213.6nC",
        "td-on": "133.1ns",
        "tr": "161.1ns",
        "td-off": "239ns",
        "tf": "101.9ns",
        "trr": "84.4ns",
        "反二极管压降Vsd": "1.1V",
        "EAS L=0.1mH": "1764mJ",
        "PD Tc=25℃": "581W",
        "RthJC max": "0.26℃/W",
        "RthJA max": "62℃/W",
        "工作温度min": "-55",
        "工作温度max": "175",
        "TSTG min": "-55",
        "TSTG max": "175",
        "Tsold": "260℃",
        "Qg测试条件": "VDS=50V, ID=50A, VGS=10V",
        "Ciss测试条件": "VDS=50V, VGS=0V, f=100kHz",
        "开关时间测试条件": "VDD=50V, VGS=10V, ID=50A, Rg=10Ω",
        "Qrr测试条件": "IS=50A, di/dt=100A/us, TJ=25℃",
        "EAS测试条件": "VDD=50V, VGS=10V, L=0.5mH, IAS=84A",
        "IDM限制条件": "Pulse width limited by maximum junction temperature",
    },
    "LSGT20R089HCF _V1.3.pdf": {
        "PDF文件名": "LSGT20R089HCF _V1.3.pdf",
        "厂家": "Lonten",
        "OPN": "LSGT20R089HCF",
        "封装": "TOLL",
        "厂家封装名": "TOLL",
        "极性": "N-channel",
        "技术": "Shielded Gate Trench DMOS",
        "特殊功能": "Fast switching",
        "认证": "Pb-free",
        "安装": "SMD",
        "VDS": "200V",
        "Vgs min": "-20V",
        "Vgs max": "20V",
        "Vth min": "2.5V",
        "Vth max": "4.5V",
        "Vplateau": "4.9V",
        "Ron 10V_type": "7.8mΩ",
        "Ron 10V_max": "8.95mΩ",
        "RDS(on) 10V TJ=150℃": "16.6mΩ",
        "Rg": "1.3Ω",
        "ID Tc=25℃": "159A",
        "ID TA=25℃": "360A",
        "ID Tc=100℃": "100A",
        "ID puls Tc=25℃": "636A",
        "Idss": "1μA",
        "IDSS TJ=150℃": "10mA",
        "Igss": "100nA",
        "IGSSF": "100nA",
        "IGSSR": "100nA",
        "Is": "159A",
        "Ism": "636A",
        "gfs": "86S",
        "Ciss": "4947pF",
        "Coss": "513pF",
        "Crss": "7.8pF",
        "Qg": "63.5nC",
        "Qg_10V": "63.5nC",
        "Qgs": "23.5nC",
        "Qgd": "9.9nC",
        "Qoss": "170nC",
        "Qrr": "1167nC",
        "td-on": "51.2ns",
        "tr": "98.8ns",
        "td-off": "62ns",
        "tf": "16.5ns",
        "trr": "121ns",
        "反二极管压降Vsd": "1.1V",
        "EAS L=0.1mH": "1122mJ",
        "PD Tc=25℃": "481W",
        "RthJC max": "0.26℃/W",
        "RthJA max": "62℃/W",
        "工作温度min": "-55",
        "工作温度max": "150",
        "TSTG min": "-55",
        "TSTG max": "150",
        "Tsold": "260℃",
        "Qg测试条件": "VDS=100V, ID=50A, VGS=10V",
        "Ciss测试条件": "VDS=100V, VGS=0V, f=250kHz",
        "开关时间测试条件": "VDD=100V, VGS=10V, ID=50A, RG=10Ω",
        "Qrr测试条件": "IS=50A, di/dt=200A/us, TJ=25℃",
        "EAS测试条件": "VDD=50V, VGS=10V, L=0.5mH, IAS=67A",
        "IDM限制条件": "Pulse width limited by maximum junction temperature",
    },
}


def extract_number(value_str: str) -> float:
    """从参数值字符串中提取数字部分"""
    if not value_str or not isinstance(value_str, str):
        return None
    value_str = value_str.strip()
    # 匹配数字（含负号、小数点）
    m = re.search(r'[-+]?\d*\.?\d+', value_str)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def values_match(gt_value: str, extracted_value: str, param_name: str) -> bool:
    """
    判断提取值是否与标准答案匹配
    
    对于文本类参数（厂家、OPN、封装等）：模糊字符串匹配
    对于数值类参数：提取数字后比较，允许5%误差
    """
    if not gt_value or not extracted_value:
        return False
    
    gt_value = gt_value.strip()
    extracted_value = extracted_value.strip()
    
    # 文本类参数：不区分大小写的包含匹配
    text_params = {'厂家', 'OPN', '封装', '厂家封装名', '极性', '技术', '特殊功能', '认证',
                   'Product Status', '安装', 'PDF文件名',
                   'Qg测试条件', 'Ciss测试条件', '开关时间测试条件', 'Qrr测试条件',
                   'EAS测试条件', 'IDM限制条件'}
    if param_name in text_params:
        gt_lower = gt_value.lower().replace(' ', '').replace('-', '').replace('_', '')
        ext_lower = extracted_value.lower().replace(' ', '').replace('-', '').replace('_', '')
        # 对于测试条件，只要关键数值都出现即可
        if '测试条件' in param_name or '限制条件' in param_name:
            gt_nums = set(re.findall(r'\d+\.?\d*', gt_value))
            ext_nums = set(re.findall(r'\d+\.?\d*', extracted_value))
            return len(gt_nums & ext_nums) >= len(gt_nums) * 0.6  # 60%的数值匹配即可
        return gt_lower in ext_lower or ext_lower in gt_lower
    
    # 数值类参数
    gt_num = extract_number(gt_value)
    ext_num = extract_number(extracted_value)
    
    if gt_num is None or ext_num is None:
        # 无法提取数字，回退到字符串匹配
        return gt_value.replace(' ', '') == extracted_value.replace(' ', '')
    
    if gt_num == 0:
        return ext_num == 0
    
    # 允许5%误差
    tolerance = 0.05
    return abs(gt_num - ext_num) / abs(gt_num) <= tolerance


def run_test():
    """运行提取测试"""
    print("=" * 70)
    print("  DeepSeek 参数提取精度测试")
    print(f"  模型: {config.ai.model} | Provider: {config.ai.provider}")
    print("=" * 70)
    
    pdf_parser = PDFParser()
    ai_processor = AIProcessor()
    db_manager = DatabaseManager()
    
    # 获取参数库（必须使用 get_all_params_with_variants，返回字典列表）
    params_info = db_manager.get_all_params_with_variants()
    print(f"\n参数库: {len(params_info)} 个标准参数")
    
    # 汇总统计
    all_results = {}
    total_tp = 0
    total_extracted = 0
    total_gt = 0
    
    pdf_files = list(GROUND_TRUTH.keys())
    
    for pdf_name in pdf_files:
        pdf_path = Path(__file__).parent / pdf_name
        
        if not pdf_path.exists():
            print(f"\n⚠ 文件不存在: {pdf_name}，跳过")
            continue
        
        gt = GROUND_TRUTH[pdf_name]
        
        print(f"\n{'─' * 70}")
        print(f"📄 正在提取: {pdf_name}")
        print(f"   标准答案: {len(gt)} 个参数")
        
        # 解析PDF
        try:
            pdf_content = pdf_parser.parse_pdf(str(pdf_path))
        except Exception as e:
            print(f"   ❌ PDF解析失败: {e}")
            continue
        
        # AI提取
        start_time = time.time()
        try:
            result = ai_processor.extract_params(pdf_content, params_info, parallel=True)
        except Exception as e:
            print(f"   ❌ AI提取失败: {e}")
            continue
        elapsed = time.time() - start_time
        
        if result.error:
            print(f"   ❌ 提取错误: {result.error}")
            continue
        
        print(f"   提取完成: {len(result.params)} 个参数, 耗时 {elapsed:.1f}s")
        
        # 构建提取结果映射（同时建立小写归一化映射，处理 TC/Tc 大小写问题）
        extracted_map = {}
        extracted_map_normalized = {}  # normalized_name -> (original_name, value)
        for p in result.params:
            extracted_map[p.standard_name] = p.value
            norm_key = p.standard_name.lower().replace(' ', '')
            extracted_map_normalized[norm_key] = (p.standard_name, p.value)
        
        # 计算匹配
        tp = 0  # True Positive (正确提取)
        fn_list = []  # False Negative (漏提)
        fp_list = []  # False Positive (多提或错提)
        correct_list = []  # 正确的参数
        wrong_list = []  # 值错误的参数
        
        # 检查 Recall: 标准答案中的每个参数是否被正确提取
        matched_ext_names = set()  # 记录已匹配的提取参数名，用于计算FP
        for gt_name, gt_value in gt.items():
            if gt_name in extracted_map:
                matched_ext_names.add(gt_name)
                if values_match(gt_value, extracted_map[gt_name], gt_name):
                    tp += 1
                    correct_list.append(gt_name)
                else:
                    wrong_list.append((gt_name, gt_value, extracted_map[gt_name]))
            else:
                # 尝试大小写归一化匹配（处理 TC/Tc 等差异）
                norm_key = gt_name.lower().replace(' ', '')
                if norm_key in extracted_map_normalized:
                    orig_name, ext_val = extracted_map_normalized[norm_key]
                    matched_ext_names.add(orig_name)
                    if values_match(gt_value, ext_val, gt_name):
                        tp += 1
                        correct_list.append(gt_name)
                    else:
                        wrong_list.append((gt_name, gt_value, ext_val))
                else:
                    fn_list.append(gt_name)
        
        # 检查 Precision: 提取的参数中有多少不在标准答案中
        gt_names_normalized = {n.lower().replace(' ', '') for n in gt.keys()}
        for ext_name, ext_value in extracted_map.items():
            if ext_name not in matched_ext_names:
                ext_norm = ext_name.lower().replace(' ', '')
                if ext_norm not in gt_names_normalized:
                    fp_list.append((ext_name, ext_value))
        
        # 计算指标
        n_extracted = len(extracted_map)
        n_gt = len(gt)
        # Precision = 正确提取 / 总提取数（包含值错误的也算提取了）
        # 这里用严格匹配：值也要对才算TP
        precision = tp / n_extracted * 100 if n_extracted > 0 else 0
        recall = tp / n_gt * 100 if n_gt > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"\n   📊 结果统计:")
        print(f"   ├─ 正确提取(TP): {tp}/{n_gt}")
        print(f"   ├─ 值错误:       {len(wrong_list)}")
        print(f"   ├─ 漏提(FN):     {len(fn_list)}")
        print(f"   ├─ 多提(FP):     {len(fp_list)}")
        print(f"   ├─ Precision:    {precision:.1f}%")
        print(f"   ├─ Recall:       {recall:.1f}%")
        print(f"   └─ F1-Score:     {f1:.1f}%")
        
        if wrong_list:
            print(f"\n   ⚠ 值错误的参数:")
            for name, gt_val, ext_val in wrong_list:
                print(f"     {name}: 标准={gt_val}, 提取={ext_val}")
        
        if fn_list:
            print(f"\n   ❌ 漏提的参数: {', '.join(fn_list)}")
        
        if fp_list:
            print(f"\n   ➕ 多提的参数:")
            for name, val in fp_list:
                print(f"     {name}: {val}")
        
        all_results[pdf_name] = {
            'tp': tp, 'n_extracted': n_extracted, 'n_gt': n_gt,
            'precision': precision, 'recall': recall, 'f1': f1,
            'wrong': len(wrong_list), 'fn': len(fn_list), 'fp': len(fp_list),
            'time': elapsed,
        }
        
        total_tp += tp
        total_extracted += n_extracted
        total_gt += n_gt
    
    # ==================== 汇总 ====================
    print(f"\n{'=' * 70}")
    print(f"  汇总结果 ({len(all_results)} 个文件)")
    print(f"{'=' * 70}")
    
    avg_p = total_tp / total_extracted * 100 if total_extracted > 0 else 0
    avg_r = total_tp / total_gt * 100 if total_gt > 0 else 0
    avg_f1 = 2 * avg_p * avg_r / (avg_p + avg_r) if (avg_p + avg_r) > 0 else 0
    
    print(f"\n{'文件名':<35} {'P':>8} {'R':>8} {'F1':>8} {'TP/GT':>10} {'耗时':>8}")
    print(f"{'─' * 35} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 10} {'─' * 8}")
    
    for pdf_name, r in all_results.items():
        short_name = pdf_name[:33] if len(pdf_name) > 33 else pdf_name
        print(f"{short_name:<35} {r['precision']:>7.1f}% {r['recall']:>7.1f}% {r['f1']:>7.1f}% {r['tp']:>4}/{r['n_gt']:<4} {r['time']:>6.1f}s")
    
    print(f"{'─' * 35} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 10} {'─' * 8}")
    print(f"{'总计/平均':<33} {avg_p:>7.1f}% {avg_r:>7.1f}% {avg_f1:>7.1f}% {total_tp:>4}/{total_gt:<4}")
    
    print(f"\n✅ 测试完成")
    return all_results


if __name__ == '__main__':
    run_test()
