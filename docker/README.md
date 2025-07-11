# YatCC-SE Docker 开发环境配置

本文档介绍如何配置和使用 YatCC-SE 的 Docker 开发环境。

## � 文件结构

```
YatCC-SE/
├── docker-compose.yml          # 主要的开发环境配置
├── start-dev-env.sh           # 快速启动脚本
├── docker/
│   ├── Dockerfile.dev         # 开发环境 Dockerfile
│   ├── docker-compose.dev.yml # 备用的开发配置
│   ├── supervisord.conf       # 进程管理配置
│   ├── start-dev.sh          # Docker 目录启动脚本
│   └── README.md             # 本文档
└── .github/workflows/
    └── docker-build.yml      # GitHub Actions 配置
```

## 🚀 快速启动

### 方式1: 使用根目录配置 (推荐)

```bash
# 1. 启动开发环境
./start-dev-env.sh

# 2. 进入开发容器
docker exec -it yatcc-dev bash

# 3. 运行应用
cd /workspace
python3 entry.py
```

### 方式2: 手动启动

```bash
# 构建镜像
docker-compose build dev

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps
```

## 📋 环境特性

### 已安装组件

- **Python 3.12**: 主要开发语言
- **Node.js & npm**: 前端开发
- **Redis**: 数据缓存
- **SSH Server**: 远程访问
- **Code Server**: 浏览器中的 VS Code
- **Docker**: 容器内开发
- **开发工具**: pytest, black, flake8, mypy 等

### 端口映射

| 服务 | 容器端口 | 主机端口 | 描述 |
|------|----------|----------|------|
| SSH | 22 | 2222 | SSH 远程连接 |
| 管理端 | 5001 | 5001 | YatCC-SE 管理界面 |
| 学生端 | 5002 | 5002 | YatCC-SE 学生界面 |
| Redis | 6379 | 6379 | Redis 数据库 |
| Code Server | 8080 | 8080 | 浏览器 VS Code |

## 🔧 使用方法

### SSH 连接

```bash
# 连接到开发容器
ssh devuser@localhost -p 2222
# 密码: devuser
```

### 在容器内开发

```bash
# 进入容器
docker exec -it yatcc-se-dev bash

# 切换到开发用户
su - devuser

# 进入项目目录
cd /workspace

# 运行应用
python3 entry.py

# 运行测试
pytest

# 代码格式化
black *.py

# 代码检查
flake8 *.py
```

### 浏览器 VS Code

访问 `http://localhost:8080` 在浏览器中使用 VS Code 编辑代码。

### 前端开发

```bash
# 进入前端目录
cd stu-site

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build
```

## 🛠️ 开发工作流

### 1. 启动环境

```bash
cd docker
docker-compose -f docker-compose.dev.yml up -d
```

### 2. 连接到容器

```bash
# 方式1: SSH 连接
ssh devuser@localhost -p 2222

# 方式2: 直接进入容器
docker exec -it yatcc-se-dev bash

# 方式3: 使用浏览器 VS Code
# 访问 http://localhost:8080
```

### 3. 开发和测试

```bash
# 运行应用
python3 entry.py

# 在另一个终端运行测试
pytest test/

# 代码质量检查
black . && flake8 . && mypy .
```

### 4. 前端开发

```bash
cd stu-site
npm run dev  # 开发模式，支持热重载
```

## 🔍 调试

### Python 调试

```python
# 在代码中插入断点
import ipdb; ipdb.set_trace()

# 或使用内置调试器
import pdb; pdb.set_trace()
```

### 日志查看

```bash
# 应用日志
tail -f /var/log/yatcc-se.log

# Redis 日志
tail -f /var/log/redis/redis.log

# 系统日志
journalctl -f
```

## 📦 数据持久化

- **项目代码**: 通过 volume 挂载，修改直接同步
- **Redis 数据**: 存储在 Docker volume 中，重启容器不会丢失
- **SSH 密钥**: 持久化存储，避免重复配置

## 🔧 自定义配置

### 修改 Python 依赖

编辑 `docker/Dockerfile.dev` 中的 pip install 部分，然后重新构建：

```bash
docker-compose -f docker-compose.dev.yml build
```

### 修改端口映射

编辑 `docker/docker-compose.dev.yml` 中的 ports 配置。

### 环境变量

在 `docker-compose.dev.yml` 中添加环境变量：

```yaml
environment:
  - CUSTOM_VAR=value
  - DEBUG=1
```

## 🚨 故障排除

### 常见问题

1. **端口冲突**: 确保主机端口未被占用
2. **权限问题**: 确保 Docker 有访问项目目录的权限
3. **构建失败**: 检查网络连接和依赖包版本

### 重置环境

```bash
# 停止并删除容器
docker-compose -f docker-compose.dev.yml down -v

# 重新构建和启动
docker-compose -f docker-compose.dev.yml up --build -d
```

### 查看详细日志

```bash
# 容器日志
docker logs yatcc-se-dev

# Compose 日志
docker-compose -f docker-compose.dev.yml logs -f
```
