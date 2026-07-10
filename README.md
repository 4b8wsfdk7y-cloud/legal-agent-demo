# ⚖️ 法务审核助手

> 企业运营智能化项目 · 法务 Agent Demo
> 合同审核(分类 + 风险 Checklist + RAG 模板检索) + ICP 外包文档(开发中)

## 📌 项目简介

法务审核助手是 Cherry Studio 企业运营智能化项目的法务模块 Demo,面向企业法务/合同管理场景。上传合同 PDF/TXT 后,AI 自动分类合同类型,用 79 项风险 Checklist 逐条审核,RAG 检索标准模板条款作参考,输出结构化风险报告,最终一键发送到飞书群。

**核心能力:**
- 📄 合同分类(采购 / 销售-toB / 销售-toC / 人事,99% 准确率)
- 🔍 风险审核(4 类合同 79 项 Checklist 逐条检查)
- 📚 RAG 知识库(4 类国家标准合同模板入库,审核时自动检索参考条款)
- 📨 一键发送审核报告到飞书群(含风险等级 + 不合规项详情)

## 🏗 技术架构

| 层 | 技术栈 | 说明 |
|---|---|---|
| Web 框架 | Flask 3.0 | 单文件 app.py |
| LLM | CherryIN 网关 · agent/deepseek-v4-pro | OpenAI 兼容协议 |
| Embedding | CherryIN 网关 · baai/bge-m3 | RAG 向量检索(必须小写) |
| 数据存储 | SQLite (legal.db) | documents + chunks 表 |
| PDF 解析 | pypdf | 合同 PDF 文本提取 |
| OCR | pdf2image + pytesseract | 扫描 PDF 识别(预留) |
| 飞书集成 | lark-cli 子进程 | 复用已认证 profile |
| 部署 | Ubuntu 24.04 + Python venv | 124.222.181.129:5003 |

## 📂 目录结构

```
.
├── app.py                 # Flask 主应用(含所有路由 + 页面 HTML)
├── cherry_client.py       # CherryIN API 客户端(LLM + Embedding)
├── feishu_client.py       # 飞书客户端(lark-cli 子进程封装)
├── checklists.py          # 4 类合同风险 Checklist + 审核 Prompt 模板
├── ingest.py              # RAG 知识库入库脚本
├── templates/             # 4 类国家标准合同模板
│   ├── 采购合同.txt
│   ├── 销售合同-toB.txt
│   ├── 销售合同-toC.txt
│   └── 人事合同.txt
├── test_contract.txt      # 有缺陷的测试合同
├── requirements.txt
├── .env.example
└── .gitignore
```

## 🚀 快速开始

### 1. 环境准备

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入:
# - CHERRYIN_API_KEY: CherryIN 网关 API Key
# - LARK_APP_ID / LARK_APP_SECRET: 飞书 Bot 应用凭证
```

### 3. 知识库入库(首次运行)

```bash
python ingest.py
# 将 templates/*.txt 入库,生成向量索引
```

### 4. 启动

```bash
python app.py
# 访问 http://localhost:5003
```

## 📡 API 接口

| 方法 | 路径 | 功能 | 状态 |
|---|---|---|---|
| GET | `/` | 首页(项目介绍 + 入口) | ✅ |
| GET | `/upload` | 合同上传 + 审核页 | ✅ |
| GET | `/health` | 健康检查 | ✅ |
| GET | `/api/test-llm` | 测试 CherryIN 连通性 | ✅ |
| POST | `/api/classify` | 合同分类(文本输入) | ✅ |
| POST | `/api/classify-file` | 合同分类(文件上传) | ✅ |
| GET | `/api/documents` | 列出知识库文档 | ✅ |
| POST | `/api/ingest` | 入库新文档 | ✅ |
| POST | `/api/search` | RAG 向量检索 | ✅ |
| POST | `/api/review` | 合同审核(文本输入) | ✅ |
| POST | `/api/review/file` | 合同审核(文件上传) | ✅ |
| GET | `/api/feishu/chats` | 列出 Bot 所在飞书群聊 | ✅ |
| POST | `/api/review/feishu` | 发送审核报告到飞书群 | ✅ |
| POST | `/webhook` | 飞书事件订阅回调 | ⏳ |

## 🔍 审核流程

```
合同上传(PDF/TXT)
    │
    ▼
AI 分类(采购 / toB / toC / 人事)
    │
    ▼
选 Checklist(4 类合同各一套,共 79 项)
    │
    ▼
RAG 检索标准模板条款(向量相似度 Top 3)
    │
    ▼
LLM 逐条审核(对照 Checklist + 模板参考)
    │
    ▼
结构化输出
  ├─ 合同类型 + 置信度
  ├─ 总体风险等级(高 / 中 / 低)
  ├─ 统计(pass / warn / fail)
  └─ 逐条结果(状态 + 问题 + 修改建议)
    │
    ▼
发送到飞书群(富文本报告)
```

## 📋 风险 Checklist

合同模板来源: [国家市场监管总局合同示范文本库](https://htsfwb.samr.gov.cn/)

| 合同类型 | 检查项数 | 典型检查点 |
|---|---|---|
| 采购合同 | 18 项 | 主体信息、质量标准、验收期限、付款比例、违约责任 |
| 销售合同-toB | 23 项 | SaaS 服务范围、SLA 标准、数据归属、续费条款、终止条件 |
| 销售合同-toC | 17 项 | 消费者权益、退款政策、隐私保护、格式条款合规 |
| 人事合同 | 21 项 | 合同期限、试用期、薪酬结构、竞业限制、解除条件 |

**合计 79 项检查点**,每项审核结果:
- ✅ `pass` — 合规
- ⚠️ `warn` — 警告(条款存在但有瑕疵)
- ❌ `fail` — 不合规(缺失或违法)

总体风险等级判定:
- **高**: fail > 2 项
- **中**: fail > 0 或 warn > 3
- **低**: 其他

## 📊 测试数据

`test_contract.txt` 是一份故意有缺陷的采购合同,测试结果:
- 合同类型: 采购合同(99% 置信度)
- 总体风险: **高**
- 统计: 1 通过 / 8 警告 / 9 不合规
- 典型问题: 验收期限缺失、付款比例不合理(预付 50%)、违约责任不对等、保密条款缺失

## 🌐 部署信息

- **服务器**: 124.222.181.129 (Ubuntu 24.04)
- **端口**: 5003
- **目录**: /home/ubuntu/legal-agent/
- **启动**: `cd /home/ubuntu/legal-agent && nohup .venv/bin/python app.py > server.log 2>&1 &`
- **飞书 Bot**: 法务审核助手(App ID: cli_aada2fb250391ce9)

## 📝 更新日志

### 2026-07-10 (D4) — 飞书 Bot 集成
- ✅ 飞书 Bot 集成 `feishu_client.py` — 通过 lark-cli 子进程发消息
- ✅ 审核报告发送到飞书群 `/api/review/feishu` — 富文本格式,含风险等级 / 统计 / 不合规项详情
- ✅ 飞书群聊列表 `/api/feishu/chats`
- ✅ 审核页面增加「发送到飞书」区域 — 审核完成后一键发送报告到群聊
- ✅ 首页 D 标记更新 D3 → D4

### 2026-07-10 (D3) — 合同审核引擎
- ✅ 4 类合同风险 Checklist(采购 18 项 / toB 23 项 / toC 17 项 / 人事 21 项,共 79 项)
- ✅ 审核 Prompt 模板 `checklists.py`
- ✅ 合同审核 API `/api/review` + `/api/review/file`
- ✅ 审核流程: 分类 → 选 Checklist → RAG 检索模板 → 逐条审核
- ✅ 审核结论结构化: 风险等级(高 / 中 / 低) + 逐条状态(pass / warn / fail) + 修改建议
- ✅ 前端审核结果表格(✅ / ⚠️ / ❌ 三色 + 风险等级徽章)
- 🧪 测试: 有缺陷的采购合同 → 18 项中 9 项风险、8 项警告,总体风险「高」

### 2026-07-10 (D2) — 分类 + RAG 知识库
- ✅ CherryIN API 客户端 `cherry_client.py`(LLM + Embedding)
- ✅ 合同分类 API `/api/classify` + `/api/classify-file`
- ✅ 4 类合同模板入库(采购 / toB / toC / 人事,共 12 chunks)
- ✅ RAG 向量检索 `/api/search` + `/api/ingest` + `/api/documents`
- ✅ SQLite 知识库(documents + chunks 表)
- ✅ 合同模板样本 `templates/*.txt`(来源:国家市场监管总局)
- ✅ 飞书 webhook 接口 `/webhook`
- ✅ LLM 连通性测试 `/api/test-llm`
- 🧪 分类准确率 99%(SaaS 合同 → 销售合同-toB)

### 2026-07-10 (D1) — 脚手架
- ✅ Flask 脚手架搭建完成
- ✅ 首页 + 合同上传页 UI
- ✅ `/health` 健康检查接口
- ✅ 部署到 124.222.181.129:5003
- ✅ 合同模板来源定位(国家市场监管总局合同示范文本库)

## 🗓 路线图

| 阶段 | 日期 | 内容 | 状态 |
|---|---|---|---|
| D1 | 7/10 | Flask 脚手架 + 首页 UI | ✅ 完成 |
| D2 | 7/10 | CherryIN 客户端 + 合同分类 + RAG 知识库 | ✅ 完成 |
| D3 | 7/10 | 79 项风险 Checklist + 审核引擎 | ✅ 完成 |
| D4 | 7/10 | 飞书 Bot 集成 + 审核报告输出 | ✅ 完成 |
| D5 | 7/14 | 人事合同个性化 + Prompt 迭代 | ⏳ 开发中 |
| D6 | 7/15 | ICP 外包需求文档 + Demo 集成 | ⏳ 计划 |
| D7 | 7/16 | Demo 交付 + 录屏 | ⏳ 计划 |

## 👥 项目背景

基于 2026-07-09 树杨、鲍天一、俞昊晟线下拜访会议的企业运营智能化项目。

- **主导**: Patrick(Cherry Studio 实习生)
- **辅助**: Yu(数据提供)、Bao(测试)
- **交付**: 7 天 Demo(7/10-7/16)
- **约束**: 无法务专家,风险 Checklist 基于 AI + 国家标准模板

## 📄 License

Internal Demo — Cherry Studio
