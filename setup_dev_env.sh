#!/bin/bash
# 开发环境安装脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GraphRAG统一查询层项目 - 开发环境安装 ===${NC}"
echo

# 检查Docker
echo -e "${YELLOW}检查Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker未安装，请先安装Docker${NC}"
    echo "请访问 https://docs.docker.com/get-docker/ 获取安装指南"
    exit 1
fi
echo -e "${GREEN}Docker已安装√${NC}"

# 检查Python版本
echo -e "${YELLOW}检查Python版本...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 10 ]; then
    echo -e "${RED}Python版本过低，需要Python 3.10+${NC}"
    echo "当前版本: $PYTHON_VERSION"
    exit 1
fi
echo -e "${GREEN}Python版本符合要求: $PYTHON_VERSION√${NC}"

# 创建数据目录
echo -e "${YELLOW}创建项目数据目录...${NC}"
mkdir -p dynamic_graph_rag/data/{raw,processed,simulated}
echo -e "${GREEN}数据目录创建完成√${NC}"

# 提示用户选择安装方式
echo
echo -e "${BLUE}请选择环境设置方式:${NC}"
echo "1) 使用pip (Python虚拟环境)"
echo "2) 使用Conda"
echo "3) 使用Poetry"
read -p "请输入选项 (1-3): " OPTION

case $OPTION in
    1)
        echo -e "${YELLOW}使用pip创建虚拟环境...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        echo -e "${GREEN}虚拟环境创建完成，已安装依赖√${NC}"
        echo -e "${YELLOW}激活命令: source venv/bin/activate${NC}"
        ;;
    2)
        echo -e "${YELLOW}检查Conda...${NC}"
        if ! command -v conda &> /dev/null; then
            echo -e "${RED}Conda未安装，请先安装Conda${NC}"
            echo "请访问 https://docs.conda.io/projects/conda/en/latest/user-guide/install/ 获取安装指南"
            exit 1
        fi
        echo -e "${GREEN}Conda已安装√${NC}"
        
        echo -e "${YELLOW}创建Conda环境...${NC}"
        conda create -y -n graphrag python=3.10
        conda activate graphrag
        pip install --upgrade pip
        pip install -r requirements.txt
        echo -e "${GREEN}Conda环境创建完成，已安装依赖√${NC}"
        echo -e "${YELLOW}激活命令: conda activate graphrag${NC}"
        ;;
    3)
        echo -e "${YELLOW}检查Poetry...${NC}"
        if ! command -v poetry &> /dev/null; then
            echo -e "${RED}Poetry未安装，正在安装...${NC}"
            curl -sSL https://install.python-poetry.org | python3 -
        fi
        echo -e "${GREEN}Poetry已安装√${NC}"
        
        echo -e "${YELLOW}使用Poetry安装依赖...${NC}"
        poetry install
        echo -e "${GREEN}Poetry环境设置完成√${NC}"
        echo -e "${YELLOW}激活命令: poetry shell${NC}"
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo
echo -e "${BLUE}=== 开发环境设置完成 ===${NC}"
echo -e "${YELLOW}下一步:${NC}"
echo "1. 部署Neo4j和InfluxDB (参考docs/infrastructure_deployment.md)"
echo "2. 运行连接测试: python -m dynamic_graph_rag.tests.connection_test"
echo "3. 开始开发!"
echo

echo -e "${GREEN}祝您开发顺利!${NC}" 