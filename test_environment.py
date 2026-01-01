#!/usr/bin/env python3
"""
环境测试脚本
验证所有模块是否能正常导入和初始化
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("开始测试模块导入...")
    print("=" * 60)
    
    try:
        # 1. 测试配置加载
        import yaml  # 从PyYAML包导入
        print("✓ PyYAML 导入成功")
        
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("✓ 配置文件加载成功")
        print(f"  学习模式: {config.get('learning', {}).get('mode', '未找到')}")
        print(f"  学习天数: {config.get('learning', {}).get('duration_days', 0)}")
        
        # 2. 测试数据模型
        from simulator.model import models
        print("✓ 数据模型模块导入成功")
        
        # 测试创建PacketMetadata实例
        pm = models.PacketMetadata(
            timestamp=datetime.now(),
            src_ip="192.168.1.100",
            dst_ip="192.168.1.10",
            dst_port=502,
            protocol="modbus",
            packet_len=64,
            direction="request"
        )
        print(f"✓ 创建PacketMetadata实例: {pm.src_ip}:{pm.dst_port}")
        
        # 测试转换为字典
        pm_dict = pm.to_dict()
        print(f"✓ 数据模型序列化成功: {pm_dict['protocol']}")
        
        # 3. 测试数据库模块
        from simulator.model import database
        print("✓ 数据库模块导入成功")
        
        # 测试数据库连接（使用内存数据库避免文件创建）
        test_db = database.ObservationDatabase(":memory:")
        print("✓ 数据库连接测试成功")
        
        # 4. 测试流量生成器
        from simulator import data_generator
        print("✓ 流量生成器模块导入成功")
        
        # 测试流量生成器初始化
        generator = data_generator.TrafficGenerator(config)
        print(f"✓ 流量生成器初始化成功")
        print(f"  PLC数量: {len(generator.plc_ips)}")
        print(f"  HMI数量: {len(generator.hmi_ips)}")
        
        # 测试生成流量
        packets = generator.generate_traffic_batch(1)  # 生成1分钟的流量
        print(f"✓ 流量生成测试成功，生成 {len(packets)} 个数据包")
        
        # 5. 测试协议数据
        from simulator.model.models import ProtocolData, ConnectionObservation, ValueObservation
        print("✓ 所有核心数据类导入成功")
        
        # 测试协议数据创建
        proto_data = ProtocolData(
            protocol_type="modbus",
            function_code=3,
            starting_address=40001
        )
        print(f"✓ 协议数据创建成功: {proto_data.protocol_type}")
        
        # 测试连接观测
        conn_obs = ConnectionObservation(
            src_ip="192.168.1.100",
            dst_ip="192.168.1.10",
            dst_port=502,
            protocol="modbus",
            first_observed=datetime.now(),
            last_observed=datetime.now()
        )
        conn_obs.update(64, datetime.now())
        print(f"✓ 连接观测创建成功: {conn_obs.observation_count} 次观测")
        
        # 测试值域观测
        val_obs = ValueObservation(
            address=40001,
            data_type="float"
        )
        val_obs.add_observation(25.5, datetime.now())
        val_obs.calculate_baseline()
        print(f"✓ 值域观测创建成功: 均值={val_obs.mean:.2f}, 标准差={val_obs.std_dev:.2f}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！环境运行正常。")
        print("=" * 60)
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请检查依赖是否安装: poetry install")
        return False
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("请确保 config.yaml 文件存在")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_poetry_environment():
    """测试Poetry环境"""
    print("\n" + "=" * 60)
    print("测试Poetry环境...")
    print("=" * 60)
    
    try:
        import pkg_resources
        
        # 检查关键依赖
        required_packages = [
            'yaml',
            'sqlite3',
            'scapy',
            'numpy',
            'pandas'
        ]
        
        for pkg in required_packages:
            try:
                dist = pkg_resources.get_distribution(pkg if pkg != 'yaml' else 'pyyaml')
                print(f"✓ {dist.project_name} ({dist.version})")
            except pkg_resources.DistributionNotFound:
                print(f"⚠  {pkg} 未找到，可能需要安装")
                
        print("✓ Poetry环境检查完成")
        return True
        
    except Exception as e:
        print(f"❌ 环境检查失败: {e}")
        return False

def run_demo():
    """运行一个简单的演示"""
    print("\n" + "=" * 60)
    print("运行简单演示...")
    print("=" * 60)
    
    try:
        import yaml
        from simulator import data_generator
        from simulator.model import database
        from datetime import datetime
        
        # 加载配置 - 使用基于脚本位置的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 创建生成器
        gen = data_generator.TrafficGenerator(config)
        
        # 生成5分钟的正常流量
        print("生成5分钟正常流量...")
        normal_packets = gen.generate_traffic_batch(5)
        print(f"生成 {len(normal_packets)} 个数据包")
        
        # 生成攻击流量
        print("\n生成攻击流量...")
        attack_packets = gen.generate_attack_traffic("recon")
        print(f"生成 {len(attack_packets)} 个攻击数据包")
        
        # 创建数据库并保存一些数据
        print("\n测试数据存储...")
        db = database.ObservationDatabase("test_demo.db")
        
        # 保存一些数据包
        for i, (packet_meta, proto_data) in enumerate(normal_packets[:10]):
            parsed_data = {
                'function_code': proto_data.function_code if proto_data else None,
                'address': proto_data.starting_address if proto_data else None
            } if proto_data else None
            
            db.save_packet_metadata(packet_meta, parsed_data)
        
        print(f"保存了10个数据包到数据库")
        
        # 获取统计信息
        stats = db.get_connection_stats(24)
        print(f"数据库统计: {stats['total_packets']} 个包, {stats['unique_connections']} 个连接")
        
        print("\n✅ 演示运行成功！")
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("工控自学习系统 - 环境测试")
    print(f"Python版本: {sys.version}")
    print(f"当前目录: {os.getcwd()}")
    print(f"Poetry环境: {'已激活' if 'VIRTUAL_ENV' in os.environ else '未检测到'}")
    
    # 运行测试
    all_passed = True
    
    # 测试Poetry环境
    if not test_poetry_environment():
        all_passed = False
    
    # 测试模块导入
    if not test_imports():
        all_passed = False
    
    # 运行演示（可选）
    if all_passed:
        run_demo()
    
    # 最终结果
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！可以开始后续开发。")
        print("\n下一步建议：")
        print("1. 运行 'poetry run python test_environment.py' 确认无错误")
        print("2. 告诉我你需要哪个模块的代码，我将继续提供")
        print("3. 推荐的顺序：packet_parser.py → base_learner.py → comm_learner.py")
    else:
        print("❌ 测试失败，请检查上述错误信息")
        print("\n常见问题解决：")
        print("1. 确保在项目根目录运行")
        print("2. 确保已运行 'poetry install'")
        print("3. 检查 config.yaml 文件是否存在")
        print("4. 检查目录结构是否正确")
    
    print("=" * 60)