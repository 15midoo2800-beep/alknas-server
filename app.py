import sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Alknas License Server")

DB_FILE = "licenses.db"

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            device_id TEXT UNIQUE NOT NULL,
            expiry_date TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# نموذج الفحص للـ API
class CheckRequest(BaseModel):
    device_id: str

# ----------------- واجهة الويب (لوحة التحكم) -----------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة إدارة تراخيص القناص</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Cairo', sans-serif; margin: 0; padding: 0; }
        body { background: #0b0f19; color: #f3f4f6; padding: 20px; }
        .container { max-width: 900px; margin: auto; }
        .header { text-align: center; margin-bottom: 25px; }
        .header h1 { color: #10b981; font-size: 26px; }
        .header p { color: #9ca3af; font-size: 14px; }
        .card { background: #131c2e; padding: 20px; border-radius: 12px; border: 1px solid #1f293d; margin-bottom: 25px; }
        .card h2 { font-size: 18px; margin-bottom: 15px; color: #38bdf8; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #cbd5e1; }
        .form-group input, .form-group select {
            width: 100%; padding: 10px; background: #0b0f19; border: 1px solid #334155;
            border-radius: 8px; color: white; font-size: 14px; outline: none;
        }
        .form-group input:focus { border-color: #10b981; }
        button.btn-add {
            background: #10b981; color: white; border: none; padding: 12px; border-radius: 8px;
            font-weight: 700; cursor: pointer; width: 100%; margin-top: 15px; font-size: 15px;
        }
        button.btn-add:hover { background: #059669; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px 10px; text-align: center; font-size: 13px; border-bottom: 1px solid #1f293d; }
        th { background: #0f172a; color: #94a3b8; }
        .badge { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }
        .badge-active { background: #064e3b; color: #34d399; }
        .badge-inactive { background: #450a0a; color: #f87171; }
        .badge-expired { background: #451a03; color: #fb923c; }
        .actions { display: flex; gap: 6px; justify-content: center; }
        .btn-action { padding: 5px 8px; border-radius: 6px; border: none; font-size: 12px; cursor: pointer; color: white; }
        .btn-toggle { background: #f59e0b; }
        .btn-delete { background: #ef4444; }
        .btn-extend { background: #3b82f6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ لوحة إدارة تراخيص القناص</h1>
            <p>إنشاء ومتابعة حسابات المشتركين وتحديد مدة الصلاحية</p>
        </div>

        <div class="card">
            <h2>➕ إضافة / تفعيل مشترك جديد</h2>
            <form action="/add" method="post">
                <div class="form-grid">
                    <div class="form-group">
                        <label>اسم العميل:</label>
                        <input type="text" name="client_name" required placeholder="مثال: أحمد محمد">
                    </div>
                    <div class="form-group">
                        <label>كود الجهاز (Device ID):</label>
                        <input type="text" name="device_id" required placeholder="مثال: 5464152599">
                    </div>
                    <div class="form-group">
                        <label>مدة الاشتراك:</label>
                        <select name="days">
                            <option value="7">7 أيام (تجريبي)</option>
                            <option value="30" selected>شهر (30 يوم)</option>
                            <option value="90">3 شهور (90 يوم)</option>
                            <option value="180">6 شهور (180 يوم)</option>
                            <option value="365">سنة كاملة (365 يوم)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn-add">إنشاء وتفعيل الحساب 🚀</button>
            </form>
        </div>

        <div class="card">
            <h2>📋 قائمة المشتركين</h2>
            <table>
                <thead>
                    <tr>
                        <th>العميل</th>
                        <th>كود الجهاز</th>
                        <th>ينتهي في</th>
                        <th>الحالة</th>
                        <th>إجراءات</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in licenses %}
                    <tr>
                        <td><strong>{{ item.client_name }}</strong></td>
                        <td style="font-family: monospace; color: #38bdf8;">{{ item.device_id }}</td>
                        <td>{{ item.expiry_date }}</td>
                        <td>
                            {% if not item.is_active %}
                                <span class="badge badge-inactive">معطل</span>
                            {% elif item.is_expired %}
                                <span class="badge badge-expired">منتهي</span>
                            {% else %}
                                <span class="badge badge-active">نشط</span>
                            {% endif %}
                        </td>
                        <td class="actions">
                            <form action="/toggle/{{ item.id }}" method="post" style="display:inline;">
                                <button class="btn-action btn-toggle">{% if item.is_active %}إيقاف{% else %}تنشيط{% endif %}</button>
                            </form>
                            <form action="/extend/{{ item.id }}" method="post" style="display:inline;">
                                <button class="btn-action btn-extend">+30 يوم</button>
                            </form>
                            <form action="/delete/{{ item.id }}" method="post" style="display:inline;" onsubmit="return confirm('هل أنت متأكد من الحذف؟');">
                                <button class="btn-action btn-delete">حذف</button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5" style="color: #64748b; padding: 20px;">لا يوجد مشتركون مسجلون حالياً</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, client_name, device_id, expiry_date, is_active FROM licenses ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    today = datetime.now().date()
    licenses = []
    for r in rows:
        exp_date = datetime.strptime(r[3], "%Y-%m-%d").date()
        licenses.append({
            "id": r[0],
            "client_name": r[1],
            "device_id": r[2],
            "expiry_date": r[3],
            "is_active": bool(r[4]),
            "is_expired": today > exp_date
        })

    # استبدال قوالب Jinja البسيطة داخل المتصفح
    from jinja2 import Template
    t = Template(HTML_TEMPLATE)
    return t.render(licenses=licenses)

@app.post("/add")
def add_license(client_name: str = Form(...), device_id: str = Form(...), days: int = Form(...)):
    expiry_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # تحديث الحساب إن كان مسجلاً سابقاً أو إنشاء حساب جديد
    c.execute('''
        INSERT INTO licenses (client_name, device_id, expiry_date, is_active, created_at)
        VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            client_name=excluded.client_name,
            expiry_date=excluded.expiry_date,
            is_active=1
    ''', (client_name.strip(), device_id.strip().upper(), expiry_date, now_str))
    conn.commit()
    conn.close()
    return HTMLResponse('<script>window.location.href="/";</script>')

@app.post("/toggle/{item_id}")
def toggle_license(item_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE licenses SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return HTMLResponse('<script>window.location.href="/";</script>')

@app.post("/extend/{item_id}")
def extend_license(item_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM licenses WHERE id = ?", (item_id,))
    row = c.fetchone()
    if row:
        curr_exp = datetime.strptime(row[0], "%Y-%m-%d")
        # إذا كان منتهياً نمدد من اليوم، وإذا كان سارياً نمدد من تاريخ انتهائه
        base_date = max(datetime.now(), curr_exp)
        new_exp = (base_date + timedelta(days=30)).strftime("%Y-%m-%d")
        c.execute("UPDATE licenses SET expiry_date = ?, is_active = 1 WHERE id = ?", (new_exp, item_id))
        conn.commit()
    conn.close()
    return HTMLResponse('<script>window.location.href="/";</script>')

@app.post("/delete/{item_id}")
def delete_license(item_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM licenses WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return HTMLResponse('<script>window.location.href="/";</script>')

# ----------------- نقطة الفحص لتطبيق العميل (API) -----------------

@app.post("/api/verify")
def verify_license_api(req: CheckRequest):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT expiry_date, is_active FROM licenses WHERE device_id = ?", (req.device_id.strip().upper(),))
    row = c.fetchone()
    conn.close()

    if not row:
        return JSONResponse(status_code=403, content={"status": False, "message": "الجهاز غير مسجل، يرجى طلب التفعيل."})

    expiry_date = datetime.strptime(row[0], "%Y-%m-%d").date()
    is_active = bool(row[1])

    if not is_active:
        return JSONResponse(status_code=403, content={"status": False, "message": "تم إيقاف هذا الحساب من قبل الإدارة."})

    if datetime.now().date() > expiry_date:
        return JSONResponse(status_code=403, content={"status": False, "message": f"انتهت صلاحية اشتراكك في ({row[0]})."})

    return {
        "status": True,
        "message": "الترخيص سارٍ بنجاح.",
        "expiry_date": row[0]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
