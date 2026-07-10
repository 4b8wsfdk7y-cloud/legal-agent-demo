#!/usr/bin/env python3
"""法务 Agent — 合同审核 Demo"""
from flask import Flask, request, jsonify, render_template_string
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# === CherryIN 配置 ===
CHERRYIN_API_KEY = os.environ.get("CHERRYIN_API_KEY", "")
CHERRYIN_BASE_URL = os.environ.get("CHERRYIN_BASE_URL", "https://express-ent-admin.cherryin.ai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "agent/deepseek-v4-pro")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "baai/bge-m3")

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
      <li>📄 <b>合同审核</b> — 上传 PDF → 识别类型 → 风险 Checklist → 飞书文档 <span class="tag tag-dev">D2-D4</span></li>
      <li>👤 <b>人事合同个性化</b> — 按岗位/职级给建议 <span class="tag tag-dev">D5</span></li>
      <li>📝 <b>ICP 外包需求文档</b> — 直发代理公司 <span class="tag tag-dev">D6</span></li>
    </ul>
  </div>
  <div class="card">
    <h2>🔧 系统状态</h2>
    <p>当前进度: <b>D1 脚手架</b> <span class="tag tag-done">运行中</span></p>
    <p>端口: 5003 | 服务器: 124.222.181.129</p>
    <a class="btn" href="/upload">前往审核</a>
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
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📄 上传合同</h1>
  </div>
  <div class="card">
    <h2>合同 PDF</h2>
    <div class="drop-zone" id="drop">点击或拖拽 PDF 文件到此处</div>
    <input type="file" id="file" accept=".pdf" style="display:none">
    <div class="info">
      支持: 采购合同 / 销售合同(toB/toC) / 人事合同<br>
      Agent 将自动识别类型,对照风险 Checklist 审核,生成飞书文档
    </div>
  </div>
  <div style="text-align:center">
    <button class="btn" id="submit" disabled>🔍 开始审核 (D4 实现)</button>
    <p style="margin-top:12px;color:#999"><a href="/">← 返回首页</a></p>
  </div>
</div>
<script>
const zone=document.getElementById('drop');
const file=document.getElementById('file');
const btn=document.getElementById('submit');
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
        "day": "D1",
        "port": 5003,
        "llm_model": LLM_MODEL,
        "embed_model": EMBED_MODEL,
    })

# === API (D2+ 实现) ===
@app.route("/api/classify", methods=["POST"])
def classify():
    """合同类型分类"""
    return jsonify({"ok": True, "message": "D3 实现"})

@app.route("/api/review", methods=["POST"])
def review():
    """合同审核"""
    return jsonify({"ok": True, "message": "D4 实现"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
