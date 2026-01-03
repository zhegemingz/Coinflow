# 大规模模糊测试指南

本指南介绍如何使用增强版的模糊测试工具来发现潜在的崩溃和边界问题。

## 测试类型

### 1. 压力测试 (Stress Testing)
测试系统在大量数据下的表现：
- **大规模交易插入**：100-1000 条交易的批量插入
- **多分类组合测试**：5-50 个分类，每个分类 10-100 条交易
- **长时间范围统计**：30-365 天的日期范围，每天 1-50 条交易

### 2. 边界测试 (Boundary Testing)
测试极端值和边界条件：
- **极端金额**：0 到 1e15 之间的任意金额
- **极端备注长度**：0 到 10000 字符的备注
- **极端日期时间**：1900-2100 年的任意日期时间
- **浮点数精度**：1e-10 到 1e10 的精度测试

### 3. 并发测试 (Concurrent Testing)
测试多线程环境下的正确性：
- **并发插入**：2-10 个线程同时插入交易
- **混合操作**：并发执行插入、查询、更新、删除操作

### 4. 崩溃检测 (Crash Detection)
专门检测潜在的崩溃和内存泄漏：
- **快速创建删除循环**：100-1000 次创建和删除操作
- **快速统计查询**：50-500 次统计查询
- **批量更新测试**：更新所有交易数据

## 使用方法

### 方法 1：使用运行脚本（推荐）

```bash
# 运行所有模糊测试
python run_fuzzing_tests.py

# 只运行压力测试
python run_fuzzing_tests.py --type stress

# 只运行边界测试
python run_fuzzing_tests.py --type boundary

# 只运行并发测试
python run_fuzzing_tests.py --type concurrent

# 只运行崩溃检测
python run_fuzzing_tests.py --type crash

# 详细输出
python run_fuzzing_tests.py --verbose

# 限制测试示例数（加快测试速度）
python run_fuzzing_tests.py --max-examples 50

# 设置超时时间
python run_fuzzing_tests.py --timeout 300
```

### 方法 2：直接使用 pytest

```bash
# 运行所有模糊测试
pytest test_fuzzing_stress.py -v

# 运行特定测试类
pytest test_fuzzing_stress.py::TestStressFuzzing -v

# 运行特定测试方法
pytest test_fuzzing_stress.py::TestStressFuzzing::test_massive_transaction_insertion -v

# 使用标记运行
pytest -m stress -v
pytest -m boundary -v
pytest -m concurrent -v
pytest -m crash -v

# 组合标记
pytest -m "stress or boundary" -v
```

### 方法 3：使用 Hypothesis 高级选项

```bash
# 增加测试示例数（更彻底的测试）
pytest test_fuzzing_stress.py --hypothesis-max-examples 500 -v

# 禁用超时限制
pytest test_fuzzing_stress.py --hypothesis-deadline=None -v

# 设置详细输出
pytest test_fuzzing_stress.py --hypothesis-verbosity=verbose -v

# 只运行生成阶段（跳过重试）
pytest test_fuzzing_stress.py --hypothesis-phases=generate -v

# 保存失败的测试用例
pytest test_fuzzing_stress.py --hypothesis-seed=12345 -v
```

## 测试配置

### pytest.ini 配置

```ini
[pytest]
hypothesis settings
max_examples = 100      # 默认最大示例数
deadline = 1000         # 默认超时（毫秒）
verbosity = 0           # 默认详细程度
```

### 在代码中覆盖配置

```python
from hypothesis import given, settings, Phase, Verbosity

@settings(
    max_examples=500,           # 增加示例数
    deadline=None,              # 禁用超时
    phases=[Phase.generate],    # 只运行生成阶段
    verbosity=Verbosity.verbose # 详细输出
)
def test_something():
    pass
```

## 持续集成

### 在 GitHub Actions 中运行大规模模糊测试

可以在 `.github/workflows/ci.yml` 中添加：

```yaml
- name: Run stress fuzzing tests
  run: |
    python run_fuzzing_tests.py --type stress --max-examples 100

- name: Run boundary fuzzing tests
  run: |
    python run_fuzzing_tests.py --type boundary --max-examples 200

- name: Run concurrent fuzzing tests
  run: |
    python run_fuzzing_tests.py --type concurrent --max-examples 50

- name: Run crash detection tests
  run: |
    python run_fuzzing_tests.py --type crash --max-examples 100
```

### 定期运行完整测试

建议设置定时任务（如每周运行一次完整测试）：

```yaml
name: Weekly Fuzzing Tests

on:
  schedule:
    - cron: '0 0 * * 0'  # 每周日午夜运行

jobs:
  fuzzing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run all fuzzing tests
        run: |
          python run_fuzzing_tests.py --type all --max-examples 500
```

## 分析测试结果

### 查看失败的测试用例

当测试失败时，Hypothesis 会生成一个最小化的失败用例：

```bash
# 重新运行失败的测试
pytest test_fuzzing_stress.py::TestBoundaryFuzzing::test_extreme_amounts -v

# Hypothesis 会显示导致失败的最小输入
```

### 使用 Hypothesis 数据库

Hypothesis 会自动保存失败的测试用例到 `.hypothesis/` 目录：

```bash
# 查看保存的失败用例
ls .hypothesis/examples/

# 清理保存的失败用例
rm -rf .hypothesis/
```

### 性能分析

使用 Python 的 cProfile 进行性能分析：

```bash
python -m cProfile -o profile.stats -m pytest test_fuzzing_stress.py::TestStressFuzzing -v

# 查看分析结果
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

## 最佳实践

1. **逐步增加测试强度**：从较少的示例数开始，逐步增加
2. **定期运行完整测试**：在 CI 中运行快速测试，定期运行完整测试
3. **关注失败的测试**：每个失败的测试都可能暴露一个真实的 bug
4. **保存失败的用例**：Hypothesis 会自动保存，便于复现问题
5. **性能监控**：关注测试运行时间，发现性能退化
6. **内存监控**：使用工具监控内存使用，发现内存泄漏

## 故障排除

### 测试超时

如果测试经常超时：

```bash
# 增加超时时间
pytest test_fuzzing_stress.py --hypothesis-deadline=5000 -v

# 禁用超时
pytest test_fuzzing_stress.py --hypothesis-deadline=None -v
```

### 测试运行太慢

如果测试运行时间过长：

```bash
# 减少示例数
pytest test_fuzzing_stress.py --hypothesis-max-examples=50 -v

# 只运行特定测试
pytest test_fuzzing_stress.py::TestBoundaryFuzzing -v
```

### 文件锁定问题

如果遇到数据库文件锁定错误：

- 确保正确关闭数据库连接
- 使用测试的 cleanup 方法清理资源
- 增加重试次数和延迟

## 扩展测试

### 添加新的模糊测试

在 `test_fuzzing_stress.py` 中添加新的测试类：

```python
class TestMyNewFuzzing:
    @pytest.fixture
    def db_manager(self):
        # 设置测试数据库
        pass
    
    @given(
        param1=st.floats(min_value=0, max_value=1000),
        param2=st.text(min_size=0, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_my_new_scenario(self, db_manager, param1, param2):
        # 测试逻辑
        pass
```

### 自定义 Hypothesis 策略

```python
from hypothesis import strategies as st

# 自定义金额策略
def amount_strategy():
    return st.floats(
        min_value=0,
        max_value=1e6,
        allow_nan=False,
        allow_infinity=False
    )

# 自定义日期策略
def date_strategy():
    return st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2030, 12, 31)
    )
```

## 参考资源

- [Hypothesis 官方文档](https://hypothesis.readthedocs.io/)
- [pytest 文档](https://docs.pytest.org/)
- [模糊测试最佳实践](https://github.com/HypothesisWorks/hypothesis/blob/master/guides/what-is-property-based-testing.md)
