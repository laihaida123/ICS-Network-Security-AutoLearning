#!/usr/bin/env python3
"""
动态攻击检测测试 - 读取实际生成的白名单进行测试
"""

import yaml
import json
from datetime import datetime
import random

def load_real_whitelist():
    """动态加载实际生成的白名单"""
    print("📋 加载实际生成的白名单...")
    
    try:
        # 1. 加载whitelist.yaml
        with open('outputs/whitelist.yaml', 'r', encoding='utf-8') as f:
            whitelist = yaml.safe_load(f)
        
        # 2. 加载learning_report.json获取统计信息
        with open('outputs/learning_report.json', 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        print(f"✅ 白名单加载成功！")
        print(f"   通信规则: {len(whitelist.get('communication_whitelist', []))} 个")
        print(f"   值域规则: {len(whitelist.get('value_whitelist', []))} 个")
        print(f"   学习数据包: {report.get('statistics', {}).get('total_packets_processed', 0):,} 个")
        
        return whitelist, report
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("请先运行完整学习生成白名单: poetry run python main.py --mode full")
        return None, None

def test_with_real_data(whitelist, report):
    """使用真实白名单数据进行测试"""
    print("\n🔍 动态攻击检测测试")
    print("=" * 60)
    
    if not whitelist:
        print("❌ 无法加载白名单，测试终止")
        return
    
    # 获取真实数据
    comm_whitelist = whitelist.get('communication_whitelist', [])
    value_whitelist = whitelist.get('value_whitelist', [])
    
    # 统计信息
    total_packets = report.get('statistics', {}).get('total_packets_processed', 0)
    approved_connections = report.get('statistics', {}).get('total_connections_approved', 0)
    
    print(f"📊 使用真实学习数据:")
    print(f"   学习时长: {whitelist.get('learning_duration_days', '未知')} 天")
    print(f"   处理数据包: {total_packets:,} 个")
    print(f"   批准连接: {approved_connections} 个")
    print(f"   值域规则: {len(value_whitelist)} 个")
    
    # 测试1：从真实白名单中抽样测试
    print("\n🧪 测试1: 真实白名单连接验证")
    print("-" * 40)
    
    if comm_whitelist:
        # 随机选择5个真实连接进行验证
        sample_size = min(5, len(comm_whitelist))
        samples = random.sample(comm_whitelist, sample_size)
        
        for i, conn in enumerate(samples):
            print(f"  示例{i+1}: {conn['src_ip']} → {conn['dst_ip']}:{conn['dst_port']}")
            print(f"     观测次数: {conn['observation_count']}次")
            print(f"     置信度: {conn['confidence']:.2%}")
            print(f"     日平均流量: {conn['avg_packets_per_day']:.1f} 包/天")
    
    # 测试2：值域规则验证
    print("\n🌡️ 测试2: 真实值域规则验证")
    print("-" * 40)
    
    if value_whitelist:
        # 按观测次数排序，选择最常观测的参数
        sorted_values = sorted(value_whitelist, 
                              key=lambda x: x.get('observation_count', 0), 
                              reverse=True)
        
        sample_size = min(3, len(sorted_values))
        for i, value_rule in enumerate(sorted_values[:sample_size]):
            print(f"  参数{i+1}: 地址 {value_rule['address']}")
            print(f"     正常范围: {value_rule['min_value']} ~ {value_rule['max_value']}")
            print(f"     观测次数: {value_rule['observation_count']}次")
            print(f"     均值: {value_rule['mean']:.2f}, 标准差: {value_rule.get('std_dev', 'N/A')}")
            if value_rule.get('unit'):
                print(f"     单位: {value_rule['unit']}")
    
    # 测试3：基于真实数据的攻击测试
    print("\n🚨 测试3: 基于真实数据的攻击检测")
    print("-" * 40)
    
    # 生成基于真实数据的测试用例
    test_cases = []
    
    if comm_whitelist and len(comm_whitelist) > 0:
        # 使用真实连接作为正常用例
        real_conn = comm_whitelist[0]
        test_cases.append({
            'name': '真实正常连接',
            'src_ip': real_conn['src_ip'],
            'dst_ip': real_conn['dst_ip'],
            'dst_port': real_conn['dst_port'],
            'should_pass': True
        })
        
        # 基于真实连接的攻击用例
        test_cases.append({
            'name': '陌生IP攻击（基于真实目标）',
            'src_ip': '192.168.1.200',  # 攻击者IP
            'dst_ip': real_conn['dst_ip'],
            'dst_port': real_conn['dst_port'],
            'should_pass': False
        })
        
        test_cases.append({
            'name': '端口扫描攻击',
            'src_ip': '192.168.1.201',
            'dst_ip': real_conn['dst_ip'],
            'dst_port': 80,  # 非工控端口
            'should_pass': False
        })
    
    if value_whitelist and len(value_whitelist) > 0:
        real_value = value_whitelist[0]
        test_cases.append({
            'name': '真实正常值域',
            'address': real_value['address'],
            'value': real_value['mean'],
            'should_pass': True
        })
        
        test_cases.append({
            'name': '异常值攻击',
            'address': real_value['address'],
            'value': real_value['max_value'] * 2,  # 两倍最大值
            'should_pass': False
        })
        
        test_cases.append({
            'name': '陌生地址攻击',
            'address': 99999,  # 不存在的地址
            'value': 50.0,
            'should_pass': False
        })
    
    # 执行测试
    detected_attacks = 0
    total_attacks = 0
    
    for test in test_cases:
        if 'dst_port' in test:  # 通信测试
            is_allowed = any(
                conn['src_ip'] == test['src_ip'] and
                conn['dst_ip'] == test['dst_ip'] and
                conn['dst_port'] == test['dst_port']
                for conn in comm_whitelist
            )
        else:  # 值域测试
            is_allowed = False
            for rule in value_whitelist:
                if rule['address'] == test['address']:
                    if rule['min_value'] <= test['value'] <= rule['max_value']:
                        is_allowed = True
                    break
        
        result = "✅ 通过" if is_allowed else "❌ 阻止"
        if test['should_pass'] != is_allowed:
            result += " (检测错误！)"
        
        # 显示测试结果
        if 'dst_port' in test:
            print(f"  {test['name']:30} {test['src_ip']}→{test['dst_ip']}:{test['dst_port']} {result}")
        else:
            print(f"  {test['name']:30} 地址{test['address']} 值{test['value']} {result}")
        
        if not test['should_pass']:
            total_attacks += 1
            if not is_allowed:
                detected_attacks += 1
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("📊 动态攻击检测报告")
    print("=" * 60)
    
    if total_attacks > 0:
        detection_rate = detected_attacks / total_attacks * 100
        print(f"  攻击检测率: {detection_rate:.1f}%")
        print(f"  检测到攻击: {detected_attacks} 个")
        print(f"  总攻击数: {total_attacks} 个")
        
        if detection_rate == 100:
            print("\n  🎉 完美！所有攻击均被检测！")
        elif detection_rate >= 90:
            print("\n  👍 优秀！检测率很高！")
        else:
            print("\n  ⚠️ 需要改进！存在漏报！")
    else:
        print("  未进行攻击测试")
    
    # 保存测试报告
    save_dynamic_report(whitelist, test_cases, detected_attacks, total_attacks)

def save_dynamic_report(whitelist, test_cases, detected, total):
    """保存动态测试报告"""
    report = {
        'test_time': datetime.now().isoformat(),
        'whitelist_source': 'outputs/whitelist.yaml',
        'whitelist_stats': {
            'communication_rules': len(whitelist.get('communication_whitelist', [])),
            'value_rules': len(whitelist.get('value_whitelist', []))
        },
        'test_cases': [
            {
                'name': case['name'],
                'type': 'communication' if 'dst_port' in case else 'value',
                'expected': 'pass' if case['should_pass'] else 'block',
                'actual': 'pass' if (
                    (case['should_pass'] and 'dst_port' in case and any(
                        conn['src_ip'] == case['src_ip'] and
                        conn['dst_ip'] == case['dst_ip'] and
                        conn['dst_port'] == case['dst_port']
                        for conn in whitelist.get('communication_whitelist', [])
                    )) or
                    (case['should_pass'] and 'address' in case and any(
                        rule['address'] == case['address'] and
                        rule['min_value'] <= case['value'] <= rule['max_value']
                        for rule in whitelist.get('value_whitelist', [])
                    ))
                ) else 'block'
            }
            for case in test_cases
        ],
        'attack_detection': {
            'total_attacks': total,
            'detected_attacks': detected,
            'detection_rate': round(detected / total * 100, 1) if total > 0 else 0
        }
    }
    
    import os
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    
    report_file = 'outputs/attack_test_dynamic.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 动态测试报告保存至: {report_file}")

def main():
    print("🚨 动态攻击检测测试 - 使用真实生成的白名单")
    print("=" * 60)
    print("说明：此脚本读取outputs/whitelist.yaml中的实际学习结果")
    print("进行攻击检测验证，确保测试的真实性")
    print("=" * 60)
    
    # 加载真实白名单
    whitelist, report = load_real_whitelist()
    
    # 执行测试
    if whitelist:
        test_with_real_data(whitelist, report)
    
    print("\n" + "=" * 60)
    print("✅ 动态测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()