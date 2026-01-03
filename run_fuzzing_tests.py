#!/usr/bin/env python3
"""
大规模模糊测试运行脚本
用于运行压力测试、边界测试、并发测试和崩溃检测测试
"""

import subprocess
import sys
import argparse


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"运行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='运行大规模模糊测试')
    parser.add_argument('--type', choices=['all', 'stress', 'boundary', 'concurrent', 'crash', 'fuzzing'], 
                       default='all', help='选择要运行的测试类型')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--max-examples', type=int, default=None, 
                       help='设置 Hypothesis 的最大示例数')
    parser.add_argument('--timeout', type=int, default=None, 
                       help='设置测试超时时间（秒）')
    
    args = parser.parse_args()
    
    base_cmd = ['pytest', '-v' if args.verbose else '-q']
    
    if args.max_examples:
        base_cmd.extend(['--hypothesis-max-examples', str(args.max_examples)])
    
    if args.timeout:
        base_cmd.extend(['--timeout', str(args.timeout)])
    
    test_files = {
        'stress': ['test_fuzzing_stress.py::TestStressFuzzing'],
        'boundary': ['test_fuzzing_stress.py::TestBoundaryFuzzing'],
        'concurrent': ['test_fuzzing_stress.py::TestConcurrentFuzzing'],
        'crash': ['test_fuzzing_stress.py::TestCrashDetection'],
        'fuzzing': ['test_fuzzing.py'],
    }
    
    if args.type == 'all':
        test_files['all'] = ['test_fuzzing_stress.py', 'test_fuzzing.py']
    
    selected_tests = test_files.get(args.type, test_files['all'])
    
    print(f"\n{'#'*60}")
    print(f"# 大规模模糊测试运行器")
    print(f"# 测试类型: {args.type}")
    print(f"# 测试文件: {', '.join(selected_tests)}")
    print(f"{'#'*60}\n")
    
    success = True
    for test in selected_tests:
        cmd = base_cmd + [test]
        if not run_command(cmd, f"{args.type.upper()} 测试"):
            success = False
    
    print(f"\n{'#'*60}")
    if success:
        print("# 所有测试通过!")
    else:
        print("# 部分测试失败!")
    print(f"{'#'*60}\n")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
