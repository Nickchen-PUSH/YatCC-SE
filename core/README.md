# core层与cluster层的连接

## 1. 连接初始化

在`core/__init__.py`中，core层通过以下方式初始化与cluster层的连接：

```python
@guard_ainit(LOGGER)
async def ainit(*, cluster_mock=False) -> None:
    global DB0, DB_STU, CLUSTER
    # ...
    CLUSTER = cluster.create(mock=cluster_mock)
```

关键点：
- 使用`cluster.create()`工厂函数创建集群实例
- 通过参数`cluster_mock`控制是否使用模拟集群
- 将创建的集群实例保存为全局变量`CLUSTER`供core层使用

## 2. 调用接口

虽然`core/student.py`中导入了cluster模块：
```python
import cluster
from base.logger import logger
```

但从代码中看，实际的cluster接口调用被封装在`CODESPACE`类中：

```python
class CODESPACE:
    @classmethod
    async def start(cls, sid: str) -> None:
        """启动代码空间"""
        #TODO
        pass

    @classmethod
    async def stop(cls, sid: str) -> None:
        """停止代码空间"""
        #TODO
        pass
    
    # ...其他方法
```

## 3. 预期的接口映射关系

基于`CODESPACE`类的方法设计和cluster层的接口，可以推断以下映射关系：

| CODESPACE方法 | 对应的cluster接口 | 功能描述 |
|--------------|-----------------|----------|
| `start(sid)` | `submit_job(job_params)` | 启动学生代码空间，创建新的容器作业 |
| `stop(sid)` | `delete_job(job_id)` | 停止学生代码空间，删除对应的容器作业 |
| `get_status(sid)` | `get_job_status(job_id)` | 获取代码空间运行状态 |
| `get_url(sid)` | - | 可能基于作业信息和端口映射生成访问URL |
| `watch(sid)` | `get_job_status(job_id)` | 监控代码空间活动状态 |
| `keep_alive(sid)` | - | 更新活动时间戳，防止空闲超时 |

## 4. 数据转换

core层需要在CODESPACE类中实现数据转换逻辑：
- 将学生ID映射到对应的作业ID
- 将`Student`和`CodespaceInfo`模型转换为`JobParams`
- 将cluster层的`JobInfo`和`JobStatus`转换为core层的表示形式

---

# core层与伺服层连接关系

## 1. 初始化连接

### 1.1 服务启动时的初始化
在两个服务文件的`wsgi()`函数中都包含了对core层的初始化过程：

```python
def wsgi():
    async def ado():
        import core
        import cluster
        await core.ainit(cluster_mock=ENVIRON.mock_cluster)
    
    LOGGER.info("Initializing service...")
    RUNNER.run(ado())
    return WSGI
```

这个初始化过程：
- 导入core和cluster模块
- 调用`core.ainit()`异步初始化函数
- 通过`RUNNER`执行初始化任务
- 配置是否使用mock集群

### 1.2 全局模块导入
服务层通过直接导入core层模块建立连接：
- 学生服务：`import core.student`
- 管理员服务：`from core import admin, student`

## 2. 数据模型共享

### 2.1 直接使用core层模型
服务层直接使用core层定义的数据模型：

```python
# 学生服务使用core层模型
@WSGI.put("/user", ...)
async def user_update(body: core.student.UserInfo):
    """修改用户信息"""
    pass
```

### 2.2 派生模型
服务层基于core层模型创建派生类：

```python
# 管理员服务基于core层模型定义派生类
class StudentBrief(BaseModel):
    id: str = student.Student.model_fields["sid"]
    name: str = student.UserInfo.model_fields["name"]
    mail: str = student.UserInfo.model_fields["mail"]
```

### 2.3 模型转换
服务层定义从core层模型到服务层模型的转换方法：

```python
@staticmethod
def from_student(stu: student.Student) -> "StudentDetail":
    return StudentDetail(
        id=stu.sid,
        name=stu.user_info.name,
        mail=stu.user_info.mail,
        # ...其他字段
    )
```

## 3. API实现方式

### 3.1 直接调用core层方法
在已实现的API中，服务层直接调用core层的方法：

```python
# 学生服务登录API
async def login(body: LoginBody) -> Response:
    if not await core.student.TABLE.check_password(body.sid, body.pwd):
        return "invalid password", 401
    return api_key_enc(body.sid)

# 管理员服务获取学生信息API
async def student_detail(id: str):
    await check_api_key()
    try:
        student_data = await student.TABLE.read(id)
    except student.StudentNotFoundError:
        raise ErrorResponse(Response("Student not found", status=404))
    return 200, StudentDetail.from_student(student_data)
```

### 3.2 创建学生实例
在管理员服务的`create_student`函数中，创建学生实例并调用core层的方法：

```python
stu = student.Student(
    sid=stu_data.id,
    user_info=student.UserInfo(name=stu_data.name, mail=stu_data.mail),
    codespace=student.CodespaceInfo(time_quota=stu_data.time_quota),
)
stu.reset_password(stu_data.pwd)
await student.TABLE.create(stu)
```

## 4. 错误处理与异常传递

### 4.1 异常注册
服务层注册对core层异常的处理：

```python
# 学生服务
WSGI.register_error_handler(core.student.StudentNotFoundError, _handle_403)
WSGI.register_error_handler(Exception, _handle_exception)
```

### 4.2 异常捕获与处理
服务层捕获并处理core层抛出的异常：

```python
try:
    student_data = await student.TABLE.read(id)
except student.StudentNotFoundError:
    raise ErrorResponse(Response("Student not found", status=404))
```

## 5. 权限验证机制

### 5.1 学生服务验证
学生服务通过`check_api_key()`验证用户：

```python
def check_api_key() -> str:
    from util import api_key_dec
    # ...验证逻辑
    return account
```

### 5.2 管理员服务验证
管理员服务通过`admin.API_KEY.get()`验证管理员密钥：

```python
async def check_api_key():
    # ...获取API密钥
    if not api_key == await admin.API_KEY.get():
        raise ErrorResponse(...)
```