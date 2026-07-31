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
# 1. تصميم CSS
# ==========================================
st.markdown("""
    <style>
    .main .block-container { direction: rtl; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .custom-kpi-card { background: linear-gradient(145deg, #1e1e2d, #26273b); border-right: 5px solid #00E676; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-bottom: 20px; text-align: right; }
    .kpi-title { color: #a1a5b7; font-size: 1.1rem; margin-bottom: 8px; font-weight: 500; }
    .kpi-value { color: #ffffff; font-size: 2.2rem; font-weight: bold; }
    .kpi-value span { color: #00E676; font-size: 1.2rem; margin-right: 5px; }
    .insight-box { background-color: #232334; padding: 20px; border-radius: 8px; border-right: 4px solid #3699ff; margin-bottom: 15px; color: #e4e6ef; line-height: 1.6; text-align: right; direction: rtl;}
    
    /* تصميم شاشة تسجيل الدخول */
    .login-box { max-width: 400px; margin: 100px auto; padding: 40px; background-color: #1e1e2d; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. نظام تسجيل الدخول الآمن المتعدد
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.title("🔐 تسجيل الدخول")
    st.markdown("---")
    
    # واجهة إدخال البيانات
    user_input = st.text_input("اسم المستخدم")
    pass_input = st.text_input("كلمة المرور", type="password")
    
    if st.button("دخول للنظام", use_container_width=True, type="primary"):
        # التحقق من البيانات الموجودة في secrets.toml
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
    st.stop() # إيقاف تحميل باقي الصفحة إذا لم يسجل دخوله

# ==========================================
# 3. الاتصال بقاعدة البيانات وإنشاء الجداول
# ==========================================
conn = st.connection("postgresql", type="sql")

with conn.session as s:
    # جدول المبيعات
    s.execute(text('''
        CREATE TABLE IF NOT EXISTS sales_data (
            id SERIAL PRIMARY KEY,
            date DATE,
            day VARCHAR(50),
            time_slot VARCHAR(100),
            sales DOUBLE PRECISION,
            entered_by VARCHAR(50)
        )
    '''))
    
    # إصلاح الخطأ: إضافة العمود الجديد للجدول القديم بأمان
    s.execute(text("ALTER TABLE sales_data ADD COLUMN IF NOT EXISTS entered_by VARCHAR(50);"))
    
    # جدول الأهداف (Targets)
    s.execute(text('''
        CREATE TABLE IF NOT EXISTS daily_targets (
            date DATE PRIMARY KEY,
            target DOUBLE PRECISION
        )
    '''))
    s.commit()

def load_data():
    return conn.query('SELECT date AS "Date", day AS "Day", time_slot AS "Time_Slot", sales AS "Sales", entered_by AS "User" FROM sales_data ORDER BY date, time_slot', ttl=0)

def load_target(d):
    target_df = conn.query(f"SELECT target FROM daily_targets WHERE date = '{d}'", ttl=0)
    return target_df.iloc[0]['target'] if not target_df.empty else 0.0

# ==========================================
# 4. إعدادات الوقت والمدخلات
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

shift_start_time = st.sidebar.time_input("⏰ وقت بدء الشيفت", value=datetime.strptime("09:00", "%H:%M").time())

with st.sidebar.form("sales_form", clear_on_submit=False):
    st.header("📝 تسجيل المبيعات")
    input_date = st.date_input("تاريخ الشيفت", value=today_date)
    input_day = input_date.strftime("%A")
    time_slot = st.selectbox("الفترة الزمنية", ["الفترة الأولى (أول 3 ساعات)", "الفترة الثانية (ثاني 3 ساعات)", "الفترة الثالثة (آخر 3 ساعات)"])
    sales_value = st.number_input("المبيعات (د.ك)", min_value=0.0, step=10.0, format="%.2f")
    
    if st.form_submit_button("💾 حفظ البيانات", use_container_width=True):
        with conn.session as s:
            s.execute(
                text("INSERT INTO sales_data (date, day, time_slot, sales, entered_by) VALUES (:date, :day, :slot, :sales, :user)"),
                {"date": input_date, "day": input_day, "slot": time_slot, "sales": sales_value, "user": st.session_state.username}
            )
            s.commit()
        st.success("✅ تم التسجيل بنجاح!")

# إدخال الهدف اليومي (Target)
with st.sidebar.expander("🎯 تعيين هدف اليوم (Target)"):
    daily_target_input = st.number_input("الهدف البيعي (د.ك)", min_value=0.0, value=load_target(today_date), step=50.0)
    if st.button("حفظ الهدف", use_container_width=True):
        with conn.session as s:
            s.execute(
                text("INSERT INTO daily_targets (date, target) VALUES (:date, :target) ON CONFLICT (date) DO UPDATE SET target = EXCLUDED.target"),
                {"date": today_date, "target": daily_target_input}
            )
            s.commit()
        st.success("تم تحديث الهدف!")
        st.rerun()

df = load_data()
today_target = load_target(today_date)

# ==========================================
# 5. الشاشة الرئيسية والتحليلات
# ==========================================
st.title("📊 نظام تحليل وإدارة المبيعات")
st.markdown("---")

shift_start_dt = cairo_tz.localize(datetime.combine(today_date, shift_start_time))
shift_end_dt = shift_start_dt + timedelta(hours=10)
if now < shift_start_dt:
    remaining_hours, shift_status = 10.0, "لم يبدأ الشيفت"
elif now > shift_end_dt:
    remaining_hours, shift_status = 0.0, "انتهى الشيفت"
else:
    remaining_hours = 10.0 - ((now - shift_start_dt).total_seconds() / 3600.0)
    shift_status = "جاري الآن"

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date']).dt.date

tab1, tab2, tab3 = st.tabs(["📈 المتابعة والأهداف", "🧠 التحليلات الاستراتيجية", "⚙️ التقارير والإدارة"])

# --- التبويب الأول: المتابعة ونسبة تحقيق الهدف ---
with tab1:
    today_sales = df[df['Date'] == today_date]['Sales'].sum() if not df.empty else 0
    achievement_perc = (today_sales / today_target * 100) if today_target > 0 else 0

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">مبيعات اليوم الفعلي</div><div class="kpi-value">{today_sales:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">الهدف اليومي (Target)</div><div class="kpi-value">{today_target:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with col3:
        # تغيير لون نسبة الإنجاز حسب النسبة
        ach_color = "#00E676" if achievement_perc >= 100 else ("#FFB822" if achievement_perc >= 75 else "#F64E60")
        st.markdown(f'<div class="custom-kpi-card" style="border-right-color: {ach_color};"><div class="kpi-title">نسبة تحقيق الهدف</div><div class="kpi-value" style="color: {ach_color};">{achievement_perc:,.1f}%</div></div>', unsafe_allow_html=True)
    
    col_chart1, col_chart2 = st.columns([1, 1.5])
    with col_chart1:
        # مؤشر تحقيق الهدف (Gauge)
        fig_target = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=today_sales,
            title={'text': "مسار تحقيق التارجت", 'font': {'color': 'white'}},
            delta={'reference': today_target, 'position': "top", 'font': {'color': 'white'}},
            number={'suffix': " د.ك", 'font': {'color': 'white'}},
            gauge={
                'axis': {'range': [0, max(today_target, today_sales) * 1.2 if today_target > 0 else 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': ach_color},
                'bgcolor': "rgba(255,255,255,0.05)",
                'steps': [
                    {'range': [0, today_target*0.5], 'color': "rgba(246, 78, 96, 0.2)"},
                    {'range': [today_target*0.5, today_target*0.9], 'color': "rgba(255, 184, 34, 0.2)"},
                    {'range': [today_target*0.9, today_target*2], 'color': "rgba(0, 230, 118, 0.2)"}],
                'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': today_target}
            }
        ))
        fig_target.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=350, margin=dict(t=50, b=0))
        st.plotly_chart(fig_target, use_container_width=True)

    with col_chart2:
        if not df.empty and not df[df['Date'] == today_date].empty:
            df_today = df[df['Date'] == today_date]
            fig_area = px.area(df_today, x="Time_Slot", y="Sales", markers=True, title="التدفق الزمني لمبيعات اليوم")
            fig_area.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=350)
            fig_area.update_traces(line_color='#00E676', fillcolor='rgba(0, 230, 118, 0.2)')
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("لم يتم تسجيل مبيعات لليوم الحالي بعد.")

# --- التبويب الثاني (تحليلات متقدمة) ---
with tab2:
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

        st.markdown("---")
        col_insight1, col_insight2 = st.columns(2)
        
        with col_insight1:
            df_slots = df.groupby('Time_Slot')['Sales'].sum().reset_index()
            best_slot = df_slots.loc[df_slots['Sales'].idxmax()]
            st.markdown(f"<div class='insight-box'><h4 style='color: #3699ff; margin-top:0;'>🎯 تحليل السلوك البيعي</h4>أظهرت البيانات التاريخية أن <b>{best_slot['Time_Slot']}</b> هي فترة الذروة، بإجمالي مبيعات بلغت <b>{best_slot['Sales']:,.2f} د.ك</b>.</div>", unsafe_allow_html=True)
            
        with col_insight2:
            df_today = df[df['Date'] == today_date]
            if not df_today.empty and len(df_today) < 3:
                avg_run_rate = df_today['Sales'].sum() / len(df_today)
                projected_sales = avg_run_rate * 3
                st.markdown(f"<div class='insight-box'><h4 style='color: #00E676; margin-top:0;'>📈 التوقع الخوارزمي للإغلاق</h4>من المتوقع أن يتم إغلاق شيفت اليوم بمبيعات تصل إلى <b>{projected_sales:,.2f} د.ك</b>.</div>", unsafe_allow_html=True)
            elif not df_today.empty and len(df_today) >= 3:
                st.markdown(f"<div class='insight-box'>تم تسجيل كافة فترات اليوم. عملية التحليل مغلقة لهذا الشيفت.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='insight-box'>بانتظار المدخلات الأولى لليوم لبناء توقعات الإغلاق.</div>", unsafe_allow_html=True)
    else:
        st.warning("التحليلات تتطلب بيانات مدخلة.")

# --- التبويب الثالث: استخراج التقارير وإدارة البيانات ---
with tab3:
    if not df.empty:
        st.markdown("### 📥 استخراج تقرير المبيعات (Excel)")
        
        # تحويل البيانات إلى Excel في الذاكرة
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            display_df = df.rename(columns={"Date": "التاريخ", "Day": "اليوم", "Time_Slot": "الفترة", "Sales": "المبيعات (د.ك)", "User": "تم الإدخال بواسطة"})
            display_df.to_excel(writer, index=False, sheet_name='Sales Data')
        
        # زر التحميل الفوري
        st.download_button(
            label="📊 تحميل البيانات كملف Excel",
            data=buffer.getvalue(),
            file_name=f"Sales_Report_{today_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        st.markdown("---")
        st.markdown("#### 📋 سجل البيانات المدخلة")
        st.dataframe(display_df.style.format({"المبيعات (د.ك)": "{:.2f}"}), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 🗑️ أداة تصحيح القيود")
        c1, c2, c3 = st.columns(3)
        with c1:
            del_date = st.selectbox("تاريخ القيد", df['Date'].unique())
        with c2:
            del_slot = st.selectbox("الفترة المستهدفة", df[df['Date'] == del_date]['Time_Slot'].unique())
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("حذف القيد", type="secondary", use_container_width=True):
                with conn.session as s:
                    s.execute(text("DELETE FROM sales_data WHERE date = :date AND time_slot = :slot"), {"date": del_date, "slot": del_slot})
                    s.commit()
                st.success("تم الحذف بنجاح!")
                st.rerun()