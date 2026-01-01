"""
工控自学习模拟器主包
"""

__version__ = "1.0.0"
__author__ = "工控安全学习项目"

# 导出主要类
from .data_generator import TrafficGenerator
from .packet_parser import PacketParser
from .learner.base_learner import BaseLearner
from .learner.comm_learner import CommunicationLearner
from .learner.value_learner import ValueLearner
from .model.models import *
from .model.database import ObservationDatabase

# 简化导入
__all__ = [
    'TrafficGenerator',
    'PacketParser', 
    'BaseLearner',
    'CommunicationLearner',
    'ValueLearner',
    'ObservationDatabase'
]