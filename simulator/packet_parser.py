"""
数据包解析器（软探针）
负责解析网络数据包，提取工控协议信息
"""

import struct
import binascii
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import ipaddress
import random  # 新增这行

from .model.models import PacketMetadata, ProtocolData

class PacketParser:
    """
    工控协议数据包解析器
    支持Modbus/TCP、S7COMM等常见工控协议
    """
    
    # 协议标识
    PROTOCOL_PORTS = {
        502: 'modbus',
        102: 's7comm',
        4840: 'opc_ua',
        20000: 'dnp3',
        2404: 'iec60870',
        34962: 'profinet',
        34963: 'profinet',
        34964: 'profinet'
    }
    
    # Modbus功能码映射
    MODBUS_FUNCTIONS = {
        0x01: "Read Coils",
        0x02: "Read Discrete Inputs", 
        0x03: "Read Holding Registers",
        0x04: "Read Input Registers",
        0x05: "Write Single Coil",
        0x06: "Write Single Register",
        0x0F: "Write Multiple Coils",
        0x10: "Write Multiple Registers"
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化解析器
        
        Args:
            config: 配置文件字典
        """
        self.config = config
        self.protocol_config = config.get('protocols', {})
        
        print("[解析器] 初始化完成，支持协议: " + ", ".join(self.PROTOCOL_PORTS.values()))
    
    def parse_packet(self, packet_meta: PacketMetadata, raw_data: bytes = None) -> ProtocolData:
        """
        解析数据包，提取协议信息
        
        Args:
            packet_meta: 数据包元数据
            raw_data: 原始数据包字节（可选）
            
        Returns:
            ProtocolData: 解析后的协议数据
        """
        import random  # 确保这里有这行！
        protocol_type = self._detect_protocol(packet_meta.dst_port)
        
        if protocol_type == 'modbus':
            return self._parse_modbus(packet_meta, raw_data)
        elif protocol_type == 's7comm':
            return self._parse_s7comm(packet_meta, raw_data)
        else:
            # 未知协议或未实现解析
            return ProtocolData(protocol_type='unknown')
    
    def _detect_protocol(self, dst_port: int) -> str:
        """
        根据目标端口检测协议类型
        
        Args:
            dst_port: 目标端口号
            
        Returns:
            协议类型字符串
        """
        return self.PROTOCOL_PORTS.get(dst_port, 'unknown')
    
    def _parse_modbus(self, packet_meta: PacketMetadata, raw_data: bytes = None) -> ProtocolData:
        """
        解析Modbus/TCP数据包
        
        Args:
            packet_meta: 数据包元数据
            raw_data: 原始数据（可选）
            
        Returns:
            解析后的Modbus协议数据
        """
        import random  # 确保这里有这行！
        # 创建基础协议数据
        proto_data = ProtocolData(protocol_type='modbus')
        
        try:
            # 模拟解析过程 - 实际项目中会根据raw_data解析
            # 这里我们根据数据包特征模拟解析结果
            
            # 判断是请求还是响应
            is_request = packet_meta.direction == 'request'
            
            if is_request:
                # 请求包：随机生成合理的Modbus参数
                import random
                
                # 选择功能码
                allowed_codes = self.protocol_config.get('modbus', {}).get('function_codes', [1, 3, 5, 6])
                proto_data.function_code = random.choice(allowed_codes)
                
                # 事务ID和单元ID
                proto_data.transaction_id = random.randint(1, 1000)
                proto_data.unit_id = random.randint(1, 247)
                
                # 根据功能码设置地址和数量
                if proto_data.function_code in [1, 2, 3, 4]:  # 读操作
                    if proto_data.function_code in [1, 2]:  # 线圈/离散输入
                        address_range = self.protocol_config.get('modbus', {}).get('coil_range', [0, 9999])
                    else:  # 保持/输入寄存器
                        address_range = self.protocol_config.get('modbus', {}).get('holding_range', [40000, 49999])
                    
                    proto_data.starting_address = random.randint(
                        address_range[0], address_range[1] - 10
                    )
                    proto_data.quantity = random.randint(1, 10)
                    
                elif proto_data.function_code in [5, 6]:  # 写单个
                    address_range = self.protocol_config.get('modbus', {}).get('holding_range', [40000, 49999])
                    proto_data.starting_address = random.randint(
                        address_range[0], address_range[1]
                    )
                    proto_data.quantity = 1
                    
                    # 模拟写入值
                    if proto_data.function_code == 5:  # 写线圈
                        proto_data.coil_values = bytes([random.choice([0x00, 0xFF])])
                    else:  # 写寄存器
                        proto_data.values = [random.uniform(0, 100)]
                        
                elif proto_data.function_code in [15, 16]:  # 写多个
                    address_range = self.protocol_config.get('modbus', {}).get('holding_range', [40000, 49999])
                    proto_data.starting_address = random.randint(
                        address_range[0], address_range[1] - 5
                    )
                    proto_data.quantity = random.randint(2, 5)
                    
                    # 模拟多个写入值
                    proto_data.values = [random.uniform(0, 100) for _ in range(proto_data.quantity)]
            
            else:
                # 响应包：基于请求的特征生成响应
                # 这里简化处理，实际应该根据之前的请求生成匹配的响应
                proto_data.function_code = 3  # 默认读响应
                proto_data.transaction_id = random.randint(1, 1000)
                proto_data.unit_id = random.randint(1, 247)
                proto_data.starting_address = random.randint(40000, 40050)
                proto_data.quantity = 1
                
                # 生成响应值
                proto_data.values = [random.uniform(20.0, 80.0)]
            
            return proto_data
            
        except Exception as e:
            print(f"[解析器] Modbus解析错误: {e}")
            return proto_data
    
    def _parse_s7comm(self, packet_meta: PacketMetadata, raw_data: bytes = None) -> ProtocolData:
        """
        解析S7COMM数据包（西门子S7协议）
        
        Args:
            packet_meta: 数据包元数据
            raw_data: 原始数据
            
        Returns:
            解析后的S7COMM协议数据
        """
        proto_data = ProtocolData(protocol_type='s7comm')
        
        try:
            # S7COMM协议解析
            # 协议结构: [TPKT][ISO-COTP][S7 Header][Parameters/Data]
            
            is_request = packet_meta.direction == 'request'
            
            if is_request:
                proto_data.rosctr = 1  # 请求
                proto_data.function_code = 0x04  # 读变量
                
                # 模拟参数和数据
                proto_data.parameter = bytes([0x12, 0x0A, 0x10, 0x00])
            else:
                proto_data.rosctr = 7  # 响应
                proto_data.function_code = 0x00
                proto_data.data = bytes([0xFF, 0x03, 0x00, 0x10])
                
            return proto_data
            
        except Exception as e:
            print(f"[解析器] S7COMM解析错误: {e}")
            return proto_data
    
    def extract_numeric_value(self, proto_data: ProtocolData) -> Optional[float]:
        """
        从协议数据中提取数值
        
        Args:
            proto_data: 协议数据
            
        Returns:
            提取的数值，如果没有则返回None
        """
        if not proto_data:
            return None
        
        # 检查是否是写操作或包含数据的响应
        is_data_operation = (
            proto_data.protocol_type == 'modbus' and
            proto_data.function_code in [5, 6, 15, 16]
        ) or (
            proto_data.protocol_type == 'modbus' and 
            proto_data.values and len(proto_data.values) > 0
        )
        
        if not is_data_operation:
            return None
        
        # 提取数值
        if proto_data.values and len(proto_data.values) > 0:
            return float(proto_data.values[0])
        elif proto_data.coil_values:
            return float(proto_data.coil_values[0])
        
        return None
    
    def extract_parameter_address(self, proto_data: ProtocolData) -> Optional[int]:
        """
        从协议数据中提取参数地址
        
        Args:
            proto_data: 协议数据
            
        Returns:
            参数地址，如果没有则返回None
        """
        if not proto_data:
            return None
        
        if proto_data.starting_address is not None:
            return proto_data.starting_address
        
        return None
    
    def is_data_operation(self, proto_data: ProtocolData) -> bool:
        """
        判断是否是数据操作（读/写数据）
        
        Args:
            proto_data: 协议数据
            
        Returns:
            如果是数据操作返回True，否则返回False
        """
        if not proto_data or proto_data.protocol_type != 'modbus':
            return False
        
        # Modbus数据操作功能码
        data_function_codes = [1, 2, 3, 4, 5, 6, 15, 16]
        
        return proto_data.function_code in data_function_codes
    
    def generate_parsed_summary(self, packet_meta: PacketMetadata, proto_data: ProtocolData) -> Dict[str, Any]:
        """
        生成解析摘要
        
        Args:
            packet_meta: 数据包元数据
            proto_data: 协议数据
            
        Returns:
            解析摘要字典
        """
        summary = {
            'timestamp': packet_meta.timestamp.isoformat(),
            'src_ip': packet_meta.src_ip,
            'dst_ip': packet_meta.dst_ip,
            'protocol': proto_data.protocol_type,
            'direction': packet_meta.direction
        }
        
        # 添加协议特定信息
        if proto_data.protocol_type == 'modbus':
            summary.update({
                'function_code': proto_data.function_code,
                'function_name': self.MODBUS_FUNCTIONS.get(proto_data.function_code, 'Unknown'),
                'address': proto_data.starting_address,
                'quantity': proto_data.quantity,
                'has_data': len(proto_data.values) > 0 or proto_data.coil_values is not None
            })
        elif proto_data.protocol_type == 's7comm':
            summary.update({
                'rosctr': proto_data.rosctr,
                'function_code': proto_data.function_code
            })
        
        return summary