import json
import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Asset:
    """资产信息"""
    id: str
    name: str
    type: str  # PLC, HMI, SCADA, etc.
    criticality: float  # 0-1
    vulnerability_score: float  # 0-1
    exposure: float  # 0-1
    impact_factor: float  # 0-1


@dataclass
class Threat:
    """威胁信息"""
    id: str
    type: str  # DoS, MITM, etc.
    severity: float  # 0-1
    likelihood: float  # 0-1
    iocs: List[str]  # Indicator of Compromise


@dataclass
class ResponseAction:
    """响应动作"""
    id: str
    name: str
    cost: float  # 0-1
    effectiveness: float  # 0-1
    recovery_time: float  # hours


class DynamicThreatAssessment:
    """
    动态威胁评估引擎
    通过三个维度计算威胁评分：威胁情报、资产脆弱性、业务影响
    """
    
    def __init__(self):
        self.assets: Dict[str, Asset] = {}
        self.threats: Dict[str, Threat] = {}
        self.responses: Dict[str, ResponseAction] = {}
        
    def add_asset(self, asset: Asset):
        """添加资产"""
        self.assets[asset.id] = asset
    
    def add_threat(self, threat: Threat):
        """添加威胁"""
        self.threats[threat.id] = threat
    
    def add_response(self, response: ResponseAction):
        """添加响应动作"""
        self.responses[response.id] = response
    
    def calculate_threat_score(self, threat_id: str, asset_id: str) -> float:
        """
        计算威胁评分
        综合考虑威胁情报、资产脆弱性和业务影响
        
        T_Score = w_I * F_I + w_V * F_V + w_B * F_B
        其中：
        - F_I: 威胁情报维度
        - F_V: 资产脆弱性维度
        - F_B: 业务影响维度
        - w_I, w_V, w_B: 权重
        """
        if threat_id not in self.threats or asset_id not in self.assets:
            return 0.0
        
        threat = self.threats[threat_id]
        asset = self.assets[asset_id]
        
        # 威胁情报维度 F_I
        # 基于威胁严重性和与资产的IOC匹配度
        ioc_match_score = self._calculate_ioc_match(threat, asset)
        f_i = threat.severity * 0.7 + ioc_match_score * 0.3
        
        # 资产脆弱性维度 F_V
        # 基于资产的暴露面和防护状态
        f_v = asset.vulnerability_score * 0.6 + asset.exposure * 0.4
        
        # 业务影响维度 F_B
        # 基于资产关键性和影响系数
        f_b = asset.criticality * 0.5 + asset.impact_factor * 0.5
        
        # 计算综合威胁评分
        # 权重可以根据实际情况调整
        w_i = 0.3  # 威胁情报权重
        w_v = 0.4  # 资产脆弱性权重
        w_b = 0.3  # 业务影响权重
        
        threat_score = w_i * f_i + w_v * f_v + w_b * f_b
        
        return threat_score
    
    def _calculate_ioc_match(self, threat: Threat, asset: Asset) -> float:
        """计算威胁与资产的IOC匹配度"""
        # 简化计算：根据资产类型和威胁类型匹配
        # 实际应用中会更复杂，需要考虑更多因素
        asset_type_threat_match = {
            'PLC': {'DoS': 0.9, 'MITM': 0.8, 'CodeInjection': 0.95},
            'HMI': {'DoS': 0.7, 'MITM': 0.8, 'DataExfiltration': 0.6},
            'SCADA': {'DoS': 0.8, 'MITM': 0.9, 'DataExfiltration': 0.7}
        }
        
        match_score = asset_type_threat_match.get(asset.type, {}).get(threat.type, 0.1)
        
        # 结合资产的漏洞评分
        match_score = match_score * asset.vulnerability_score
        
        return min(match_score, 1.0)  # 确保在0-1范围内
    
    def calculate_response_optimization(self, threat_id: str, asset_id: str) -> List[ResponseAction]:
        """
        计算响应优化
        根据威胁评分和资产重要性，计算响应动作的成本效益比
        """
        threat_score = self.calculate_threat_score(threat_id, asset_id)
        if threat_score <= 0:
            return []
        
        asset = self.assets[asset_id]
        
        # 计算每个响应动作的优先级
        prioritized_responses = []
        for response_id, response in self.responses.items():
            # 成本效益比 = (威胁降低程度 * 资产重要性) / 响应成本
            threat_reduction = response.effectiveness * threat_score
            cost_benefit_ratio = (threat_reduction * asset.criticality) / (response.cost + 0.1)  # 避免除零
            
            prioritized_responses.append({
                'response': response,
                'cost_benefit_ratio': cost_benefit_ratio,
                'priority_score': cost_benefit_ratio * response.effectiveness
            })
        
        # 按优先级排序
        prioritized_responses.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # 返回前3个最优响应
        return [item['response'] for item in prioritized_responses[:3]]
    
    def get_threat_path(self, start_asset_id: str, target_asset_id: str) -> List[str]:
        """
        获取威胁路径
        计算从起始资产到目标资产的潜在威胁路径
        """
        # 这里使用简化的路径计算
        # 实际应用中可能需要更复杂的图算法
        if start_asset_id not in self.assets or target_asset_id not in self.assets:
            return []
        
        # 模拟资产间的连接关系
        # 实际应用中这些关系需要从网络拓扑中获取
        asset_connections = {
            'hmi1': ['plc1', 'plc2'],
            'plc1': ['scada1', 'hmi1'],
            'plc2': ['scada1', 'hmi1'],
            'scada1': ['plc1', 'plc2', 'enterprise']
        }
        
        # 使用广度优先搜索查找路径
        visited = set()
        queue = [(start_asset_id, [start_asset_id])]
        
        while queue:
            current_asset, path = queue.pop(0)
            
            if current_asset == target_asset_id:
                return path
            
            if current_asset in visited:
                continue
                
            visited.add(current_asset)
            
            # 添加相邻资产到队列
            if current_asset in asset_connections:
                for neighbor in asset_connections[current_asset]:
                    if neighbor not in visited:
                        queue.append((neighbor, path + [neighbor]))
        
        return []  # 没有找到路径


def run_example():
    """运行示例"""
    print("🔍 动态威胁评估算法示例")
    print("=" * 50)
    
    # 创建威胁评估引擎
    dta = DynamicThreatAssessment()
    
    # 添加资产
    plc1 = Asset("plc1", "PLC Unit 1", "PLC", 0.9, 0.7, 0.8, 0.9)
    hmi1 = Asset("hmi1", "HMI Station 1", "HMI", 0.7, 0.5, 0.6, 0.6)
    scada1 = Asset("scada1", "SCADA Server", "SCADA", 0.95, 0.4, 0.7, 0.95)
    
    dta.add_asset(plc1)
    dta.add_asset(hmi1)
    dta.add_asset(scada1)
    
    # 添加威胁
    dos_threat = Threat("dos1", "DoS Attack", 0.8, 0.6, ["ip_192.168.1.100"])
    mitm_threat = Threat("mitm1", "MITM Attack", 0.9, 0.5, ["mac_00:11:22:33:44:55"])
    
    dta.add_threat(dos_threat)
    dta.add_threat(mitm_threat)
    
    # 添加响应动作
    isolate_resp = ResponseAction("isolate", "Isolate Asset", 0.3, 0.9, 0.5)
    block_resp = ResponseAction("block", "Block Traffic", 0.1, 0.7, 0.1)
    alert_resp = ResponseAction("alert", "Send Alert", 0.05, 0.3, 0.01)
    
    dta.add_response(isolate_resp)
    dta.add_response(block_resp)
    dta.add_response(alert_resp)
    
    # 计算威胁评分
    threat_score = dta.calculate_threat_score("dos1", "plc1")
    print(f"威胁评分 (DoS -> PLC1): {threat_score:.2f}")
    
    # 计算响应优化
    responses = dta.calculate_response_optimization("dos1", "plc1")
    print(f"推荐响应动作: {[r.name for r in responses]}")
    
    # 获取威胁路径
    path = dta.get_threat_path("hmi1", "scada1")
    print(f"威胁路径 (HMI1 -> SCADA1): {' -> '.join(path)}")
    
    print("\n✅ 示例执行完成")


if __name__ == "__main__":
    run_example()
