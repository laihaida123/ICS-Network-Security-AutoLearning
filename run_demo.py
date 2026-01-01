#!/usr/bin/env python3
"""
快速演示脚本
运行一个完整的学习和验证流程
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_quick_demo():
    """运行快速演示"""
    print("🚀 工控自学习系统 - 快速演示")
    print("=" * 50)
    
    # 导入主系统
    from main import ICSLearningSystem
    
    try:
        # 创建系统实例
        system = ICSLearningSystem("config.yaml")
        
        # 运行1天的演示
        print("\n1. 初始化系统...")
        system.initialize_system()
        
        print("\n2. 运行1天学习...")
        system.run_learning_phase(1)  # 只学习1天以加快演示
        
        print("\n3. 运行攻击检测测试...")
        system.run_validation()
        
        print("\n✅ 演示完成！")
        print("\n📁 生成的文件:")
        print(f"  白名单: {Path('outputs/whitelist.yaml').absolute()}")
        print(f"  学习报告: {Path('outputs/learning_report.json').absolute()}")
        print(f"  数据库: {Path('data/observations.db').absolute()}")
        
        # 显示白名单摘要
        print("\n📋 白名单摘要:")
        import yaml
        with open('outputs/whitelist.yaml', 'r', encoding='utf-8') as f:
            whitelist = yaml.safe_load(f)
        
        print(f"  批准连接数: {len(whitelist.get('communication_whitelist', []))}")
        print(f"  值域规则数: {len(whitelist.get('value_whitelist', []))}")
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_quick_demo()