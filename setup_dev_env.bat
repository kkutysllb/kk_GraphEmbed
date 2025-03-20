@echo off
REM GraphRAG统一查询层项目 - Windows开发环境安装脚本

echo === GraphRAG统一查询层项目 - 开发环境安装 ===
echo.

REM 检查Docker
echo 检查Docker...
docker --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Docker未安装，请先安装Docker
    echo 请访问 https://docs.docker.com/get-docker/ 获取安装指南
    exit /b 1
)
echo Docker已安装√

REM 检查Python版本
echo 检查Python版本...
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python未安装，请先安装Python 3.10+
    exit /b 1
)
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
echo Python版本: %PYTHON_VERSION%

REM 创建数据目录
echo 创建项目数据目录...
mkdir dynamic_graph_rag\data\raw 2>nul
mkdir dynamic_graph_rag\data\processed 2>nul
mkdir dynamic_graph_rag\data\simulated 2>nul
echo 数据目录创建完成√

REM 提示用户选择安装方式
echo.
echo 请选择环境设置方式:
echo 1) 使用pip (Python虚拟环境)
echo 2) 使用Conda
echo 3) 使用Poetry
set /p OPTION="请输入选项 (1-3): "

if "%OPTION%"=="1" (
    echo 使用pip创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
    echo 虚拟环境创建完成，已安装依赖√
    echo 激活命令: venv\Scripts\activate.bat
) else if "%OPTION%"=="2" (
    echo 检查Conda...
    conda --version > nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Conda未安装，请先安装Conda
        echo 请访问 https://docs.conda.io/projects/conda/en/latest/user-guide/install/ 获取安装指南
        exit /b 1
    )
    echo Conda已安装√
    
    echo 创建Conda环境...
    conda create -y -n graphrag python=3.10
    call conda activate graphrag
    pip install --upgrade pip
    pip install -r requirements.txt
    echo Conda环境创建完成，已安装依赖√
    echo 激活命令: conda activate graphrag
) else if "%OPTION%"=="3" (
    echo 检查Poetry...
    poetry --version > nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Poetry未安装，请先安装Poetry
        echo 可以使用以下命令安装: 
        echo (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content ^| python -
        exit /b 1
    )
    echo Poetry已安装√
    
    echo 使用Poetry安装依赖...
    poetry install
    echo Poetry环境设置完成√
    echo 激活命令: poetry shell
) else (
    echo 无效选项
    exit /b 1
)

echo.
echo === 开发环境设置完成 ===
echo 下一步:
echo 1. 部署Neo4j和InfluxDB (参考docs/infrastructure_deployment.md)
echo 2. 运行连接测试: python -m dynamic_graph_rag.tests.connection_test
echo 3. 开始开发!
echo.

echo 祝您开发顺利! 