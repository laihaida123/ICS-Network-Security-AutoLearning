#!/usr/bin/env python3
"""
值域学习专项修复 - 确保地址范围正确
"""

import yaml
from datetime import datetime
import sys
from pathlib import Path
import random

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from simulator.data_generator import TrafficGenerator
from simulator.packet_parser import PacketParser
from simulator.model.models import LearningContext
from simulator.learner.comm_learner import CommunicationLearner
from simulator.learner.value_learner import ValueLearner

def main():
    print("🎯 值域学习专项修复")
    print("=" * 60)
    
    # 1. 加载配置并强制修改地址生成逻辑
    with open('config_powerful.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 强制确保地址范围正确
    print("\n🔧 强制设置地址范围:")
    config['simulation']['data_types']['temperature']['address_range'] = [40001, 40005]  # 只学5个地址！
    print(f"   地址范围: {config['simulation']['data_types']['temperature']['address_range']}")
    
    # 2. 创建学习上下文（更宽松）
    context = LearningContext(
        mode='training',
        start_time=datetime.now(),
        duration_days=1,
        min_observation_count=2,  # 更宽松：看到2次就算
        min_observation_days=1
    )
    
    # 3. 初始化组件
    print("\n🚀 初始化组件...")
    generator = TrafficGenerator(config)
    parser = PacketParser(config)
    comm_learner = CommunicationLearner(config, context, db=None)
    value_learner = ValueLearner(config, context, parser, db=None)
    
    # 4. 模拟2小时流量，专门学习值域
    print("\n📊 专项值域学习（2小时）...")
    
    # 方法：生成少量但集中的流量
    for hour in range(2):
        print(f"\n小时 {hour+1}/2:")
        
        # 生成流量
        packets = []
        for _ in range(300):  # 少量但重复的流量
            # 手动创建一个简单的数据包
            from simulator.model.models import PacketMetadata, ProtocolData
            
            # 固定几个地址重复出现
            target_address = 40001 + (hour * 2)  # 小时1:40001,40002；小时2:40003,40004
            
            packet_meta = PacketMetadata(
                timestamp=datetime.now(),
                src_ip="192.168.1.100",
                dst_ip="192.168.1.10",
                dst_port=502,
                protocol="modbus",
                packet_len=100,
                direction="request"
            )
            
            proto_data = ProtocolData(
                protocol_type="modbus",
                function_code=3,  # 读寄存器
                starting_address=target_address,
                quantity=1,
                values=[random.uniform(20.0, 80.0)]  # 温度值
            )
            
            packets.append((packet_meta, proto_data))
        
        # 学习这些数据包
        for packet_meta, proto_data in packets:
            value_learner.learn(packet_meta, proto_data)
        
        print(f"  已学习 {len(packets)} 个数据包")
        
        # 检查学习进度
        param_count = 0
        for (protocol, addr), val_obs in value_learner.value_observations.items():
            if val_obs.observation_count >= 3:  # 达到最小样本数
                param_count += 1
        
        print(f"  已达到3次观测的参数: {param_count} 个")
    
    # 5. 完成学习并展示结果
    print("\n🎯 完成值域学习...")
    value_result = value_learner.finalize_learning()
    
    print(f"\n✅ 值域学习结果:")
    print(f"   有效模型: {value_result['valid_models']} 个")
    print(f"   样本不足: {value_result['invalid_models']} 个")
    
    # 显示学习到的值域规则
    if value_result['valid_models'] > 0:
        print("\n📈 学习到的值域规则:")
        for (protocol, addr), val_obs in value_learner.value_observations.items():
            if val_obs.observation_count >= 3 and val_obs.baseline_min is not None:
                print(f"   地址 {addr}: {val_obs.baseline_min:.1f}°C ~ {val_obs.baseline_max:.1f}°C")
                print(f"     观测次数: {val_obs.observation_count}, 均值: {val_obs.mean:.1f}°C")
    
    # 6. 保存结果
    import json
    outputs_dir = Path('outputs')
    outputs_dir.mkdir(exist_ok=True)
    
    value_rules = []
    for (protocol, addr), val_obs in value_learner.value_observations.items():
        if val_obs.observation_count >= 3 and val_obs.baseline_min is not None:
            value_rules.append({
                'address': addr,
                'min_value': round(val_obs.baseline_min, 2),
                'max_value': round(val_obs.baseline_max, 2),
                'mean': round(val_obs.mean, 2),
                'observations': val_obs.observation_count
            })
    
    result = {
        'generated_at': datetime.now().isoformat(),
        'valid_value_rules': len(value_rules),
        'value_rules': value_rules
    }
    
    with open('outputs/value_rules_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 结果保存到: outputs/value_rules_fixed.json")

if __name__ == "__main__":
    main()