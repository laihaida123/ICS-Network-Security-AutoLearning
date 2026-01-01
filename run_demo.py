# Relative Path: run_demo.py
#!/usr/bin/env python3
"""
运行演示
运行一个简短的演示，展示工控自学习系统的核心功能
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

def run_demo():
    """运行演示"""
    print("🏭 工控自学习系统 - 演示版")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    print(f"⚙️  使用配置: config.yaml")
    
    # 创建输出目录
    os.makedirs("outputs", exist_ok=True)
    
    # 初始化学习上下文（2小时学习）
    context = LearningContext(
        mode='training',
        start_time=datetime.now(),
        duration_days=1,  # 实际上我们只学习2小时，但设置为1天
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
    
    print("🚀 开始学习阶段（2小时模拟）")
    print("-" * 40)
    
    # 模拟2小时的流量（实际运行时间会更快）
    total_minutes = 120
    batch_minutes = 10  # 每次处理10分钟的流量
    
    processed_minutes = 0
    while processed_minutes < total_minutes:
        # 计算当前批次的时长
        current_batch = min(batch_minutes, total_minutes - processed_minutes)
        
        # 生成一批流量
        packets = generator.generate_traffic_batch(current_batch)
        
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
        processed_minutes += current_batch
        progress = processed_minutes / total_minutes * 100
        print(f"📊 进度: {progress:.1f}% ({processed_minutes}/{total_minutes}) "
              f"- 已处理 {context.total_packets_processed} 个数据包")
    
    print("\n✅ 学习阶段完成")
    
    # 完成学习
    comm_result = comm_learner.finalize_learning()
    value_result = value_learner.finalize_learning()
    
    print(f"📈 通信学习结果: {comm_result['total_connections']} 个连接, "
          f"{comm_result['approved_connections']} 个批准")
    print(f"📈 值域学习结果: {value_result['total_parameters']} 个参数, "
          f"{value_result['valid_models']} 个有效模型")
    
    # 生成白名单
    print("\n📋 生成白名单...")
    whitelist = {
        'generated_at': datetime.now().isoformat(),
        'learning_duration_hours': 2,
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
            'confidence': conn.confidence,
            'observation_count': conn.observation_count
        })
    
    # 添加值域规则
    for (protocol, address), value_obs in value_learner.value_observations.items():
        if value_obs.observation_count >= value_learner.min_value_observations and value_obs.baseline_min is not None:
            whitelist['value_rules'].append({
                'address': value_obs.address,
                'min_value': value_obs.baseline_min,
                'max_value': value_obs.baseline_max,
                'mean': value_obs.mean,
                'std_dev': value_obs.std_dev,
                'observations': value_obs.observation_count
            })
    
    # 保存白名单
    whitelist_path = "outputs/demo_whitelist.json"
    with open(whitelist_path, 'w', encoding='utf-8') as f:
        json.dump(whitelist, f, indent=2, ensure_ascii=False)
    
    print(f"💾 白名单已保存到 {whitelist_path}")
    print(f"   - {len(whitelist['communication_rules'])} 个通信规则")
    print(f"   - {len(whitelist['value_rules'])} 个值域规则")
    
    # 简单验证测试
    print("\n🔍 运行验证测试...")
    
    # 生成一些正常流量进行测试
    test_packets = generator.generate_traffic_batch(5)  # 5分钟测试流量
    
    valid_count = 0
    invalid_count = 0
    
    for packet_meta, proto_data in test_packets:
        # 测试通信验证
        comm_result = comm_learner.validate(packet_meta, proto_data)
        value_result = value_learner.validate(packet_meta, proto_data)
        
        if comm_result['approved'] and value_result['approved']:
            valid_count += 1
        else:
            invalid_count += 1
    
    print(f"✅ 验证结果: {valid_count} 个有效, {invalid_count} 个无效")
    
    # 生成学习报告
    report = {
        'demo_time': datetime.now().isoformat(),
        'total_packets_processed': context.total_packets_processed,
        'total_connections_observed': context.total_sessions_observed,
        'approved_connections': len(whitelist['communication_rules']),
        'value_rules': len(whitelist['value_rules']),
        'validation_results': {
            'test_packets': len(test_packets),
            'valid_packets': valid_count,
            'invalid_packets': invalid_count
        }
    }
    
    report_path = "outputs/demo_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"📊 学习报告已保存到 {report_path}")
    
    print("\n🎉 演示完成！")
    print("=" * 60)

if __name__ == "__main__":
    run_demo()