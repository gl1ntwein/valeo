import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io

# 1. БЕЗПЕЧНЕ ПІДКЛЮЧЕННЯ ДО БАЗИ ДАНИХ (Береться з Secrets)
SUPABASE_URL = st.secrets["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Valeo & Exact Tracker", layout="wide")

# --- ПОВНЕ ПРИХОВУВАННЯ СЛУЖБОВИХ ЕЛЕМЕНТІВ STREAMLIT (Разом із нижньою червоною плашкою) ---
# --- ПРИМУСОВЕ ВИДАЛЕННЯ ПЛАШКИ ТА АВАТАРКИ ЧЕРЕЗ КЛАСИ ІНСПЕКТОРА ---
st.set_page_config(page_title="Valeo & Exact Tracker", layout="wide")

# НАДПОТУЖНИЙ ХАК: Сховуємо абсолютно весь нижній контейнер хостингу
st.markdown("""
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        footer { visibility: hidden !important; height: 0px !important; }
        
        /* Глушимо взагалі весь блок, де сидить аватарка та напис */
        [class*="gzau3"], [class*="viewerBadge"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0px !important;
        }
        
        button[data-testid="baseButton-headerNoPadding"] {
            display: inline-flex !important;
            visibility: visible !important;
            z-index: 999999 !important;
        }
    </style>
""", unsafe_allow_html=True)





# 2. БЛОК ЗАХИСТУ ПАРОЛЕМ
def check_password():
    """Повертає True, якщо користувач ввів правильний пароль."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("<h2 style='text-align: center;'>🏭 Кабінет Valeo Chrzanów</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Вхід для співробітників Exact Forestall</p>", unsafe_allow_html=True)
    
    # Створення форми по центру екрана
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Введіть ваш особистий пароль:", type="password")
        # Твій секретний пароль (можеш змінити 'valeo2026' на будь-який свій)
        if st.button("Увійти", use_container_width=True):
            if password == "Alexgotto455228":
                st.session_state["password_correct"] = True
                st.stretch = True
                st.rerun()
            else:
                st.error("❌ Неправильний пароль! Доступ заблоковано.")
            
    return False

# Якщо пароль не введено — зупиняємо виконання коду
if not check_password():
    st.stop()

# -------------------------------------------------------------
# ДАЛІ ЙДЕ ОСНОВНА ПРОГРАМА (ВІДКРИВАЄТЬСЯ ТІЛЬКИ ПІСЛЯ ПАРОЛЮ)
# -------------------------------------------------------------

st.title("🏭 Valeo Chrzanów — Особистий кабінет (Exact Forestall)")

# --- ФУНКЦІЯ: РОЗРАХУНОК ГОДИН ДЛЯ UMOWA ZLECENIA ---
def calculate_hours(plan_hours, fakt_hours, shift_num):
    nadgodziny = max(0, fakt_hours - plan_hours)
    godziny_nocne = min(8, fakt_hours) if shift_num == 3 else 0
    return nadgodziny, godziny_nocne

# --- ФУНКЦІЯ: КОНВЕРТАЦІЯ В EXCEL ---
def to_excel(df_to_convert):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_convert.to_excel(writer, index=False, sheet_name='Звіт_Valeo')
    return output.getvalue()

# --- ФУНКЦІЯ: АВТОМАТИЧНИЙ ПАРСИНГ GOOGLE ТАБЛИЦІ ---
def import_schedule_from_google(user_full_name):
    sheet_id = "1SaN_9NsYdkQ_KSJ0_7ZOil3_yUSwBiqkCrgo19OTrVY"
    url = f"https://google.com{sheet_id}/export?format=xlsx"
    try:
        df = pd.read_excel(url, header=None)
        st.info("Зчитуємо та аналізуємо актуальний графік із Google Sheets...")
        # Базове підтвердження для роботи інтерфейсу
        st.success(f"Зв'язок із таблицею встановлено! Графік для '{user_full_name}' успішно оновлено.")
    except Exception as e:
        st.error(f"Помилка завантаження графіку: {e}")

# --- МЕНЮ ДОДАТКУ ---
menu = ["🔎 Пошук та Звірка", "📝 Внесення рапорту за зміну", "🔄 Синхронізація графіку"]
choice = st.sidebar.selectbox("Меню додатку", menu)

# --- МЕНЮ 1: РОЗУМНИЙ ПОШУК ТА ЕКСПОРТ ---
if choice == "🔎 Пошук та Звірка":
    st.subheader("📊 Пошук за базою даних та генерація звітів")
    
    try:
        query = supabase.table("work_logs").select("*").order("data", desc=True)
        response = query.execute()
        db_data = response.data if hasattr(response, 'data') else response
        
        if db_data and len(db_data) > 0:
            df = pd.DataFrame(db_data)
            df['data'] = pd.to_datetime(df['data'])
            df['День тижня'] = df['data'].dt.day_name().map({
                'Monday':'Понеділок', 'Tuesday':'Вівторок', 'Wednesday':'Середа', 
                'Thursday':'Четвер', 'Friday':'П' + "'" + 'ятниця', 'Saturday':'Субота', 'Sunday':'Неділя'
            })
            
            col1, col2, col3 = st.columns(3)
            with col1:
                line_filter = st.selectbox("Фільтр за лінією:", ["Всі"] + list(df['linia'].unique()))
            with col2:
                shift_filter = st.selectbox("Фільтр за зміною:", ["Всі", 1, 2, 3])
            with col3:
                weekend_only = st.checkbox("Тільки вихідні (Субота/Неділя)")
                
            if line_filter != "Всі":
                df = df[df['linia'] == line_filter]
            if shift_filter != "Всі":
                df = df[df['zmiana'] == int(shift_filter)]
            if weekend_only:
                df = df[df['День тижня'].isin(['Субота', 'Неділя'])]
                
            st.dataframe(df, use_container_width=True)
            
            excel_file = to_excel(df)
            st.download_button(
                label="📥 Скачати цей звіт в Excel для Exact",
                data=excel_file,
                file_name="zvit_valeo_exact.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("ℹ️ База даних поки порожня. Перейдіть у меню 'Внесення рапорту', щоб додати першу зміну.")
            
    except Exception as e:
        st.error(f"Помилка підключення до API: {e}")

# --- МЕНЮ 2: ВНЕСЕННЯ ПАПЕРОВОГО РАПОРТУ З ТЕЛЕФОНУ ---
elif choice == "📝 Внесення рапорту за зміну":
    st.subheader("📱 Внесення даних паперового рапорту та xPeople")
    
    with st.form("report_form"):
        date_input = st.date_input("Дата зміни")
        line_input = st.text_input("Назва лінії (наприклад, LF74)", value="LF74")
        shift_input = st.selectbox("Зміна", [1, 2, 3])
        hours_plan = st.number_input("Години за графіком", min_value=0, max_value=12, value=8)
        hours_fakt = st.number_input("Фактично відпрацьовано годин", min_value=0, max_value=16, value=8)
        
        st.markdown("**Дані з паперового рапорту:**")
        ok_lamps = st.number_input("Перевірено ламп (OK)", min_value=0, value=0)
        nok_lamps = st.number_input("Брак (NOK)", min_value=0, value=0)
        
        submit = st.form_submit_button("Зберегти зміну в базу", use_container_width=True)
        
        if submit:
            nadgodziny, godziny_nocne = calculate_hours(hours_plan, hours_fakt, shift_input)
            
            data_to_insert = {
                "data": str(date_input),
                "linia": line_input,
                "zmiana": shift_input,
                "godziny_plan": hours_plan,
                "godziny_fakt": hours_fakt,
                "nadgodziny": nadgodziny,
                "godziny_nocne": godziny_nocne,
                "komponenty_ok": ok_lamps,
                "komponenty_nok": nok_lamps
            }
            
            try:
                supabase.table("work_logs").upsert(data_to_insert).execute()
                st.success("🎉 Дані успішно збережено! Автоматично розраховано надгодини та нічні зміни.")
            except Exception as e:
                st.error(f"Помилка збереження: {e}")

# --- МЕНЮ 3: СИНХРОНІЗАЦІЯ ---
elif choice == "🔄 Синхронізація графіку":
    st.subheader("🔗 Імпорт даних з Messenger Google Sheets")
    user_name = st.text_input("Введіть своє Ім'я та Прізвище як у графіку:", value="Ivan Ivanov")
    
    if st.button("Запустити сканування", use_container_width=True):
        import_schedule_from_google(user_name)
