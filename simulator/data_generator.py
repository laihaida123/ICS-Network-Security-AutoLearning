"""
工控流量模拟生成器
模拟真实的工控网络流量，用于系统学习和测试
"""

import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from ipaddress import IPv4Address, IPv4Network
import socket
import struct

from .model.models import PacketMetadata, ProtocolData

class TrafficGenerator:
    """
    工控流量生成器
    模拟HMI、PLC、SCADA等设备之间的通信流量
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化流量生成器
        
        Args:
            config: 配置字典，包含网络和模拟参数
        """
        self.config = config
        self.network_config = config.get('network', {})
        self.protocol_config = config.get('protocols', {})
        self.simulation_config = config.get('simulation', {})
        
        # 初始化设备池
        self.plc_ips = self._generate_ip_pool(
            self.network_config.get('plc_ip_range', {})
        )
        self.hmi_ips = self._generate_ip_pool(
            self.network_config.get('hmi_ip_range', {})
        )
        
        # 协议端口映射
        self.protocol_ports = {
            'modbus': self.network_config.get('ports', {}).get('modbus', 502),
            's7comm': self.network_config.get('ports', {}).get('s7comm', 102),
            'opc_ua': self.network_config.get('ports', {}).get('opc_ua', 4840)
        }
        
        # 模拟状态
        self.current_time = datetime.now()
        self.day_offset = 0  # 模拟天数偏移
        
        # 模拟的工程变量（标签点）
        self.process_variables = self._init_process_variables()
        
        # 流量模式：模拟昼夜变化
        self.traffic_pattern = {
            'night_low': (0, 6, 0.1),    # 0-6点，10%流量
            'morning_peak': (7, 9, 2.0), # 7-9点，200%流量（早高峰）
            'day_normal': (10, 16, 1.0), # 10-16点，正常流量
            'evening_peak': (17, 19, 1.5), # 17-19点，150%流量
            'night_normal': (20, 23, 0.5) # 20-23点，50%流量
        }
        
        print(f"[生成器] 初始化完成: {len(self.plc_ips)}个PLC, {len(self.hmi_ips)}个HMI")
    
    def _generate_ip_pool(self, ip_range: Dict) -> List[str]:
        """生成IP地址池"""
        if not ip_range:
            return []
        
        start_ip = IPv4Address(ip_range.get('start', '192.168.1.10'))
        end_ip = IPv4Address(ip_range.get('end', '192.168.1.20'))
        
        ip_pool = []
        current_ip = start_ip
        while current_ip <= end_ip:
            ip_pool.append(str(current_ip))
            current_ip += 1
            
        return ip_pool
    
    def _init_process_variables(self) -> List[Dict[str, Any]]:
        """初始化过程变量（模拟真实的工控数据点）"""
        variables = []
        data_types = self.simulation_config.get('data_types', {})
        
        # 温度变量
        if 'temperature' in data_types:
            temp_config = data_types['temperature']
            for addr in range(temp_config['address_range'][0], 
                            temp_config['address_range'][1] + 1):
                variables.append({
                    'address': addr,
                    'name': f'TEMP_{addr - 40000:03d}',
                    'type': 'float',
                    'unit': temp_config.get('unit', '°C'),
                    'min_value': temp_config['value_range'][0],
                    'max_value': temp_config['value_range'][1],
                    'current_value': random.uniform(*temp_config['value_range']),
                    'normal_range': (
                        temp_config['value_range'][0] * 1.1,
                        temp_config['value_range'][1] * 0.9
                    ),
                    'drift_rate': random.uniform(-0.1, 0.1)  # 每小时漂移率
                })
        
        # 压力变量
        if 'pressure' in data_types:
            pressure_config = data_types['pressure']
            for addr in range(pressure_config['address_range'][0],
                            pressure_config['address_range'][1] + 1):
                variables.append({
                    'address': addr,
                    'name': f'PRESS_{addr - 40050:03d}',
                    'type': 'float',
                    'unit': pressure_config.get('unit', 'MPa'),
                    'min_value': pressure_config['value_range'][0],
                    'max_value': pressure_config['value_range'][1],
                    'current_value': random.uniform(*pressure_config['value_range']),
                    'normal_range': (
                        pressure_config['value_range'][0] * 1.05,
                        pressure_config['value_range'][1] * 0.95
                    ),
                    'drift_rate': random.uniform(-0.05, 0.05)
                })
        
        print(f"[生成器] 初始化了 {len(variables)} 个过程变量")
        return variables
    
    def _get_traffic_multiplier(self, hour: int) -> float:
        """根据时间获取流量乘数（模拟昼夜模式）"""
        for period_name, (start_hour, end_hour, multiplier) in self.traffic_pattern.items():
            if start_hour <= hour <= end_hour:
                return multiplier
        return 1.0  # 默认乘数
    
    def _update_process_variables(self):
        """更新过程变量的当前值（模拟过程动态）"""
        for var in self.process_variables:
            # 基础漂移
            drift = var['drift_rate'] * random.uniform(0.8, 1.2)
            new_value = var['current_value'] + drift
            
            # 添加随机波动
            fluctuation = (var['max_value'] - var['min_value']) * 0.02 * random.uniform(-1, 1)
            new_value += fluctuation
            
            # 确保在合理范围内
            if new_value < var['min_value']:
                new_value = var['min_value'] + abs(fluctuation)
            elif new_value > var['max_value']:
                new_value = var['max_value'] - abs(fluctuation)
            
            # 模拟周期性变化（例如白天温度高）
            hour = self.current_time.hour
            if var['unit'] == '°C' and 6 <= hour <= 18:
                new_value += (var['max_value'] - var['min_value']) * 0.1
            
            var['current_value'] = round(new_value, 2)
    
    def _generate_modbus_packet(self, src_ip: str, dst_ip: str, 
                               is_request: bool = True) -> Tuple[PacketMetadata, ProtocolData]:
        """生成Modbus/TCP数据包"""
        
        # 选择功能码（根据配置）
        function_codes = self.protocol_config.get('modbus', {}).get('function_codes', [1, 3, 5, 6])
        function_code = random.choice(function_codes)
        
        # 选择寄存器地址
        if function_code in [1, 2]:  # 读线圈/离散输入
            address_range = self.protocol_config.get('modbus', {}).get('coil_range', [0, 9999])
        elif function_code in [3, 4]:  # 读保持寄存器/输入寄存器
            address_range = self.protocol_config.get('modbus', {}).get('holding_range', [40000, 49999])
        else:
            address_range = [40000, 49999]  # 默认
        
        address = random.randint(address_range[0], address_range[1])
        quantity = random.randint(1, 10)  # 读取数量
        
        # 创建协议数据
        protocol_data = ProtocolData(
            protocol_type='modbus',
            function_code=function_code,
            transaction_id=random.randint(1, 1000),
            unit_id=random.randint(1, 247),
            starting_address=address,
            quantity=quantity
        )
        
        # 对于响应包或写操作，包含数据值
        if not is_request or function_code in [5, 6, 15, 16]:
            if is_request:
                # 写请求：生成合理的写入值
                var = next((v for v in self.process_variables if v['address'] == address), None)
                if var:
                    write_value = random.uniform(var['normal_range'][0], var['normal_range'][1])
                    protocol_data.values = [write_value]
                else:
                    protocol_data.values = [random.uniform(0, 100)]
            else:
                # 读响应：返回当前过程值
                var = next((v for v in self.process_variables if v['address'] == address), None)
                if var:
                    # 添加少量噪声
                    noise = var['current_value'] * 0.02 * random.uniform(-1, 1)
                    response_value = var['current_value'] + noise
                    protocol_data.values = [response_value]
                else:
                    protocol_data.values = [random.uniform(0, 100)]
        
        # 创建数据包元数据
        packet_meta = PacketMetadata(
            timestamp=self.current_time,
            src_ip=src_ip,
            dst_ip=dst_ip,
            dst_port=self.protocol_ports['modbus'],
            protocol='modbus',
            packet_len=random.randint(32, 256),  # 模拟Modbus包长度
            direction='request' if is_request else 'response'
        )
        
        return packet_meta, protocol_data
    
    def _generate_s7comm_packet(self, src_ip: str, dst_ip: str,
                               is_request: bool = True) -> Tuple[PacketMetadata, ProtocolData]:
        """生成S7COMM数据包（西门子S7协议）"""
        
        protocol_data = ProtocolData(
            protocol_type='s7comm',
            rosctr=1 if is_request else 7,  # 1=请求, 7=响应
            function_code=0x04 if is_request else 0x00  # 读/写
        )
        
        # 简单模拟S7数据
        if is_request:
            protocol_data.parameter = bytes([0x12, 0x0A, 0x10, 0x00])  # 示例参数
        else:
            protocol_data.data = bytes([0xFF, 0x03, 0x00, 0x10])  # 示例数据
        
        packet_meta = PacketMetadata(
            timestamp=self.current_time,
            src_ip=src_ip,
            dst_ip=dst_ip,
            dst_port=self.protocol_ports['s7comm'],
            protocol='s7comm',
            packet_len=random.randint(64, 512),
            direction='request' if is_request else 'response'
        )
        
        return packet_meta, protocol_data
    
    def generate_traffic_batch(self, duration_minutes: int = 1) -> List[Tuple[PacketMetadata, ProtocolData]]:
        """
        生成一批模拟流量
        
        Args:
            duration_minutes: 模拟的时间长度（分钟）
            
        Returns:
            包含(包元数据, 协议数据)的列表
        """
        packets = []
        
        # 更新模拟时间
        time_increment = timedelta(minutes=duration_minutes)
        self.current_time += time_increment
        self.day_offset += duration_minutes / (24 * 60)
        
        # 更新过程变量
        self._update_process_variables()
        
        # 确定当前时段的流量强度
        current_hour = self.current_time.hour
        traffic_multiplier = self._get_traffic_multiplier(current_hour)
        base_packets = self.simulation_config.get('packets_per_hour', 1000) / 60
        packets_to_generate = int(base_packets * duration_minutes * traffic_multiplier)
        
        print(f"[生成器] 为 {self.current_time.strftime('%Y-%m-%d %H:%M')} "
              f"生成 {packets_to_generate} 个包 (流量乘数: {traffic_multiplier:.1f}x)")
        
        # 生成数据包
        for _ in range(packets_to_generate):
            # 随机选择协议
            if random.random() < 0.8:  # 80%概率为Modbus
                protocol = 'modbus'
            else:
                protocol = 's7comm'
            
            # 随机选择设备
            src_ip = random.choice(self.hmi_ips)  # HMI发起请求
            dst_ip = random.choice(self.plc_ips)   # PLC响应
            
            # 生成请求包
            if protocol == 'modbus':
                request_meta, request_proto = self._generate_modbus_packet(
                    src_ip, dst_ip, is_request=True
                )
            else:
                request_meta, request_proto = self._generate_s7comm_packet(
                    src_ip, dst_ip, is_request=True
                )
            
            packets.append((request_meta, request_proto))
            
            # 90%的情况下生成响应包（模拟丢包或延迟）
            if random.random() < 0.9:
                response_time = self.current_time + timedelta(
                    milliseconds=random.randint(10, 100)  # 10-100ms响应时间
                )
                
                if protocol == 'modbus':
                    response_meta, response_proto = self._generate_modbus_packet(
                        dst_ip, src_ip, is_request=False
                    )
                else:
                    response_meta, response_proto = self._generate_s7comm_packet(
                        dst_ip, src_ip, is_request=False
                    )
                
                response_meta.timestamp = response_time
                packets.append((response_meta, response_proto))
        
        # 添加噪声包（5%的随机包）
        noise_count = int(packets_to_generate * 0.05)
        for _ in range(noise_count):
            # 随机源目的
            src_ip = f"192.168.1.{random.randint(2, 254)}"
            dst_ip = f"192.168.1.{random.randint(2, 254)}"
            
            noise_meta = PacketMetadata(
                timestamp=self.current_time + timedelta(milliseconds=random.randint(0, 1000)),
                src_ip=src_ip,
                dst_ip=dst_ip,
                dst_port=random.choice([80, 443, 21, 23, 502]),
                protocol=random.choice(['modbus', 'http', 'ftp', 'telnet']),
                packet_len=random.randint(40, 1500),
                direction='request' if random.random() > 0.5 else 'response'
            )
            
            packets.append((noise_meta, None))
        
        print(f"[生成器] 生成了 {len(packets)} 个数据包 ({noise_count} 个噪声包)")
        return packets
    
    def generate_attack_traffic(self, attack_type: str = "recon") -> List[Tuple[PacketMetadata, ProtocolData]]:
        """
        生成攻击流量用于测试
        
        Args:
            attack_type: 攻击类型 ('recon', 'dos', 'malicious_command')
            
        Returns:
            攻击流量包列表
        """
        packets = []
        attack_time = datetime.now()
        
        if attack_type == "recon":
            # 端口扫描攻击
            print(f"[攻击模拟] 生成端口扫描流量")
            for port in range(500, 510):  # 扫描多个端口
                for target_ip in self.plc_ips:
                    scan_meta = PacketMetadata(
                        timestamp=attack_time,
                        src_ip="192.168.1.200",  # 攻击者IP
                        dst_ip=target_ip,
                        dst_port=port,
                        protocol='tcp',
                        packet_len=60,
                        direction='request'
                    )
                    packets.append((scan_meta, None))
        
        elif attack_type == "dos":
            # 拒绝服务攻击（高频请求）
            print(f"[攻击模拟] 生成DoS攻击流量")
            target_ip = random.choice(self.plc_ips)
            for i in range(100):  # 短时间内大量请求
                dos_meta = PacketMetadata(
                    timestamp=attack_time + timedelta(milliseconds=i * 10),
                    src_ip="192.168.1.201",
                    dst_ip=target_ip,
                    dst_port=502,
                    protocol='modbus',
                    packet_len=100,
                    direction='request'
                )
                
                dos_proto = ProtocolData(
                    protocol_type='modbus',
                    function_code=random.choice([1, 3, 5]),
                    transaction_id=1000 + i,
                    unit_id=1,
                    starting_address=40000 + i % 100,
                    quantity=1
                )
                packets.append((dos_meta, dos_proto))
        
        elif attack_type == "malicious_command":
            # 恶意命令注入（写入危险值）
            print(f"[攻击模拟] 生成恶意命令流量")
            target_ip = random.choice(self.plc_ips)
            
            malicious_meta = PacketMetadata(
                timestamp=attack_time,
                src_ip="192.168.1.202",
                dst_ip=target_ip,
                dst_port=502,
                protocol='modbus',
                packet_len=120,
                direction='request'
            )
            
            # 写入超出正常范围的值（例如，设置温度过高）
            malicious_proto = ProtocolData(
                protocol_type='modbus',
                function_code=6,  # 写单个寄存器
                transaction_id=9999,
                unit_id=1,
                starting_address=40001,  # 温度控制寄存器
                quantity=1,
                values=[999.0]  # 危险的高温值
            )
            packets.append((malicious_meta, malicious_proto))
        
        return packets