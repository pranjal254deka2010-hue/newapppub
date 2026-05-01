import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import datetime

# --- 1. SECURE CONNECTION TO GOOGLE SHEETS ---
def get_gspread_client():
    # Everything inside this function MUST be indented
    info = dict(st.secrets["gcp_service_account"])
    
    # This fix handles the private key formatting perfectly
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        
    creds = Credentials.from_service_account_info(
        info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

def fetch_students():
    client = get_gspread_client()
    # Your specific Spreadsheet ID
    sheet = client.open_by_key("1koS82MP0W-vlFXsZCcED6qdUzMgLOnYkwaGY35firh8").worksheet("Students")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def update_students(df):
    client = get_gspread_client()
    sheet = client.open_by_key("1koS82MP0W-vlFXsZCcED6qdUzMgLOnYkwaGY35firh8").worksheet("Students")
    sheet.clear()
    # Writes the headers and the data back to the sheet
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- 2. DOCUMENT GENERATOR ---
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

# --- 3. APP INTERFACE ---
st.set_page_config(page_title="Oxford Skill Portal", page_icon="🎓")

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
                df['id'] = df['id'].astype(str).str.strip()
                df['pass'] = df['pass'].astype(str).str.strip()
                user = df[(df['id'] == str(uid)) & (df['pass'] == str(pwd))]
                
                if not user.empty:
                    st.session_state.auth = {"logged_in": True, "role": "student", "user": user.iloc[0].to_dict()}
                    st.rerun()
                else:
                    st.error("Invalid ID or Password")
            except Exception as e:
                st.error("Access Denied: Please check your Google Sheet sharing permissions.")

else:
    # Logout Sidebar
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # Admin Panel
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Administration")
        tab1, tab2 = st.tabs(["Enrollment", "Records"])
        
        with tab1:
            with st.form("enroll"):
                sid = st.text_input("Student ID")
                sname = st.text_input("Name")
                spass = st.text_input("Password")
                sphone = st.text_input("Phone Number")
                if st.form_submit_button("Enroll Now"):
                    df = fetch_students()
                    new_row = {"id": sid, "name": sname, "pass": spass, "status": "Paid", "phone": sphone}
                    update_students(pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                    st.success("Successfully Enrolled!")

        with tab2:
            st.dataframe(fetch_students())

    # Student Panel
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        df = fetch_students()
        # Find current status for this student
        status = df[df['id'].astype(str) == str(u['id'])]['status'].values[0]
        
        if str(status).lower() == "pending":
            st.error("Fees Pending - Access to downloads is locked.")
        else:
            st.success("Account Active.")
            if st.button("Download Admit Card"):
                pdf = create_pdf("ADMIT CARD", u['name'], u['id'], {"Exam": "Semester Final 2026"})
                st.download_button("Download Now", pdf, f"Admit_{u['id']}.pdf")
