import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os

# --- ۱. تنظیمات اولیه و تم ---
st.set_page_config(page_title="Varia Studio | Founder OS", layout="wide", page_icon="🌱")

# پالت رنگی Varia Studio
FOREST = "#2F4F3A"
CREAM = "#F5F0E8"
GOLD = "#D4A24C"
INK = "#1A1A1A"

st.markdown(f"""
<style>
    /* فونت و رنگ‌ها */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {INK}; }}
    
    /* هدرها */
    h1, h2, h3 {{ color: {CREAM} !important; font-weight: 600; }}
    
    /* کارت‌های متریک */
    div[data-testid="stMetric"] {{
        background-color: {FOREST};
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid {GOLD};
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    div[data-testid="stMetricValue"] {{ color: {GOLD} !important; font-size: 2rem !important; }}
    div[data-testid="stMetricLabel"] {{ color: {CREAM} !important; }}
    
    /* تب‌ها */
    .stTabs [data-baseweb="tab"] {{ color: {CREAM}; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{ color: {GOLD} !important; border-bottom-color: {GOLD} !important; }}
    
    /* دکمه‌ها */
    .stButton>button, .stFormSubmitButton>button {{
        background-color: {GOLD} !important;
        color: {INK} !important;
        border-radius: 8px !important;
        font-weight: 700;
        border: none;
        width: 100%;
    }}
    .stButton>button:hover, .stFormSubmitButton>button:hover {{
        background-color: {CREAM} !important;
        color: {FOREST} !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- ۲. دیتابیس ---
DB_FILE = "varia_os.db"
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        # مشتریان (CRM)
        c.execute('''CREATE TABLE IF NOT EXISTS leads 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, person TEXT, 
                      email TEXT, status TEXT, notes TEXT, date TEXT)''')
        # تسک‌ها
        c.execute('''CREATE TABLE IF NOT EXISTS tasks 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, category TEXT, 
                      priority TEXT, status TEXT, date TEXT)''')
        # درآمد
        c.execute('''CREATE TABLE IF NOT EXISTS revenue 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL, source TEXT, date TEXT)''')
        # پیش‌نویس‌های محتوا (Content Pipeline)
        c.execute('''CREATE TABLE IF NOT EXISTS content_drafts 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, draft_text TEXT, 
                      status TEXT, date TEXT)''')
        conn.commit()

init_db()

today = datetime.now().strftime("%Y-%m-%d")

# --- ۳. هدر و شاخص‌های کلیدی (KPIs) ---
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown(f"<h1 style='color:{GOLD}; font-size: 3rem;'>🌱</h1>", unsafe_allow_html=True)
with col_title:
    st.markdown(f"<h1>Varia Studio <span style='color:{GOLD}; font-size: 1.2rem; font-weight:400;'>| Founder OS</span></h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{CREAM}; opacity:0.7;'>Mission: $1,000 MRR. Build. Sell. Learn.</p>", unsafe_allow_html=True)

st.divider()

with get_db() as conn:
    total_revenue = conn.execute("SELECT SUM(amount) FROM revenue").fetchone()[0] or 0
    pilots_sold = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'Pilot Paid'").fetchone()[0]
    tasks_today = conn.execute("SELECT COUNT(*) FROM tasks WHERE date = ?", (today,)).fetchone()[0]
    total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Revenue", f"${total_revenue:,.0f} / $1k", delta=f"{int((total_revenue/1000)*100)}% Complete" if total_revenue < 1000 else "Goal Reached!")
c2.metric("🎯 Pilots Signed", f"{pilots_sold} / 5", delta="Target: 5")
c3.metric("📋 Tasks Today", tasks_today)
c4.metric("🏢 Leads Pipeline", total_leads)

st.divider()

# --- ۴. تب‌های اصلی (Founder OS) ---
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Sales & CRM", "📅 Daily Execution", "📸 Content Studio", "📈 Analytics"])

# ==========================================
# تب ۱: فروش و مدیریت مشتریان (CRM)
# ==========================================
with tab1:
    st.subheader("Lead Pipeline (B2B)")
    
    with st.expander("➕ Add / Update a Lead", expanded=False):
        with st.form("crm_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                company = st.text_input("Company Name (e.g., Kilter)")
                person = st.text_input("Contact Person (e.g., Tore)")
            with col2:
                email = st.text_input("Email")
                status = st.selectbox("Status", ["Contacted", "Follow-up Sent", "Meeting Scheduled", "Pilot Paid", "Lost / Rejected"])
            
            notes = st.text_area("Notes (e.g., Sent YOLOv8 proposal, waiting for reply)")
            
            if st.form_submit_button("Save Lead"):
                if company:
                    with get_db() as conn:
                        conn.execute("INSERT INTO leads (company, person, email, status, notes, date) VALUES (?, ?, ?, ?, ?, ?)",
                                     (company, person, email, status, notes, today))
                        conn.commit()
                    st.success("Lead saved to pipeline!")
                    st.rerun()

    with get_db() as conn:
        leads_df = pd.read_sql_query("SELECT * FROM leads ORDER BY id DESC", conn)
    
    if not leads_df.empty:
        # رنگی کردن وضعیت‌ها
        def color_status(val):
            if val == "Pilot Paid": return 'background-color: #2F4F3A; color: #D4A24C'
            if val == "Lost / Rejected": return 'background-color: #8B0000; color: white'
            return ''
        
        st.dataframe(leads_df[['company', 'person', 'email', 'status', 'notes', 'date']].style.applymap(color_status, subset=['status']), 
                     use_container_width=True, hide_index=True)
    else:
        st.info("Pipeline is empty. Start hunting!")

# ==========================================
# تب ۲: اجرای روزانه (تسک‌ها)
# ==========================================
with tab2:
    st.subheader("Today's Focus (3 Max)")
    
    with st.form("task_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            task_desc = st.text_input("What needs to be done?")
        with col2:
            task_cat = st.selectbox("Category", ["Sales/Outreach", "Product/Code", "Content/Brand", "Learning"])
        with col3:
            priority = st.selectbox("Priority", ["🔥 High", "⚡ Medium", "☕ Low"])
            
        if st.form_submit_button("Add Task"):
            if task_desc:
                with get_db() as conn:
                    conn.execute("INSERT INTO tasks (task, category, priority, status, date) VALUES (?, ?, ?, ?, ?)",
                                 (task_desc, task_cat, priority, "Pending", today))
                    conn.commit()
                st.rerun()

    with get_db() as conn:
        tasks_df = pd.read_sql_query("SELECT * FROM tasks WHERE date = ? ORDER BY priority ASC, id DESC", conn, params=(today,))
    
    if tasks_df.empty:
        st.info("No tasks for today. What's the plan?")
    else:
        for _, row in tasks_df.iterrows():
            col1, col2, col3, col4 = st.columns([1, 5, 2, 1])
            with col1:
                is_done = row['status'] == 'Done'
                if st.checkbox("", value=is_done, key=f"task_{row['id']}"):
                    if not is_done:
                        with get_db() as conn:
                            conn.execute("UPDATE tasks SET status = 'Done' WHERE id = ?", (row['id'],))
                            conn.commit()
                        st.rerun()
            with col2:
                st.write(f"**{row['priority']}** | {row['task']}")
            with col3:
                st.caption(f"{row['category']}")
            with col4:
                if row['status'] == 'Done':
                    st.success("✅")
                else:
                    st.warning("⏳")

# ==========================================
# تب ۳: استودیوی محتوا (Content Studio)
# ==========================================
with tab3:
    st.subheader("Content Pipeline")
    st.write("Draft your LinkedIn posts and Instagram captions here before publishing.")
    
    with st.form("content_form", clear_on_submit=True):
        platform = st.selectbox("Platform", ["LinkedIn", "Instagram (Feed)", "Instagram (Story)", "X (Twitter)"])
        draft_text = st.text_area("Draft (Hook + Body + CTA)", height=150)
        
        if st.form_submit_button("Save Draft"):
            if draft_text:
                with get_db() as conn:
                    conn.execute("INSERT INTO content_drafts (platform, draft_text, status, date) VALUES (?, ?, ?, ?)",
                                 (platform, draft_text, "Draft", today))
                    conn.commit()
                st.success("Draft saved!")
                st.rerun()
                
    with get_db() as conn:
        drafts_df = pd.read_sql_query("SELECT * FROM content_drafts ORDER BY id DESC", conn)
        
    if not drafts_df.empty:
        for _, row in drafts_df.iterrows():
            with st.expander(f"{row['platform']} - {row['date']}"):
                st.write(row['draft_text'])
                if st.button("Mark as Published", key=f"pub_{row['id']}"):
                    with get_db() as conn:
                        conn.execute("UPDATE content_drafts SET status = 'Published' WHERE id = ?", (row['id'],))
                        conn.commit()
                    st.rerun()

# ==========================================
# تب ۴: آنالیتیکس و درآمد
# ==========================================
with tab4:
    st.subheader("Revenue & Analytics")
    
    with st.form("revenue_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Pilot Amount (USD)", min_value=50.0, step=50.0, value=200.0)
        with col2:
            source = st.text_input("Client (e.g., Kilter Pilot)")
            
        if st.form_submit_button("Log Payment"):
            if source:
                with get_db() as conn:
                    conn.execute("INSERT INTO revenue (amount, source, date) VALUES (?, ?, ?)",
                                 (amount, source, today))
                    conn.commit()
                st.rerun()
                
    with get_db() as conn:
        rev_df = pd.read_sql_query("SELECT * FROM revenue ORDER BY date ASC", conn)
        
    if not rev_df.empty:
        st.dataframe(rev_df, use_container_width=True, hide_index=True)
        
        # نمودار پیشرفت درآمد
        rev_df['cum_sum'] = rev_df['amount'].cumsum()
        fig = px.line(rev_df, x='date', y='cum_sum', markers=True, 
                      title="Cumulative Revenue Progress",
                      labels={'cum_sum': 'Total Revenue ($)', 'date': 'Date'})
        fig.update_traces(line_color=GOLD, marker_color=CREAM)
        fig.update_layout(plot_bgcolor=INK, paper_bgcolor=INK, font_color=CREAM, title_font_color=CREAM)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No revenue logged yet. The first $200 is the hardest.")