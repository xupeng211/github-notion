# Gitee-Notion 同步服务运维手册

## 1. 日常运维

### 1.1 服务监控
- 定期检查 CloudWatch 仪表板
- 关注以下关键指标：
  - 服务健康状态
  - API 响应时间
  - 错误率
  - 资源使用率
  - 同步延迟

### 1.2 日志检查
```bash
# 查看应用日志
aws logs get-log-events \
    --log-group-name /aws/ecs/gitee-notion-sync \
    --log-stream-name $(date +%Y/%m/%d)

# 查看错误日志
aws logs filter-log-events \
    --log-group-name /aws/ecs/gitee-notion-sync \
    --filter-pattern "ERROR"
```

### 1.3 备份验证
```bash
# 检查最近的备份状态
aws s3 ls s3://backup-bucket/config/ --recursive | sort -r | head -n 5

# 验证备份完整性
aws s3 cp s3://backup-bucket/config/latest/ ./backup-verify/ --recursive
```

### 1.4 性能优化
- 定期运行性能测试
- 分析资源使用情况
- 优化自动扩展配置

## 2. 问题处理

### 2.1 服务不可用
1. 检查健康状态：
   ```bash
   curl -f https://your-service.com/health
   ```

2. 检查日志：
   ```bash
   aws logs get-log-events \
       --log-group-name /aws/ecs/gitee-notion-sync \
       --log-stream-name $(date +%Y/%m/%d) \
       --start-time $(date -d '15 minutes ago' +%s000)
   ```

3. 检查 ECS 服务状态：
   ```bash
   aws ecs describe-services \
       --cluster gitee-notion-sync-cluster \
       --services gitee-notion-sync-service
   ```

4. 如需回滚：
   ```bash
   aws ecs update-service \
       --cluster gitee-notion-sync-cluster \
       --service gitee-notion-sync-service \
       --task-definition gitee-notion-sync:PREVIOUS_VERSION
   ```

### 2.2 同步延迟
1. 检查 Notion API 状态：
   ```bash
   curl -f https://api.notion.com/v1/users/me \
       -H "Authorization: Bearer $NOTION_API_TOKEN" \
       -H "Notion-Version: 2022-06-28"
   ```

2. 检查 Gitee API 状态：
   ```bash
   curl -f https://gitee.com/api/v5/user \
       -H "Authorization: token $GITEE_TOKEN"
   ```

3. 检查队列积压：
   ```bash
   aws cloudwatch get-metric-statistics \
       --namespace GiteeNotionSync \
       --metric-name SyncQueueSize \
       --period 300 \
       --start-time $(date -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
       --end-time $(date +%Y-%m-%dT%H:%M:%S) \
       --statistics Average
   ```

### 2.3 高错误率
1. 分析错误模式：
   ```bash
   aws logs insights-query \
       --log-group-name /aws/ecs/gitee-notion-sync \
       --query 'filter @message like /ERROR/ | stats count(*) by errorType'
   ```

2. 检查资源使用：
   ```bash
   aws cloudwatch get-metric-statistics \
       --namespace AWS/ECS \
       --metric-name CPUUtilization \
       --dimensions Name=ServiceName,Value=gitee-notion-sync \
       --period 300 \
       --start-time $(date -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
       --end-time $(date +%Y-%m-%dT%H:%M:%S) \
       --statistics Average
   ```

## 3. 维护任务

### 3.1 证书更新
1. 检查证书过期时间：
   ```bash
   aws acm describe-certificate \
       --certificate-arn ${ACM_CERTIFICATE_ARN}
   ```

2. 更新证书：
   ```bash
   aws acm import-certificate \
       --certificate-arn ${ACM_CERTIFICATE_ARN} \
       --certificate file://new-cert.pem \
       --private-key file://new-key.pem \
       --certificate-chain file://new-chain.pem
   ```

### 3.2 密钥轮换
1. 更新 Webhook 密钥：
   ```bash
   aws secretsmanager update-secret \
       --secret-id gitee-notion-sync/webhook-secret \
       --secret-string "new-secret-value"
   ```

2. 更新 API 令牌：
   ```bash
   aws secretsmanager update-secret \
       --secret-id gitee-notion-sync/api-tokens \
       --secret-string '{"notion": "new-notion-token", "gitee": "new-gitee-token"}'
   ```

### 3.3 配置更新
1. 更新任务定义：
   ```bash
   aws ecs register-task-definition \
       --cli-input-json file://task-definition.json
   ```

2. 更新服务：
   ```bash
   aws ecs update-service \
       --cluster gitee-notion-sync-cluster \
       --service gitee-notion-sync-service \
       --task-definition gitee-notion-sync:LATEST
   ```

## 4. 扩展管理

### 4.1 手动扩展
```bash
# 增加任务数量
aws ecs update-service \
    --cluster gitee-notion-sync-cluster \
    --service gitee-notion-sync-service \
    --desired-count 3

# 减少任务数量
aws ecs update-service \
    --cluster gitee-notion-sync-cluster \
    --service gitee-notion-sync-service \
    --desired-count 1
```

### 4.2 自动扩展配置
```bash
# 更新扩展策略
aws application-autoscaling put-scaling-policy \
    --policy-name cpu-tracking \
    --service-namespace ecs \
    --resource-id service/gitee-notion-sync-cluster/gitee-notion-sync-service \
    --scalable-dimension ecs:service:DesiredCount \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

## 5. 监控配置

### 5.1 告警管理
```bash
# 创建新告警
aws cloudwatch put-metric-alarm \
    --alarm-name high-error-rate \
    --metric-name ErrorCount \
    --namespace GiteeNotionSync \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions ${SNS_TOPIC_ARN}

# 查看告警状态
aws cloudwatch describe-alarms \
    --alarm-names high-error-rate
```

### 5.2 仪表板管理
```bash
# 更新仪表板
aws cloudwatch put-dashboard \
    --dashboard-name gitee-notion-sync \
    --dashboard-body file://dashboard.json
```

## 6. 成本管理

### 6.1 成本分析
```bash
# 获取月度成本报告
aws ce get-cost-and-usage \
    --time-period Start=$(date -d 'last month' +%Y-%m-01),End=$(date +%Y-%m-01) \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=TAG,Key=Project

# 检查资源标签
aws resourcegroupstaggingapi get-resources \
    --tag-filters Key=Project,Values=gitee-notion-sync
```

### 6.2 预算管理
```bash
# 更新预算配置
aws budgets update-budget \
    --account-id ${AWS_ACCOUNT_ID} \
    --budget file://budget.json

# 检查预算状态
aws budgets describe-budget \
    --account-id ${AWS_ACCOUNT_ID} \
    --budget-name gitee-notion-sync-budget
```

## 7. 安全管理

### 7.1 安全扫描
```bash
# 运行漏洞扫描
aws ecr start-image-scan \
    --repository-name gitee-notion-sync \
    --image-id imageTag=latest

# 检查扫描结果
aws ecr describe-image-scan-findings \
    --repository-name gitee-notion-sync \
    --image-id imageTag=latest
```

### 7.2 安全组管理
```bash
# 更新安全组规则
aws ec2 update-security-group-rule-descriptions-ingress \
    --group-id ${SECURITY_GROUP_ID} \
    --ip-permissions file://security-group-rules.json
```

## 8. 故障恢复

### 8.1 数据恢复
```bash
# 从备份恢复配置
aws s3 cp s3://backup-bucket/config/latest/ ./config/ --recursive

# 应用恢复的配置
aws ecs update-service \
    --cluster gitee-notion-sync-cluster \
    --service gitee-notion-sync-service \
    --force-new-deployment
```

### 8.2 服务恢复
```bash
# 在备用区域启动服务
aws ecs create-service \
    --cluster gitee-notion-sync-cluster-backup \
    --service-name gitee-notion-sync-service \
    --task-definition gitee-notion-sync:LATEST \
    --desired-count 1

# 更新 DNS
aws route53 change-resource-record-sets \
    --hosted-zone-id ${HOSTED_ZONE_ID} \
    --change-batch file://dns-update.json
```

## 9. 联系信息

### 9.1 团队联系方式
- 运维团队：[联系方式]
- 开发团队：[联系方式]
- 安全团队：[联系方式]

### 9.2 外部支持
- AWS 支持：[联系方式]
- Notion 支持：[联系方式]
- Gitee 支持：[联系方式]
