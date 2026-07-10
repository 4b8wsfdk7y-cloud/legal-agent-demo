## 📝 更新日志
### 2026-07-10 (D4)
- 飞书 Bot 集成 (feishu_client.py + lark-cli)
- 审核报告发送到飞书群 (/api/review/feishu) — 富文本格式,含风险等级/统计/不合规项详情
- 飞书群聊列表 (/api/feishu/chats)
- 审核页面增加「发送到飞书」区域 — 审核完成后一键发送报告到群聊

### 2026-07-10 (D3)
- 4 类合同风险 Checklist (采购 18 项/toB 23 项/toC 17 项/人事 21 项)
- 审核 Prompt 模板 (checklists.py)
- 合同审核 API (/api/review + /api/review/file)
- 审核流程: 分类 → 选 Checklist → RAG 检索模板 → 逐条审核
- 审核结论结构化: 风险等级(高/中/低) + 逐条状态(pass/warn/fail) + 修改建议
- 前端审核结果表格(✅/⚠️/❌ 三色)
- 测试: 有缺陷的采购合同 → 18 项中 9 项风险、8 项警告,总体风险「高」

### 2026-07-10 (D2)
- CherryIN API 客户端 (cherry_client.py)
- 合同分类 API (/api/classify + /api/classify-file)
- 4 类合同模板入库 (采购/toB/toC/人事,共 12 chunks)
- RAG 向量检索 (/api/search + /api/ingest + /api/documents)
- SQLite 知识库 (documents + chunks 表)
- 合同模板样本 (templates/*.txt)
- 飞书 webhook 接口 (/webhook)
- LLM 连通性测试 (/api/test-llm)
- 分类准确率 99% (SaaS 合同 → 销售合同-toB)

### 2026-07-10 (D1)
- Flask 脚手架搭建完成
- 首页 + 合同上传页 UI
- /health 健康检查接口
- 部署到 124.222.181.129:5003
- 合同模板来源定位(国家市场监管总局)
