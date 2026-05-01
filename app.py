import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Oxford Skill Portal", page_icon="🎓")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_students():
    # ttl=0 ensures live data from your Guwahati office updates
    return conn.read(worksheet="Students", ttl=0)

def update_students(df):
    conn.update(worksheet="Students", data=df)
    st.cache_data.clear()

# --- PDF GENERATOR ---
def create_pdf(title, name, sid, details):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, title, ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(100, 10, f"Student: {name}")
    pdf.cell(90, 10, f"ID: {sid}", ln=True)
    for k, v in details.items():
        pdf.cell(190, 10, f"{k}: {v}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN STATE ---
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.header("🔑 Oxford Skill Portal Login")
    uid = st.text_input("Enter ID")
    pwd = st.text_input("Enter Password", type="password")
    
    if st.button("Sign In"):
        if uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        else:
            try:
                df = fetch_students()
                user = df[(df['id'].astype(str) == str(uid)) & (df['pass'].astype(str) == str(pwd))]
                if not user.empty:
                    st.session_state.auth = {"logged_in": True, "role": "student", "user": user.iloc[0].to_dict()}
                    st.rerun()
                else:
                    st.error("Invalid ID or Password")
            except:
                st.error("Database Error: Please ensure headers are 'id', 'name', 'pass', 'status', 'phone'")

else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # --- TEACHER INTERFACE ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Administration")
        tab1, tab2 = st.tabs(["New Enrollment", "Database & Reminders"])
        
        with tab1:
            with st.form("enroll_student"):
                sid = st.text_input("Assign Student ID")
                sname = st.text_input("Full Name")
                spass = st.text_input("Set Password")
                sphone = st.text_input("Phone (No +91)")
                if st.form_submit_button("Enroll Now"):
                    df = fetch_students()
                    new_student = {"id": sid, "name": sname, "pass": spass, "status": "Paid", "phone": sphone}
                    update_students(pd.concat([df, pd.DataFrame([new_student])], ignore_index=True))
                    st.success(f"Successfully Enrolled {sname}!")

        with tab2:
            df = fetch_students()
            st.dataframe(df)
            st.subheader("⚠️ Send Fee Reminders")
            pending = df[df['status'] == "Pending"]
            for _, r in pending.iterrows():
                wa_msg = f"https://wa.me/91{r['phone']}?text=Fee%20Reminder%20from%20Oxford%20Skill%20Centre"
                st.markdown(f"[{r['name']} - Send WhatsApp]({wa_msg})")

    # --- STUDENT INTERFACE ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Hello, {u['name']}")
        
        # Verify status directly from Sheet
        df = fetch_students()
        current_status = df[df['id'].astype(str) == str(u['id'])]['status'].values[0]
        
        if current_status == "Pending":
            st.error("Document access restricted. Please clear pending fees at the office.")
        else:
            st.success("Your account is in good standing.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Get Admit Card"):
                    doc = create_pdf("ADMIT CARD", u['name'], u['id'], {"Exam": "Semester Finals 2026"})
                    st.download_button("Download PDF", doc, f"Admit_{u['id']}.pdf")
            with col2:
                if st.button("Get Last Receipt"):
                    doc = create_pdf("FEE RECEIPT", u['name'], u['id'], {"Type": "Monthly Tuition", "Status": "CLEARED"})
                    st.download_button("Download PDF", doc, f"Receipt_{u['id']}.pdf")
