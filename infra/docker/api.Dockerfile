# ================================
# 🚀 GitHub-Notion API 多阶段构建 Dockerfile
# 优化构建上下文和层缓存，支持CI/CD环境
# ================================

# ================================
# 阶段1: 依赖构建阶段
# ================================
FROM python:3.11-slim-bullseye@sha256:9e25f400253a5fa3191813d6a67eb801ca1e6f012b3bd2588fa6920b59e3eba6 AS dependencies

# 设置工作目录
WORKDIR /app

# 设置环境变量 - 优化pip安装
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=3 \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 升级pip和构建工具
RUN python -m pip install --upgrade pip setuptools wheel

# 先复制依赖文件（利用Docker层缓存）
COPY requirements.txt .
COPY requirements-dev.txt* ./

# 安装Python依赖（这一层会被缓存，除非requirements.txt改变）
RUN echo "🔧 安装Python依赖..." && \
    pip install --no-cache-dir \
    --timeout 300 \
    --retries 3 \
    --prefer-binary \
    -r requirements.txt && \
    echo "✅ 依赖安装完成"

# ================================
# 阶段2: 运行时阶段
# ================================
FROM python:3.11-slim-bullseye@sha256:9e25f400253a5fa3191813d6a67eb801ca1e6f012b3bd2588fa6920b59e3eba6 AS runtime

# 设置工作目录
WORKDIR /app

# 设置运行时环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# 安装运行时必需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从依赖阶段复制已安装的Python包
COPY --from=dependencies /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=dependencies /usr/local/bin/ /usr/local/bin/

# 创建非root用户（安全最佳实践）
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制应用代码（只复制必要文件，排除测试和缓存）
COPY app/ ./app/
COPY *.py ./
COPY docker-compose.yml* ./

# 创建必要的目录并设置权限
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 暴露端口
EXPOSE ${PORT}

# 启动命令
CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
