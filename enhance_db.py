# -*- coding: utf-8 -*-
from backend.db_manager import DatabaseManager

def enhance_variants():
    db = DatabaseManager()
    
    # 变体补丁清单： (标准参数名, [新增变体列表])
    patches = [
        ('VCE(sat)-type (Tj=25℃)', ['VCEsat', 'VCE(sat)', 'Collector-emitter saturation voltage']),
        ('VCE(sat)max (Tj=25℃)', ['VCEsat']),
        ('Vge(th)min', ['VGE(th)', 'Gate Threshold Voltage']),
        ('Vge(th)-type', ['VGE(th)']),
        ('Cies', ['CIES', 'Input Capacitance']),
        ('Coes', ['COES', 'Output Capacitance']),
        ('Cres', ['CRES', 'Reverse Transfer Capacitance']),
        ('tdon 25℃', ['Turn-on Delay Time', 'td(on)']),
        ('tdoff 25℃', ['Turn-off Delay Time', 'td(off)']),
        ('tr 25℃', ['Rise Time', 't r']),
        ('tf 25℃', ['Fall Time', 't f']),
        ('QG_IGBT', ['QG', 'Gate Charge Total']),
        ('QGE', ['QGE', 'Gate to Emitter Charge']),
        ('QGC', ['QGC', 'Gate to Collector Charge']),
        ('Rth(j-c)', ['RthJC', 'IGBT Thermal Resistance']),
        ('Rth(j-c)_diode', ['RthJC', 'SiC SBD Thermal Resistance'])
    ]
    
    for std_name, variants in patches:
        param = db.get_standard_param_by_name(std_name)
        if param:
            for v in variants:
                db.add_variant(param.id, v)
                print(f"Added variant '{v}' for '{std_name}'")
        else:
            print(f"Warning: Standard param '{std_name}' not found")

if __name__ == '__main__':
    enhance_variants()
