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

def fetch_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def get_monthly_report(student_id, current_year_status):
    try:
        res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).eq("fee_type", "Monthly Fee").execute()
        paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    except:
        paid_list = []
    
    report = []
    # 1st Year: May 2026 - May 2028 (25 months)
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

# --- 2. AUTHENTICATION ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    role = st.selectbox("Login As", ["Admin", "Teacher", "Student"])
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

    # --- TEACHER DASHBOARD ---
    if st.session_state.auth["role"] == "teacher":
        t_info = st.session_state.auth["user"]
        st.title(f"👨‍🏫 Teacher: {t_info['name']}")
        tab1, tab2 = st.tabs(["📤 Upload Notes", "🗑️ Manage My Notes"])
        
        with tab1:
            with st.form("upload"):
                title = st.text_input("Title")
                crs = st.selectbox("Course", COURSES)
                f = st.file_uploader("PDF", type=["pdf"])
                if st.form_submit_button("Publish"):
                    if f:
                        fname = f"{random.randint(1000,9999)}_{f.name}"
                        path = f"notes/{fname}"
                        supabase.storage.from_("notes").upload(path, f.getvalue())
                        url = supabase.storage.from_("notes").get_public_url(path)
                        supabase.table("study_material").insert({"title": title, "course": crs, "file_url": url, "teacher_id": t_info['id'], "file_path": path}).execute()
                        st.success("Uploaded!"); st.rerun()
        
        with tab2:
            my_notes = supabase.table("study_material").select("*").eq("teacher_id", t_info['id']).execute().data
            for n in my_notes:
                c1, c2 = st.columns([4, 1])
                c1.info(f"📄 {n['title']} ({n['course']})")
                if c2.button("Delete", key=n['id']):
                    supabase.storage.from_("notes").remove([n['file_path']])
                    supabase.table("study_material").delete().eq("id", n['id']).execute()
                    st.rerun()

    # --- ADMIN DASHBOARD ---
    elif st.session_state.auth["role"] == "admin":
        st.title("🛡️ Admin Panel")
        df = fetch_data("students")
        t1, t2, t3 = st.tabs(["🆕 Enrollment", "💰 Payments", "📊 Records"])
        
        with t1:
            with st.form("en"):
                c1, c2 = st.columns(2)
                sid, sname = c1.text_input("ID"), c2.text_input("Name")
                strm, yr = c1.selectbox("Course", COURSES), c2.selectbox("Year", YEARS)
                spass = st.text_input("Pass")
                if st.form_submit_button("Enroll"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "stream": strm, "year_of_study": yr}).execute()
                    st.success("Enrolled!"); st.rerun()
        
        with t2:
            if not df.empty:
                target = st.selectbox("Student", df['id'].tolist())
                with st.form("pay"):
                    p_type = st.selectbox("Type", ["Monthly Fee", "Exam Fee", "Admission Fee"])
                    amt = st.number_input("Amount", min_value=0)
                    m = st.selectbox("Month", ["May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March", "April"])
                    y = st.selectbox("Year", ["2026", "2027", "2028"])
                    if st.form_submit_button("Paid"):
                        supabase.table("fee_records").insert({"student_id": target, "month": m, "year": y, "amount_paid": str(amt), "fee_type": p_type}).execute()
                        st.success("Payment Recorded!")

        with t3:
            for _, row in df.iterrows():
                history = supabase.table("fee_records").select("*").eq("student_id", row['id']).execute().data
                report = get_monthly_report(row['id'], row['year_of_study'])
                with st.expander(f"👤 {row['name']} | Pass: {row['pass']}"):
                    st.write("**Payment Tracker**")
                    cols = st.columns(4)
                    for i, item in enumerate(report):
                        if item['status'] == "PAID": cols[i % 4].success(item['label'])
                        else: cols[i % 4].error(item['label'])

    # --- STUDENT DASHBOARD ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome {u['name']}")
        notes = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
        for n in notes: st.info(f"📄 {n['title']} ([Download]({n['file_url']}))")
