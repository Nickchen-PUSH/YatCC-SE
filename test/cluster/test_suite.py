"""cluster 模块测试套件

运行所有 cluster 相关的测试。
"""

import unittest
import sys
from base.logger import logger

LOGGER = logger(__spec__, __file__)


def create_test_suite():
    """创建完整的测试套件"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加各个测试模块
    test_modules = [
        'test.cluster.test_mock',          # Mock 集群测试
        'test.cluster.test_kubernetes',    # Kubernetes 集群测试
    ]
    
    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            module_tests = loader.loadTestsFromModule(module)
            suite.addTest(module_tests)
            LOGGER.info(f"✅ Added {module_name} to test suite")
        except ImportError as e:
            LOGGER.warning(f"⚠️  Failed to load {module_name}: {e}")
        except Exception as e:
            LOGGER.error(f"💥 Error loading {module_name}: {e}")
    
    return suite


def run_tests(verbosity=2, pattern=None):
    """运行所有测试"""
    LOGGER.info("🚀 Starting cluster test suite")
    
    suite = create_test_suite()
    
    # 如果指定了模式，则过滤测试
    if pattern:
        filtered_suite = unittest.TestSuite()
        for test_group in suite:
            if hasattr(test_group, '_tests'):
                for test_case in test_group._tests:
                    if pattern.lower() in str(test_case).lower():
                        filtered_suite.addTest(test_case)
            else:
                if pattern.lower() in str(test_group).lower():
                    filtered_suite.addTest(test_group)
        suite = filtered_suite
        LOGGER.info(f"🔍 Filtered tests with pattern: {pattern}")
    
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    result = runner.run(suite)
    
    # 输出测试结果摘要
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(getattr(result, 'skipped', []))
    passed = total_tests - failures - errors - skipped
    
    LOGGER.info("=" * 70)
    LOGGER.info("📊 Test Results Summary:")
    LOGGER.info(f"  📝 Total Tests: {total_tests}")
    LOGGER.info(f"  ✅ Passed: {passed}")
    LOGGER.info(f"  ❌ Failed: {failures}")
    LOGGER.info(f"  💥 Errors: {errors}")
    LOGGER.info(f"  ⏭️  Skipped: {skipped}")
    
    success = result.wasSuccessful()
    if success:
        LOGGER.info("🎉 All cluster tests passed!")
    else:
        LOGGER.error("❌ Some cluster tests failed!")
        
        if failures:
            LOGGER.error("💔 Test Failures:")
            for test, traceback in result.failures:
                LOGGER.error(f"  FAIL: {test}")
        
        if errors:
            LOGGER.error("🚨 Test Errors:")
            for test, traceback in result.errors:
                LOGGER.error(f"  ERROR: {test}")
    
    LOGGER.info("=" * 70)
    return success


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run YatCC-SE cluster tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test/cluster/test_suite.py                    # Run all tests
  python3 test/cluster/test_suite.py -m factory         # Run factory tests  
  python3 test/cluster/test_suite.py -m kubernetes      # Run kubernetes tests
  python3 test/cluster/test_suite.py -p user            # Filter by pattern
  python3 test/cluster/test_suite.py -v 1               # Lower verbosity
        """
    )
    
    parser.add_argument(
        '--verbosity', '-v',
        type=int,
        default=2,
        choices=[0, 1, 2],
        help='Test verbosity level (0=minimal, 1=normal, 2=verbose)'
    )
    
    parser.add_argument(
        '--module', '-m',
        choices=['factory', 'mock', 'kubernetes'],
        help='Run specific test module'
    )
    
    parser.add_argument(
        '--pattern', '-p',
        help='Filter tests by pattern (case insensitive)'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List available test modules and exit'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available test modules:")
        print("  factory     - Factory functions and convenience functions")
        print("  mock        - Mock cluster implementation")
        print("  kubernetes  - Kubernetes cluster implementation")
        return
    
    success = False
    
    try:
        if args.module:
            # 运行特定模块
            module_name = f'test.cluster.test_{args.module}'
            suite = unittest.TestLoader().loadTestsFromName(module_name)
            runner = unittest.TextTestRunner(verbosity=args.verbosity)
            result = runner.run(suite)
            success = result.wasSuccessful()
        else:
            # 运行所有测试
            success = run_tests(verbosity=args.verbosity, pattern=args.pattern)
    
    except KeyboardInterrupt:
        LOGGER.warning("⚠️  Tests interrupted by user")
        success = False
    except Exception as e:
        LOGGER.error(f"💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()