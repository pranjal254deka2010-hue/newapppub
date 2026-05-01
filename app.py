import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random

# --- 1. DATABASE CONNECTION ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

def fetch_students():
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data)

# --- 2. ENHANCED RECEIPT GENERATOR ---
def create_receipt_pdf(name, sid, amount, phone):
    pdf = FPDF()
    pdf.add_page()
    
    # Outer Border
    pdf.rect(5, 5, 200, 140) # Half-page receipt
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Recognized Educational Institute", ln=True, align='C')
    pdf.ln(10)
    
    # Receipt Info
    r_no = f"OSDC-REC-{random.randint(1000, 9999)}"
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 10, f"MONEY RECEIPT - {r_no}", ln=True, align='C', fill=True)
    pdf.ln(5)
    
    # Body
    pdf.set_font("Arial", '', 12)
    pdf.cell(95, 10, f"Date: {datetime.date.today()}")
    pdf.cell(95, 10, f"Student ID: {sid}", ln=True)
    pdf.cell(190, 10, f"Received with thanks from: {name}", ln=True)
    pdf.cell(190, 10, f"Contact Number: {phone}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 15, f"AMOUNT PAID: INR {amount}/-", border=1, ln=True, align='C')
    
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(95, 10, "Student Signature")
    pdf.cell(95, 10, "Authorized Signatory", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1'), r_no

# --- 3. INTERFACE ---
st.set_page_config(page_title="Oxford Admin & Billing", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Portal")
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
    # --- ADMIN VIEW ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Billing & Records")
        df = fetch_students()
        
        tab1, tab2, tab3 = st.tabs(["👥 Enrollment", "💰 Fees & Receipts", "📊 Database"])
        
        with tab1:
            # (Enrollment code stays same as previous)
            with st.form("enroll"):
                c1, c2 = st.columns(2)
                sid = c1.text_input("Student ID")
                sname = c2.text_input("Full Name")
                spass = c1.text_input("Password")
                sphone = c2.text_input("Phone")
                if st.form_submit_button("Enroll Student"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "status": "Pending"}).execute()
                    st.success("Enrolled!")

        with tab2:
            st.subheader("Generate Official Receipt")
            target = st.selectbox("Select Student", df['id'].tolist() if not df.empty else [])
            amount = st.number_input("Amount Received (INR)", min_value=0)
            
            if st.button("Generate & Save Receipt"):
                student_data = df[df['id'] == target].iloc[0]
                pdf_data, rec_no = create_receipt_pdf(student_data['name'], target, amount, student_data['phone'])
                
                # Save to database so student sees it
                supabase.table("students").update({
                    "status": "Paid", 
                    "amount_paid": str(amount),
                    "receipt_no": rec_no
                }).eq("id", target).execute()
                
                st.success(f"Receipt {rec_no} generated!")
                st.download_button("🖨️ Print Receipt Now", pdf_data, f"Receipt_{target}.pdf")

        with tab3:
            st.dataframe(fetch_students())

    # --- STUDENT VIEW ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        
        # Check current data
        res = supabase.table("students").select("*").eq("id", u['id']).execute()
        s = res.data[0]

        if s['status'] == "Pending":
            st.error("Fees Pending. Please clear your dues at the office.")
        else:
            st.success(f"Fees Paid: INR {s.get('amount_paid', '0')}")
            if s.get('receipt_no'):
                st.info(f"Last Receipt No: {s['receipt_no']}")
                
            if st.button("📥 Download My Receipt"):
                pdf_data, _ = create_receipt_pdf(s['name'], s['id'], s['amount_paid'], s['phone'])
                st.download_button("Click to Download", pdf_data, "My_Receipt.pdf")
