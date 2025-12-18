FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 优化 1: 更换 APT 源为阿里云镜像 (针对 Debian Bookworm/Trixie)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 优化 2: 使用清华 PyPI 镜像安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Playwright 浏览器和系统依赖
# 优化 3: Playwright 下载也可能慢，这取决于网络，通常很难加速，
# 但 install-deps 依赖 apt，上面换源后会快很多。
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

# 启动命令
CMD ["python", "http_server.py"]
