# Relative Path: simulator/model/models.py
"""
数据模型定义模块
定义学习系统中使用的所有核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json

@dataclass
class PacketMetadata:
    """
    数据包元数据
    表示一个网络数据包的基本信息
    """
    timestamp: datetime
    src_ip: str
    dst_ip: str
    dst_port: int
    protocol: str
    packet_len: int
    direction: str  # 'request' 或 'response'
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'src_ip': self.src_ip,
            'dst_ip': self.dst_ip,
            'dst_port': self.dst_port,
            'protocol': self.protocol,
            'packet_len': self.packet_len,
            'direction': self.direction
        }

@dataclass 
class ProtocolData:
    """
    协议解析数据
    包含从数据包中解析出的具体协议信息
    """
    protocol_type: str  # 'modbus', 's7comm' 等
    function_code: Optional[int] = None
    transaction_id: Optional[int] = None
    unit_id: Optional[int] = None
    
    # Modbus特定字段
    starting_address: Optional[int] = None
    quantity: Optional[int] = None
    values: List[Any] = field(default_factory=list)
    coil_values: Optional[bytes] = None
    
    # S7COMM特定字段
    rosctr: Optional[int] = None
    parameter: Optional[bytes] = None
    data: Optional[bytes] = None

@dataclass
class ConnectionObservation:
    """
    连接观测记录
    记录两个端点之间的通信情况
    """
    src_ip: str
    dst_ip: str
    dst_port: int
    protocol: str
    
    # 观测统计
    first_observed: datetime
    last_observed: datetime
    observation_count: int = 0
    total_bytes: int = 0
    total_packets: int = 0
    
    # 速率统计
    packets_per_minute: List[float] = field(default_factory=list)
    avg_packets_per_day: float = 0.0
    max_packets_per_minute: float = 0.0
    
    # 时间模式
    hour_distribution: Dict[int, int] = field(default_factory=dict)
    day_distribution: Dict[int, int] = field(default_factory=dict)
    
    # 批准状态
    approved: bool = False
    confidence: float = 0.0  # 置信度评分
    rejection_reason: Optional[str] = None
    
    def update(self, packet_len: int, timestamp: datetime):
        """更新连接观测统计"""
        self.last_observed = timestamp
        self.observation_count += 1
        self.total_bytes += packet_len
        self.total_packets += 1
        
        # 更新小时分布
        hour = timestamp.hour
        self.hour_distribution[hour] = self.hour_distribution.get(hour, 0) + 1
        
        # 更新星期分布
        weekday = timestamp.weekday()
        self.day_distribution[weekday] = self.day_distribution.get(weekday, 0) + 1
        
    def calculate_confidence(self, min_obs: int) -> float:
        """计算连接置信度评分"""
        if self.observation_count < min_obs:
            return 0.0
            
        # 基础分：观测频率
        freq_score = min(1.0, self.observation_count / (min_obs * 10))
        
        # 时间分布分：检查是否在多个小时段出现
        time_score = len(self.hour_distribution) / 24.0
        
        # 综合置信度
        self.confidence = freq_score * 0.7 + time_score * 0.3
        return self.confidence

@dataclass
class FunctionCodeStats:
    """
    功能码统计
    记录特定协议功能码的使用情况
    """
    code: int
    name: str
    count: int = 0
    unique_src_ips: List[str] = field(default_factory=list)
    
    # 频率统计
    frequency: float = 0.0
    last_observed: Optional[datetime] = None
    
    def update(self, src_ip: str, timestamp: datetime):
        """更新功能码统计"""
        self.count += 1
        self.last_observed = timestamp
        
        if src_ip not in self.unique_src_ips:
            self.unique_src_ips.append(src_ip)

@dataclass
class ValueObservation:
    """
    值域观测记录
    记录特定参数地址的数值观测
    """
    address: int  # 参数地址，如Modbus寄存器地址
    data_type: str  # 'int16', 'uint32', 'float', 'bool'等
    tag_name: Optional[str] = None  # 工程标签名
    unit: Optional[str] = None  # 工程单位
    
    # 观测值记录
    values: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    
    # 统计指标
    observation_count: int = 0
    min_observed: Optional[float] = None
    max_observed: Optional[float] = None
    mean: float = 0.0
    std_dev: float = 0.0
    
    # 计算得出的基线
    baseline_min: Optional[float] = None
    baseline_max: Optional[float] = None
    tolerance: Optional[float] = None
    
    def add_observation(self, value: float, timestamp: datetime):
        """添加新的观测值（使用Welford在线算法）"""
        self.values.append(value)
        self.timestamps.append(timestamp)
        self.observation_count += 1
        
        # 更新最小最大值
        if self.min_observed is None or value < self.min_observed:
            self.min_observed = value
        if self.max_observed is None or value > self.max_observed:
            self.max_observed = value
        
        # Welford在线算法更新均值和标准差
        if self.observation_count == 1:
            self.mean = value
            self.std_dev = 0.0
        else:
            old_mean = self.mean
            self.mean = old_mean + (value - old_mean) / self.observation_count
            self.std_dev = self.std_dev + (value - old_mean) * (value - self.mean)
    
    def calculate_baseline(self, std_dev_multiplier: float = 3.0):
        """计算值域基线（nσ原则）"""
        if self.observation_count < 2:
            return
            
        # 计算样本标准差
        if self.observation_count > 1:
            variance = self.std_dev / (self.observation_count - 1)
            sample_std_dev = variance ** 0.5
        else:
            sample_std_dev = 0.0
        
        self.tolerance = sample_std_dev * std_dev_multiplier
        self.baseline_min = self.mean - self.tolerance
        self.baseline_max = self.mean + self.tolerance
        
        # 确保基线范围不超出实际观测范围
        if self.baseline_min < self.min_observed:
            self.baseline_min = self.min_observed
        if self.baseline_max > self.max_observed:
            self.baseline_max = self.max_observed

@dataclass
class LearningContext:
    """
    学习上下文
    管理整个学习过程的状态和配置
    """
    # 学习模式配置
    mode: str  # 'training', 'validation', 'production'
    start_time: datetime
    duration_days: int
    
    # 统计阈值
    min_observation_count: int
    min_observation_days: int
    
    # 学习状态
    enabled: bool = True
    current_day: int = 0
    
    # 统计计数器
    total_packets_processed: int = 0
    total_sessions_observed: int = 0
    total_connections_approved: int = 0
    
    # 学习模型存储
    connection_models: Dict[str, ConnectionObservation] = field(default_factory=dict)
    protocol_models: Dict[str, Dict[int, FunctionCodeStats]] = field(default_factory=dict)
    value_models: Dict[Tuple[str, int], ValueObservation] = field(default_factory=dict)
    
    # 性能统计
    processing_times: List[float] = field(default_factory=list)
    memory_usage_mb: List[float] = field(default_factory=list)
    
    def is_learning_complete(self) -> bool:
        """检查学习是否完成"""
        elapsed_days = (datetime.now() - self.start_time).days
        return elapsed_days >= self.duration_days and self.current_day >= self.duration_days
    
    def get_progress(self) -> Dict[str, Any]:
        """获取学习进度报告"""
        elapsed_days = (datetime.now() - self.start_time).days
        progress_pct = min(100, (elapsed_days / self.duration_days) * 100) if self.duration_days > 0 else 0
        
        return {
            'elapsed_days': elapsed_days,
            'total_days': self.duration_days,
            'progress_percent': progress_pct,
            'packets_processed': self.total_packets_processed,
            'connections_observed': self.total_sessions_observed,
            'connections_approved': self.total_connections_approved,
            'connection_approval_rate': (
                self.total_connections_approved / self.total_sessions_observed 
                if self.total_sessions_observed > 0 else 0
            )
        }