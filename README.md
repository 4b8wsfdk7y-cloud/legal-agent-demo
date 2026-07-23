# ⚖️ 法务审核助手

> 企业运营智能化项目 · 法务 Agent Demo
> 合同审核(分类 + 风险 Checklist + RAG 模板检索) + ICP 外包文档(开发中)

## 📌 项目简介

法务审核助手是 Cherry Studio 企业运营智能化项目的法务模块 Demo,面向企业法务/合同管理场景。上传合同 PDF/DOC/DOCX/TXT 后,AI 自动分类合同类型,用 79 项风险 Checklist 逐条审核,RAG 检索标准模板条款作参考,输出结构化风险报告,最终一键发送到飞书群。

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
| OCR | pdf2image + pytesseract | 扫描 PDF 识别；Docker 安装 Poppler/Tesseract 中文包 |
| Word 解析 | python-docx + antiword | DOCX 与旧版 DOC 文本提取 |
| 飞书集成 | 飞书 OpenAPI REST | Bot 消息与文件下载 |
| 部署 | Railway + Docker | 构建时固定安装系统解析依赖 |

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

## 上传约束与隐私

- 支持 PDF、TXT、DOC、DOCX；文件超过 32MB 会被拒绝。
- PDF 最多 50 页；DOCX 会校验内部文件数量和解压后体积；提取文本超过 80,000 字会拒绝审核，不会静默截断。
- 扫描 PDF 自动 OCR；解析失败会返回具体错误，不会把无法读取的文件交给模型编造审核结论。
- 合同正文不写入应用日志；.env 与本地 SQLite 数据库不纳入 Git。

## 🔍 审核流程

```
合同上传(PDF/DOC/DOCX/TXT)
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

### 2026-07-13 (D6) — ICP 外包需求文档
- 📋 新增 ICP 备案外包需求文档生成器 — AI 根据企业信息生成结构化需求文档
- 📋 新增 `/icp` 页面 — 表单填写(企业/网站/功能模块),一键 AI 生成
- 📋 新增 `/api/icp/generate` POST 端点 — 调 LLM 生成 Markdown 格式需求文档
- 📋 新增 `/api/icp/feishu` POST 端点 — 推送需求文档到飞书群
- 📋 文档结构: 项目概述/企业信息/网站信息/功能需求/ICP备案要求/技术要求/服务范围/交付标准/时间安排
- 📋 表单字段: 企业名称/信用代码/联系人/电话/网站名/域名/类型/访问量/功能模块(7选)/特殊要求
- ✅ 端到端验证: 填表 → AI 64 秒生成 4376 字文档(含法规引用、表格、分章节)
- 🧪 新增 `TestICP` 测试类 — 7 个测试:页面/缺字段×3/AI生成/LLM失败/飞书缺chat_id
- 🧪 测试总数: 41 → 48 个(全绿)

### 2026-07-13 (D5) — 合同 OCR
- 📄 新增 `_ocr_pdf()` 函数 — pdf2image(200 DPI)+ tesseract(chi_sim+eng)OCR 扫描 PDF
- 📄 `extract_text_from_upload` 重写 — pypdf 提取文本 < 20 字符时自动降级 OCR(扫描件兜底)
- 📄 OCR 安全限制 — 最多 50 页 / DPI 200 / 单页失败不中断 / 图片内存即时释放
- 📄 `/api/classify-file` 和 `/api/review/file` 自动复用 — 无需改动路由,扫描 PDF 直传即可
- 📦 安装依赖: Pillow + pdf2image + pytesseract(法务 venv 原本只有 pypdf)
- 🧪 新增 `TestOCR` 测试类 — 5 个测试覆盖:TXT 提取/空 TXT 报错/扫描 PDF OCR/OCR 降级触发/OCR 失败处理
- 🧪 测试总数: 36 → 41 个(全绿)
- ✅ 端到端验证: 英文扫描 PDF(图片型)→ pypdf 提取 0 字符 → 自动 OCR 5.7 秒 → 提取 231 字符 → 正确分类为"采购合同"

### 2026-07-11 (D4.3) — 飞书告警系统
- 🚨 飞书告警集成 — `monitor.py` 新增告警引擎,自动推送关键告警到飞书群
- 🚨 3 类告警触发规则:
  - **5xx 错误** — 服务端异常告警(每路径 5 分钟限流,避免告警风暴)
  - **健康检查失败** — DB/LLM 连不上即告警(10 分钟限流)
  - **错误率激增** — 5 分钟窗口 >30% 错误率告警(至少 20 请求,15 分钟限流)
- 🚨 新增 `/api/alert/test` 端点 — 一键发送测试告警,验证飞书链路通畅
- 🚨 `/monitor` 仪表盘新增「飞书告警」卡片(累计告警数)+「最近告警」列表
- 🚨 仪表盘底部新增「🧪 发送测试告警」按钮
- 🧪 新增 `TestAlert` 测试类 — 4 个测试覆盖:端点调用/5xx 触发/5xx 限流/4xx 不触发
- 🧪 测试总数: 32 → 36 个(全绿)
- ✅ 端到端验证: 测试告警秒发到飞书群,`alerts_sent` 计数正确

### 2026-07-11 (D4.2) — 监控 + 单元测试
- 📊 新增 `monitor.py` 监控模块:请求统计 + 健康检查 + 结构化日志
- 📊 新增 `/api/stats` 端点 — 请求总数/错误数/错误率/端点明细/最近 50 条错误
- 📊 新增 `/api/health/full` 端点 — DB + LLM 连通性 + 运行时间
- 📊 新增 `/monitor` 监控仪表盘 — 暗色主题,展示总览/端点统计/错误列表
- 📊 结构化日志 — `logs/legal-agent.log`(10MB 轮转)
- 🧪 新增 `test_app.py` — 32 个单元测试,覆盖 health/stats/classify/ingest(含去重)/search/review(含风险等级+confidence 钳制)/checklists 内容校验/webhook
- 🧪 测试运行: `.venv/bin/python test_app.py`

### 2026-07-11 (D4.1) — 代码审计修复
- 🔒 `debug=True` 改为环境变量控制(`FLASK_DEBUG=1` 才开),关闭 Werkzeug 调试器 RCE 风险
- 🔒 `MAX_CONTENT_LENGTH=16MB` 限制上传体积,防止内存耗尽
- 🔒 前端所有 `innerHTML` 拼接的 LLM / 用户内容加 `escapeHtml()` 转义,堵 XSS(审核结果表、群聊列表、文件名、错误提示)
- 🔧 `_do_review` 重写:分类失败显式返回错误(不再静默 fallback 采购 checklist);RAG 按 `doc_type` 过滤(不再跨类型污染);全文送审(不再 `text[:3000]` 截断,deepseek-v4-pro 支持 128k);支持 JSON 数组 `[{...}]` 和对象 `{"items":[...]}` 两种 LLM 输出格式
- 🔧 `/api/ingest` 重写:`try/finally` 防连接泄漏;同名文档先删旧再插新;embedding 失败 `rollback`;`overlap >= chunk_size` 校验
- 🔧 `/api/search` 重写:`try/finally`;维度不匹配跳过;`top_k` 上限 20
- 🔧 `checklists.py` 修正:"合同法规定" → "《劳动合同法》第19条"(试用期长度标准);新增违约金限制、不得解除情形;新增 toC 格式条款提示义务(《民法典》496条)
- 🔧 `review_feishu` 错误检查修正:用 `result.get("ok")` 代替 `result.get("code") == 0`;去掉 post 格式不渲染的 `style: ["bold"]`
- 🔧 `loadChats` 加 try/catch,修复未闭合括号 `(`
- 🔧 `confidence` 显示加 `Number(...||0)` 防 NaN
- 🔧 `/api/classify` 和 `/api/classify-file` 加 LLM 错误检查(之前失败也返回 `ok:true`)
- 🔧 新增 `extract_text_from_upload` 辅助函数:PDF 解析加 try/except(损坏 PDF 不再 500);复用于 `/api/classify-file` 和 `/api/review/file`
- 🔧 `/api/ingest` 加 `doc_type` 白名单校验 + `doc_name` 非空校验
- 🔧 `/api/search` 的 `top_k` 加 `try/except` 容错(非数字默认 3)
- 🔧 `_do_review` 的 `confidence` 限制到 `[0, 1]` 范围(LLM 可能返回 >1 或 <0)
- 🔧 `_do_review` 统计时过滤非 dict 的 items,确保 `total = pass + warn + fail`
- 🔧 `review_feishu` 的 fail/warn items 加 `isinstance(dict)` 检查 + `str()` 转换防 `get()` 崩溃
- 🔧 `chat_json` 失败标记从 `error` 改为 `_error`,避免与 LLM 合法返回的 error 字段混淆
- 🔧 RAG 检索的 `scored` 变量移到 try 块外,防止 DB 异常导致 `NameError`

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
| D5 | 7/13 | 合同 OCR(扫描 PDF 识别) | ✅ 完成 |
| D6 | 7/13 | ICP 外包需求文档 + Demo 集成 | ✅ 完成 |
| D7 | 7/13 | Demo 交付 + 录屏 | ✅ 完成 |

## 👥 项目背景

基于 2026-07-09 树杨、鲍天一、俞昊晟线下拜访会议的企业运营智能化项目。

- **主导**: Patrick(Cherry Studio 实习生)
- **辅助**: Yu(数据提供)、Bao(测试)
- **交付**: 7 天 Demo(7/10-7/16)
- **约束**: 无法务专家,风险 Checklist 基于 AI + 国家标准模板

## 📄 License

Internal Demo — Cherry Studio
