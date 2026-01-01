#!/usr/bin/env python3
"""
根据实际实验结果生成可视化图表 - 使用你的真实数据
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

# 在 visualization_real.py 开头添加
import matplotlib
import warnings

# 设置字体
matplotlib.rcParams['font.family'] = 'sans-serif'
# 尝试多个字体，按顺序使用
matplotlib.rcParams['font.sans-serif'] = [
    'DejaVu Sans',
    'Arial', 
    'Helvetica',
    'Verdana',
    'Bitstream Vera Sans'
]
matplotlib.rcParams['axes.unicode_minus'] = False

# 忽略特定警告
warnings.filterwarnings("ignore", 
    message="Font .* does not have a glyph for.*",
    category=UserWarning)
# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 使用系统支持的英文字体
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'  # 或 'Arial', 'Times New Roman'
plt.rcParams['axes.unicode_minus'] = True
def create_real_visualizations():
    """使用你的真实数据创建可视化图表"""
    print("📊 根据实际实验结果生成可视化图表")
    print("=" * 60)
    
    # 确保输出目录存在
    if not os.path.exists('outputs'):
        os.makedirs('outputs')
    
    # 1. 你的实际实验数据
    experiments = [
        {'name': '严格配置\n(流量:100包/小时)', 
         'packets': 377, 
         'connections': 0, 
         'values': 0,
         'desc': '阈值过高，无法学习'},
        
        {'name': '适中配置\n(流量:300包/小时)', 
         'packets': 1127, 
         'connections': 2, 
         'values': 0,
         'desc': '开始学习，但效率低'},
        
        {'name': '强力配置\n(流量:1000包/小时)', 
         'packets': 78754, 
         'connections': 484, 
         'values': 7658,
         'desc': '最佳学习效果'}
    ]
    
    # 2. 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('工控自学习系统实验结果可视化分析', fontsize=18, fontweight='bold', y=1.02)
    
    # 图表1：学习效果对比（使用对数坐标，因为数据量差异大）
    ax1 = axes[0, 0]
    names = [exp['name'] for exp in experiments]
    connections = [exp['connections'] for exp in experiments]
    values = [exp['values'] for exp in experiments]
    
    x = np.arange(len(names))
    width = 0.35
    
    # 使用对数坐标，因为484和7658与0、2差异太大
    ax1.bar(x - width/2, [max(conn, 0.1) for conn in connections], width, 
            label='通信规则', color='skyblue', alpha=0.8)
    ax1.bar(x + width/2, [max(val, 0.1) for val in values], width, 
            label='值域规则', color='lightcoral', alpha=0.8)
    
    ax1.set_xlabel('实验配置', fontsize=12)
    ax1.set_ylabel('学习到的规则数量（对数坐标）', fontsize=12)
    ax1.set_title('不同配置的学习效果对比', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, fontsize=10)
    ax1.set_yscale('log')  # 对数坐标
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3, which='both')
    
    # 添加数值标签（实际值）
    for i, (conn, val) in enumerate(zip(connections, values)):
        ax1.text(i - width/2, max(conn, 1) * 1.2, str(conn), 
                ha='center', va='bottom', fontsize=10, fontweight='bold')
        ax1.text(i + width/2, max(val, 1) * 1.2, str(val), 
                ha='center', va='bottom', fontsize=10, fontweight='bold')
        # 添加描述
        ax1.text(i, 0.05, experiments[i]['desc'], 
                ha='center', va='top', fontsize=9, style='italic')
    
    # 图表2：流量与学习效果关系（双Y轴）
    ax2 = axes[0, 1]
    
    packets = [exp['packets'] for exp in experiments]
    total_rules = [conn + val for conn, val in zip(connections, values)]
    
    # 主Y轴：总规则数
    color1 = 'tab:green'
    ax2.set_xlabel('总数据包数量', fontsize=12)
    ax2.set_ylabel('学习到的规则总数', color=color1, fontsize=12)
    line1 = ax2.plot(names, total_rules, 'o-', color=color1, 
                    linewidth=3, markersize=10, label='总规则数')[0]
    ax2.tick_params(axis='y', labelcolor=color1)
    ax2.set_yscale('log')
    
    # 添加数据点标签
    for i, (name, total) in enumerate(zip(names, total_rules)):
        ax2.annotate(f'{total:,}', (i, total), 
                    xytext=(0, 15), textcoords='offset points',
                    ha='center', fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    # 次Y轴：数据包数
    ax2b = ax2.twinx()
    color2 = 'tab:blue'
    ax2b.set_ylabel('数据包数量', color=color2, fontsize=12)
    bars = ax2b.bar(names, packets, alpha=0.3, color=color2, label='数据包数')
    ax2b.tick_params(axis='y', labelcolor=color2)
    ax2b.set_yscale('log')
    
    ax2.set_title('流量大小与学习效果关系', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 添加柱状图数值标签
    for bar, pkt in zip(bars, packets):
        height = bar.get_height()
        ax2b.text(bar.get_x() + bar.get_width()/2., height, f'{pkt:,}',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 图表3：攻击检测结果（你的实际结果）
    ax3 = axes[1, 0]
    
    attack_types = ['端口扫描\n(110个包)', 'DoS攻击\n(100个包)', '恶意命令\n(1个包)']
    detection_counts = [110, 100, 1]  # 实际检测到的攻击数
    total_attacks = [110, 100, 1]     # 总攻击数
    
    # 计算检测率
    detection_rates = []
    for detected, total in zip(detection_counts, total_attacks):
        rate = (detected / total * 100) if total > 0 else 0
        detection_rates.append(rate)
    
    colors = ['gold', 'lightgreen', 'lightblue']
    bars = ax3.bar(attack_types, detection_rates, color=colors, alpha=0.8)
    
    ax3.set_xlabel('攻击类型', fontsize=12)
    ax3.set_ylabel('检测率 (%)', fontsize=12)
    ax3.set_title('攻击检测效果验证', fontsize=14, fontweight='bold')
    ax3.set_ylim(0, 110)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 添加检测率和数量标签
    for bar, rate, detected, total in zip(bars, detection_rates, detection_counts, total_attacks):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'{rate:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
        # 在柱状图内部显示数量
        ax3.text(bar.get_x() + bar.get_width()/2., height/2,
                f'{detected}/{total}', ha='center', va='center', 
                fontsize=9, color='black', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))
    
    # 图表4：学习效率分析
    ax4 = axes[1, 1]
    
    # 计算学习效率：规则数/千数据包
    efficiency_data = []
    for exp in experiments:
        if exp['packets'] > 0:
            efficiency = (exp['connections'] + exp['values']) / exp['packets'] * 1000
        else:
            efficiency = 0
        efficiency_data.append({
            'name': exp['name'],
            'efficiency': efficiency,
            'rules_per_k': f"{(exp['connections'] + exp['values']) / exp['packets'] * 1000:.1f}" if exp['packets'] > 0 else "0"
        })
    
    eff_names = [d['name'] for d in efficiency_data]
    eff_values = [d['efficiency'] for d in efficiency_data]
    
    colors_eff = ['lightgray', 'lightblue', 'darkgreen']
    bars_eff = ax4.bar(eff_names, eff_values, color=colors_eff, alpha=0.8)
    
    ax4.set_xlabel('实验配置', fontsize=12)
    ax4.set_ylabel('学习效率 (规则数/千数据包)', fontsize=12)
    ax4.set_title('不同配置的学习效率对比', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # 添加效率值标签
    for bar, eff, data in zip(bars_eff, eff_values, efficiency_data):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + max(eff_values)*0.05,
                f"{data['rules_per_k']} 规则/千包", 
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 3. 调整布局并保存
    plt.tight_layout()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'outputs/experiment_visualization_real_{timestamp}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    
    print(f"\n✅ 图表已生成: {output_file}")
    print("=" * 60)
    
    # 4. 教你如何读图
    print("\n📖 如何解读这些图表：")
    print("=" * 60)
    print("""图表1：学习效果对比
    • 蓝色柱子：通信规则数（谁可以和谁说话）
    • 红色柱子：值域规则数（说话内容范围）
    • 关键发现：强力配置效果最好，学习到484+7658条规则
    • 对数坐标：因为数据差异太大（0→484），普通坐标无法清晰显示""")
    
    print("""\n图表2：流量与学习效果关系
    • 绿线：总规则数变化趋势
    • 蓝柱：数据包数量（对数坐标）
    • 关键发现：数据包从377→78754，规则数从0→8142
    • 学习效率：数据量增加209倍，规则增加∞倍（从0开始）""")
    
    print("""\n图表3：攻击检测效果
    • 柱子高度：检测率（都是100%）
    • 柱子内部数字：检测到数/总数
    • 关键验证：系统能100%检测所有模拟攻击
    • 实际意义：证明学习到的白名单有效""")
    
    print("""\n图表4：学习效率分析
    • 柱子高度：每千个数据包学到的规则数
    • 强力配置：103.4规则/千包
    • 关键指标：衡量学习算法的效率
    • 优化方向：提高这个值意味着更高效的学习""")
    
    print("\n" + "=" * 60)
    print("💡 核心发现总结：")
    print("  1. 流量是关键：1000包/小时效果最好")
    print("  2. 阈值要适中：3次观测启动学习")
    print("  3. 系统有效：100%攻击检测率")
    print("  4. 效率优秀：103.4规则/千包")
    print("=" * 60)
    
    # 5. 生成文本报告
    generate_real_report(experiments, detection_rates, output_file)

def generate_real_report(experiments, detection_rates, image_path):
    """生成真实实验报告"""
    report = {
        "report_title": "工控自学习系统实际实验结果报告",
        "generated_at": datetime.now().isoformat(),
        "experiment_data": [
            {
                "name": exp['name'].replace('\n', ' '),
                "packets": exp['packets'],
                "connections": exp['connections'],
                "values": exp['values'],
                "total_rules": exp['connections'] + exp['values'],
                "efficiency": f"{(exp['connections'] + exp['values']) / exp['packets'] * 1000:.1f}" if exp['packets'] > 0 else "0"
            } for exp in experiments
        ],
        "performance_metrics": {
            "best_configuration": experiments[-1]['name'].replace('\n', ' '),
            "total_packets_processed": experiments[-1]['packets'],
            "total_rules_learned": experiments[-1]['connections'] + experiments[-1]['values'],
            "learning_efficiency": f"{(experiments[-1]['connections'] + experiments[-1]['values']) / experiments[-1]['packets'] * 1000:.1f}",
            "attack_detection_rate": f"{sum(detection_rates)/len(detection_rates):.1f}%"
        },
        "key_findings": [
            "流量密度是影响学习效果的最关键因素（1000包/小时最佳）",
            "观测阈值3次在启动速度和准确性间达到最佳平衡",
            "系统实现了100%的模拟攻击检测率",
            "学习效率达到103.4规则/千数据包"
        ],
        "visualization_file": image_path,
        "data_files": [
            "outputs/whitelist.yaml",
            "outputs/learning_report.json",
            "outputs/attack_test_report.json"
        ]
    }
    
    report_file = 'outputs/experiment_real_summary.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 详细数据报告已保存: {report_file}")

if __name__ == "__main__":
    create_real_visualizations()