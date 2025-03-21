#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目配置文件
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量（如果有.env文件）
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# 当前环境
ENV = os.getenv("ENV", "dev")

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

# 数据目录
DATA_DIR = BASE_DIR / 'dynamic_graph_rag' / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
SIMULATED_DATA_DIR = DATA_DIR / 'simulated'

# 确保所有数据目录存在
for dir_path in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, SIMULATED_DATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 数据目录字典（兼容旧代码）
DATA_DIRS = {
    "raw": RAW_DATA_DIR,
    "processed": PROCESSED_DATA_DIR,
    "simulated": SIMULATED_DATA_DIR
}

# 时间范围默认配置
DEFAULT_TIME_RANGE = {
    "short": "-1h",    # 短期：1小时
    "medium": "-1d",   # 中期：1天
    "long": "-30d",    # 长期：30天
    "default": "-7d"   # 默认：7天
}

# Neo4j图数据库配置
GRAPH_DB_CONFIG = {
    "uri": os.getenv("NEO4J_URI", "bolt://localhost:7688"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "graphrag_password"),
    "database": os.getenv("NEO4J_DATABASE", "neo4j")
}

# InfluxDB时序数据库配置
INFLUXDB_CONFIG = {
    "url": os.getenv("INFLUXDB_URL", "http://localhost:8087"),
    "token": os.getenv("INFLUXDB_TOKEN", "graphrag_token"),
    "org": os.getenv("INFLUXDB_ORG", "graphrag_org"),
    "bucket": os.getenv("INFLUXDB_BUCKET", "metrics"),
    "timeout": int(os.getenv("INFLUXDB_TIMEOUT", "30000"))
}

# 节点类型配置
NODE_TYPES = [
    "DC",          # 数据中心
    "TENANT",      # 租户
    "NE",          # 网元
    "VM",          # 虚拟机
    "HOST",        # 物理主机
    "HOSTGROUP",   # 主机组
    "TRU",         # 存储池
]

# 边类型配置
EDGE_TYPES = [
    "HAS_TENANT",   # 拥有租户关系
    "HAS_NE",       # 拥有网元关系
    "HAS_VM",       # 拥有虚拟机关系
    "DEPLOYED_ON",  # 部署于关系
    "BELONGS_TO",   # 属于关系
    "HAS_STORAGE",  # 拥有存储关系
]

# 时序数据指标配置
METRICS = {
    "VM": [
        {"name": "cpu_usage", "unit": "%", "sampling_interval": "60s"},
        {"name": "mem_usage", "unit": "%", "sampling_interval": "60s"},
        {"name": "disk_io", "unit": "IOPS", "sampling_interval": "60s"},
        {"name": "network_throughput", "unit": "Mbps", "sampling_interval": "60s"}
    ],
    "HOST": [
        {"name": "cpu_usage", "unit": "%", "sampling_interval": "60s"},
        {"name": "mem_usage", "unit": "%", "sampling_interval": "60s"},
        {"name": "disk_usage", "unit": "%", "sampling_interval": "60s"},
        {"name": "temperature", "unit": "°C", "sampling_interval": "300s"}
    ],
    "NE": [
        {"name": "load", "unit": "%", "sampling_interval": "60s"},
        {"name": "response_time", "unit": "ms", "sampling_interval": "60s"},
        {"name": "success_rate", "unit": "%", "sampling_interval": "60s"},
        {"name": "resource_usage", "unit": "%", "sampling_interval": "60s"}
    ],
    "TRU": [
        {"name": "usage", "unit": "%", "sampling_interval": "300s"},
        {"name": "iops", "unit": "IOPS", "sampling_interval": "60s"},
        {"name": "latency", "unit": "ms", "sampling_interval": "60s"},
        {"name": "read_write_ratio", "unit": "ratio", "sampling_interval": "300s"}
    ],
    "HOSTGROUP": [
        {"name": "agg_cpu_usage", "unit": "%", "sampling_interval": "60s"},
        {"name": "agg_mem_usage", "unit": "%", "sampling_interval": "60s"},
        {"name": "load_balance", "unit": "%", "sampling_interval": "300s"}
    ]
}

# 数据保留策略（天）
RETENTION_POLICIES = {
    "raw_metrics": 30,      # 原始指标数据保留30天
    "hourly_rollups": 90,   # 每小时汇总数据保留90天
    "daily_rollups": 365    # 每日汇总数据保留365天
}

# 日志配置
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": LOG_DIR / "graphrag.log"
}

# 身份验证和安全配置
AUTH_CONFIG = {
    "require_auth": os.getenv("REQUIRE_AUTH", "false").lower() == "true",
    "token_expiry": int(os.getenv("TOKEN_EXPIRY", "86400")),  # 默认24小时
    "api_key": os.getenv("API_KEY", "")
}

# API配置
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000")),
    "debug": os.getenv("API_DEBUG", "false").lower() == "true",
    "workers": int(os.getenv("API_WORKERS", "4"))
}

# LM Studio配置
LMSTUDIO_CONFIG = {
    "base_url": os.getenv("LMSTUDIO_BASE_URL", "http://localhost:12343"),
    # "model": os.getenv("LMSTUDIO_MODEL", "deepseek-r1-distill-qwen-32b"),
    "model": os.getenv("LMSTUDIO_MODEL", "mistral-small-3.1-24b-instruct-2503"),
    "max_tokens": int(os.getenv("LMSTUDIO_MAX_TOKENS", "2048")),
    "temperature": float(os.getenv("LMSTUDIO_TEMPERATURE", "0.7")),
    "top_p": float(os.getenv("LMSTUDIO_TOP_P", "0.9")),
    "timeout": int(os.getenv("LMSTUDIO_TIMEOUT", "30000"))
}

# Ollama配置
OLLAMA_CONFIG = {
    "api_base": os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
    "model_name": os.getenv("OLLAMA_MODEL_NAME", "deepseek-r1:32b"),
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))
}

# vLLM配置
VLLM_CONFIG = {
    "api_url": os.getenv("VLLM_API_URL", "http://localhost:8000/v1"),
    "model_name": os.getenv("VLLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-1M"),
    "temperature": float(os.getenv("VLLM_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("VLLM_MAX_TOKENS", "1024"))
}

# 兼容性函数，用于获取配置（兼容旧代码）
def get_neo4j_config():
    return GRAPH_DB_CONFIG

def get_influxdb_config():
    return INFLUXDB_CONFIG

def get_lmstudio_config():
    return LMSTUDIO_CONFIG

def get_ollama_config():
    return OLLAMA_CONFIG

def get_vllm_config():
    return VLLM_CONFIG 