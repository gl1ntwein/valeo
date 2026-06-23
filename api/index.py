import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from supabase import create_client, Client
import pandas as pd
import io

# Імпортуємо HTML-код із сусіднього файлу модуля
from .html_template import COMBINED_HTML

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "valeo-exact-secret-2026")

def get_supabase():
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if url and key:
        return create_client(url, key)
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    error_msg = None
    if request.method == 'POST' and not session.get('authorized'):
        if request.form.get('password') == 'valeo2026':
            session['authorized'] = True
            return redirect(url_for('index'))
        else:
            error_msg = "❌ Неправильний пароль!"

    db_data = []
    if session.get('authorized'):
        db = get_supabase()
        if db:
            try:
                res = db.table("work_logs").select("*").order("data", desc=True).execute()
                db_data = res.data if hasattr(res, 'data') else res
            except Exception as e:
                print(f"Помилка бази даних: {e}")

    return render_template_string(COMBINED_HTML, authorized=session.get('authorized'), logs=db_data, error=error_msg)

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
    
    db = get_supabase()
    if db:
        try:
            db.table("work_logs").upsert(data_to_insert).execute()
        except Exception as e:
            print(e)
            
    return redirect(url_for('index'))

@app.route('/download_excel')
def download_excel():
    if not session.get('authorized'): return redirect(url_for('index'))
    db = get_supabase()
    if not db: return "Помилка бази даних"
    
    res = db.table("work_logs").select("*").order("data", desc=True).execute()
    db_data = res.data if hasattr(res, 'data') else res
    df = pd.DataFrame(db_data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Звіт_Valeo')
    output.seek(0)
    
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="zvit_valeo.xlsx")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
