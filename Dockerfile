# 最优策略：使用官方python镜像避免编译问题
# GitHub Actions资源限制下的最佳实践

# 使用标准Python镜像（非slim），包含必要的编译工具
FROM python:3.11-bullseye AS builder

# 设置工作目录
WORKDIR /app

# 设置环境变量优化构建
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_PREFER_BINARY=1

# 安装构建依赖，确保如 cryptography/httptools/uvloop 等可编译
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 升级pip到最新版本，并设置构建优化
RUN pip install --upgrade pip setuptools wheel && \
    pip config set global.cache-dir /tmp/pip-cache && \
    pip config set global.prefer-binary true

# 复制并安装Python依赖（优先二进制轮子，减少编译时间）
COPY requirements.txt .
RUN --mount=type=cache,target=/tmp/pip-cache \
    pip install --user --no-warn-script-location \
    --cache-dir=/tmp/pip-cache \
    --prefer-binary \
    --timeout=300 \
    --retries=3 \
    -r requirements.txt

# 生产阶段：使用相同基础镜像保持兼容性
FROM python:3.11-bullseye

WORKDIR /app

# 安装生产环境必需的系统工具（包括curl用于健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# 复制构建产物到appuser的目录
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# 复制应用代码
COPY --chown=appuser:appuser . .

# 切换到非root用户
USER appuser

# 设置PATH (使用appuser的本地目录)
ENV PATH="/home/appuser/.local/bin:$PATH"

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
