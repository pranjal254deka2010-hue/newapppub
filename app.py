import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Oxford Skill Portal", page_icon="🎓", layout="centered")

# --- 2. DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_students():
    # Read data from the 'Students' worksheet
    return conn.read(worksheet="Students", ttl="0")

def update_students(df):
    # Update the Google Sheet with the new dataframe
    conn.update(worksheet="Students", data=df)
    st.cache_data.clear()

# --- 3. DOCUMENT GENERATOR (PDF) ---
def create_pdf_doc(title, student_name, student_id, details):
    pdf = FPDF()
    pdf.add_page()
    
    # Border
    pdf.rect(5, 5, 200, 100)
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, "Guwahati, Assam | Digital Student Portal", ln=True, align='C')
    pdf.ln(10)
    
    # Document Title
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, title.upper(), ln=True, align='C')
    pdf.ln(5)
    
    # Content
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, f"Name: {student_name}")
    pdf.cell(100, 10, f"ID: {student_id}", ln=True)
    pdf.cell(200, 10, f"Date: {datetime.date.today()}", ln=True)
    
    for key, value in details.items():
        pdf.cell(200, 10, f"{key}: {value}", ln=True)
    
    pdf.ln(15)
    pdf.cell(190, 10, "Authorized Signatory", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user = None

if not st.session_state.logged_in:
    st.header("🔑 Oxford Skill Portal Login")
    user_input = st.text_input("Student ID / Admin Username")
    pass_input = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # Admin Login (Hardcoded for you)
        if user_input == "admin" and pass_input == "oxford2026":
            st.session_state.logged_in = True
            st.session_state.role = "admin"
            st.rerun()
        
        # Student Login (Checking Google Sheet)
        else:
            try:
                df = fetch_students()
                # Clean data to ensure strings match
                df['id'] = df['id'].astype(str)
                df['pass'] = df['pass'].astype(str)
                
                match = df[(df['id'] == user_input) & (df['pass'] == pass_input)]
                
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.role = "student"
                    st.session_state.user = match.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Invalid ID or Password.")
            except Exception as e:
                st.error("System Error: Ensure Google Sheet headers match 'id', 'name', 'pass', 'status', 'phone'")

else:
    # --- LOGOUT ---
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 5. TEACHER / ADMIN DASHBOARD ---
    if st.session_state.role == "admin":
        st.title("🛡️ Admin Management")
        menu = st.sidebar.radio("Menu", ["Enroll New Student", "Student Directory & Fees", "Quick Reminders"])

        if menu == "Enroll New Student":
            st.subheader("📝 Register Student")
            with st.form("reg_form"):
                n_id = st.text_input("Assign Student ID (e.g., OSDC001)")
                n_name = st.text_input("Full Name")
                n_pass = st.text_input("Set Password")
                n_phone = st.text_input("Phone Number")
                n_status = st.selectbox("Initial Fee Status", ["Paid", "Pending"])
                
                if st.form_submit_button("Enroll Student"):
                    df = fetch_students()
                    new_row = {"id": n_id, "name": n_name, "pass": n_pass, "status": n_status, "phone": n_phone}
                    updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    update_students(updated_df)
                    st.success(f"Enrolled {n_name} successfully!")

        elif menu == "Student Directory & Fees":
            st.subheader("📋 Student Records")
            df = fetch_students()
            st.dataframe(df)
            
            st.divider()
            st.subheader("🔄 Update Fee Status")
            target_id = st.selectbox("Select Student ID", df['id'].tolist())
            new_stat = st.radio("New Status", ["Paid", "Pending"], horizontal=True)
            if st.button("Update Status"):
                df.loc[df['id'] == target_id, 'status'] = new_stat
                update_students(df)
                st.success("Status Updated!")

        elif menu == "Quick Reminders":
            st.subheader("🔔 Fee Overdue List")
            df = fetch_students()
            pending = df[df['status'] == "Pending"]
            if not pending.empty:
                for _, row in pending.iterrows():
                    st.warning(f"Pending: {row['name']} ({row['phone']})")
                    # WhatsApp Link
                    wa_link = f"https://wa.me/91{row['phone']}?text=Hello%20{row['name']},%20this%20is%20Oxford%20Skill%20Centre.%20Your%20fees%20are%20currently%20pending."
                    st.markdown(f"[Send WhatsApp Reminder to {row['name']}]( {wa_link} )")
            else:
                st.success("No pending fees found!")

    # --- 6. STUDENT DASHBOARD ---
    elif st.session_state.role == "student":
        user = st.session_state.user
        st.title(f"👋 Welcome, {user['name']}")
        
        # Fresh data fetch for status check
        df_fresh = fetch_students()
        current_status = df_fresh[df_fresh['id'] == user['id']]['status'].values[0]

        if current_status == "Pending":
            st.error("🔴 ATTENTION: Your fees are pending. Document downloads are locked.")
        else:
            st.success("🟢 Your account is active. You may download your documents below.")

        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🪪 Admit Card")
            if current_status == "Paid":
                if st.button("Generate Admit Card"):
                    pdf = create_pdf_doc("Admit Card", user['name'], user['id'], {"Exam": "Term Examination 2026", "Venue": "Oxford Main Hall"})
                    st.download_button("📥 Download PDF", pdf, f"Admit_{user['id']}.pdf")
            else:
                st.lock_icon()

        with col2:
            st.subheader("🧾 Fee Receipt")
            if current_status == "Paid":
                if st.button("Generate Last Receipt"):
                    pdf = create_pdf_doc("Fee Receipt", user['name'], user['id'], {"Purpose": "Course Monthly Fee", "Status": "Paid"})
                    st.download_button("📥 Download PDF", pdf, f"Receipt_{user['id']}.pdf")
            else:
                st.lock_icon()
