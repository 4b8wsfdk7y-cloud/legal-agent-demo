#!/usr/bin/env python3
"""法务合同模板 RAG 入库脚本 — 把 templates/ 下 4 份合同入库"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

CHERRYIN_API_KEY = os.environ.get("CHERRYIN_API_KEY", "")
CHERRYIN_BASE_URL = os.environ.get("CHERRYIN_BASE_URL", "https://express-ent-admin.cherryin.ai/v1")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "baai/bge-m3")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
AGENT_URL = "http://localhost:5003"  # 本地 Agent 的 /api/ingest 接口


def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def main():
    if not os.path.isdir(TEMPLATES_DIR):
        print(f"templates 目录不存在: {TEMPLATES_DIR}")
        sys.exit(1)
    files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".txt")]
    if not files:
        print("templates 目录下没有 .txt 文件")
        sys.exit(1)
    total_chunks = 0
    for filename in files:
        filepath = os.path.join(TEMPLATES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            print(f"跳过空文件: {filename}")
            continue
        doc_name = filename
        doc_type = filename.replace(".txt", "")
        chunks = chunk_text(content)
        print(f"[{doc_name}] {len(content)} 字 → {len(chunks)} chunks")
        # 调 Agent 的 /api/ingest 接口
        try:
            resp = requests.post(
                f"{AGENT_URL}/api/ingest",
                json={
                    "doc_type": doc_type,
                    "doc_name": doc_name,
                    "content": content,
                },
                timeout=120,
            )
            result = resp.json()
            if result.get("ok"):
                print(f"  ✅ doc_id={result['doc_id']}, chunks={result['chunk_count']}")
                total_chunks += result["chunk_count"]
            else:
                print(f"  ❌ 失败: {result.get('error', result)}")
        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
    print(f"\n=== 完成,共 {total_chunks} chunks 入库 ===")


if __name__ == "__main__":
    main()
