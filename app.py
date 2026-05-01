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
YEARS = ["1st Year", "2nd Year", "3rd Year"]
# Academic Session Cycle
SESSION_MONTHS = ["May", "June", "July", "August", "September", "October", "November", "December", 
                  "January", "February", "March", "April"]

def fetch_students():
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data)

def get_monthly_report(student_id):
    """Checks which months are paid in the fee_records table."""
    res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).execute()
    paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    
    report = []
    for m in SESSION_MONTHS:
        # Simple logic: May-Dec is 2026, Jan-Apr is 2027
        yr = "2026" if m in SESSION_MONTHS[:8] else "2027"
        label = f"{m} {yr}"
        status = "✅ Paid" if label in paid_list else "❌ Pending"
        report.append({"Month": label, "Status": status})
    return report

# --- 2. RECEIPT GENERATOR ---
def create_receipt(s_info, bill):
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(5, 5, 200, 185)
    
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 10, 25)
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Skill Development & Paramedical Training", ln=True, align='C')
    pdf.ln(15)
    
    r_no = f"OSDC-{random.randint(100000, 999999)}"
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"FEES RECEIPT - {r_no}", ln=True, align='C', fill=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Name: {s_info['name']}")
    pdf.cell(95, 8, f"ID: {s_info['id']}", ln=True)
    pdf.cell(95, 8, f"Stream: {s_info['stream']}")
    pdf.cell(95, 8, f"Academic Year: {s_info['year_of_study']}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Description", border=1, fill=True)
    pdf.cell(50, 8, "Amount (INR)", border=1, ln=True, align='C', fill=True)
    
    pdf.set_font("Arial", '', 10)
    total = 0
    fees = [
        ("Admission Fees", bill['adm']),
        ("Exam Fees", bill['exam']),
        (f"Monthly Fees ({bill['m']} {bill['y']})", bill['mon']),
        ("Fine / Late Penalty", bill['fine'])
    ]
    
    for desc, amt in fees:
        if int(amt) > 0:
            pdf.cell(140, 8, desc, border=1)
            pdf.cell(50, 8, f"{amt}/-", border=1, ln=True, align='C')
            total += int(amt)
            
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "GRAND TOTAL", border=1)
    pdf.cell(50, 10, f"INR {total}/-", border=1, ln=True, align='C')
    
    pdf.ln(20)
    pdf.cell(95, 10, "Student Signature")
    pdf.cell(95, 10, "Office Seal & Signature", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1'), r_no, total

# --- 3. MAIN APP ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        else:
            res = supabase.table("students").select("*").eq("id", uid).eq("pass", pwd).execute()
            if res.data:
                st.session_state.auth = {"logged_in": True, "role": "student", "user": res.data[0]}
                st.rerun()

else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Institutional Admin Dashboard")
        df = fetch_students()
        
        t1, t2, t3 = st.tabs(["🆕 Enrollment", "💳 Billing & Fines", "📋 Monthly Records"])
        
        with t1:
            with st.form("enroll"):
                c1, c2, c3 = st.columns(3)
                sid = c1.text_input("Student ID")
                sname = c2.text_input("Full Name")
                sphone = c3.text_input("Phone")
                stream = c1.selectbox("Stream", COURSES)
                year = c2.selectbox("Year", YEARS)
                spass = c3.text_input("Password")
                if st.form_submit_button("Register"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "stream": stream, "year_of_study": year, "status": "Pending"}).execute()
                    st.success("Enrolled!")
                    st.rerun()

        with t2:
            if not df.empty:
                target = st.selectbox("Select Student", df['id'].tolist())
                s_info = df[df['id'] == target].iloc[0]
                
                print_spot = st.container()
                with st.form("billing"):
                    ca, cb = st.columns(2)
                    adm = ca.number_input("Admission Fee", 0)
                    exm = cb.number_input("Exam Fee", 0)
                    mon = ca.number_input("Monthly Fee", 0)
                    fine = cb.number_input("Fine", 0)
                    sel_m = ca.selectbox("For Month", SESSION_MONTHS)
                    sel_y = cb.selectbox("For Year", ["2026", "2027", "2028"])
                    
                    if st.form_submit_button("Generate Receipt"):
                        bill = {"adm": adm, "exam": exm, "mon": mon, "fine": fine, "m": sel_m, "y": sel_y}
                        pdf, r_no, total = create_receipt(s_info, bill)
                        
                        # 1. Update Student Overall Status
                        supabase.table("students").update({"status": "Paid", "amount_paid": str(total)}).eq("id", target).execute()
                        
                        # 2. Insert into Monthly Tracking Table
                        supabase.table("fee_records").insert({
                            "student_id": target, "month": sel_m, "year": sel_y, 
                            "amount_paid": str(mon), "receipt_no": r_no
                        }).execute()
                        
                        st.success(f"Receipt {r_no} Generated!")
                        print_spot.download_button("🖨️ Print Receipt", pdf, f"Rec_{target}_{sel_m}.pdf")

        with t3:
            st.subheader("Monthly Payment Tracking Sheet")
            for _, row in df.iterrows():
                with st.expander(f"👤 {row['id']} - {row['name']} ({row['stream']})"):
                    report = get_monthly_report(row['id'])
                    cols = st.columns(4)
                    for i, item in enumerate(report):
                        with cols[i % 4]:
                            if "Pending" in item['Status']:
                                st.error(f"**{item['Month']}**\n\n{item['Status']}")
                            else:
                                st.success(f"**{item['Month']}**\n\n{item['Status']}")

    else:
        # Student View
        u = st.session_state.auth["user"]
        st.title(f"👋 Student Portal: {u['name']}")
        report = get_monthly_report(u['id'])
        
        st.subheader("Your Fee Status")
        cols = st.columns(6)
        for i, item in enumerate(report):
            cols[i % 6].write(f"{item['Month']}\n{item['Status']}")
        
        if st.button("Download Latest Admit Card"):
            pdf, _, _ = create_receipt(u, {"adm": 0, "exam": 0, "mon": 0, "fine": 0, "m": "N/A", "y": ""})
            st.download_button("Download", pdf, "Admit_Card.pdf")
