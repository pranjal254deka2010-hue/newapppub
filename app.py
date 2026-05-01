import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os

# --- 1. DATABASE CONNECTION ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

def fetch_students():
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data)

# --- 2. BRANDED PDF GENERATOR ---
def create_branded_pdf(title, name, sid, details, is_receipt=False):
    pdf = FPDF()
    pdf.add_page()
    
    # Border
    pdf.rect(5, 5, 200, 287 if not is_receipt else 140)
    
    # Logo Placement (Checks if logo.png exists in the folder)
    if os.path.exists("logo.png"):
        # Image(path, x, y, width)
        pdf.image("logo.png", 10, 10, 25)
    
    # Header
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Skill Development & Paramedical Training", ln=True, align='C')
    pdf.ln(15)
    
    # Title Section
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 12, title.upper(), ln=True, align='C', fill=True)
    pdf.ln(10)
    
    # Body
    pdf.set_font("Arial", size=12)
    pdf.cell(95, 10, f"Student Name: {name}", border=1)
    pdf.cell(95, 10, f"Student ID: {sid}", border=1, ln=True)
    
    for k, v in details.items():
        pdf.cell(190, 10, f"{k}: {v}", border=1, ln=True)
    
    # Footer
    pdf.ln(25)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 10, "Student's Signature", align='L')
    pdf.cell(95, 10, "Authorized Signatory", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INTERFACE ---
st.set_page_config(page_title="Oxford Skill Centre", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    st.markdown("### Secure Administrative & Student Portal")
    
    col1, _ = st.columns([1, 1])
    with col1:
        uid = st.text_input("User ID")
        pwd = st.text_input("Password", type="password")
        if st.button("Log In", use_container_width=True):
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
                        st.error("Invalid credentials.")
                except:
                    st.error("Connection error.")

else:
    # Sidebar Logout
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Dashboard")
        df = fetch_students()
        
        tab1, tab2, tab3 = st.tabs(["🆕 Enrollment", "💰 Fees & Receipts", "👥 Database"])
        
        with tab1:
            st.subheader("New Registration")
            with st.form("reg"):
                c1, c2 = st.columns(2)
                sid = c1.text_input("ID")
                sname = c2.text_input("Name")
                spass = c1.text_input("Pass")
                sphone = c2.text_input("Phone")
                if st.form_submit_button("Enroll"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "status": "Pending"}).execute()
                    st.success("Enrolled.")
                    st.rerun()

        with tab2:
            st.subheader("Billing Section")
            if not df.empty:
                target = st.selectbox("Select Student", df['id'].tolist())
                amt = st.number_input("Amount (INR)", min_value=0)
                if st.button("Generate & Save Receipt"):
                    s_info = df[df['id'] == target].iloc[0]
                    rec_no = f"REC-{random.randint(10000, 99999)}"
                    
                    # Update database
                    supabase.table("students").update({
                        "status": "Paid", 
                        "amount_paid": str(amt),
                        "receipt_no": rec_no
                    }).eq("id", target).execute()
                    
                    # Generate PDF
                    pdf = create_branded_pdf("MONEY RECEIPT", s_info['name'], target, {
                        "Receipt No": rec_no,
                        "Amount Paid": f"INR {amt}/-",
                        "Payment Status": "SUCCESSFUL"
                    }, is_receipt=True)
                    
                    st.success(f"Receipt Generated for {s_info['name']}")
                    st.download_button("🖨️ Print Receipt", pdf, f"Receipt_{target}.pdf")

        with tab3:
            st.dataframe(df, use_container_width=True)

    else:
        # Student View
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        
        # Check status
        res = supabase.table("students").select("*").eq("id", u['id']).execute()
        s = res.data[0]

        if s['status'] == "Pending":
            st.error("Fees Pending. Please clear dues to access documents.")
        else:
            st.success("Account Active.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Download Admit Card"):
                    pdf = create_branded_pdf("ADMIT CARD", s['name'], s['id'], {"Session": "2026", "Exam": "Skill Assessment"})
                    st.download_button("Download Now", pdf, "Admit_Card.pdf")
            with c2:
                if s.get('receipt_no'):
                    if st.button("Download Last Receipt"):
                        pdf = create_branded_pdf("MONEY RECEIPT", s['name'], s['id'], {
                            "Receipt No": s['receipt_no'],
                            "Amount Paid": f"INR {s['amount_paid']}/-"
                        }, is_receipt=True)
                        st.download_button("Download Now", pdf, "Receipt.pdf")
