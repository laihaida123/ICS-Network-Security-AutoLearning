# Relative Path: attack_test.py
"""
攻击检测测试模块
用于测试学习到的白名单对各种攻击的检测能力
"""

import json
import yaml
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

from simulator.data_generator import TrafficGenerator
from simulator.packet_parser import PacketParser
from simulator.learner.comm_learner import CommunicationLearner
from simulator.learner.value_learner import ValueLearner
from simulator.model.models import PacketMetadata, ProtocolData, LearningContext
from simulator.model.database import ObservationDatabase


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_whitelist(whitelist_path: str = "outputs/whitelist.yaml"):
    """加载白名单"""
    with open(whitelist_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_attack_tests(config_path: str = "config.yaml", whitelist_path: str = "outputs/whitelist.yaml"):
    """运行攻击检测测试"""
    print("🛡️ 攻击检测测试")
    print("=" * 60)
    
    # 加载配置和白名单
    config = load_config(config_path)
    whitelist = load_whitelist(whitelist_path)
    
    print(f"⚙️  使用配置: {config_path}")
    print(f"📋 使用白名单: {whitelist_path}")
    print(f"📊 白名单统计: {len(whitelist.get('communication_rules', []))} 个通信规则, "
          f"{len(whitelist.get('value_rules', []))} 个值域规则")
    
    # 初始化组件
    context = LearningContext(
        mode='validation',
        start_time=datetime.now(),
        duration_days=1,
        min_observation_count=config.get('learning', {}).get('min_observation_count', 10),
        min_observation_days=config.get('learning', {}).get('min_observation_days', 2)
    )
    
    packet_parser = PacketParser(config)
    db = ObservationDatabase()
    
    # 创建学习器实例（用于验证，不进行学习）
    comm_learner = CommunicationLearner(config, context, db)
    value_learner = ValueLearner(config, context, packet_parser, db)
    
    # 从白名单加载已学习的模型
    # 通信规则
    for rule in whitelist.get('communication_rules', []):
        connection_key = f"{rule['src_ip']}_{rule['dst_ip']}_{rule['dst_port']}_{rule['protocol']}"
        from simulator.model.models import ConnectionObservation
        conn_obs = ConnectionObservation(
            src_ip=rule['src_ip'],
            dst_ip=rule['dst_ip'],
            dst_port=rule['dst_port'],
            protocol=rule['protocol'],
            first_observed=datetime.fromisoformat(rule['first_observed']),
            last_observed=datetime.fromisoformat(rule['last_observed'])
        )
        conn_obs.observation_count = rule['observation_count']
        conn_obs.confidence = rule['confidence']
        conn_obs.approved = True  # 白名单中的连接都是批准的
        conn_obs.avg_packets_per_day = rule.get('avg_packets_per_day', 0.0)
        conn_obs.max_packets_per_minute = rule.get('max_packets_per_minute', 0.0)
        
        comm_learner.connection_observations[connection_key] = conn_obs
    
    context.total_connections_approved = len(comm_learner.connection_observations)
    
    # 值域规则
    for rule in whitelist.get('value_rules', []):
        value_key = ('modbus', rule['address'])  # 假设都是modbus协议
        from simulator.model.models import ValueObservation
        val_obs = ValueObservation(
            address=rule['address'],
            data_type=rule.get('data_type', 'float'),
            tag_name=rule.get('tag_name'),
            unit=rule.get('unit')
        )
        val_obs.baseline_min = rule['min_value']
        val_obs.baseline_max = rule['max_value']
        val_obs.mean = rule['mean']
        val_obs.observation_count = rule['observations']
        
        value_learner.value_observations[value_key] = val_obs
    
    # 初始化流量生成器
    generator = TrafficGenerator(config)
    
    # 定义测试用例
    test_cases = [
        {
            'name': '真实正常连接',
            'type': 'normal',
            'expected': 'pass',
            'description': '已学习的正常通信模式'
        },
        {
            'name': '陌生IP攻击（基于真实目标）',
            'type': 'unknown_ip',
            'expected': 'block',
            'description': '使用陌生IP连接已知目标'
        },
        {
            'name': '端口扫描攻击',
            'type': 'port_scan',
            'expected': 'block',
            'description': '对PLC进行端口扫描'
        },
        {
            'name': '真实正常值域',
            'type': 'normal_value',
            'expected': 'pass',
            'description': '在正常范围内的参数值'
        },
        {
            'name': '异常值攻击',
            'type': 'value_anomaly',
            'expected': 'block',
            'description': '超出正常范围的参数值'
        },
        {
            'name': '陌生地址攻击',
            'type': 'unknown_address',
            'expected': 'block',
            'description': '访问未学习的寄存器地址'
        }
    ]
    
    # 执行测试
    results = []
    
    for test_case in test_cases:
        print(f"\n🧪 执行测试: {test_case['name']}")
        print(f"   类型: {test_case['type']}, 期望: {test_case['expected']}")
        
        test_packets = []
        actual_result = 'unknown'
        
        if test_case['type'] == 'normal':
            # 生成正常流量 - 使用与学习阶段相同的模式
            test_packets = generator.generate_traffic_batch(10)  # 10分钟正常流量
            actual_result = 'pass'  # 默认为通过，后续验证
            
        elif test_case['type'] == 'unknown_ip':
            # 生成来自陌生IP的流量
            normal_packets = generator.generate_traffic_batch(5)
            # 修改部分包的源IP为陌生IP
            for i, (meta, proto) in enumerate(normal_packets):
                if i < len(normal_packets) // 3:  # 修改前1/3的包
                    meta.src_ip = "192.168.99.99"  # 陌生IP
                test_packets.append((meta, proto))
            actual_result = 'block'  # 期望被阻止
            
        elif test_case['type'] == 'port_scan':
            # 生成端口扫描攻击
            test_packets = generator.generate_attack_traffic("recon")
            actual_result = 'block'
            
        elif test_case['type'] == 'normal_value':
            # 生成正常值域流量
            test_packets = generator.generate_traffic_batch(5)
            actual_result = 'pass'
            
        elif test_case['type'] == 'value_anomaly':
            # 生成异常值攻击
            test_packets = generator.generate_attack_traffic("malicious_command")
            actual_result = 'block'
            
        elif test_case['type'] == 'unknown_address':
            # 生成访问陌生地址的流量
            normal_packets = generator.generate_traffic_batch(5)
            # 修改部分包的地址为陌生地址
            for i, (meta, proto) in enumerate(normal_packets):
                if proto and proto.starting_address:
                    # 将地址修改为一个未学习的地址
                    proto.starting_address = 59999  # 假设这是未学习的地址
                test_packets.append((meta, proto))
            actual_result = 'block'
        
        # 验证测试包
        blocked_count = 0
        passed_count = 0
        
        for packet_meta, proto_data in test_packets:
            # 使用学习器验证
            comm_result = comm_learner.validate(packet_meta, proto_data)
            value_result = value_learner.validate(packet_meta, proto_data)
            
            # 如果任一验证失败，则认为被阻止
            if not comm_result['approved'] or not value_result['approved']:
                blocked_count += 1
            else:
                passed_count += 1
        
        # 确定实际结果
        if test_case['type'] in ['port_scan', 'value_anomaly']:
            # 这些是专门生成的攻击流量，应该全部被阻止
            actual_result = 'block' if blocked_count > 0 else 'pass'
        else:
            # 其他测试基于多数包的结果
            actual_result = 'block' if blocked_count > passed_count else 'pass'
        
        # 记录结果
        result = {
            'name': test_case['name'],
            'type': test_case['type'],
            'expected': test_case['expected'],
            'actual': actual_result,
            'passed': test_case['expected'] == actual_result,
            'details': {
                'total_packets': len(test_packets),
                'blocked': blocked_count,
                'passed': passed_count
            }
        }
        
        results.append(result)
        print(f"   结果: {'✅' if result['passed'] else '❌'} {actual_result} "
              f"({blocked_count} 阻止, {passed_count} 通过)")
    
    # 计算总体统计
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['passed'])
    detection_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    # 统计攻击检测情况
    attack_tests = [r for r in results if r['expected'] == 'block']
    detected_attacks = sum(1 for r in attack_tests if r['actual'] == 'block')
    total_attacks = len(attack_tests)
    attack_detection_rate = (detected_attacks / total_attacks) * 100 if total_attacks > 0 else 0
    
    print(f"\n📊 测试总结:")
    print(f"   总体准确率: {detection_rate:.1f}% ({passed_tests}/{total_tests} 测试通过)")
    print(f"   攻击检测率: {attack_detection_rate:.1f}% ({detected_attacks}/{total_attacks} 攻击被检测)")
    
    # 生成测试报告
    report = {
        'test_time': datetime.now().isoformat(),
        'whitelist_source': whitelist_path,
        'whitelist_stats': {
            'communication_rules': len(whitelist.get('communication_rules', [])),
            'value_rules': len(whitelist.get('value_rules', []))
        },
        'test_cases': results,
        'summary': {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'accuracy_rate': detection_rate,
            'attack_detection': {
                'total_attacks': total_attacks,
                'detected_attacks': detected_attacks,
                'detection_rate': attack_detection_rate
            }
        }
    }
    
    # 保存报告
    os.makedirs("outputs", exist_ok=True)
    report_path = "outputs/attack_test_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 攻击检测报告已保存到 {report_path}")
    
    # 打印详细结果
    print(f"\n📋 详细结果:")
    for result in results:
        status = "✅" if result['passed'] else "❌"
        print(f"   {status} {result['name']}: 期望={result['expected']}, 实际={result['actual']}")
    
    print("\n✅ 攻击检测测试完成！")
    print("=" * 60)
    
    return report


def main():
    """主函数"""
    return run_attack_tests()


if __name__ == "__main__":
    main()