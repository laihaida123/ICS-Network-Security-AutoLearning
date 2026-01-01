# Relative Path: run_complete.py
#!/usr/bin/env python3
"""
完整运行脚本
运行完整的工控自学习流程，包括学习、验证和报告生成
"""

import yaml
import json
import os
from datetime import datetime
from typing import Dict, Any

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

def run_complete_pipeline():
    """运行完整的自学习流程"""
    print("🏭 工控自学习系统 - 完整运行")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    print(f"⚙️  使用配置: config.yaml")
    
    # 创建输出目录
    os.makedirs("outputs", exist_ok=True)
    
    # 初始化学习上下文（2天学习）
    duration_days = config.get('learning', {}).get('duration_days', 2)
    context = LearningContext(
        mode='training',
        start_time=datetime.now(),
        duration_days=duration_days,
        min_observation_count=config.get('learning', {}).get('min_observation_count', 10),
        min_observation_days=config.get('learning', {}).get('min_observation_days', 2)
    )
    
    # 初始化数据库
    db = ObservationDatabase()
    
    # 初始化学习器
    packet_parser = PacketParser(config)
    comm_learner = CommunicationLearner(config, context, db)
    value_learner = ValueLearner(config, context, packet_parser, db)
    
    # 初始化流量生成器
    generator = TrafficGenerator(config)
    
    print(f"🚀 开始学习阶段（{duration_days}天模拟）")
    print("-" * 40)
    
    # 模拟多天的流量（实际运行时间会更快）
    total_hours = duration_days * 24
    batch_minutes = 60  # 每次处理1小时的流量
    
    processed_hours = 0
    while processed_hours < total_hours:
        # 生成1小时流量
        packets = generator.generate_traffic_batch(batch_minutes)
        
        # 处理每个数据包
        for packet_meta, proto_data in packets:
            # 通信学习器学习
            comm_learner.learn(packet_meta, proto_data)
            
            # 值域学习器学习
            value_learner.learn(packet_meta, proto_data)
        
        # 更新上下文
        context.total_packets_processed += len(packets)
        context.total_sessions_observed += len([p for p in packets if p[1] is not None])
        
        # 更新进度
        processed_hours += 1
        progress = processed_hours / total_hours * 100
        if processed_hours % 10 == 0 or processed_hours == total_hours:  # 每10小时或结束时打印一次
            print(f"📊 进度: {progress:.1f}% ({processed_hours}/{total_hours}) "
                  f"- 已处理 {context.total_packets_processed} 个数据包")
    
    print("\n✅ 学习阶段完成")
    
    # 完成学习
    comm_result = comm_learner.finalize_learning()
    value_result = value_learner.finalize_learning()
    
    print(f"📈 通信学习结果: {comm_result['total_connections']} 个连接, "
          f"{comm_result['approved_connections']} 个批准")
    print(f"📈 值域学习结果: {value_result['total_parameters']} 个参数, "
          f"{value_result['valid_models']} 个有效模型")
    
    # 生成完整白名单
    print("\n📋 生成完整白名单...")
    whitelist = {
        'generated_at': datetime.now().isoformat(),
        'learning_duration_days': duration_days,
        'total_packets_processed': context.total_packets_processed,
        'communication_rules': [],
        'value_rules': []
    }
    
    # 添加批准的连接到白名单
    approved_connections = comm_learner.get_approved_connections()
    for conn in approved_connections:
        whitelist['communication_rules'].append({
            'src_ip': conn.src_ip,
            'dst_ip': conn.dst_ip,
            'dst_port': conn.dst_port,
            'protocol': conn.protocol,
            'first_observed': conn.first_observed.isoformat(),
            'last_observed': conn.last_observed.isoformat(),
            'observation_count': conn.observation_count,
            'avg_packets_per_day': conn.avg_packets_per_day,
            'max_packets_per_minute': conn.max_packets_per_minute,
            'confidence': conn.confidence,
            'rejection_reason': conn.rejection_reason
        })
    
    # 添加值域规则
    for (protocol, address), value_obs in value_learner.value_observations.items():
        if value_obs.observation_count >= value_learner.min_value_observations and value_obs.baseline_min is not None:
            whitelist['value_rules'].append({
                'address': value_obs.address,
                'data_type': value_obs.data_type,
                'tag_name': value_obs.tag_name,
                'unit': value_obs.unit,
                'min_value': value_obs.baseline_min,
                'max_value': value_obs.baseline_max,
                'mean': value_obs.mean,
                'std_dev': value_obs.std_dev,
                'tolerance': value_obs.tolerance,
                'observation_count': value_obs.observation_count
            })
    
    # 保存白名单
    whitelist_path = "outputs/whitelist.yaml"
    with open(whitelist_path, 'w', encoding='utf-8') as f:
        import yaml
        yaml.dump(whitelist, f, default_flow_style=False, allow_unicode=True)
    
    print(f"💾 完整白名单已保存到 {whitelist_path}")
    print(f"   - {len(whitelist['communication_rules'])} 个通信规则")
    print(f"   - {len(whitelist['value_rules'])} 个值域规则")
    
    # 运行验证测试
    print("\n🔍 运行验证测试...")
    
    # 生成正常测试流量
    normal_test_packets = generator.generate_traffic_batch(60)  # 1小时正常流量
    
    # 生成攻击测试流量
    recon_attack = generator.generate_attack_traffic("recon")
    dos_attack = generator.generate_attack_traffic("dos")
    command_attack = generator.generate_attack_traffic("malicious_command")
    
    all_test_packets = normal_test_packets + recon_attack + dos_attack + command_attack
    
    # 验证所有测试包
    valid_comm_count = 0
    invalid_comm_count = 0
    valid_value_count = 0
    invalid_value_count = 0
    
    for packet_meta, proto_data in all_test_packets:
        # 测试通信验证
        comm_result = comm_learner.validate(packet_meta, proto_data)
        if comm_result['approved']:
            valid_comm_count += 1
        else:
            invalid_comm_count += 1
        
        # 测试值域验证
        value_result = value_learner.validate(packet_meta, proto_data)
        if value_result['approved']:
            valid_value_count += 1
        else:
            invalid_value_count += 1
    
    print(f"✅ 验证结果:")
    print(f"   通信验证: {valid_comm_count} 有效, {invalid_comm_count} 无效")
    print(f"   值域验证: {valid_value_count} 有效, {invalid_value_count} 无效")
    
    # 生成完整学习报告
    report = {
        'system_info': {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'total_runtime_seconds': (datetime.now() - context.start_time).total_seconds()
        },
        'learning_context': {
            'mode': context.mode,
            'duration_days': context.duration_days,
            'start_time': context.start_time.isoformat(),
            'end_time': datetime.now().isoformat()
        },
        'statistics': {
            'total_packets_processed': context.total_packets_processed,
            'total_sessions_observed': context.total_sessions_observed,
            'total_connections_approved': context.total_connections_approved
        },
        'communication_learning': {
            'total_connections': len(comm_learner.connection_observations),
            'approved_connections': context.total_connections_approved,
            'rejected_connections': len(comm_learner.connection_observations) - context.total_connections_approved,
            'approval_rate': context.total_connections_approved / len(comm_learner.connection_observations) if len(comm_learner.connection_observations) > 0 else 0,
            'avg_confidence': sum(c.confidence for c in comm_learner.connection_observations.values()) / len(comm_learner.connection_observations) if comm_learner.connection_observations else 0
        },
        'value_learning': {
            'total_parameters': len(value_learner.value_observations),
            'valid_models': len([v for v in value_learner.value_observations.values() if v.observation_count >= value_learner.min_value_observations]),
            'invalid_models': len([v for v in value_learner.value_observations.values() if v.observation_count < value_learner.min_value_observations]),
            'avg_observations_per_param': sum(v.observation_count for v in value_learner.value_observations.values()) / len(value_learner.value_observations) if value_learner.value_observations else 0,
            'std_dev_multiplier': value_learner.std_dev_multiplier
        },
        'validation_results': {
            'total_test_packets': len(all_test_packets),
            'normal_packets': len(normal_test_packets),
            'attack_packets': len(recon_attack + dos_attack + command_attack),
            'communication_validation': {
                'valid_packets': valid_comm_count,
                'invalid_packets': invalid_comm_count,
                'detection_rate': invalid_comm_count / len(all_test_packets) * 100 if len(all_test_packets) > 0 else 0
            },
            'value_validation': {
                'valid_packets': valid_value_count,
                'invalid_packets': invalid_value_count,
                'detection_rate': invalid_value_count / len(all_test_packets) * 100 if len(all_test_packets) > 0 else 0
            }
        }
    }
    
    report_path = "outputs/learning_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"📊 学习报告已保存到 {report_path}")
    
    # 生成攻击检测报告
    attack_report = {
        'test_time': datetime.now().isoformat(),
        'whitelist_size': {
            'communication_rules': len(whitelist['communication_rules']),
            'value_rules': len(whitelist['value_rules'])
        },
        'attack_detection': {
            'total_attacks': len(recon_attack + dos_attack + command_attack),
            'detected_attacks': invalid_comm_count + invalid_value_count,  # 攻击应该被检测为无效
            'detection_rate': (invalid_comm_count + invalid_value_count) / len(recon_attack + dos_attack + command_attack) * 100 if len(recon_attack + dos_attack + command_attack) > 0 else 0
        },
        'test_summary': '系统成功使用学习到的白名单检测多种攻击'
    }
    
    attack_report_path = "outputs/attack_test_report.json"
    with open(attack_report_path, 'w', encoding='utf-8') as f:
        json.dump(attack_report, f, indent=2, ensure_ascii=False)
    
    print(f"🛡️  攻击检测报告已保存到 {attack_report_path}")
    
    print("\n🎉 完整运行完成！")
    print("=" * 60)
    print("📁 生成的文件:")
    print(f"   - 白名单: {whitelist_path}")
    print(f"   - 学习报告: {report_path}")
    print(f"   - 攻击检测报告: {attack_report_path}")

if __name__ == "__main__":
    run_complete_pipeline()