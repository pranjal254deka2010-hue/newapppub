import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os
import requests
from io import BytesIO

# --- 1. CONFIG & CONNECTION ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year"]
SESSION_MONTHS = ["May", "June", "July", "August", "September", "October", "November", "December", 
                  "January", "February", "March", "April"]

# --- 2. DATA HELPERS ---
def fetch_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def get_monthly_report(student_id, current_year_status):
    """Calculates status based on 1st/2nd year timelines."""
    try:
        res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).eq("fee_type", "Monthly Fee").execute()
        paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    except:
        paid_list = []
    
    report = []
    # 1st Year: May 2026 - May 2028 (25 months)
    if current_year_status == "1st Year":
        timeline = [ (m, "2026") for m in SESSION_MONTHS[0:8] ] + \
                   [ (m, "2027") for m in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2028") for m in ["January", "February", "March", "April", "May"] ]
    # 2nd Year: May 2026 - May 2027 (13 months)
    else:
        timeline = [ (m, "2026") for m in SESSION_MONTHS[0:8] ] + \
                   [ (m, "2027") for m in ["January", "February", "March", "April", "May"] ]

    for m, yr in timeline:
        label = f"{m} {yr}"
        report.append({"label": label, "status": "PAID" if label in paid_list else "PENDING"})
    return report

def generate_receipt_pdf(s_info, bill):
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
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Student: {s_info['name']}")
    pdf.cell(95, 8, f"ID: {s_info['id']}", ln=True)
    pdf.cell(190, 10, f"TOTAL PAID: INR {bill['total']}/-", border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1'), r_no

# --- 3. LOGIN INTERFACE ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford ERP Portal")
    c1, c2 = st.columns(2)
    role = c1.selectbox("Login as", ["Student", "Admin", "Teacher"])
    uid = c2.text_input("User ID")
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
    # --- ADMIN SIDE ---
    if st.session_state.auth["role"] == "admin":
        st.sidebar.title("Admin Menu")
        if st.sidebar.button("Logout"): st.session_state.auth = {"logged_in": False}; st.rerun()
        
        df = fetch_data("students")
        t1, t2, t3, t4 = st.tabs(["🆕 Enrollment", "💰 Payments", "📊 Records", "👨‍🏫 Staff Control"])
        
        with t1:
            with st.form("enroll"):
                c1, c2 = st.columns(2)
                sid, sname = c1.text_input("New ID"), c2.text_input("Full Name")
                strm, yr = c1.selectbox("Course", COURSES), c2.selectbox("Year", YEARS)
                spass = st.text_input("Set Student Password")
                if st.form_submit_button("Register"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "stream": strm, "year_of_study": yr}).execute()
                    st.success("Enrolled!"); st.rerun()
        
        with t2:
            if not df.empty:
                target = st.selectbox("Select Student", df['id'].tolist())
                s_info = df[df['id'] == target].iloc[0]
                with st.form("pay"):
                    p_type = st.selectbox("Type", ["Monthly Fee", "Exam Fee", "Admission Fee"])
                    amt = st.number_input("Amount", min_value=0)
                    m, y = st.selectbox("Month", SESSION_MONTHS), st.selectbox("Year", ["2026", "2027", "2028"])
                    if st.form_submit_button("Record Payment"):
                        pdf, r_no = generate_receipt_pdf(s_info, {"total": amt})
                        supabase.table("fee_records").insert({"student_id": target, "month": m, "year": y, "amount_paid": str(amt), "receipt_no": r_no, "fee_type": p_type}).execute()
                        st.success("Paid!"); st.download_button("Download Receipt", pdf, f"Rec_{r_no}.pdf")

        with t3:
            for _, row in df.iterrows():
                report = get_monthly_report(row['id'], row['year_of_study'])
                with st.expander(f"👤 {row['name']} | Pass: {row['pass']}"):
                    cols = st.columns(4)
                    for i, item in enumerate(report):
                        if item['status'] == "PAID": cols[i % 4].success(item['label'])
                        else: cols[i % 4].error(item['label'])

        with t4:
            st.subheader("Create Teacher Accounts")
            with st.form("t_reg"):
                tid, tname, tpas = st.text_input("Teacher ID"), st.text_input("Name"), st.text_input("Pass")
                if st.form_submit_button("Add Teacher"):
                    supabase.table("teachers").insert({"id": tid, "name": tname, "pass": tpas}).execute()
                    st.success("Teacher Added!")

    # --- TEACHER SIDE ---
    elif st.session_state.auth["role"] == "teacher":
        t_info = st.session_state.auth["user"]
        st.title(f"👨‍🏫 Teacher: {t_info['name']}")
        if st.button("Logout"): st.session_state.auth = {"logged_in": False}; st.rerun()
        
        tab_up, tab_man = st.tabs(["Upload Notes", "Manage Files"])
        with tab_up:
            with st.form("up"):
                title, crs = st.text_input("Title"), st.selectbox("Course", COURSES)
                file = st.file_uploader("PDF", type=["pdf"])
                if st.form_submit_button("Publish"):
                    if file:
                        path = f"notes/{random.randint(1000,9999)}_{file.name}"
                        supabase.storage.from_("notes").upload(path, file.getvalue())
                        url = supabase.storage.from_("notes").get_public_url(path)
                        supabase.table("study_material").insert({"title": title, "course": crs, "file_url": url, "teacher_id": t_info['id'], "file_path": path}).execute()
                        st.success("Uploaded!"); st.rerun()
        with tab_man:
            my_notes = supabase.table("study_material").select("*").eq("teacher_id", t_info['id']).execute().data
            for n in my_notes:
                c1, c2 = st.columns([4, 1])
                c1.info(f"📄 {n['title']}")
                if c2.button("Delete", key=n['id']):
                    supabase.storage.from_("notes").remove([n['file_path']])
                    supabase.table("study_material").delete().eq("id", n['id']).execute()
                    st.rerun()

    # --- STUDENT SIDE ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome {u['name']}")
        if st.button("Logout"): st.session_state.auth = {"logged_in": False}; st.rerun()
        
        notes = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
        for n in notes: st.info(f"📄 {n['title']} ([Download]({n['file_url']}))")
