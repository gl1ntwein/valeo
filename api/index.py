import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file, make_response
from supabase import create_client, Client
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "valeo-exact-secret-2026")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True

# Глобальне підключення, щоб не створювати нові пули з'єднань щоразу
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Помилка Supabase: {e}")

# Імпортуємо твій HTML-дизайн
from .html_template import COMBINED_HTML

# Допоміжна функція для швидкої та чіткої відповіді браузеру
def quick_response(html_content):
    response = make_response(html_content)
    # Перетворюємо текст в байти, щоб дізнатися точну вагу сторінки
    response_bytes = html_content.encode('utf-8')
    
    # Головні хаки проти зависань на Vercel:
    response.headers["Content-Length"] = str(len(response_bytes)) # МИТТЄВО обриває крутіння в браузері
    response.headers["Connection"] = "close"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route('/', methods=['GET', 'POST'])
def index():
    error_msg = None
    if request.method == 'POST' and not session.get('authorized'):
        if request.form.get('password') == 'valeo2026':
            session['authorized'] = True
            res = make_response(redirect(url_for('index')))
            res.headers["Connection"] = "close"
            return res
        else:
            error_msg = "❌ Неправильний пароль!"

    db_data = []
    if session.get('authorized') and supabase_client:
        try:
            data_res = supabase_client.table("work_logs").select("*").order("data", desc=True).execute()
            db_data = data_res.data if hasattr(data_res, 'data') else data_res
        except Exception as e:
            print(f"Помилка бази: {e}")

    rendered = render_template_string(COMBINED_HTML, authorized=session.get('authorized'), logs=db_data, error=error_msg)
    return quick_response(rendered)

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
    
    if supabase_client:
        try:
            supabase_client.table("work_logs").upsert(data_to_insert).execute()
        except Exception as e:
            print(e)
            
    res = make_response(redirect(url_for('index')))
    res.headers["Connection"] = "close"
    return res

@app.route('/download_excel')
def download_excel():
    if not session.get('authorized'): return redirect(url_for('index'))
    if not supabase_client: return "Помилка бази даних"
    
    import pandas as pd
    res = supabase_client.table("work_logs").select("*").order("data", desc=True).execute()
    db_data = res.data if hasattr(res, 'data') else res
    df = pd.DataFrame(db_data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Звіт_Valeo')
    output.seek(0)
    
    response = make_response(send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="zvit_valeo.xlsx"))
    response.headers["Connection"] = "close"
    return response

@app.route('/logout')
def logout():
    session.clear()
    res = make_response(redirect(url_for('index')))
    res.headers["Connection"] = "close"
    return res
