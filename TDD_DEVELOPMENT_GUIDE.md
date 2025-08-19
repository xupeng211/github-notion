# 🔄 测试驱动开发 (TDD) 指南

## 📋 概览

测试驱动开发 (Test-Driven Development, TDD) 是一种软件开发方法，要求在编写功能代码之前先编写测试。

## 🎯 TDD 的三个步骤

### 🔴 Red - 编写失败的测试
1. 编写一个描述新功能的测试
2. 运行测试，确保它失败
3. 确保失败的原因是功能未实现，而不是测试错误

### 🟢 Green - 编写最少代码使测试通过
1. 编写最少的代码使测试通过
2. 不要过度设计，只关注让测试通过
3. 运行所有测试，确保新代码没有破坏现有功能

### 🔵 Refactor - 重构代码
1. 清理代码，消除重复
2. 改进设计和结构
3. 运行测试，确保重构没有改变行为

## 🛠️ TDD 实践示例

### 示例：添加新的 Webhook 事件类型支持

#### 步骤 1: 🔴 编写失败的测试

```python
# tests/priority/core_business/test_new_webhook_events.py
def test_should_process_pull_request_opened_event():
    """测试应该处理 pull request opened 事件"""
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "title": "Test PR",
            "body": "Test PR body",
            "state": "open",
            "html_url": "https://github.com/test/repo/pull/123",
            "user": {"login": "testuser"}
        },
        "repository": {
            "name": "test-repo",
            "owner": {"login": "testowner"}
        }
    }
    
    body_bytes = json.dumps(payload).encode('utf-8')
    
    # 这个测试现在会失败，因为功能还没实现
    success, message = process_github_event(body_bytes, "pull_request")
    
    assert success is True
    assert message == "ok"
```

运行测试：
```bash
python -m pytest tests/priority/core_business/test_new_webhook_events.py::test_should_process_pull_request_opened_event -v
# 预期：测试失败 ❌
```

#### 步骤 2: 🟢 编写最少代码使测试通过

```python
# app/service.py
def process_github_event(body_bytes: bytes, event_type: str) -> tuple[bool, str]:
    """处理 GitHub 事件"""
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
        
        # 添加对 pull_request 事件的支持
        if event_type == "pull_request":
            return process_pull_request_event(payload)
        elif event_type == "issues":
            return process_issues_event(payload)
        else:
            return True, "ignored_event"
    except Exception as e:
        return False, f"error: {str(e)}"

def process_pull_request_event(payload: dict) -> tuple[bool, str]:
    """处理 pull request 事件"""
    # 最少的实现，只是让测试通过
    if payload.get("action") == "opened":
        return True, "ok"
    return True, "ignored_action"
```

运行测试：
```bash
python -m pytest tests/priority/core_business/test_new_webhook_events.py::test_should_process_pull_request_opened_event -v
# 预期：测试通过 ✅
```

#### 步骤 3: 🔵 重构代码

```python
# app/service.py
def process_github_event(body_bytes: bytes, event_type: str) -> tuple[bool, str]:
    """处理 GitHub 事件"""
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
        
        # 使用策略模式重构
        event_processors = {
            "issues": process_issues_event,
            "pull_request": process_pull_request_event,
        }
        
        processor = event_processors.get(event_type)
        if processor:
            return processor(payload)
        else:
            return True, "ignored_event"
            
    except Exception as e:
        return False, f"error: {str(e)}"

def process_pull_request_event(payload: dict) -> tuple[bool, str]:
    """处理 pull request 事件"""
    action = payload.get("action")
    
    if action in ["opened", "edited", "closed"]:
        # 重构：提取通用逻辑
        return process_github_item_event(payload, "pull_request")
    
    return True, "ignored_action"

def process_github_item_event(payload: dict, item_type: str) -> tuple[bool, str]:
    """处理 GitHub 项目事件的通用逻辑"""
    # 通用的处理逻辑
    return True, "ok"
```

运行所有测试：
```bash
all_priority_tests
# 确保重构没有破坏现有功能
```

## 🎯 TDD 最佳实践

### 1. 测试命名规范
```python
def test_should_[expected_behavior]_when_[condition]():
    """清晰描述测试意图"""
    pass

# 好的例子
def test_should_create_notion_page_when_github_issue_opened():
def test_should_reject_webhook_when_signature_invalid():
def test_should_retry_request_when_api_returns_500():
```

### 2. 测试结构 (AAA 模式)
```python
def test_example():
    # Arrange - 准备测试数据和环境
    payload = create_test_payload()
    mock_service = setup_mock_service()
    
    # Act - 执行被测试的操作
    result = process_event(payload)
    
    # Assert - 验证结果
    assert result.success is True
    assert result.message == "expected_message"
```

### 3. 一次只测试一个行为
```python
# 好的例子 - 每个测试只验证一个行为
def test_should_validate_signature():
    # 只测试签名验证
    pass

def test_should_parse_payload():
    # 只测试 payload 解析
    pass

# 避免的例子 - 一个测试验证多个行为
def test_should_validate_and_parse_and_process():
    # 测试太复杂，难以维护
    pass
```

### 4. 使用描述性的断言消息
```python
def test_webhook_processing():
    result = process_webhook(payload)
    
    # 好的例子
    assert result.success, f"Webhook processing failed: {result.error}"
    assert result.page_id, "Notion page ID should be returned"
    
    # 避免的例子
    assert result.success  # 失败时不知道原因
```

## 🔄 TDD 工作流集成

### 开发新功能的完整流程

```bash
# 1. 创建功能分支
git checkout -b feature/new-webhook-support

# 2. 编写失败的测试
vim tests/priority/core_business/test_new_feature.py

# 3. 运行测试，确保失败
python -m pytest tests/priority/core_business/test_new_feature.py -v

# 4. 编写最少代码使测试通过
vim app/service.py

# 5. 运行测试，确保通过
python -m pytest tests/priority/core_business/test_new_feature.py -v

# 6. 运行所有测试，确保没有破坏现有功能
all_priority_tests

# 7. 重构代码
vim app/service.py

# 8. 再次运行所有测试
all_priority_tests

# 9. 提交代码
smart_commit "feat: add new webhook support with TDD"

# 10. 推送代码
safe_push
```

### IDE 集成

#### VS Code 配置
```json
// .vscode/settings.json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests/priority"
    ],
    "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

#### 快捷键配置
```json
// .vscode/keybindings.json
[
    {
        "key": "ctrl+shift+t",
        "command": "python.runCurrentTest"
    },
    {
        "key": "ctrl+shift+a",
        "command": "python.runAllTests"
    }
]
```

## 📊 TDD 指标监控

### 关键指标
- **测试覆盖率**: 新功能应该有 100% 测试覆盖
- **测试通过率**: 应该始终保持 100%
- **重构频率**: 每个功能至少重构一次
- **测试执行时间**: 单个测试 < 1秒

### 监控脚本
```bash
#!/bin/bash
# tdd-metrics.sh - TDD 指标监控

echo "📊 TDD 指标报告"
echo "==============="

# 测试覆盖率
echo "🎯 测试覆盖率:"
python -m pytest tests/priority/ --cov=app --cov-report=term | grep TOTAL

# 测试执行时间
echo "⏱️ 测试执行时间:"
python -m pytest tests/priority/ --durations=10

# 测试通过率
echo "✅ 测试通过率:"
python -m pytest tests/priority/ --tb=no -q
```

## 🎓 团队 TDD 培训

### 培训计划
1. **理论学习** (1小时): TDD 原理和好处
2. **实践演示** (1小时): 现场 TDD 演示
3. **动手练习** (2小时): 团队成员实践 TDD
4. **代码审查** (持续): 审查 TDD 实践

### 常见问题和解决方案

#### Q: 写测试太慢，影响开发效率？
A: 
- 初期确实会慢一些，但长期会提高效率
- 减少调试时间和 bug 修复时间
- 提高代码质量和可维护性

#### Q: 如何测试复杂的业务逻辑？
A:
- 将复杂逻辑分解为小的函数
- 使用 Mock 隔离外部依赖
- 专注于测试行为而不是实现

#### Q: 测试代码也需要维护，增加了工作量？
A:
- 好的测试是活文档，帮助理解代码
- 测试帮助安全重构，减少维护成本
- 投入产出比是正向的

## 🚀 TDD 成功案例

### 案例 1: Webhook 安全验证
使用 TDD 开发的 webhook 安全验证功能：
- 19 个测试，100% 覆盖关键场景
- 零安全漏洞
- 代码简洁，易于维护

### 案例 2: GitHub-Notion 同步
使用 TDD 开发的同步功能：
- 22 个测试，覆盖主要业务场景
- 幂等性保证，无重复同步
- 错误处理完善

---

**🎯 目标：在1个月内，所有新功能开发都采用 TDD 方法，提高代码质量和开发效率！** 🔄
