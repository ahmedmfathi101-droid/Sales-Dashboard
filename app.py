import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb

# إعداد الصفحة لتكون بعرض الشاشة واسم احترافي
st.set_page_config(page_title="داش بورد المبيعات", page_icon="📊", layout="wide")

# ==========================================
# إضافة تصميم CSS احترافي ودعم للغة العربية
# ==========================================
st.markdown("""
    <style>
    /* محاذاة النصوص لليمين */
    * {
        direction: rtl;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* تصميم بطاقات المؤشرات (Metrics Cards) */
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
# 1. نافذة المدخلات الاحترافية (باستخدام Form)
# ==========================================
with st.sidebar.form("sales_form", clear_on_submit=False):
    st.header("📝 إدخال بيانات البيع (د.ك)")
    st.markdown("---")
    
    input_date = st.date_input("تاريخ الشيفت")
    input_day = input_date.strftime("%A")
    
    time_slot = st.selectbox("الفترة الزمنية", 
                             [
                                 "الفترة الأولى (أول 3 ساعات)", 
                                 "الفترة الثانية (ثاني 3 ساعات)", 
                                 "الفترة الثالثة (آخر 3 ساعات)"
                             ])
    
    # تم تعديل النص هنا بناءً على طلبك
    sales_value = st.number_input("قيمة المبيعات (د.ك)", min_value=0.0, step=10.0, format="%.2f")
    
    submit_button = st.form_submit_button("💾 تسجيل المبيعات", use_container_width=True)
    
    if submit_button:
        with duckdb.connect(DB_FILE) as conn:
            conn.execute(
                "INSERT INTO sales_data VALUES (?, ?, ?, ?)",
                [input_date, input_day, time_slot, sales_value]
            )
        st.success("✅ تم حفظ المبيعات بنجاح!")

# تحميل البيانات بعد الإدخال
df = load_data()

# ==========================================
# 2. نافذة المخرجات والتحليل الرئيسية
# ==========================================
st.title("📊 التحليل الديناميكي لمبيعات الشهر")
st.markdown("---")

if not df.empty:
    # إنشاء تبويبات لعرض البيانات بشكل منظم
    tab1, tab2 = st.tabs(["📈 لوحة المؤشرات", "📋 سجل البيانات"])
    
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    
    with tab1:
        # حساب المؤشرات
        total_sales = df['Sales'].sum()
        today_sales = df[df['Date'] == input_date]['Sales'].sum()
        
        # صف المؤشرات العلوية
        col1, col2, col3 = st.columns(3)
        col1.metric("إجمالي المبيعات الشهرية", f"{total_sales:,.2f} د.ك")
        col2.metric("مبيعات اليوم الحالي", f"{today_sales:,.2f} د.ك")
        col3.metric("عدد العمليات المسجلة", f"{len(df)} فترة")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # الرسوم البيانية
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            df_today = df[df['Date'] == input_date]
            if not df_today.empty:
                fig_line = px.line(df_today, x="Time_Slot", y="Sales", markers=True, 
                                   title="تدفق مبيعات اليوم (كل 3 ساعات)")
                # تحسين شكل الرسم البياني
                fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                fig_line.update_traces(line_color='#4CAF50', line_width=3, marker_size=10)
                fig_line.update_yaxes(ticksuffix=" د.ك", title="")
                fig_line.update_xaxes(title="")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("لا توجد مبيعات مسجلة لليوم المختار حتى الآن.")
                
        with col_chart2:
            df_daily = df.groupby('Date')['Sales'].sum().reset_index()
            fig_bar = px.bar(df_daily, x='Date', y='Sales', text='Sales',
                             title="مقارنة الأداء اليومي")
            # تحسين شكل الرسم الشريطي
            fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            fig_bar.update_traces(marker_color='#1f77b4', texttemplate='%{text:,.0f}', textposition='outside')
            fig_bar.update_yaxes(ticksuffix=" د.ك", title="")
            fig_bar.update_xaxes(title="")
            st.plotly_chart(fig_bar, use_container_width=True)
            
    with tab2:
        st.subheader("تفاصيل البيانات المدخلة")
        # عرض البيانات كجدول أنيق
        st.dataframe(
            df.style.format({"Sales": "{:.2f} د.ك"}),
            use_container_width=True,
            hide_index=True
        )
else:
    st.warning("⚠️ قاعدة البيانات فارغة. يرجى تسجيل مبيعات الفترة الأولى من القائمة الجانبية.")