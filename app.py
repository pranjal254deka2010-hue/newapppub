import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os

# --- 1. CONFIG & CONNECTION ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year"]
SESSION_MONTHS = ["May", "June", "July", "August", "September", "October", "November", "December", 
                  "January", "February", "March", "April"]

# --- 2. LOGIC HELPERS ---
def fetch_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def get_monthly_report(student_id, current_year_status):
    """Calculates status based on specific course timelines[cite: 1]."""
    try:
        res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).eq("fee_type", "Monthly Fee").execute()
        paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    except:
        paid_list = []
    
    report = []
    # 1st Year: May 2026 - May 2028 (25 months)[cite: 1]
    if current_year_status == "1st Year":
        timeline = [ (m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2027") for m in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2028") for m in ["January", "February", "March", "April", "May"] ]
    # 2nd Year: May 2026 - May 2027 (13 months)[cite: 1]
    else:
        timeline = [ (m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2027") for m in ["January", "February", "March", "April", "May"] ]

    for m, yr in timeline:
        label = f"{m} {yr}"
        report.append({"label": label, "status": "PAID" if label in paid_list else "PENDING"})
    return report

def create_receipt(s_info, bill):
    """Generates a detailed PDF receipt[cite: 1]."""
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(5, 5, 200, 287)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(190, 15, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.ln(10)
    
    r_no = f"OSDC-{random.randint(1000, 9999)}"
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"PAYMENT RECEIPT: {r_no}", ln=True, align='C', fill=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Student: {s_info['name']}")
    pdf.cell(95, 8, f"ID: {s_info['id']}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Description / Fee Month", border=1, fill=True)
    pdf.cell(50, 10, "Amount (INR)", border=1, ln=True, align='C', fill=True)
    
    pdf.set_font("Arial", '', 11)
    description = f"{bill['type']} - {bill['month']} {bill['year']}" # Details added[cite: 1]
    pdf.cell(140, 12, description, border=1)
    pdf.cell(50, 12, f"INR {bill['total']}/-", border=1, ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 12, "TOTAL PAID", border=1)
    pdf.cell(50, 12, f"INR {bill['total']}/-", border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1'), r_no

# --- 3. MAIN APP ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    role = st.selectbox("Select Access Level", ["Student", "Teacher", "Admin"])
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    
    if st.button("Login", use_container_width=True):
        if role == "Admin" and uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        elif role == "Teacher":
            res = supabase.table("teachers").select("*").eq("id", uid).eq("pass", pwd).execute()
            if res.data:
                st.session_state.auth = {"logged_in": True, "role": "teacher", "user": res.data[0]}
                st.rerun()
        else:
            res = supabase.table("students").select("*").eq("id", uid).eq("pass", pwd).execute()
            if res.data:
                st.session_state.auth = {"logged_in": True, "role": "student", "user": res.data[0]}
                st.rerun()
        st.error("Invalid Credentials")

else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False}; st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Admin Panel")
        df = fetch_data("students")
        t1, t2, t3, t4 = st.tabs(["🆕 Enrollment", "💰 Fees", "📊 Records", "👨‍🏫 Staff"])
        
        with t1:
            with st.form("en"):
                c1, c2 = st.columns(2)
                sid, sname = c1.text_input("ID"), c2.text_input("Name")
                strm, yr = c1.selectbox("Course", COURSES), c2.selectbox("Year", YEARS)
                spass = st.text_input("Password")
                if st.form_submit_button("Enroll Student"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "stream": strm, "year_of_study": yr}).execute()
                    st.success("Enrolled!"); st.rerun()
        
        with t2:
            if not df.empty:
                target = st.selectbox("Select Student", df['id'].tolist())
                download_placeholder = st.empty() # Placeholder fix[cite: 1]
                with st.form("billing"):
                    ftype = st.selectbox("Fee Category", ["Monthly Fee", "Exam Fee", "Admission Fee"])
                    amt = st.number_input("Amount Paid", min_value=0)
                    m = st.selectbox("Month", SESSION_MONTHS)
                    y = st.selectbox("Year", ["2026", "2027", "2028"])
                    submitted = st.form_submit_button("Generate Receipt")
                    if submitted:
                        s_row = df[df['id'] == target].iloc[0]
                        pdf_data, r_no = create_receipt(s_row, {"total": amt, "type": ftype, "month": m, "year": y})
                        supabase.table("fee_records").insert({
                            "student_id": target, "month": m, "year": y, 
                            "amount_paid": str(amt), "receipt_no": r_no, "fee_type": ftype
                        }).execute()
                        st.success(f"Receipt {r_no} ready.")
                        download_placeholder.download_button("📥 Download Receipt", pdf_data, f"Rec_{r_no}.pdf")

        with t3:
            for _, row in df.iterrows():
                report = get_monthly_report(row['id'], row['year_of_study'])
                with st.expander(f"👤 {row['name']} | ID: {row['id']}"):
                    cols = st.columns(6)
                    for i, item in enumerate(report):
                        if item['status'] == "PAID": cols[i % 6].success(item['label'])
                        else: cols[i % 6].error(item['label'])

        with t4:
            st.subheader("Manage Teacher Accounts")
            with st.form("t_reg"):
                tid, tname, tpas = st.text_input("Teacher ID"), st.text_input("Name"), st.text_input("Password")
                if st.form_submit_button("Create Teacher Account"):
                    supabase.table("teachers").insert({"id": tid, "name": tname, "pass": tpas}).execute()
                    st.success("Staff Account Created!"); st.rerun()

    # --- TEACHER VIEW ---
    elif st.session_state.auth["role"] == "teacher":
        t_user = st.session_state.auth["user"]
        st.title(f"👨‍🏫 Welcome, {t_user['name']}")
        tab_up, tab_man = st.tabs(["Upload New Notes", "Delete Old Notes"])
        with tab_up:
            with st.form("up"):
                title, crs = st.text_input("Title"), st.selectbox("Course", COURSES)
                file = st.file_uploader("Select PDF", type=["pdf"])
                if st.form_submit_button("Publish"):
                    if file and title:
                        fname = f"{random.randint(1000,9999)}_{file.name}"
                        path = f"notes/{fname}"
                        supabase.storage.from_("notes").upload(path, file.getvalue())
                        url = supabase.storage.from_("notes").get_public_url(path)
                        supabase.table("study_material").insert({"title": title, "course": crs, "file_url": url, "teacher_id": t_user['id'], "file_path": path}).execute()
                        st.success("Published!"); st.rerun()
        with tab_man:
            my_notes = supabase.table("study_material").select("*").eq("teacher_id", t_user['id']).execute().data
            for n in my_notes:
                c1, c2 = st.columns([4, 1])
                c1.info(f"📄 {n['title']}")
                if c2.button("Delete", key=n['id']):
                    supabase.storage.from_("notes").remove([n['file_path']])
                    supabase.table("study_material").delete().eq("id", n['id']).execute()
                    st.success("Deleted!"); st.rerun()

    # --- STUDENT VIEW ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        s_tab1, s_tab2 = st.tabs(["📚 My Notes", "💳 Fee Summary"])
        with s_tab1:
            notes = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
            if notes:
                for n in notes:
                    t_res = supabase.table("teachers").select("name").eq("id", n['teacher_id']).execute()
                    t_name = t_res.data[0]['name'] if t_res.data else "Faculty"
                    st.info(f"📄 **{n['title']}** (By: {t_name})")
                    st.markdown(f"[Download PDF]({n['file_url']})")
        with s_tab2:
            report = get_monthly_report(u['id'], u['year_of_study'])
            hist = supabase.table("fee_records").select("*").eq("student_id", u['id']).order("created_at", desc=True).execute().data
            if hist: st.success(f"🗓️ Last Payment: {hist[0]['created_at'][:10]}")
            st.subheader("Fee Status Checklist")
            scols = st.columns(4)
            for i, item in enumerate(report):
                status_icon = "✅" if item['status'] == "PAID" else "❌"
                scols[i % 4].write(f"{status_icon} {item['label']}")
