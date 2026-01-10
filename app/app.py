from flask import Flask, request, redirect, render_template_string
import os
import mariadb

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "notesuser")
DB_PASS = os.getenv("DB_PASS", "ChangeMe_StrongPassword")
DB_NAME = os.getenv("DB_NAME", "notesdb")

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Notes App</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 12px; }
    textarea { width: 100%; height: 110px; padding: 10px; }
    button { padding: 10px 16px; margin-top: 10px; cursor: pointer; }
    .note { border: 1px solid #ddd; border-radius: 10px; padding: 12px 14px; margin-top: 14px; background: #fff; }
    .ts { color: #666; font-size: 0.92em; margin-bottom: 6px; }
    .content { white-space: pre-wrap; }
    .footer { margin-top: 30px; color: #888; font-size: 0.9em; }
  </style>
</head>
<body>
  <h1>📝 Note-Taking App</h1>
  <form method="post" action="/add">
    <textarea name="content" placeholder="Write your note here..." required></textarea>
    <br/>
    <button type="submit">Save Note</button>
  </form>

  <h2>Latest Notes</h2>
  {% for n in notes %}
    <div class="note">
      <div class="ts">🕒 {{ n['created_at'] }}</div>
      <div class="content">📌 {{ n['content'] }}</div>
    </div>
  {% else %}
    <p>No notes yet.</p>
  {% endfor %}

  <div class="footer">Deployed with Nginx + Gunicorn + MariaDB</div>
</body>
</html>
"""

def get_conn():
    return mariadb.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=True,
    )

@app.get("/")
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT content, created_at FROM notes ORDER BY created_at DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    notes = [{"content": r[0], "created_at": r[1].strftime("%Y-%m-%d %H:%M:%S")} for r in rows]
    return render_template_string(HTML, notes=notes)

@app.post("/add")
def add_note():
    content = request.form.get("content", "").strip()
    if content:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO notes (content) VALUES (?);", (content,))
        cur.close()
        conn.close()
    return redirect("/")

@app.get("/health")
def health():
    # Simple health check: DB connectivity + basic query
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok"}, 200
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
