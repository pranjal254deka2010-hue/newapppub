import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os

# --- 1. CONFIG & SESSION SETTINGS ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year"]
# Standard tracking from May to May
SESSION_MONTHS = ["May", "June", "July", "August", "September", "October", "November", "December", 
                  "January", "February", "March", "April"]

# --- 2. DATA HELPERS ---
def fetch_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

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
    pdf.cell(95, 8, f"Name: {s_info['name']}")
    pdf.cell(95, 8, f"ID: {s_info['id']}", ln=True)
    pdf.cell(190, 8, f"Description: {bill['desc']} ({bill['month']} {bill['year']})", ln=True)
    pdf.cell(190, 12, f"TOTAL PAID: INR {bill['total']}/-", border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1'), r_no

# --- 3. APP INTERFACE ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford ERP Login")
    role = st.selectbox("Role", ["Admin", "Teacher", "Student"])
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if role == "Admin" and uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        elif role == "Teacher" and pwd == "teacher123":
            st.session_state.auth = {"logged_in": True, "role": "teacher", "user": uid}
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

    if st.session_state.auth["role"] == "admin":
        df = fetch_data("students")
        t1, t2, t3 = st.tabs(["🆕 Enrollment", "💰 Payments", "📊 Detailed Records"])

        with t1:
            with st.form("enroll"):
                c1, c2 = st.columns(2)
                sid, sname = c1.text_input("ID"), c2.text_input("Full Name")
                strm, yr = c1.selectbox("Course", COURSES), c2.selectbox("Year", YEARS)
                spass = st.text_input("Set Password")
                if st.form_submit_button("Register"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "stream": strm, "year_of_study": yr}).execute()
                    st.success("Student Enrolled!"); st.rerun()

        with t2:
            if not df.empty:
                target = st.selectbox("Select Student", df['id'].tolist())
                s_info = df[df['id'] == target].iloc[0]
                with st.form("pay"):
                    c1, c2 = st.columns(2)
                    p_type = c1.selectbox("Payment Type", ["Monthly Fee", "Exam Fee", "Admission Fee", "Fine"])
                    amt = c2.number_input("Amount (INR)", min_value=0)
                    m_val = c1.selectbox("Month", SESSION_MONTHS)
                    y_val = c2.selectbox("Year", ["2026", "2027", "2028"])
                    if st.form_submit_button("Confirm Payment"):
                        pdf, r_no = generate_receipt_pdf(s_info, {"desc": p_type, "total": amt, "month": m_val, "year": y_val})
                        supabase.table("fee_records").insert({"student_id": target, "month": m_val, "year": y_val, "amount_paid": str(amt), "receipt_no": r_no, "fee_type": p_type}).execute()
                        st.success(f"Receipt {r_no} Generated!"); st.download_button("Download", pdf, f"Receipt_{r_no}.pdf")

        with t3:
            st.subheader("📊 Financial Monitoring Sheet")
            if not df.empty:
                for _, row in df.iterrows():
                    # Fetch all payments for this student
                    history = supabase.table("fee_records").select("*").eq("student_id", row['id']).order("created_at", desc=True).execute().data
                    paid_months = [h['month'] for h in history if h['fee_type'] == "Monthly Fee"]
                    
                    last_date = history[0]['created_at'][:10] if history else "Never Paid"
                    
                    with st.expander(f"👤 {row['name']} | Last Payment: {last_date} | Password: {row['pass']}"):
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            st.write("**Payment History**")
                            if history:
                                st.table(pd.DataFrame(history)[['month', 'year', 'fee_type', 'amount_paid']])
                        with col2:
                            st.write("**Pending Monthly Fees (Session: May-April)**")
                            for m in SESSION_MONTHS:
                                if m in paid_months:
                                    st.success(f"✅ {m}: Paid")
                                else:
                                    st.error(f"❌ {m}: Pending")

    elif st.session_state.auth["role"] == "teacher":
        st.title("👨‍🏫 Teacher Notes Portal")
        with st.form("notes"):
            title = st.text_input("Notes Title")
            crs = st.selectbox("Course", COURSES)
            f = st.file_uploader("Upload PDF", type=["pdf"])
            if st.form_submit_button("Upload"):
                if f:
                    path = f"notes/{random.randint(100,999)}_{f.name}"
                    supabase.storage.from_("notes").upload(path, f.getvalue())
                    url = supabase.storage.from_("notes").get_public_url(path)
                    supabase.table("study_material").insert({"title": title, "course": crs, "file_url": url}).execute()
                    st.success("Notes Shared!")

    else:
        # Student Dashboard
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome {u['name']}")
        notes = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
        for n in notes: st.info(f"📄 {n['title']} ([Download]({n['file_url']}))")
