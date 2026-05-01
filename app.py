import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime

# --- 1. DATABASE CONNECTION ---
# Ensure these match the labels in your Streamlit Secrets exactly
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

def fetch_students():
    """Retrieves all students from the Supabase table."""
    res = supabase.table("students").select("*").execute()
    return pd.DataFrame(res.data)

# --- 2. PDF GENERATOR ---
def create_pdf(title, name, sid, details):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(190, 10, "Dhupdhara, Assam", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, title.upper(), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, f"Student: {name}")
    pdf.cell(90, 10, f"ID: {sid}", ln=True)
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
    uid = st.text_input("User ID / Student ID")
    pwd = st.text_input("Password", type="password")
    
    if st.button("Sign In"):
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
                    st.error("Invalid ID or Password.")
            except:
                st.error("Database connection failed. Please check Supabase credentials.")

else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Staff Control Center")
        tab1, tab2, tab3 = st.tabs(["🆕 Enrollment", "👥 Student List", "💰 Fee Management"])
        
        # TAB 1: ENROLLMENT PAGE
        with tab1:
            st.subheader("Register New Student")
            with st.form("enroll_student"):
                new_id = st.text_input("Assign Student ID")
                new_name = st.text_input("Full Name")
                new_pass = st.text_input("Set Password")
                new_phone = st.text_input("Phone Number")
                new_status = st.selectbox("Initial Fee Status", ["Paid", "Pending"])
                
                if st.form_submit_button("Complete Enrollment"):
                    if new_id and new_name:
                        supabase.table("students").insert({
                            "id": new_id, "name": new_name, "pass": new_pass, 
                            "phone": new_phone, "status": new_status
                        }).execute()
                        st.success(f"Successfully Enrolled {new_name}!")
                    else:
                        st.warning("ID and Name are required.")

        # TAB 2: STUDENT LIST
        with tab2:
            st.subheader("All Enrolled Students")
            df = fetch_students()
            if not df.empty:
                st.dataframe(df[['id', 'name', 'phone', 'status', 'created_at']], use_container_width=True)
            else:
                st.info("No students enrolled yet.")

        # TAB 3: FEES PAID/UNPAID PAGE
        with tab3:
            st.subheader("Update Fee Status")
            df = fetch_students()
            if not df.empty:
                target_id = st.selectbox("Select Student ID to Update", df['id'].tolist())
                new_stat = st.radio("Current Payment Status", ["Paid", "Pending"], horizontal=True)
                
                if st.button("Save Payment Update"):
                    supabase.table("students").update({"status": new_stat}).eq("id", target_id).execute()
                    st.success(f"Status for {target_id} updated to {new_stat}!")
            else:
                st.info("Enroll students first to manage fees.")

    # --- STUDENT DASHBOARD ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome, {u['name']}")
        
        # Real-time check of their status from database
        res = supabase.table("students").select("status").eq("id", u['id']).execute()
        current_status = res.data[0]['status']

        if str(current_status).lower() == "pending":
            st.error("⚠️ ACCESS LOCKED: Your fees are currently unpaid. Please visit the office to clear your dues.")
        else:
            st.success("✅ Account Active: You can now download your documents.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Generate Admit Card"):
                    pdf = create_pdf("ADMIT CARD", u['name'], u['id'], {"Exam": "Semester Finals 2026", "Campus": "Dhupdhara"})
                    st.download_button("Download Admit Card", pdf, f"Admit_{u['id']}.pdf")
            with col2:
                if st.button("Generate Fee Receipt"):
                    pdf = create_pdf("OFFICIAL RECEIPT", u['name'], u['id'], {"Description": "Tuition Fee", "Status": "PAID IN FULL"})
                    st.download_button("Download Receipt", pdf, f"Receipt_{u['id']}.pdf")
