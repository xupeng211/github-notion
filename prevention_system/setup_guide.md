# 🛡️ CI/CD 问题预防体系实施指南

## 📋 概述

这套预防体系通过四个层级的防护，从根源上避免CI/CD问题的发生：

1. **🏗️ 架构层预防** - 环境一致性保障和自适应架构
2. **🔧 工具链预防** - 示例值管理和增强的Pre-commit检查
3. **🧪 测试层预防** - 智能测试生成和环境模拟
4. **📊 监控层预防** - 实时问题检测和告警

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install psutil sqlalchemy
```

### 2. 基础设置

```python
from prevention_system import setup_prevention_system, quick_health_check

# 设置预防系统
prevention_config = {
    "enable_monitoring": True,
    "enable_env_consistency": True,
    "enable_example_management": True,
    "enable_enhanced_precommit": True
}

systems = setup_prevention_system(prevention_config)

# 运行健康检查
is_healthy = quick_health_check()
```

### 3. Pre-commit Hook 集成

在 `.pre-commit-config.yaml` 中添加：

```yaml
repos:
  - repo: local
    hooks:
      - id: example-value-check
        name: Example Value Security Check
        entry: python -m prevention_system.example_value_manager
        args: [scan, --directory, .]
        language: system
        pass_filenames: false

      - id: enhanced-precommit
        name: Enhanced Pre-commit Checks
        entry: python -m prevention_system.enhanced_precommit
        language: system
        pass_filenames: false
```

## 🏗️ 架构层预防详细配置

### 环境一致性管理

```python
from prevention_system import EnvironmentConsistencyManager

# 在不同环境中捕获配置档案
manager = EnvironmentConsistencyManager()

# 本地环境
with SessionLocal() as db:
    local_profile = manager.capture_environment_profile("local", db)
    manager.save_profile(local_profile, "profiles/local.json")

# CI环境（在CI中运行）
with SessionLocal() as db:
    ci_profile = manager.capture_environment_profile("ci", db)
    manager.save_profile(ci_profile, "profiles/ci.json")

# 比较差异
differences = manager.compare_environments("local", "ci")
adapter_code = manager.generate_compatibility_adapter(differences)

# 保存适配器代码
with open("app/environment_adapter.py", "w") as f:
    f.write(adapter_code)
```

### 自适应架构实现

```python
from prevention_system import adaptive_function, capability_registry

# 注册自定义能力检测器
def detect_custom_feature(db):
    # 自定义检测逻辑
    return True

capability_registry.register_capability('custom_feature', detect_custom_feature)

# 使用自适应函数装饰器
@adaptive_function('source_platform_column')
def my_database_function(db, param1, param2):
    # 函数会根据环境能力自动适配
    pass
```

## 🔧 工具链预防详细配置

### 示例值管理

```python
from prevention_system import ExampleValueManager

manager = ExampleValueManager()

# 扫描项目中的危险示例值
results = manager.scan_directory(".")

# 生成报告
report = manager.generate_report(results, "security_scan_report.md")

# 自动修复
for filepath, findings in results["files"].items():
    manager.fix_file(filepath, findings)
```

### 增强的Pre-commit系统

```python
from prevention_system import EnhancedPreCommitSystem

system = EnhancedPreCommitSystem()

# 运行所有检查
all_passed, results = system.run_all_checks()

# 生成报告
report = system.generate_report(results)
print(report)

# 交互式修复
if not all_passed:
    system.run_interactive_fix(results)
```

## 🧪 测试层预防详细配置

### 智能测试生成

```python
from prevention_system import SmartTestGenerator

generator = SmartTestGenerator()

# 为特定函数生成测试
test_cases = generator.generate_tests_for_function("app/models.py", "should_skip_event")

# 为整个文件生成测试
test_file = generator.generate_test_file("app/service.py", "tests/test_service_generated.py")
```

### 环境模拟测试

```python
from prevention_system import EnvironmentSimulator, cross_environment_test

# 使用装饰器进行跨环境测试
@cross_environment_test(["local_dev", "ci_fresh", "production"])
def test_my_function(session, env_context):
    # 测试逻辑
    result = my_function(session, "test_data")
    assert result is not None
    return result

# 手动环境模拟
simulator = EnvironmentSimulator()
with simulator.simulate_environment("ci_fresh") as env:
    # 在模拟的CI环境中运行测试
    session = env["session_factory"]()
    test_my_function(session, env)
```

## 📊 监控层预防详细配置

### 实时监控设置

```python
from prevention_system import RealtimeMonitor, console_alert_handler, webhook_alert_handler

# 创建监控实例
monitor = RealtimeMonitor(check_interval=30)

# 添加告警处理器
monitor.add_alert_handler(console_alert_handler)
monitor.add_alert_handler(webhook_alert_handler("https://your-webhook-url.com"))

# 启动监控
monitor.start()

# 获取健康状态
health = monitor.get_health_status()
print(f"System status: {health['status']}")

# 获取最近告警
recent_alerts = monitor.get_recent_alerts(hours=24)
```

## 📁 项目结构建议

```
your_project/
├── prevention_system/          # 预防系统代码
│   ├── __init__.py
│   ├── environment_consistency.py
│   ├── adaptive_architecture.py
│   ├── example_value_manager.py
│   ├── enhanced_precommit.py
│   ├── smart_test_generator.py
│   ├── environment_simulator.py
│   └── realtime_monitor.py
├── profiles/                   # 环境配置档案
│   ├── local.json
│   ├── ci.json
│   └── production.json
├── tests/
│   ├── generated/              # 自动生成的测试
│   └── environment/            # 环境特定测试
├── .pre-commit-config.yaml     # 增强的pre-commit配置
├── .secrets.baseline           # 安全扫描基线
└── prevention_config.yaml     # 预防系统配置
```

## ⚙️ 配置文件示例

### prevention_config.yaml

```yaml
prevention_system:
  monitoring:
    enabled: true
    check_interval: 30
    alert_handlers:
      - console
      - webhook: "https://your-webhook-url.com"

  environment_consistency:
    enabled: true
    profile_directory: "profiles"
    auto_generate_adapters: true

  example_management:
    enabled: true
    auto_fix: false
    scan_extensions: [".py", ".yml", ".yaml", ".json", ".env", ".example"]
    exclude_patterns:
      - ".git/*"
      - "node_modules/*"
      - "__pycache__/*"

  enhanced_precommit:
    enabled: true
    checks:
      - example_values
      - test_completeness
      - database_compatibility
      - environment_consistency
      - documentation_sync

  smart_testing:
    enabled: true
    auto_generate: false
    test_output_directory: "tests/generated"

  environment_simulation:
    enabled: true
    environments:
      - local_dev
      - ci_fresh
      - production
      - minimal
```

## 🔄 CI/CD 集成

### GitHub Actions 集成

```yaml
name: Enhanced CI with Prevention System

on: [push, pull_request]

jobs:
  prevention-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install psutil

      - name: Run prevention system checks
        run: |
          python -c "
          from prevention_system import quick_health_check
          import sys
          if not quick_health_check():
              sys.exit(1)
          "

      - name: Enhanced pre-commit checks
        run: python -m prevention_system.enhanced_precommit

      - name: Cross-environment tests
        run: python -m pytest tests/environment/ -v
```

## 📈 监控和告警

### 健康检查端点

```python
from flask import Flask, jsonify
from prevention_system import get_monitor

app = Flask(__name__)

@app.route('/health')
def health_check():
    monitor = get_monitor()
    health_status = monitor.get_health_status()

    status_code = 200 if health_status['status'] != 'critical' else 503
    return jsonify(health_status), status_code

@app.route('/metrics')
def metrics():
    monitor = get_monitor()
    metrics = monitor.get_metrics_summary()
    return jsonify(metrics)

@app.route('/alerts')
def alerts():
    monitor = get_monitor()
    alerts = monitor.get_recent_alerts(hours=24)
    return jsonify([alert.__dict__ for alert in alerts])
```

## 🎯 最佳实践

### 1. 渐进式部署
- 先在开发环境部署监控系统
- 逐步启用各个预防模块
- 根据实际情况调整阈值和规则

### 2. 团队培训
- 培训团队成员使用新的工具
- 建立问题响应流程
- 定期回顾和改进

### 3. 持续优化
- 定期分析告警数据
- 优化检测规则和阈值
- 根据新问题扩展检查项

### 4. 文档维护
- 保持配置文档更新
- 记录问题解决方案
- 分享最佳实践

## 🔧 故障排除

### 常见问题

1. **监控系统启动失败**
   ```bash
   # 检查依赖
   pip install psutil sqlalchemy

   # 检查权限
   python -c "import psutil; print(psutil.cpu_percent())"
   ```

2. **环境检测失败**
   ```bash
   # 检查数据库连接
   python -c "from app.models import SessionLocal; SessionLocal()"

   # 检查环境变量
   python -c "import os; print(os.environ.get('DB_URL'))"
   ```

3. **Pre-commit检查失败**
   ```bash
   # 手动运行检查
   python -m prevention_system.enhanced_precommit

   # 查看详细错误
   python -m prevention_system.enhanced_precommit --interactive
   ```

## 📞 支持和反馈

如果遇到问题或有改进建议，请：

1. 检查日志文件中的详细错误信息
2. 运行 `quick_health_check()` 进行诊断
3. 查看监控系统的告警信息
4. 参考故障排除指南

这套预防体系将帮助你的团队避免重复遇到类似的CI/CD问题，提高开发效率和代码质量！
