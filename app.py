import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os

# --- 1. CONFIG & CONNECTION ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year"]

def fetch_students():
    try:
        res = supabase.table("students").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def get_monthly_report(student_id, current_year_status):
    try:
        res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).eq("fee_type", "Monthly Fee").execute()
        paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    except:
        paid_list = []
    
    report = []
    if current_year_status == "1st Year":
        timeline = [ (m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2027") for m in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2028") for m in ["January", "February", "March", "April", "May"] ]
    else:
        timeline = [ (m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"] ] + \
                   [ (m, "2027") for m in ["January", "February", "March", "April", "May"] ]

    for m, yr in timeline:
        label = f"{m} {yr}"
        report.append({"label": label, "status": "PAID" if label in paid_list else "PENDING"})
    return report

# --- 2. MAIN APP ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    role = st.selectbox("Login As", ["Admin", "Teacher", "Student"])
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if role == "Admin" and uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        elif role == "Teacher":
            # Check teachers table in Supabase
            res = supabase.table("teachers").select("*").eq("id", uid).eq("pass", pwd).execute()
            if res.data:
                st.session_state.auth = {"logged_in": True, "role": "teacher", "user": res.data[0]}
                st.rerun()
            else: st.error("Invalid Teacher Credentials")
        else:
            res = supabase.table("students").select("*").eq("id", uid).eq("pass", pwd).execute()
            if res.data:
                st.session_state.auth = {"logged_in": True, "role": "student", "user": res.data[0]}
                st.rerun()
            else: st.error("Invalid Student Credentials")

else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "role": None, "user": None}
        st.rerun()

    # --- TEACHER DASHBOARD (UPDATED) ---
    if st.session_state.auth["role"] == "teacher":
        teacher_info = st.session_state.auth["user"]
        st.title(f"👨‍🏫 Teacher Portal: {teacher_info['name']}")
        
        tab_upload, tab_manage = st.tabs(["📤 Upload New Notes", "🗑️ Manage Uploaded Notes"])
        
        with tab_upload:
            with st.form("notes_upload"):
                title = st.text_input("Notes Title (e.g. Anatomy Chapter 1)")
                crs = st.selectbox("Assign to Course", COURSES)
                f = st.file_uploader("Select PDF Note", type=["pdf"])
                if st.form_submit_button("Publish Note"):
                    if f and title:
                        file_name = f"{random.randint(1000,9999)}_{f.name}"
                        path = f"notes/{file_name}"
                        # Upload to Storage
                        supabase.storage.from_("notes").upload(path, f.getvalue())
                        url = supabase.storage.from_("notes").get_public_url(path)
                        # Save Reference with teacher_id
                        supabase.table("study_material").insert({
                            "title": title, 
                            "course": crs, 
                            "file_url": url, 
                            "teacher_id": teacher_info['id'],
                            "file_path": path  # Store path for deletion
                        }).execute()
                        st.success(f"Successfully uploaded: {title}")
                        st.rerun()
                    else:
                        st.error("Please provide a title and a PDF file.")

        with tab_manage:
            st.subheader("Your Published Materials")
            # Fetch only notes uploaded by this teacher[cite: 1]
            my_notes = supabase.table("study_material").select("*").eq("teacher_id", teacher_info['id']).execute().data
            
            if my_notes:
                for n in my_notes:
                    col_info, col_del = st.columns([4, 1])
                    col_info.info(f"📄 **{n['title']}** ({n['course']})")
                    if col_del.button("🗑️ Delete", key=f"del_{n['id']}"):
                        # 1. Delete from Storage[cite: 1]
                        if 'file_path' in n and n['file_path']:
                            supabase.storage.from_("notes").remove([n['file_path']])
                        # 2. Delete from Database[cite: 1]
                        supabase.table("study_material").delete().eq("id", n['id']).execute()
                        st.warning(f"Deleted: {n['title']}")
                        st.rerun()
            else:
                st.write("You haven't uploaded any notes yet.")

    # --- ADMIN & STUDENT LOGIC REMAINS THE SAME ---
    # (Insert the Admin and Student logic from the previous code block here)
