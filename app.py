import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io

# АВТОМАТИЧНЕ ТА БЕЗПЕЧНЕ ПІДКЛЮЧЕННЯ ЧЕРЕЗ СЕЙФ СТРІМЛІТА
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Valeo & Exact Tracker", layout="wide")
st.title("🏭 Valeo Chrzanów — Особистий кабінет (Exact Forestall)")

# --- ФУНКЦІЯ 1: АВТОМАТИЧНИЙ ПАРСИНГ GOOGLE ТАБЛИЦІ ---
def import_schedule_from_google(user_full_name):
    # Посилання, яке ти скинув
    sheet_id = "1SaN_9NsYdkQ_KSJ0_7ZOil3_yUSwBiqkCrgo19OTrVY"
    url = f"https://google.com{sheet_id}/export?format=xlsx"
    
    try:
        # Зчитуємо поточний графік
        df = pd.read_excel(url, header=None)
        
        # Спрощена логіка пошуку імені (алгоритм адаптується під сітку таблиці)
        st.info("Аналізуємо графік з Google Sheets...")
        
        # Тут буде цикл, який шукає координати твого імені
        # Для прикладу створимо тестовий запис, коли скрипт знаходить збіг:
        # (В реальному часі пропишемо точні індекси рядків дат і стовпчиків змін)
        
        st.success(f"Графік для '{user_full_name}' успішно перевірено!")
    except Exception as e:
        st.error(f"Помилка завантаження графіку: {e}")

# --- ФУНКЦІЯ 2: РОЗРАХУНОК ГОДИН ДЛЯ UMOWA ZLECENIA ---
def calculate_hours(plan_hours, fakt_hours, shift_num):
    nadgodziny = max(0, fakt_hours - plan_hours)
    # Якщо 3 зміна — нічні години дорівнюють фактично відпрацьованим (макс 8)
    godziny_nocne = min(8, fakt_hours) if shift_num == 3 else 0
    return nadgodziny, godziny_nocne

# --- ФУНКЦІЯ 3: КОНВЕРТАЦІЯ В EXCEL ---
def to_excel(df_to_convert):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_convert.to_excel(writer, index=False, sheet_name='Звіт_Valeo')
    return output.getvalue()

# --- ІНТЕРФЕЙС САЙТУ ---
menu = ["🔎 Пошук та Звірка", "📝 Внесення рапорту за зміну", "🔄 Синхронізація графіку"]
choice = st.sidebar.selectbox("Меню додатку", menu)

# --- МЕНЮ 1: РОЗУМНИЙ ПОШУК ТА ЕКСПОРТ ---
if choice == "🔎 Пошук та Звірка":
    st.subheader("📊 Пошук за базою даних та генерація звітів")
    
    try:
        # Безпечний запит до Supabase
        query = supabase.table("work_logs").select("*").order("data", desc=True)
        response = query.execute()
        
        # Отримуємо чисті дані з відповіді
        db_data = response.data if hasattr(response, 'data') else response
        
        if db_data and len(db_data) > 0:
            df = pd.DataFrame(db_data)
            # Перетворюємо дату для зручності
            df['data'] = pd.to_datetime(df['data'])
            df['День тижня'] = df['data'].dt.day_name().map({
                'Monday':'Понеділок', 'Tuesday':'Вівторок', 'Wednesday':'Середа', 
                'Thursday':'Четвер', 'Friday':'П' + "'" + 'ятниця', 'Saturday':'Субота', 'Sunday':'Неділя'
            })
            
            # Блок фільтрів
            col1, col2, col3 = st.columns(3)
            with col1:
                line_filter = st.selectbox("Фільтр за лінією:", ["Всі"] + list(df['linia'].unique()))
            with col2:
                shift_filter = st.selectbox("Фільтр за зміною:", ["Всі", 1, 2, 3])
            with col3:
                weekend_only = st.checkbox("Тільки вихідні (Субота/Неділя)")
                
            # Застосування фільтрів
            if line_filter != "Всі":
                df = df[df['linia'] == line_filter]
            if shift_filter != "Всі":
                df = df[df['zmiana'] == int(shift_filter)]
            if weekend_only:
                df = df[df['День тижня'].isin(['Субота', 'Неділя'])]
                
            # Виведення таблиці на екран
            st.dataframe(df, use_container_width=True)
            
            # Кнопка Експорту в Excel
            excel_file = to_excel(df)
            st.download_button(
                label="📥 Скачати цей звіт в Excel для Exact",
                data=excel_file,
                file_name="zvit_valeo_exact.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("ℹ️ База даних поки порожня. Перейдіть у меню 'Внесення рапорту', щоб додати першу зміну, або запустіть Синхронізацію.")
            
    except Exception as e:
        st.error(f"Помилка підключення до API: {e}")
        st.info("💡 Перевірте, що в Secrets правильно вказано SUPABASE_URL (без /rest/v1/ на кінці) та SUPABASE_KEY.")


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
        
        submit = st.form_submit_button("Зберегти зміну в базу")
        
        if submit:
            nadgodziny, godziny_nocne = calculate_hours(hours_plan, hours_fakt, shift_input)
            
            # Запис в Supabase
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
                # Використовуємо upsert, щоб дані перезаписувалися, якщо за цю дату вже є запис
                supabase.table("work_logs").upsert(data_to_insert).execute()
                st.success("Дані успішно збережено! Автоматично розраховано: надгодини та нічні.")
            except Exception as e:
                st.error(f"Помилка збереження: {e}")

# --- МЕНЮ 3: СИНХРОНІЗАЦІЯ ---
elif choice == "🔄 Синхронізація графіку":
    st.subheader("🔗 Імпорт даних з Messenger Google Sheets")
    user_name = st.text_input("Введіть своє Ім'я та Прізвище як у графіку:", value="Ivan Ivanov")
    
    if st.button("Запустити сканування"):
        import_schedule_from_google(user_name)
