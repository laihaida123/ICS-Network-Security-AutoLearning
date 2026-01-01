# Relative Path: simulator/learner/base_learner.py
"""
学习器基类
定义所有学习器的通用接口和功能
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import hashlib

from ..model.models import PacketMetadata, ProtocolData, LearningContext
from ..model.database import ObservationDatabase

class BaseLearner(ABC):
    """
    学习器抽象基类
    所有具体学习器都应该继承这个类
    """
    
    def __init__(self, config: Dict[str, Any], context: LearningContext):
        """
        初始化学习器
        
        Args:
            config: 配置字典
            context: 学习上下文
        """
        self.config = config
        self.context = context
        self.learner_config = config.get('statistical', {})
        
        # 统计信息
        self.observations_processed = 0
        self.models_created = 0
        self.last_processing_time = 0.0
        
        # 学习状态
        self.is_training = context.mode == 'training'
        self.is_initialized = False
        
        print(f"[{self.__class__.__name__}] 初始化完成")
    
    @abstractmethod
    def learn(self, packet_meta: PacketMetadata, proto_data: ProtocolData) -> bool:
        """
        从单个数据包中学习
        
        Args:
            packet_meta: 数据包元数据
            proto_data: 协议数据
            
        Returns:
            学习是否成功
        """
        pass
    
    @abstractmethod
    def finalize_learning(self) -> Dict[str, Any]:
        """
        完成学习，生成最终模型
        
        Returns:
            学习结果摘要
        """
        pass
    
    @abstractmethod
    def validate(self, packet_meta: PacketMetadata, proto_data: ProtocolData) -> Dict[str, Any]:
        """
        验证数据包是否符合学习到的模型
        
        Args:
            packet_meta: 数据包元数据
            proto_data: 协议数据
            
        Returns:
            验证结果字典，包含是否通过和置信度等信息
        """
        pass
    
    def update_statistics(self, processing_time: float):
        """
        更新学习器统计信息
        
        Args:
            processing_time: 处理时间（秒）
        """
        self.observations_processed += 1
        self.last_processing_time = processing_time
        
        # 每1000次处理输出一次统计
        if self.observations_processed % 1000 == 0:
            print(f"[{self.__class__.__name__}] 已处理 {self.observations_processed} 个观测")
    
    def calculate_confidence(self, observation_count: int, unique_days: int, 
                           min_obs: int, min_days: int) -> float:
        """
        计算置信度分数
        
        Args:
            observation_count: 观测次数
            unique_days: 观测到的唯一天数
            min_obs: 最小观测次数阈值
            min_days: 最小观测天数阈值
            
        Returns:
            置信度分数（0.0-1.0）
        """
        if observation_count < min_obs or unique_days < min_days:
            return 0.0
        
        # 基础频率分数
        freq_score = min(1.0, observation_count / (min_obs * 3))
        
        # 时间分布分数
        time_score = min(1.0, unique_days / (min_days * 2))
        
        # 综合置信度
        confidence = (freq_score * 0.6 + time_score * 0.4)
        
        return round(confidence, 3)
    
    def should_approve(self, observation_count: int, unique_days: int,
                      confidence: float, threshold: float = 0.85) -> bool:
        """
        判断是否应该批准（加入白名单）
        
        Args:
            observation_count: 观测次数
            unique_days: 观测天数
            confidence: 置信度分数
            threshold: 批准阈值
            
        Returns:
            是否批准
        """
        min_obs = self.config.get('learning', {}).get('min_observation_count', 10)
        min_days = self.config.get('learning', {}).get('min_observation_days', 2)
        
        # 必须满足最小观测要求
        if observation_count < min_obs or unique_days < min_days:
            return False
        
        # 置信度必须超过阈值
        if confidence < threshold:
            return False
        
        return True
    
    def generate_key(self, *args) -> str:
        """
        生成唯一键
        
        Args:
            *args: 用于生成键的参数
            
        Returns:
            唯一键字符串
        """
        key_string = "_".join(str(arg) for arg in args if arg is not None)
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        获取学习器摘要
        
        Returns:
            学习器状态摘要
        """
        return {
            'learner_type': self.__class__.__name__,
            'observations_processed': self.observations_processed,
            'models_created': self.models_created,
            'is_training': self.is_training,
            'is_initialized': self.is_initialized,
            'last_processing_time': self.last_processing_time,
            'approval_threshold': self.learner_config.get('comm_approval_threshold', 0.85)
        }
    
    def save_model(self, file_path: str):
        """
        保存学习到的模型
        
        Args:
            file_path: 模型文件路径
        """
        model_data = self.get_model_data()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, indent=2, ensure_ascii=False)
        
        print(f"[{self.__class__.__name__}] 模型保存到: {file_path}")
    
    def load_model(self, file_path: str) -> bool:
        """
        加载已学习的模型
        
        Args:
            file_path: 模型文件路径
            
        Returns:
            加载是否成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            self.load_model_data(model_data)
            self.is_initialized = True
            
            print(f"[{self.__class__.__name__}] 从 {file_path} 加载模型")
            return True
            
        except Exception as e:
            print(f"[{self.__class__.__name__}] 加载模型失败: {e}")
            return False
    
    @abstractmethod
    def get_model_data(self) -> Dict[str, Any]:
        """
        获取模型数据用于保存
        
        Returns:
            模型数据字典
        """
        pass
    
    @abstractmethod
    def load_model_data(self, model_data: Dict[str, Any]):
        """
        从数据加载模型
        
        Args:
            model_data: 模型数据字典
        """
        pass
    
    def reset(self):
        """重置学习器状态"""
        self.observations_processed = 0
        self.models_created = 0
        self.is_initialized = False
        
        print(f"[{self.__class__.__name__}] 已重置")