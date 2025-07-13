# YatCC-SE (Young Architect Training Course Collection - Software Engineering)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](Dockerfile)
[![Kubernetes](https://img.shields.io/badge/kubernetes-supported-blue.svg)](deployment.yaml)

YatCC-SE 是一个**面向计算机实验课程的在线云开发平台**。它提供了完整的容器化开发环境，支持多用户隔离的 Code-Server 实例，并集成了作业管理、进度跟踪和自动化部署等功能。

## 🌟 核心特性

### 🎯 教学功能

- **多用户隔离**: 每个学生拥有独立的开发环境和存储空间
- **在线代码编辑**: 基于 Code-Server 的浏览器 VS Code 环境
- **作业管理**: 支持作业分发、提交和自动化评分
- **进度跟踪**: 实时监控学生学习进度和代码完成情况
- **资源配额**: 灵活的 CPU/内存资源分配和时间配额管理

### 🏗️ 技术架构

- **微服务架构**: 分离的管理端和学生端服务
- **容器化部署**: 基于 Docker 和 Kubernetes 的容器编排
- **异步处理**: 基于 Python asyncio 的高并发处理
- **REST API**: 完整的 OpenAPI 3.0 文档化接口
- **Redis 缓存**: 高性能的会话和数据缓存

### 🔧 开发体验

- **一键部署**: 支持本地开发、Minikube 和阿里云 ACK 部署
- **热重载**: 开发环境支持代码热重载
- **实时日志**: 统一的日志管理和监控
- **健康检查**: 内置服务健康检查和自动恢复

## 🚀 快速开始

### 环境要求

- **Python**: 3.12+
- **Docker**: 20.10+
- **Node.js**: 18+ (前端开发)
- **Kubernetes**: 1.20+ (生产部署)

### 本地开发

1. **克隆项目**

   ```bash
   git clone https://github.com/Nickchen-PUSH/YatCC-SE.git
   cd YatCC-SE
   ```
2. **使用 Docker 开发环境** (推荐)

   ```bash
   # 启动开发环境
   cd docker
   docker-compose -f docker-compose.dev.yml up -d

   # 进入开发容器
   docker exec -it yatcc-se-dev bash

   # 运行应用
   python3 entry.py
   ```
3. **原生环境开发**

   ```bash
   # 创建虚拟环境
   python3 -m venv venv
   source venv/bin/activate

   # 安装依赖
   bash build-env.sh
   pip install -r requirements.txt

   # 配置环境
   cp config.py.example config.py

   # 启动服务
   python3 entry.py
   ```

### 访问服务

开发环境启动后，可以通过以下地址访问：

- **管理端**: http://localhost:5001
- **学生端**: http://localhost:5002
- **SSH 连接**: `ssh root@localhost -p 2222`
- **浏览器 VS Code**: http://localhost:8080

## 📁 项目结构

```
YatCC-SE/
├── 📂 base/              # 基础框架和工具类
├── 📂 cluster/           # 集群管理和容器编排
├── 📂 core/              # 核心业务逻辑
├── 📂 docker/            # Docker 开发环境配置
├── 📂 scripts/           # 运维和部署脚本
├── 📂 stu-site/          # 学生端前端 (Vue 3)
├── 📂 adm-site/          # 管理端前端 (Vue 3)  
├── 📂 run/               # 运行时和打包工具
├── 📂 test/              # 单元测试和集成测试
├── 📄 entry.py           # 应用程序入口
├── 📄 svc_adm.py         # 管理端 API 服务
├── 📄 svc_stu.py         # 学生端 API 服务
├── 📄 config.py          # 开发环境配置
└──📄 deployment.yaml    # Kubernetes 部署配置
```

## 🏭 部署指南

### Docker 部署

1. **构建生产镜像**

   ```bash
   # 使用内置脚本
   ./scripts/dev/yatcc-se build

   # 或手动构建
   docker build -f docker/Dockerfile.production -t yatcc-se:latest .
   ```
2. **运行生产容器**

   ```bash
   docker run -d \
     --name yatcc-se \
     -p 22:22 \
     -p 5001:5001 \
     -p 5002:5002 \
     -v /data/yatcc-se:/io \
     yatcc-se:latest
   ```

### Kubernetes 部署

1. **部署到集群**

   ```bash
   # 应用配置
   kubectl apply -f deployment.yaml

   # 检查状态
   kubectl get pods -l app=yatcc-se
   ```
2. **配置访问**

   ```bash
   # 端口转发到本地
   kubectl port-forward svc/yatcc-se-svc 5001:5001 5002:5002
   ```

### 阿里云 ACK 部署

参考 [部署文档](docs/deployment.md) 了解阿里云容器服务的详细配置。

## 🔧 配置说明

### 环境配置

项目支持多环境配置：

- **开发环境**: `config.py` - 本地开发配置
- **生产环境**: `run/yatcc-se/config.py` - 容器化生产配置

### 主要配置项

```python
# 基础配置
CONFIG.app_dir = "/app/"                    # 应用目录
CONFIG.io_dir = "/io/"                      # 数据目录
CONFIG.log_level = 1                        # 日志级别

# 服务配置
CONFIG.SVC_ADM.host = "0.0.0.0"            # 管理端监听地址
CONFIG.SVC_ADM.port = 5001                  # 管理端端口
CONFIG.SVC_STU.host = "0.0.0.0"            # 学生端监听地址  
CONFIG.SVC_STU.port = 5002                  # 学生端端口

# 集群配置
CONFIG.CLUSTER.namespace = "yatcc-se"       # Kubernetes 命名空间
CONFIG.CLUSTER.image = "codercom/code-server:latest"  # Code-Server 镜像
```

## 📊 架构概览

![system](system-se.drawio.svg)

## 🧪 开发工具

### 代码质量

```bash
# 代码格式化
black . 

# 代码检查
flake8 .

# 类型检查
mypy .

# 运行测试
pytest test/
```

### 前端开发

```bash
# 学生端开发
cd stu-site
npm install
npm run dev

# 管理端开发  
cd adm-site
npm install
npm run dev
```

### API 文档

启动服务后访问自动生成的 OpenAPI 文档：

- **管理端 API**: http://localhost:5001/openapi/swagger
- **学生端 API**: http://localhost:5002/openapi/swagger

## 🔍 监控和日志

### 健康检查

```bash
# 检查服务状态
curl http://localhost:5001/health
curl http://localhost:5002/health

# 检查就绪状态
curl http://localhost:5001/readiness
curl http://localhost:5002/readiness
```

### 日志查看

```bash
# 容器日志
docker logs yatcc-se

# Kubernetes 日志
kubectl logs -f deployment/yatcc-se

# 应用日志
tail -f io/log/\*.log
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 创建 Pull Request

### 开发规范

- 遵循 [PEP 8](https://pep8.org/) Python 代码风格
- 前端代码使用 ESLint 和 Prettier
- 提交信息使用 [Conventional Commits](https://conventionalcommits.org/)
- 添加适当的单元测试和文档

## 🐛 问题反馈

遇到问题？请通过以下方式反馈：

- [GitHub Issues](https://github.com/Nickchen-PUSH/YatCC-SE/issues) - Bug 报告和功能请求
- [讨论区](https://github.com/Nickchen-PUSH/YatCC-SE/discussions) - 技术讨论和使用问题
- 邮件联系: [chenhq](mailto:chenhq79@mail2.sysu.edu.cn)

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

## 🙏 致谢

感谢以下开源项目的支持：

- [Code-Server](https://github.com/coder/code-server) - 浏览器中的 VS Code
- [Flask](https://flask.palletsprojects.com/) - Python Web 框架
- [Vue.js](https://vuejs.org/) - 前端 JavaScript 框架
- [Kubernetes](https://kubernetes.io/) - 容器编排平台
- [Redis](https://redis.io/) - 内存数据库

---

<div align="center">
  <p>Made with ❤️ by YatCC Team</p>
</div>
