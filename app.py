import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb

# إعداد الصفحة
st.set_page_config(page_title="داش بورد المبيعات الديناميكي", layout="wide")

# اسم ملف قاعدة بيانات DuckDB
DB_FILE = "sales_dashboard.db"

# ==========================================
# 0. تهيئة قاعدة البيانات (إنشاء الجدول إذا لم يكن موجوداً)
# ==========================================
# نستخدم with context manager لضمان فتح وإغلاق الاتصال بأمان
with duckdb.connect(DB_FILE) as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales_data (
            Date DATE,
            Day VARCHAR,
            Time_Slot VARCHAR,
            Sales DOUBLE
        )
    ''')

# دالة لجلب البيانات من القاعدة
def load_data():
    with duckdb.connect(DB_FILE) as conn:
        # قراءة البيانات وتحويلها مباشرة إلى Pandas DataFrame للرسم
        return conn.execute("SELECT * FROM sales_data ORDER BY Date, Time_Slot").df()

# ==========================================
# 1. نافذة المدخلات (الشريط الجانبي)
# ==========================================
st.sidebar.header("📝 إدخال بيانات البيع (د.ك)")
input_date = st.sidebar.date_input("التاريخ")
input_day = input_date.strftime("%A")

time_slot = st.sidebar.selectbox("الفترة الزمنية (كل 3 ساعات)", 
                                 [
                                     "الفترة الأولى (أول 3 ساعات)", 
                                     "الفترة الثانية (ثاني 3 ساعات)", 
                                     "الفترة الثالثة (آخر 3 ساعات)"
                                 ])

sales_value = st.sidebar.number_input("قيمة المبيعات (دينار كويتي)", min_value=0.0, step=10.0)

if st.sidebar.button("تسجيل المبيعات"):
    # إدخال البيانات في DuckDB باستخدام Prepared Statements لحماية البيانات
    with duckdb.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO sales_data VALUES (?, ?, ?, ?)",
            [input_date, input_day, time_slot, sales_value]
        )
    st.sidebar.success("تم تسجيل المبيعات بنجاح في قاعدة البيانات!")

# تحميل البيانات المحدثة للعرض
df = load_data()

# ==========================================
# 2. نافذة المخرجات والتحليل
# ==========================================
st.title("📊 التحليل الديناميكي لمبيعات الشهر (بالدينار الكويتي)")
st.markdown("---")

if not df.empty:
    # حساب المؤشرات
    total_sales = df['Sales'].sum()
    
    # حساب مبيعات اليوم الحالي باستخدام Pandas (يمكن أيضاً حسابها بـ SQL داخل DuckDB)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    today_sales = df[df['Date'] == input_date]['Sales'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي المبيعات الشهرية", f"{total_sales:,.2f} د.ك")
    col2.metric("مبيعات اليوم الحالي", f"{today_sales:,.2f} د.ك")
    col3.metric("إجمالي فترات الإدخال", f"{len(df)} فترة")
    
    st.markdown("---")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📈 حركة المبيعات خلال فترات الشيفت (لليوم)")
        df_today = df[df['Date'] == input_date]
        if not df_today.empty:
            fig_line = px.line(df_today, x="Time_Slot", y="Sales", markers=True, 
                               title="تدفق المبيعات (كل 3 ساعات)",
                               labels={"Sales": "المبيعات (د.ك)", "Time_Slot": "الفترة الزمنية"})
            fig_line.update_yaxes(ticksuffix=" د.ك")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("لا توجد بيانات مسجلة لليوم الحالي بعد.")
            
    with col_chart2:
        st.subheader("📊 مقارنة الأداء اليومي خلال الشهر")
        df_daily = df.groupby('Date')['Sales'].sum().reset_index()
        fig_bar = px.bar(df_daily, x='Date', y='Sales', 
                         title="إجمالي المبيعات للأيام المسجلة", 
                         text='Sales',
                         labels={"Sales": "المبيعات (د.ك)", "Date": "التاريخ"})
        fig_bar.update_traces(texttemplate='%{text:,.2f} د.ك', textposition='outside')
        fig_bar.update_yaxes(ticksuffix=" د.ك")
        st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.warning("قاعدة البيانات فارغة. يرجى إدخال مبيعات الفترة الأولى لبدء التحليل.")