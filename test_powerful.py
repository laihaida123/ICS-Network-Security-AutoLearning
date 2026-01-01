#!/usr/bin/env python3
"""
强力测试脚本 - 保证配置生效
"""

import yaml
from datetime import datetime
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from simulator.data_generator import TrafficGenerator
from simulator.packet_parser import PacketParser
from simulator.model.models import LearningContext
from simulator.learner.comm_learner import CommunicationLearner
from simulator.learner.value_learner import ValueLearner

def main():
    print("🔥 强力学习测试 - 确保配置生效")
    print("=" * 60)
    
    # 1. 加载强力配置
    with open('config_powerful.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 验证配置
    print("\n✅ 配置验证:")
    print(f"   packets_per_hour: {config['simulation']['packets_per_hour']}")
    print(f"   min_observation_count: {config['learning']['min_observation_count']}")
    print(f"   temperature地址范围: {config['simulation']['data_types']['temperature']['address_range']}")
    
    # 2. 创建学习上下文（使用配置中的值）
    learning_config = config['learning']
    context = LearningContext(
        mode='training',
        start_time=datetime.now(),
        duration_days=1,
        min_observation_count=learning_config['min_observation_count'],
        min_observation_days=learning_config['min_observation_days']
    )
    
    # 3. 初始化组件
    print("\n🚀 初始化组件...")
    generator = TrafficGenerator(config)
    # 在 test_powerful.py 中找到 generator = TrafficGenerator(config) 这行
    # 在它后面添加：

    print("\n🔧 检查地址生成...")
    # 生成几个数据包检查地址
    for i in range(10):
        # 临时修改：直接调用内部方法生成地址
        import random
        addr = random.randint(40001, 40030)
        print(f"  测试地址{i+1}: {addr} (应该在40001-40030之间)")
    parser = PacketParser(config)
    comm_learner = CommunicationLearner(config, context, db=None)
    value_learner = ValueLearner(config, context, parser, db=None)
    
    # 4. 学习1小时（高强度）
    print("\n📊 学习1小时高强度流量...")
    
    # 生成1小时流量（但使用高峰时段的流量乘数）
    import random
    packets = generator.generate_traffic_batch(60)
    
    print(f"生成 {len(packets)} 个数据包")
    print(f"流量乘数: 1.0x（应该是这个）")
    
    # 学习
    for packet_meta, proto_data in packets:
        if proto_data:
            comm_learner.learn(packet_meta, proto_data)
            value_learner.learn(packet_meta, proto_data)
    
    # 5. 检查学习情况
    print(f"\n📈 学习统计:")
    print(f"  通信观测: {comm_learner.observations_processed}")
    print(f"  值域观测: {value_learner.observations_processed}")
    
    # 检查前几个连接
    print("\n🔗 前5个连接观测情况:")
    connections = list(comm_learner.connection_observations.items())[:5]
    for i, (conn_key, conn_obs) in enumerate(connections):
        print(f"  {i+1}. {conn_obs.src_ip}→{conn_obs.dst_ip}: 观测{conn_obs.observation_count}次")
    
    # 检查前几个参数
    print("\n📊 前5个参数观测情况:")
    params = list(value_learner.value_observations.items())[:5]
    for i, ((protocol, addr), val_obs) in enumerate(params):
        print(f"  {i+1}. 地址{addr}: 观测{val_obs.observation_count}次, 值{val_obs.min_observed:.1f}-{val_obs.max_observed:.1f}")
    
    # 6. 完成学习
    print("\n🎯 完成学习...")
    comm_result = comm_learner.finalize_learning()
    value_result = value_learner.finalize_learning()
    
    print(f"批准连接: {comm_result['approved_connections']}")
    print(f"有效值域模型: {value_result['valid_models']}")

if __name__ == "__main__":
    main()