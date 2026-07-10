# ⚖️ 法务审核助手 Bot

> 企业运营智能化项目 · 法务 Agent Demo
> 主导: Patrick | 协助: 俞昊昇(Yu) / 鲍天一(Bao)

## 📋 项目简介

基于 Flask + CherryIN(deepseek-v4-pro + bge-m3) 的法务智能 Agent,包含两大模块:

- **📄 合同审核** — 上传合同 PDF → AI 识别类型 → 风险 Checklist 审核 → 生成飞书文档
- **📝 ICP 外包需求文档** — 输出给代理公司的需求文档(不做 Agent)

## 🏗️ 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python Flask |
| LLM | CherryIN agent/deepseek-v4-pro |
| RAG Embedding | CherryIN baai/bge-m3 |
| 数据库 | SQLite |
| 飞书交互 | lark-cli + Bot |
| OCR | tesseract chi_sim+eng(扫描合同 PDF) |

## 🚀 部署信息

- **服务器**: 124.222.181.129
- **端口**: 5003
- **目录**: /home/ubuntu/legal-agent/
- **Demo 入口**: http://124.222.181.129:5003/
- **上传页**: http://124.222.181.129:5003/upload

## 📅 开发时间线(7 天)

| 天 | 日期 | 主线任务 | 状态 |
|---|---|---|---|
| D1 | 7/10 周四 | 合同模板收集 + 风险 Checklist 起草 + Flask 骨架 | ✅ 完成 |
| D2 | 7/11 周五 | Flask 骨架 + RAG 入库(模板 + 历史合同 OCR) | ⏳ |
| D3 | 7/12 周六 | 审核 Prompt v1(4 类合同各一份) + 合同类型分类器 | ⏳ |
| D4 | 7/13 周日 | 审核流程联调 + 飞书文档输出 | ⏳ |
| D5 | 7/14 周一 | 人事合同个性化(岗位/职级维度) + Prompt 迭代 | ⏳ |
| D6 | 7/15 周二 | ICP 外包需求文档 + 法务 Demo 联调 | ⏳ |
| D7 | 7/16 周三 | **Demo 交付** + 录屏 | ⏳ |

## ⚙️ 本地开发

```bash
# 1. 克隆
git clone https://github.com/4b8wsfdk7y-cloud/--bot_demo.git
cd --bot_demo

# 2. 虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际 API key

# 5. 启动
python app.py
```

## 📁 项目结构

```
.
├── app.py              # Flask 主程序
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
├── .gitignore
└── README.md
```

## 📚 合同模板来源

- **国家市场监管总局合同示范文本库**: https://htsfwb.samr.gov.cn/
- 4 类模板: 采购合同 / 销售合同 toB(SaaS) / 销售合同 toC / 人事合同

## ⚠️ 局限性说明

- **无专业法务专家校准**,审核能力基于 AI 通用知识 + 国家标准模板
- 风险 Checklist 是 AI + 通用知识生成的,可能有遗漏
- **Agent 输出仅作辅助,不替代律师,重大合同必须人工审核**
- 正式上线前必须找法务顾问 review 一批结果

## 📄 项目文档

- [飞书项目计划文档](https://acnwi1crgmwa.feishu.cn/docx/RdxwdfKWronVQXxNojxc8eT4njc)

## 📝 更新日志

### 2026-07-10 (D1)
- Flask 脚手架搭建完成
- 首页 + 合同上传页 UI
- /health 健康检查接口
- 部署到 124.222.181.129:5003
- 合同模板来源定位(国家市场监管总局)
