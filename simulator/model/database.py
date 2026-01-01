# Relative Path: simulator/model/database.py
"""
数据存储模块
负责观测数据的持久化存储和查询
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from .models import PacketMetadata, ConnectionObservation, ValueObservation

class ObservationDatabase:
    """观测数据库管理器"""
    
    def __init__(self, db_file: str = "data/observations.db"):
        """
        初始化数据库连接
        
        Args:
            db_file: SQLite数据库文件路径
        """
        self.db_file = db_file
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        # 确保数据目录存在
        Path(self.db_file).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 创建数据包元数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS packet_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                src_ip TEXT NOT NULL,
                dst_ip TEXT NOT NULL,
                dst_port INTEGER NOT NULL,
                protocol TEXT NOT NULL,
                packet_len INTEGER NOT NULL,
                direction TEXT NOT NULL,
                parsed_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建连接观测表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connection_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_key TEXT UNIQUE NOT NULL,
                src_ip TEXT NOT NULL,
                dst_ip TEXT NOT NULL,
                dst_port INTEGER NOT NULL,
                protocol TEXT NOT NULL,
                first_observed TEXT NOT NULL,
                last_observed TEXT NOT NULL,
                observation_count INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                total_packets INTEGER DEFAULT 0,
                avg_packets_per_day REAL DEFAULT 0.0,
                max_packets_per_minute REAL DEFAULT 0.0,
                hour_distribution TEXT,
                day_distribution TEXT,
                approved INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.0,
                rejection_reason TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建值域观测表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS value_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol TEXT NOT NULL,
                address INTEGER NOT NULL,
                data_type TEXT NOT NULL,
                tag_name TEXT,
                unit TEXT,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(protocol, address, timestamp)
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_packet_timestamp 
            ON packet_metadata(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_packet_src_dst 
            ON packet_metadata(src_ip, dst_ip)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_connection_key 
            ON connection_observations(connection_key)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_value_protocol_address 
            ON value_observations(protocol, address)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_packet_metadata(self, metadata: PacketMetadata, parsed_data: Optional[Dict] = None):
        """保存数据包元数据到数据库"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        parsed_json = json.dumps(parsed_data) if parsed_data else None
        
        cursor.execute('''
            INSERT INTO packet_metadata 
            (timestamp, src_ip, dst_ip, dst_port, protocol, packet_len, direction, parsed_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.timestamp.isoformat(),
            metadata.src_ip,
            metadata.dst_ip,
            metadata.dst_port,
            metadata.protocol,
            metadata.packet_len,
            metadata.direction,
            parsed_json
        ))
        
        conn.commit()
        conn.close()
    
    def save_connection_observation(self, observation: ConnectionObservation):
        """保存或更新连接观测"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 生成唯一连接键
        connection_key = f"{observation.src_ip}_{observation.dst_ip}_{observation.dst_port}_{observation.protocol}"
        
        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM connection_observations WHERE connection_key = ?",
            (connection_key,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute('''
                UPDATE connection_observations 
                SET last_observed = ?, observation_count = ?, total_bytes = ?, total_packets = ?,
                    hour_distribution = ?, day_distribution = ?, approved = ?, confidence = ?,
                    rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE connection_key = ?
            ''', (
                observation.last_observed.isoformat(),
                observation.observation_count,
                observation.total_bytes,
                observation.total_packets,
                json.dumps(observation.hour_distribution),
                json.dumps(observation.day_distribution),
                1 if observation.approved else 0,
                observation.confidence,
                observation.rejection_reason,
                connection_key
            ))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO connection_observations 
                (connection_key, src_ip, dst_ip, dst_port, protocol, 
                 first_observed, last_observed, observation_count, total_bytes, total_packets,
                 hour_distribution, day_distribution, approved, confidence, rejection_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                connection_key,
                observation.src_ip,
                observation.dst_ip,
                observation.dst_port,
                observation.protocol,
                observation.first_observed.isoformat(),
                observation.last_observed.isoformat(),
                observation.observation_count,
                observation.total_bytes,
                observation.total_packets,
                json.dumps(observation.hour_distribution),
                json.dumps(observation.day_distribution),
                1 if observation.approved else 0,
                observation.confidence,
                observation.rejection_reason
            ))
        
        conn.commit()
        conn.close()
    
    def save_value_observation(self, protocol: str, address: int, 
                              data_type: str, value: float, timestamp: datetime):
        """保存值域观测数据"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO value_observations 
                (protocol, address, data_type, value, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                protocol,
                address,
                data_type,
                value,
                timestamp.isoformat()
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            # 忽略重复记录（相同协议、地址、时间戳）
            pass
        finally:
            conn.close()
    
    def get_connection_stats(self, hours: int = 24) -> Dict[str, Any]:
        """获取指定时间范围内的连接统计"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # 总数据包数
        cursor.execute('''
            SELECT COUNT(*) FROM packet_metadata 
            WHERE timestamp >= ?
        ''', (cutoff_time,))
        total_packets = cursor.fetchone()[0]
        
        # 唯一连接数
        cursor.execute('''
            SELECT COUNT(DISTINCT src_ip || ':' || dst_ip || ':' || dst_port) 
            FROM packet_metadata 
            WHERE timestamp >= ?
        ''', (cutoff_time,))
        unique_connections = cursor.fetchone()[0]
        
        # 协议分布
        cursor.execute('''
            SELECT protocol, COUNT(*) as count 
            FROM packet_metadata 
            WHERE timestamp >= ?
            GROUP BY protocol 
            ORDER BY count DESC
        ''', (cutoff_time,))
        protocol_dist = dict(cursor.fetchall())
        
        # 流量大小统计
        cursor.execute('''
            SELECT 
                SUM(packet_len) as total_bytes,
                AVG(packet_len) as avg_packet_size,
                MAX(packet_len) as max_packet_size
            FROM packet_metadata 
            WHERE timestamp >= ?
        ''', (cutoff_time,))
        traffic_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_packets': total_packets,
            'unique_connections': unique_connections,
            'protocol_distribution': protocol_dist,
            'total_bytes': traffic_stats[0] or 0,
            'avg_packet_size': traffic_stats[1] or 0,
            'max_packet_size': traffic_stats[2] or 0
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """清理指定天数前的旧数据"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        # 清理数据包元数据
        cursor.execute('DELETE FROM packet_metadata WHERE timestamp < ?', (cutoff_time,))
        packets_deleted = cursor.rowcount
        
        # 清理值域观测数据
        cursor.execute('DELETE FROM value_observations WHERE timestamp < ?', (cutoff_time,))
        values_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {
            'packets_deleted': packets_deleted,
            'values_deleted': values_deleted,
            'cutoff_time': cutoff_time
        }