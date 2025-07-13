# YatCC-SE Cluster 模块接口文档

## 概述

YatCC-SE Cluster 模块提供统一的集群管理接口，专门用于部署和管理用户独立的 code-server 容器。支持 Mock 和 Kubernetes 两种集群类型。

## 目录

- [快速开始](#快速开始)
- [核心类和方法](#核心类和方法)
- [数据模型](#数据模型)
- [集群实现](#集群实现)
- [异常处理](#异常处理)
- [使用示例](#使用示例)
- [配置说明](#配置说明)

## 快速开始

### 基本使用

```python
from cluster import create, create_code_server_job

# 创建集群实例
cluster = create(type="kubernetes")  # 或 "mock"
await cluster.initialize()

# 创建 code-server 作业参数
job_params = create_code_server_job(
    user_id=1001,
    cpu_limit="500m",
    memory_limit="1Gi"
)

# 提交作业
job_info = await cluster.submit_job(job_params)
print(f"作业已创建: {job_info.id}")

# 获取服务访问 URL (自动创建端口转发到本地)
service_url = await cluster.get_service_url(job_info.id)
print(f"访问地址: {service_url}")  # 例如: http://localhost:30001
```

## 核心类和方法

### ClusterABC (抽象基类)

所有集群实现的基类，定义了统一的接口。

#### 初始化方法

```python
async def initialize() -> None
```

- **功能**: 初始化集群连接
- **返回**: 无
- **异常**: `ClusterError` - 初始化失败

```python
async def ensure_initialized() -> None
```

- **功能**: 确保集群已初始化
- **返回**: 无

#### 作业管理方法

```python
async def allocate_resources(job_params: JobParams) -> JobInfo
```

- **功能**: 为用户分配一个 deployment 资源（同时启动）
- **参数**:
  - `job_params`: 作业参数对象
- **返回**: `JobInfo` - 作业信息
- **异常**:
  - `ValueError` - 参数无效
  - `ClusterError` - 分配失败

```python
async def submit_job(job_params: JobParams) -> JobInfo
```

- **功能**: 启动或恢复用户对应的 deployment
- **参数**:
  - `job_params`: 作业参数对象，**必须包含 `name` 字段**
- **返回**: `JobInfo` - 作业信息
- **异常**:
  - `ValueError` - 参数无效（如缺少 `name` 字段）
  - `ClusterError` - 提交失败
- **说明**:
  - 如果用户已有被暂停的 deployment，会自动恢复
  - 如果没有现有 deployment，会创建新的
  - 会自动更新环境变量和资源配置

```python
async def get_job_status(job_name: str) -> JobInfo.Status
```

- **功能**: 获取作业状态
- **参数**:
  - `job_name`: 作业名称（deployment 名称）
- **返回**: `JobInfo.Status` - 作业状态枚举
- **异常**:
  - `JobNotFoundError` - 作业不存在
  - `ClusterError` - 获取失败

```python
async def get_job_info(job_name: str) -> JobInfo
```

- **功能**: 获取作业详细信息
- **参数**:
  - `job_name`: 作业名称
- **返回**: `JobInfo` - 完整的作业信息
- **异常**:
  - `JobNotFoundError` - 作业不存在
  - `ClusterError` - 获取失败

```python
async def delete_job(job_name: str) -> List[str]
```

- **功能**: 暂停指定的作业（不是真正删除）
- **参数**:
  - `job_name`: 作业名称
- **返回**: `List[str]` - 被暂停的作业ID列表
- **异常**:
  - `JobNotFoundError` - 作业不存在
  - `ClusterError` - 操作失败
- **说明**:
  - 会将 deployment 的副本数设置为 0
  - 保存原始副本数到注解中用于恢复
  - 会停止相关的端口转发

```python
async def list_jobs() -> List[JobInfo]
```

- **功能**: 列出所有 YatCC-SE 管理的作业
- **返回**: `List[JobInfo]` - 作业信息列表
- **异常**: `ClusterError` - 列出失败
- **说明**: 只返回带有 `managed-by=yatcc-se` 和 `type=code-server` 标签的 deployment

```python
async def get_job_logs(job_name: str, lines: int = 100) -> str
```

- **功能**: 获取作业日志
- **参数**:
  - `job_name`: 作业名称
  - `lines`: 日志行数，默认100行
- **返回**: `str` - 日志内容
- **异常**:
  - `JobNotFoundError` - 作业不存在
  - `ClusterError` - 获取失败

#### 服务访问方法

```python
async def get_service_url(job_name: str) -> str
```

- **功能**: 获取作业的服务访问URL（自动创建本地端口转发）
- **参数**:
  - `job_name`: 作业名称
- **返回**: `str` - 本地访问URL，格式为 `http://localhost:{port}`
- **异常**:
  - `JobNotFoundError` - 作业不存在
  - `ClusterError` - 获取失败
- **说明**:
  - 会自动使用 `kubectl port-forward` 创建到本地的端口转发
  - 端口从 30000 开始自动分配
  - 每个作业只会有一个活跃的端口转发

```python
async def stop_port_forward(job_name: str) -> None
```

- **功能**: 停止指定作业的端口转发
- **参数**:
  - `job_name`: 作业名称
- **返回**: 无
- **说明**: 会优雅地终止 `kubectl port-forward` 进程

#### 清理方法

```python
async def cleanup(job_name: str) -> None
```

- **功能**: 完全删除作业及其所有资源
- **参数**:
  - `job_name`: 作业名称
- **返回**: 无
- **异常**: `ClusterError` - 删除失败
- **说明**:
  - 删除 Deployment
  - 删除 Service
  - 停止端口转发
  - **不会删除 PVC（持久化存储）**

## 数据模型

### JobParams

作业参数模型，用于定义 code-server 作业的配置。

```python
class JobParams(BaseModel):
    """作业参数"""

    name: str = Field(..., description="作业名称")
    image: str = Field(default="codercom/code-server:latest", description="镜像名称")
    ports: List[PortParams] = Field(default_factory=list, description="端口映射列表")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")

    # 资源限制
    cpu_limit: Optional[str] = Field(None, description="CPU限制，如 '1000m'")
    memory_limit: Optional[str] = Field(None, description="内存限制，如 '2Gi'")
    storage_size: Optional[str] = Field(None, description="存储大小，如 '5Gi'")

    # 用户信息（用于隔离）
    user_id: str = Field(..., description="用户ID")
```

**字段说明**:

- `name`: **必填** - 作业显示名称，通常为用户ID
- `image`: Docker镜像地址
- `ports`: 容器暴露的端口列表
- `env`: 传递给容器的环境变量
- `cpu_limit`: CPU资源限制，使用Kubernetes格式（如 "500m", "1000m", "2"）
- `memory_limit`: 内存资源限制，使用Kubernetes格式（如 "512Mi", "1Gi", "2Gi"）
- `storage_size`: 持久化存储大小（当前版本暂未使用）
- `user_id`: 用户唯一标识，用于资源隔离和目录挂载

### JobInfo

作业信息模型，包含作业的完整状态和配置信息。

```python
class JobInfo(BaseModel):
    """作业信息"""

    id: str = Field(..., description="作业ID")
    name: str = Field(..., description="作业名称")
    image: str = Field(..., description="镜像名称")
    ports: List[PortParams] = Field(default_factory=list, description="端口映射列表")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    status: int = Field(..., description="作业状态")

    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    namespace: Optional[str] = Field(None, description="命名空间")
    service_url: Optional[str] = Field(None, description="服务访问地址")

    # 用户信息
    user_id: Optional[str] = Field(None, description="用户ID")

    class Status(IntEnum):
        PENDING = 0
        RUNNING = 1
        FAILED = 2
        SUSPENDED = 3
        STARTING = 4
```

**状态说明**:

- `PENDING`: 作业已提交，正在等待资源分配或启动
- `RUNNING`: 作业正在运行，至少有一个 Pod 就绪
- `SUCCESS`: 作业成功完成（对于长期运行的服务较少使用）
- `FAILED`: 作业运行失败，有不可用的副本
- `STOPPING`: 作业正在停止
- `STOPPED`: 作业已停止（暂停状态，副本数为0）
- `SUSPENDED`:作业挂起
- `STARTING`：作业正在启动

## 集群实现

### MockCluster

用于开发和测试的模拟集群实现。

**特点**:

- 无需真实的Kubernetes环境
- 快速启动和响应
- 模拟真实的作业生命周期
- 适用于单元测试和开发调试

**使用场景**:

```python
# 创建Mock集群
cluster = create(type="mock")
await cluster.initialize()

# 所有接口与真实集群一致
job_info = await cluster.submit_job(job_params)
```

### KubernetesCluster

真实的Kubernetes集群实现，支持完整的容器编排功能。

**特点**:

- 支持真实的Kubernetes部署
- 自动创建Deployment、Service等资源
- 自动端口转发到本地 localhost
- 支持作业暂停和恢复
- 运行时配置更新（滚动更新）

**资源管理**:

```python
# 每个用户作业会创建以下Kubernetes资源：
# 1. Deployment: 管理Pod生命周期
# 2. Service (NodePort): 提供服务发现和负载均衡
# 3. kubectl port-forward: 提供本地访问
```

**用户隔离**:

- 使用标签进行用户级别的资源隔离：
  - `managed-by=yatcc-se`
  - `user-id={user_id}`
  - `type=code-server`
- 支持按用户ID查找和管理作业
- 防止用户间的资源冲突

**存储挂载**:
每个用户的容器会自动挂载以下目录：

```python
# 主机路径 -> 容器路径
f"{CONFIG.CORE.students_dir}/{user_id}/code" -> "/workspace"  # 代码工作区
f"{CONFIG.CORE.students_dir}/{user_id}/io"   -> "/io"         # 输入输出目录
f"{CONFIG.CORE.students_dir}/{user_id}/root" -> "/data"       # 用户数据目录
```

## 异常处理

### ClusterError

集群操作的基础异常类。

```python
class ClusterError(Exception):
    """集群操作异常"""
    pass
```

**常见原因**:

- 集群连接失败
- 资源创建失败
- 配置错误
- 网络问题

### JobNotFoundError

作业不存在异常，继承自ClusterError。

```python
class JobNotFoundError(ClusterError):
    """作业不存在异常"""
    pass
```

**常见原因**:

- 提供的作业名称不存在
- 作业已被删除
- 权限不足

### 异常处理示例

```python
try:
    job_info = await cluster.get_job_info("nonexistent-job")
except JobNotFoundError:
    print("作业不存在")
except ClusterError as e:
    print(f"集群操作失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 使用示例

### 1. 创建和管理Code-Server作业

```python
import asyncio
from cluster import create, create_code_server_job

async def main():
    # 创建Kubernetes集群
    cluster = create(type="kubernetes")
    await cluster.initialize()
  
    # 为用户1001创建code-server
    job_params = create_code_server_job(
        user_id=1001,
        cpu_limit="500m",
        memory_limit="1Gi",
        env={
            "WORKSPACE_NAME": "python-project",
            "CUSTOM_VAR": "value"
        }
    )
  
    # 重要：设置作业名称（通常为用户ID）
    job_params.name = str(job_params.user_id)
  
    # 提交作业
    job_info = await cluster.submit_job(job_params)
    print(f"作业创建成功: {job_info.id}")
  
    # 等待作业运行
    while True:
        status = await cluster.get_job_status(job_info.id)
        if status == JobInfo.Status.RUNNING:
            print("作业已启动")
            break
        elif status == JobInfo.Status.FAILED:
            print("作业启动失败")
            return
        await asyncio.sleep(2)
  
    # 获取本地访问地址（自动创建端口转发）
    local_url = await cluster.get_service_url(job_info.id)
    print(f"本地访问地址: {local_url}")  # 例如: http://localhost:30001
  
    # 获取作业日志
    logs = await cluster.get_job_logs(job_info.id, lines=50)
    print(f"最近50行日志:\n{logs}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 用户作业生命周期管理

```python
async def manage_user_jobs():
    cluster = create(type="kubernetes")
    await cluster.initialize()
  
    user_id = 1001
    job_name = str(user_id)  # 作业名称通常为用户ID
  
    # 检查用户是否已有作业
    try:
        existing_job = await cluster.get_job_info(job_name)
        print(f"用户 {user_id} 已有作业: {existing_job.id}")
    
        # 暂停用户的作业
        suspended_jobs = await cluster.delete_job(job_name)
        print(f"已暂停作业: {suspended_jobs}")
    except JobNotFoundError:
        print(f"用户 {user_id} 没有现有作业")
  
    # 创建新作业（会自动恢复被暂停的作业）
    job_params = create_code_server_job(
        user_id=user_id,
        memory_limit="2Gi"  # 更新资源配置
    )
    job_params.name = job_name
  
    job_info = await cluster.submit_job(job_params)
    print(f"作业已恢复/创建: {job_info.id}")
  
    # 获取本地访问URL
    local_url = await cluster.get_service_url(job_info.id)
    print(f"访问地址: {local_url}")
```

### 3. 批量作业管理

```python
async def batch_job_management():
    cluster = create(type="kubernetes")
    await cluster.initialize()
  
    # 为多个用户创建作业
    user_ids = [1001, 1002, 1003, 1004, 1005]
    jobs = []
  
    for user_id in user_ids:
        job_params = create_code_server_job(
            user_id=user_id,
            cpu_limit="250m",
            memory_limit="512Mi"
        )
        job_params.name = str(user_id)
    
        try:
            job_info = await cluster.submit_job(job_params)
            jobs.append(job_info)
            print(f"✅ 用户 {user_id} 作业创建成功: {job_info.id}")
        except Exception as e:
            print(f"❌ 用户 {user_id} 作业创建失败: {e}")
  
    # 等待所有作业启动并获取访问地址
    print("等待作业启动...")
    for job_info in jobs:
        while True:
            status = await cluster.get_job_status(job_info.id)
            if status == JobInfo.Status.RUNNING:
                local_url = await cluster.get_service_url(job_info.id)
                print(f"✅ {job_info.id} 已启动: {local_url}")
                break
            elif status == JobInfo.Status.FAILED:
                print(f"❌ {job_info.id} 启动失败")
                break
            await asyncio.sleep(1)
  
    # 列出所有运行中的作业
    running_jobs = await cluster.list_jobs()
    running_count = len([j for j in running_jobs if j.status == JobInfo.Status.RUNNING])
    print(f"当前运行中的作业数量: {running_count}")
```

### 4. 端口转发管理

```python
async def port_forward_management():
    cluster = create(type="kubernetes")
    await cluster.initialize()
  
    user_id = 1001
    job_name = str(user_id)
  
    # 创建作业
    job_params = create_code_server_job(user_id=user_id)
    job_params.name = job_name
    job_info = await cluster.submit_job(job_params)
  
    # 等待作业启动
    while await cluster.get_job_status(job_name) != JobInfo.Status.RUNNING:
        await asyncio.sleep(2)
  
    # 创建端口转发
    local_url = await cluster.get_service_url(job_name)
    print(f"端口转发已创建: {local_url}")
  
    # 使用服务...
    await asyncio.sleep(10)
  
    # 手动停止端口转发
    await cluster.stop_port_forward(job_name)
    print("端口转发已停止")
  
    # 清理作业
    await cluster.cleanup(job_name)
    print("作业已清理")
```

### 5. 错误处理和重试

```python
async def robust_job_creation():
    cluster = create(type="kubernetes")
    await cluster.initialize()
  
    max_retries = 3
    user_id = 1001
    job_name = str(user_id)
  
    for attempt in range(max_retries):
        try:
            job_params = create_code_server_job(
                user_id=user_id,
                memory_limit="1Gi"
            )
            job_params.name = job_name
        
            job_info = await cluster.submit_job(job_params)
            print(f"作业创建成功: {job_info.id}")
        
            # 验证作业是否真正启动
            for _ in range(30):  # 最多等待30秒
                status = await cluster.get_job_status(job_info.id)
                if status == JobInfo.Status.RUNNING:
                    print("作业已成功启动")
                    local_url = await cluster.get_service_url(job_info.id)
                    print(f"访问地址: {local_url}")
                    return job_info
                elif status == JobInfo.Status.FAILED:
                    # 获取日志进行诊断
                    logs = await cluster.get_job_logs(job_info.id, lines=20)
                    print(f"作业启动失败，日志:\n{logs}")
                    raise ClusterError("作业启动失败")
                await asyncio.sleep(1)
        
            raise ClusterError("作业启动超时")
        
        except JobNotFoundError:
            print(f"尝试 {attempt + 1}: 作业不存在，可能是配置问题")
        except ClusterError as e:
            print(f"尝试 {attempt + 1}: 集群错误 - {e}")
            if attempt < max_retries - 1:
                print(f"等待 {2 ** attempt} 秒后重试...")
                await asyncio.sleep(2 ** attempt)
        except Exception as e:
            print(f"尝试 {attempt + 1}: 未知错误 - {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
  
    print("所有重试尝试都失败了")
    return None
```

## 配置说明

### 集群配置

通过 `CONFIG` 对象进行配置：

```python
from config import CONFIG

# Kubernetes 配置
CONFIG.Kubernetes.NAMESPACE = "yatcc-se"           # Kubernetes命名空间
CONFIG.Kubernetes.KUBECONFIG_PATH = "~/.kube/config"  # kubeconfig文件路径

# Code-Server 配置  
CONFIG.Codespace.IMAGE = "codercom/code-server:latest"  # 默认镜像
CONFIG.Codespace.PORT = 8080                             # 服务端口
CONFIG.Codespace.DEFAULT_CPU_LIMIT = "1000m"           # 默认CPU限制
CONFIG.Codespace.DEFAULT_MEMORY_LIMIT = "2Gi"          # 默认内存限制
CONFIG.Codespace.DEFAULT_STORAGE_SIZE = "5Gi"          # 默认存储大小

# 核心配置
CONFIG.CORE.students_dir = "/data/students"             # 学生数据目录
```

### 环境变量

系统会自动为每个 code-server 容器设置用户自定义的环境变量，常见的包括：

```python
{
    "PASSWORD": f"student{user_id}",      # code-server登录密码
    "SUDO_PASSWORD": f"student{user_id}", # sudo密码  
    "USER_ID": str(user_id),              # 用户ID
    "WORKSPACE_NAME": "workspace_name",   # 工作区名称
    # ... 其他自定义环境变量
}
```

### 资源配置

```python
# 容器资源配置
resources = {
    "requests": {
        "memory": "256Mi",  # 基础内存请求
        "cpu": "250m"       # 基础CPU请求
    },
    "limits": {
        "memory": job_params.memory_limit or CONFIG.Codespace.DEFAULT_MEMORY_LIMIT,
        "cpu": job_params.cpu_limit or CONFIG.Codespace.DEFAULT_CPU_LIMIT
    }
}
```

### 端口转发配置

```python
# 端口转发从 30000 开始自动分配
_local_port_base = 30000

# 每个作业只能有一个活跃的端口转发
# 使用 kubectl port-forward 命令创建转发
# 格式: kubectl port-forward svc/{job_name}-svc {local_port}:{target_port} -n {namespace}
```

## 最佳实践

### 1. 作业命名规范

```python
# 推荐：使用用户ID作为作业名称
def create_user_job(user_id: int):
    job_params = create_code_server_job(user_id=user_id)
    job_params.name = str(user_id)  # 重要：设置作业名称
    return job_params

# 每个用户只应该有一个 code-server 作业
user_job_name = str(user_id)
```

### 2. 资源管理

```python
# 根据用户级别设置不同的资源限制
def create_job_for_user_level(user_id: int, level: str):
    resource_configs = {
        "basic": {"cpu_limit": "250m", "memory_limit": "512Mi"},
        "standard": {"cpu_limit": "500m", "memory_limit": "1Gi"},
        "premium": {"cpu_limit": "1000m", "memory_limit": "2Gi"}
    }
  
    config = resource_configs.get(level, resource_configs["basic"])
    job_params = create_code_server_job(user_id=user_id, **config)
    job_params.name = str(user_id)
    return job_params
```

### 3. 端口转发生命周期管理

```python
async def managed_port_forward_session(cluster, job_name: str):
    """管理端口转发的生命周期"""
    local_url = None
    try:
        # 创建端口转发
        local_url = await cluster.get_service_url(job_name)
        print(f"端口转发已创建: {local_url}")
    
        # 使用服务
        yield local_url
    
    finally:
        # 确保清理端口转发
        if local_url:
            await cluster.stop_port_forward(job_name)
            print("端口转发已清理")

# 使用示例
async with managed_port_forward_session(cluster, job_name) as local_url:
    # 使用 local_url 访问服务
    pass
```

### 4. 错误监控

```python
async def monitor_job_health(cluster, job_name: str):
    """监控作业健康状态"""
    while True:
        try:
            status = await cluster.get_job_status(job_name)
            if status == JobInfo.Status.FAILED:
                # 获取日志进行诊断
                logs = await cluster.get_job_logs(job_name, lines=100)
                logger.error(f"Job {job_name} failed. Logs:\n{logs}")
                break
            elif status == JobInfo.Status.RUNNING:
                # 检查端口转发可用性
                try:
                    local_url = await cluster.get_service_url(job_name)
                    # 可以添加 HTTP 健康检查
                except Exception as e:
                    logger.warning(f"Port forward issue for {job_name}: {e}")
        except Exception as e:
            logger.error(f"Health check failed for {job_name}: {e}")
    
        await asyncio.sleep(30)  # 每30秒检查一次
```

### 5. 批量操作优化

```python
async def create_jobs_with_concurrency_limit(cluster, user_ids: List[int], max_concurrent: int = 5):
    """限制并发数量的批量作业创建"""
    semaphore = asyncio.Semaphore(max_concurrent)
  
    async def create_single_job(user_id: int):
        async with semaphore:
            job_params = create_code_server_job(user_id=user_id)
            job_params.name = str(user_id)
            return await cluster.submit_job(job_params)
  
    # 并发创建作业，但限制同时进行的数量
    tasks = [create_single_job(user_id) for user_id in user_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
  
    # 处理结果
    successful = [r for r in results if isinstance(r, JobInfo)]
    failed = [r for r in results if isinstance(r, Exception)]
  
    print(f"成功创建 {len(successful)} 个作业，失败 {len(failed)} 个")
    return successful, failed
```

## 版本信息

- **当前版本**: 1.0.0
- **兼容性**: Python 3.8+
- **依赖**: kubernetes, pydantic, asyncio
- **Kubernetes版本**: 1.20+
- **kubectl要求**: 需要 kubectl 命令行工具用于端口转发

## 注意事项

1. **作业名称**: `submit_job` 方法要求 `job_params.name` 字段不能为空
2. **端口转发**: 会自动创建 `kubectl port-forward`，需要确保 kubectl 可用
3. **资源隔离**: 每个用户的数据通过 hostPath 挂载实现隔离
4. **暂停恢复**: `delete_job` 只是暂停作业，`submit_job` 会自动恢复暂停的作业
5. **并发安全**: 对同一用户的操作会自动串行化执行
