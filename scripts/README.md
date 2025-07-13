# YatCC-SE Scripts 目录说明

本目录包含YatCC-SE项目的实用脚本工具。

## 脚本列表

### 1. test_service_url.py

**功能**：提交Kubernetes作业并显示服务URL。

**用法**：
```bash
python scripts/test_service_url.py
python scripts/test_service_url.py --user-id 8001 --mock
```

**参数**：
- `--user-id`: 用户ID (默认: 8001)
- `--workspace`: 工作空间名称 (默认: 'test-workspace')
- `--memory`: 内存限制 (默认: '512Mi')
- `--cpu`: CPU限制 (默认: '500m')
- `--password`: code-server密码 (默认: 'test123')
- `--wait`: 等待服务就绪的时间(秒) (默认: 10)
- `--mock`: 强制使用Mock集群
- `--namespace`: Kubernetes命名空间 (默认: 'default')

**功能说明**：
- 检查Kubernetes Python客户端是否可用
- 确保命名空间存在
- 提交Kubernetes作业
- 获取服务URL
- 测试服务连通性
- 提供管理命令用于清理作业

### 2. codespace

**功能**：CODESPACE项目构建和运行管理工具。

**用法**：
```bash
python scripts/codespace build  # 执行构建
python scripts/codespace run [options]  # 运行构建出的镜像
```

**运行参数**：
- `--code-server`: 指定code-server端口 (默认: 6443)
- `--io`: 指定/io挂载目录
- `--root`: 指定/root挂载目录
- `--code`: 指定/code挂载目录
- `args`: 传递给容器的参数

### 3. student

**功能**：学生管理工具。

**子命令**：
- `list`: 列出学生
  - `--full`: 显示完整信息
- `query`: 查询学生
  - `sid`: 学生学号(可多个)
- `create`: 创建学生
  - `--example`: 打印创建学生用的JSON文件示例
  - `json`: 学生创建信息JSON文件
  - `--force`: 强制操作(只改变数据库状态)
  - `--it`: 交互式创建学生
- `delete`: 删除学生
  - `sid`: 学生学号(可多个)
  - `--force`: 强制操作(只改变数据库状态)
- `password`: 学生密码操作
  - `sid`: 学号
  - `pwd`: 密码 (默认: '123456')
  - `--reset`: 重置学生密码

## 使用示例

1. 测试Kubernetes服务URL:
```bash
python scripts/test_service_url.py --user-id 9001 --namespace test-ns
```

2. 构建并运行CODESPACE:
```bash
python scripts/codespace build
python scripts/codespace run --code-server 8080 --io ./data
```

3. 学生管理:
```bash
# 列出所有学生
python scripts/student list

# 创建学生
python scripts/student create --example > student.json
python scripts/student create student.json

# 重置密码
python scripts/student password 22335009 newpassword --reset
```

## 注意事项

1. 运行脚本前请确保已安装所有依赖项。
2. 使用Kubernetes相关功能需要配置kubectl和Kubernetes Python客户端。
3. 学生管理工具需要数据库连接配置正确。
