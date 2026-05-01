import streamlit as st
from fpdf import FPDF
import datetime

# --- Page Configuration ---
st.set_page_config(page_title="Oxford Skill Centre", page_icon="🎓")

# --- Custom Styling for "Premium" Look ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- Receipt Generation Function ---
def generate_receipt(name, student_id, amount, purpose):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, "Guwahati, Assam | Official Fee Receipt", ln=True, align='C')
    pdf.ln(10)
    
    # Body
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Date: {datetime.date.today()}", ln=True)
    pdf.cell(200, 10, f"Receipt No: OSDC-{datetime.datetime.now().strftime('%M%S')}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, f"Student Name: {name}", ln=True)
    pdf.cell(200, 10, f"Student ID: {student_id}", ln=True)
    pdf.cell(200, 10, f"Amount Paid: Rs. {amount}", ln=True)
    pdf.cell(200, 10, f"Purpose: {purpose}", ln=True)
    
    pdf.ln(20)
    pdf.cell(200, 10, "Authorized Signatory", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- Main App Logic ---
st.title("🎓 Oxford Skill Portal")

menu = ["Student Login", "Admin Dashboard"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "Student Login":
    st.subheader("Student Access")
    id_input = st.text_input("Enter Student ID")
    if st.button("Access Dashboard"):
        # Placeholder for DB check
        st.success(f"Welcome back, Student {id_input}!")
        st.info("Your latest receipt is ready for download.")
        # Logic to fetch student data would go here

elif choice == "Admin Dashboard":
    st.subheader("Staff Portal")
    pwd = st.text_input("Admin Password", type="password")
    if pwd == "admin123": # Change this!
        st.write("### Generate New Receipt")
        s_name = st.text_input("Full Name")
        s_id = st.text_input("ID Number")
        s_amount = st.number_input("Amount (INR)", min_value=0)
        s_purpose = st.selectbox("Fee Type", ["Monthly Tuition", "Admission", "Exam Fee", "Others"])
        
        if st.button("Generate & Preview PDF"):
            pdf_data = generate_receipt(s_name, s_id, s_amount, s_purpose)
            st.download_button(label="📥 Download Receipt PDF", data=pdf_data, file_name=f"Receipt_{s_id}.pdf", mime="application/pdf")
