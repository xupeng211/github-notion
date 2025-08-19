# 🧪 测试体系使用指南

## 📋 概览

本项目采用三层测试架构，提供全面的质量保障：

- **🔐 安全测试**: 防止安全漏洞
- **🔄 核心业务测试**: 确保业务逻辑正确性
- **🌐 API 集成测试**: 保证外部服务集成稳定性

## 🚀 快速开始

### 1. 环境设置

```bash
# 安装测试依赖
pip install pytest pytest-cov pytest-mock pytest-asyncio responses

# 加载开发命令
source scripts/dev-commands.sh
```

### 2. 运行测试

```bash
# 运行所有测试 (推荐)
all_priority_tests

# 运行单独测试模块
security_test           # 安全测试 (30秒)
core_business_test      # 核心业务测试 (1分钟)
api_integration_test    # API 集成测试 (2分钟)
```

## 📊 测试架构

### 🔐 安全测试 (19个测试)
**文件**: `tests/priority/security/test_webhook_security_priority.py`
**覆盖**: `app/webhook_security.py` (58% 覆盖率)

**测试内容**:
- Webhook 签名验证
- 重放攻击防护
- 时序攻击防护
- 边界情况处理

**何时运行**: 修改安全相关代码后

### 🔄 核心业务测试 (22个测试)
**文件**: `tests/priority/core_business/test_service_priority.py`
**覆盖**: `app/service.py` (42% 覆盖率)

**测试内容**:
- GitHub ↔ Notion 同步流程
- 错误处理和重试机制
- 幂等性和防循环
- 异步函数和边界情况

**何时运行**: 修改业务逻辑后

### 🌐 API 集成测试 (27个测试)
**文件**: `tests/priority/api_integration/test_api_integration_priority.py`
**覆盖**: `app/github.py` + `app/notion.py` (48% 覆盖率)

**测试内容**:
- GitHub API 集成
- Notion API 集成
- 网络异常处理
- 并发操作验证

**何时运行**: 修改 API 集成代码后

## 🛠️ 开发工作流

### 标准开发流程

```bash
# 1. 修改代码
vim app/service.py

# 2. 运行相关测试
core_business_test

# 3. 如果测试通过，提交代码
smart_commit "feat: add new feature"

# 4. 推送代码
safe_push
```

### 完整开发流程

```bash
# 一键完成：修复 + 测试 + 提交 + 推送
dev_flow "feat: implement new feature"
```

## 📈 质量标准

### 覆盖率要求
- **安全模块**: > 50%
- **核心业务模块**: > 40%
- **API 集成模块**: > 45%
- **整体项目**: > 50%

### 测试通过率
- **所有测试必须通过**: 68/68 = 100%
- **CI/CD 质量门禁**: 测试失败阻止部署

## 🔍 故障排除

### 常见问题

#### 1. 测试失败
```bash
# 查看详细错误信息
python -m pytest tests/priority/security/ -v --tb=long

# 运行单个测试
python -m pytest tests/priority/security/test_webhook_security_priority.py::TestWebhookSecurityValidator::test_github_valid_signature_verification -v
```

#### 2. 覆盖率不足
```bash
# 生成详细覆盖率报告
python -m pytest tests/priority/ --cov=app --cov-report=html:coverage-report

# 查看报告
open coverage-report/index.html
```

#### 3. 依赖问题
```bash
# 重新安装依赖
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock pytest-asyncio responses
```

## 📝 编写新测试

### 测试文件结构
```
tests/priority/
├── security/           # 安全测试
├── core_business/      # 核心业务测试
└── api_integration/    # API 集成测试
```

### 测试命名规范
```python
def test_should_do_something_when_condition():
    """测试描述：在特定条件下应该执行某个操作"""
    # Arrange - 准备测试数据
    # Act - 执行被测试的操作
    # Assert - 验证结果
```

### 测试类型指南

#### 单元测试
```python
def test_webhook_signature_validation():
    """测试单个函数的行为"""
    validator = WebhookSecurityValidator("secret", "github")
    result = validator.verify_signature(payload, signature)
    assert result is True
```

#### 集成测试
```python
@patch('app.service.notion_upsert_page')
def test_github_to_notion_sync(mock_notion):
    """测试模块间交互"""
    mock_notion.return_value = (True, "page_123")
    success, message = process_github_event(payload, "issues")
    assert success is True
```

#### Mock 测试
```python
@responses.activate
def test_github_api_call():
    """测试外部 API 调用"""
    responses.add(responses.GET, "https://api.github.com/...", json={...})
    result = github_service.get_issue("owner", "repo", 123)
    assert result is not None
```

## 🎯 最佳实践

### 1. 测试驱动开发 (TDD)
1. 先写测试
2. 运行测试（应该失败）
3. 编写最少代码使测试通过
4. 重构代码
5. 重复循环

### 2. 测试金字塔
- **70% 单元测试**: 快速、独立、覆盖具体功能
- **20% 集成测试**: 测试模块间交互
- **10% 端到端测试**: 测试完整用户场景

### 3. 测试维护
- 定期审查测试覆盖率
- 删除过时的测试
- 重构重复的测试代码
- 保持测试简单和可读

## 🚀 CI/CD 集成

### GitHub Actions 工作流

测试自动在以下情况运行：
- **Push 到 main/develop**: 运行完整测试套件
- **Pull Request**: 运行相关测试
- **手动触发**: 可选择测试级别

### 质量门禁

部署前必须满足：
- ✅ 所有测试通过
- ✅ 覆盖率达标
- ✅ 无安全漏洞

## 📊 监控和报告

### 覆盖率报告
- **本地**: `coverage-report/index.html`
- **CI/CD**: Codecov 集成
- **GitHub**: PR 中的覆盖率评论

### 测试报告
- **本地**: 终端输出
- **CI/CD**: GitHub Actions 摘要
- **失败通知**: Slack/Email 集成

## 🎓 团队培训

### 新成员入门
1. 阅读本指南
2. 运行 `all_priority_tests` 验证环境
3. 修改一个测试并观察结果
4. 编写一个新测试

### 定期培训
- **月度**: 测试覆盖率审查
- **季度**: 测试策略优化
- **年度**: 测试工具和框架更新

## 📞 支持

### 获取帮助
- **文档**: 查看测试报告和覆盖率
- **命令**: 使用 `source scripts/dev-commands.sh` 查看可用命令
- **问题**: 在团队频道提问

### 贡献改进
- 发现测试覆盖盲点时添加测试
- 优化慢速测试
- 改进测试文档和工具

---

**🎉 恭喜！你现在掌握了完整的测试体系。记住：好的测试是代码质量的保障，也是团队协作的基础！** 🚀
