import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from datetime import datetime, timedelta
import pytz # لضبط المنطقة الزمنية

# إعداد الصفحة
st.set_page_config(page_title="داش بورد المبيعات المتقدم", page_icon="📈", layout="wide")

# ==========================================
# إصلاح تصميم CSS (دعم العربية بدون تخريب الجداول)
# ==========================================
st.markdown("""
    <style>
    /* محاذاة النصوص لليمين دون التأثير على بنية جداول البيانات */
    h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    /* تصميم البطاقات الذكية */
    div[data-testid="metric-container"] {
        background-color: #1a1a24;
        border: 1px solid #2e2e40;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        text-align: right;
        direction: rtl;
    }
    div[data-testid="metric-container"] > label {
        font-size: 1.1rem;
        color: #b0b0c0;
        margin-bottom: 10px;
    }
    div[data-testid="metric-container"] > div {
        font-size: 2.2rem;
        color: #00E676;
        font-weight: bold;
    }
    
    /* لوحات الاستنتاجات */
    .insight-box {
        background-color: #262730;
        padding: 20px;
        border-right: 5px solid #00E676;
        border-radius: 5px;
        margin-bottom: 15px;
        text-align: right;
        direction: rtl;
    }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "sales_dashboard.db"

# تهيئة قاعدة البيانات
with duckdb.connect(DB_FILE) as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales_data (
            Date DATE,
            Day VARCHAR,
            Time_Slot VARCHAR,
            Sales DOUBLE
        )
    ''')

def load_data():
    with duckdb.connect(DB_FILE) as conn:
        return conn.execute("SELECT * FROM sales_data ORDER BY Date, Time_Slot").df()

# ==========================================
# ضبط الوقت الفعلي (توقيت مصر/القاهرة)
# ==========================================
cairo_tz = pytz.timezone('Africa/Cairo')
now = datetime.now(cairo_tz)
today_date = now.date()

st.sidebar.header("⏱️ إعدادات الوقت والشيفت")
st.sidebar.info(f"**الوقت المباشر:** {now.strftime('%I:%M %p')}")

shift_start_time = st.sidebar.time_input("⏰ متى يبدأ الشيفت؟", value=datetime.strptime("09:00", "%H:%M").time())

# ==========================================
# 1. نافذة المدخلات
# ==========================================
with st.sidebar.form("sales_form", clear_on_submit=False):
    st.header("📝 إدخال بيانات البيع (د.ك)")
    st.markdown("---")
    
    input_date = st.date_input("تاريخ الشيفت", value=today_date)
    input_day = input_date.strftime("%A")
    
    time_slot = st.selectbox("الفترة الزمنية", 
                             [
                                 "الفترة الأولى (أول 3 ساعات)", 
                                 "الفترة الثانية (ثاني 3 ساعات)", 
                                 "الفترة الثالثة (آخر 3 ساعات)"
                             ])
    
    sales_value = st.number_input("قيمة المبيعات (د.ك)", min_value=0.0, step=10.0, format="%.2f")
    
    submit_button = st.form_submit_button("💾 تسجيل المبيعات", use_container_width=True)
    
    if submit_button:
        with duckdb.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO sales_data VALUES (?, ?, ?, ?)",
                [input_date, input_day, time_slot, sales_value]
            )
        st.success("✅ تم حفظ المبيعات بنجاح!")

df = load_data()

# ==========================================
# 2. الشاشة الرئيسية والتبويبات
# ==========================================
st.title("📊 لوحة تحكم المبيعات والتحليلات المتقدمة")
st.markdown("---")

shift_start_dt = cairo_tz.localize(datetime.combine(today_date, shift_start_time))
shift_end_dt = shift_start_dt + timedelta(hours=10)

if now < shift_start_dt:
    remaining_hours, shift_status, bar_color = 10.0, "لم يبدأ الشيفت بعد", "#1f77b4"
elif now > shift_end_dt:
    remaining_hours, shift_status, bar_color = 0.0, "انتهى الشيفت", "#333333"
else:
    elapsed = now - shift_start_dt
    remaining_hours = 10.0 - (elapsed.total_seconds() / 3600.0)
    shift_status = "الشيفت جاري الآن..."
    bar_color = "#FF4B4B" if remaining_hours < 2 else "#00E676"

tab1, tab2, tab3 = st.tabs(["📈 المتابعة المباشرة", "🧠 التحليلات والتنبؤات الذكية", "⚙️ إدارة وسجل البيانات"])

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date']).dt.date

# ---------------------------------------------------------
# التبويب الأول: المتابعة المباشرة
# ---------------------------------------------------------
with tab1:
    col1, col2, col3 = st.columns(3)
    total_sales = df['Sales'].sum() if not df.empty else 0
    today_sales = df[df['Date'] == today_date]['Sales'].sum() if not df.empty else 0

    col1.metric("مبيعات اليوم الفعلي", f"{today_sales:,.2f} د.ك")
    col2.metric("إجمالي المبيعات الشهرية", f"{total_sales:,.2f} د.ك")
    col3.metric("حالة الشيفت", shift_status)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_chart1, col_chart2 = st.columns([1, 1.5])
    with col_chart1:
        # عداد تنازلي للوقت
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = remaining_hours,
            title = {'text': "ساعات العمل المتبقية", 'font': {'size': 20, 'color': 'white'}},
            number = {'suffix': " ساعة", 'font': {'color': 'white'}, 'valueformat': ".1f"},
            gauge = {
                'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': bar_color},
                'bgcolor': "rgba(255,255,255,0.05)",
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=350, margin=dict(t=50, b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_chart2:
        if not df.empty and not df[df['Date'] == today_date].empty:
            df_today = df[df['Date'] == today_date]
            # رسم مساحي متراكم (Area Chart) لمعرفة وتيرة المبيعات
            fig_area = px.area(df_today, x="Time_Slot", y="Sales", markers=True, 
                               title="وتيرة المبيعات خلال شيفت اليوم (د.ك)")
            fig_area.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=350)
            fig_area.update_traces(line_color='#00E676', fillcolor='rgba(0, 230, 118, 0.2)')
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("لا توجد مبيعات مسجلة لليوم الحالي لرسم المؤشر.")

# ---------------------------------------------------------
# التبويب الثاني: التحليلات والتنبؤات
# ---------------------------------------------------------
with tab2:
    if not df.empty:
        col_insight1, col_insight2 = st.columns(2)
        
        # تحليل قوة الفترات الزمنية (Donut Chart)
        with col_insight1:
            df_slots = df.groupby('Time_Slot')['Sales'].sum().reset_index()
            fig_pie = px.pie(df_slots, values='Sales', names='Time_Slot', hole=0.4,
                             title="نسبة مساهمة كل فترة في إجمالي المبيعات",
                             color_discrete_sequence=px.colors.sequential.Tealgrn)
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        # قسم الاستنتاجات والتنبؤ (AI Logic)
        with col_insight2:
            st.markdown("<h3 style='text-align: right; direction: rtl;'>🧠 استنتاجات وتنبؤات الأداء</h3>", unsafe_allow_html=True)
            
            # 1. توقع إغلاق اليوم
            df_today = df[df['Date'] == today_date]
            if not df_today.empty and len(df_today) > 0 and len(df_today) < 3:
                avg_run_rate = df_today['Sales'].sum() / len(df_today)
                projected_sales = avg_run_rate * 3
                st.markdown(f"""
                <div class='insight-box'>
                    <strong>🎯 التنبؤ بإغلاق الشيفت:</strong><br>
                    بناءً على معدل المبيعات الحالي (Run-Rate)، من المتوقع أن تغلق شيفت اليوم بإجمالي 
                    <span style='color:#00E676; font-size:1.2em; font-weight:bold;'>{projected_sales:,.2f} د.ك</span>.
                </div>
                """, unsafe_allow_html=True)
            elif len(df_today) == 3:
                st.markdown(f"<div class='insight-box'><strong>🏁 تم إغلاق فترات اليوم بالكامل. إجمالي ممتاز!</strong></div>", unsafe_allow_html=True)

            # 2. أفضل فترة أداءً تاريخياً
            best_slot = df_slots.loc[df_slots['Sales'].idxmax()]
            st.markdown(f"""
            <div class='insight-box'>
                <strong>🔥 ذروة المبيعات:</strong><br>
                أثبتت البيانات أن <b>{best_slot['Time_Slot']}</b> هي الأفضل أداءً، 
                حيث ولّدت مبيعات بقيمة {best_slot['Sales']:,.2f} د.ك حتى الآن.
            </div>
            """, unsafe_allow_html=True)
            
            # 3. متوسط المبيعات اليومية
            df_daily_avg = df.groupby('Date')['Sales'].sum().mean()
            st.markdown(f"""
            <div class='insight-box'>
                <strong>📊 متوسط الأداء اليومي:</strong><br>
                يبلغ متوسط المبيعات اليومية خلال الأيام المسجلة حوالي {df_daily_avg:,.2f} د.ك.
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("يرجى إدخال البيانات أولاً لتفعيل محرك التحليلات والتنبؤات.")

# ---------------------------------------------------------
# التبويب الثالث: سجل وإدارة البيانات
# ---------------------------------------------------------
with tab3:
    if not df.empty:
        st.subheader("📋 سجل البيانات المدخلة")
        
        # ترجمة أسماء الأعمدة لظهور احترافي في الجدول بدون أخطاء التنسيق
        display_df = df.rename(columns={
            "Date": "التاريخ",
            "Day": "اليوم",
            "Time_Slot": "الفترة الزمنية",
            "Sales": "المبيعات (د.ك)"
        })
        
        st.dataframe(
            display_df.style.format({"المبيعات (د.ك)": "{:.2f} د.ك"}),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        st.subheader("🗑️ حذف بيانات مسجلة بالخطأ")
        
        del_col1, del_col2, del_col3 = st.columns(3)
        with del_col1:
            dates_list = df['Date'].unique()
            del_date = st.selectbox("اختر تاريخ القيد للحذف", dates_list)
        with del_col2:
            slots_list = df[df['Date'] == del_date]['Time_Slot'].unique()
            del_slot = st.selectbox("اختر الفترة للحذف", slots_list)
        with del_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("❌ حذف القيد المحدد", use_container_width=True):
                with duckdb.connect(DB_FILE) as conn:
                    conn.execute("DELETE FROM sales_data WHERE Date = ? AND Time_Slot = ?", [del_date, del_slot])
                st.success("تم الحذف بنجاح! جاري التحديث...")
                st.rerun()
    else:
        st.info("لا توجد بيانات متاحة لعرضها أو حذفها.")