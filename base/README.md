# Base基础模块

Base模块为YatCC-SE系统提供核心基础功能。

## 模块概述

### entry.py
定义系统入口点和初始化方法。这是启动系统的主要接口。

### logger.py
提供可配置的集中式日志功能，包括：
- 多级日志记录(DEBUG, INFO, WARNING, ERROR)
- 自定义日志格式
- 文件和终端输出处理器

### progress.py
处理进度报告和输出格式化，包含：
- 进度条实现
- 状态消息格式化
- 终端输出工具

### run.py
包含系统运行的脚本和工具，提供：
- 命令行接口集成
- 脚本执行辅助
- 系统进程管理



## 使用示例

```python
from YatCC-SE.base import logger, progress

# 初始化日志
log = logger.get_logger(__name__)
log.info("系统已初始化")

# 跟踪进度
with progress.ProgressBar(total=100) as bar:
    for i in range(100):
        bar.update(1)
```

## 依赖要求

- Python 3.8+

