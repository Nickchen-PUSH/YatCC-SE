# YatCC-SE Dockerfile
# 优化版本，适用于云容器服务
# Multi-stage build for smaller image size and better security

# ============================================================================
# Stage 1: Base image with system dependencies
# ============================================================================
FROM ubuntu:24.04 AS base

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 更新包管理器并安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python 运行环境
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    # Redis 服务器
    redis-server \
    # SSH 服务器
    openssh-server \
    # 系统工具
    ca-certificates \
    curl \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 配置 SSH 服务
RUN mkdir -p /run/sshd /var/run/sshd \
    && ssh-keygen -A

# ============================================================================
# Stage 2: Python dependencies
# ============================================================================
FROM base AS python-deps

WORKDIR /app

# 创建 Python 虚拟环境
RUN python3 -m venv venv

# 激活虚拟环境并安装 Python 包
RUN . venv/bin/activate && pip install \
    'flask[async]' gunicorn redis cryptography httpx \
    'flask-openapi3[swagger, rapipdf, rapidoc]' kubernetes

# ============================================================================
# Stage 3: Build frontend (if needed)
# ============================================================================
FROM node:20.12.2-alpine AS frontend-builder

# 如果有前端代码，在这里构建
COPY stu-site/ /stu-site/
WORKDIR /stu-site/
RUN npm install
RUN npm run build

COPY adm-site/ /adm-site/
WORKDIR /adm-site/
RUN npm install
RUN npm run build

# ============================================================================
# Stage 4: Application assembly
# ============================================================================
FROM python-deps AS app-builder

# 复制应用文件
COPY base /app/base
COPY cluster /app/cluster
COPY core /app/core
COPY run /app/run
COPY scripts /app/scripts
COPY test /app/test
COPY svc_stu.py svc_adm.py util.py entry.py /app/

# 复制配置文件和启动脚本
COPY run/yatcc-se/config.py /app/
COPY run/yatcc-se/YatCC-SE /YatCC-SE

# 设置正确的权限
RUN chmod +x /YatCC-SE

# 复制前端构建结果
COPY --from=frontend-builder /stu-site/dist /app/stu-site
COPY --from=frontend-builder /adm-site/dist /app/adm-site

# ============================================================================
# Stage 5: Production image
# ============================================================================
FROM base AS production

# 从构建阶段复制应用
COPY --from=app-builder /app /app
COPY --from=app-builder /YatCC-SE /YatCC-SE

# 设置工作目录
WORKDIR /app

# 暴露端口
EXPOSE 22 5001 5002

# 设置卷
VOLUME ["/io"]

# 设置标签（生产环境元数据）
LABEL maintainer="YatCC-SE Team" \
    version="1.0" \
    description="YatCC-SE Production Image" \
    org.opencontainers.image.title="YatCC-SE" \
    org.opencontainers.image.description="Young Architect Training Course Collection - Software Engineering" \
    org.opencontainers.image.vendor="YatCC-SE Team" \
    org.opencontainers.image.version="1.0"

# 入口点
ENTRYPOINT ["/YatCC-SE"]
