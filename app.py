import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import datetime

# --- 1. SECURE CONNECTION TO GOOGLE SHEETS ---
def get_gspread_client():
    """Authenticates using the Service Account key from Secrets."""
    info = dict(st.secrets["gcp_service_account"])
    
    # CRITICAL: Convert escaped \n characters back to real newlines
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        
    creds = Credentials.from_service_account_info(
        info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

def fetch_students():
    """Reads all rows from the 'Students' worksheet."""
    client = get_gspread_client()
    # Using your specific Spreadsheet ID
    sheet = client.open_by_key("1koS82MP0W-vlFXsZCcED6qdUzMgLOnYkwaGY35firh8").worksheet("Students")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def update_students(df):
    """Overwrites the sheet with the updated student list."""
    client = get_gspread_client()
    sheet = client.open_by_key("1koS82MP0W-vlFXsZCcED6qdUzMgLOnYkwaGY35firh8").worksheet("Students")
    sheet.clear()
    # Writes headers and all data rows
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- 2. DOCUMENT GENERATOR ---
def create_pdf(title, name, sid, details):
    """Generates a simple official PDF document."""
    pdf = FPDF()
    pdf.add_page()
    
    # Centre Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.ln(10)
    
    # Document Title
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, title.upper(), ln=True, align='C')
    pdf.ln(10)
    
    # Student Info
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, f"Student Name: {name}")
    pdf.cell(90, 10, f"Student ID: {sid}", ln=True)
    pdf.cell(190, 10, f"Issued Date: {datetime.date.today()}", ln=True)
    
    # Additional Details
    pdf.ln(5)
    for k, v in details.items():
        pdf.cell(190, 10, f"{k}: {v}", ln=True)
        
    pdf.ln(20)
    pdf.cell(190, 10, "Authorized Signature / Seal", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. APP INTERFACE & LOGIC ---
st.set_page_config(page_title="Oxford Skill Portal", page_icon="🎓")

# Initialize login session
if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Portal")
    st.subheader("Login to Access Your Dashboard")
    
    uid = st.text_input("User ID / Student ID")
    pwd = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # Admin / Teacher Access
        if uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin Staff"}
            st.rerun()
        
        # Student Access
        else:
            try:
                df = fetch_students()
                # Ensure values are strings for clean comparison
                df['id'] = df['id'].astype(str).str.strip()
                df['pass'] = df['pass'].astype(str).str.strip()
                
                user_match = df[(df['id'] == str(uid)) & (df['pass'] == str(pwd))]
                
                if not user_match.empty:
                    st.session_state.auth = {"logged_in": True, "role": "student", "user": user_match.iloc[0].to_dict()}
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please contact the centre.")
            except Exception as e:
                st.error("Error connecting to database. Please ensure your Secrets are correct.")

else:
    # --- LOGOUT ---
    if st.sidebar.button("Log Out"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # --- TEACHER / ADMIN FRONT ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Management Dashboard")
        st.sidebar.info("Logged in as Admin")
        
        tab1, tab2 = st.tabs(["Add New Student", "View All Records"])
        
        with tab1:
            st.subheader("Register New Enrollment")
            with st.form("enroll_form"):
                new_id = st.text_input("New Student ID (e.g. OSDC001)")
                new_name = st.text_input("Full Name")
                new_pass = st.text_input("Login Password")
                new_phone = st.text_input("Phone Number")
                new_status = st.selectbox("Fee Status", ["Paid", "Pending"])
                
                if st.form_submit_button("Enroll Student"):
                    if new_id and new_name and new_pass:
                        df_all = fetch_students()
                        new_entry = {"id": new_id, "name": new_name, "pass": new_pass, "status": new_status, "phone": new_phone}
                        updated_df = pd.concat([df_all, pd.DataFrame([new_entry])], ignore_index=True)
                        update_students(updated_df)
                        st.success(f"Enrolled {new_name} successfully!")
                    else:
                        st.warning("Please fill in ID, Name, and Password.")

        with tab2:
            st.subheader("Current Student Database")
            current_df = fetch_students()
            st.dataframe(current_df)
            
            # Quick status update tool
            st.divider()
            st.subheader("Update Payment Status")
            target_id = st.selectbox("Select Student ID", current_df['id'].tolist())
            update_stat = st.radio("Set New Status", ["Paid", "Pending"], horizontal=True)
            if st.button("Save New Status"):
                current_df.loc[current_df['id'].astype(str) == str(target_id), 'status'] = update_stat
                update_students(current_df)
                st.success(f"Status for {target_id} updated to {update_stat}")

    # --- STUDENT FRONT ---
    elif st.session_state.auth["role"] == "student":
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        
        # Verify status directly from the Google Sheet
        current_data = fetch_students()
        student_row = current_data[current_data['id'].astype(str) == str(u['id'])]
        
        if student_row.empty:
            st.error("Account data not found. Please contact the centre.")
        else:
            status = student_row.iloc[0]['status']
            
            if str(status).lower() == "pending":
                st.error("⚠️ ACTION REQUIRED: Your fees are currently pending. Document access is locked.")
            else:
                st.success("✅ Your account is active. Documents are available for download.")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Admit Card")
                    if st.button("Generate Admit Card"):
                        pdf_file = create_pdf("ADMIT CARD", u['name'], u['id'], {"Exam": "Term Examination 2026", "Venue": "Oxford Campus Hall"})
                        st.download_button("📥 Download PDF", pdf_file, f"Admit_{u['id']}.pdf")
                        
                with col2:
                    st.subheader("Fee Receipt")
                    if st.button("Generate Last Receipt"):
                        pdf_file = create_pdf("FEE RECEIPT", u['name'], u['id'], {"Description": "Course Tuition Fee", "Payment Status": "PAID"})
                        st.download_button("📥 Download PDF", pdf_file, f"Receipt_{u['id']}.pdf")
