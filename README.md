## 📝 更新日志

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
