import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text

# إعداد الصفحة
st.set_page_config(page_title="داش بورد المبيعات المتقدم", page_icon="📈", layout="wide")

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
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. الاتصال بقاعدة البيانات السحابية (Neon)
# ==========================================
# ستقوم Streamlit بقراءة الرابط السري الذي وضعته في الموقع تلقائياً
conn = st.connection("postgresql", type="sql")

# إنشاء الجدول في السحابة إذا لم يكن موجوداً
with conn.session as s:
    s.execute(text('''
        CREATE TABLE IF NOT EXISTS sales_data (
            id SERIAL PRIMARY KEY,
            date DATE,
            day VARCHAR(50),
            time_slot VARCHAR(100),
            sales DOUBLE PRECISION
        )
    '''))
    s.commit()

# دالة لجلب البيانات
def load_data():
    return conn.query('SELECT date AS "Date", day AS "Day", time_slot AS "Time_Slot", sales AS "Sales" FROM sales_data ORDER BY date, time_slot', ttl=0)

# ==========================================
# 3. إعدادات الوقت الفعلي
# ==========================================
cairo_tz = pytz.timezone('Africa/Cairo')
now = datetime.now(cairo_tz)
today_date = now.date()

st.sidebar.header("⏱️ لوحة التحكم الزمنية")

if st.sidebar.button("🔄 تحديث الوقت والبيانات الآن", use_container_width=True):
    st.rerun()

st.sidebar.info(f"**الوقت المباشر:** {now.strftime('%I:%M %p')}")
shift_start_time = st.sidebar.time_input("⏰ وقت بدء الشيفت", value=datetime.strptime("09:00", "%H:%M").time())

# ==========================================
# 4. نافذة المدخلات
# ==========================================
with st.sidebar.form("sales_form", clear_on_submit=False):
    st.header("📝 تسجيل المبيعات")
    st.markdown("---")
    
    input_date = st.date_input("تاريخ الشيفت", value=today_date)
    input_day = input_date.strftime("%A")
    time_slot = st.selectbox("الفترة الزمنية", ["الفترة الأولى (أول 3 ساعات)", "الفترة الثانية (ثاني 3 ساعات)", "الفترة الثالثة (آخر 3 ساعات)"])
    sales_value = st.number_input("المبيعات (د.ك)", min_value=0.0, step=10.0, format="%.2f")
    
    submit_button = st.form_submit_button("💾 حفظ البيانات في السحابة", use_container_width=True)
    
    if submit_button:
        with conn.session as s:
            s.execute(
                text("INSERT INTO sales_data (date, day, time_slot, sales) VALUES (:date, :day, :slot, :sales)"),
                {"date": input_date, "day": input_day, "slot": time_slot, "sales": sales_value}
            )
            s.commit()
        st.success("✅ تم حفظ البيانات في السحابة الدائمة بنجاح!")

df = load_data()

# ==========================================
# 5. الشاشة الرئيسية والتحليلات
# ==========================================
st.title("📊 مركز تحليل مبيعات الشيفت السحابي")
st.markdown("---")

shift_start_dt = cairo_tz.localize(datetime.combine(today_date, shift_start_time))
shift_end_dt = shift_start_dt + timedelta(hours=10)

if now < shift_start_dt:
    remaining_hours, shift_status, bar_color = 10.0, "لم يبدأ الشيفت", "#1f77b4"
elif now > shift_end_dt:
    remaining_hours, shift_status, bar_color = 0.0, "انتهى الشيفت", "#f64e60"
else:
    elapsed = now - shift_start_dt
    remaining_hours = 10.0 - (elapsed.total_seconds() / 3600.0)
    shift_status = "جاري الآن"
    bar_color = "#FF4B4B" if remaining_hours < 2 else "#00E676"

tab1, tab2, tab3 = st.tabs(["📈 المتابعة المباشرة", "🧠 التحليلات الاستراتيجية", "⚙️ إدارة البيانات السحابية"])

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date']).dt.date

# --- التبويب الأول ---
with tab1:
    total_sales = df['Sales'].sum() if not df.empty else 0
    today_sales = df[df['Date'] == today_date]['Sales'].sum() if not df.empty else 0

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">مبيعات اليوم الفعلي</div><div class="kpi-value">{today_sales:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="custom-kpi-card"><div class="kpi-title">إجمالي المبيعات التراكمية</div><div class="kpi-value">{total_sales:,.2f} <span>د.ك</span></div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="custom-kpi-card" style="border-right-color: {bar_color};"><div class="kpi-title">حالة الشيفت</div><div class="kpi-value" style="font-size: 1.8rem; padding-top:8px;">{shift_status}</div></div>', unsafe_allow_html=True)
    
    col_chart1, col_chart2 = st.columns([1, 1.5])
    with col_chart1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=remaining_hours,
            title={'text': "ساعات العمل المتبقية", 'font': {'color': 'white'}},
            number={'suffix': " ساعة", 'font': {'color': 'white'}},
            gauge={'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "white"}, 'bar': {'color': bar_color}, 'bgcolor': "rgba(255,255,255,0.05)"}
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=350, margin=dict(t=30, b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_chart2:
        if not df.empty and not df[df['Date'] == today_date].empty:
            df_today = df[df['Date'] == today_date]
            fig_area = px.area(df_today, x="Time_Slot", y="Sales", markers=True, title="التدفق الزمني لمبيعات اليوم")
            fig_area.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=350)
            fig_area.update_traces(line_color='#00E676', fillcolor='rgba(0, 230, 118, 0.2)')
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("لم يتم تسجيل مبيعات لليوم الحالي بعد.")

# --- التبويب الثاني ---
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
            elif not df_today.empty and len(df_today) == 3:
                st.markdown(f"<div class='insight-box'>تم تسجيل كافة فترات اليوم. عملية التحليل مغلقة لهذا الشيفت.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='insight-box'>بانتظار المدخلات الأولى لليوم لبناء توقعات الإغلاق.</div>", unsafe_allow_html=True)
    else:
        st.warning("التحليلات تتطلب إدخال بيانات مسبقة.")

# --- التبويب الثالث ---
with tab3:
    if not df.empty:
        display_df = df.rename(columns={"Date": "التاريخ", "Day": "اليوم", "Time_Slot": "الفترة", "Sales": "المبيعات (د.ك)"})
        st.dataframe(display_df.style.format({"المبيعات (د.ك)": "{:.2f}"}), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 🗑️ أداة تصحيح القيود السحابية")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            del_date = st.selectbox("تاريخ القيد", df['Date'].unique())
        with c2:
            del_slot = st.selectbox("الفترة المستهدفة", df[df['Date'] == del_date]['Time_Slot'].unique())
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("حذف القيد", type="primary", use_container_width=True):
                with conn.session as s:
                    s.execute(text("DELETE FROM sales_data WHERE date = :date AND time_slot = :slot"), {"date": del_date, "slot": del_slot})
                    s.commit()
                st.success("تم الحذف من السحابة بنجاح!")
                st.rerun()