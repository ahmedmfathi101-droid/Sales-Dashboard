import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
import io
import os
import random

# إعداد الصفحة
st.set_page_config(page_title="نظام إدارة المبيعات المتقدم", page_icon="📈", layout="wide")

# ==========================================
# 1. تصميم CSS الاحترافي (RTL & Login UI)
# ==========================================
st.markdown("""
    <style>
    .main .block-container { direction: rtl; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    .custom-kpi-card { background: linear-gradient(145deg, #1e1e2d, #26273b); border-right: 5px solid #00E676; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px; text-align: right; }
    .kpi-title { color: #a1a5b7; font-size: 1.1rem; margin-bottom: 8px; font-weight: 500; }
    .kpi-value { color: #ffffff; font-size: 2.2rem; font-weight: bold; }
    .kpi-value span { color: #00E676; font-size: 1.2rem; margin-right: 5px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e1e2d; border-radius: 8px 8px 0 0; padding: 10px 20px; }
    
    .english-quote-box {
        padding: 20px; background: linear-gradient(145deg, #1e1e2d, #26273b); border-radius: 15px;
        border-top: 4px solid #00E676; color: #e4e6ef; font-size: 1.15rem; font-style: italic;
        text-align: center; direction: ltr; box-shadow: 0 10px 20px rgba(0,0,0,0.3); margin-bottom: 25px; font-family: 'Georgia', serif;
    }
    
    .arabic-quote-box {
        background: rgba(0, 230, 118, 0.05); border-right: 4px solid #00E676; padding: 15px; margin: 20px 0;
        border-radius: 8px; color: #e4e6ef; font-size: 1.05rem; font-style: italic; line-height: 1.5; text-align: right; direction: rtl;
    }
    
    .dev-footer { background: rgba(30, 30, 45, 0.7); padding: 25px; border-radius: 15px; border: 1px solid #2e2e40; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.3); margin-top: 30px;}
    .dev-name { font-size: 1.8rem; font-weight: bold; background: -webkit-linear-gradient(45deg, #00E676, #3699ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .dev-title { color: #a1a5b7; font-size: 1rem; margin-bottom: 20px; letter-spacing: 1px; }
    .social-links { display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; direction: ltr; }
    .social-links a { color: #e4e6ef; text-decoration: none; font-size: 0.95rem; font-weight: 500; display: flex; align-items: center; gap: 8px; transition: all 0.3s ease; padding: 10px 18px; background: #232334; border-radius: 8px; border: 1px solid #333; }
    .social-links a:hover { background: #3699ff; color: white; border-color: #3699ff; transform: translateY(-3px); box-shadow: 0 5px 15px rgba(54, 153, 255, 0.4); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. نظام تسجيل الدخول المحدث (مانع أخطاء المسافات)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    eng_quotes = [
        "\"The best salespeople wonder what they would want if they were the buyer.\" – Richard Thalheimer",
        "\"Success in sales is the sum of small efforts, repeated day in and day out.\" – Robert Collier",
        "\"Approach each customer with the idea of helping him solve a problem, not of selling a product.\" – Brian Tracy",
        "\"Great salespeople are relationship builders who provide value and help their customers win.\" – Jeffrey Gitomer"
    ]
    ar_quotes = [
        "«المبيعات ليست مجرد أرقام، بل هي فن بناء الثقة وحل مشكلات ضيوفنا.»",
        "«أفضل بائع هو من يمتلك مهارة الاستماع الفعال والتعاطف مع احتياجات العميل.»",
        "«لا تبيع منتجاً، بل قدم رعايةً وحلاً يصنع فارقاً حقيقياً.»",
        "«النجاح في المبيعات هو نتيجة الانضباط اليومي، والالتزام بأعلى المعايير الأخلاقية.»"
    ]
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="english-quote-box">{random.choice(eng_quotes)}</div>', unsafe_allow_html=True)
        
        if os.path.exists("logo.jpg"):
            img_col1, img_col2, img_col3 = st.columns([1, 2, 1])
            with img_col2:
                st.image("logo.jpg", use_container_width=True)
                
        st.markdown("<h2 style='text-align: center; color: white; margin-top: 15px;'>نظام إدارة المبيعات المتقدم</h2>", unsafe_allow_html=True)
        st.markdown(f'<div class="arabic-quote-box">💡 {random.choice(ar_quotes)}</div>', unsafe_allow_html=True)
        
        user_input = st.text_input("اسم المستخدم", placeholder="أدخل اسم المستخدم هنا...")
        pass_input = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة المرور...")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("تسجيل الدخول 🚀", use_container_width=True, type="primary"):
            # استخدام strip() لإزالة أي مسافات فارغة كتبها المستخدم بالخطأ
            clean_user = user_input.strip()
            clean_pass = pass_input.strip()
            
            if "users" in st.secrets and clean_user in st.secrets["users"]:
                if str(st.secrets["users"][clean_user]) == clean_pass:
                    st.session_state.logged_in = True
                    st.session_state.username = clean_user
                    st.rerun()
                else:
                    st.error("❌ كلمة المرور غير صحيحة")
            else:
                st.error("❌ اسم المستخدم غير مسجل في النظام")
                
        st.markdown("""
        <div class="dev-footer">
            <div class="dev-name">Ahmed Fathi The Wolf</div>
            <div class="dev-title">Pharmacist, Data Analyst & Researcher</div>
            <div class="social-links">
                <a href="http://ahmedmf.online/" target="_blank">🌐 Website</a>
                <a href="https://www.linkedin.com/in/ahmed-fathi-132101" target="_blank">💼 LinkedIn</a>
                <a href="https://github.com/ahmedmfathi101-droid" target="_blank">🐙 GitHub</a>
                <a href="https://x.com/ahmed101fathi" target="_blank">𝕏</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. الاتصال بقاعدة البيانات وتهيئة العزل 
# ==========================================
conn = st.connection("postgresql", type="sql")

with conn.session as s:
    s.execute(text('''CREATE TABLE IF NOT EXISTS sales_data (id SERIAL PRIMARY KEY, date DATE, day VARCHAR(50), time_slot VARCHAR(100), sales DOUBLE PRECISION, entered_by VARCHAR(50))'''))
    s.execute(text('''CREATE TABLE IF NOT EXISTS user_daily_targets (date DATE, username VARCHAR(50), target DOUBLE PRECISION, PRIMARY KEY (date, username))'''))
    s.execute(text('''CREATE TABLE IF NOT EXISTS user_shift_schedule (date DATE, username VARCHAR(50), start_time VARCHAR(10), end_time VARCHAR(10), PRIMARY KEY (date, username))'''))
    s.commit()

def load_data(user):
    query = f"""SELECT date AS "Date", day AS "Day", time_slot AS "Time_Slot", sales AS "Sales" FROM sales_data WHERE entered_by = '{user}' ORDER BY date, time_slot"""
    return conn.query(query, ttl=0)

def load_target(d, user):
    query = f"""SELECT target FROM user_daily_targets WHERE date = '{str(d)}' AND username = '{user}'"""
    target_df = conn.query(query, ttl=0)
    return target_df.iloc[0]['target'] if not target_df.empty else 0.0

# ==========================================
# 4. إعدادات الوقت والجدولة الذكية 
# ==========================================
cairo_tz = pytz.timezone('Africa/Cairo')
now = datetime.now(cairo_tz)
today_date = now.date()
current_user = st.session_state.username

st.sidebar.markdown(f"👤 مرحباً، **{current_user}**")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⏱️ لوحة التحكم الزمنية")
if st.sidebar.button("🔄 تحديث الوقت والبيانات", use_container_width=True):
    st.rerun()
st.sidebar.info(f"**الوقت المباشر:** {now.strftime('%I:%M %p')}")

sched_query = f"""SELECT start_time, end_time FROM user_shift_schedule WHERE date = '{str(today_date)}' AND username = '{current_user}'"""
sched_df = conn.query(sched_query, ttl=0)

if not sched_df.empty:
    start_str = sched_df.iloc[0]['start_time']
    end_str = sched_df.iloc[0]['end_time']
    shift_start_time = datetime.strptime(start_str, "%H:%M").time()
    shift_end_time = datetime.strptime(end_str, "%H:%M").time()
    schedule_status = "✅ مجدول لك اليوم"
else:
    shift_start_time = datetime.strptime("09:00", "%H:%M").time()
    shift_end_time = datetime.strptime("19:00", "%H:%M").time()
    schedule_status = "⚠️ افتراضي (غير مجدول)"

st.sidebar.caption(schedule_status)

# ==========================================
# 5. نافذة المدخلات الجانبية
# ==========================================
with st.sidebar.form("sales_form", clear_on_submit=False):
    st.header("📝 تسجيل المبيعات")
    input_date = st.date_input("تاريخ الشيفت", value=today_date)
    input_day = input_date.strftime("%A")
    time_slot = st.selectbox("الفترة الزمنية", ["الفترة الأولى (أول 3 ساعات)", "الفترة الثانية (ثاني 3 ساعات)", "الفترة الثالثة (آخر 3 ساعات)"])
    sales_value = st.number_input("المبيعات (د.ك)", min_value=0.0, step=10.0, format="%.2f")
    if st.form_submit_button("💾 حفظ البيانات", use_container_width=True):
        with conn.session as s:
            s.execute(text("INSERT INTO sales_data (date, day, time_slot, sales, entered_by) VALUES (:date, :day, :slot, :sales, :user)"),
                      {"date": str(input_date), "day": input_day, "slot": time_slot, "sales": sales_value, "user": current_user})
            s.commit()
        st.success("✅ تم التسجيل بنجاح في ملفك الشخصي!")

with st.sidebar.expander("🎯 تعيين الهدف البيعي الخاص بك"):
    daily_target_input = st.number_input("الهدف البيعي (د.ك)", min_value=0.0, value=load_target(today_date, current_user), step=50.0)
    if st.button("حفظ الهدف الخاص بي", use_container_width=True):
        with conn.session as s:
            s.execute(text("INSERT INTO user_daily_targets (date, username, target) VALUES (:date, :user, :target) ON CONFLICT (date, username) DO UPDATE SET target = EXCLUDED.target"),
                      {"date": str(today_date), "user": current_user, "target": daily_target_input})
            s.commit()
        st.success("تم التحديث!")
        st.rerun()

df = load_data(current_user)
today_target = load_target(today_date, current_user)

# ==========================================
# 6. الشاشة الرئيسية
# ==========================================
st.title("📊 نظام تحليل وإدارة المبيعات")
st.markdown("---")

shift_start_dt = cairo_tz.localize(datetime.combine(today_date, shift_start_time))
shift_end_dt = cairo_tz.localize(datetime.combine(today_date, shift_end_time))
if shift_end_dt <= shift_start_dt:
    shift_end_dt += timedelta(days=1) 

total_shift_hours = (shift_end_dt - shift_start_dt).total_seconds() / 3600.0

if now < shift_start_dt:
    remaining_hours, shift_status = total_shift_hours, "لم يبدأ الشيفت"
elif now > shift_end_dt:
    remaining_hours, shift_status = 0.0, "انتهى الشيفت"
else:
    remaining_hours = total_shift_hours - ((now - shift_start_dt).total_seconds() / 3600.0)
    shift_status = "جاري الآن"

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date']).dt.date

tab1, tab2, tab3, tab4 = st.tabs(["📈 المتابعة المباشرة", "📅 جدول مواعيد العمل الخاص بي", "🧠 التحليلات الاستراتيجية", "⚙️ التقارير الشخصية"])

# --- التبويب الأول ---
with tab1:
    today_sales = df[df['Date'] == today_date]['Sales'].sum() if not df.empty else 0
    achievement_perc = (today_sales / today_target * 100) if today_target > 0 else 0
    c1, c2, c3 = st.columns(3)
    ach_color = "#00E676" if achievement_perc >= 100 else ("#FFB822" if achievement_perc >= 75 else "#F64E60")
    
    with c1: st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">مبيعاتك اليوم</div><div class="kpi-value">{today_sales:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">هدفك (Target)</div><div class="kpi-value">{today_target:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="custom-kpi-card" style="border-right-color: {ach_color};"><div class="kpi-title">نسبة الإنجاز</div><div class="kpi-value" style="color: {ach_color};">{achievement_perc:,.1f}%</div></div>', unsafe_allow_html=True)
    
    g1, g2 = st.columns(2)
    with g1:
        time_color = "#FF4B4B" if remaining_hours < 2 else "#00E676"
        fig_time = go.Figure(go.Indicator(
            mode="gauge+number", value=remaining_hours, title={'text': "⏳ ساعات العمل المتبقية", 'font': {'color': 'white'}},
            number={'suffix': " ساعة", 'font': {'color': 'white'}, 'valueformat': ".1f"},
            gauge={'axis': {'range': [0, total_shift_hours], 'tickwidth': 1, 'tickcolor': "white"}, 'bar': {'color': time_color}, 'bgcolor': "rgba(255,255,255,0.05)"}
        ))
        fig_time.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(t=50, b=0))
        st.plotly_chart(fig_time, use_container_width=True)
        
    with g2:
        fig_target = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=today_sales, title={'text': "🎯 مسارك نحو الهدف", 'font': {'color': 'white'}},
            delta={'reference': today_target, 'position': "top", 'font': {'color': 'white'}}, number={'suffix': " د.ك", 'font': {'color': 'white'}},
            gauge={'axis': {'range': [0, max(today_target, today_sales) * 1.2 if today_target > 0 else 100], 'tickwidth': 1, 'tickcolor': "white"},
                   'bar': {'color': ach_color}, 'bgcolor': "rgba(255,255,255,0.05)",
                   'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': today_target}}
        ))
        fig_target.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(t=50, b=0))
        st.plotly_chart(fig_target, use_container_width=True)

    if not df.empty and not df[df['Date'] == today_date].empty:
        df_today = df[df['Date'] == today_date]
        fig_area = px.area(df_today, x="Time_Slot", y="Sales", markers=True, title="منحنى التدفق الزمني لمبيعاتك اليوم")
        fig_area.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=350)
        fig_area.update_traces(line_color='#3699ff', fillcolor='rgba(54, 153, 255, 0.2)')
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("لم يتم تسجيل مبيعات لليوم الحالي بعد.")

# --- التبويب الثاني ---
with tab2:
    st.markdown("### 📅 إعداد جدول مواعيدك")
    with st.form("schedule_form"):
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1: sched_date = st.date_input("تاريخ الشيفت المستهدف")
        with col_s2: sched_start = st.time_input("وقت البداية", value=datetime.strptime("09:00", "%H:%M").time())
        with col_s3: sched_end = st.time_input("وقت النهاية", value=datetime.strptime("19:00", "%H:%M").time())
        if st.form_submit_button("حفظ الموعد 💾", type="primary"):
            start_str = sched_start.strftime("%H:%M")
            end_str = sched_end.strftime("%H:%M")
            with conn.session as s:
                s.execute(text("INSERT INTO user_shift_schedule (date, username, start_time, end_time) VALUES (:date, :user, :start, :end) ON CONFLICT (date, username) DO UPDATE SET start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time"),
                          {"date": str(sched_date), "user": current_user, "start": start_str, "end": end_str})
                s.commit()
            st.success("تم تحديث جدولك الشخصي بنجاح!")
            st.rerun()
            
    st.markdown("---")
    st.markdown("#### 📆 شيفتاتك المبرمجة")
    all_sched_query = f"""SELECT date AS "التاريخ", start_time AS "وقت البداية", end_time AS "وقت النهاية" FROM user_shift_schedule WHERE username = '{current_user}' ORDER BY date DESC"""
    all_schedules = conn.query(all_sched_query, ttl=0)
    if not all_schedules.empty:
        st.dataframe(all_schedules, use_container_width=True, hide_index=True)
    else:
        st.info("جدولك فارغ حالياً.")

# --- التبويب الثالث ---
with tab3:
    if not df.empty:
        col_heat, col_trend = st.columns(2)
        with col_heat:
            fig_heat = px.density_heatmap(df, x="Time_Slot", y="Date", z="Sales", histfunc="sum", title="خريطة كثافة أدائك الشخصي")
            fig_heat.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig_heat, use_container_width=True)
        with col_trend:
            df_daily = df.groupby('Date')['Sales'].sum().reset_index()
            fig_trend = px.bar(df_daily, x="Date", y="Sales", text="Sales", title="مقارنة أدائك اليومي")
            fig_trend.update_traces(marker_color='#3699ff', texttemplate='%{text:,.0f}')
            fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.warning("التحليلات تتطلب بيانات مدخلة.")

# --- التبويب الرابع ---
with tab4:
    if not df.empty:
        st.markdown("### 📥 استخراج تقرير مبيعاتك الشخصية (Excel)")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            display_df = df.rename(columns={"Date": "التاريخ", "Day": "اليوم", "Time_Slot": "الفترة", "Sales": "المبيعات (د.ك)"})
            display_df.to_excel(writer, index=False, sheet_name=f'Sales {current_user}')
        
        st.download_button("📊 تحميل بياناتي كملف Excel", data=buffer.getvalue(), file_name=f"Sales_{current_user}_{today_date}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        
        st.markdown("---")
        st.markdown("#### 📋 سجل قيودك")
        st.dataframe(display_df.style.format({"المبيعات (د.ك)": "{:.2f}"}), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 🗑️ تصحيح قيد خاطئ")
        c1, c2, c3 = st.columns(3)
        with c1: del_date = st.selectbox("تاريخ القيد", df['Date'].unique())
        with c2: del_slot = st.selectbox("الفترة المستهدفة", df[df['Date'] == del_date]['Time_Slot'].unique())
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("حذف قيدي", type="secondary", use_container_width=True):
                with conn.session as s:
                    s.execute(text("DELETE FROM sales_data WHERE date = :date AND time_slot = :slot AND entered_by = :user"), 
                              {"date": str(del_date), "slot": del_slot, "user": current_user})
                    s.commit()
                st.success("تم الحذف بنجاح!")
                st.rerun()