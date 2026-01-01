# Relative Path: simulator/learner/value_learner.py
"""
参数值域学习器
学习工控参数（如温度、压力等）的正常值范围
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import json
import math
from collections import defaultdict
import numpy as np

from .base_learner import BaseLearner
from ..model.models import PacketMetadata, ProtocolData, ValueObservation, LearningContext
from ..model.database import ObservationDatabase
from ..packet_parser import PacketParser

class ValueLearner(BaseLearner):
    """
    值域学习器
    学习工控参数的正常值范围，建立值域基线
    """
    
    def __init__(self, config: Dict[str, Any], context: LearningContext, 
                 packet_parser: PacketParser, db: Optional[ObservationDatabase] = None):
        """
        初始化值域学习器
        
        Args:
            config: 配置字典
            context: 学习上下文
            packet_parser: 数据包解析器实例
            db: 数据库实例（可选）
        """
        super().__init__(config, context)
        
        # 学习参数
        self.std_dev_multiplier = config.get('statistical', {}).get('value_std_dev_multiplier', 3.0)
        self.min_value_observations = config.get('statistical', {}).get('min_value_observations', 20)
        
        # 存储值域观测
        self.value_observations: Dict[Tuple[str, int], ValueObservation] = {}
        
        # 依赖组件
        self.packet_parser = packet_parser
        self.db = db
        
        # 数据类型推断
        self.data_type_patterns = {
            'bool': {'min': 0, 'max': 1, 'values': [0, 1]},
            'int16': {'min': -32768, 'max': 32767},
            'uint16': {'min': 0, 'max': 65535},
            'int32': {'min': -2147483648, 'max': 2147483647},
            'uint32': {'min': 0, 'max': 4294967295},
            'float': {'min': -3.4e38, 'max': 3.4e38}
        }
        
        # 工程标签映射（从配置加载）
        self.engineering_tags = self._load_engineering_tags(config)
        
        print(f"[值域学习器] 初始化完成，使用 {self.std_dev_multiplier}σ原则，最小样本数: {self.min_value_observations}")
    
    def _load_engineering_tags(self, config: Dict[str, Any]) -> Dict[int, Dict[str, str]]:
        """加载工程标签映射"""
        tags = {}
        data_types = config.get('simulation', {}).get('data_types', {})
        
        # 从模拟配置创建标签映射
        for var_type, var_config in data_types.items():
            address_range = var_config.get('address_range', [])
            unit = var_config.get('unit', '')
            
            if address_range and len(address_range) == 2:
                start_addr, end_addr = address_range
                for addr in range(start_addr, end_addr + 1):
                    tags[addr] = {
                        'name': f"{var_type.upper()}_{addr - start_addr + 1:03d}",
                        'unit': unit,
                        'type': 'float'  # 默认为浮点数
                    }
        
        print(f"[值域学习器] 加载了 {len(tags)} 个工程标签")
        return tags
    
    def infer_data_type(self, value: float, address: int) -> str:
        """
        推断数据类型
        
        Args:
            value: 观测值
            address: 参数地址
            
        Returns:
            推断的数据类型
        """
        # 如果地址有已知标签，使用标签的类型
        if address in self.engineering_tags:
            tag_info = self.engineering_tags[address]
            if 'type' in tag_info:
                return tag_info['type']
        
        # 根据值特征推断
        if value == 0 or value == 1:
            return 'bool'
        elif value.is_integer():
            int_value = int(value)
            if 0 <= int_value <= 1:
                return 'bool'
            elif -32768 <= int_value <= 32767:
                return 'int16'
            elif 0 <= int_value <= 65535:
                return 'uint16'
            else:
                return 'int32'
        else:
            return 'float'
    
    def learn(self, packet_meta: PacketMetadata, proto_data: ProtocolData) -> bool:
        """
        学习参数值域
        
        Args:
            packet_meta: 数据包元数据
            proto_data: 协议数据
            
        Returns:
            学习是否成功
        """
        try:
            import time
            start_time = time.time()
            
            # 只处理包含数据的操作
            if not self.packet_parser.is_data_operation(proto_data):
                return False
            
            # 提取数值和地址
            value = self.packet_parser.extract_numeric_value(proto_data)
            address = self.packet_parser.extract_parameter_address(proto_data)
            
            if value is None or address is None:
                return False
            
            # 生成值域键
            value_key = (proto_data.protocol_type, address)
            
            # 获取或创建值域观测
            if value_key in self.value_observations:
                val_obs = self.value_observations[value_key]
            else:
                # 推断数据类型
                data_type = self.infer_data_type(value, address)
                
                # 获取工程标签信息
                tag_name = None
                unit = None
                if address in self.engineering_tags:
                    tag_info = self.engineering_tags[address]
                    tag_name = tag_info.get('name')
                    unit = tag_info.get('unit')
                
                val_obs = ValueObservation(
                    address=address,
                    data_type=data_type,
                    tag_name=tag_name,
                    unit=unit
                )
                self.value_observations[value_key] = val_obs
                self.models_created += 1
            
            # 添加观测值
            val_obs.add_observation(value, packet_meta.timestamp)
            
            # 如果达到最小样本数，计算基线
            if val_obs.observation_count >= self.min_value_observations:
                val_obs.calculate_baseline(self.std_dev_multiplier)
            
            # 保存到数据库（如果可用）
            if self.db:
                self.db.save_value_observation(
                    proto_data.protocol_type,
                    address,
                    val_obs.data_type,
                    value,
                    packet_meta.timestamp
                )
            
            # 更新统计
            processing_time = time.time() - start_time
            self.update_statistics(processing_time)
            
            return True
            
        except Exception as e:
            print(f"[值域学习器] 学习错误: {e}")
            return False
    
    def finalize_learning(self) -> Dict[str, Any]:
        """
        完成学习，为所有参数计算最终基线
        
        Returns:
            学习结果摘要
        """
        valid_models = 0
        invalid_models = 0
        
        print(f"[值域学习器] 完成学习，处理 {len(self.value_observations)} 个参数...")
        
        for value_key, val_obs in self.value_observations.items():
            if val_obs.observation_count >= self.min_value_observations:
                # 计算最终基线
                val_obs.calculate_baseline(self.std_dev_multiplier)
                valid_models += 1
            else:
                invalid_models += 1
        
        print(f"[值域学习器] 学习完成: {valid_models} 个有效模型, {invalid_models} 个样本不足")
        
        return {
            'total_parameters': len(self.value_observations),
            'valid_models': valid_models,
            'invalid_models': invalid_models,
            'avg_observations_per_param': sum(v.observation_count for v in self.value_observations.values()) / len(self.value_observations) if self.value_observations else 0,
            'std_dev_multiplier': self.std_dev_multiplier
        }
    
    def validate(self, packet_meta: PacketMetadata, proto_data: ProtocolData) -> Dict[str, Any]:
        """
        验证参数值是否在正常范围内
        
        Args:
            packet_meta: 数据包元数据
            proto_data: 协议数据
            
        Returns:
            验证结果
        """
        # 只验证包含数据的操作
        if not self.packet_parser.is_data_operation(proto_data):
            return {
                'approved': True,
                'reason': '非数据操作',
                'severity': 'low'
            }
        
        # 提取数值和地址
        value = self.packet_parser.extract_numeric_value(proto_data)
        address = self.packet_parser.extract_parameter_address(proto_data)
        
        if value is None or address is None:
            return {
                'approved': True,
                'reason': '无法提取数值',
                'severity': 'low'
            }
        
        value_key = (proto_data.protocol_type, address)
        
        if value_key not in self.value_observations:
            # 未知参数
            return {
                'approved': False,
                'value': value,
                'address': address,
                'reason': '未知参数地址',
                'is_whitelisted': False,
                'severity': 'medium'
            }
        
        val_obs = self.value_observations[value_key]
        
        # 检查是否有足够观测建立基线
        if val_obs.observation_count < self.min_value_observations:
            return {
                'approved': True,  # 样本不足时不拒绝
                'value': value,
                'address': address,
                'reason': f'样本不足 ({val_obs.observation_count}/{self.min_value_observations})',
                'baseline_available': False,
                'severity': 'low'
            }
        
        # 检查值是否在基线范围内
        in_range = (
            val_obs.baseline_min is not None and 
            val_obs.baseline_max is not None and
            val_obs.baseline_min <= value <= val_obs.baseline_max
        )
        
        if in_range:
            # 计算偏离程度
            deviation = self._calculate_deviation(value, val_obs)
            
            return {
                'approved': True,
                'value': value,
                'address': address,
                'in_range': True,
                'deviation': deviation,
                'baseline_min': val_obs.baseline_min,
                'baseline_max': val_obs.baseline_max,
                'mean': val_obs.mean,
                'is_whitelisted': True,
                'severity': 'low'
            }
        else:
            # 超出范围，计算异常程度
            anomaly_score = self._calculate_anomaly_score(value, val_obs)
            
            return {
                'approved': False,
                'value': value,
                'address': address,
                'in_range': False,
                'anomaly_score': anomaly_score,
                'baseline_min': val_obs.baseline_min,
                'baseline_max': val_obs.baseline_max,
                'mean': val_obs.mean,
                'reason': f'值超出正常范围 ({value:.2f} 不在 [{val_obs.baseline_min:.2f}, {val_obs.baseline_max:.2f}] 内)',
                'is_whitelisted': False,
                'severity': 'high' if anomaly_score > 2.0 else 'medium'
            }
    
    def _calculate_deviation(self, value: float, val_obs: ValueObservation) -> float:
        """计算值偏离均值的程度（标准差倍数）"""
        if val_obs.std_dev == 0:
            return 0.0
        
        return abs(value - val_obs.mean) / val_obs.std_dev
    
    def _calculate_anomaly_score(self, value: float, val_obs: ValueObservation) -> float:
        """计算异常分数"""
        if val_obs.std_dev == 0:
            return abs(value - val_obs.mean)
        
        return abs(value - val_obs.mean) / val_obs.std_dev
    
    def get_value_statistics(self, protocol: str, address: int) -> Optional[Dict[str, Any]]:
        """
        获取参数的统计信息
        
        Args:
            protocol: 协议类型
            address: 参数地址
            
        Returns:
            统计信息字典，如果参数不存在则返回None
        """
        value_key = (protocol, address)
        
        if value_key not in self.value_observations:
            return None
        
        val_obs = self.value_observations[value_key]
        
        stats = {
            'address': val_obs.address,
            'data_type': val_obs.data_type,
            'tag_name': val_obs.tag_name,
            'unit': val_obs.unit,
            'observation_count': val_obs.observation_count,
            'min_observed': val_obs.min_observed,
            'max_observed': val_obs.max_observed,
            'mean': val_obs.mean,
            'std_dev': val_obs.std_dev,
            'has_baseline': val_obs.observation_count >= self.min_value_observations
        }
        
        if stats['has_baseline']:
            stats.update({
                'baseline_min': val_obs.baseline_min,
                'baseline_max': val_obs.baseline_max,
                'tolerance': val_obs.tolerance,
                'range_width': val_obs.baseline_max - val_obs.baseline_min if val_obs.baseline_max and val_obs.baseline_min else None
            })
        
        return stats
    
    def get_out_of_range_alerts(self, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        获取超出范围的值（用于检测异常）
        
        Args:
            threshold: 异常阈值（标准差倍数）
            
        Returns:
            异常值列表
        """
        alerts = []
        
        for (protocol, address), val_obs in self.value_observations.items():
            if val_obs.observation_count < self.min_value_observations:
                continue
            
            # 检查最近的观测值
            recent_values = val_obs.values[-10:]  # 最近10个值
            
            for i, value in enumerate(recent_values):
                if val_obs.baseline_min <= value <= val_obs.baseline_max:
                    continue
                
                # 计算异常分数
                anomaly_score = self._calculate_anomaly_score(value, val_obs)
                
                if anomaly_score > threshold:
                    alerts.append({
                        'protocol': protocol,
                        'address': address,
                        'tag_name': val_obs.tag_name,
                        'value': value,
                        'baseline_min': val_obs.baseline_min,
                        'baseline_max': val_obs.baseline_max,
                        'anomaly_score': anomaly_score,
                        'timestamp': val_obs.timestamps[-(10 - i)] if i < len(val_obs.timestamps) else None
                    })
        
        return alerts
    
    def get_model_data(self) -> Dict[str, Any]:
        """获取模型数据"""
        model_data = {
            'learner_type': 'ValueLearner',
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'parameters': {
                'std_dev_multiplier': self.std_dev_multiplier,
                'min_value_observations': self.min_value_observations
            },
            'value_models': {}
        }
        
        for (protocol, address), val_obs in self.value_observations.items():
            model_key = f"{protocol}_{address}"
            
            model_data['value_models'][model_key] = {
                'protocol': protocol,
                'address': address,
                'data_type': val_obs.data_type,
                'tag_name': val_obs.tag_name,
                'unit': val_obs.unit,
                'observation_count': val_obs.observation_count,
                'min_observed': val_obs.min_observed,
                'max_observed': val_obs.max_observed,
                'mean': val_obs.mean,
                'std_dev': val_obs.std_dev,
                'has_baseline': val_obs.observation_count >= self.min_value_observations
            }
            
            if val_obs.observation_count >= self.min_value_observations:
                model_data['value_models'][model_key].update({
                    'baseline_min': val_obs.baseline_min,
                    'baseline_max': val_obs.baseline_max,
                    'tolerance': val_obs.tolerance
                })
        
        return model_data
    
    def load_model_data(self, model_data: Dict[str, Any]):
        """加载模型数据"""
        if model_data.get('learner_type') != 'ValueLearner':
            raise ValueError("不匹配的模型类型")
        
        # 加载参数
        params = model_data.get('parameters', {})
        self.std_dev_multiplier = params.get('std_dev_multiplier', self.std_dev_multiplier)
        self.min_value_observations = params.get('min_value_observations', self.min_value_observations)
        
        # 加载值域模型
        self.value_observations.clear()
        value_models = model_data.get('value_models', {})
        
        for model_key, model_data in value_models.items():
            protocol = model_data['protocol']
            address = model_data['address']
            value_key = (protocol, address)
            
            val_obs = ValueObservation(
                address=address,
                data_type=model_data['data_type'],
                tag_name=model_data.get('tag_name'),
                unit=model_data.get('unit')
            )
            
            # 设置统计属性
            val_obs.observation_count = model_data.get('observation_count', 0)
            val_obs.min_observed = model_data.get('min_observed')
            val_obs.max_observed = model_data.get('max_observed')
            val_obs.mean = model_data.get('mean', 0.0)
            val_obs.std_dev = model_data.get('std_dev', 0.0)
            
            if model_data.get('has_baseline', False):
                val_obs.baseline_min = model_data.get('baseline_min')
                val_obs.baseline_max = model_data.get('baseline_max')
                val_obs.tolerance = model_data.get('tolerance')
            
            self.value_observations[value_key] = val_obs
        
        self.models_created = len(self.value_observations)
        self.is_initialized = True
        
        print(f"[值域学习器] 加载了 {self.models_created} 个值域模型")