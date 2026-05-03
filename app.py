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
STANDARD_MONTHS = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]

def fetch_students():
    try:
        res = supabase.table("students").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def get_monthly_report(student_id, current_year_status):
    """Generates the specific timeline and checks payment status from Supabase."""
    try:
        res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).eq("fee_type", "Monthly Fee").execute()
        paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    except:
        paid_list = []
    
    report = []
    # Logic for 1st Year (May 2026 to May 2028 - 25 Months)
    if current_year_status == "1st Year":
        timeline = [ (m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2027") for m in STANDARD_MONTHS ] + \
                   [ (m, "2028") for m in ["January", "February", "March", "April", "May"] ]
    
    # Logic for 2nd Year (May 2026 to May 2027 - 13 Months)
    else:
        timeline = [ (m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2027") for m in ["January", "February", "March", "April", "May"] ]

    for m, yr in timeline:
        label = f"{m} {yr}"
        report.append({"label": label, "status": "PAID" if label in paid_list else "PENDING"})
        
    return report

# --- 2. RECEIPT GENERATOR ---
def create_receipt(s_info, bill):
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(5, 5, 200, 287)
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Skill Development & Paramedical Training", ln=True, align='C')
    pdf.ln(15)
    
    r_no = f"OSDC-{random.randint(1000, 9999)}"
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"OFFICIAL FEES RECEIPT - {r_no}", ln=True, align='C', fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Name: {s_info['name']}")
    pdf.cell(95, 8, f"ID: {s_info['id']}", ln=True)
    pdf.cell(95, 8, f"Course: {s_info['stream']}")
    pdf.cell(95, 8, f"Session Year: {s_info['year_of_study']}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Description", border=1, fill=True)
    pdf.cell(50, 8, "Amount (INR)", border=1, ln=True, align='C', fill=True)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(140, 8, f"{bill['type']} ({bill['m']} {bill['y']})", border=1)
    pdf.cell(50, 8, f"{bill['amt']}/-", border=1, ln=True, align='C')
            
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "GRAND TOTAL PAID", border=1)
    pdf.cell(50, 10, f"INR {bill['amt']}/-", border=1, ln=True, align='C')
    pdf.ln(20)
    pdf.cell(190, 10, "Authorized Signatory", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1'), r_no

# --- 3. MAIN APP ---
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
        elif role == "Teacher" and pwd == "teacher123":
            st.session_state.auth = {"logged_in": True, "role": "teacher", "user": uid}
            st.rerun()
        else:
            try:
                res = supabase.table("students").select("*").eq("id", uid).eq("pass", pwd).execute()
                if res.data:
                    st.session_state.auth = {"logged_in": True, "role": "student", "user": res.data[0]}
                    st.rerun()
                else: st.error("Invalid Credentials")
            except: st.error("Database Connection Error")

else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Admin Management System")
        df = fetch_students()
        
        t1, t2, t3 = st.tabs(["🆕 Enrollment", "💳 Billing & Receipts", "📊 Financial Records"])
        
        with t1:
            with st.form("enroll"):
                c1, c2 = st.columns(2)
                sid, sname = c1.text_input("Student ID"), c2.text_input("Name")
                stream, year = c1.selectbox("Stream", COURSES), c2.selectbox("Current Year", YEARS)
                spass, sphone = c1.text_input("Password"), c2.text_input("Phone")
                if st.form_submit_button("Register"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "stream": stream, "year_of_study": year}).execute()
                    st.success("Student Enrolled Successfully!"); st.rerun()

        with t2:
            if not df.empty:
                target = st.selectbox("Select Student for Billing", df['id'].tolist())
                s_info = df[df['id'] == target].iloc[0]
                with st.form("billing"):
                    ca, cb = st.columns(2)
                    p_type = ca.selectbox("Payment Type", ["Monthly Fee", "Exam Fee", "Admission Fee", "Fine"])
                    amt = cb.number_input("Amount (INR)", min_value=0)
                    sel_m = ca.selectbox("For Month", ["May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March", "April"])
                    sel_y = cb.selectbox("For Year", ["2026", "2027", "2028"])
                    if st.form_submit_button("Generate Receipt"):
                        bill = {"amt": amt, "m": sel_m, "y": sel_y, "type": p_type}
                        pdf, r_no = create_receipt(s_info, bill)
                        supabase.table("fee_records").insert({"student_id": target, "month": sel_m, "year": sel_y, "amount_paid": str(amt), "receipt_no": r_no, "fee_type": p_type}).execute()
                        st.success(f"Receipt {r_no} Generated!")
                        st.download_button("🖨️ Download Receipt", pdf, f"Rec_{target}_{sel_m}.pdf")

        with t3:
            st.subheader("📊 Session-wise Financial Monitoring")
            if not df.empty:
                for _, row in df.iterrows():
                    history = supabase.table("fee_records").select("*").eq("student_id", row['id']).order("created_at", desc=True).execute().data
                    last_pay = history[0]['created_at'][:10] if history else "No Payments"
                    report = get_monthly_report(row['id'], row['year_of_study'])
                    
                    with st.expander(f"👤 {row['name']} ({row['id']}) | Last Pay: {last_pay} | Pass: {row['pass']}"):
                        c1, c2 = st.columns([1, 1])
                        with c1:
                            st.write("**Payment History**")
                            if history: st.table(pd.DataFrame(history)[['month', 'year', 'fee_type', 'amount_paid']])
                        with c2:
                            st.write(f"**Course Tracker ({row['year_of_study']})**")
                            mc = st.columns(4)
                            for i, item in enumerate(report):
                                with mc[i % 4]:
                                    if item['status'] == "PAID": st.success(f"{item['label']}")
                                    else: st.error(f"{item['label']}")

    elif st.session_state.auth["role"] == "teacher":
        st.title("👨‍🏫 Teacher Notes Portal")
        with st.form("notes"):
            title, crs = st.text_input("Notes Title"), st.selectbox("Course", COURSES)
            f = st.file_uploader("Upload PDF", type=["pdf"])
            if st.form_submit_button("Upload"):
                if f:
                    path = f"notes/{random.randint(100,999)}_{f.name}"
                    supabase.storage.from_("notes").upload(path, f.getvalue())
                    url = supabase.storage.from_("notes").get_public_url(path)
                    supabase.table("study_material").insert({"title": title, "course": crs, "file_url": url}).execute()
                    st.success("Notes Shared!")

    else:
        # Student View
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome {u['name']}")
        t_a, t_b = st.tabs(["📚 Study Materials", "💸 Payment Status"])
        with t_a:
            notes = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
            if notes:
                for n in notes: st.info(f"📄 {n['title']} ([Download]({n['file_url']}))")
        with t_b:
            report = get_monthly_report(u['id'], u['year_of_study'])
            st.subheader("Monthly Fee Status")
            cols = st.columns(6)
            for i, item in enumerate(report):
                cols[i % 6].write(f"{item['label']}\n{item['status']}")
