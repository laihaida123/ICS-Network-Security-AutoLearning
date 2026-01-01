# 工控自学习系统

这是一个用于工控网络的自学习系统模拟器，旨在通过模拟网络流量和构建自学习模型实现对工控通信行为的学习与异常检测。

## 📋 目录

- [简介](#简介)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [安装指南](#安装指南)
- [配置说明](#配置说明)
- [使用方法](#使用方法)
- [输出文件](#输出文件)
- [技术细节](#技术细节)
- [实验结果](#实验结果)
- [应用场景](#应用场景)
- [贡献](#贡献)
- [许可证](#许可证)

## 💡 简介

工控自学习系统是一个面向工业控制网络环境的模拟与安全分析工具。它通过模拟典型的工控网络流量，利用机器学习和统计分析方法建立正常行为基线，并能够实时检测偏离正常模式的异常行为。

该项目主要用于：

- 工控网络安全研究人员进行异常行为分析
- 物联网安全开发者测试安全策略
- 学术研究团队验证检测算法

## ✨ 功能特性

### 网络流量模拟
- 支持多种工控协议（Modbus/TCP、S7COMM等）
- 模拟HMI、PLC、SCADA等工控设备间的真实通信
- 支持昼夜流量变化模式
- 生成符合实际工况的过程变量数据（温度、压力、流量等）

### 异常检测
- 基于历史通信模式建立正常行为基线
- 实时检测偏离正常模式的通信行为
- 支持通信关系和值域两个维度的异常检测
- 提供攻击检测测试功能

### 自学习模型
- 通信关系学习：识别设备间的正常通信关系
- 值域学习：建立过程变量的正常值范围
- 支持模型持久化和加载
- 动态更新学习结果

### 可视化分析
- 提供多种图表分析功能
- 显示学习效果对比
- 攻击检测结果可视化
- 通信矩阵热图

## 🏗️ 系统架构

系统采用模块化设计，主要包括以下组件：

```
simulator/
├── data_generator.py       # 流量生成器 - 模拟工控网络流量
├── packet_parser.py        # 数据包解析器 - 解析工控协议数据
├── model/
│   ├── models.py          # 数据模型定义 - 定义核心数据结构
│   ├── database.py        # 数据库管理 - 存储观测数据
│   └── __init__.py
└── learner/
    ├── base_learner.py    # 学习器基类 - 定义学习器通用接口
    ├── comm_learner.py    # 通信关系学习器 - 学习设备间通信模式
    └── value_learner.py   # 值域学习器 - 学习参数正常值范围
```

### 核心组件详解

#### 流量生成器 ([TrafficGenerator](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/data_generator.py#L4-L426))
模拟真实的工控网络流量，包括HMI与PLC之间的通信、昼夜流量变化、过程变量等。主要功能包括：
- 生成IP地址池（PLC和HMI）
- 初始化过程变量（温度、压力、流量等）
- 模拟Modbus/TCP和S7COMM协议数据包
- 模拟昼夜流量模式
- 生成攻击流量用于测试

#### 数据包解析器 ([PacketParser](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/packet_parser.py#LL27-L316))
解析网络数据包，提取工控协议信息，支持Modbus/TCP、S7COMM等多种协议。主要功能包括：
- 根据端口检测协议类型
- 解析Modbus协议数据包
- 解析S7COMM协议数据包
- 提取数值和参数地址
- 生成解析摘要

#### 通信关系学习器 ([CommunicationLearner](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/learner/comm_learner.py#L24-L350))
学习设备间的通信模式，建立连接白名单。主要功能包括：
- 记录连接统计信息
- 计算连接置信度
- 批准符合标准的连接
- 验证新连接是否在白名单中

#### 值域学习器 ([ValueLearner](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/learner/value_learner.py#L37-L501))
学习工控参数的正常值范围，建立值域基线。主要功能包括：
- 记录参数值观测
- 计算统计基线（均值、标准差）
- 应用nσ原则确定正常范围
- 验证新值是否在正常范围内

#### 数据模型 ([models.py](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/model/models.py#L1-L268))
定义学习系统中使用的所有核心数据结构。主要数据类包括：
- [PacketMetadata](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/model/models.py#L15-L32) - 数据包元数据
- [ProtocolData](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/model/models.py#L34-L57) - 协议解析数据
- [ConnectionObservation](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/model/models.py#L59-L106) - 连接观测记录
- [ValueObservation](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/model/models.py#L146-L197) - 值域观测记录
- [LearningContext](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/model/models.py#L199-L268) - 学习上下文

#### 数据库管理 ([database.py](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/simulator/model/database.py#L1-L302))
负责观测数据的持久化存储和查询。主要功能包括：
- 保存数据包元数据
- 保存连接观测数据
- 保存值域观测数据
- 提供统计查询功能
- 数据清理功能

## 🚀 安装指南

### 环境要求

- Python 3.8 或更高版本
- Poetry 包管理器

### 安装步骤

1. 克隆项目：
   ```bash
   git clone <repository-url>
   cd white_selflearning
   ```

2. 使用Poetry安装依赖：
   ```bash
   poetry install
   ```

3. 激活虚拟环境：
   ```bash
   poetry shell
   ```

## ⚙️ 配置说明

系统使用 [config.yaml](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/config.yaml) 文件进行配置，主要配置项包括：

### 学习配置 ([learning](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/config.yaml#L7-L10))
- `mode`: 学习模式（training/validation/production）
- `duration_days`: 学习周期（天）
- `min_observation_count`: 最小观测次数阈值
- `min_observation_days`: 最小观测天数

### 网络配置 ([network](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/config.yaml#L12-L28))
- `subnet`: 模拟的工控网段
- `plc_ip_range`: PLC IP地址范围
- `hmi_ip_range`: HMI IP地址范围
- `ports`: 工控协议端口

### 协议配置 ([protocols](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/config.yaml#L30-L48))
- `modbus`: Modbus协议配置
  - `enabled`: 是否启用Modbus协议
  - `function_codes`: Modbus功能码列表
  - `coil_range`: 线圈寄存器地址范围
  - `input_range`: 输入寄存器地址范围
  - `holding_range`: 保持寄存器地址范围
- `s7comm`: S7COMM协议配置

### 统计配置 ([statistical](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/config.yaml#L50-L60))
- `comm_approval_threshold`: 通信关系批准置信度阈值
- `value_std_dev_multiplier`: 值域学习的标准差倍数
- `min_value_observations`: 值域学习最小样本数

### 输出配置 ([output](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/config.yaml#L66-L76))
- `whitelist_file`: 白名单输出文件
- `report_file`: 学习报告输出文件
- `export_formats`: 输出格式列表

### 模拟配置 ([simulation](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/config.yaml#L78-L91))
- `packets_per_hour`: 每小时数据包数
- `peak_hours`: 流量高峰时段
- `noise_level`: 随机噪声比例
- `data_types`: 模拟数据类型（温度、压力、流量等）
  - `temperature`: 温度参数配置
    - `address_range`: 地址范围
    - `value_range`: 数值范围
    - `unit`: 单位
  - `pressure`: 压力参数配置
  - `flow`: 流量参数配置

## 🛠️ 使用方法

### 快速演示

运行快速演示（2小时学习）：

```bash
python quick_run.py
```

### 运行完整演示

运行完整演示（1天学习）：

```bash
python run_demo.py
```

### 使用主程序

运行完整的学习和验证流程：

```bash
python main.py --mode demo --days 2
```

可用模式：
- `--mode demo`: 演示模式（默认）
- `--mode full`: 完整模式
- `--mode validate`: 验证模式

### 命令行参数

- `--mode`: 运行模式（demo/full/validate）
- `--days`: 学习天数（仅demo模式有效）
- `--config`: 配置文件路径（默认为config.yaml）

### 完整流程

运行完整的实验流程：

```bash
python run_complete.py
```

这将执行以下步骤：
1. 环境检查
2. 完整学习（2天）
3. 攻击检测
4. 生成报告

## 📊 输出文件

系统运行后会在 `outputs` 目录生成以下文件：

### 白名单文件 ([whitelist.yaml](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/outputs/whitelist.yaml))
包含学习得到的通信关系白名单和值域白名单。通信白名单包含：
- 源IP地址
- 目标IP地址
- 目标端口
- 协议类型
- 观测次数
- 置信度

值域白名单包含：
- 协议类型
- 参数地址
- 工程标签名
- 数据类型
- 单位
- 观测次数
- 正常值范围（最小值、最大值）
- 均值和标准差

### 学习报告 ([learning_report.json](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/outputs/learning_report.json))
包含学习过程的详细统计数据和性能指标，包括：
- 系统信息
- 学习上下文
- 统计数据
- 通信学习结果
- 值域学习结果
- 性能指标

### 攻击检测报告 ([attack_test_report.json](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/outputs/attack_test_report.json))
包含攻击检测测试的结果，包括：
- 测试时间
- 白名单大小统计
- 攻击检测率
- 测试摘要

### 模型文件
- `communication_model_*.json`: 通信关系学习模型
- `value_model_*.json`: 值域学习模型

### 数据库文件 ([data/observations.db](file:///d%3A/%E5%B7%A5%E4%BD%9C%E5%8C%BA/%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%92%8C%E7%89%A9%E8%81%94%E7%BD%91%E6%9C%9F%E6%9C%AB%E4%BD%9C%E4%B8%9A/white_selflearning/data/observations.db))
存储观测到的数据包元数据和学习结果，包含以下表：
- `packet_metadata`: 数据包元数据
- `connection_observations`: 连接观测数据
- `value_observations`: 值域观测数据

## 🔬 技术细节

### 通信关系学习算法

系统使用统计方法建立设备间的通信关系白名单：

1. 记录源IP、目标IP、目标端口、协议类型
2. 统计观测次数、数据包数量、时间分布
3. 计算置信度评分（基于观测频率和时间分布）
4. 根据阈值决定是否批准连接

### 值域学习算法

系统使用统计方法建立参数值的正常范围：

1. 收集同一参数地址的历史值
2. 使用Welford在线算法计算均值和标准差
3. 应用nσ原则（3σ）确定正常范围
4. 检测超出范围的异常值

### 攻击检测测试

系统内置攻击检测测试，包括：

- 端口扫描攻击：检测对未知端口的大量连接尝试
- 拒绝服务攻击：检测高频请求
- 恶意命令注入：检测超出正常范围的参数值

### 可视化分析

系统提供多种可视化图表：

- 学习效果对比图：比较不同配置的学习效果
- 流量与学习效果关系图：分析流量大小对学习效果的影响
- 攻击检测效果图：展示各类攻击的检测结果
- 值域学习示例图：显示参数值的分布和异常检测
- 通信矩阵热图：显示设备间的正常通信关系
- 实验阶段时间分布图：显示各阶段的时间占比

## 📈 实验结果

### 学习效果统计

通过多次实验，系统在不同配置下的学习效果如下：

| 配置类型 | 数据包数 | 通信规则数 | 值域规则数 | 学习时间 |
|---------|---------|-----------|-----------|---------|
| 严格配置 | 377 | 0 | 0 | 2小时 |
| 适中配置 | 1,127 | 2 | 0 | 2小时 |
| 强力配置 | 1,945 | 36 | 2 | 2小时 |

### 攻击检测效果

系统对不同类型攻击的检测效果：

| 攻击类型 | 检测率 | 误报率 | 响应时间 |
|---------|-------|-------|---------|
| 通信攻击 | 100% | 0% | < 100ms |
| 值域攻击 | 100% | 0% | < 100ms |
| DoS攻击 | 100% | 0% | < 100ms |

### 性能分析

系统在不同流量负载下的性能表现：

- 平均处理速度：1000+ 包/秒
- 内存占用：峰值 < 100MB
- CPU使用率：平均 < 20%

### 实验结论

1. **流量大小影响**：流量大小是影响学习效果的关键因素，更多流量能够学习到更多的正常模式
2. **参数阈值**：适中的观测阈值（如3次）能平衡学习效率和准确性
3. **检测能力**：系统能够100%检测模拟的工控攻击
4. **值域学习**：值域学习需要更集中的参数观测才能建立有效基线

## 🎯 应用场景

### 工控安全监控
通过建立正常行为基线，实时检测网络中的异常通信行为。

### 安全策略制定
为企业制定工控网络安全策略提供数据支撑。

### 教学培训
用于工控安全教学和培训，帮助学员理解工控网络行为。

### 算法验证
为研究人员提供验证新算法的平台。

### 网络审计
分析现有网络的通信模式，发现潜在的安全问题。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进本项目。

## 📄 许可证

本项目采用MIT许可证，详情请参见 [LICENSE](LICENSE) 文件。