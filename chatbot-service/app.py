"""Managed knowledge retrieval with optional, attributed AI paraphrasing."""
from flask import g

from shared.auth import require_auth
from shared.chatbot_llm import rewrite_answer
from shared.chatbot_resident import resident_reply
from shared.chatbot_retrieval import normalize, match_score, retrieve
from shared.db import get_db
from shared.domain import one, text
from shared.web import APIError, body, create_app as service_app, required, run


def source_metadata(matches):
    return [{key: item[key] for key in ("source", "source_id", "source_title", "confidence")}
            for item in matches]


def answer_response(answer, matches=(), *, engine="knowledge_base", **extra):
    top = matches[0] if matches else {}
    return {"answer": answer, "matched": bool(matches), "source": top.get("source"),
            "source_id": top.get("source_id"), "source_title": top.get("source_title"),
            "confidence": top.get("confidence", 0), "sources": source_metadata(matches),
            "engine": engine, **extra}


def create_app():
    app = service_app("chatbot")

    @app.post("/api/chatbot/ask")
    @require_auth("admin", "resident", "technician")
    def ask():
        data = body()
        required(data, "question")
        if set(data) - {"question"}:
            raise APIError("Chỉ gửi question; nguồn kiến thức và quyền truy cập do máy chủ xác định.")
        question = text(data["question"], "Câu hỏi", limit=1500)
        db = get_db()
        found = retrieve(question, [dict(row) for row in db.execute("SELECT * FROM faq_knowledge_base")],
                         [dict(row) for row in db.execute("SELECT * FROM locations")])
        if found["needs_clarification"] and not found["emergency"]:
            return answer_response(found["clarification"], needs_clarification=True)
        if not found["emergency"]:
            personal = resident_reply(question, g.user)
            if personal is not None:
                sources = [{"source": "billing", "source_id": "own-invoices",
                            "source_title": "Hóa đơn của tài khoản đang đăng nhập", "confidence": 1}]
                return answer_response(personal["answer"], sources if personal["verified"] else (),
                                       engine="resident_data" if personal["verified"] else "knowledge_base")
        selected = found["selected"][:3]
        if not selected:
            message = ("Mình chưa có hướng dẫn đã xác nhận cho sự cố này. Nếu đang có nguy hiểm, hãy liên hệ lực lượng ứng cứu hoặc bảo vệ ngay; đừng chờ phản hồi của chatbot."
                       if found["emergency"] else
                       "Mình chưa có thông tin chính xác về vấn đề này. Bạn có thể hỏi về gửi xe, thanh toán, nội quy hoặc vị trí tiện ích; với trường hợp riêng, vui lòng liên hệ Ban quản lý.")
            return answer_response(message, emergency=found["emergency"],
                                   suggestions=["Phí gửi xe bao nhiêu?", "Hotline Ban quản lý?", "Hiệu thuốc ở đâu?"])
        if not found["emergency"]:
            rewritten = rewrite_answer(question, found["matches"])
            if rewritten:
                cited = [item for item in found["matches"]
                         if f"{item['source']}:{item['source_id']}" in rewritten["source_ids"]]
                return answer_response(rewritten["answer"], cited, engine="llm")
        return answer_response("\n\n".join(item["answer"] for item in selected), selected,
                               emergency=found["emergency"])

    @app.get("/api/chatbot/faqs")
    @require_auth("admin", "resident", "technician")
    def faqs():
        return {"items": [dict(r) for r in get_db().execute("SELECT * FROM faq_knowledge_base ORDER BY category,faq_id")]}

    @app.get("/api/chatbot/locations")
    @require_auth("admin", "resident", "technician")
    def locations():
        return {"items": [dict(r) for r in get_db().execute("SELECT * FROM locations ORDER BY name")]}

    def faq_values(data, old=None):
        merged = dict(old or {})
        merged.update(data)
        required(merged, "question", "answer")
        return (text(merged.get("category"), "Danh mục", limit=150, optional=True), text(merged["question"], "Câu hỏi", limit=1500), text(merged["answer"], "Câu trả lời", limit=10000))

    @app.post("/api/chatbot/faqs")
    @require_auth("admin")
    def add_faq():
        values = faq_values(body())
        db = get_db()
        cursor = db.execute("INSERT INTO faq_knowledge_base(category,question,answer) VALUES (?,?,?)", values)
        db.commit()
        return one(db, "faq_knowledge_base", "faq_id", cursor.lastrowid), 201

    @app.patch("/api/chatbot/faqs/<int:faq_id>")
    @require_auth("admin")
    def update_faq(faq_id):
        db = get_db()
        values = faq_values(body(), one(db, "faq_knowledge_base", "faq_id", faq_id))
        db.execute("UPDATE faq_knowledge_base SET category=?,question=?,answer=? WHERE faq_id=?", (*values, faq_id))
        db.commit()
        return one(db, "faq_knowledge_base", "faq_id", faq_id)

    @app.delete("/api/chatbot/faqs/<int:faq_id>")
    @require_auth("admin")
    def delete_faq(faq_id):
        db = get_db()
        one(db, "faq_knowledge_base", "faq_id", faq_id)
        db.execute("DELETE FROM faq_knowledge_base WHERE faq_id=?", (faq_id,))
        db.commit()
        return {"deleted": True}

    def location_values(data, old=None):
        merged = dict(old or {})
        merged.update(data)
        required(merged, "name")
        return tuple(text(merged.get(key), key, limit=5000 if key == "description" else 200, optional=key != "name") for key in ("name", "block", "floor", "description"))

    @app.post("/api/chatbot/locations")
    @require_auth("admin")
    def add_location():
        values = location_values(body())
        db = get_db()
        cursor = db.execute("INSERT INTO locations(name,block,floor,description) VALUES (?,?,?,?)", values)
        db.commit()
        return one(db, "locations", "location_id", cursor.lastrowid), 201

    @app.patch("/api/chatbot/locations/<int:location_id>")
    @require_auth("admin")
    def update_location(location_id):
        db = get_db()
        values = location_values(body(), one(db, "locations", "location_id", location_id))
        db.execute("UPDATE locations SET name=?,block=?,floor=?,description=? WHERE location_id=?", (*values, location_id))
        db.commit()
        return one(db, "locations", "location_id", location_id)

    @app.delete("/api/chatbot/locations/<int:location_id>")
    @require_auth("admin")
    def delete_location(location_id):
        db = get_db()
        one(db, "locations", "location_id", location_id)
        db.execute("DELETE FROM locations WHERE location_id=?", (location_id,))
        db.commit()
        return {"deleted": True}

    return app


app = create_app()
if __name__ == "__main__":
    run(app, 5008)
