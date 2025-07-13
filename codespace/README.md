# Codespace开发环境模块

本模块提供YatCC-SE系统的开发环境配置和管理功能。

## 模块功能

### entry.py
- 开发环境的主入口点
- 提供环境初始化功能
- 包含开发服务器启动逻辑

### config.py
- 开发环境的核心配置文件
- 支持以下配置项：
  - 开发服务器端口设置
  - 数据库连接配置
  - 调试模式开关
  - 第三方服务API密钥

## 安装与配置

1. 确保已安装Python 3.8+
2. 安装依赖包：
```bash
./build_env.sh
```
3. 复制示例配置文件：
```bash
cp config.example.py config.py
```
4. 根据实际情况修改config.py中的配置项

## 使用说明

### 启动开发环境
```bash
python -m YatCC-SE.codespace.entry
```

### 常用命令
- `--port`: 指定服务端口(默认8000)
- `--debug`: 启用调试模式
- `--reload`: 启用代码热重载

## 开发环境要求

- Python 3.8+
- PostgreSQL 12+(可选，如需数据库支持)
- Redis(可选，如需缓存支持)

## 示例配置

```python
# config.py示例
DEBUG = True
DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"
API_KEYS = {
    "service_a": "your_api_key_here"
}
```

## 注意事项

1. 请勿将包含敏感信息的config.py提交到版本控制
2. 生产环境请确保DEBUG=False
3. 修改配置后需要重启服务生效
