#!/usr/bin/env python3
"""
完整流程脚本：学习 → 生成白名单 → 攻击测试
"""

import subprocess
import os
import time

def run_complete_pipeline():
    print("🔄 完整工控安全实验流程")
    print("=" * 60)
    
    steps = [
        ("1. 环境检查", "poetry run python test_environment.py"),
        ("2. 完整学习（2天）", "poetry run python main.py --mode full --config config_powerful.yaml"),
        ("3. 攻击检测", "poetry run python attack_test.py"),
        ("4. 生成报告", "poetry run python generate_report.py")
    ]
    
    for step_name, command in steps:
        print(f"\n{step_name}")
        print("-" * 40)
        print(f"执行: {command}")
        
        try:
            result = subprocess.run(command, shell=True, check=True)
            print(f"✅ {step_name} 完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ {step_name} 失败: {e}")
            break
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("🎉 完整流程完成！")
    print("生成的文件：")
    print("  outputs/whitelist.yaml           # 完整白名单")
    print("  outputs/attack_test_report.json  # 攻击检测报告")
    print("  outputs/visualization.png        # 可视化图表")

if __name__ == "__main__":
    run_complete_pipeline()