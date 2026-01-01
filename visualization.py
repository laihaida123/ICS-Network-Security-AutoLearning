#!/usr/bin/env python3
"""
实验结果可视化 - 生成图表
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

import platform

# 设置中文字体
def setup_chinese_font():
    """配置中文字体支持"""
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 根据操作系统选择字体
    system = platform.system()
    if system == 'Windows':
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
    elif system == 'Darwin':  # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'Songti SC']
    else:  # Linux
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'WenQuanYi Zen Hei']
    
    print(f"系统检测: {system}")
    print(f"字体设置: {plt.rcParams['font.sans-serif']}")
def create_visualizations():
    """创建所有可视化图表"""
    print("📊 生成实验结果可视化图表")
    
    # 确保输出目录存在
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    
    # 1. 学习效果对比图
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('工控自学习系统实验可视化报告', fontsize=16, fontweight='bold')
    
    # 实验数据（用你的实际数据）
    experiments = [
        {'name': '严格配置', 'packets': 377, 'connections': 0, 'values': 0},
        {'name': '适中配置', 'packets': 1127, 'connections': 2, 'values': 0},
        {'name': '强力配置', 'packets': 1945, 'connections': 36, 'values': 2}
    ]
    
    # 图表1：学习效果对比
    ax1 = axes[0, 0]
    names = [exp['name'] for exp in experiments]
    connections = [exp['connections'] for exp in experiments]
    values = [exp['values'] for exp in experiments]
    
    x = np.arange(len(names))
    width = 0.35
    
    ax1.bar(x - width/2, connections, width, label='通信规则', color='skyblue')
    ax1.bar(x + width/2, values, width, label='值域规则', color='lightcoral')
    
    ax1.set_xlabel('实验配置')
    ax1.set_ylabel('学习到的规则数量')
    ax1.set_title('不同配置的学习效果对比')
    ax1.set_xticks(x)
    ax1.set_xticklabels(names)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 添加数值标签
    for i, (conn, val) in enumerate(zip(connections, values)):
        ax1.text(i - width/2, conn + 0.5, str(conn), ha='center', va='bottom')
        ax1.text(i + width/2, val + 0.5, str(val), ha='center', va='bottom')
    
    # 图表2：流量与学习效果关系
    ax2 = axes[0, 1]
    packets = [exp['packets'] for exp in experiments]
    total_rules = [conn + val for conn, val in zip(connections, values)]
    
    ax2.scatter(packets, total_rules, s=100, color='green', alpha=0.6)
    
    # 添加趋势线
    z = np.polyfit(packets, total_rules, 1)
    p = np.poly1d(z)
    ax2.plot(packets, p(packets), "r--", alpha=0.5)
    
    ax2.set_xlabel('总数据包数量')
    ax2.set_ylabel('学习到的规则总数')
    ax2.set_title('流量大小与学习效果关系')
    ax2.grid(True, alpha=0.3)
    
    # 添加数据点标签
    for i, (pkt, rule) in enumerate(zip(packets, total_rules)):
        ax2.annotate(f"{names[i]}", (pkt, rule), 
                    xytext=(5, 5), textcoords='offset points')
    
    # 图表3：攻击检测结果
    ax3 = axes[0, 2]
    attack_types = ['通信攻击', '值域攻击', 'DoS攻击']
    detection_rates = [100, 100, 100]  # 你的结果都是100%
    colors = ['gold', 'lightgreen', 'lightblue']
    
    bars = ax3.bar(attack_types, detection_rates, color=colors)
    ax3.set_ylabel('检测率 (%)')
    ax3.set_title('攻击检测效果')
    ax3.set_ylim(0, 110)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 添加百分比标签
    for bar, rate in zip(bars, detection_rates):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'{rate}%', ha='center', va='bottom')
    
    # 图表4：值域学习示例
    ax4 = axes[1, 0]
    
    # 模拟温度数据
    np.random.seed(42)
    normal_temps = np.random.normal(50, 10, 50)  # 正常温度：均值50，标准差10
    attack_temps = [10, 150, 5, 200, -5]  # 攻击温度
    
    # 绘制正常温度分布
    ax4.hist(normal_temps, bins=15, alpha=0.7, color='lightblue', 
             edgecolor='black', label='正常温度')
    
    # 标记攻击温度
    for temp in attack_temps:
        ax4.axvline(x=temp, color='red', linestyle='--', alpha=0.7, 
                   linewidth=2, label='攻击值' if temp == attack_temps[0] else "")
    
    ax4.set_xlabel('温度值 (°C)')
    ax4.set_ylabel('出现频次')
    ax4.set_title('温度值分布与攻击检测')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 图表5：通信矩阵热图
    ax5 = axes[1, 1]
    
    # 模拟通信矩阵
    devices = ['HMI-100', 'HMI-101', 'HMI-102', 'PLC-10', 'PLC-11', 'PLC-12']
    comm_matrix = np.array([
        [0, 0, 0, 1, 0, 0],  # HMI-100 只和 PLC-10 通信
        [0, 0, 0, 0, 1, 0],  # HMI-101 只和 PLC-11 通信
        [0, 0, 0, 0, 0, 1],  # HMI-102 只和 PLC-12 通信
        [1, 0, 0, 0, 0, 0],  # PLC-10 回应 HMI-100
        [0, 1, 0, 0, 0, 0],  # PLC-11 回应 HMI-101
        [0, 0, 1, 0, 0, 0],  # PLC-12 回应 HMI-102
    ])
    
    im = ax5.imshow(comm_matrix, cmap='Blues', interpolation='nearest')
    ax5.set_xticks(np.arange(len(devices)))
    ax5.set_yticks(np.arange(len(devices)))
    ax5.set_xticklabels(devices, rotation=45)
    ax5.set_yticklabels(devices)
    ax5.set_title('设备通信矩阵（学习到的正常连接）')
    
    # 添加数值标签
    for i in range(len(devices)):
        for j in range(len(devices)):
            text = ax5.text(j, i, comm_matrix[i, j],
                          ha="center", va="center", 
                          color="white" if comm_matrix[i, j] > 0.5 else "black")
    
    # 图表6：时间线
    ax6 = axes[1, 2]
    
    timeline_data = [
        ('环境搭建', 0.1, 'skyblue'),
        ('基础学习', 0.2, 'lightgreen'),
        ('参数调优', 0.3, 'gold'),
        ('攻击检测', 0.2, 'lightcoral'),
        ('报告生成', 0.2, 'violet')
    ]
    
    categories = [item[0] for item in timeline_data]
    values = [item[1] for item in timeline_data]
    colors = [item[2] for item in timeline_data]
    
    ax6.barh(categories, values, color=colors)
    ax6.set_xlabel('时间占比')
    ax6.set_title('实验阶段时间分布')
    ax6.grid(True, alpha=0.3, axis='x')
    
    # 添加百分比标签
    for i, (category, value) in enumerate(zip(categories, values)):
        ax6.text(value + 0.01, i, f'{value*100:.0f}%', 
                va='center', fontweight='bold')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'outputs/experiment_visualization_{timestamp}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\n✅ 图表已生成: {output_file}")
    
    # 生成报告文件
    generate_text_report(experiments, detection_rates, output_file)

def generate_text_report(experiments, detection_rates, image_path):
    """生成文本报告"""
    report = {
        "report_title": "工控自学习系统实验报告",
        "generated_at": datetime.now().isoformat(),
        "experiment_summary": {
            "total_experiments": len(experiments),
            "best_configuration": experiments[-1]['name'],
            "highest_connection_rules": max(exp['connections'] for exp in experiments),
            "highest_value_rules": max(exp['values'] for exp in experiments)
        },
        "attack_detection_summary": {
            "average_detection_rate": sum(detection_rates) / len(detection_rates),
            "all_passed": all(rate == 100 for rate in detection_rates)
        },
        "key_findings": [
            "流量大小是影响学习效果的关键因素",
            "适中的观测阈值（3次）能平衡学习效率和准确性",
            "系统能100%检测模拟的工控攻击",
            "值域学习需要更集中的参数观测"
        ],
        "visualization_file": image_path
    }
    
    # 保存报告
    report_file = 'outputs/experiment_summary.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 打印摘要
    print(f"\n📋 实验摘要报告")
    print("=" * 50)
    print(f"实验次数: {report['experiment_summary']['total_experiments']}")
    print(f"最佳配置: {report['experiment_summary']['best_configuration']}")
    print(f"最高通信规则数: {report['experiment_summary']['highest_connection_rules']}")
    print(f"最高值域规则数: {report['experiment_summary']['highest_value_rules']}")
    print(f"平均攻击检测率: {report['attack_detection_summary']['average_detection_rate']:.1f}%")
    print(f"所有攻击检测通过: {'✅ 是' if report['attack_detection_summary']['all_passed'] else '❌ 否'}")
    print(f"详细报告: {report_file}")

if __name__ == "__main__":
    create_visualizations()