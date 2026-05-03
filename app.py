import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os

# --- 1. CONFIG ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year"]
MONTH_LIST = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]

# --- 2. HELPERS ---
def fetch_data(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data)

def generate_receipt_pdf(s_info, bill):
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(5, 5, 200, 287)
    
    # Header
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(190, 15, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, "Dhupdhara, Assam | Skill Development & Paramedical Training", ln=True, align='C')
    pdf.ln(10)
    
    # Receipt Info
    r_no = f"OSDC-PAY-{random.randint(1000, 9999)}"
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"PAYMENT RECEIPT: {r_no}", ln=True, align='C', fill=True)
    pdf.ln(5)
    
    # Details
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Student Name: {s_info['name']}")
    pdf.cell(95, 8, f"Student ID: {s_info['id']}", ln=True)
    pdf.cell(95, 8, f"Course: {s_info['stream']}")
    pdf.cell(95, 8, f"Year: {s_info['year_of_study']}", ln=True)
    pdf.cell(190, 8, f"Date: {datetime.date.today().strftime('%d-%b-%Y')}", ln=True)
    pdf.ln(5)
    
    # Table Header
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Description", border=1)
    pdf.cell(50, 10, "Amount (INR)", border=1, ln=True, align='C')
    
    # Table Body
    pdf.set_font("Arial", '', 11)
    items = [
        (f"Monthly Fee ({bill['month']} {bill['year']})", bill['amount']),
        ("Fine/Late Fees", bill['fine'])
    ]
    total = 0
    for desc, amt in items:
        if int(amt) > 0:
            pdf.cell(140, 10, desc, border=1)
            pdf.cell(50, 10, f"{amt}/-", border=1, ln=True, align='C')
            total += int(amt)
            
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 12, "GRAND TOTAL", border=1)
    pdf.cell(50, 12, f"INR {total}/-", border=1, ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(190, 5, "This is a computer-generated receipt.", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1'), r_no

# --- 3. AUTH ---
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
            # Simple check for demo, can link to a 'teachers' table
            if pwd == "teacher123":
                st.session_state.auth = {"logged_in": True, "role": "teacher", "user": uid}
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
        st.sidebar.title("Admin Panel")
        if st.sidebar.button("Logout"):
            st.session_state.auth = {"logged_in": False}; st.rerun()
            
        df = fetch_data("students")
        t1, t2, t3 = st.tabs(["🆕 Student Enrollment", "💰 Collect Payment", "📋 Records & Passwords"])
        
        with t1:
            with st.form("enroll"):
                c1, c2 = st.columns(2)
                sid = c1.text_input("New Student ID")
                sname = c2.text_input("Full Name")
                sphone = c1.text_input("Phone Number")
                spass = c2.text_input("Set Password")
                strm = c1.selectbox("Course", COURSES)
                yr = c2.selectbox("Year", YEARS)
                if st.form_submit_button("Register Student"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "stream": strm, "year_of_study": yr}).execute()
                    st.success("Enrolled Successfully!"); st.rerun()
        
        with t2:
            if not df.empty:
                target_id = st.selectbox("Select Student", df['id'].tolist())
                s_info = df[df['id'] == target_id].iloc[0]
                with st.form("pay"):
                    c1, c2 = st.columns(2)
                    amt = c1.number_input("Monthly Fee Amount", min_value=0)
                    fine = c2.number_input("Fine (if any)", min_value=0)
                    m = c1.selectbox("For Month", MONTH_LIST)
                    y = c2.selectbox("For Year", ["2026", "2027", "2028"])
                    if st.form_submit_button("Process Payment & Generate Receipt"):
                        bill = {"amount": amt, "fine": fine, "month": m, "year": y}
                        pdf, r_no = generate_receipt_pdf(s_info, bill)
                        supabase.table("fee_records").insert({"student_id": target_id, "month": m, "year": y, "amount_paid": str(amt+fine), "receipt_no": r_no}).execute()
                        st.success(f"Payment Successful! Receipt {r_no} ready.")
                        st.download_button("📥 Download Receipt", pdf, f"Receipt_{r_no}.pdf")
        
        with t3:
            st.dataframe(df[['id', 'name', 'stream', 'year_of_study', 'pass', 'phone']], use_container_width=True)

    # --- TEACHER SIDE ---
    elif st.session_state.auth["role"] == "teacher":
        st.title(f"👨‍🏫 Teacher Dashboard ({st.session_state.auth['user']})")
        if st.button("Logout"): st.session_state.auth = {"logged_in": False}; st.rerun()
        
        with st.form("upload_notes"):
            st.subheader("Upload Study Material")
            title = st.text_input("Title of the Notes")
            course = st.selectbox("For Course", COURSES)
            file = st.file_uploader("Select PDF File", type=["pdf"])
            if st.form_submit_button("Post to Students"):
                if file:
                    path = f"notes/{random.randint(100,999)}_{file.name}"
                    supabase.storage.from_("notes").upload(path, file.getvalue())
                    url = supabase.storage.from_("notes").get_public_url(path)
                    supabase.table("study_material").insert({"teacher_id": st.session_state.auth['user'], "title": title, "course": course, "file_url": url}).execute()
                    st.success("Notes published successfully!")

    # --- STUDENT SIDE ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        if st.button("Logout"): st.session_state.auth = {"logged_in": False}; st.rerun()
        
        t1, t2 = st.tabs(["📚 Study Materials", "💸 My Payment History"])
        
        with t1:
            st.subheader(f"Notes for {u['stream']}")
            notes = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
            if notes:
                for n in notes:
                    st.info(f"📄 **{n['title']}**")
                    st.markdown(f"[Download PDF]({n['file_url']})")
            else:
                st.write("No notes available for your course yet.")
        
        with t2:
            st.subheader("Payment Records")
            history = supabase.table("fee_records").select("*").eq("student_id", u['id']).execute().data
            if history:
                for h in history:
                    st.success(f"✅ {h['month']} {h['year']} - Amount: ₹{h['amount_paid']} (Receipt: {h['receipt_no']})")
            else:
                st.write("No payment history found.")
