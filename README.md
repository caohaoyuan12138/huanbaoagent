# 化工环保 Agent

化工行业环保领域智能助手，集知识库、报告生成、设备监控、资讯采集、AI分析于一体。

## 功能模块

- **🏠 仪表盘** — 实时排放监控、异常预警、最新资讯
- **📚 知识库** — 环保法律法规、排放标准限值查询
- **📝 报告写作** — 自动生成巡查报告、超标分析报告、合规排查报告
- **📡 设备数据** — 接入监测设备，AI分析趋势，生成建议
- **📰 环保资讯** — 全网采集环保行业新闻、政策、标准动态
- **🤖 智能助手** — 自然语言交互，多步任务编排

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy + SQLite
- **前端**: Vue 3 + Element Plus + ECharts
- **AI**: LangChain / 大模型集成（可扩展）

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
python main.py
```

服务运行在 `http://localhost:8000`，API文档：`http://localhost:8000/docs`

### 3. 初始化数据

访问 API 或在前端点击"初始化数据"按钮：
- `/api/knowledge/seed` — 初始化标准库
- `/api/reports/seed` — 初始化报告模板
- `/api/devices/seed` — 初始化示例设备
- `/api/news/news/seed` — 初始化新闻数据

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 启动前端开发服务器

```bash
npm run dev
```

访问 `http://localhost:3000`

## 项目结构

```
agent/
├── backend/                    # 后端服务
│   ├── main.py                 # FastAPI 入口
│   ├── app/
│   │   ├── db/
│   │   │   ├── models.py       # 数据库模型
│   │   │   └── database.py     # 数据库连接
│   │   ├── routers/
│   │   │   ├── knowledge.py    # 知识库API
│   │   │   ├── reports.py      # 报告生成API
│   │   │   ├── devices.py      # 设备数据API
│   │   │   ├── news.py         # 新闻采集API
│   │   │   └── agent.py        # Agent智能API
│   │   └── models.py           # Pydantic模型
│   └── requirements.txt
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   ├── api/                # API封装
│   │   ├── router/             # 路由配置
│   │   └── styles/             # 全局样式
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 扩展开发

### 接入真实 IoT 数据

在 `devices` 路由中添加 MQTT 订阅器：

```python
import asyncio
import paho.mqtt.client as mqtt

async def start_mqtt_listener():
    client = mqtt.Client()
    client.on_message = on_message_received
    client.connect("mqtt-broker", 1883)
    client.subscribe("factory/#")
    client.loop_start()
```

### 集成大模型

在 `agent.py` 路由中集成 OpenAI/DeepSeek API：

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def call_llm(message, context):
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content
```

### 部署

使用 Docker Compose 一键部署：

```bash
docker-compose up -d
```

## License

MIT
