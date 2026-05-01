import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os

# --- 1. CONNECTION ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year", "3rd Year"]
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]

def fetch_students():
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data)

# --- 2. THE COMPLEX RECEIPT GENERATOR ---
def create_complex_receipt(s_info, billing_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(5, 5, 200, 180) # Slightly larger frame for details
    
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 10, 25)
    
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Skill Development & Paramedical Training", ln=True, align='C')
    pdf.ln(15)
    
    rec_no = f"OSDC-{random.randint(100000, 999999)}"
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"OFFICIAL FEE RECEIPT - {rec_no}", ln=True, align='C', fill=True)
    pdf.ln(5)
    
    # Student Details Section
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Name: {s_info['name']}")
    pdf.cell(95, 8, f"ID: {s_info['id']}", ln=True)
    pdf.cell(95, 8, f"Course: {s_info['stream']}")
    pdf.cell(95, 8, f"Year: {s_info['year_of_study']}", ln=True)
    pdf.ln(5)
    
    # Billing Table
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Description", border=1, fill=True)
    pdf.cell(50, 8, "Amount (INR)", border=1, ln=True, align='C', fill=True)
    
    pdf.set_font("Arial", '', 10)
    items = [
        ("Admission Fees", billing_data['adm']),
        ("Exam Fees", billing_data['exam']),
        (f"Monthly Fees ({billing_data['f_mon']} to {billing_data['t_mon']})", billing_data['mon']),
        ("Fine / Late Penalty", billing_data['fine'])
    ]
    
    total = 0
    for desc, amt in items:
        if int(amt) > 0:
            pdf.cell(140, 8, desc, border=1)
            pdf.cell(50, 8, f"{amt}/-", border=1, ln=True, align='C')
            total += int(amt)
            
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "GRAND TOTAL PAID", border=1)
    pdf.cell(50, 10, f"INR {total}/-", border=1, ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(95, 10, "Signature of Student")
    pdf.cell(95, 10, "Seal & Signature of Office", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1'), rec_no, total

# --- 3. APP LOGIC ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    # (Login code remains same as previous steps)
    st.title("🎓 Oxford Skill Development Centre")
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        # Student login logic here...
else:
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Institutional Management")
        df = fetch_students()
        
        tab1, tab2, tab3 = st.tabs(["🆕 Enrollment", "💳 Monthly Billing", "📈 Records"])
        
        with tab1:
            st.subheader("Add Student to Stream")
            with st.form("enroll_new"):
                c1, c2, c3 = st.columns(3)
                sid = c1.text_input("ID")
                sname = c2.text_input("Name")
                sphone = c3.text_input("Phone")
                stream = c1.selectbox("Stream/Course", COURSES)
                year = c2.selectbox("Academic Year", YEARS)
                spass = c3.text_input("Login Password")
                
                if st.form_submit_button("Register Student"):
                    supabase.table("students").insert({
                        "id": sid, "name": sname, "pass": spass, "phone": sphone, 
                        "stream": stream, "year_of_study": year, "status": "Pending"
                    }).execute()
                    st.success(f"Registered {sname} for {stream}")

        with tab2:
            st.subheader("Generate Monthly Receipt")
            if not df.empty:
                sid_select = st.selectbox("Search Student ID", df['id'].tolist())
                s_curr = df[df['id'] == sid_select].iloc[0]
                
                st.info(f"Student: {s_curr['name']} | Stream: {s_curr['stream']}")
                
                with st.form("bill_form"):
                    col_a, col_b = st.columns(2)
                    adm_f = col_a.number_input("Admission Fee", value=0)
                    exm_f = col_b.number_input("Exam Fee", value=0)
                    mon_f = col_a.number_input("Monthly Tuition Fee", value=0)
                    fine_f = col_b.number_input("Late Fine Amount", value=0)
                    
                    f_m = col_a.selectbox("From Month", MONTHS)
                    t_m = col_b.selectbox("To Month", MONTHS)
                    
                    if st.form_submit_button("Generate & Update Record"):
                        bill = {"adm": adm_f, "exam": exm_f, "mon": mon_f, "fine": fine_f, "f_mon": f_m, "t_mon": t_m}
                        pdf, r_no, total = create_complex_receipt(s_curr, bill)
                        
                        # Update Supabase
                        supabase.table("students").update({
                            "status": "Paid",
                            "admission_fees": str(adm_f),
                            "exam_fees": str(exm_f),
                            "monthly_fees": str(mon_f),
                            "fine_amount": str(fine_f),
                            "fees_from_month": f_m,
                            "fees_to_month": t_m,
                            "amount_paid": str(total),
                            "receipt_no": r_no
                        }).eq("id", sid_select).execute()
                        
                        st.success(f"Receipt {r_no} saved. Total: {total}/-")
                        st.download_button("🖨️ Print Final Receipt", pdf, f"Receipt_{sid_select}.pdf")

        with tab3:
            st.subheader("Year-Wise & Course-Wise Data")
            f_stream = st.multiselect("Filter by Course", COURSES, default=COURSES)
            f_year = st.multiselect("Filter by Year", YEARS, default=YEARS)
            
            filtered = df[df['stream'].isin(f_stream) & df['year_of_study'].isin(f_year)]
            st.dataframe(filtered, use_container_width=True)
