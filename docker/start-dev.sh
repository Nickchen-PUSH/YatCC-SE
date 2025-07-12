#!/bin/bash

# YatCC-SE 开发环境启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 启动 YatCC-SE 开发环境..."

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 进入 docker 目录
cd "$SCRIPT_DIR"

# 检查是否是首次运行
if ! docker image ls | grep -q yatcc-se-dev; then
    echo "📦 首次运行，正在构建开发镜像..."
    docker-compose -f docker-compose.dev.yml build
fi

# 启动服务
echo "🔧 启动开发服务..."
docker-compose -f docker-compose.dev.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "✅ 开发环境启动成功!"
    echo ""
    echo "📋 访问信息:"
    echo "  🌐 管理端:     http://localhost:5001"
    echo "  🌐 学生端:     http://localhost:5002"
    echo "  🔧 VS Code:    http://localhost:8080"
    echo "  📊 Redis:      localhost:6379"
    echo "  🔐 SSH:        ssh devuser@localhost -p 2222 (密码: devuser)"
    echo ""
    echo "📝 常用命令:"
    echo "  查看日志:     docker-compose -f docker-compose.dev.yml logs -f"
    echo "  进入容器:     docker exec -it yatcc-se-dev bash"
    echo "  停止服务:     docker-compose -f docker-compose.dev.yml down"
    echo ""
    echo "📚 详细文档请查看: docker/README.md"
else
    echo "❌ 服务启动失败，请查看日志:"
    docker-compose -f docker-compose.dev.yml logs
    exit 1
fi
