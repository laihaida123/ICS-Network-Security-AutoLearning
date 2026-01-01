import json
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
from enum import Enum
import matplotlib.pyplot as plt

import matplotlib.pyplot as plt
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

# 在代码开头调用
setup_chinese_font()
# ==================== 1. 数据模型定义 ====================
class AssetCriticality(Enum):
    TEST = 0.3      # 测试服务器
    APP = 0.7       # 应用服务器
    CORE_DB = 1.0   # 核心数据库

class ThreatLevel(Enum):
    SCAN = 0.2      # 扫描
    EXPLOIT = 0.9   # 漏洞利用
    LATERAL = 0.7   # 横向移动

@dataclass
class Asset:
    """模拟资产（服务器）"""
    id: str
    name: str
    criticality: AssetCriticality  # 资产关键性
    is_internet_facing: bool       # 是否暴露于公网
    is_patched: bool               # 是否已打补丁
    has_edr: bool                  # 是否有终端防护
    
    def __str__(self):
        return f"{self.name}(关键性:{self.criticality.value}, 公网:{self.is_internet_facing}, 已打补丁:{self.is_patched})"

@dataclass 
class SecurityAlert:
    """模拟安全告警"""
    id: str
    threat_type: ThreatLevel       # 威胁类型
    source_ip: str                 # 源IP
    target_asset: Asset            # 目标资产
    ioc_match: bool = True         # 威胁情报匹配
    timestamp: str = "2024-01-01 10:00:00"
    
    def __str__(self):
        return f"告警[{self.id}]: {self.threat_type.name}攻击 -> {self.target_asset.name}"

# ==================== 2. 动态威胁评估引擎 ====================
class DynamicThreatAssessment:
    """动态威胁评估模型 (核心算法)"""
    
    def __init__(self, weights: Dict[str, float] = None):
        # 默认权重: I(威胁情报), V(脆弱性), B(业务影响)
        self.weights = weights or {'w_I': 0.3, 'w_V': 0.3, 'w_B': 0.4}
        
    def calculate_F_I(self, alert: SecurityAlert) -> float:
        """计算威胁情报维度得分"""
        # 基于威胁类型和IOC匹配度
        base_score = alert.threat_type.value
        ioc_bonus = 0.2 if alert.ioc_match else 0.0
        return min(1.0, base_score + ioc_bonus)
    
    def calculate_F_V(self, alert: SecurityAlert) -> float:
        """计算资产脆弱性维度得分"""
        asset = alert.target_asset
        
        # 漏洞可利用性
        exploitability = 0.9 if alert.threat_type == ThreatLevel.EXPLOIT else 0.5
        
        # 资产暴露面
        exposure = 0.9 if asset.is_internet_facing else 0.3
        
        # 防护状态 (有多项防护就降低脆弱性)
        protection = 0.0
        if asset.is_patched:
            protection += 0.4
        if asset.has_edr:
            protection += 0.3
            
        # 脆弱性 = 可利用性 × 暴露面 × (1 - 防护效果)
        f_v = exploitability * exposure * (1 - min(0.8, protection))
        return round(f_v, 2)
    
    def calculate_F_B(self, alert: SecurityAlert) -> float:
        """计算业务影响维度得分"""
        asset = alert.target_asset
        
        # 资产关键性
        criticality = asset.criticality.value
        
        # 攻击类型对业务的影响系数
        impact_multiplier = 1.0
        if alert.threat_type == ThreatLevel.EXPLOIT:
            impact_multiplier = 1.2  # 漏洞利用影响更大
        elif alert.threat_type == ThreatLevel.LATERAL:
            impact_multiplier = 1.1  # 横向移动次之
            
        f_b = criticality * impact_multiplier
        return min(1.0, f_b)
    
    def calculate_T_Score(self, alert: SecurityAlert) -> float:
        """计算综合威胁评分 T_Score"""
        f_i = self.calculate_F_I(alert)
        f_v = self.calculate_F_V(alert) 
        f_b = self.calculate_F_B(alert)
        
        t_score = (self.weights['w_I'] * f_i + 
                   self.weights['w_V'] * f_v + 
                   self.weights['w_B'] * f_b)
        
        return {
            't_score': round(t_score, 3),
            'components': {'F_I': f_i, 'F_V': f_v, 'F_B': f_b},
            'alert': alert
        }

# ==================== 3. 响应优化引擎 ====================
class ResponseOptimizer:
    """响应路径优化引擎"""
    
    def __init__(self):
        self.response_actions = {
            'log_only': {'cost': 0.1, 'effect': 0.1, 'description': '仅记录日志'},
            'block_ip': {'cost': 0.3, 'effect': 0.6, 'description': '阻断源IP'},
            'isolate_asset': {'cost': 0.9, 'effect': 0.95, 'description': '隔离资产'},
            'apply_patch': {'cost': 0.4, 'effect': 0.8, 'description': '应用补丁'},
            'add_firewall_rule': {'cost': 0.2, 'effect': 0.5, 'description': '添加防火墙规则'}
        }
    
    def calculate_response_cost(self, action: str, asset: Asset, t_score: float) -> float:
        """计算响应动作的综合成本"""
        base_cost = self.response_actions[action]['cost']
        
        # 业务中断成本: 与资产关键性正相关
        business_interruption = base_cost * asset.criticality.value * 2
        
        # 误报风险成本: 与威胁评分负相关 (评分越低，误报可能性越高)
        false_positive_risk = (1 - t_score) * 0.3
        
        total_cost = base_cost + business_interruption + false_positive_risk
        return total_cost
    
    def optimize_response_path(self, assessment_result: Dict, budget: float = 1.0) -> List[Dict]:
        """为威胁推荐最优响应路径"""
        t_score = assessment_result['t_score']
        asset = assessment_result['alert'].target_asset
        
        candidate_actions = []
        
        # 评估每个可能的响应动作
        for action_id, action_info in self.response_actions.items():
            cost = self.calculate_response_cost(action_id, asset, t_score)
            benefit = action_info['effect'] * t_score  # 效果与威胁程度相关
            
            # 成本效益比 = 效益 / 成本
            if cost <= budget and cost > 0:
                cost_benefit_ratio = benefit / cost
                candidate_actions.append({
                    'action': action_id,
                    'description': action_info['description'],
                    'cost': round(cost, 2),
                    'benefit': round(benefit, 2),
                    'cost_benefit_ratio': round(cost_benefit_ratio, 2)
                })
        
        # 按成本效益比降序排序
        candidate_actions.sort(key=lambda x: x['cost_benefit_ratio'], reverse=True)
        
        # 构建最优响应路径 (这里简化: 选择前2个动作)
        optimal_path = candidate_actions[:2] if len(candidate_actions) >= 2 else candidate_actions
        
        return {
            'threat_level': t_score,
            'asset': str(asset),
            'optimal_path': optimal_path,
            'candidate_actions': candidate_actions
        }

# ==================== 4. 模拟实验 ====================
def run_simulation():
    """运行完整的模拟实验"""
    print("=" * 60)
    print("DynaSOAR 核心逻辑模拟实验")
    print("=" * 60)
    
    # 1. 创建模拟资产
    print("\n1. 创建模拟资产...")
    assets = [
        Asset("db-01", "核心数据库服务器", AssetCriticality.CORE_DB, False, True, True),
        Asset("web-01", "官网Web服务器", AssetCriticality.APP, True, False, True),
        Asset("test-01", "开发测试服务器", AssetCriticality.TEST, False, False, False),
        Asset("api-01", "公有云API服务器", AssetCriticality.APP, True, True, False)
    ]
    
    for asset in assets:
        print(f"  - {asset}")
    
    # 2. 创建模拟安全告警
    print("\n2. 生成模拟安全告警...")
    alerts = [
        SecurityAlert("alert-001", ThreatLevel.EXPLOIT, "202.96.128.86", assets[1]),  # 漏洞利用 -> Web服务器
        SecurityAlert("alert-002", ThreatLevel.SCAN, "58.218.92.102", assets[2]),      # 扫描 -> 测试服务器
        SecurityAlert("alert-003", ThreatLevel.LATERAL, "10.0.0.5", assets[0]),        # 横向移动 -> 数据库
        SecurityAlert("alert-004", ThreatLevel.EXPLOIT, "139.199.23.87", assets[3])    # 漏洞利用 -> API服务器
    ]
    
    for alert in alerts:
        print(f"  - {alert}")
    
    # 3. 初始化评估引擎
    print("\n3. 初始化动态威胁评估引擎...")
    assessment_engine = DynamicThreatAssessment()
    
    # 4. 对每个告警进行评估
    print("\n4. 执行动态威胁评估...")
    print("-" * 60)
    assessment_results = []
    
    for alert in alerts:
        result = assessment_engine.calculate_T_Score(alert)
        print(f"告警: {alert.id}")
        print(f"  目标: {alert.target_asset.name}")
        print(f"  威胁类型: {alert.threat_type.name}")
        print(f"  评分: F_I={result['components']['F_I']}, "
              f"F_V={result['components']['F_V']}, "
              f"F_B={result['components']['F_B']}")
        print(f"  T_Score: {result['t_score']}")
        print("-" * 40)
        assessment_results.append(result)
    
    # 5. 按T_Score排序 (响应优先级排序)
    print("\n5. 响应优先级排序结果...")
    sorted_results = sorted(assessment_results, key=lambda x: x['t_score'], reverse=True)
    
    for i, result in enumerate(sorted_results, 1):
        alert = result['alert']
        print(f"优先级 {i}: T_Score={result['t_score']} | "
              f"告警[{alert.id}] -> {alert.target_asset.name}")
    
    # 6. 对高威胁告警进行响应优化
    print("\n6. 高威胁告警响应路径优化...")
    print("-" * 60)
    optimizer = ResponseOptimizer()
    
    # 只处理T_Score > 0.5的高威胁告警
    high_threat_results = [r for r in sorted_results if r['t_score'] > 0.5]
    
    for result in high_threat_results:
        optimization = optimizer.optimize_response_path(result, budget=0.8)
        
        print(f"\n威胁告警: {result['alert'].id}")
        print(f"综合评分: {result['t_score']}")
        print(f"目标资产: {result['alert'].target_asset.name}")
        print("推荐响应路径:")
        
        for i, action in enumerate(optimization['optimal_path'], 1):
            print(f"  步骤{i}: {action['description']} "
                  f"[成本:{action['cost']}, 效益:{action['benefit']}, 性价比:{action['cost_benefit_ratio']}]")
    
    # 7. 可视化结果
    print("\n7. 生成可视化分析图表...")
    visualize_results(sorted_results)
    
    return sorted_results

def visualize_results(assessment_results):
    """可视化评估结果"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # 图1: 各告警的T_Score对比
    alert_ids = [f"{r['alert'].id}\n({r['alert'].target_asset.name})" 
                 for r in assessment_results]
    t_scores = [r['t_score'] for r in assessment_results]
    
    colors = []
    for score in t_scores:
        if score > 0.7:
            colors.append('#ff6b6b')  # 红色: 高风险
        elif score > 0.4:
            colors.append('#ffd166')  # 黄色: 中风险
        else:
            colors.append('#06d6a0')  # 绿色: 低风险
    
    axes[0].bar(alert_ids, t_scores, color=colors, edgecolor='black')
    axes[0].set_title('各告警动态威胁评分(T_Score)对比', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('T_Score (0-1)', fontsize=12)
    axes[0].axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='高威胁阈值')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 图2: 最后一个高威胁告警的评分组成
    if assessment_results:
        last_result = assessment_results[0]
        components = last_result['components']
        
        labels = ['F_I(威胁情报)', 'F_V(资产脆弱性)', 'F_B(业务影响)']
        values = [components['F_I'], components['F_V'], components['F_B']]
        weights = [0.3, 0.3, 0.4]  # 权重
        
        # 计算加权值
        weighted_values = [values[i] * weights[i] for i in range(3)]
        
        x = np.arange(len(labels))
        width = 0.35
        
        axes[1].bar(x - width/2, values, width, label='原始值', color='skyblue')
        axes[1].bar(x + width/2, weighted_values, width, label='加权值', color='lightcoral')
        
        axes[1].set_title(f"告警{last_result['alert'].id}的威胁评分组成分析", fontsize=14, fontweight='bold')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(labels, fontsize=11)
        axes[1].set_ylabel('评分', fontsize=12)
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dynasoar_simulation_results.png', dpi=150, bbox_inches='tight')
    print("  图表已保存为: dynasoar_simulation_results.png")
    plt.show()

# ==================== 主程序 ====================
if __name__ == "__main__":
    print("开始运行DynaSOAR模拟器...")
    print("说明: 本模拟器展示了动态威胁评估与响应优化的核心逻辑")
    print("=" * 60)
    
    try:
        results = run_simulation()
        
        print("\n" + "=" * 60)
        print("模拟实验完成!")
        print("=" * 60)
        print("\n关键结论:")
        print("1. 动态威胁评估能够根据资产上下文智能调整威胁评分")
        print("2. 相同攻击对不同资产产生的威胁值差异显著")
        print("3. 响应优化引擎能推荐性价比最高的处置方案")
        print("4. 实现了从'静态规则'到'动态评估'的演进")
        
        # 导出结果到JSON文件
        output_data = []
        for result in results:
            output_data.append({
                'alert_id': result['alert'].id,
                'target_asset': result['alert'].target_asset.name,
                'threat_type': result['alert'].threat_type.name,
                't_score': result['t_score'],
                'components': result['components']
            })
        
        with open('simulation_results.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print("\n详细结果已导出到: simulation_results.json")
        
    except Exception as e:
        print(f"\n模拟器运行出错: {e}")
        import traceback
        traceback.print_exc()