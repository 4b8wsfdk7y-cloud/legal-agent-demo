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
<title>法务 Agent — 合同审核</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--primary:#11998e;--primary-dark:#38ef7d;--accent:#52c41a;--warn:#fa8c16;--danger:#f5222d;--bg:#f0f2f5;--card:#fff;--text:#1a1a2e;--text-light:#666;--border:#e8e8e8;--radius:16px;--shadow:0 4px 24px rgba(0,0,0,.06);--shadow-hover:0 8px 32px rgba(17,153,142,.15)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,"PingFang SC",sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.container{max-width:1000px;margin:0 auto;padding:24px}
.hero{background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%);color:#fff;padding:48px 40px;border-radius:var(--radius);margin-bottom:28px;position:relative;overflow:hidden;box-shadow:0 8px 32px rgba(17,153,142,.25)}
.hero::before{content:'';position:absolute;top:-50%;right:-20%;width:400px;height:400px;background:rgba(255,255,255,.08);border-radius:50%;animation:float 6s ease-in-out infinite}
.hero::after{content:'';position:absolute;bottom:-30%;left:-10%;width:300px;height:300px;background:rgba(255,255,255,.06);border-radius:50%;animation:float 8s ease-in-out infinite reverse}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-20px)}}
.hero-content{position:relative;z-index:1}
.hero h1{font-size:32px;font-weight:800;margin-bottom:8px;display:flex;align-items:center;gap:12px}
.hero .subtitle{font-size:16px;opacity:.9;font-weight:400}
.hero .badge{display:inline-block;background:rgba(255,255,255,.2);backdrop-filter:blur(10px);padding:6px 16px;border-radius:20px;font-size:13px;font-weight:500;margin-top:16px}
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px}
.stat-card{background:var(--card);padding:24px;border-radius:var(--radius);box-shadow:var(--shadow);transition:transform .3s,box-shadow .3s}
.stat-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-hover)}
.stat-card .stat-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:12px}
.stat-card .stat-label{font-size:13px;color:var(--text-light);font-weight:500}
.stat-card .stat-value{font-size:24px;font-weight:700;margin-top:4px}
.section-title{font-size:20px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.section-title::before{content:'';width:4px;height:24px;background:linear-gradient(135deg,var(--primary),var(--primary-dark));border-radius:2px}
.card{background:var(--card);padding:28px;border-radius:var(--radius);box-shadow:var(--shadow);margin-bottom:20px}
.feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.feature-item{padding:20px;border:2px solid var(--border);border-radius:12px;transition:all .3s;cursor:default}
.feature-item:hover{border-color:var(--primary);transform:translateY(-2px);box-shadow:var(--shadow-hover)}
.feature-item .feat-icon{font-size:32px;margin-bottom:8px}
.feature-item h3{font-size:16px;font-weight:600;margin-bottom:6px}
.feature-item p{font-size:13px;color:var(--text-light)}
.tag{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;margin-top:8px}
.tag-done{background:#f6ffed;color:var(--accent);border:1px solid #b7eb8f}
.tag-dev{background:#fff7e6;color:var(--warn);border:1px solid #ffd591}
.status-bar{display:flex;align-items:center;gap:12px;padding:12px 20px;background:linear-gradient(90deg,#f6ffed,#fff);border:1px solid #b7eb8f;border-radius:12px;margin-bottom:16px}
.status-dot{width:10px;height:10px;border-radius:50%;background:var(--accent);animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(82,196,26,.4)}70%{box-shadow:0 0 0 8px rgba(82,196,26,0)}100%{box-shadow:0 0 0 0 rgba(82,196,26,0)}}
.btn-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}
a.btn{display:inline-flex;align-items:center;gap:6px;padding:12px 28px;border-radius:12px;font-size:14px;font-weight:600;text-decoration:none;transition:all .3s}
.btn-primary{background:linear-gradient(135deg,var(--primary),var(--primary-dark));color:#fff;box-shadow:0 4px 16px rgba(17,153,142,.3)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 6px 24px rgba(17,153,142,.4)}
.btn-secondary{background:#fff;color:var(--primary);border:2px solid var(--primary)}
.btn-secondary:hover{background:var(--primary);color:#fff}
.btn-accent{background:linear-gradient(135deg,#52c41a,#389e0d);color:#fff;box-shadow:0 4px 16px rgba(82,196,26,.3)}
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <div class="hero-content">
      <h1>⚖️ 法务 Agent</h1>
      <p class="subtitle">合同审核 · 风险 Checklist · RAG 知识库</p>
      <span class="badge">🚀 D3 已上线 · 4 类合同 79 项检查点</span>
    </div>
  </div>

  <div class="status-bar">
    <div class="status-dot"></div>
    <span><b>系统运行中</b> · 端口 5003 · 服务器 124.222.181.129</span>
  </div>

  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-icon" style="background:#f6ffed">📋</div>
      <div class="stat-label">合同模板</div>
      <div class="stat-value">4 类</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background:#f0f5ff">🔍</div>
      <div class="stat-label">风险检查点</div>
      <div class="stat-value">79 项</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon" style="background:#fff7e6">📚</div>
      <div class="stat-label">知识库</div>
      <div class="stat-value">12 chunks</div>
    </div>
  </div>

  <h2 class="section-title">功能模块</h2>
  <div class="feature-grid">
    <div class="feature-item">
      <div class="feat-icon">📄</div>
      <h3>合同分类</h3>
      <p>上传 PDF → AI 自动识别类型(采购/toB/toC/人事)</p>
      <span class="tag tag-done">✅ D2 已实现</span>
    </div>
    <div class="feature-item">
      <div class="feat-icon">🔍</div>
      <h3>合同审核</h3>
      <p>风险 Checklist 逐条审核 + 修改建议 + 模板引用</p>
      <span class="tag tag-done">✅ D3 已实现</span>
    </div>
    <div class="feature-item">
      <div class="feat-icon">📚</div>
      <h3>RAG 知识库</h3>
      <p>4 类合同模板入库,审核时自动检索参考条款</p>
      <span class="tag tag-done">✅ D2 已实现</span>
    </div>
    <div class="feature-item">
      <div class="feat-icon">📝</div>
      <h3>ICP 外包文档</h3>
      <p>输出 ICP 备案外包需求文档,直发代理公司</p>
      <span class="tag tag-dev">⏳ D6 开发中</span>
    </div>
  </div>

  <div class="btn-row">
    <a class="btn btn-primary" href="/upload">📄 前往审核</a>
    <a class="btn btn-accent" href="/api/test-llm" target="_blank">⚡ 测试 LLM</a>
    <a class="btn btn-secondary" href="/api/documents" target="_blank">📚 知识库</a>
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--primary:#11998e;--primary-dark:#38ef7d;--accent:#52c41a;--warn:#fa8c16;--danger:#f5222d;--bg:#f0f2f5;--card:#fff;--text:#1a1a2e;--text-light:#666;--border:#e8e8e8;--radius:16px;--shadow:0 4px 24px rgba(0,0,0,.06)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,"PingFang SC",sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.container{max-width:900px;margin:0 auto;padding:24px}
.hero{background:linear-gradient(135deg,#11998e 0%,#38ef7d 100%);color:#fff;padding:32px;border-radius:var(--radius);margin-bottom:24px}
.hero h1{font-size:24px;font-weight:700;margin-bottom:4px}
.hero p{opacity:.9;font-size:14px}
.card{background:var(--card);padding:28px;border-radius:var(--radius);box-shadow:var(--shadow);margin-bottom:20px}
.card h2{font-size:18px;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.drop-zone{border:2px dashed var(--border);border-radius:12px;padding:48px;text-align:center;color:var(--text-light);cursor:pointer;transition:all .3s;background:#fafafa}
.drop-zone:hover{border-color:var(--primary);background:#f0fff9;transform:scale(1.01)}
.drop-zone.dragover{border-color:var(--primary);background:#f0fff9}
.drop-zone.has-file{border-color:var(--accent);background:#f6ffed;color:var(--accent)}
.drop-icon{font-size:48px;margin-bottom:8px}
.drop-text{font-size:16px;font-weight:600;margin-bottom:4px}
.drop-hint{font-size:13px;opacity:.7}
.info-box{background:linear-gradient(135deg,#e6fffb,#fff);border:1px solid #87e8de;border-radius:12px;padding:14px;margin-top:12px;font-size:13px;color:#006d75}
.btn{display:inline-flex;align-items:center;gap:6px;padding:14px 36px;background:linear-gradient(135deg,var(--primary),var(--primary-dark));color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:600;cursor:pointer;transition:all .3s;box-shadow:0 4px 16px rgba(17,153,142,.3)}
.btn:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 6px 24px rgba(17,153,142,.4)}
.btn:disabled{background:#d9d9d9;cursor:not-allowed;box-shadow:none}
a{color:var(--primary);text-decoration:none;font-weight:500}
a:hover{text-decoration:underline}
.result-box{margin-top:16px}
.result-summary{background:linear-gradient(135deg,#f6ffed,#fff);border:1px solid #b7eb8f;border-radius:12px;padding:16px;margin-bottom:12px}
.risk-badge{display:inline-block;padding:4px 14px;border-radius:16px;font-size:13px;font-weight:700}
.risk-high{background:#fff1f0;color:#f5222d;border:1px solid #ffa39e}
.risk-medium{background:#fff7e6;color:#fa8c16;border:1px solid #ffd591}
.risk-low{background:#f6ffed;color:#52c41a;border:1px solid #b7eb8f}
.stat-pills{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.stat-pill{padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600}
.pill-pass{background:#f6ffed;color:#52c41a}
.pill-warn{background:#fff7e6;color:#fa8c16}
.pill-fail{background:#fff1f0;color:#f5222d}
.result-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}
.result-table th{background:linear-gradient(135deg,var(--primary),var(--primary-dark));color:#fff;padding:10px;text-align:left;font-weight:600}
.result-table th:first-child{border-radius:8px 0 0 0}
.result-table th:last-child{border-radius:0 8px 0 0}
.result-table td{padding:10px;border-bottom:1px solid var(--border);vertical-align:top}
.result-table tr:hover{background:#f0fff9}
.status-icon{font-size:18px}
.suggestion{color:var(--text-light);font-size:12px;margin-top:4px}
.loading{display:inline-block;width:20px;height:20px;border:3px solid var(--border);border-top-color:var(--primary);border-radius:50%;animation:spin 1s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.back-link{display:inline-flex;align-items:center;gap:4px;color:var(--text-light);font-size:14px;margin-top:16px}
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <h1>📄 合同审核</h1>
    <p>上传合同 PDF/TXT → AI 分类 → 风险 Checklist 审核 → 结构化结论</p>
  </div>

  <div class="card">
    <h2>📤 上传合同</h2>
    <div class="drop-zone" id="drop">
      <div class="drop-icon">📁</div>
      <div class="drop-text">点击或拖拽文件到此处</div>
      <div class="drop-hint">支持 PDF 和 TXT 格式</div>
    </div>
    <input type="file" id="file" accept=".pdf,.txt" style="display:none">
    <div class="info-box">
      <b>📋 支持 4 类合同:</b> 采购合同 / 销售合同-toB(SaaS) / 销售合同-toC / 人事合同<br>
      <b>🔍 审核流程:</b> 分类 → 选 Checklist → RAG 检索模板 → 逐条审核 → 风险等级
    </div>
    <div style="text-align:center;margin-top:20px">
      <button class="btn" id="submit" disabled>🔍 分类 + 审核</button>
    </div>
    <div class="result-box" id="result"></div>
    <div style="text-align:center">
      <a href="/" class="back-link">← 返回首页</a>
    </div>
  </div>
</div>
<script>
const zone=document.getElementById('drop');
const file=document.getElementById('file');
const btn=document.getElementById('submit');
const result=document.getElementById('result');
zone.addEventListener('click',()=>file.click());
zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('dragover')});
zone.addEventListener('dragleave',e=>{zone.classList.remove('dragover')});
zone.addEventListener('drop',e=>{
  e.preventDefault();
  zone.classList.remove('dragover');
  if(e.dataTransfer.files.length){file.files=e.dataTransfer.files;showFile()}
});
file.addEventListener('change',showFile);
function showFile(){
  if(file.files.length){
    zone.innerHTML='<div class="drop-icon">✅</div><div class="drop-text">'+file.files[0].name+'</div><div class="drop-hint">点击重新选择</div>';
    zone.classList.add('has-file');
    btn.disabled=false;
  }
}
btn.addEventListener('click',async()=>{
  if(!file.files.length)return;
  result.innerHTML='<div style="text-align:center;padding:24px"><span class="loading"></span>分类 + 审核中(约 30-60 秒)...</div>';
  const fd=new FormData();
  fd.append('file',file.files[0]);
  try{
    const r=await fetch('/api/review/file',{method:'POST',body:fd});
    const j=await r.json();
    if(j.ok){
      const riskClass=j.overall_risk==='高'?'risk-high':j.overall_risk==='中'?'risk-medium':'risk-low';
      let html='<div class="result-summary">';
      html+='<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
      html+='<div><b>合同类型:</b> '+j.contract_type+' <span style="color:#999;font-size:12px">('+(j.type_confidence*100).toFixed(0)+'% 置信度)</span></div>';
      html+='<span class="risk-badge '+riskClass+'">风险等级: '+j.overall_risk+'</span>';
      html+='</div>';
      html+='<div class="stat-pills">';
      html+='<span class="stat-pill pill-pass">✅ '+j.stats.pass+' 通过</span>';
      html+='<span class="stat-pill pill-warn">⚠️ '+j.stats.warn+' 警告</span>';
      html+='<span class="stat-pill pill-fail">❌ '+j.stats.fail+' 风险</span>';
      html+='<span class="stat-pill" style="background:#f0f5ff;color:#667eea">共 '+j.stats.total+' 项</span>';
      html+='</div></div>';
      if(j.items&&j.items.length){
        html+='<table class="result-table"><thead><tr><th style="width:40px">状态</th><th>检查项</th><th>问题 / 建议</th></tr></thead><tbody>';
        j.items.forEach(it=>{
          const icon=it.status==='pass'?'✅':it.status==='warn'?'⚠️':'❌';
          const color=it.status==='pass'?'#52c41a':it.status==='warn'?'#fa8c16':'#f5222d';
          html+='<tr><td class="status-icon" style="color:'+color+'">'+icon+'</td><td>'+(it.item||'')+'</td><td>';
          if(it.issue)html+=it.issue;
          if(it.suggestion)html+='<div class="suggestion"><b>建议:</b>'+it.suggestion+'</div>';
          html+='</td></tr>';
        });
        html+='</tbody></table>';
      }
      result.innerHTML=html;
    }else{
      result.innerHTML='<div style="color:red;padding:16px;background:#fff0f0;border-radius:8px">❌ '+(j.error||JSON.stringify(j))+'</div>';
    }
  }catch(e){result.innerHTML='<div style="color:red">错误: '+e.message+'</div>'}
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
