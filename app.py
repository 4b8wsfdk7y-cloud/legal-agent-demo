#!/usr/bin/env python3
"""法务 Agent — 合同审核 Demo (D3)"""
from flask import Flask, request, jsonify, render_template_string
import os
import json
import sqlite3
import math
from dotenv import load_dotenv
from cherry_client import chat, chat_json, embed, test_connection
from checklists import CHECKLISTS, REVIEW_PROMPT

load_dotenv()

app = Flask(__name__)

# === 配置 ===
CHERRYIN_API_KEY = os.environ.get("CHERRYIN_API_KEY", "")
CHERRYIN_BASE_URL = os.environ.get("CHERRYIN_BASE_URL", "https://express-ent-admin.cherryin.ai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "agent/deepseek-v4-pro")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "baai/bge-m3")

DB_PATH = os.path.join(os.path.dirname(__file__), "legal.db")

# === 合同类型 ===
CONTRACT_TYPES = ["采购合同", "销售合同-toB", "销售合同-toC", "人事合同"]

# === 分类 Prompt ===
CLASSIFY_PROMPT = """分析以下合同文本,判断属于哪一类:

可选类型:
1. 采购合同(买方向供应商采购商品或服务)
2. 销售合同-toB(SaaS/企业软件销售,卖方为企业提供软件服务)
3. 销售合同-toC(向个人消费者销售商品或服务)
4. 人事合同(劳动合同/聘用协议)

合同文本(前 1500 字):
{text}

返回 JSON(不要其他文字):
{{
  "type": "采购合同|销售合同-toB|销售合同-toC|人事合同",
  "confidence": 0.0到1.0,
  "reason": "30字以内判断依据"
}}
"""

# === 数据库初始化 ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT,
        doc_name TEXT,
        content TEXT,
        chunk_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id INTEGER,
        chunk_index INTEGER,
        chunk_text TEXT,
        embedding TEXT,
        FOREIGN KEY (doc_id) REFERENCES documents(id)
    )""")
    conn.commit()
    conn.close()

init_db()

# === 页面 ===
INDEX_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>法务 Agent</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#f0f2f5;color:#333}
.container{max-width:900px;margin:0 auto;padding:20px}
.header{background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%);color:#fff;padding:40px;border-radius:12px;margin-bottom:24px}
.header h1{font-size:28px;margin-bottom:8px}
.header p{opacity:.9}
.card{background:#fff;padding:24px;border-radius:8px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.card h2{font-size:18px;margin-bottom:16px;color:#444}
.feature-list{list-style:none}
.feature-list li{padding:10px 0;border-bottom:1px solid #f0f0f0}
.feature-list li:last-child{border-bottom:none}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600}
.tag-dev{background:#fff7e6;color:#fa8c16}
.tag-done{background:#f6ffed;color:#52c41a}
a.btn{display:inline-block;padding:10px 24px;background:#11998e;color:#fff;text-decoration:none;border-radius:6px;margin-top:12px}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>⚖️ 法务 Agent</h1>
    <p>合同审核 + ICP 外包需求 | Demo</p>
  </div>
  <div class="card">
    <h2>📋 功能模块</h2>
    <ul class="feature-list">
      <li>📄 <b>合同分类</b> — 上传 PDF → AI 识别类型 <span class="tag tag-done">D2 已实现</span></li>
      <li>📚 <b>RAG 知识库</b> — 4 类合同模板入库,可检索 <span class="tag tag-done">D2 入库中</span></li>
      <li>🔍 <b>合同审核</b> — 风险 Checklist + 修改建议 <span class="tag tag-done">D3 已实现</span></li>
      <li>📝 <b>ICP 外包需求文档</b> <span class="tag tag-dev">D6</span></li>
    </ul>
  </div>
  <div class="card">
    <h2>🔧 系统状态</h2>
    <p>当前进度: <b>D3 审核 Prompt</b> <span class="tag tag-done">运行中</span></p>
    <p>端口: 5003 | 服务器: 124.222.181.129</p>
    <p><a class="btn" href="/upload">前往审核</a> <a class="btn" href="/api/test-llm" style="background:#52c41a">测试 LLM</a> <a class="btn" href="/api/documents" style="background:#722ed1">知识库</a></p>
  </div>
</div>
</body>
</html>"""

UPLOAD_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>合同审核 — 法务 Agent</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#f0f2f5;color:#333}
.container{max-width:900px;margin:0 auto;padding:20px}
.header{background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%);color:#fff;padding:30px;border-radius:12px;margin-bottom:24px}
.card{background:#fff;padding:24px;border-radius:8px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.card h2{font-size:18px;margin-bottom:16px;color:#444}
.drop-zone{border:2px dashed #d9d9d9;border-radius:8px;padding:40px;text-align:center;color:#999;cursor:pointer;transition:border-color .3s}
.drop-zone:hover{border-color:#11998e}
.drop-zone.has-file{border-color:#52c41a;color:#52c41a}
.btn{display:inline-block;padding:10px 32px;background:#11998e;color:#fff;border:none;border-radius:6px;font-size:14px;cursor:pointer;margin-top:16px}
.btn:disabled{background:#d9d9d9;cursor:not-allowed}
a{color:#11998e}
.info{background:#e6fffb;border:1px solid #87e8de;border-radius:4px;padding:12px;margin-top:12px;font-size:13px;color:#006d75}
#result{margin-top:16px}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📄 上传合同</h1>
  </div>
  <div class="card">
    <h2>合同 PDF / 文本</h2>
    <div class="drop-zone" id="drop">点击或拖拽 PDF 或 TXT 文件到此处</div>
    <input type="file" id="file" accept=".pdf,.txt" style="display:none">
    <div class="info">
      支持: 采购合同 / 销售合同(toB/toC) / 人事合同<br>
      D3: 上传后自动分类 + 审核风险 Checklist,D4 会加飞书文档输出
    </div>
    <button class="btn" id="submit" disabled>🔍 分类 + 审核</button>
    <div id="result"></div>
    <p style="margin-top:12px;color:#999"><a href="/">← 返回首页</a></p>
  </div>
</div>
<script>
const zone=document.getElementById('drop');
const file=document.getElementById('file');
const btn=document.getElementById('submit');
const result=document.getElementById('result');
zone.addEventListener('click',()=>file.click());
zone.addEventListener('dragover',e=>{e.preventDefault();zone.style.borderColor='#11998e'});
zone.addEventListener('dragleave',e=>{zone.style.borderColor='#d9d9d9'});
zone.addEventListener('drop',e=>{
  e.preventDefault();
  if(e.dataTransfer.files.length){file.files=e.dataTransfer.files;zone.textContent='✅ '+file.files[0].name;zone.classList.add('has-file');btn.disabled=false}
});
file.addEventListener('change',()=>{
  if(file.files.length){zone.textContent='✅ '+file.files[0].name;zone.classList.add('has-file');btn.disabled=false}
});
btn.addEventListener('click',async()=>{
  if(!file.files.length)return;
  result.textContent='分类 + 审核中(约 30-60 秒)...';
  const fd=new FormData();
  fd.append('file',file.files[0]);
  try{
    const r=await fetch('/api/review/file',{method:'POST',body:fd});
    const j=await r.json();
    if(j.ok){
      let html='<div style="margin:12px 0">';
      html+=`<p><b>类型:</b> ${j.contract_type} (置信度 ${(j.type_confidence*100).toFixed(0)}%)</p>`;
      html+=`<p><b>总体风险:</b> <span style="color:${j.overall_risk==='高'?'red':j.overall_risk==='中'?'orange':'green'};font-weight:bold">${j.overall_risk}</span></p>`;
      html+=`<p><b>统计:</b> ✅ ${j.stats.pass} 通过 / ⚠️ ${j.stats.warn} 警告 / ❌ ${j.stats.fail} 风险 / 共 ${j.stats.total} 项</p>`;
      html+='</div>';
      if(j.items && j.items.length){
        html+='<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr><th style="border:1px solid #ddd;padding:6px;text-align:left">状态</th><th style="border:1px solid #ddd;padding:6px;text-align:left">检查项</th><th style="border:1px solid #ddd;padding:6px;text-align:left">问题/建议</th></tr></thead><tbody>';
        j.items.forEach(it=>{
          const icon=it.status==='pass'?'✅':it.status==='warn'?'⚠️':'❌';
          const color=it.status==='pass'?'#52c41a':it.status==='warn'?'#fa8c16':'#f5222d';
          html+=`<tr><td style="border:1px solid #ddd;padding:6px;color:${color}">${icon}</td><td style="border:1px solid #ddd;padding:6px">${it.item||''}</td><td style="border:1px solid #ddd;padding:6px">${it.issue||''}${it.suggestion?'<br><b>建议:</b>'+it.suggestion:''}</td></tr>`;
        });
        html+='</tbody></table>';
      }
      result.innerHTML=html;
    }else{
      result.innerHTML='<pre style="color:red">'+JSON.stringify(j,null,2)+'</pre>';
    }
  }catch(e){result.textContent='错误: '+e.message}
});
</script>
</body>
</html>"""

# === 路由 ===
@app.route("/")
def index():
    return INDEX_HTML

@app.route("/upload")
def upload():
    return UPLOAD_HTML

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "legal-agent",
        "day": "D3",
        "port": 5003,
        "llm_model": LLM_MODEL,
        "embed_model": EMBED_MODEL,
    })

# === API ===
@app.route("/api/test-llm")
def test_llm():
    result = test_connection()
    return jsonify(result)

@app.route("/api/classify", methods=["POST"])
def classify():
    """合同类型分类(文本输入)"""
    data = request.json or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"ok": False, "error": "text is required"})
    snippet = text[:1500]
    prompt = CLASSIFY_PROMPT.format(text=snippet)
    result = chat_json([
        {"role": "system", "content": "你是合同分类助手。只返回 JSON。"},
        {"role": "user", "content": prompt},
    ], temperature=0.1)
    return jsonify({"ok": True, "result": result})

@app.route("/api/classify-file", methods=["POST"])
def classify_file():
    """合同类型分类(文件上传)"""
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "file is required"})
    filename = f.filename
    text = ""
    if filename.endswith(".txt"):
        text = f.read().decode("utf-8", errors="ignore")
    elif filename.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(f.read()))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return jsonify({"ok": False, "error": "pypdf not installed"})
    else:
        text = f.read().decode("utf-8", errors="ignore")
    if not text.strip():
        return jsonify({"ok": False, "error": "无法提取文本"})
    snippet = text[:1500]
    prompt = CLASSIFY_PROMPT.format(text=snippet)
    result = chat_json([
        {"role": "system", "content": "你是合同分类助手。只返回 JSON。"},
        {"role": "user", "content": prompt},
    ], temperature=0.1)
    return jsonify({"ok": True, "filename": filename, "text_length": len(text), "result": result})

# === RAG 知识库 ===
@app.route("/api/documents")
def documents():
    """列出已入库文档"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, doc_type, doc_name, chunk_count, created_at FROM documents ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return jsonify({"ok": True, "documents": [
        {"id": r[0], "doc_type": r[1], "doc_name": r[2], "chunk_count": r[3], "created_at": r[4]}
        for r in rows
    ]})

@app.route("/api/ingest", methods=["POST"])
def ingest():
    """文本入库(分块 + embedding)"""
    data = request.json or {}
    doc_type = data.get("doc_type", "")
    doc_name = data.get("doc_name", "")
    content = data.get("content", "")
    if not content:
        return jsonify({"ok": False, "error": "content is required"})
    chunk_size = 500
    overlap = 50
    chunks = []
    start = 0
    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]
        chunks.append(chunk)
        start = end - overlap
    # 入库
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO documents (doc_type, doc_name, content, chunk_count) VALUES (?, ?, ?, ?)",
              (doc_type, doc_name, content, len(chunks)))
    doc_id = c.lastrowid
    # embedding(批量,每批 10 个)
    for i in range(0, len(chunks), 10):
        batch = chunks[i:i+10]
        emb_result = embed(batch)
        if emb_result.get("error"):
            return jsonify({"ok": False, "error": emb_result["error"], "stage": "embedding"})
        for j, e in enumerate(emb_result["embeddings"]):
            c.execute("INSERT INTO chunks (doc_id, chunk_index, chunk_text, embedding) VALUES (?, ?, ?, ?)",
                      (doc_id, i+j, batch[j], json.dumps(e)))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "doc_id": doc_id, "chunk_count": len(chunks)})

@app.route("/api/search", methods=["POST"])
def search():
    """向量检索"""
    data = request.json or {}
    query = data.get("query", "")
    top_k = data.get("top_k", 3)
    if not query:
        return jsonify({"ok": False, "error": "query is required"})
    emb_result = embed(query)
    if emb_result.get("error"):
        return jsonify({"ok": False, "error": emb_result["error"]})
    query_vec = emb_result["embeddings"][0]
    import math
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, doc_id, chunk_index, chunk_text, embedding FROM chunks")
    scored = []
    for row in c.fetchall():
        emb = json.loads(row[4])
        # cosine similarity
        dot = sum(a*b for a, b in zip(query_vec, emb))
        norm_q = math.sqrt(sum(x*x for x in query_vec))
        norm_e = math.sqrt(sum(x*x for x in emb))
        if norm_q > 0 and norm_e > 0:
            sim = dot / (norm_q * norm_e)
        else:
            sim = 0
        scored.append((sim, row))
    scored.sort(key=lambda x: -x[0])
    conn.close()
    results = []
    for sim, row in scored[:top_k]:
        results.append({
            "score": round(sim, 4),
            "chunk_index": row[2],
            "chunk_text": row[3][:200] + "..." if len(row[3]) > 200 else row[3],
        })
    return jsonify({"ok": True, "query": query, "results": results})

def _do_review(text):
    """合同审核核心逻辑: 分类 → 选 Checklist → RAG → 逐条审核"""
    # 1. 分类
    snippet = text[:1500]
    classify_prompt = CLASSIFY_PROMPT.format(text=snippet)
    classify_result = chat_json([
        {"role": "system", "content": "你是合同分类助手。只返回 JSON。"},
        {"role": "user", "content": classify_prompt},
    ], temperature=0.1)

    contract_type = classify_result.get("type", "未知") if isinstance(classify_result, dict) else "未知"
    confidence = classify_result.get("confidence", 0) if isinstance(classify_result, dict) else 0

    # 2. 选 Checklist
    checklist_items = CHECKLISTS.get(contract_type, CHECKLISTS["采购合同"])
    checklist_text = "\n".join(f"{i+1}. {item}" for i, item in enumerate(checklist_items))

    # 3. RAG 检索模板条款
    rag_context = ""
    try:
        emb_result = embed(text[:500])
        if emb_result.get("embeddings"):
            query_vec = emb_result["embeddings"][0]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT chunk_text, embedding FROM chunks")
            scored = []
            for row in c.fetchall():
                emb = json.loads(row[1])
                dot = sum(a*b for a, b in zip(query_vec, emb))
                norm_q = math.sqrt(sum(x*x for x in query_vec))
                norm_e = math.sqrt(sum(x*x for x in emb))
                sim = dot / (norm_q * norm_e) if norm_q > 0 and norm_e > 0 else 0
                scored.append((sim, row[0]))
            conn.close()
            scored.sort(key=lambda x: -x[0])
            top_chunks = [s[1] for s in scored[:3]]
            rag_context = "\n---\n".join(top_chunks)
    except Exception as e:
        rag_context = f"(RAG 检索失败: {e})"

    # 4. 审核
    review_prompt = REVIEW_PROMPT.format(
        contract_type=contract_type,
        checklist=checklist_text,
        contract_text=text[:3000],
        rag_context=rag_context[:2000] or "(无)",
    )

    review_result = chat_json([
        {"role": "system", "content": "你是法务审核专员。逐条检查 Checklist,返回 JSON 数组。"},
        {"role": "user", "content": review_prompt},
    ], temperature=0.1)

    # 5. 统计
    items = review_result if isinstance(review_result, list) else []
    stats = {"pass": 0, "warn": 0, "fail": 0, "total": len(items)}
    for item in items:
        status = item.get("status", "warn")
        if status in stats:
            stats[status] += 1
    overall_risk = "高" if stats["fail"] > 2 else ("中" if stats["fail"] > 0 or stats["warn"] > 3 else "低")

    return {
        "ok": True,
        "contract_type": contract_type,
        "type_confidence": confidence,
        "overall_risk": overall_risk,
        "stats": stats,
        "items": items,
    }

@app.route("/api/review", methods=["POST"])
def review():
    """合同审核: 分类 → 选 Checklist → RAG 检索模板 → 逐条审核"""
    data = request.json or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"ok": False, "error": "text is required"})
    return jsonify(_do_review(text))

@app.route("/api/review/file", methods=["POST"])
def review_file():
    """合同审核(文件上传)"""
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "file is required"})
    filename = f.filename
    text = ""
    if filename.endswith(".txt"):
        text = f.read().decode("utf-8", errors="ignore")
    elif filename.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(f.read()))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return jsonify({"ok": False, "error": "pypdf not installed"})
    else:
        text = f.read().decode("utf-8", errors="ignore")
    if not text.strip():
        return jsonify({"ok": False, "error": "无法提取文本"})
    return jsonify(_do_review(text))


# === 飞书 webhook ===
@app.route("/webhook", methods=["POST"])
def webhook():
    """飞书事件订阅回调"""
    data = request.json or {}
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    event = data.get("event", {})
    msg = event.get("message", {})
    if msg:
        pass  # 后续实现
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
