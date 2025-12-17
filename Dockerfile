FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖和 Playwright 依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器和系统依赖
# 注意：chromium 是必须的
RUN playwright install chromium
RUN playwright install-deps chromium

# 复制源代码
COPY . .

# 编译 proto 文件
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/spider.proto

# 创建日志目录
RUN mkdir -p log

# 暴露端口
EXPOSE 8000 50051

# 启动命令 (默认启动 HTTP Server)
CMD ["python", "http_server.py"]

