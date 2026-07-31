import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
import io

# إعداد الصفحة
st.set_page_config(page_title="نظام إدارة المبيعات المتقدم", page_icon="📈", layout="wide")

# ==========================================
# 1. تصميم CSS الاحترافي (RTL)
# ==========================================
st.markdown("""
    <style>
    .main .block-container { direction: rtl; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .custom-kpi-card { background: linear-gradient(145deg, #1e1e2d, #26273b); border-right: 5px solid #00E676; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px; text-align: right; }
    .kpi-title { color: #a1a5b7; font-size: 1.1rem; margin-bottom: 8px; font-weight: 500; }
    .kpi-value { color: #ffffff; font-size: 2.2rem; font-weight: bold; }
    .kpi-value span { color: #00E676; font-size: 1.2rem; margin-right: 5px; }
    .insight-box { background-color: #232334; padding: 20px; border-radius: 8px; border-right: 4px solid #3699ff; margin-bottom: 15px; color: #e4e6ef; line-height: 1.6; text-align: right; direction: rtl;}
    .login-box { max-width: 400px; margin: 100px auto; padding: 40px; background-color: #1e1e2d; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: center; }
    
    /* تنسيق أزرار التبويبات */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e1e2d; border-radius: 8px 8px 0 0; padding: 10px 20px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. نظام تسجيل الدخول
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.title("🔐 تسجيل الدخول")
    st.markdown("---")
    user_input = st.text_input("اسم المستخدم")
    pass_input = st.text_input("كلمة المرور", type="password")
    if st.button("دخول للنظام", use_container_width=True, type="primary"):
        if "users" in st.secrets and user_input in st.secrets["users"]:
            if st.secrets["users"][user_input] == pass_input:
                st.session_state.logged_in = True
                st.session_state.username = user_input
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
        else:
            st.error("❌ اسم المستخدم غير مسجل")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. الاتصال بقاعدة البيانات وإنشاء الجداول
# ==========================================
conn = st.connection("postgresql", type="sql")

with conn.session as s:
    s.execute(text('''
        CREATE TABLE IF NOT EXISTS sales_data (
            id SERIAL PRIMARY KEY, date DATE, day VARCHAR(50),
            time_slot VARCHAR(100), sales DOUBLE PRECISION, entered_by VARCHAR(50)
        )
    '''))
    s.execute(text("ALTER TABLE sales_data ADD COLUMN IF NOT EXISTS entered_by VARCHAR(50);"))
    s.execute(text('''
        CREATE TABLE IF NOT EXISTS daily_targets (
            date DATE PRIMARY KEY, target DOUBLE PRECISION
        )
    '''))
    # جدول مواعيد الشيفتات الجديد (Calendar)
    s.execute(text('''
        CREATE TABLE IF NOT EXISTS shift_schedule (
            date DATE PRIMARY KEY, start_time VARCHAR(10), end_time VARCHAR(10)
        )
    '''))
    s.commit()

def load_data():
    return conn.query('SELECT date AS "Date", day AS "Day", time_slot AS "Time_Slot", sales AS "Sales", entered_by AS "User" FROM sales_data ORDER BY date, time_slot', ttl=0)

def load_target(d):
    target_df = conn.query(f"SELECT target FROM daily_targets WHERE date = '{d}'", ttl=0)
    return target_df.iloc[0]['target'] if not target_df.empty else 0.0

# ==========================================
# 4. إعدادات الوقت والجدولة الذكية
# ==========================================
cairo_tz = pytz.timezone('Africa/Cairo')
now = datetime.now(cairo_tz)
today_date = now.date()

st.sidebar.markdown(f"👤 مرحباً، **{st.session_state.username}**")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⏱️ لوحة التحكم الزمنية")
if st.sidebar.button("🔄 تحديث الوقت والبيانات", use_container_width=True):
    st.rerun()
st.sidebar.info(f"**الوقت المباشر:** {now.strftime('%I:%M %p')}")

# -- النظام الذكي لحساب الشيفت --
sched_df = conn.query(f"SELECT start_time, end_time FROM shift_schedule WHERE date = '{today_date}'", ttl=0)
if not sched_df.empty:
    start_str = sched_df.iloc[0]['start_time']
    end_str = sched_df.iloc[0]['end_time']
    shift_start_time = datetime.strptime(start_str, "%H:%M").time()
    shift_end_time = datetime.strptime(end_str, "%H:%M").time()
    schedule_status = "✅ مبرمج تلقائياً من الجدول"
else:
    # افتراضي إذا لم يتم وضع جدول لليوم
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
                      {"date": input_date, "day": input_day, "slot": time_slot, "sales": sales_value, "user": st.session_state.username})
            s.commit()
        st.success("✅ تم التسجيل بنجاح!")

with st.sidebar.expander("🎯 تعيين هدف اليوم (Target)"):
    daily_target_input = st.number_input("الهدف البيعي (د.ك)", min_value=0.0, value=load_target(today_date), step=50.0)
    if st.button("حفظ الهدف", use_container_width=True):
        with conn.session as s:
            s.execute(text("INSERT INTO daily_targets (date, target) VALUES (:date, :target) ON CONFLICT (date) DO UPDATE SET target = EXCLUDED.target"),
                      {"date": today_date, "target": daily_target_input})
            s.commit()
        st.success("تم تحديث الهدف!")
        st.rerun()

df = load_data()
today_target = load_target(today_date)

# ==========================================
# 6. الشاشة الرئيسية
# ==========================================
st.title("📊 نظام تحليل وإدارة المبيعات")
st.markdown("---")

# حسابات الوقت الدقيقة
shift_start_dt = cairo_tz.localize(datetime.combine(today_date, shift_start_time))
shift_end_dt = cairo_tz.localize(datetime.combine(today_date, shift_end_time))
if shift_end_dt <= shift_start_dt:
    shift_end_dt += timedelta(days=1) # إذا كان الشيفت يعبر منتصف الليل

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

# التبويبات (تم إضافة تبويب الجدول)
tab1, tab2, tab3, tab4 = st.tabs(["📈 المتابعة المباشرة", "📅 جدول مواعيد العمل", "🧠 التحليلات الاستراتيجية", "⚙️ التقارير والإدارة"])

# --- التبويب الأول: المتابعة المباشرة ---
with tab1:
    today_sales = df[df['Date'] == today_date]['Sales'].sum() if not df.empty else 0
    achievement_perc = (today_sales / today_target * 100) if today_target > 0 else 0

    c1, c2, c3 = st.columns(3)
    ach_color = "#00E676" if achievement_perc >= 100 else ("#FFB822" if achievement_perc >= 75 else "#F64E60")
    
    with c1: st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">مبيعات اليوم الفعلي</div><div class="kpi-value">{today_sales:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">الهدف اليومي (Target)</div><div class="kpi-value">{today_target:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="custom-kpi-card" style="border-right-color: {ach_color};"><div class="kpi-title">نسبة تحقيق الهدف</div><div class="kpi-value" style="color: {ach_color};">{achievement_perc:,.1f}%</div></div>', unsafe_allow_html=True)
    
    # صف الجرافس: مؤشر الوقت + مؤشر الهدف بجوار بعضهما
    g1, g2 = st.columns(2)
    with g1:
        time_color = "#FF4B4B" if remaining_hours < 2 else "#00E676"
        fig_time = go.Figure(go.Indicator(
            mode="gauge+number", value=remaining_hours,
            title={'text': "⏳ ساعات العمل المتبقية", 'font': {'color': 'white'}},
            number={'suffix': " ساعة", 'font': {'color': 'white'}, 'valueformat': ".1f"},
            gauge={'axis': {'range': [0, total_shift_hours], 'tickwidth': 1, 'tickcolor': "white"}, 'bar': {'color': time_color}, 'bgcolor': "rgba(255,255,255,0.05)"}
        ))
        fig_time.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(t=50, b=0))
        st.plotly_chart(fig_time, use_container_width=True)
        
    with g2:
        fig_target = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=today_sales,
            title={'text': "🎯 مسار تحقيق التارجت", 'font': {'color': 'white'}},
            delta={'reference': today_target, 'position': "top", 'font': {'color': 'white'}},
            number={'suffix': " د.ك", 'font': {'color': 'white'}},
            gauge={'axis': {'range': [0, max(today_target, today_sales) * 1.2 if today_target > 0 else 100], 'tickwidth': 1, 'tickcolor': "white"},
                   'bar': {'color': ach_color}, 'bgcolor': "rgba(255,255,255,0.05)",
                   'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': today_target}}
        ))
        fig_target.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(t=50, b=0))
        st.plotly_chart(fig_target, use_container_width=True)

    # الرسم البياني الخطي أسفلهما
    if not df.empty and not df[df['Date'] == today_date].empty:
        df_today = df[df['Date'] == today_date]
        fig_area = px.area(df_today, x="Time_Slot", y="Sales", markers=True, title="التدفق الزمني لمبيعات اليوم")
        fig_area.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=350)
        fig_area.update_traces(line_color='#3699ff', fillcolor='rgba(54, 153, 255, 0.2)')
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("لم يتم تسجيل مبيعات لليوم الحالي بعد.")

# --- التبويب الثاني: جدول مواعيد العمل (Calendar) ---
with tab2:
    st.markdown("### 📅 إعداد جدول مواعيد الشيفتات")
    st.markdown("قم بتحديد تاريخ اليوم أو الأيام القادمة، وحدد وقت بداية ونهاية الشيفت. سيقوم النظام تلقائياً بضبط العداد التنازلي بناءً على هذا الجدول.")
    
    with st.form("schedule_form"):
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1: sched_date = st.date_input("تاريخ الشيفت المستهدف")
        with col_s2: sched_start = st.time_input("وقت البداية", value=datetime.strptime("09:00", "%H:%M").time())
        with col_s3: sched_end = st.time_input("وقت النهاية", value=datetime.strptime("19:00", "%H:%M").time())
        
        if st.form_submit_button("حفظ الموعد في الجدول 💾", type="primary"):
            start_str = sched_start.strftime("%H:%M")
            end_str = sched_end.strftime("%H:%M")
            with conn.session as s:
                s.execute(text("INSERT INTO shift_schedule (date, start_time, end_time) VALUES (:date, :start, :end) ON CONFLICT (date) DO UPDATE SET start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time"),
                          {"date": sched_date, "start": start_str, "end": end_str})
                s.commit()
            st.success("تم تحديث الجدول بنجاح! سيتم تطبيق الأوقات تلقائياً في هذا التاريخ.")
            st.rerun()
            
    st.markdown("---")
    st.markdown("#### 📆 الشيفتات المبرمجة سابقاً")
    all_schedules = conn.query('SELECT date AS "التاريخ", start_time AS "وقت البداية", end_time AS "وقت النهاية" FROM shift_schedule ORDER BY date DESC', ttl=0)
    if not all_schedules.empty:
        st.dataframe(all_schedules, use_container_width=True, hide_index=True)
    else:
        st.info("الجدول فارغ حالياً.")

# --- التبويب الثالث: تحليلات متقدمة ---
with tab3:
    if not df.empty:
        col_heat, col_trend = st.columns(2)
        with col_heat:
            fig_heat = px.density_heatmap(df, x="Time_Slot", y="Date", z="Sales", histfunc="sum", title="خريطة الكثافة: تركز المبيعات حسب الأيام والفترات")
            fig_heat.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig_heat, use_container_width=True)
        with col_trend:
            df_daily = df.groupby('Date')['Sales'].sum().reset_index()
            fig_trend = px.bar(df_daily, x="Date", y="Sales", text="Sales", title="مقارنة الأداء الإجمالي للأيام")
            fig_trend.update_traces(marker_color='#3699ff', texttemplate='%{text:,.0f}')
            fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.warning("التحليلات تتطلب بيانات مدخلة.")

# --- التبويب الرابع: التقارير والإدارة ---
with tab4:
    if not df.empty:
        st.markdown("### 📥 استخراج تقرير المبيعات (Excel)")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            display_df = df.rename(columns={"Date": "التاريخ", "Day": "اليوم", "Time_Slot": "الفترة", "Sales": "المبيعات (د.ك)", "User": "تم الإدخال بواسطة"})
            display_df.to_excel(writer, index=False, sheet_name='Sales Data')
        
        st.download_button("📊 تحميل البيانات كملف Excel", data=buffer.getvalue(), file_name=f"Sales_Report_{today_date}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        
        st.markdown("---")
        st.markdown("#### 📋 سجل البيانات المدخلة")
        st.dataframe(display_df.style.format({"المبيعات (د.ك)": "{:.2f}"}), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 🗑️ أداة تصحيح القيود")
        c1, c2, c3 = st.columns(3)
        with c1: del_date = st.selectbox("تاريخ القيد", df['Date'].unique())
        with c2: del_slot = st.selectbox("الفترة المستهدفة", df[df['Date'] == del_date]['Time_Slot'].unique())
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("حذف القيد", type="secondary", use_container_width=True):
                with conn.session as s:
                    s.execute(text("DELETE FROM sales_data WHERE date = :date AND time_slot = :slot"), {"date": del_date, "slot": del_slot})
                    s.commit()
                st.success("تم الحذف بنجاح!")
                st.rerun()