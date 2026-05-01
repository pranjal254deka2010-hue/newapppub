import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- 1. SIMULATED DATABASE (We will replace this with Google Sheets later) ---
if 'student_db' not in st.session_state:
    st.session_state.student_db = [
        {"id": "OSDC001", "name": "Pranjal Deka", "pass": "12345", "status": "Paid"},
        {"id": "OSDC002", "name": "Rahul Das", "pass": "phone123", "status": "Pending"}
    ]

# --- 2. THE PDF ENGINES ---
def create_admit_card(name, sid):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(190, 10, "OFFICIAL ADMIT CARD", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(100, 10, f"Student Name: {name}")
    pdf.cell(100, 10, f"Roll No: {sid}", ln=True)
    pdf.cell(190, 10, f"Date: {datetime.date.today()}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. THE LOGIN SHIELD ---
st.title("🎓 Oxford Skill Portal")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_data = None

if not st.session_state.logged_in:
    col1, col2 = st.columns(2)
    with col1:
        user_id = st.text_input("User ID / Student ID")
    with col2:
        password = st.text_input("Password", type="password")
    
    if st.button("Login to Portal"):
        # Check if Admin
        if user_id == "admin" and password == "oxford2026":
            st.session_state.logged_in = True
            st.session_state.user_role = "admin"
            st.rerun()
        
        # Check if Student
        else:
            student = next((s for s in st.session_state.student_db if s['id'] == user_id and s['pass'] == password), None)
            if student:
                st.session_state.logged_in = True
                st.session_state.user_role = "student"
                st.session_state.user_data = student
                st.rerun()
            else:
                st.error("Invalid Credentials. Please check your ID and Password.")

else:
    # --- LOGOUT BUTTON ---
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 4. TEACHER / ADMIN FRONT ---
    if st.session_state.user_role == "admin":
        st.sidebar.subheader("Teacher Dashboard")
        admin_mode = st.sidebar.radio("Go To", ["Enroll Students", "Fee Management", "Reminders"])

        if admin_mode == "Enroll Students":
            st.header("📝 Student Enrollment")
            with st.form("enroll_form"):
                new_name = st.text_input("Full Name")
                new_id = st.text_input("Create Student ID")
                new_pass = st.text_input("Set Password")
                if st.form_submit_button("Enroll Student"):
                    st.session_state.student_db.append({"id": new_id, "name": new_name, "pass": new_pass, "status": "Paid"})
                    st.success(f"Success! {new_name} is now enrolled.")

        elif admin_mode == "Fee Management":
            st.header("💰 Fee Records")
            df = pd.DataFrame(st.session_state.student_db)
            st.dataframe(df[['id', 'name', 'status']])
            
        elif admin_mode == "Reminders":
            st.header("🔔 Payment Reminders")
            pending = [s for s in st.session_state.student_db if s['status'] == "Pending"]
            for p in pending:
                st.warning(f"REMINDER: {p['name']} ({p['id']}) has not paid fees.")
                if st.button(f"Notify {p['name']}"):
                    st.info(f"Notification alert prepared for {p['name']}")

    # --- 5. STUDENT FRONT ---
    elif st.session_state.user_role == "student":
        student = st.session_state.user_data
        st.sidebar.subheader(f"Welcome, {student['name']}")
        
        # --- Student Notifications ---
        if student['status'] == "Pending":
            st.error("⚠️ ALERT: Your fees for this month are pending. Please visit the office.")
        else:
            st.success("✅ Your account is in good standing.")

        st.header(f"👋 Hello, {student['name']}")
        
        tab1, tab2 = st.tabs(["My Documents", "Profile"])
        
        with tab1:
            st.subheader("Download Center")
            if student['status'] == "Paid":
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Generate Admit Card"):
                        pdf_data = create_admit_card(student['name'], student['id'])
                        st.download_button("📥 Download PDF", pdf_data, "AdmitCard.pdf")
                with col_b:
                    st.button("Download Fee Receipt") # Same logic as Admit Card
            else:
                st.info("Documents are locked until fees are cleared.")

        with tab2:
            st.write(f"**Student ID:** {student['id']}")
            st.write(f"**Institute:** Oxford Skill Development Centre")
