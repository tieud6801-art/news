# TrendRadar Docker 部署操作文档

> **项目地址**: https://github.com/sansan0/TrendRadar  
> **版本**: 6.0.0  
> **最后更新**: 2026-03-08

---

## 目录

- [前置条件](#前置条件)
- [一、克隆项目](#一克隆项目)
- [二、配置环境变量](#二配置环境变量)
- [三、构建与启动](#三构建与启动)
- [四、验证运行](#四验证运行)
- [五、日常管理命令](#五日常管理命令)
- [六、通知渠道配置](#六通知渠道配置)
- [七、AI 分析功能](#七ai-分析功能)
- [八、MCP 服务（可选）](#八mcp-服务可选)
- [九、目录结构说明](#九目录结构说明)
- [十、更新升级](#十更新升级)
- [十一、常见问题排查](#十一常见问题排查)

---

## 前置条件

| 依赖 | 最低版本 | 检查命令 |
|------|---------|---------|
| Docker | ≥ 20.10 | `docker --version` |
| Docker Compose | ≥ 2.0 | `docker compose version` |

---

## 一、克隆项目

```bash
git clone https://github.com/sansan0/TrendRadar.git
cd TrendRadar
```

---

## 二、配置环境变量

项目已内置 `docker/.env` 文件，编辑即可：

```bash
vim docker/.env
```

### 最小化配置（仅抓取，无推送）

只需确认以下参数：

```dotenv
ENABLE_WEBSERVER=true          # 开启 Web 报告服务
WEBSERVER_PORT=5555            # Web 端口（可自定义，避免与其他服务冲突）
RUN_MODE=cron                  # 定时模式
CRON_SCHEDULE=*/30 * * * *    # 每 30 分钟抓取一次
IMMEDIATE_RUN=true             # 启动时立即执行首次抓取
```

### `.env` 完整参数说明

<details>
<summary>点击展开 .env 全部参数</summary>

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| **Web 服务器** | | |
| `ENABLE_WEBSERVER` | `false` | 是否启动 Web 服务器托管 HTML 报告 |
| `WEBSERVER_PORT` | `8080` | Web 服务器端口（可改为 5555 等任意端口） |
| **运行模式** | | |
| `RUN_MODE` | `cron` | `cron`（定时循环）/ `once`（执行一次退出） |
| `CRON_SCHEDULE` | `*/30 * * * *` | cron 表达式（默认每 30 分钟） |
| `IMMEDIATE_RUN` | `true` | 启动时是否立即执行一次 |
| **飞书** | | |
| `FEISHU_WEBHOOK_URL` | 空 | 飞书机器人 Webhook URL（多账号用 `;` 分隔） |
| **Telegram** | | |
| `TELEGRAM_BOT_TOKEN` | 空 | Bot Token（多账号用 `;` 分隔） |
| `TELEGRAM_CHAT_ID` | 空 | Chat ID（数量须与 Token 一致） |
| **钉钉** | | |
| `DINGTALK_WEBHOOK_URL` | 空 | 钉钉机器人 Webhook URL |
| **企业微信** | | |
| `WEWORK_WEBHOOK_URL` | 空 | 企业微信机器人 Webhook URL |
| `WEWORK_MSG_TYPE` | 空 | `markdown` 或 `text` |
| **邮件** | | |
| `EMAIL_FROM` | 空 | 发件人邮箱 |
| `EMAIL_PASSWORD` | 空 | 邮箱密码/授权码 |
| `EMAIL_TO` | 空 | 收件人（多个逗号分隔） |
| `EMAIL_SMTP_SERVER` | 空 | SMTP 服务器（留空自动识别） |
| `EMAIL_SMTP_PORT` | 空 | SMTP 端口（留空自动识别） |
| **ntfy** | | |
| `NTFY_SERVER_URL` | `https://ntfy.sh` | ntfy 服务器地址 |
| `NTFY_TOPIC` | 空 | ntfy 主题名 |
| `NTFY_TOKEN` | 空 | 访问令牌（可选） |
| **Bark** | | |
| `BARK_URL` | 空 | Bark 推送 URL |
| **Slack** | | |
| `SLACK_WEBHOOK_URL` | 空 | Slack Incoming Webhook URL |
| **通用 Webhook** | | |
| `GENERIC_WEBHOOK_URL` | 空 | 通用 Webhook URL（Discord/Matrix/IFTTT 等） |
| `GENERIC_WEBHOOK_TEMPLATE` | 空 | JSON 模板，支持 `{title}` 和 `{content}` 占位符 |
| **AI 分析** | | |
| `AI_ANALYSIS_ENABLED` | 空 | `true` / `false` |
| `AI_API_KEY` | 空 | AI API Key（如 `sk-xxx`） |
| `AI_MODEL` | 空 | LiteLLM 格式模型名（如 `deepseek/deepseek-chat`） |
| `AI_API_BASE` | 空 | 自定义 API 端点（可选） |
| **远程存储（S3 兼容）** | | |
| `S3_ENDPOINT_URL` | 空 | S3 端点 URL |
| `S3_BUCKET_NAME` | 空 | 存储桶名 |
| `S3_ACCESS_KEY_ID` | 空 | Access Key |
| `S3_SECRET_ACCESS_KEY` | 空 | Secret Key |
| `S3_REGION` | 空 | 区域 |

</details>

### 功能配置（config.yaml）

`config/config.yaml` 控制具体的抓取行为、数据源、报告模式等，关键项：

| 配置路径 | 说明 |
|---------|------|
| `app.timezone` | 时区，默认 `Asia/Shanghai` |
| `schedule.preset` | 调度模板：`always_on` / `morning_evening` / `office_hours` / `night_owl` / `custom` |
| `platforms.sources` | 热榜平台列表（今日头条、微博、知乎等 11 个） |
| `rss.feeds` | RSS 订阅源列表 |
| `report.mode` | 报告模式：`daily` / `current` / `incremental` |
| `notification.enabled` | 通知总开关 |
| `ai_analysis.enabled` | AI 分析总开关 |

可视化配置编辑器: https://sansan0.github.io/TrendRadar/

---

## 三、构建与启动

提供两种方式，任选其一：

### 方式 A：拉取 DockerHub 镜像（推荐）

```bash
cd docker
docker compose pull
docker compose up -d trendradar
```

> **注意**：如遇到 DockerHub 匿名拉取限速（`429 Too Many Requests`），需先登录：
> ```bash
> docker login -u 你的用户名
> ```
> 或配置国内镜像加速（见 [常见问题](#q1-dockerhub-拉取限速-429-too-many-requests)）。

### 方式 B：本地源码构建

适用于无法拉取 DockerHub 镜像，或需要修改代码的场景。

构建过程中 Dockerfile 会从 GitHub 下载 supercronic，如果网络不通需要先配置代理或镜像加速（见 [常见问题 Q2](#q2-构建时下载-supercronic-超时)）。

```bash
cd docker
docker compose -f docker-compose-build.yml build trendradar
docker compose -f docker-compose-build.yml up -d trendradar
```

> ⚠️ **不要修改原始 Dockerfile**，构建网络问题应通过配置 Docker 代理或镜像加速器解决。

---

## 四、验证运行

### 4.1 查看容器状态

```bash
docker ps | grep trendradar
```

预期输出：
```
bffcb3c35e53   docker-trendradar   "/entrypoint.sh"   Up 53 seconds   127.0.0.1:5555->5555/tcp   trendradar
```

### 4.2 查看启动日志

```bash
docker logs -f trendradar
```

正常日志示例：
```
📅 生成的crontab内容: */30 * * * * cd /app && /usr/local/bin/python -m trendradar
▶️ 立即执行一次
配置文件加载成功: /app/config/config.yaml
TrendRadar v6.0.0 配置加载完成
监控平台数量: 11
获取 toutiao 成功（最新数据）
获取 baidu 成功（最新数据）
...
HTML报告已生成: output/html/2026-03-08/20-40.html
🌐 Web 服务器已启动 (端口: 8080)
⏰ 启动supercronic: */30 * * * *
```

### 4.3 查看抓取状态

```bash
docker exec -it trendradar python manage.py status
```

### 4.4 浏览器访问 Web 报告

```
http://localhost:5555
```

首页将展示最新一次抓取生成的 HTML 热榜报告。端口号取决于 `docker/.env` 中的 `WEBSERVER_PORT` 配置。

### 4.5 确认数据文件

```bash
ls output/news/        # 热榜 SQLite 数据库（按日期命名）
ls output/html/        # HTML 报告
ls output/rss/         # RSS 数据库
```

---

## 五、日常管理命令

| 操作 | 命令 |
|------|------|
| 查看日志 | `docker logs -f trendradar` |
| 查看状态 | `docker exec -it trendradar python manage.py status` |
| 停止服务 | `docker compose -f docker-compose-build.yml down` |
| 重启服务 | `docker compose -f docker-compose-build.yml restart trendradar` |
| 进入容器 | `docker exec -it trendradar bash` |
| 手动触发一次抓取 | `docker exec -it trendradar python -m trendradar` |
| 启动 Web 服务器 | `docker exec -it trendradar python manage.py start_webserver` |
| 停止 Web 服务器 | `docker exec -it trendradar python manage.py stop_webserver` |

> **注意**：如果使用的是方式 A（DockerHub 镜像），将上述命令中的 `-f docker-compose-build.yml` 去掉即可（默认使用 `docker-compose.yml`）。

---

## 六、通知渠道配置

在 `docker/.env` 中填入对应字段即可。**至少配置一个渠道才会发送推送**。

### 飞书

```dotenv
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

### Telegram

```dotenv
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```

### 钉钉

```dotenv
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
```

### 企业微信

```dotenv
WEWORK_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
WEWORK_MSG_TYPE=markdown
```

### 邮件

```dotenv
EMAIL_FROM=your@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=recipient1@example.com,recipient2@example.com
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

### 多账号

所有渠道支持多账号，用 `;` 分隔：

```dotenv
FEISHU_WEBHOOK_URL=https://hook1;https://hook2;https://hook3
```

配置修改后需重启容器生效：

```bash
cd docker
docker compose -f docker-compose-build.yml up -d trendradar
```

---

## 七、AI 分析功能

使用 AI 大模型对抓取的热点进行深度分析。基于 LiteLLM，支持 100+ AI 提供商。

### 启用步骤

1. 在 `docker/.env` 中配置：

```dotenv
AI_ANALYSIS_ENABLED=true
AI_API_KEY=sk-your-api-key-here
AI_MODEL=deepseek/deepseek-chat
# AI_API_BASE=                     # 自定义端点（可选）
```

2. 常用模型格式：

| 提供商 | `AI_MODEL` 值 |
|--------|--------------|
| DeepSeek | `deepseek/deepseek-chat` |
| OpenAI | `openai/gpt-4o` |
| Google Gemini | `gemini/gemini-2.5-flash` |
| Anthropic | `anthropic/claude-3-5-sonnet` |
| 本地 Ollama | `ollama/llama3` |

3. 重启容器：

```bash
cd docker
docker compose -f docker-compose-build.yml up -d trendradar
```

### 成本参考（DeepSeek 模型）

| 场景 | 约费用 |
|------|--------|
| 50 条新闻/次，每日 20 次推送 | ≈ ¥0.1/天 |
| 50 条新闻/次，每日 48 次推送 | ≈ ¥0.2/天 |

---

## 八、MCP 服务（可选）

MCP (Model Context Protocol) 服务提供 HTTP API，可对接 AI 客户端（如 Cherry Studio）进行交互式数据查询。

### 启动 MCP 服务

**方式 A（DockerHub 镜像）**：
```bash
cd docker
docker compose up -d trendradar-mcp
```

**方式 B（本地构建）**：
```bash
cd docker
docker compose -f docker-compose-build.yml build trendradar-mcp
docker compose -f docker-compose-build.yml up -d trendradar-mcp
```

MCP 服务端口：`http://localhost:3333`

---

## 九、目录结构说明

```
TrendRadar/
├── config/                         # 配置文件目录（挂载到容器，只读）
│   ├── config.yaml                 #   主配置文件
│   ├── timeline.yaml               #   调度时间线配置
│   ├── frequency_words.txt         #   监控关键词列表
│   ├── ai_analysis_prompt.txt      #   AI 分析提示词
│   └── ai_translation_prompt.txt   #   AI 翻译提示词
├── docker/                         # Docker 部署文件
│   ├── docker-compose.yml          #   拉取镜像方式
│   ├── docker-compose-build.yml    #   本地构建方式
│   ├── Dockerfile                  #   主服务镜像
│   ├── Dockerfile.mcp              #   MCP 服务镜像
│   ├── entrypoint.sh               #   容器入口脚本
│   ├── manage.py                   #   容器管理工具
│   └── .env                        #   环境变量（敏感信息写这里）
└── output/                         # 数据输出目录（挂载到容器，读写）
    ├── news/                       #   热榜 SQLite 数据库（按日期）
    │   └── 2026-03-08.db
    ├── rss/                        #   RSS SQLite 数据库（按日期）
    │   └── 2026-03-08.db
    ├── html/                       #   HTML 报告
    │   ├── 2026-03-08/
    │   │   └── 20-40.html
    │   └── latest/
    │       └── daily.html          #   最新报告（Web 首页链接到此）
    └── index.html                  #   Web 服务根页面
```

---

## 十、更新升级

### 方式 A（DockerHub 镜像）

```bash
cd docker
docker compose pull
docker compose up -d
```

### 方式 B（本地构建）

```bash
cd /path/to/TrendRadar
git pull origin master
cd docker
docker compose -f docker-compose-build.yml build trendradar
docker compose -f docker-compose-build.yml up -d trendradar
```

---

## 十一、常见问题排查

### Q1: DockerHub 拉取限速（429 Too Many Requests）

**原因**：DockerHub 对匿名用户有拉取频率限制。

**解决方案**（任选一）：

**方案 1**：登录 DockerHub（免费账号即可解除限制）
```bash
docker login -u 你的用户名
```

**方案 2**：配置国内镜像加速器
```bash
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerhub.icu",
    "https://docker.nju.edu.cn"
  ]
}
EOF
sudo systemctl restart docker
```

**方案 3**：改用本地构建（见 [方式 B](#方式-b本地源码构建)）

### Q2: 构建时下载 supercronic 超时

**原因**：Dockerfile 需要从 GitHub 下载 supercronic 二进制文件，国内直连可能很慢。

**解决方案**（不要修改 Dockerfile，配置 Docker 构建代理）：

```bash
# 方法 1：为 Docker 守护进程配置代理
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/proxy.conf <<'EOF'
[Service]
Environment="HTTP_PROXY=http://your-proxy:port"
Environment="HTTPS_PROXY=http://your-proxy:port"
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker

# 方法 2：使用 --build-arg 传递代理
docker compose -f docker-compose-build.yml build \
  --build-arg HTTP_PROXY=http://your-proxy:port \
  --build-arg HTTPS_PROXY=http://your-proxy:port \
  trendradar
```

如果没有代理，可以多次重试构建（Dockerfile 内置了 3 次重试机制），或改用 DockerHub 镜像方式（方式 A）。

### Q3: 容器启动后立即退出

检查日志：
```bash
docker logs trendradar
```

常见原因：
- `config/config.yaml` 不存在 → 确认 `config/` 目录挂载正确
- `config/frequency_words.txt` 不存在 → 检查项目是否完整克隆

### Q4: Web 页面无法访问（localhost:8080）

1. 确认 Web 服务已启用：`docker/.env` 中 `ENABLE_WEBSERVER=true`
2. 确认容器在运行：`docker ps | grep trendradar`
3. 确认端口映射：`docker port trendradar`
4. 确认首次抓取已完成（需等待日志出现 `HTML报告已生成`）

### Q5: AI 分析失败

日志报 `未配置 AI API Key`：
- 确认 `docker/.env` 中 `AI_API_KEY` 已填写
- 确认 `AI_ANALYSIS_ENABLED=true`
- 重启容器使配置生效

### Q6: 通知未收到

- 确认 `config/config.yaml` 中 `notification.enabled: true`
- 确认 `docker/.env` 中对应渠道的 Webhook/Token 已填写
- 查看日志中是否有 `未配置任何通知渠道` 的警告
- 重启容器使配置生效

### Q7: 如何修改抓取频率

编辑 `docker/.env`：

```dotenv
CRON_SCHEDULE=0 * * * *       # 每小时整点执行
CRON_SCHEDULE=*/15 * * * *    # 每 15 分钟执行
CRON_SCHEDULE=0 8,12,18 * * * # 每天 8 点、12 点、18 点执行
```

修改后重启容器：`docker compose -f docker-compose-build.yml up -d trendradar`

### Q8: 如何清理旧数据

```bash
# 删除 7 天前的数据库
find output/news/ -name "*.db" -mtime +7 -delete
find output/rss/ -name "*.db" -mtime +7 -delete

# 删除 7 天前的 HTML 报告
find output/html/ -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +
```

或在 `config/config.yaml` 中配置自动清理：
```yaml
storage:
  local:
    retention_days: 7    # 自动保留最近 7 天（0=永久保留）
```
