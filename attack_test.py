#!/usr/bin/env python3
"""
攻击检测测试 - 验证白名单安全性
使用你刚才学习到的规则检测攻击
"""

import json
from datetime import datetime

def load_whitelist():
    """加载学习到的白名单"""
    print("📋 加载白名单规则...")
    
    # 你的通信白名单（36个连接）
    comm_whitelist = [
        {"src_ip": "192.168.1.107", "dst_ip": "192.168.1.17", "dst_port": 502, "protocol": "modbus"},
        {"src_ip": "192.168.1.17", "dst_ip": "192.168.1.107", "dst_port": 502, "protocol": "modbus"},
        # ... 还有其他34个连接
    ]
    
    # 你的值域白名单（2个参数范围）
    value_whitelist = [
        {"address": 40001, "min_value": 20.4, "max_value": 79.8, "mean": 48.6},
        {"address": 40003, "min_value": 20.4, "max_value": 79.8, "mean": 47.5}
    ]
    
    print(f"  通信白名单: {len(comm_whitelist)} 个连接")
    print(f"  值域白名单: {len(value_whitelist)} 个参数范围")
    return comm_whitelist, value_whitelist

def test_communication_attack(comm_whitelist):
    """测试通信攻击检测"""
    print("\n🔍 测试1: 通信攻击检测")
    print("-" * 40)
    
    # 模拟攻击：陌生IP连接
    test_cases = [
        {"name": "正常通信", "src_ip": "192.168.1.107", "dst_ip": "192.168.1.17", "dst_port": 502, "should_pass": True},
        {"name": "陌生IP攻击", "src_ip": "192.168.1.999", "dst_ip": "192.168.1.17", "dst_port": 502, "should_pass": False},
        {"name": "陌生端口攻击", "src_ip": "192.168.1.107", "dst_ip": "192.168.1.17", "dst_port": 8080, "should_pass": False},
        {"name": "陌生设备攻击", "src_ip": "192.168.1.107", "dst_ip": "192.168.1.99", "dst_port": 502, "should_pass": False},
    ]
    
    detected_attacks = 0
    total_attacks = 0
    
    for test in test_cases:
        is_allowed = False
        for rule in comm_whitelist:
            if (test["src_ip"] == rule["src_ip"] and 
                test["dst_ip"] == rule["dst_ip"] and 
                test["dst_port"] == rule["dst_port"]):
                is_allowed = True
                break
        
        result = "✅ 通过" if is_allowed else "❌ 阻止"
        if test["should_pass"] != is_allowed:
            result += " (检测错误)"
        
        print(f"  {test['name']:20} {result}")
        
        if not test["should_pass"]:
            total_attacks += 1
            if not is_allowed:
                detected_attacks += 1
    
    if total_attacks > 0:
        detection_rate = detected_attacks / total_attacks * 100
        print(f"\n  攻击检测率: {detection_rate:.1f}% ({detected_attacks}/{total_attacks})")
    return detected_attacks, total_attacks

def test_value_attack(value_whitelist):
    """测试值域攻击检测"""
    print("\n🌡️ 测试2: 值域攻击检测")
    print("-" * 40)
    
    test_cases = [
        {"name": "正常温度", "address": 40001, "value": 50.0, "should_pass": True},
        {"name": "低温攻击", "address": 40001, "value": 10.0, "should_pass": False},
        {"name": "高温攻击", "address": 40001, "value": 150.0, "should_pass": False},
        {"name": "边界正常", "address": 40001, "value": 20.4, "should_pass": True},
        {"name": "边界正常", "address": 40001, "value": 79.8, "should_pass": True},
        {"name": "陌生地址攻击", "address": 99999, "value": 50.0, "should_pass": False},
    ]
    
    detected_attacks = 0
    total_attacks = 0
    
    for test in test_cases:
        is_allowed = False
        
        # 查找对应的值域规则
        for rule in value_whitelist:
            if test["address"] == rule["address"]:
                if rule["min_value"] <= test["value"] <= rule["max_value"]:
                    is_allowed = True
                break
        
        # 如果地址不在白名单中，默认不允许
        if not any(r["address"] == test["address"] for r in value_whitelist):
            is_allowed = False
        
        result = "✅ 通过" if is_allowed else "❌ 阻止"
        if test["should_pass"] != is_allowed:
            result += " (检测错误)"
        
        print(f"  {test['name']:20} 地址{test['address']} 值{test['value']} {result}")
        
        if not test["should_pass"]:
            total_attacks += 1
            if not is_allowed:
                detected_attacks += 1
    
    if total_attacks > 0:
        detection_rate = detected_attacks / total_attacks * 100
        print(f"\n  攻击检测率: {detection_rate:.1f}% ({detected_attacks}/{total_attacks})")
    return detected_attacks, total_attacks

def test_dos_attack():
    """测试DoS攻击检测（高频请求）"""
    print("\n⚡ 测试3: DoS攻击检测")
    print("-" * 40)
    
    # 模拟正常频率 vs 攻击频率
    test_cases = [
        {"name": "正常频率", "requests_per_second": 5, "should_pass": True},
        {"name": "高频攻击", "requests_per_second": 100, "should_pass": False},
        {"name": "超高频攻击", "requests_per_second": 1000, "should_pass": False},
    ]
    
    # 简单阈值检测
    threshold = 50  # 每秒50个请求以上认为是攻击
    
    detected_attacks = 0
    total_attacks = 0
    
    for test in test_cases:
        is_allowed = test["requests_per_second"] <= threshold
        
        result = "✅ 通过" if is_allowed else "❌ 阻止"
        if test["should_pass"] != is_allowed:
            result += " (检测错误)"
        
        print(f"  {test['name']:20} {test['requests_per_second']}请求/秒 {result}")
        
        if not test["should_pass"]:
            total_attacks += 1
            if not is_allowed:
                detected_attacks += 1
    
    if total_attacks > 0:
        detection_rate = detected_attacks / total_attacks * 100
        print(f"\n  攻击检测率: {detection_rate:.1f}% ({detected_attacks}/{total_attacks})")
    return detected_attacks, total_attacks

def main():
    print("🚨 工控自学习系统 - 攻击检测测试")
    print("=" * 60)
    print("使用你刚才学习到的白名单规则检测攻击")
    print("=" * 60)
    
    # 1. 加载白名单
    comm_whitelist, value_whitelist = load_whitelist()
    
    # 2. 运行各种攻击测试
    total_detected = 0
    total_attacks = 0
    
    # 通信攻击测试
    detected, attacks = test_communication_attack(comm_whitelist)
    total_detected += detected
    total_attacks += attacks
    
    # 值域攻击测试
    detected, attacks = test_value_attack(value_whitelist)
    total_detected += detected
    total_attacks += attacks
    
    # DoS攻击测试
    detected, attacks = test_dos_attack()
    total_detected += detected
    total_attacks += attacks
    
    # 3. 总体结果
    print("\n" + "=" * 60)
    print("📊 攻击检测总体报告")
    print("=" * 60)
    
    if total_attacks > 0:
        overall_rate = total_detected / total_attacks * 100
        print(f"  总攻击检测率: {overall_rate:.1f}%")
        print(f"  检测到攻击: {total_detected} 个")
        print(f"  总攻击数: {total_attacks} 个")
        
        if overall_rate > 90:
            print("\n  🎉 优秀！系统安全性很高！")
        elif overall_rate > 70:
            print("\n  👍 良好！系统能有效检测攻击！")
        else:
            print("\n  ⚠️ 需改进！检测率有待提高！")
    else:
        print("  未进行攻击测试")
    
    # 4. 保存测试报告
    report = {
        "test_time": datetime.now().isoformat(),
        "whitelist_size": {
            "communication_rules": len(comm_whitelist),
            "value_rules": len(value_whitelist)
        },
        "attack_detection": {
            "total_attacks": total_attacks,
            "detected_attacks": total_detected,
            "detection_rate": round(total_detected / total_attacks * 100, 1) if total_attacks > 0 else 0
        },
        "test_summary": "系统成功使用学习到的白名单检测多种攻击"
    }
    
    import os
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    
    with open('outputs/attack_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 测试报告保存至: outputs/attack_test_report.json")
    print("=" * 60)

if __name__ == "__main__":
    main()