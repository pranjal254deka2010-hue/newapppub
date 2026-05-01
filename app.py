import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os

# --- 1. CONNECTION & CONFIG ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year", "3rd Year"]
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]

def fetch_students():
    """Retrieves all student records from Supabase."""
    try:
        res = supabase.table("students").select("*").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

# --- 2. ADVANCED PDF GENERATOR ---
def create_complex_receipt(s_info, billing_data):
    pdf = FPDF()
    pdf.add_page()
    
    # Outer Border
    pdf.rect(5, 5, 200, 180)
    
    # Logo
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 10, 25)
    
    # Header
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Skill Development & Paramedical Training", ln=True, align='C')
    pdf.ln(15)
    
    # Receipt Banner
    rec_no = f"OSDC-{random.randint(100000, 999999)}"
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"OFFICIAL FEE RECEIPT - {rec_no}", ln=True, align='C', fill=True)
    pdf.ln(5)
    
    # Student Profile
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Student Name: {s_info['name']}")
    pdf.cell(95, 8, f"Student ID: {s_info['id']}", ln=True)
    pdf.cell(95, 8, f"Course/Stream: {s_info['stream']}")
    pdf.cell(95, 8, f"Academic Year: {s_info['year_of_study']}", ln=True)
    pdf.ln(5)
    
    # Billing Table Headers
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Description", border=1, fill=True)
    pdf.cell(50, 8, "Amount (INR)", border=1, ln=True, align='C', fill=True)
    
    pdf.set_font("Arial", '', 10)
    items = [
        ("Admission Fees", billing_data['adm']),
        ("Exam Fees", billing_data['exam']),
        (f"Monthly Fees ({billing_data['f_mon']} to {billing_data['t_mon']})", billing_data['mon']),
        ("Late Fine / Penalty", billing_data['fine'])
    ]
    
    total = 0
    for desc, amt in items:
        if int(amt) > 0:
            pdf.cell(140, 8, desc, border=1)
            pdf.cell(50, 8, f"{amt}/-", border=1, ln=True, align='C')
            total += int(amt)
            
    # Total Row
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "GRAND TOTAL PAID", border=1)
    pdf.cell(50, 10, f"INR {total}/-", border=1, ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(95, 10, "Signature of Student")
    pdf.cell(95, 10, "Office Seal & Signature", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1'), rec_no, total

# --- 3. APP INTERFACE ---
st.set_page_config(page_title="Oxford ERP Portal", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

# Login Page
if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    col1, _ = st.columns([1, 1])
    with col1:
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
                    else:
                        st.error("Invalid User ID or Password.")
                except Exception:
                    st.error("Database Connection Error.")

else:
    # Sidebar
    st.sidebar.title(f"Welcome, {st.session_state.auth['role'].capitalize()}")
    if st.sidebar.button("Log Out"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # ADMIN DASHBOARD
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Administrative Management")
        df = fetch_students()
        
        tab1, tab2, tab3 = st.tabs(["🆕 Enrollment", "💳 Billing & Fines", "📈 Records"])
        
        with tab1:
            st.subheader("New Student Registration")
            with st.form("enroll_form"):
                c1, c2, c3 = st.columns(3)
                new_sid = c1.text_input("Assign Student ID")
                new_name = c2.text_input("Full Name")
                new_phone = c3.text_input("Phone Number")
                new_stream = c1.selectbox("Course Stream", COURSES)
                new_year = c2.selectbox("Academic Year", YEARS)
                new_pass = c3.text_input("Login Password")
                
                if st.form_submit_button("Submit Enrollment"):
                    if new_sid and new_name:
                        supabase.table("students").insert({
                            "id": new_sid, "name": new_name, "pass": new_pass, 
                            "phone": new_phone, "stream": new_stream, 
                            "year_of_study": new_year, "status": "Pending"
                        }).execute()
                        st.success(f"Successfully Registered {new_name}")
                        st.rerun()

        with tab2:
            st.subheader("Generate & Print Receipt")
            if not df.empty:
                # Search student
                target_id = st.selectbox("Select Student for Billing", df['id'].tolist())
                s_curr = df[df['id'] == target_id].iloc[0]
                st.write(f"**Billing for:** {s_curr['name']} ({s_curr['stream']})")
                
                # Download container OUTSIDE the form to avoid API exception
                print_container = st.container()
                
                with st.form("billing_logic"):
                    ca, cb = st.columns(2)
                    f_adm = ca.number_input("Admission Fee", min_value=0, value=0)
                    f_exm = cb.number_input("Exam Fee", min_value=0, value=0)
                    f_mon = ca.number_input("Monthly Fee", min_value=0, value=0)
                    f_fine = cb.number_input("Late Fine", min_value=0, value=0)
                    m_from = ca.selectbox("Paid From", MONTHS)
                    m_to = cb.selectbox("Paid To", MONTHS)
                    
                    if st.form_submit_button("Save & Generate PDF"):
                        bill_pkg = {"adm": f_adm, "exam": f_exm, "mon": f_mon, "fine": f_fine, "f_mon": m_from, "t_mon": m_to}
                        pdf_bytes, r_no, g_total = create_complex_receipt(s_curr, bill_pkg)
                        
                        # Update database
                        supabase.table("students").update({
                            "status": "Paid", "admission_fees": str(f_adm), "exam_fees": str(f_exm),
                            "monthly_fees": str(f_mon), "fine_amount": str(f_fine),
                            "fees_from_month": m_from, "fees_to_month": m_to,
                            "amount_paid": str(g_total), "receipt_no": r_no
                        }).eq("id", target_id).execute()
                        
                        st.success(f"Billing recorded! Receipt: {r_no}")
                        print_container.download_button(
                            label="🖨️ Click Here to Print Receipt",
                            data=pdf_bytes,
                            file_name=f"Receipt_{target_id}.pdf",
                            mime="application/pdf"
                        )
            else:
                st.info("Enroll students first.")

        with tab3:
            st.subheader("Student Database Records")
            st.dataframe(df, use_container_width=True)

    # STUDENT VIEW
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        
        # Check current status
        res = supabase.table("students").select("*").eq("id", u['id']).execute()
        s = res.data[0]

        if s['status'] == "Pending":
            st.error("Dues Pending. Please clear your fees at the office to access your documents.")
        else:
            st.success(f"Account Active. Last payment: INR {s.get('amount_paid', '0')}/-")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Download Admit Card"):
                    # Quick Admit Card generation using the same branded logic
                    details = {"Course": s['stream'], "Year": s['year_of_study'], "Session": "2026"}
                    pdf_bytes, _, _ = create_complex_receipt(s, {"adm": 0, "exam": 0, "mon": 0, "fine": 0, "f_mon": "N/A", "t_mon": "N/A"})
                    st.download_button("Download Admit Card", pdf_bytes, "Admit_Card.pdf")
            with col2:
                if s.get('receipt_no'):
                    # Regenerate the last receipt based on stored DB values
                    old_bill = {
                        "adm": s['admission_fees'], "exam": s['exam_fees'], 
                        "mon": s['monthly_fees'], "fine": s['fine_amount'],
                        "f_mon": s['fees_from_month'], "t_mon": s['fees_to_month']
                    }
                    pdf_bytes, _, _ = create_complex_receipt(s, old_bill)
                    st.download_button("Download Last Receipt", pdf_bytes, "Fee_Receipt.pdf")
