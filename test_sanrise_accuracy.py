# -*- coding: utf-8 -*-
"""
尚阳通(Sanrise) PDF 精度测试
前5份PDF：1个IGBT + 4个Si MOSFET (Super Junction)
P = 正确填入 / Excel实际填入, R = 正确填入 / PDF中应填入
"""

import os, sys, re, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import config
from backend.db_manager import DatabaseManager, StandardParam, ParamVariant
from backend.pdf_parser import PDFParser
from backend.ai_processor import AIProcessor

# ===================== 工具函数 =====================
def get_first_5_files():
    """获取尚阳通规格书前5个文件（按ls排序）"""
    folder = Path(__file__).parent / '尚阳通规格书'
    files = sorted(os.listdir(folder))
    # ls排序: Sanrise-SRE... 在 SRC... 前面（locale排序）
    # 但Python sort是ASCII排序，大写S < 小写a，所以SRC在Sanrise前
    # 手动把IGBT放第一个
    igbt_file = None
    mosfet_files = []
    for f in files:
        if f.startswith('Sanrise-SRE'):
            igbt_file = f
        elif len(mosfet_files) < 4:
            mosfet_files.append(f)
    result = []
    if igbt_file:
        result.append(igbt_file)
    result.extend(mosfet_files)
    return result[:5], folder


# ===================== 标准答案 =====================
# 注意：这些Sanrise PDF的文件名可能含有\xa0（非断行空格），用os.listdir获取的真实文件名作为key

GROUND_TRUTH_BY_OPN = {
    # ===== IGBT: SRE50N120FSUS7 =====
    "SRE50N120FSUS7": {
        "device_type": "IGBT",
        "params": {
            "Part Number": "SRE50N120FSUS7",
            "Package": "TO-247",
            "V(BR)CE": "1200V",
            "IC (TC=25℃)": "100A",
            "IC (TC=100℃)": "50A",
            "ICpulse": "250A",
            "IF (TC=100℃)": "40A",
            "VGE": "±20V",
            "Ptot-mos (TC=25℃)": "500W",
            "Ptot-mos (TC=100℃)": "250W",
            "VCE(sat)-type (Tj=25℃)": "1.6V",
            "VCE(sat)max (Tj=25℃)": "2.0V",
            "VF 25℃": "1.6V",
            "VF 175℃": "2.4V",
            "Vge(th)min": "4.4V",
            "Vge(th)-type": "5.4V",
            "Vge(th)max": "6.4V",
            "ICES 25℃": "100μA",
            "IGES": "100nA",
            "Cies": "4450pF",
            "Coes": "215pF",
            "Cres": "26pF",
            "tdon 25℃": "43ns",
            "tr 25℃": "24ns",
            "tdoff 25℃": "200ns",
            "tf 25℃": "95ns",
            "Eon 25℃": "0.6mJ",
            "Eoff 25℃": "0.8mJ",
            "Ets 25℃": "1.4mJ",
            "QG_IGBT": "410nC",
            "QGE": "62nC",
            "QGC": "170nC",
            "Rth(j-c)": "0.3℃/W",
            "Rth(j-c)_diode": "0.6℃/W",
            "Rth(j-a)": "40℃/W",
            "Tj min": "-40",
            "Tj max": "175",
            "标准等级": "Non-Automotive Qualified",
        },
    },
    # ===== MOSFET: SRC30R018B (300V) =====
    "SRC30R018B": {
        "device_type": "Si MOSFET",
        "params": {
            "PDF文件名": "",  # 运行时填充
            "厂家": "Sanrise", "OPN": "SRC30R018B",
            "封装": "TO-LL", "厂家封装名": "TO-LL",
            "极性": "N-channel", "技术": "Super Junction",
            "认证": "Green", "安装": "SMD",
            "VDS": "300V", "Vgs min": "-20V", "Vgs max": "20V",
            "Vth min": "3.0V", "Vth type": "4.0V", "Vth max": "5.0V",
            "Ron 10V_type": "14.5mΩ", "Ron 10V_max": "18mΩ",
            "Rg": "1.7Ω",
            "ID Tc=25℃": "82A", "ID Tc=100℃": "52A",
            "ID puls Tc=25℃": "246A",
            "Idss": "10μA",
            "IGSSF": "100nA", "IGSSR": "-100nA",
            "Is": "82A", "Ism": "246A",
            "Ciss": "3700pF", "Coss": "150pF",
            "Qgs": "27nC", "Qgd": "19nC",
            "Qg": "71nC", "Qg_10V": "71nC",
            "Vplateau": "6.5V",
            "反二极管压降Vsd": "0.9V",
            "td-on": "12ns", "tr": "23ns", "td-off": "75ns", "tf": "10ns",
            "trr": "130ns", "Qrr": "650nC", "Irrm": "10A",
            "EAS L=0.1mH": "70mJ",
            "PD Tc=25℃": "304W",
            "RthJC max": "0.41℃/W", "RthJA max": "62℃/W",
            "工作温度max": "150",
            "TSTG min": "-55", "TSTG max": "150", "Tsold": "260℃",
            "Qg测试条件": "VDD=125V, ID=15A, VGS=0~10V",
            "Ciss测试条件": "VDS=125V, VGS=0V, f=100KHz",
            "开关时间测试条件": "VDD=125V, ID=15A, RG=10Ω, VGS=12V",
            "Qrr测试条件": "VR=125V, IF=15A, dIF/dt=100A/us",
            "EAS测试条件": "IAS=16A, VDD=60V, RG=25Ω",
            "IDM限制条件": "Pulse width limited by maximum junction temperature",
        },
    },
    # ===== MOSFET: SRC60R017FB (600V, 17mΩ) =====
    "SRC60R017FB": {
        "device_type": "Si MOSFET",
        "params": {
            "PDF文件名": "",
            "厂家": "Sanrise", "OPN": "SRC60R017FB",
            "封装": "TO-247", "厂家封装名": "TO-247",
            "极性": "N-channel", "技术": "Super Junction",
            "认证": "Green", "安装": "THT",
            "VDS": "600V", "Vgs min": "-20V", "Vgs max": "20V",
            "Vth min": "3.0V", "Vth type": "4.0V", "Vth max": "5.0V",
            "Ron 10V_type": "15.1mΩ", "Ron 10V_max": "17mΩ",
            "Rg": "1.3Ω",
            "ID Tc=25℃": "120A", "ID Tc=100℃": "76A",
            "ID puls Tc=25℃": "360A",
            "Idss": "10μA",
            "IGSSF": "200nA", "IGSSR": "-200nA",
            "Is": "120A", "Ism": "360A",
            "Ciss": "13700pF", "Coss": "222pF",
            "Qgs": "85nC", "Qgd": "90nC",
            "Qg": "290nC", "Qg_10V": "290nC",
            "Vplateau": "6.5V",
            "反二极管压降Vsd": "0.85V",
            "td-on": "73.2ns", "tr": "21.6ns", "td-off": "184ns", "tf": "12.4ns",
            "trr": "195ns", "Qrr": "1800nC", "Irrm": "15A",
            "EAS L=0.1mH": "600mJ",
            "PD Tc=25℃": "657W",
            "RthJC max": "0.19℃/W", "RthJA max": "62℃/W",
            "工作温度max": "150",
            "TSTG min": "-55", "TSTG max": "150", "Tsold": "260℃",
            "Qg测试条件": "VDD=400V, ID=60A, VGS=0~10V",
            "Ciss测试条件": "VDS=400V, VGS=0V, f=100KHz",
            "开关时间测试条件": "VDD=400V, ID=60A, RG=2Ω, VGS=12V",
            "Qrr测试条件": "VR=400V, IF=50A, dIF/dt=100A/us",
            "EAS测试条件": "IAS=5.5A, VDD=60V, RG=25Ω",
            "IDM限制条件": "Pulse width limited by maximum junction temperature",
        },
    },
    # ===== MOSFET: SRC60R017FBS (600V, 17mΩ variant) =====
    "SRC60R017FBS": {
        "device_type": "Si MOSFET",
        "params": {
            "PDF文件名": "",
            "厂家": "Sanrise", "OPN": "SRC60R017FBS",
            "封装": "TO-247", "厂家封装名": "TO-247",
            "极性": "N-channel", "技术": "Super Junction",
            "认证": "Green", "安装": "THT",
            "VDS": "600V", "Vgs min": "-20V", "Vgs max": "20V",
            "Vth min": "3.5V", "Vth type": "4.5V", "Vth max": "5.5V",
            "Ron 10V_type": "14.8mΩ", "Ron 10V_max": "17mΩ",
            "Rg": "1.3Ω",
            "ID Tc=25℃": "120A", "ID Tc=100℃": "76A",
            "ID puls Tc=25℃": "360A",
            "Idss": "10μA",
            "IGSSF": "200nA", "IGSSR": "-200nA",
            "Is": "120A", "Ism": "360A",
            "Ciss": "13700pF", "Coss": "222pF",
            "Qgs": "85nC", "Qgd": "90nC",
            "Qg": "290nC", "Qg_10V": "290nC",
            "Vplateau": "6.5V",
            "反二极管压降Vsd": "0.83V",
            "td-on": "73.2ns", "tr": "21.6ns", "td-off": "184ns", "tf": "12.4ns",
            "trr": "204ns", "Qrr": "2000nC", "Irrm": "17.5A",
            "EAS L=0.1mH": "600mJ",
            "PD Tc=25℃": "657W",
            "RthJC max": "0.19℃/W", "RthJA max": "62℃/W",
            "工作温度max": "150",
            "TSTG min": "-55", "TSTG max": "150", "Tsold": "260℃",
            "Qg测试条件": "VDD=400V, ID=60A, VGS=0~10V",
            "Ciss测试条件": "VDS=400V, VGS=0V, f=100KHz",
            "开关时间测试条件": "VDD=400V, ID=60A, RG=2Ω, VGS=12V",
            "Qrr测试条件": "VR=400V, IF=60A, dIF/dt=100A/us",
            "EAS测试条件": "IAS=5.5A, VDD=60V, RG=25Ω",
            "IDM限制条件": "Pulse width limited by maximum junction temperature",
        },
    },
    # ===== MOSFET: SRC60R020BS (600V, 20mΩ) =====
    "SRC60R020BS": {
        "device_type": "Si MOSFET",
        "params": {
            "PDF文件名": "",
            "厂家": "Sanrise", "OPN": "SRC60R020BS",
            "封装": "TO-247", "厂家封装名": "TO-247",
            "极性": "N-channel", "技术": "Super Junction",
            "认证": "Green", "安装": "THT",
            "VDS": "600V", "Vgs min": "-20V", "Vgs max": "20V",
            "Vth min": "3.5V", "Vth type": "4.5V", "Vth max": "5.5V",
            "Ron 10V_type": "17mΩ", "Ron 10V_max": "20mΩ",
            "Rg": "1.02Ω",
            "ID Tc=25℃": "118A", "ID Tc=100℃": "75A",
            "ID puls Tc=25℃": "354A",
            "Idss": "10μA",
            "IGSSF": "200nA", "IGSSR": "-200nA",
            "Is": "118A", "Ism": "354A",
            "Ciss": "11900pF", "Coss": "202pF",
            "Qgs": "118nC", "Qgd": "224nC",
            "Qg": "471nC", "Qg_10V": "471nC",
            "Vplateau": "6.5V",
            "反二极管压降Vsd": "0.86V",
            "td-on": "31ns", "tr": "28ns", "td-off": "132ns", "tf": "6ns",
            "trr": "91ns", "Qrr": "1450nC", "Irrm": "27A",
            "EAS L=0.1mH": "720mJ",
            "RthJC max": "0.18℃/W", "RthJA max": "62℃/W",
            "工作温度max": "150",
            "TSTG min": "-55", "TSTG max": "150", "Tsold": "260℃",
            "Qg测试条件": "VDD=480V, ID=40A, VGS=0~10V",
            "Ciss测试条件": "VDS=400V, VGS=0V, f=100KHz",
            "开关时间测试条件": "VDD=400V, ID=40A, RG=1.8Ω, VGS=10V",
            "Qrr测试条件": "VR=100V, IF=40A, dIF/dt=100A/us",
            "EAS测试条件": "IAS=6.0A, VDD=90V, RG=25Ω",
            "IDM限制条件": "Pulse width limited by maximum junction temperature",
        },
    },
}

# OPN到文件名映射（运行时建立）
OPN_KEYWORDS = {
    "SRE50N120FSUS7": "SRE50N120FSUS7",
    "SRC30R018B": "SRC30R018B",
    "SRC60R017FB": "SRC60R017FB",  # 注意不要匹配到FBS
    "SRC60R017FBS": "SRC60R017FBS",
    "SRC60R020BS": "SRC60R020BS",
}


def extract_number(s):
    if not s or not isinstance(s, str):
        return None
    # 处理nF到pF的转换
    s_clean = s.strip()
    m = re.search(r'([-+]?\d*\.?\d+)\s*(nF|pF|μF|uF|mΩ|Ω|mJ|mA|μA|nA|nC|uC|ns|A|V|W|S|℃/W)?', s_clean, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or '').strip()
        return val, unit
    return None, ''


def values_match(gt_val, ext_val, param_name):
    if not gt_val or not ext_val:
        return False
    gt_val, ext_val = gt_val.strip(), ext_val.strip()

    text_params = {'厂家', 'OPN', '封装', '厂家封装名', '极性', '技术', '特殊功能', '认证',
                   'Product Status', '安装', 'PDF文件名', '文件名', 'Part Number', 'Package',
                   '标准等级',
                   'Qg测试条件', 'Ciss测试条件', '开关时间测试条件', 'Qrr测试条件',
                   'EAS测试条件', 'IDM限制条件'}
    if param_name in text_params:
        gt_l = gt_val.lower().replace(' ', '').replace('-', '').replace('\xa0', '')
        ex_l = ext_val.lower().replace(' ', '').replace('-', '').replace('\xa0', '')
        if '测试条件' in param_name or '限制条件' in param_name:
            gt_nums = set(re.findall(r'\d+\.?\d*', gt_val))
            ex_nums = set(re.findall(r'\d+\.?\d*', ext_val))
            return len(gt_nums & ex_nums) >= len(gt_nums) * 0.6
        return gt_l in ex_l or ex_l in gt_l

    # 数值匹配 - 先统一单位
    gn, gu = extract_number(gt_val)
    en, eu = extract_number(ext_val)
    if gn is None or en is None:
        return gt_val.replace(' ', '') == ext_val.replace(' ', '')

    # 单位转换
    unit_convert = {
        ('nf', 'pf'): 1000, ('pf', 'nf'): 0.001,
        ('uf', 'pf'): 1e6, ('pf', 'uf'): 1e-6,
        ('uc', 'nc'): 1000, ('nc', 'uc'): 0.001,
        ('ma', 'a'): 0.001, ('a', 'ma'): 1000,
        ('μa', 'a'): 1e-6, ('a', 'μa'): 1e6,
    }
    gu_l, eu_l = gu.lower(), eu.lower()
    # 将 en 从 eu 单位转换为 gu 单位：查 (eu, gu) 方向
    if gu_l != eu_l and (eu_l, gu_l) in unit_convert:
        en = en * unit_convert[(eu_l, gu_l)]

    if gn == 0:
        return en == 0
    return abs(gn - en) / abs(gn) <= 0.05


def build_excel_param_map(session):
    """复刻 generate_comparison_table 中的参数名映射逻辑"""
    all_params = session.query(StandardParam).order_by(StandardParam.id).all()
    param_names = [p.param_name for p in all_params]
    param_name_map = {}
    for p in all_params:
        norm = p.param_name.lower().replace(' ', '').replace('_', '').replace('-', '')
        param_name_map[norm] = p.param_name
        param_name_map[p.param_name] = p.param_name
        if p.param_name_en:
            param_name_map[p.param_name_en] = p.param_name
            en_norm = p.param_name_en.lower().replace(' ', '').replace('_', '').replace('-', '')
            param_name_map[en_norm] = p.param_name
        variants = session.query(ParamVariant).filter_by(param_id=p.id).all()
        for v in variants:
            vn = v.variant_name.lower().replace(' ', '').replace('_', '').replace('-', '')
            param_name_map[vn] = p.param_name
            param_name_map[v.variant_name] = p.param_name

    legacy = {
        'Ron 10V_type': 'RDS(on) 10V_type', 'Ron 10V_max': 'RDS(on) 10V_max',
        'Ron 4.5V_type': 'RDS(on) 4.5V_type', 'Ron 4.5V_max': 'RDS(on) 4.5V_max',
        'Ron 2.5V_type': 'RDS(on) 2.5V_type', 'Ron 2.5V_max': 'RDS(on) 2.5V_max',
        'Igss': 'IGSSF',
        'ID Tc=25℃': 'ID TC=25℃', 'ID Tc=100℃': 'ID TC=100℃',
        'ID puls Tc=25℃': 'ID puls TC=25℃', 'PD Tc=25℃': 'PD TC=25℃',
    }
    valid_names = set(param_names)
    for old, new in legacy.items():
        if new in valid_names:
            param_name_map[old] = new
            param_name_map[old.lower().replace(' ', '').replace('_', '').replace('-', '')] = new

    return param_names, param_name_map


def simulate_excel_row(extracted_params, param_names, param_name_map):
    excel_row = {}
    param_names_set = set(param_names)
    for p in extracted_params:
        name = p.standard_name
        value = p.value or '-'
        if not name or value == '-':
            continue
        matched = None
        if name in param_name_map:
            matched = param_name_map[name]
        else:
            norm = name.lower().replace(' ', '').replace('_', '').replace('-', '')
            if norm in param_name_map:
                matched = param_name_map[norm]
        if matched and matched in param_names_set:
            if matched not in excel_row:
                excel_row[matched] = value
    return excel_row


def match_file_to_opn(filename):
    """根据文件名匹配到OPN"""
    # SRC60R017FBS 必须在 SRC60R017FB 之前检查
    ordered_opns = ["SRE50N120FSUS7", "SRC30R018B", "SRC60R017FBS", "SRC60R017FB", "SRC60R020BS"]
    for opn in ordered_opns:
        if opn in filename:
            return opn
    return None


def run_test():
    print("=" * 80)
    print("  尚阳通(Sanrise) PDF 精度测试")
    print(f"  模型: {config.ai.model} | Provider: {config.ai.provider}")
    print(f"  P = 正确填入 / Excel实际填入 | R = 正确填入 / PDF中应填入")
    print("=" * 80)

    db = DatabaseManager()
    session = db.get_session()
    parser = PDFParser()
    ai = AIProcessor()
    params_info = db.get_all_params_with_variants()
    param_names, param_name_map = build_excel_param_map(session)
    param_names_set = set(param_names)

    print(f"\n参数库: {len(param_names)} 个标准参数列")

    files, folder = get_first_5_files()
    print(f"测试文件: {len(files)} 个")
    for f in files:
        print(f"  - {f}")

    total_tp, total_filled, total_should = 0, 0, 0
    all_results = {}

    for filename in files:
        opn = match_file_to_opn(filename)
        if not opn or opn not in GROUND_TRUTH_BY_OPN:
            print(f"\n⚠ 无法匹配OPN: {filename}")
            continue

        gt_info = GROUND_TRUTH_BY_OPN[opn]
        gt = gt_info['params'].copy()
        # 填充PDF文件名
        if 'PDF文件名' in gt:
            gt['PDF文件名'] = filename
        if '文件名' in gt:
            gt['文件名'] = filename

        # 将GT key映射到Excel标准列名
        gt_excel = {}
        for gk, gv in gt.items():
            if not gv:
                continue
            if gk in param_name_map:
                mapped = param_name_map[gk]
                if mapped in param_names_set:
                    gt_excel[mapped] = gv
            else:
                norm = gk.lower().replace(' ', '').replace('_', '').replace('-', '')
                if norm in param_name_map:
                    mapped = param_name_map[norm]
                    if mapped in param_names_set:
                        gt_excel[mapped] = gv

        pdf_path = folder / filename
        print(f"\n{'─' * 80}")
        print(f"📄 {filename} ({opn}, {gt_info['device_type']})")
        print(f"   标准答案映射到Excel列: {len(gt_excel)} 个")

        pdf_content = parser.parse_pdf(str(pdf_path))
        t0 = time.time()
        result = ai.extract_params(pdf_content, params_info, parallel=True)
        elapsed = time.time() - t0

        if result.error:
            print(f"   ❌ 提取错误: {result.error}")
            continue

        excel_row = simulate_excel_row(result.params, param_names, param_name_map)
        print(f"   AI提取 → Excel填入: {len(excel_row)} 个单元格, 耗时 {elapsed:.1f}s")
        print(f"   AI识别设备类型: {result.device_type}")

        tp, wrong_list, missed_list, extra_list = 0, [], [], []

        for col_name, gt_val in gt_excel.items():
            if col_name in excel_row:
                if values_match(gt_val, excel_row[col_name], col_name):
                    tp += 1
                else:
                    wrong_list.append((col_name, gt_val, excel_row[col_name]))
            else:
                missed_list.append((col_name, gt_val))

        for col_name, val in excel_row.items():
            if col_name not in gt_excel:
                extra_list.append((col_name, val))

        n_filled = len(excel_row)
        n_should = len(gt_excel)
        p = tp / n_filled * 100 if n_filled else 0
        r = tp / n_should * 100 if n_should else 0
        f1 = 2 * p * r / (p + r) if (p + r) else 0

        print(f"\n   📊 Excel输出统计:")
        print(f"   ├─ 应填入: {n_should} 个")
        print(f"   ├─ 实际填入: {n_filled} 个")
        print(f"   ├─ 正确(TP): {tp}")
        print(f"   ├─ 值错误:   {len(wrong_list)}")
        print(f"   ├─ 漏填(FN): {len(missed_list)}")
        print(f"   ├─ 多填(FP): {len(extra_list)}")
        print(f"   ├─ Precision: {p:.1f}%")
        print(f"   ├─ Recall:    {r:.1f}%")
        print(f"   └─ F1-Score:  {f1:.1f}%")

        if wrong_list:
            print(f"\n   ⚠ 值错误:")
            for c, gv, ev in wrong_list:
                print(f"     {c}: 标准={gv} → 提取={ev}")
        if missed_list:
            print(f"\n   ❌ 漏填:")
            for c, gv in missed_list:
                print(f"     {c}: 应为={gv}")
        if extra_list:
            print(f"\n   ➕ 多填:")
            for c, v in extra_list:
                print(f"     {c}: {v}")

        all_results[filename] = {
            'opn': opn, 'device_type': gt_info['device_type'],
            'tp': tp, 'filled': n_filled, 'should': n_should,
            'p': p, 'r': r, 'f1': f1, 'time': elapsed,
            'wrong': len(wrong_list), 'missed': len(missed_list), 'extra': len(extra_list)
        }
        total_tp += tp
        total_filled += n_filled
        total_should += n_should

    # 汇总
    avg_p = total_tp / total_filled * 100 if total_filled else 0
    avg_r = total_tp / total_should * 100 if total_should else 0
    avg_f1 = 2 * avg_p * avg_r / (avg_p + avg_r) if (avg_p + avg_r) else 0

    print(f"\n{'=' * 80}")
    print(f"  汇总")
    print(f"{'=' * 80}")
    print(f"\n{'OPN':<22} {'类型':<12} {'P':>8} {'R':>8} {'F1':>8} {'TP':>4} {'填':>4} {'应':>4} {'错':>3} {'漏':>3} {'多':>3} {'时':>6}")
    print(f"{'─'*22} {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*4} {'─'*4} {'─'*4} {'─'*3} {'─'*3} {'─'*3} {'─'*6}")
    for name, r in all_results.items():
        opn = r['opn']
        dt = r['device_type']
        print(f"{opn:<22} {dt:<12} {r['p']:>7.1f}% {r['r']:>7.1f}% {r['f1']:>7.1f}% {r['tp']:>4} {r['filled']:>4} {r['should']:>4} {r['wrong']:>3} {r['missed']:>3} {r['extra']:>3} {r['time']:>4.0f}s")
    print(f"{'─'*22} {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*4} {'─'*4} {'─'*4}")
    print(f"{'总计':<20} {'':12} {avg_p:>7.1f}% {avg_r:>7.1f}% {avg_f1:>7.1f}% {total_tp:>4} {total_filled:>4} {total_should:>4}")

    session.close()
    print(f"\n✅ 测试完成")


if __name__ == '__main__':
    run_test()
