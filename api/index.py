import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file, flash
from supabase import create_client, Client
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "valeo-key-2026")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        supabase = None
except Exception as e:
    supabase = None

BASE_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Valeo Cab</title>
    <link href="https://jsdelivr.net" rel="stylesheet">
    <link href="https://googleapis.com" rel="stylesheet">
    <link rel="stylesheet" href="https://jsdelivr.net">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Inter', sans-serif; }
        .navbar { background-color: #1e293b; border-bottom: 1px solid #334155; padding: 15px 0; }
        .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); color: #f8fafc; }
        .form-control, .form-select { background-color: #0f172a; border: 1px solid #334155; color: #f8fafc; border-radius: 10px; padding: 10px 14px; }
        .form-control:focus, .form-select:focus { background-color: #0f172a; border-color: #38bdf8; color: #f8fafc; box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2); }
        .btn-primary { background-color: #0284c7; border: none; border-radius: 10px; padding: 12px; font-weight: 600; }
        .btn-success { background-color: #10b981; border: none; border-radius: 10px; padding: 12px; font-weight: 600; }
        .badge-shift { padding: 6px 12px; border-radius: 8px; font-weight: 600; font-size: 0.85rem; }
        .shift-1 { background-color: #1e40af; color: #93c5fd; }
        .shift-2 { background-color: #854d0e; color: #fde047; }
        .shift-3 { background-color: #581c87; color: #f3e8ff; }
        @media (max-width: 768px) { .desktop-table { display: none; } .mobile-card-list { display: block; } }
        @media (min-width: 769px) { .desktop-table { display: table; } .mobile-card-list { display: none; } }
        .mobile-log-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 15px; margin-bottom: 12px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark mb-4">
        <div class="container">
            <span class="navbar-brand mb-0 h1 fw-bold"><i class="bi bi-factory me-2 text-info"></i>Valeo Cab</span>
            {% if session.get('authorized') %}
                <a href="/logout" class="btn btn-outline-danger btn-sm px-3" style="border-radius: 8px;"><i class="bi bi-box-arrow-right me-1"></i>Вихід</a>
            {% endif %}
        </div>
    </nav>
    <div class="container mb-5">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="alert alert-info border-0 text-white bg-info bg-opacity-25 mb-4" style="border-radius: 10px;">{{ message }}</div>
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
    if not session.get('authorized'):
        error_msg = ""
        if request.method == 'POST':
            if request.form.get('password') == 'valeo2026':
                session['authorized'] = True
                return redirect(url_for('index'))
            else:
                error_msg = '<div class="alert alert-danger border-0 bg-danger bg-opacity-10 text-danger mt-3" style="border-radius:10px;">❌ Неправильний пароль!</div>'
        
        return render_template_string(BASE_HTML, content=f"""
            <div class="row justify-content-center mt-5"><div class="col-md-4 card p-4 m-3">
                <div class="text-center mb-4">
                    <i class="bi bi-shield-lock-fill text-info" style="font-size: 3rem;"></i>
                    <h3 class="mt-2 fw-bold">Вхід до системи</h3>
                    <p class="text-muted small">Введіть ваш таємний пароль для доступу</p>
                </div>
                <form method="POST">
                    <input type="password" name="password" class="form-control mb-3 text-center" placeholder="••••••••" required>
                    <button type="submit" class="btn btn-primary w-100"><i class="bi bi-unlock-fill me-2"></i>Увійти</button>
                </form>
                {error_msg}
            </div></div>
        """)

    db_data = []
    if supabase:
        try:
            res = supabase.table("work_logs").select("*").order("data", desc=True).execute()
            db_data = res.data if hasattr(res, 'data') else res
        except Exception as e:
            print(e)

    rows_html = ""
    for row in db_data:
        rows_html += f"""
        <tr style="border-bottom: 1px solid #334155; vertical-align: middle;">
            <td class="fw-medium text-white">{row['data']}</td>
            <td><span class="badge bg-secondary px-2.5 py-1.5" style="border-radius:6px;">{row['linia']}</span></td>
            <td><span class="badge-shift shift-{row['zmiana']}">{row['zmiana']} зміна</span></td>
            <td>
                <span class="text-white-50">{row['godziny_fakt']} год</span> 
                {f'<span class="badge bg-info bg-opacity-10 text-info ms-1 small" style="font-size:0.75rem;">Ніч: {row["godziny_nocne"]}</span>' if row['godziny_nocne'] > 0 else ''}
                {f'<span class="badge bg-warning bg-opacity-10 text-warning ms-1 small" style="font-size:0.75rem;">Над: {row["nadgodziny"]}</span>' if row['nadgodziny'] > 0 else ''}
            </td>
            <td>
                <span class="text-success fw-semibold"><i class="bi bi-check-circle-fill me-1"></i>{row['komponenty_ok']}</span> 
                <span class="text-muted mx-1">/</span>
                <span class="text-danger fw-semibold"><i class="bi bi-x-circle-fill me-1"></i>{row['komponenty_nok']}</span>
            </td>
        </tr>
        """

    mobile_cards_html = ""
    for row in db_data:
        mobile_cards_html += f"""
        <div class="mobile-log-card">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="fw-bold text-white"><i class="bi bi-calendar3 me-2 text-info"></i>{row['data']}</span>
                <span class="badge-shift shift-{row['zmiana']}">{row['zmiana']} зміна</span>
            </div>
            <div class="d-flex justify-content-between text-muted small mb-2" style="border-bottom: 1px solid #334155; padding-bottom:8px;">
                <span>Лінія: <strong class="text-white">{row['linia']}</strong></span>
                <span>Відпрацьовано: <strong class="text-white">{row['godziny_fakt']} год</strong></span>
            </div>
            <div class="d-flex justify-content-between align-items-center pt-1">
                <div class="small">
                    {f'<span class="text-info me-2"><i class="bi bi-moon-stars me-1"></i>Нічні: {row["godziny_nocne"]}</span>' if row['godziny_nocne'] > 0 else ''}
                    {f'<span class="text-warning"><i class="bi bi-lightning me-1"></i>Над: {row["nadgodziny"]}</span>' if row['nadgodziny'] > 0 else ''}
                </div>
                <div>
                    <span class="badge bg-success bg-opacity-10 text-success px-2 py-1">OK: {row['komponenty_ok']}</span>
                    <span class="badge bg-danger bg-opacity-10 text-danger px-2 py-1 ms-1">NOK: {row['komponenty_nok']}</span>
                </div>
            </div>
        </div>
        """
    page_content = f"""
    <div class="row g-4">
        <div class="col-md-4">
            <div class="card p-4">
                <h4 class="fw-bold mb-3 text-info"><i class="bi bi-pen me-2"></i>Внесення зміни</h4>
                <form action="/add_report" method="POST">
                    <div class="mb-3">
                        <label class="form-label text-white-50 small fw-medium">Дата зміни</label>
                        <input type="date" name="data" class="form-control" required>
                    </div>
                    <div class="row g-2 mb-3">
                        <div class="col-7">
                            <label class="form-label text-white-50 small fw-medium">Назва лінії</label>
                            <input type="text" name="linia" class="form-control" value="LF74" required>
                        </div>
                        <div class="col-5">
                            <label class="form-label text-white-50 small fw-medium">Зміна</label>
                            <select name="zmiana" class="form-select">
                                <option value="1">1 зміна</option>
                                <option value="2">2 зміна</option>
                                <option value="3">3 зміна</option>
                            </select>
                        </div>
                    </div>
                    <div class="row g-2 mb-3" style="border-bottom: 1px solid #334155; padding-bottom: 15px;">
                        <div class="col-6">
                            <label class="form-label text-white-50 small fw-medium">Годин за графіком</label>
                            <input type="number" name="godziny_plan" class="form-control" value="8">
                        </div>
                        <div class="col-6">
                            <label class="form-label text-white-50 small fw-medium">Відпрацьовано факт</label>
                            <input type="number" name="godziny_fakt" class="form-control" value="8">
                        </div>
                    </div>
                    <h6 class="fw-bold mb-2 text-white"><i class="bi bi-box-seam me-2 text-muted"></i>Паперовий рапорт деталей:</h6>
                    <div class="row g-2 mb-4">
                        <div class="col-6">
                            <label class="form-label text-success small fw-medium">Кількість OK</label>
                            <input type="number" name="komponenty_ok" class="form-control" value="0">
                        </div>
                        <div class="col-6">
                            <label class="form-label text-danger small fw-medium">Кількість NOK</label>
                            <input type="number" name="komponenty_nok" class="form-control" value="0">
                        </div>
                    </div>
                    <button type="submit" class="btn btn-success w-100"><i class="bi bi-cloud-arrow-up-fill me-2"></i>Зберегти в базу даних</button>
                </form>
            </div>
        </div>
        <div class="col-md-8">
            <div class="card p-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h4 class="fw-bold m-0 text-info"><i class="bi bi-database-check me-2"></i>Історія та звірка годин</h4>
                    <a href="/download_excel" class="btn btn-primary btn-sm px-3"><i class="bi bi-file-earmark-excel me-1"></i>Скачати Excel</a>
                </div>
                <div class="table-responsive desktop-table">
                    <table class="table table-dark table-hover m-0">
                        <thead>
                            <tr style="border-bottom: 2px solid #334155; color: #94a3b8; font-size: 0.85rem;">
                                <th>ДАТА</th>
                                <th>ЛІНІЯ</th>
                                <th>ЗМІНА</th>
                                <th>ГОДИНИ</th>
                                <th>ДЕТАЛІ (OK/NOK)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html if rows_html else '<tr><td colspan="5" class="text-center text-muted py-4">База даних порожня. Внеси першу зміну ліворуч!</td></tr>'}
                        </tbody>
                    </table>
                </div>
                <div class="mobile-card-list">
                    {mobile_cards_html if mobile_cards_html else '<p class="text-center text-muted py-4">База даних порожня. Внеси першу зміну!</p>'}
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
