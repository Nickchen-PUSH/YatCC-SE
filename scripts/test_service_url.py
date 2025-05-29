#!/usr/bin/env python3
"""
提交 Kubernetes 作业并显示服务 URL

用法:
  python scripts/test_service_url.py
  python scripts/test_service_url.py --user-id 8001 --mock
"""

import sys
import asyncio
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cluster import create, ClusterConfig


def check_kubernetes_available():
    """检查是否可以使用 Kubernetes"""
    try:
        import kubernetes
        # 尝试导入 Kubernetes 客户端
        kubernetes.config.load_kube_config()
        print("✅ Kubernetes Python 客户端可用")
        return True
    except :
        return False


async def ensure_namespace_exists(cluster, namespace: str):
    """确保命名空间存在"""
    try:
        await asyncio.to_thread(
            cluster.core_v1.read_namespace,
            name=namespace
        )
        print(f"✅ 命名空间 '{namespace}' 已存在")
        return True
    except Exception as e:
        if "404" in str(e) or "Not Found" in str(e):
            print(f"⚠️  命名空间 '{namespace}' 不存在，正在创建...")
            return await create_namespace(cluster, namespace)
        else:
            print(f"❌ 检查命名空间时出错: {e}")
            return False


async def create_namespace(cluster, namespace: str):
    """创建命名空间"""
    try:
        namespace_spec = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": namespace,
                "labels": {
                    "name": namespace,
                    "managed-by": "yatcc-se"
                }
            }
        }
        
        await asyncio.to_thread(
            cluster.core_v1.create_namespace,
            body=namespace_spec
        )
        print(f"✅ 成功创建命名空间 '{namespace}'")
        return True
    except Exception as e:
        print(f"❌ 创建命名空间失败: {e}")
        return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='提交 Kubernetes 作业并显示服务 URL')
    parser.add_argument('--user-id', type=int, default=8001, help='用户 ID (默认: 8001)')
    parser.add_argument('--workspace', type=str, default='test-workspace', help='工作空间名称')
    parser.add_argument('--memory', type=str, default='512Mi', help='内存限制')
    parser.add_argument('--cpu', type=str, default='500m', help='CPU 限制')
    parser.add_argument('--password', type=str, default='test123', help='code-server 密码')
    parser.add_argument('--wait', type=int, default=10, help='等待服务就绪的时间(秒)')
    parser.add_argument('--mock', action='store_true', help='强制使用 Mock 集群')
    parser.add_argument('--namespace', type=str, default='default', help='Kubernetes 命名空间 (默认: default)')
    
    args = parser.parse_args()
    
    print("🚀 提交 Kubernetes 作业并获取服务 URL")
    print("=" * 50)
    
    # 检查 Kubernetes 可用性
    k8s_available = check_kubernetes_available()
    
    if not k8s_available and not args.mock:
        print("⚠️  Kubernetes Python 客户端未安装")
        print("💡 自动切换到 Mock 模式")
        print("📝 要安装 Kubernetes 客户端，请运行: pip install kubernetes")
        args.mock = True
    
    try:
        # 1. 创建集群配置
        config = ClusterConfig()
        config.Kubernetes.NAMESPACE = args.namespace
        
        print(f"📋 配置信息:")
        print(f"  - 用户ID: {args.user_id}")
        print(f"  - 工作空间: {args.workspace}")
        print(f"  - 命名空间: {config.Kubernetes.NAMESPACE}")
        print(f"  - Mock 模式: {args.mock}")
        
        # 2. 创建集群实例
        if args.mock:
            print("🎭 使用 Mock 集群...")
            cluster = create("mock", config)
        else:
            print("🔧 使用 Kubernetes 集群...")
            cluster = create("kubernetes", config)
        
        # 3. 初始化集群
        print("🔧 初始化集群...")
        await cluster.initialize()
        print("✅ 集群初始化成功")
        
        # 4. 确保命名空间存在（仅真实集群）
        if not args.mock:
            namespace_ok = await ensure_namespace_exists(cluster, config.Kubernetes.NAMESPACE)
            if not namespace_ok:
                print(f"❌ 无法创建或访问命名空间 '{config.Kubernetes.NAMESPACE}'")
                print("💡 尝试使用 'default' 命名空间...")
                config.Kubernetes.NAMESPACE = "default"
        
        # 5. 创建作业参数
        from cluster import create_code_server_job
        
        job_params = create_code_server_job(
            user_id=str(args.user_id),
            workspace_name=args.workspace,
            memory_limit=args.memory,
            cpu_limit=args.cpu,
            env={
                "PASSWORD": args.password,
                "WORKSPACE_NAME": args.workspace,
                "USER_ID": str(args.user_id),
                "CREATED_BY": "test_script"
            }
        )
        
        print(f"\n📝 作业参数:")
        print(f"  - 作业名称: {job_params.name}")
        print(f"  - 用户ID: {job_params.user_id}")
        print(f"  - 镜像: {job_params.image}")
        print(f"  - 内存限制: {job_params.memory_limit}")
        print(f"  - CPU限制: {job_params.cpu_limit}")
        print(f"  - 密码: {args.password}")
        
        # 6. 提交作业
        print("\n📤 提交作业...")
        job_info = await cluster.submit_job(job_params)
        
        print("✅ 作业创建成功!")
        print(f"🆔 作业ID: {job_info.id}")
        print(f"📊 状态: {job_info.status}")
        print(f"🌐 初始服务URL: {job_info.service_url}")
        
        # 7. 等待服务就绪
        if args.wait > 0 and not args.mock:
            print(f"\n⏳ 等待 {args.wait} 秒让服务启动...")
        
            await asyncio.sleep(args.wait)
        # 8. 获取服务 URL
        print("🔗 获取服务访问URL...")
        try:
            service_url = await cluster.get_service_url(job_info.id)
            
            print("\n" + "🎯" + "=" * 48)
            print("📍 服务访问URL:")
            print(f"   {service_url}")
            print("=" * 50)
            
            # 解析URL信息
            from urllib.parse import urlparse
            parsed = urlparse(service_url)
            
            print("🔍 URL 详细信息:")
            print(f"  - 协议: {parsed.scheme}")
            print(f"  - 主机: {parsed.hostname}")
            print(f"  - 端口: {parsed.port}")
            
            if parsed.hostname == 'localhost':
                print("\n💡 这是端口转发URL，可以直接在浏览器中访问")
                print(f"🌐 在浏览器打开: {service_url}")
                print(f"🔑 登录密码: {args.password}")
            elif args.mock:
                print("\n🎭 这是 Mock 集群的模拟URL")
            else:
                print("\n🌐 这是集群URL")
                if parsed.hostname and parsed.hostname not in ['localhost', '127.0.0.1']:
                    print("💡 如果无法直接访问，可能需要端口转发")
            await asyncio.sleep(args.wait)
            
        except Exception as e:
            print(f"❌ 获取服务URL失败: {e}")
            if not args.mock:
                await debug_cluster_state(cluster, job_info.id, config.Kubernetes.NAMESPACE)
            return
        
        # 9. 检查作业状态
        print("\n📊 检查作业状态...")
        try:
            job_status = await cluster.get_job_status(job_info.id)
            print(f"当前状态: {job_status}")
            
            if str(job_status) == "JobInfo.Status.RUNNING":
                print("✅ 作业正在运行")
            elif str(job_status) == "JobInfo.Status.PENDING":
                print("⏳ 作业正在启动中...")
            else:
                print(f"⚠️  作业状态: {job_status}")
                
        except Exception as e:
            print(f"⚠️  无法获取作业状态: {e}")
        
        # 10. 测试连通性（仅真实集群的 localhost URL）
        if not args.mock and 'parsed' in locals() and parsed.hostname == 'localhost':
            print("\n🔌 测试连通性...")
            await test_connectivity(service_url)
        
        # 11. 显示管理命令
        if not args.mock:
            print("\n📖 管理命令:")
            print(f"🧹 清理作业: kubectl delete deployment {job_info.id} -n {config.Kubernetes.NAMESPACE}")
            print(f"🧹 清理服务: kubectl delete service {job_info.id}-svc -n {config.Kubernetes.NAMESPACE}")
            print(f"📋 查看Pod: kubectl get pods -l app={job_info.id} -n {config.Kubernetes.NAMESPACE}")
            print(f"📜 查看日志: kubectl logs -l app={job_info.id} -n {config.Kubernetes.NAMESPACE}")
            print(f"🔍 查看事件: kubectl get events -n {config.Kubernetes.NAMESPACE} --sort-by='.lastTimestamp'")
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        print(f"详细信息: {traceback.format_exc()}")
        sys.exit(1)


async def debug_cluster_state(cluster, job_id: str, namespace: str):
    """调试集群状态"""
    print("\n🔍 调试集群状态...")
    
    try:
        # 检查命名空间
        print(f"📂 检查命名空间 '{namespace}'...")
        try:
            ns = await asyncio.to_thread(
                cluster.core_v1.read_namespace,
                name=namespace
            )
            print(f"✅ 命名空间存在: {ns.metadata.name}")
        except Exception as e:
            print(f"❌ 命名空间问题: {e}")
        
        # 检查 Pod 状态
        print(f"📦 检查 Pod 状态...")
        try:
            pods = await asyncio.to_thread(
                cluster.core_v1.list_namespaced_pod,
                namespace=namespace,
                label_selector=f"app={job_id}"
            )
            
            if pods.items:
                for pod in pods.items:
                    print(f"📦 Pod: {pod.metadata.name}")
                    print(f"  - 阶段: {pod.status.phase}")
                    if pod.status.container_statuses:
                        for container in pod.status.container_statuses:
                            print(f"  - 容器 {container.name}: 就绪={container.ready}")
                    if pod.status.conditions:
                        for condition in pod.status.conditions:
                            if condition.status == "False":
                                print(f"  - 条件问题: {condition.type} - {condition.message}")
            else:
                print("❌ 没有找到相关 Pod")
        except Exception as e:
            print(f"❌ Pod 检查失败: {e}")
        
        # 检查 Service 状态
        print(f"🌐 检查 Service 状态...")
        try:
            service = await asyncio.to_thread(
                cluster.core_v1.read_namespaced_service,
                name=f"{job_id}-svc",
                namespace=namespace
            )
            print(f"🌐 Service: {service.metadata.name}")
            print(f"  - 类型: {service.spec.type}")
            print(f"  - 端口: {service.spec.ports}")
        except Exception as e:
            print(f"❌ Service 检查失败: {e}")
            
    except Exception as e:
        print(f"❌ 调试失败: {e}")


async def test_connectivity(url: str):
    """测试服务连通性"""
    try:
        import socket
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port
        
        print(f"  🔌 测试端口 {host}:{port}...")
        
        # 端口连通性测试
        def check_port():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(3)
                    result = sock.connect_ex((host, port))
                    return result == 0
            except Exception:
                return False
        
        loop = asyncio.get_event_loop()
        port_accessible = await loop.run_in_executor(None, check_port)
        
        if port_accessible:
            print("  ✅ 端口可访问")
            
            # HTTP连通性测试
            print("  🌐 测试HTTP连接...")
            
            def check_http():
                try:
                    import urllib.request
                    req = urllib.request.Request(url, headers={
                        'User-Agent': 'YatCC-SE-Script/1.0'
                    })
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return response.getcode()
                except urllib.error.HTTPError as e:
                    return e.code
                except Exception:
                    return None
            
            http_status = await loop.run_in_executor(None, check_http)
            
            if http_status:
                print(f"  ✅ HTTP响应: {http_status}")
                if http_status in [200, 302, 401, 403]:
                    print("  🎉 服务运行正常!")
                else:
                    print(f"  ⚠️  HTTP状态码: {http_status}")
            else:
                print("  ⚠️  HTTP连接失败")
        else:
            print("  ⚠️  端口不可访问")
            print("  💡 可能需要等待更长时间让服务启动")
            
    except Exception as e:
        print(f"  ❌ 连通性测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())