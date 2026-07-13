#!/usr/bin/env python3
"""法务 Agent 单元测试

运行:
    cd /home/ubuntu/legal-agent
    .venv/bin/python -m pytest test_app.py -v

或直接运行:
    .venv/bin/python test_app.py
"""
import os
import sys
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("CHERRYIN_API_KEY", "test-key")

sys.path.insert(0, os.path.dirname(__file__))

import app as legal_app


class LegalAppTestCase(unittest.TestCase):
    """Flask app 测试基类"""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        legal_app.DB_PATH = self.db_path
        legal_app.init_db()
        self.app = legal_app.app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _insert_mock_doc(self, doc_type="采购合同", doc_name="测试模板", content="测试内容"):
        """插入 mock 文档到 documents 表"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO documents (doc_type, doc_name, content, chunk_count) VALUES (?, ?, ?, ?)",
                  (doc_type, doc_name, content, 1))
        doc_id = c.lastrowid
        c.execute("INSERT INTO chunks (doc_id, chunk_index, chunk_text, embedding) VALUES (?, ?, ?, ?)",
                  (doc_id, 0, content, json.dumps([0.1] * 1024)))
        conn.commit()
        conn.close()
        return doc_id


class TestHealth(LegalAppTestCase):

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "legal-agent")
        self.assertEqual(data["port"], 5003)

    def test_health_full(self):
        r = self.client.get("/api/health/full")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("db", data)


class TestStats(LegalAppTestCase):

    def test_stats(self):
        r = self.client.get("/api/stats")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["ok"], True)
        self.assertIn("alerts_sent", data)

    def test_monitor_page(self):
        r = self.client.get("/monitor")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"legal-agent", r.data)
        self.assertIn("监控".encode(), r.data)


class TestAlert(LegalAppTestCase):
    """告警系统测试"""

    @patch("monitor._send_feishu_alert")
    def test_alert_test_endpoint(self, mock_send):
        mock_send.return_value = True
        r = self.client.post("/api/alert/test")
        data = r.get_json()
        self.assertTrue(data["ok"])
        mock_send.assert_called_once()

    @patch("monitor._send_feishu_alert")
    def test_5xx_triggers_alert(self, mock_send):
        """5xx 错误应触发飞书告警"""
        from monitor import _track_request
        mock_send.return_value = True
        _track_request("/fake-500", "GET", 500, 0.5, "127.0.0.1")
        mock_send.assert_called()

    @patch("monitor._send_feishu_alert")
    def test_5xx_throttled(self, mock_send):
        """同端点 5xx 5 分钟内只告警一次"""
        from monitor import _track_request
        mock_send.return_value = True
        _track_request("/fake-throttle", "GET", 500, 0.5, "127.0.0.1")
        _track_request("/fake-throttle", "GET", 500, 0.5, "127.0.0.1")
        _track_request("/fake-throttle", "GET", 500, 0.5, "127.0.0.1")
        self.assertEqual(mock_send.call_count, 1)

    @patch("monitor._send_feishu_alert")
    def test_4xx_no_alert(self, mock_send):
        """4xx 错误不触发飞书告警"""
        from monitor import _track_request
        mock_send.return_value = True
        _track_request("/fake-404", "GET", 404, 0.1, "127.0.0.1")
        mock_send.assert_not_called()


class TestClassify(LegalAppTestCase):

    def test_missing_text(self):
        r = self.client.post("/api/classify", json={})
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("text", data["error"])

    @patch("app.chat_json")
    def test_classify_success(self, mock_chat):
        mock_chat.return_value = {"type": "采购合同", "confidence": 0.95, "reason": "采购"}
        r = self.client.post("/api/classify", json={"text": "甲方向乙方采购服务器10台"})
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["result"]["type"], "采购合同")

    @patch("app.chat_json")
    def test_classify_llm_error(self, mock_chat):
        mock_chat.return_value = {"_error": "LLM down", "raw": ""}
        r = self.client.post("/api/classify", json={"text": "测试合同"})
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("LLM down", data["error"])


class TestIngest(LegalAppTestCase):

    def test_missing_doc_type(self):
        r = self.client.post("/api/ingest", json={"doc_name": "test", "content": "hello"})
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("doc_type", data["error"])

    def test_bad_doc_type(self):
        r = self.client.post("/api/ingest", json={"doc_type": "恶意", "doc_name": "test", "content": "hello"})
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("doc_type", data["error"])

    def test_missing_doc_name(self):
        r = self.client.post("/api/ingest", json={"doc_type": "采购合同", "content": "hello"})
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("doc_name", data["error"])

    def test_missing_content(self):
        r = self.client.post("/api/ingest", json={"doc_type": "采购合同", "doc_name": "test"})
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("content", data["error"])

    @patch("app.embed")
    def test_ingest_success(self, mock_embed):
        mock_embed.return_value = {"embeddings": [[0.1] * 1024], "raw": {}}
        r = self.client.post("/api/ingest", json={
            "doc_type": "采购合同", "doc_name": "测试模板", "content": "这是一段测试合同文本,用于测试入库功能。",
        })
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertGreater(data["chunk_count"], 0)

    @patch("app.embed")
    def test_ingest_dedup(self, mock_embed):
        """同名文档重复入库应先删旧再插新"""
        mock_embed.return_value = {"embeddings": [[0.1] * 1024], "raw": {}}
        # 第一次入库
        self.client.post("/api/ingest", json={
            "doc_type": "采购合同", "doc_name": "测试", "content": "第一次内容",
        })
        # 第二次入库(同名)
        self.client.post("/api/ingest", json={
            "doc_type": "采购合同", "doc_name": "测试", "content": "第二次内容",
        })
        # 应该只有 1 条文档
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM documents WHERE doc_name = '测试'")
        count = c.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)


class TestSearch(LegalAppTestCase):

    def test_missing_query(self):
        r = self.client.post("/api/search", json={})
        data = r.get_json()
        self.assertFalse(data["ok"])

    def test_bad_top_k(self):
        """top_k 非数字应容错为默认值"""
        self._insert_mock_doc()
        with patch("app.embed") as mock_embed:
            mock_embed.return_value = {"embeddings": [[0.1] * 1024], "raw": {}}
            r = self.client.post("/api/search", json={"query": "test", "top_k": "abc"})
            data = r.get_json()
            self.assertTrue(data["ok"])

    @patch("app.embed")
    def test_search_success(self, mock_embed):
        self._insert_mock_doc(content="验收期7个工作日")
        mock_embed.return_value = {"embeddings": [[0.1] * 1024], "raw": {}}
        r = self.client.post("/api/search", json={"query": "验收"})
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertGreater(len(data["results"]), 0)


class TestReview(LegalAppTestCase):

    def test_missing_text(self):
        r = self.client.post("/api/review", json={})
        data = r.get_json()
        self.assertFalse(data["ok"])

    @patch("app.chat_json")
    def test_review_classify_fail(self, mock_chat):
        """分类失败应显式返回错误,不静默 fallback"""
        mock_chat.return_value = {"_error": "LLM down", "raw": ""}
        r = self.client.post("/api/review", json={"text": "测试合同"})
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("分类失败", data["error"])

    @patch("app.chat_json")
    @patch("app.embed")
    def test_review_success(self, mock_embed, mock_chat):
        mock_embed.return_value = {"embeddings": [[0.1] * 1024], "raw": {}}
        # 第一次调 chat_json 是分类,第二次是审核
        mock_chat.side_effect = [
            {"type": "采购合同", "confidence": 0.95, "reason": "采购"},
            [
                {"item": "合同主体", "status": "pass", "suggestion": ""},
                {"item": "质量标准", "status": "warn", "issue": "未明确", "suggestion": "补充"},
                {"item": "违约责任", "status": "fail", "issue": "缺失", "suggestion": "添加"},
            ],
        ]
        r = self.client.post("/api/review", json={"text": "甲方向乙方采购服务器10台,总价50万元"})
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["contract_type"], "采购合同")
        self.assertEqual(data["stats"]["total"], 3)
        self.assertEqual(data["stats"]["pass"], 1)
        self.assertEqual(data["stats"]["warn"], 1)
        self.assertEqual(data["stats"]["fail"], 1)
        # fail=1 -> "中"(fail>2 才是"高")
        self.assertEqual(data["overall_risk"], "中")

    @patch("app.chat_json")
    @patch("app.embed")
    def test_review_high_risk(self, mock_embed, mock_chat):
        """3 个 fail 应判定为高风险"""
        mock_embed.return_value = {"embeddings": [[0.1] * 1024], "raw": {}}
        mock_chat.side_effect = [
            {"type": "采购合同", "confidence": 0.9, "reason": "test"},
            [
                {"item": "检查1", "status": "fail", "issue": "缺失", "suggestion": "补"},
                {"item": "检查2", "status": "fail", "issue": "缺失", "suggestion": "补"},
                {"item": "检查3", "status": "fail", "issue": "缺失", "suggestion": "补"},
                {"item": "检查4", "status": "pass", "suggestion": ""},
            ],
        ]
        r = self.client.post("/api/review", json={"text": "测试合同"})
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["stats"]["fail"], 3)
        self.assertEqual(data["overall_risk"], "高")

    @patch("app.chat_json")
    @patch("app.embed")
    def test_review_confidence_clamped(self, mock_embed, mock_chat):
        """confidence >1 应被限制到 1"""
        mock_embed.return_value = {"embeddings": [[0.1] * 1024], "raw": {}}
        mock_chat.side_effect = [
            {"type": "采购合同", "confidence": 1.5, "reason": "test"},  # 越界值
            [],
        ]
        r = self.client.post("/api/review", json={"text": "采购合同测试"})
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["type_confidence"], 1.0)  # 被限制


class TestPages(LegalAppTestCase):

    def test_index(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Agent", r.data)

    def test_upload_page(self):
        r = self.client.get("/upload")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"escapeHtml", r.data)


class TestOCR(LegalAppTestCase):
    """D5: OCR 功能测试"""

    def _make_scanned_pdf(self, path):
        """用 PIL 生成一个图片型 PDF(扫描件)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.skipTest("Pillow not installed")
        img = Image.new("RGB", (800, 400), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((50, 50), "Purchase Contract", fill="black", font=font)
        draw.text((50, 100), "Party A buys 10 servers from Party B", fill="black", font=font)
        draw.text((50, 150), "Total price 500000 CNY", fill="black", font=font)
        draw.text((50, 200), "Delivery in 30 working days", fill="black", font=font)
        img.save(path, "PDF", resolution=200)

    def test_txt_extract(self):
        """TXT 文件提取文本"""
        import io
        text = legal_app.extract_text_from_upload(
            io.BytesIO(b"hello world"), "test.txt")
        self.assertEqual(text, "hello world")

    def test_empty_txt(self):
        """空 TXT 应返回错误"""
        import io
        result = legal_app.extract_text_from_upload(
            io.BytesIO(b"   "), "empty.txt")
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])

    def test_scanned_pdf_ocr(self):
        """扫描 PDF 应自动触发 OCR 提取文本"""
        import io
        import tempfile
        _, pdf_path = tempfile.mkstemp(suffix=".pdf")
        try:
            self._make_scanned_pdf(pdf_path)
            with open(pdf_path, "rb") as f:
                result = legal_app.extract_text_from_upload(f, "scanned.pdf")
            # OCR 可能因环境差异略有不同,关键是提取到了文本
            self.assertIsInstance(result, str, f"OCR 应返回文本,但返回: {result}")
            self.assertGreater(len(result.strip()), 10, "OCR 文本过短")
        finally:
            os.unlink(pdf_path)

    @patch("app._ocr_pdf")
    def test_ocr_fallback_on_empty_text(self, mock_ocr):
        """pypdf 提取空文本时应降级到 OCR"""
        import io
        mock_ocr.return_value = ("OCR extracted text", None)
        # 创建一个 pypdf 能读但提取为空文本的 PDF 很难,
        # 直接 mock _ocr_pdf 验证调用逻辑
        # 用一个极简的"空"PDF
        from pypdf import PdfWriter
        buf = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(buf)
        buf.seek(0)
        result = legal_app.extract_text_from_upload(buf, "blank.pdf")
        mock_ocr.assert_called()
        self.assertEqual(result, "OCR extracted text")

    @patch("app._ocr_pdf")
    def test_ocr_error_handled(self, mock_ocr):
        """OCR 失败应返回错误,不崩溃"""
        import io
        mock_ocr.return_value = (None, "tesseract not found")
        from pypdf import PdfWriter
        buf = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(buf)
        buf.seek(0)
        result = legal_app.extract_text_from_upload(buf, "blank.pdf")
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])
        self.assertIn("OCR", result["error"])


class TestChecklists(unittest.TestCase):
    """checklists.py 内容校验"""

    def test_all_types_present(self):
        from checklists import CHECKLISTS
        self.assertIn("采购合同", CHECKLISTS)
        self.assertIn("销售合同-toB", CHECKLISTS)
        self.assertIn("销售合同-toC", CHECKLISTS)
        self.assertIn("人事合同", CHECKLISTS)

    def test_checklist_items_nonempty(self):
        from checklists import CHECKLISTS
        for ctype, items in CHECKLISTS.items():
            self.assertGreater(len(items), 10, f"{ctype} checklist 太短")
            for item in items:
                self.assertIsInstance(item, str)
                self.assertGreater(len(item), 5, f"{ctype} 某项太短: {item}")

    def test_no_contract_law_typo(self):
        """不应再出现'合同法规定'(应改为'劳动合同法')"""
        from checklists import CHECKLISTS
        all_text = " ".join(CHECKLISTS["人事合同"])
        self.assertNotIn("合同法规定", all_text, "人事合同 checklist 仍有'合同法规定'笔误")

    def test_labor_law_cited(self):
        """人事合同应引用《劳动合同法》"""
        from checklists import CHECKLISTS
        all_text = " ".join(CHECKLISTS["人事合同"])
        self.assertIn("劳动合同法", all_text)

    def test_toC_format_clause(self):
        """toC 合同应有格式条款提示义务"""
        from checklists import CHECKLISTS
        all_text = " ".join(CHECKLISTS["销售合同-toC"])
        self.assertIn("格式条款", all_text)

    def test_review_prompt_template(self):
        from checklists import REVIEW_PROMPT
        self.assertIn("{contract_type}", REVIEW_PROMPT)
        self.assertIn("{checklist}", REVIEW_PROMPT)
        self.assertIn("{contract_text}", REVIEW_PROMPT)


class TestDocuments(LegalAppTestCase):

    def test_empty_docs(self):
        r = self.client.get("/api/documents")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["documents"]), 0)

    def test_with_doc(self):
        self._insert_mock_doc(doc_name="测试合同")
        r = self.client.get("/api/documents")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["documents"]), 1)
        self.assertEqual(data["documents"][0]["doc_name"], "测试合同")


class TestWebhook(LegalAppTestCase):

    def test_challenge(self):
        r = self.client.post("/webhook", json={"challenge": "abc123"})
        data = r.get_json()
        self.assertEqual(data["challenge"], "abc123")


class TestICP(LegalAppTestCase):
    """D6: ICP 外包需求文档测试"""

    def test_icp_page(self):
        """ICP 页面应返回 200"""
        r = self.client.get("/icp")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ICP".encode(), r.data)

    def test_missing_company_name(self):
        """缺少企业名称应报错"""
        r = self.client.post("/api/icp/generate", json={
            "site_name": "测试", "domain": "test.com",
        })
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("company_name", data["error"])

    def test_missing_domain(self):
        """缺少域名应报错"""
        r = self.client.post("/api/icp/generate", json={
            "company_name": "测试公司", "site_name": "测试",
        })
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("domain", data["error"])

    def test_missing_site_name(self):
        """缺少网站名称应报错"""
        r = self.client.post("/api/icp/generate", json={
            "company_name": "测试公司", "domain": "test.com",
        })
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("site_name", data["error"])

    @patch("app.chat")
    def test_icp_generate_success(self, mock_chat):
        """AI 生成 ICP 文档"""
        mock_chat.return_value = {"content": "# ICP 备案外包需求文档\n## 一、项目概述\n测试内容...", "raw": {}}
        r = self.client.post("/api/icp/generate", json={
            "company_name": "北京测试科技有限公司",
            "site_name": "测试官网",
            "domain": "test.com",
            "site_type": "企业官网",
            "features": ["信息发布", "用户注册"],
        })
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("ICP", data["document"])

    @patch("app.chat")
    def test_icp_generate_llm_error(self, mock_chat):
        """LLM 失败应返回错误"""
        mock_chat.return_value = {"content": "", "error": "LLM timeout", "raw": {}}
        r = self.client.post("/api/icp/generate", json={
            "company_name": "测试公司", "site_name": "测试", "domain": "test.com",
        })
        data = r.get_json()
        self.assertFalse(data["ok"])

    def test_icp_feishu_no_chat_id(self):
        """推飞书缺 chat_id 应报错"""
        r = self.client.post("/api/icp/feishu", json={
            "form_data": {"company_name": "测试", "site_name": "测试", "domain": "t.com"},
        })
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("chat_id", data["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
