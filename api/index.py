import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from supabase import create_client, Client
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-valeo")

# Підключення до Supabase через змінні оточення Vercel
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

# Головний HTML шаблон сайту (Чистий та адаптивний для телефону)
BASE_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Valeo Cab</title>
    <link href="https://jsdelivr.net" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; font-family: sans-serif; }
        .navbar { background-color: #212529; }
        .card { border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark mb-4">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🏭 Кабінет Valeo</span>
            {% if session.get('authorized') %}
                <a href="/logout" class="btn btn-outline-light btn-sm">Вихід</a>
            {% endif %}
        </div>
    </nav>
    <div class="container mb-5">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="alert alert-info">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        
        {{ content | safe }}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    # 1. Перевірка паролю
    if not session.get('authorized'):
        if request.method == 'POST':
            if request.form.get('password') == 'valeo2026': # Твій пароль
                session['authorized'] = True
                return redirect(url_for('index'))
            else:
                return render_template_string(BASE_HTML, content="""
                    <div class="row justify-content-center"><div class="col-md-4 card p-4 text-center">
                        <h3>🔒 Вхід до кабінету</h3>
                        <form method="POST" class="mt-3">
                            <input type="password" name="password" class="form-control mb-3" placeholder="Введіть особистий пароль" required>
                            <button type="submit" class="btn btn-primary w-100">Увійти</button>
                        </form>
                        <p class="text-danger mt-2">Неправильний пароль!</p>
                    </div></div>
                """)
        return render_template_string(BASE_HTML, content="""
            <div class="row justify-content-center"><div class="col-md-4 card p-4 text-center">
                <h3>🔒 Вхід до кабінету</h3>
                <form method="POST" class="mt-3">
                    <input type="password" name="password" class="form-control mb-3" placeholder="Введіть особистий пароль" required>
                    <button type="submit" class="btn btn-primary w-100">Увійти</button>
                </form>
            </div></div>
        """)

    # 2. Якщо авторизований — показуємо головну сторінку з даними та формою пошуку
    db_data = []
    if supabase:
        try:
            res = supabase.table("work_logs").select("*").order("data", desc=True).execute()
            db_data = res.data
        except Exception as e:
            print(e)

    # Формуємо таблицю рядків
    rows_html = ""
    for row in db_data:
        rows_html += f"""
        <tr>
            <td>{row['data']}</td>
            <td>{row['linia']}</td>
            <td>{row['zmiana']} зміна</td>
            <td>{row['godziny_fakt']} год (Ніч: {row['godziny_nocne']}, Над: {row['nadgodziny']})</td>
            <td><span class="text-success">OK: {row['komponenty_ok']}</span> / <span class="text-danger">NOK: {row['komponenty_nok']}</span></td>
        </tr>
        """

    page_content = f"""
    <div class="row g-4">
        <!-- Блок внесення рапорту -->
        <div class="col-md-4">
            <div class="card p-4">
                <h4>📝 Внесення рапорту за зміну</h4>
                <form action="/add_report" method="POST" class="mt-3">
                    <label class="form-label">Дата зміни</label>
                    <input type="date" name="data" class="form-control mb-2" required>
                    
                    <label class="form-label">Назва лінії</label>
                    <input type="text" name="linia" class="form-control mb-2" value="LF74" required>
                    
                    <label class="form-label">Зміна</label>
                    <select name="zmiana" class="form-select mb-2">
                        <option value="1">1 зміна</option>
                        <option value="2">2 зміна</option>
                        <option value="3">3 зміна</option>
                    </select>
                    
                    <label class="form-label">Планові години</label>
                    <input type="number" name="godziny_plan" class="form-control mb-2" value="8">
                    
                    <label class="form-label">Фактичні години</label>
                    <input type="number" name="godziny_fakt" class="form-control mb-3" value="8">
                    
                    <hr>
                    <label class="form-label text-success fw-bold">Перевірено ламп (OK)</label>
                    <input type="number" name="komponenty_ok" class="form-control mb-2" value="0">
                    
                    <label class="form-label text-danger fw-bold">Брак (NOK)</label>
                    <input type="number" name="komponenty_nok" class="form-control mb-3" value="0">
                    
                    <button type="submit" class="btn btn-success w-100">Зберегти в базу</button>
                </form>
            </div>
        </div>
        
        <!-- Блок пошуку та звірки годин -->
        <div class="col-md-8">
            <div class="card p-4 h-100">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h4>📊 Твої відпрацьовані зміни</h4>
                    <a href="/download_excel" class="btn btn-outline-primary btn-sm">📥 Скачати Excel</a>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover table-striped">
                        <thead class="table-dark">
                            <tr>
                                <th>Дата</th>
                                <th>Лінія</th>
                                <th>Зміна</th>
                                <th>Години</th>
                                <th>Рапорт деталей</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html if rows_html else '<tr><td colspan="5" class="text-center text-muted">База даних порожня. Внеси першу зміну ліворуч!</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """
    return render_template_string(BASE_HTML, content=page_content)

@app.route('/add_report', methods=['POST'])
def add_report():
    if not session.get('authorized'): return redirect(url_for('index'))
    
    data = request.form.get('data')
    linia = request.form.get('linia')
    zmiana = int(request.form.get('zmiana'))
    g_plan = int(request.form.get('godziny_plan', 8))
    g_fakt = int(request.form.get('godziny_fakt', 8))
    ok_lamps = int(request.form.get('komponenty_ok', 0))
    nok_lamps = int(request.form.get('komponenty_nok', 0))
    
    # Розрахунок годин для Umowa Zlecenia
    nadgodziny = max(0, g_fakt - g_plan)
    godziny_nocne = min(8, g_fakt) if zmiana == 3 else 0
    
    data_to_insert = {
        "data": data, "linia": linia, "zmiana": zmiana,
        "godziny_plan": g_plan, "godziny_fakt": g_fakt,
        "nadgodziny": nadgodziny, "godziny_nocne": godziny_nocne,
        "komponenty_ok": ok_lamps, "komponenty_nok": nok_lamps
    }
    
    if supabase:
        try:
            supabase.table("work_logs").upsert(data_to_insert).execute()
        except Exception as e:
            print(e)
            
    return redirect(url_for('index'))

@app.route('/download_excel')
def download_excel():
    if not session.get('authorized'): return redirect(url_for('index'))
    if not supabase: return "Помилка бази даних"
    
    res = supabase.table("work_logs").select("*").order("data", desc=True).execute()
    df = pd.DataFrame(res.data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Звіт_Valeo')
    output.seek(0)
    
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="zvit_valeo.xlsx")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
