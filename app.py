import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- 1. CONFIGURATION ---
SHEET_ID = "1koS82MP0W-vlFXsZCcED6qdUzMgLOnYkwaGY35firh8"
# This URL converts your sheet into a CSV format that the app can read easily
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

def fetch_students():
    """Fetches the latest student data from the Google Sheet link."""
    try:
        # We add a timestamp to the URL to bypass cache and get 'live' data
        df = pd.read_csv(f"{CSV_URL}&cachebuster={datetime.datetime.now().timestamp()}")
        # Clean up columns and data
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error("Could not connect to the Google Sheet. Make sure 'Anyone with the link' is enabled.")
        return pd.DataFrame()

# --- 2. DOCUMENT GENERATOR (PDF) ---
def create_pdf(title, name, sid, details):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(190, 10, "Guwahati, Assam", ln=True, align='C')
    pdf.ln(10)
    
    # Title
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, title.upper(), ln=True, align='C')
    pdf.ln(5)
    
    # Content
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, f"Student: {name}")
    pdf.cell(90, 10, f"ID: {sid}", ln=True)
    pdf.cell(190, 10, f"Date: {datetime.date.today()}", ln=True)
    
    for k, v in details.items():
        pdf.cell(190, 10, f"{k}: {v}", ln=True)
        
    pdf.ln(20)
    pdf.cell(190, 10, "Authorized Signatory", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. APP INTERFACE ---
st.set_page_config(page_title="Oxford Skill Portal", page_icon="🎓")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Portal")
    st.info("Welcome to the Student & Staff Dashboard.")
    
    uid = st.text_input("Enter ID (Admin or Student ID)")
    pwd = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        # Admin Login
        if uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        
        # Student Login
        else:
            df = fetch_students()
            if not df.empty:
                # Ensure we match ID and Pass exactly
                user_match = df[(df['id'].astype(str).str.strip() == str(uid)) & 
                                (df['pass'].astype(str).str.strip() == str(pwd))]
                
                if not user_match.empty:
                    st.session_state.auth = {"logged_in": True, "role": "student", "user": user_match.iloc[0].to_dict()}
                    st.rerun()
                else:
                    st.error("Invalid ID or Password. Please try again.")

else:
    # --- LOGOUT BUTTON ---
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Management")
        st.write("Current Student List (Live from Google Sheets)")
        
        df = fetch_students()
        st.dataframe(df)
        
        st.sidebar.success("Logged in as Admin")
        st.sidebar.markdown("""
        **How to update data:**
        Edit your Google Sheet directly. 
        Refresh this page to see changes.
        """)

    # --- STUDENT VIEW ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        
        # Fresh status check
        df_fresh = fetch_students()
        status = df_fresh[df_fresh['id'].astype(str) == str(u['id'])]['status'].values[0]
        
        if str(status).lower() == "pending":
            st.error("🔴 Access Restricted: Your fees are currently pending. Please clear your dues to download documents.")
        else:
            st.success("🟢 Your account is active.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Admit Card")
                if st.button("Get Admit Card"):
                    doc = create_pdf("ADMIT CARD", u['name'], u['id'], {"Exam": "Semester Finals 2026", "Venue": "Oxford Campus"})
                    st.download_button("📥 Download PDF", doc, f"Admit_{u['id']}.pdf")
                    
            with col2:
                st.subheader("Fee Receipt")
                if st.button("Get Last Receipt"):
                    doc = create_pdf("FEE RECEIPT", u['name'], u['id'], {"Description": "Course Tuition", "Status": "Paid"})
                    st.download_button("📥 Download PDF", doc, f"Receipt_{u['id']}.pdf")
