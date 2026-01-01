"""
通信关系学习器
学习工控网络中的通信模式（谁和谁通信）
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import json
from collections import defaultdict

from .base_learner import BaseLearner
from ..model.models import PacketMetadata, ProtocolData, ConnectionObservation, LearningContext
from ..model.database import ObservationDatabase

class CommunicationLearner(BaseLearner):
    """
    通信关系学习器
    学习设备之间的通信模式，建立连接白名单
    """
    
    def __init__(self, config: Dict[str, Any], context: LearningContext, db: Optional[ObservationDatabase] = None):
        """
        初始化通信关系学习器
        
        Args:
            config: 配置字典
            context: 学习上下文
            db: 数据库实例（可选）
        """
        super().__init__(config, context)
        
        # 学习参数
        self.min_obs_count = config.get('learning', {}).get('min_observation_count', 10)
        self.min_obs_days = config.get('learning', {}).get('min_observation_days', 2)
        self.approval_threshold = config.get('statistical', {}).get('comm_approval_threshold', 0.85)
        
        # 存储连接观测
        self.connection_observations: Dict[str, ConnectionObservation] = {}
        
        # 通信矩阵（源IP -> 目标IP列表）
        self.communication_matrix: Dict[str, List[str]] = defaultdict(list)
        
        # 数据库连接
        self.db = db
        
        # 速率统计
        self.rate_windows: Dict[str, List[datetime]] = defaultdict(list)
        
        print(f"[通信学习器] 初始化完成，阈值: {self.min_obs_count}次/{self.min_obs_days}天")
    
    def learn(self, packet_meta: PacketMetadata, proto_data: ProtocolData) -> bool:
        """
        学习通信关系
        
        Args:
            packet_meta: 数据包元数据
            proto_data: 协议数据
            
        Returns:
            学习是否成功
        """
        try:
            import time
            start_time = time.time()
            
            # 生成连接键
            connection_key = self._generate_connection_key(packet_meta)
            
            # 获取或创建连接观测
            if connection_key in self.connection_observations:
                conn_obs = self.connection_observations[connection_key]
            else:
                conn_obs = ConnectionObservation(
                    src_ip=packet_meta.src_ip,
                    dst_ip=packet_meta.dst_ip,
                    dst_port=packet_meta.dst_port,
                    protocol=packet_meta.protocol,
                    first_observed=packet_meta.timestamp,
                    last_observed=packet_meta.timestamp
                )
                self.connection_observations[connection_key] = conn_obs
                self.models_created += 1
            
            # 更新连接观测
            conn_obs.update(packet_meta.packet_len, packet_meta.timestamp)
            
            # 更新通信矩阵
            self._update_communication_matrix(packet_meta)
            
            # 更新速率统计
            self._update_rate_statistics(connection_key, packet_meta.timestamp)
            
            # 计算最大速率
            self._calculate_max_rate(connection_key, conn_obs)
            
            # 保存到数据库（如果可用）
            if self.db:
                self.db.save_connection_observation(conn_obs)
            
            # 更新统计
            processing_time = time.time() - start_time
            self.update_statistics(processing_time)
            
            return True
            
        except Exception as e:
            print(f"[通信学习器] 学习错误: {e}")
            return False
    
    def _generate_connection_key(self, packet_meta: PacketMetadata) -> str:
        """生成连接唯一键"""
        return f"{packet_meta.src_ip}_{packet_meta.dst_ip}_{packet_meta.dst_port}_{packet_meta.protocol}"
    
    def _update_communication_matrix(self, packet_meta: PacketMetadata):
        """更新通信矩阵"""
        src_ip = packet_meta.src_ip
        dst_ip = packet_meta.dst_ip
        
        # 避免重复添加
        if dst_ip not in self.communication_matrix[src_ip]:
            self.communication_matrix[src_ip].append(dst_ip)
    
    def _update_rate_statistics(self, connection_key: str, timestamp: datetime):
        """更新速率统计"""
        # 维护最近1分钟的时间窗口
        window = self.rate_windows[connection_key]
        window.append(timestamp)
        
        # 移除1分钟前的记录
        cutoff = timestamp - timedelta(minutes=1)
        self.rate_windows[connection_key] = [t for t in window if t > cutoff]
    
    def _calculate_max_rate(self, connection_key: str, conn_obs: ConnectionObservation):
        """计算最大包速率"""
        window = self.rate_windows.get(connection_key, [])
        packets_per_minute = len(window)
        
        if packets_per_minute > conn_obs.max_packets_per_minute:
            conn_obs.max_packets_per_minute = packets_per_minute
    
    def calculate_connection_confidence(self, conn_obs: ConnectionObservation) -> float:
        """
        计算连接置信度
        
        Args:
            conn_obs: 连接观测
            
        Returns:
            置信度分数
        """
        # 计算观测到的天数
        duration_days = (conn_obs.last_observed - conn_obs.first_observed).days + 1
        
        return self.calculate_confidence(
            conn_obs.observation_count,
            duration_days,
            self.min_obs_count,
            self.min_obs_days
        )
    
    def finalize_learning(self) -> Dict[str, Any]:
        """
        完成学习，批准符合条件的连接
        
        Returns:
            学习结果摘要
        """
        approved_count = 0
        rejected_count = 0
        
        print(f"[通信学习器] 完成学习，处理 {len(self.connection_observations)} 个连接...")
        
        for conn_key, conn_obs in self.connection_observations.items():
            # 计算置信度
            confidence = self.calculate_connection_confidence(conn_obs)
            conn_obs.confidence = confidence
            
            # 计算观测天数
            duration_days = (conn_obs.last_observed - conn_obs.first_observed).days + 1
            
            # 判断是否批准
            should_approve = self.should_approve(
                conn_obs.observation_count,
                duration_days,
                confidence,
                self.approval_threshold
            )
            
            if should_approve:
                conn_obs.approved = True
                approved_count += 1
            else:
                conn_obs.approved = False
                conn_obs.rejection_reason = self._get_rejection_reason(
                    conn_obs.observation_count,
                    duration_days,
                    confidence
                )
                rejected_count += 1
            
            # 计算日平均速率
            if duration_days > 0:
                conn_obs.avg_packets_per_day = conn_obs.total_packets / duration_days
        
        # 更新上下文
        self.context.total_connections_approved = approved_count
        
        print(f"[通信学习器] 学习完成: 批准 {approved_count} 个, 拒绝 {rejected_count} 个连接")
        
        return {
            'total_connections': len(self.connection_observations),
            'approved_connections': approved_count,
            'rejected_connections': rejected_count,
            'approval_rate': approved_count / len(self.connection_observations) if self.connection_observations else 0,
            'avg_confidence': sum(c.confidence for c in self.connection_observations.values()) / len(self.connection_observations) if self.connection_observations else 0
        }
    
    def _get_rejection_reason(self, observation_count: int, duration_days: int, confidence: float) -> str:
        """获取拒绝原因"""
        if observation_count < self.min_obs_count:
            return f"观测次数不足 ({observation_count}/{self.min_obs_count})"
        elif duration_days < self.min_obs_days:
            return f"观测天数不足 ({duration_days}/{self.min_obs_days})"
        elif confidence < self.approval_threshold:
            return f"置信度不足 ({confidence:.3f}/{self.approval_threshold})"
        else:
            return "未知原因"
    
    def validate(self, packet_meta: PacketMetadata, proto_data: ProtocolData) -> Dict[str, Any]:
        """
        验证连接是否在白名单中
        
        Args:
            packet_meta: 数据包元数据
            proto_data: 协议数据
            
        Returns:
            验证结果
        """
        connection_key = self._generate_connection_key(packet_meta)
        
        if connection_key not in self.connection_observations:
            # 未知连接
            return {
                'approved': False,
                'confidence': 0.0,
                'reason': '未知连接',
                'is_whitelisted': False,
                'severity': 'high'  # 高风险
            }
        
        conn_obs = self.connection_observations[connection_key]
        
        if conn_obs.approved:
            # 已批准连接
            return {
                'approved': True,
                'confidence': conn_obs.confidence,
                'reason': '白名单连接',
                'is_whitelisted': True,
                'severity': 'low'
            }
        else:
            # 已知但未批准连接
            return {
                'approved': False,
                'confidence': conn_obs.confidence,
                'reason': conn_obs.rejection_reason or '未达到批准标准',
                'is_whitelisted': False,
                'severity': 'medium'
            }
    
    def get_approved_connections(self) -> List[ConnectionObservation]:
        """获取已批准的连接列表"""
        return [conn for conn in self.connection_observations.values() if conn.approved]
    
    def get_communication_matrix(self) -> Dict[str, List[str]]:
        """获取通信矩阵"""
        return dict(self.communication_matrix)
    
    def get_model_data(self) -> Dict[str, Any]:
        """获取模型数据"""
        model_data = {
            'learner_type': 'CommunicationLearner',
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'parameters': {
                'min_observation_count': self.min_obs_count,
                'min_observation_days': self.min_obs_days,
                'approval_threshold': self.approval_threshold
            },
            'connections': {}
        }
        
        for conn_key, conn_obs in self.connection_observations.items():
            model_data['connections'][conn_key] = {
                'src_ip': conn_obs.src_ip,
                'dst_ip': conn_obs.dst_ip,
                'dst_port': conn_obs.dst_port,
                'protocol': conn_obs.protocol,
                'observation_count': conn_obs.observation_count,
                'first_observed': conn_obs.first_observed.isoformat(),
                'last_observed': conn_obs.last_observed.isoformat(),
                'approved': conn_obs.approved,
                'confidence': conn_obs.confidence,
                'rejection_reason': conn_obs.rejection_reason,
                'avg_packets_per_day': conn_obs.avg_packets_per_day,
                'max_packets_per_minute': conn_obs.max_packets_per_minute
            }
        
        return model_data
    
    def load_model_data(self, model_data: Dict[str, Any]):
        """加载模型数据"""
        if model_data.get('learner_type') != 'CommunicationLearner':
            raise ValueError("不匹配的模型类型")
        
        # 加载参数
        params = model_data.get('parameters', {})
        self.min_obs_count = params.get('min_observation_count', self.min_obs_count)
        self.min_obs_days = params.get('min_observation_days', self.min_obs_days)
        self.approval_threshold = params.get('approval_threshold', self.approval_threshold)
        
        # 加载连接数据
        self.connection_observations.clear()
        connections = model_data.get('connections', {})
        
        for conn_key, conn_data in connections.items():
            conn_obs = ConnectionObservation(
                src_ip=conn_data['src_ip'],
                dst_ip=conn_data['dst_ip'],
                dst_port=conn_data['dst_port'],
                protocol=conn_data['protocol'],
                first_observed=datetime.fromisoformat(conn_data['first_observed']),
                last_observed=datetime.fromisoformat(conn_data['last_observed'])
            )
            
            # 设置其他属性
            conn_obs.observation_count = conn_data.get('observation_count', 0)
            conn_obs.approved = conn_data.get('approved', False)
            conn_obs.confidence = conn_data.get('confidence', 0.0)
            conn_obs.rejection_reason = conn_data.get('rejection_reason')
            conn_obs.avg_packets_per_day = conn_data.get('avg_packets_per_day', 0.0)
            conn_obs.max_packets_per_minute = conn_data.get('max_packets_per_minute', 0.0)
            
            self.connection_observations[conn_key] = conn_obs
        
        self.models_created = len(self.connection_observations)
        self.is_initialized = True
        
        print(f"[通信学习器] 加载了 {self.models_created} 个连接模型")