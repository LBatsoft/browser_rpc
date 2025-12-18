FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 优化 1: 更换 APT 源为阿里云镜像
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统依赖 (手动列出 Chromium 所需依赖，适配 Debian)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 优化 2: 使用清华 PyPI 镜像安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Playwright 浏览器 (跳过 install-deps，因为上面已经手动安装了)
RUN playwright install chromium

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
