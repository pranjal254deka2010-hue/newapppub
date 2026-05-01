import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Oxford Skill Portal", page_icon="🎓")

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_students():
    # ttl=0 ensures live data updates immediately
    # spreadsheet=... points directly to the secret URL to avoid HTTP errors
    return conn.read(
        spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"],
        worksheet="Students", 
        ttl=0
    )

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
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    
    if st.button("Sign In"):
        if uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        else:
            try:
                df = fetch_students()
                # Clean strings for exact matching
                df['id'] = df['id'].astype(str).str.strip()
                df['pass'] = df['pass'].astype(str).str.strip()
                
                user = df[(df['id'] == str(uid)) & (df['pass'] == str(pwd))]
                if not user.empty:
                    st.session_state.auth = {"logged_in": True, "role": "student", "user": user.iloc[0].to_dict()}
                    st.rerun()
                else:
                    st.error("Invalid ID or Password")
            except Exception as e:
                st.error("Connection Error: Please check your Google Sheet headers ('id', 'name', 'pass', 'status', 'phone')")

else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # --- TEACHER / ADMIN FRONT ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Control Panel")
        tab1, tab2 = st.tabs(["Enrollment", "Student Records & Reminders"])
        
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
            st.subheader("⚠️ WhatsApp Fee Reminders")
            pending = df[df['status'].str.lower() == "pending"]
            for _, r in pending.iterrows():
                wa_msg = f"https://wa.me/91{r['phone']}?text=Fee%20Reminder%20from%20Oxford%20Skill%20Centre"
                st.markdown(f"[{r['name']} - Send WhatsApp Reminder]({wa_msg})")

    # --- STUDENT FRONT ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        
        # Fresh status check from the sheet
        df_now = fetch_students()
        current_status = df_now[df_now['id'].astype(str) == str(u['id'])]['status'].values[0]
        
        if current_status.lower() == "pending":
            st.error("Your fees are currently pending. Downloads are locked until cleared at the office.")
        else:
            st.success("Your account is in good standing.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Generate Admit Card"):
                    doc = create_pdf("ADMIT CARD", u['name'], u['id'], {"Exam": "Term Finals 2026", "Venue": "Oxford Campus"})
                    st.download_button("Download Admit Card", doc, f"Admit_{u['id']}.pdf")
            with col2:
                if st.button("Generate Last Receipt"):
                    doc = create_pdf("FEE RECEIPT", u['name'], u['id'], {"Type": "Monthly Fee", "Status": "CLEARED"})
                    st.download_button("Download Receipt", doc, f"Receipt_{u['id']}.pdf")
