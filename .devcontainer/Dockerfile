FROM ubuntu:24.04

# 避免交互式安装过程中的提示
ENV DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /workspace

# 安装必要的包
RUN apt-get update && apt-get install -y \
    curl wget git vim nano tree htop \
    python3 python3-pip python3-venv python3-dev \
    redis kubectl make gcc g++ sudo \
    && rm -rf /var/lib/apt/lists/*

# 安装 minikube
RUN curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 \
    && install minikube-linux-amd64 /usr/local/bin/minikube \
    && rm minikube-linux-amd64

# 安装 Docker
RUN curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh get-docker.sh \
    && rm get-docker.sh

# 创建 Python 虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install \
    'flask[async]' gunicorn redis cryptography httpx locust \
    'flask-openapi3[swagger, redoc, rapidoc, rapipdf, scalar, elements]' \
    coverage kubernetes pytest pytest-asyncio pytest-cov \
    black isort flake8 mypy

# 创建开发用户
RUN useradd -m -s /bin/bash developer \
    && usermod -aG docker developer \
    && echo "developer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# 设置 Git 配置
RUN git config --global --add safe.directory /workspace

USER developer
ENV PYTHONPATH="/workspace:$PYTHONPATH"
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 5000 8080 8443
CMD ["/bin/bash"]