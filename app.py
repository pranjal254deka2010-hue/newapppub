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
    try:
        res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).execute()
        paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    except:
        paid_list = []
    
    report = []
    if current_year_status == "1st Year":
        timeline = [ (m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2027") for m in STANDARD_MONTHS ] + \
                   [ (m, "2028") for m in ["January", "February", "March", "April", "May"] ]
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
    pdf.rect(5, 5, 200, 185)
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 10, 25)
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Skill Development & Paramedical Training", ln=True, align='C')
    pdf.ln(15)
    
    r_no = f"OSDC-{random.randint(100000, 999999)}"
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
    total = 0
    fees = [("Admission Fees", bill['adm']), ("Exam Fees", bill['exam']), 
            (f"Monthly Fee ({bill['m']} {bill['y']})", bill['mon']), ("Late Fine / Penalty", bill['fine'])]
    for desc, amt in fees:
        if int(amt) > 0:
            pdf.cell(140, 8, desc, border=1)
            pdf.cell(50, 8, f"{amt}/-", border=1, ln=True, align='C')
            total += int(amt)
            
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "GRAND TOTAL PAID", border=1)
    pdf.cell(50, 10, f"INR {total}/-", border=1, ln=True, align='C')
    pdf.ln(20)
    pdf.cell(95, 10, "Signature of Student")
    pdf.cell(95, 10, "Authorized Signatory", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1'), r_no, total

# --- 3. MAIN APP ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
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
        
        # ADDED "STUDENT RECORDS" TAB HERE
        t1, t2, t3, t4 = st.tabs(["🆕 Enrollment", "💳 Billing", "📋 Monthly Tracking", "📂 Student Records"])
        
        with t1:
            with st.form("enroll"):
                c1, c2, c3 = st.columns(3)
                sid, sname, sphone = c1.text_input("Student ID"), c2.text_input("Name"), c3.text_input("Phone")
                stream, year, spass = c1.selectbox("Stream", COURSES), c2.selectbox("Current Year", YEARS), c3.text_input("Password")
                if st.form_submit_button("Register"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "stream": stream, "year_of_study": year, "status": "Pending"}).execute()
                    st.success("Enrolled!"); st.rerun()

        with t2:
            if not df.empty:
                target = st.selectbox("Select Student", df['id'].tolist())
                s_info = df[df['id'] == target].iloc[0]
                print_spot = st.container()
                with st.form("billing"):
                    ca, cb = st.columns(2)
                    adm, exm, mon, fine = ca.number_input("Admission Fee", 0), cb.number_input("Exam Fee", 0), ca.number_input("Monthly Fee", 0), cb.number_input("Fine", 0)
                    sel_m, sel_y = ca.selectbox("Month", STANDARD_MONTHS, index=4), cb.selectbox("Year", ["2026", "2027", "2028"])
                    if st.form_submit_button("Generate Receipt"):
                        bill = {"adm": adm, "exam": exm, "mon": mon, "fine": fine, "m": sel_m, "y": sel_y}
                        pdf, r_no, total = create_receipt(s_info, bill)
                        supabase.table("fee_records").insert({"student_id": target, "month": sel_m, "year": sel_y, "amount_paid": str(mon), "receipt_no": r_no}).execute()
                        st.success(f"Receipt {r_no} Generated!")
                        print_spot.download_button("🖨️ Print Receipt", pdf, f"Rec_{target}.pdf")

        with t3:
            st.subheader("📊 Session-wise Fee Monitoring")
            for _, row in df.iterrows():
                with st.expander(f"👤 {row['id']} | {row['name']}"):
                    report = get_monthly_report(row['id'], row['year_of_study'])
                    cols = st.columns(4)
                    for i, item in enumerate(report):
                        with cols[i % 4]:
                            if item['status'] == "PAID": st.success(f"**{item['label']}**")
                            else: st.error(f"**{item['label']}**")

        # NEW: STUDENT RECORDS TAB LOGIC
        with t4:
            st.subheader("📂 Complete Student Directory")
            if not df.empty:
                # Filters
                f1, f2 = st.columns(2)
                filter_course = f1.multiselect("Filter by Course", COURSES, default=COURSES)
                filter_year = f2.multiselect("Filter by Year", YEARS, default=YEARS)
                
                # Applying Filters
                filtered_df = df[df['stream'].isin(filter_course) & df['year_of_study'].isin(filter_year)]
                
                # Display Summary
                st.write(f"Showing **{len(filtered_df)}** students.")
                
                # Table with Passwords Visible
                st.table(filtered_df[['id', 'name', 'stream', 'year_of_study', 'phone', 'pass']])
            else:
                st.info("No records found.")

    else:
        # Student View
        u = st.session_state.auth["user"]
        st.title(f"👋 Student Portal: {u['name']}")
        report = get_monthly_report(u['id'], u['year_of_study'])
        st.subheader("Your Fee Status")
        cols = st.columns(6)
        for i, item in enumerate(report):
            cols[i % 6].write(f"{item['label']}\n{item['status']}")
