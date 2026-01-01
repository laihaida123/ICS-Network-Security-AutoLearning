# Relative Path: quick_run.py
#!/usr/bin/env python3
"""
超快速演示 - 只学习2小时，不保存数据库
"""

import yaml
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入必要模块
from simulator.data_generator import TrafficGenerator
from simulator.packet_parser import PacketParser
from simulator.model.models import LearningContext
from simulator.learner.comm_learner import CommunicationLearner
from simulator.learner.value_learner import ValueLearner

def quick_learning():
    """快速学习演示"""
    print("⚡ 超快速学习演示 - 只学2小时")
    print("=" * 50)
    
    # 1. 加载配置
    with open('config_powerful.yaml', 'r', encoding='utf-8') as f:
        # 在 with open(...) 语句后面添加：
        print(f"\n🔧 配置验证:")
        print(f"   packets_per_hour: {config.get('simulation', {}).get('packets_per_hour', '未找到')}")
        print(f"   min_observation_count: {config.get('learning', {}).get('min_observation_count', '未找到')}")
        config = yaml.safe_load(f)
    
    # 2. 修改配置为快速模式
    config['simulation']['packets_per_hour'] = 200  # 减少流量
    config['learning']['min_observation_count'] = 5  # 降低要求
    config['learning']['min_observation_days'] = 1   # 只需1天
    
    # 3. 创建学习上下文（只学1天）
    context = LearningContext(
        mode='training',
        start_time=datetime.now(),
        duration_days=1,
        min_observation_count=5,
        min_observation_days=1
    )
    
    # 4. 初始化组件（不创建数据库）
    print("初始化组件...")
    generator = TrafficGenerator(config)
    parser = PacketParser(config)
    
    # 创建学习器，不传递数据库参数（None）
    comm_learner = CommunicationLearner(config, context, db=None)
    value_learner = ValueLearner(config, context, parser, db=None)
    
    # 5. 只模拟2小时的流量（而不是24小时）
    print("\n模拟2小时流量学习...")
    total_packets = 0
    
    for hour in range(2):  # 只学2小时
        print(f"\n小时 {hour+1}/2:")
        
        # 生成1小时流量
        packets = generator.generate_traffic_batch(60)
        print(f"  生成 {len(packets)} 个数据包")
        
        # 学习每个数据包
        for packet_meta, proto_data in packets:
            if proto_data:  # 只处理有协议数据的包
                comm_learner.learn(packet_meta, proto_data)
                value_learner.learn(packet_meta, proto_data)
                total_packets += 1
        
        print(f"  已学习 {total_packets} 个数据包")
        print(f"  通信关系: {comm_learner.observations_processed} 个观测")
        print(f"  值域学习: {value_learner.observations_processed} 个观测")
    
    # 6. 完成学习并生成白名单
    print("\n" + "=" * 50)
    print("完成学习，生成白名单...")
    
    # 完成学习
    comm_result = comm_learner.finalize_learning()
    value_result = value_learner.finalize_learning()
    
    # 在学习循环后添加这段代码（大约在第60行附近）
    print("\n🔍 详细学习进展检查:")
    print("=" * 40)

    # 检查通信学习
    print("1. 通信学习情况:")
    for i, (conn_key, conn_obs) in enumerate(list(comm_learner.connection_observations.items())[:5]):
        print(f"   连接{i+1}: {conn_obs.src_ip}→{conn_obs.dst_ip}:{conn_obs.dst_port}")
        print(f"     观测次数: {conn_obs.observation_count}, 天数: {(conn_obs.last_observed - conn_obs.first_observed).days + 1}")

    # 检查值域学习
    print("\n2. 值域学习情况:")
    for i, ((protocol, addr), val_obs) in enumerate(list(value_learner.value_observations.items())[:5]):
        print(f"   参数{i+1}: 地址{addr}, 类型{val_obs.data_type}")
        print(f"     观测次数: {val_obs.observation_count}, 值范围: {val_obs.min_observed:.1f}-{val_obs.max_observed:.1f}")
    # 7. 生成白名单文件
    import json
    
    # 收集批准的连接
    approved_connections = []
    for conn_key, conn_obs in comm_learner.connection_observations.items():
        if conn_obs.approved:
            approved_connections.append({
                'src_ip': conn_obs.src_ip,
                'dst_ip': conn_obs.dst_ip,
                'dst_port': conn_obs.dst_port,
                'protocol': conn_obs.protocol,
                'observation_count': conn_obs.observation_count,
                'confidence': conn_obs.confidence
            })
    
    # 收集值域规则
    value_rules = []
    for (protocol, address), val_obs in value_learner.value_observations.items():
        if val_obs.observation_count >= 5:  # 最少5个样本
            value_rules.append({
                'address': address,
                'protocol': protocol,
                'tag_name': val_obs.tag_name,
                'min_value': round(val_obs.min_observed, 2) if val_obs.min_observed else None,
                'max_value': round(val_obs.max_observed, 2) if val_obs.max_observed else None,
                'mean': round(val_obs.mean, 2) if val_obs.mean else None,
                'observation_count': val_obs.observation_count
            })
    
    # 创建输出目录
    outputs_dir = Path('outputs')
    outputs_dir.mkdir(exist_ok=True)
    
    # 保存为JSON（比YAML简单）
    whitelist = {
        'generated_at': datetime.now().isoformat(),
        'learning_hours': 2,
        'total_packets_learned': total_packets,
        'approved_connections': approved_connections,
        'value_rules': value_rules
    }
    
    with open('outputs/quick_whitelist.json', 'w', encoding='utf-8') as f:
        json.dump(whitelist, f, indent=2, ensure_ascii=False)
    
    # 8. 输出结果
    print("\n" + "=" * 50)
    print("✅ 学习完成！")
    print(f"📊 统计:")
    print(f"   总数据包: {total_packets}")
    print(f"   批准连接: {len(approved_connections)} 个")
    print(f"   值域规则: {len(value_rules)} 个")
    print(f"\n📁 白名单已保存: outputs/quick_whitelist.json")
    print("=" * 50)
    
    # 显示几个例子
    if approved_connections:
        print("\n🔗 批准的连接示例:")
        for conn in approved_connections[:3]:  # 显示前3个
            print(f"   {conn['src_ip']} → {conn['dst_ip']}:{conn['dst_port']} ({conn['protocol']})")
    
    if value_rules:
        print("\n📈 值域规则示例:")
        for rule in value_rules[:3]:  # 显示前3个
            if rule['min_value'] is not None and rule['max_value'] is not None:
                print(f"   地址 {rule['address']}: {rule['min_value']} ~ {rule['max_value']}")

if __name__ == "__main__":
    quick_learning()