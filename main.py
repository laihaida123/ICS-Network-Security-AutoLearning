# Relative Path: main.py
#!/usr/bin/env python3
"""
工控自学习系统主程序
整合所有模块，实现完整的自学习流程
"""

import os
import sys
import time
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from simulator.data_generator import TrafficGenerator
from simulator.packet_parser import PacketParser
from simulator.model.models import LearningContext, PacketMetadata, ProtocolData
from simulator.model.database import ObservationDatabase
from simulator.learner.comm_learner import CommunicationLearner
from simulator.learner.value_learner import ValueLearner

class ICSLearningSystem:
    """
    工控自学习系统主类
    管理整个学习流程：从流量模拟到白名单生成
    """
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        初始化学习系统
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        
        # 创建输出目录
        self._create_directories()
        
        # 系统组件
        self.generator = None
        self.parser = None
        self.database = None
        self.context = None
        self.comm_learner = None
        self.value_learner = None
        
        # 系统状态
        self.is_running = False
        self.start_time = None
        self.total_packets_processed = 0
        
        print("=" * 60)
        print("工控自学习系统 v1.0")
        print("=" * 60)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            print(f"[系统] 配置文件加载成功: {self.config_file}")
            return config
            
        except FileNotFoundError:
            print(f"[错误] 配置文件未找到: {self.config_file}")
            print("请确保 config.yaml 文件存在")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"[错误] 配置文件格式错误: {e}")
            sys.exit(1)
    
    def _create_directories(self):
        """创建必要的目录"""
        directories = ['outputs', 'data', 'logs', 'models']
        
        for dir_name in directories:
            dir_path = Path(project_root) / dir_name
            dir_path.mkdir(exist_ok=True)
            print(f"[系统] 目录已创建/确认: {dir_path}")
    
    def initialize_system(self):
        """初始化系统所有组件"""
        print("\n[系统] 正在初始化组件...")
        
        # 1. 创建学习上下文
        learning_config = self.config.get('learning', {})
        self.context = LearningContext(
            mode=learning_config.get('mode', 'training'),
            start_time=datetime.now(),
            duration_days=learning_config.get('duration_days', 7),
            min_observation_count=learning_config.get('min_observation_count', 10),
            min_observation_days=learning_config.get('min_observation_days', 2)
        )
        
        # 2. 初始化数据库
        db_config = self.config.get('database', {})
        db_file = db_config.get('file', 'data/observations.db')
        self.database = ObservationDatabase(db_file)
        
        # 3. 初始化流量生成器
        self.generator = TrafficGenerator(self.config)
        
        # 4. 初始化数据包解析器
        self.parser = PacketParser(self.config)
        
        # 5. 初始化学习器
        self.comm_learner = CommunicationLearner(self.config, self.context, self.database)
        self.value_learner = ValueLearner(self.config, self.context, self.parser, self.database)
        
        print("[系统] 所有组件初始化完成 ✓")
    
    def run_learning_phase(self, simulated_days: int = None):
        """
        运行学习阶段
        
        Args:
            simulated_days: 模拟学习的天数（如果为None则使用配置中的天数）
        """
        if not self.context:
            print("[错误] 系统未初始化")
            return
        
        if self.context.mode != 'training':
            print(f"[警告] 当前模式为 {self.context.mode}，非学习模式")
        
        learning_days = simulated_days or self.context.duration_days
        
        print(f"\n[系统] 开始学习阶段，模拟 {learning_days} 天...")
        print("-" * 60)
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # 模拟多天的学习
        for day in range(learning_days):
            day_start = time.time()
            
            print(f"\n📅 第 {day + 1}/{learning_days} 天学习开始...")
            
            # 模拟一天的学习（每小时为一个批次）
            for hour in range(24):
                # 生成1小时的流量
                packets = self.generator.generate_traffic_batch(60)  # 60分钟
                
                # 处理每个数据包
                for packet_meta, proto_data in packets:
                    self._process_packet(packet_meta, proto_data)
                
                # 输出进度
                if (hour + 1) % 6 == 0:  # 每6小时输出一次
                    progress = self._get_progress(day + 1, learning_days, hour + 1)
                    print(f"  进度: {progress}")
            
            # 更新上下文
            self.context.current_day = day + 1
            
            day_time = time.time() - day_start
            print(f"✅ 第 {day + 1} 天学习完成，用时 {day_time:.1f} 秒")
            print(f"   已处理包: {self.total_packets_processed}")
            print(f"   连接数: {self.comm_learner.observations_processed}")
            print(f"   参数数: {self.value_learner.observations_processed}")
        
        # 完成学习
        self._finalize_learning()
        
        print("\n" + "=" * 60)
        print("🎉 学习阶段完成！")
        print("=" * 60)
    
    def _process_packet(self, packet_meta: PacketMetadata, proto_data: ProtocolData):
        """处理单个数据包"""
        # 解析数据包（如果需要）
        if proto_data is None:
            proto_data = self.parser.parse_packet(packet_meta)
        
        # 保存到数据库
        parsed_summary = self.parser.generate_parsed_summary(packet_meta, proto_data)
        self.database.save_packet_metadata(packet_meta, parsed_summary)
        
        # 各个学习器学习
        self.comm_learner.learn(packet_meta, proto_data)
        self.value_learner.learn(packet_meta, proto_data)
        
        # 更新统计
        self.total_packets_processed += 1
        self.context.total_packets_processed = self.total_packets_processed
        self.context.total_sessions_observed = len(self.comm_learner.connection_observations)
    
    def _get_progress(self, current_day: int, total_days: int, current_hour: int) -> str:
        """获取进度字符串"""
        day_percent = (current_day - 1 + current_hour / 24) / total_days * 100
        return f"第{current_day}天 {current_hour:02d}:00 | 总体进度: {day_percent:.1f}%"
    
    def _finalize_learning(self):
        """完成学习，生成最终模型"""
        print("\n[系统] 正在生成最终模型...")
        
        # 各个学习器完成学习
        comm_result = self.comm_learner.finalize_learning()
        value_result = self.value_learner.finalize_learning()
        
        # 更新上下文
        self.context.total_connections_approved = comm_result['approved_connections']
        
        # 生成白名单
        self._generate_whitelist(comm_result, value_result)
        
        # 生成学习报告
        self._generate_learning_report(comm_result, value_result)
        
        # 保存模型
        self._save_models()
    
    def _generate_whitelist(self, comm_result: Dict, value_result: Dict):
        """生成白名单文件"""
        whitelist = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'learning_duration_days': self.context.duration_days,
            'summary': {
                'total_packets': self.total_packets_processed,
                'approved_connections': comm_result['approved_connections'],
                'valid_value_models': value_result['valid_models']
            },
            'communication_whitelist': [],
            'value_whitelist': []
        }
        
        # 通信白名单
        approved_connections = self.comm_learner.get_approved_connections()
        for conn in approved_connections:
            whitelist['communication_whitelist'].append({
                'src_ip': conn.src_ip,
                'dst_ip': conn.dst_ip,
                'dst_port': conn.dst_port,
                'protocol': conn.protocol,
                'observation_count': conn.observation_count,
                'confidence': conn.confidence,
                'avg_packets_per_day': conn.avg_packets_per_day,
                'max_packets_per_minute': conn.max_packets_per_minute,
                'first_observed': conn.first_observed.isoformat(),
                'last_observed': conn.last_observed.isoformat()
            })
        
        # 值域白名单
        for (protocol, address), val_obs in self.value_learner.value_observations.items():
            if val_obs.observation_count >= self.value_learner.min_value_observations:
                whitelist['value_whitelist'].append({
                    'protocol': protocol,
                    'address': address,
                    'tag_name': val_obs.tag_name,
                    'data_type': val_obs.data_type,
                    'unit': val_obs.unit,
                    'observation_count': val_obs.observation_count,
                    'min_value': val_obs.baseline_min,
                    'max_value': val_obs.baseline_max,
                    'mean': val_obs.mean,
                    'std_dev': val_obs.std_dev,
                    'tolerance': val_obs.tolerance
                })
        
        # 保存到文件
        output_config = self.config.get('output', {})
        whitelist_file = output_config.get('whitelist_file', 'outputs/whitelist.yaml')
        
        with open(whitelist_file, 'w', encoding='utf-8') as f:
            yaml.dump(whitelist, f, default_flow_style=False, allow_unicode=True)
        
        print(f"[系统] 白名单已生成: {whitelist_file}")
        print(f"      包含 {len(whitelist['communication_whitelist'])} 个连接")
        print(f"      包含 {len(whitelist['value_whitelist'])} 个值域规则")
    
    def _generate_learning_report(self, comm_result: Dict, value_result: Dict):
        """生成学习报告"""
        report = {
            'system_info': {
                'version': '1.0',
                'generated_at': datetime.now().isoformat(),
                'total_runtime_seconds': (datetime.now() - self.start_time).total_seconds()
            },
            'learning_context': {
                'mode': self.context.mode,
                'duration_days': self.context.duration_days,
                'start_time': self.context.start_time.isoformat(),
                'end_time': datetime.now().isoformat()
            },
            'statistics': {
                'total_packets_processed': self.total_packets_processed,
                'total_sessions_observed': self.context.total_sessions_observed,
                'total_connections_approved': self.context.total_connections_approved
            },
            'communication_learning': comm_result,
            'value_learning': value_result,
            'performance_metrics': {
                'packets_per_second': self.total_packets_processed / max(1, (datetime.now() - self.start_time).total_seconds()),
                'memory_usage_mb': self._get_memory_usage()
            }
        }
        
        # 保存报告
        output_config = self.config.get('output', {})
        report_file = output_config.get('report_file', 'outputs/learning_report.json')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"[系统] 学习报告已生成: {report_file}")
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量（MB）"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _save_models(self):
        """保存学习模型"""
        models_dir = Path(project_root) / 'models'
        models_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存通信模型
        comm_model_file = models_dir / f'communication_model_{timestamp}.json'
        self.comm_learner.save_model(str(comm_model_file))
        
        # 保存值域模型
        value_model_file = models_dir / f'value_model_{timestamp}.json'
        self.value_learner.save_model(str(value_model_file))
    
    def run_validation(self):
        """运行验证测试"""
        print("\n[系统] 开始验证测试...")
        print("-" * 60)
        
        # 生成攻击流量
        attack_types = ['recon', 'dos', 'malicious_command']
        
        for attack_type in attack_types:
            print(f"\n🚨 测试攻击类型: {attack_type}")
            
            # 生成攻击流量
            attack_packets = self.generator.generate_attack_traffic(attack_type)
            
            detected_count = 0
            total_attacks = len(attack_packets)
            
            for packet_meta, proto_data in attack_packets:
                # 验证通信关系
                comm_result = self.comm_learner.validate(packet_meta, proto_data)
                
                # 验证值域（如果适用）
                value_result = self.value_learner.validate(packet_meta, proto_data) if proto_data else {'approved': True}
                
                # 如果任一验证失败，则检测到攻击
                if not comm_result['approved'] or not value_result['approved']:
                    detected_count += 1
            
            detection_rate = detected_count / total_attacks * 100 if total_attacks > 0 else 0
            print(f"  攻击包数: {total_attacks}")
            print(f"  检测到数: {detected_count}")
            print(f"  检测率: {detection_rate:.1f}%")
    
    def run_demo_mode(self, days: int = 2):
        """
        运行演示模式（快速测试）
        
        Args:
            days: 模拟学习的天数
        """
        print("\n[系统] 启动演示模式...")
        print("=" * 60)
        
        # 修改配置为演示模式
        self.config['learning']['duration_days'] = days
        self.config['simulation']['packets_per_hour'] = 200  # 减少流量
        
        # 重新初始化
        self.initialize_system()
        
        # 运行学习
        self.run_learning_phase(days)
        
        # 运行验证
        self.run_validation()
        
        print("\n" + "=" * 60)
        print("🎬 演示模式完成！")
        print("=" * 60)
        print("生成的文件:")
        print(f"  白名单: outputs/whitelist.yaml")
        print(f"  报告: outputs/learning_report.json")
        print(f"  数据库: data/observations.db")
        print("=" * 60)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='工控自学习系统')
    parser.add_argument('--mode', choices=['full', 'demo', 'validate'], 
                       default='demo', help='运行模式')
    parser.add_argument('--days', type=int, default=2, 
                       help='学习天数（仅demo模式有效）')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='配置文件路径')
    
    args = parser.parse_args()
    
    # 创建系统实例
    system = ICSLearningSystem(args.config)
    
    # 根据模式运行
    if args.mode == 'demo':
        system.run_demo_mode(args.days)
    elif args.mode == 'full':
        system.initialize_system()
        system.run_learning_phase()
        system.run_validation()
    elif args.mode == 'validate':
        system.initialize_system()
        system.run_validation()

if __name__ == "__main__":
    main()