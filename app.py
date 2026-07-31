import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from datetime import datetime, timedelta

# إعداد الصفحة
st.set_page_config(page_title="داش بورد المبيعات", page_icon="📊", layout="wide")

# تصميم CSS الاحترافي
st.markdown("""
    <style>
    * {
        direction: rtl;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    div[data-testid="metric-container"] > label {
        font-size: 1.1rem;
        color: #A0A0A0;
        margin-bottom: 10px;
    }
    div[data-testid="metric-container"] > div {
        font-size: 2rem;
        color: #4CAF50;
        font-weight: bold;
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
# إعدادات الوقت الفعلي والشيفت
# ==========================================
now = datetime.now()
today_date = now.date()

st.sidebar.header("⏱️ إعدادات الوقت والشيفت")
st.sidebar.info(f"**الوقت الحالي:** {now.strftime('%I:%M %p')}")

# تحديد وقت بداية الشيفت لحساب العد التنازلي
shift_start_time = st.sidebar.time_input("⏰ متى يبدأ الشيفت؟", value=datetime.strptime("09:00", "%H:%M").time())

# ==========================================
# 1. نافذة المدخلات
# ==========================================
with st.sidebar.form("sales_form", clear_on_submit=False):
    st.header("📝 إدخال بيانات البيع (د.ك)")
    st.markdown("---")
    
    # التاريخ مضبوط تلقائياً على تاريخ اليوم الفعلي
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
# 2. الشاشة الرئيسية والتحليل
# ==========================================
st.title("📊 لوحة تحكم المبيعات المباشرة")
st.markdown("---")

# حساب العد التنازلي للشيفت (10 ساعات)
shift_start_dt = datetime.combine(today_date, shift_start_time)
shift_end_dt = shift_start_dt + timedelta(hours=10)

if now < shift_start_dt:
    remaining_hours = 10.0
    shift_status = "لم يبدأ الشيفت بعد"
    bar_color = "#1f77b4"
elif now > shift_end_dt:
    remaining_hours = 0.0
    shift_status = "انتهى الشيفت"
    bar_color = "#333333"
else:
    elapsed = now - shift_start_dt
    remaining_hours = 10.0 - (elapsed.total_seconds() / 3600.0)
    shift_status = "الشيفت جاري الآن..."
    # يتغير اللون للأحمر إذا تبقى أقل من ساعتين
    bar_color = "#FF4B4B" if remaining_hours < 2 else "#4CAF50"

# إنشاء تبويبات
tab1, tab2 = st.tabs(["📈 التحليل المباشر والمؤشرات", "⚙️ إدارة وسجل البيانات"])

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date']).dt.date

with tab1:
    # --- المؤشرات العلوية ---
    col1, col2, col3 = st.columns(3)
    if not df.empty:
        total_sales = df['Sales'].sum()
        today_sales = df[df['Date'] == today_date]['Sales'].sum()
    else:
        total_sales = today_sales = 0

    col1.metric("إجمالي المبيعات الشهرية", f"{total_sales:,.2f} د.ك")
    col2.metric("مبيعات اليوم الفعلي", f"{today_sales:,.2f} د.ك")
    col3.metric("حالة الشيفت", shift_status)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- الرسوم البيانية ---
    col_chart1, col_chart2 = st.columns([1, 1])
    
    with col_chart1:
        # عداد تنازلي احترافي للوقت
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = remaining_hours,
            title = {'text': "الوقت المتبقي من الشيفت", 'font': {'size': 20, 'color': 'white'}},
            number = {'suffix': " ساعة", 'font': {'color': 'white'}, 'valueformat': ".1f"},
            gauge = {
                'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': bar_color},
                'bgcolor': "rgba(0,0,0,0.1)",
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=350, margin=dict(t=50, b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_chart2:
        if not df.empty:
            df_today = df[df['Date'] == today_date]
            if not df_today.empty:
                fig_line = px.line(df_today, x="Time_Slot", y="Sales", markers=True, 
                                   title="تدفق مبيعات اليوم (كل 3 ساعات)")
                fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=350)
                fig_line.update_traces(line_color='#4CAF50', line_width=3, marker_size=10)
                fig_line.update_yaxes(ticksuffix=" د.ك", title="")
                fig_line.update_xaxes(title="")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("لا توجد مبيعات مسجلة لليوم الحالي حتى الآن.")
        else:
            st.warning("قاعدة البيانات فارغة.")

with tab2:
    if not df.empty:
        st.subheader("📋 سجل البيانات المدخلة")
        st.dataframe(
            df.style.format({"Sales": "{:.2f} د.ك"}),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        st.subheader("🗑️ حذف بيانات مسجلة بالخطأ")
        
        # واجهة الحذف
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
                st.rerun() # إعادة تحميل الصفحة فوراً لتحديث الجداول والأرقام
    else:
        st.info("لا توجد بيانات متاحة لعرضها أو حذفها.")