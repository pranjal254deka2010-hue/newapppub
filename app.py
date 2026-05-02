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
MONTHS = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]

# --- 2. DATABASE HELPERS ---
def fetch_data(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data)

def get_monthly_report(student_id, year_status):
    res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).execute()
    paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    report = []
    if year_status == "1st Year":
        timeline = [(m, "2026") for m in MONTHS[4:]] + [(m, "2027") for m in MONTHS] + [(m, "2028") for m in MONTHS[:5]]
    else:
        timeline = [(m, "2026") for m in MONTHS[4:]] + [(m, "2027") for m in MONTHS[:5]]
    for m, yr in timeline:
        label = f"{m} {yr}"
        report.append({"label": label, "status": "PAID" if label in paid_list else "PENDING"})
    return report

# --- 3. ID CARD GENERATOR ---
def create_id_card(s_info, photo_url=None):
    pdf = FPDF(format=(54, 86)) # Standard ID CR80 size in mm
    pdf.add_page()
    
    # Background Color Header
    pdf.set_fill_color(0, 51, 102) # Oxford Blue
    pdf.rect(0, 0, 54, 20, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 8)
    pdf.text(5, 8, "OXFORD SKILL")
    pdf.text(5, 12, "DEVELOPMENT CENTRE")
    
    # Photo Placeholder or Real Photo
    pdf.set_fill_color(240, 240, 240)
    if photo_url:
        try: pdf.image(photo_url, 17, 22, 20, 25)
        except: pdf.rect(17, 22, 20, 25, 'F')
    else:
        pdf.rect(17, 22, 20, 25, 'F')
        
    # Student Details
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 9)
    pdf.text(5, 55, s_info['name'].upper())
    
    pdf.set_font("Arial", '', 7)
    pdf.text(5, 60, f"ID: {s_info['id']}")
    pdf.text(5, 64, f"Course: {s_info['stream']}")
    pdf.text(5, 68, f"Valid Till: May 2028")
    
    # Footer
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(0, 80, 54, 6, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", '', 6)
    pdf.text(15, 84, "www.oxfordskill.com")
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. LOGIN LOGIC ---
st.set_page_config(page_title="Oxford ERP v3.0", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🎓 Oxford Skill Development Centre")
    role_sel = st.radio("Login As:", ["Student", "Teacher", "Admin"], horizontal=True)
    uid = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")
    
    if st.button("Access Portal", use_container_width=True):
        if role_sel == "Admin" and uid == "admin" and pwd == "oxford2026":
            st.session_state.auth = {"logged_in": True, "role": "admin", "user": "Admin"}
            st.rerun()
        elif role_sel == "Teacher":
            res = supabase.table("teachers").select("*").eq("id", uid).eq("pass", pwd).execute()
            if res.data:
                st.session_state.auth = {"logged_in": True, "role": "teacher", "user": res.data[0]}
                st.rerun()
        else:
            res = supabase.table("students").select("*").eq("id", uid).eq("pass", pwd).execute()
            if res.data:
                st.session_state.auth = {"logged_in": True, "role": "student", "user": res.data[0]}
                st.rerun()
        st.error("Invalid Login")

else:
    # --- ADMIN VIEW ---
    if st.session_state.auth["role"] == "admin":
        st.title("🛡️ Super Admin Control")
        df = fetch_data("students")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Enrollment", "Staff Management", "ID Card Setup", "Records"])
        
        with tab1:
            with st.form("enroll"):
                c1, c2, c3 = st.columns(3)
                sid, sname, sphone = c1.text_input("ID"), c2.text_input("Name"), c3.text_input("Phone")
                stream, year, spass = c1.selectbox("Stream", COURSES), c2.selectbox("Year", YEARS), c3.text_input("Pass")
                if st.form_submit_button("Register"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "stream": stream, "year_of_study": year, "status": "Pending"}).execute()
                    st.success("Registered!"); st.rerun()

        with tab2:
            st.subheader("Manage Teachers")
            with st.form("teacher_reg"):
                t_id, t_name, t_pass = st.text_input("Teacher ID"), st.text_input("Teacher Name"), st.text_input("Teacher Password")
                if st.form_submit_button("Add Teacher"):
                    supabase.table("teachers").insert({"id": t_id, "name": t_name, "pass": t_pass}).execute()
                    st.success("Teacher Added!")

        with tab3:
            st.subheader("Upload Student Photos for ID")
            target = st.selectbox("Select Student", df['id'].tolist() if not df.empty else [])
            photo_file = st.file_uploader("Upload Profile Photo", type=['jpg', 'png'])
            if st.button("Save Photo") and photo_file:
                # Upload to Supabase Storage
                path = f"photos/{target}.jpg"
                supabase.storage.from_("photos").upload(path, photo_file.getvalue(), {"content-type": "image/jpeg", "x-upsert": "true"})
                # Update DB with URL
                public_url = supabase.storage.from_("photos").get_public_url(path)
                supabase.table("students").update({"profile_photo_url": public_url}).eq("id", target).execute()
                st.success("Photo Uploaded!")

    # --- TEACHER VIEW ---
    elif st.session_state.auth["role"] == "teacher":
        st.title(f"👨‍🏫 Teacher Portal: {st.session_state.auth['user']['name']}")
        tab_a, tab_b = st.tabs(["Take Attendance", "Share Study Material"])
        
        with tab_a:
            sel_course = st.selectbox("Select Course", COURSES)
            date = st.date_input("Attendance Date")
            students = supabase.table("students").select("id, name").eq("stream", sel_course).execute().data
            if students:
                with st.form("att_form"):
                    attendance_data = []
                    for s in students:
                        status = st.checkbox(f"{s['name']} (Present)", key=s['id'], value=True)
                        attendance_data.append({"student_id": s['id'], "date": str(date), "status": "Present" if status else "Absent"})
                    if st.form_submit_button("Save Attendance"):
                        supabase.table("attendance").insert(attendance_data).execute()
                        st.success("Attendance Recorded!")

        with tab_b:
            st.subheader("Upload Notes")
            file = st.file_uploader("Upload PDF Notes", type=['pdf'])
            title = st.text_input("Chapter Title")
            if st.button("Post Material") and file:
                path = f"notes/{random.randint(100,999)}_{file.name}"
                supabase.storage.from_("notes").upload(path, file.getvalue())
                url = supabase.storage.from_("notes").get_public_url(path)
                supabase.table("study_material").insert({"teacher_id": st.session_state.auth['user']['id'], "title": title, "course": sel_course, "file_url": url}).execute()
                st.success("Notes Shared!")

    # --- STUDENT VIEW ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Student Home: {u['name']}")
        
        col_1, col_2 = st.columns([1, 2])
        
        with col_1:
            st.subheader("Your ID Card")
            # Fetch fresh photo URL
            res = supabase.table("students").select("profile_photo_url").eq("id", u['id']).execute()
            photo = res.data[0]['profile_photo_url'] if res.data else None
            
            if st.button("🪪 Download Official ID Card"):
                id_pdf = create_id_card(u, photo)
                st.download_button("Click to Download ID", id_pdf, f"ID_{u['id']}.pdf")
        
        with col_2:
            st.subheader("📚 Study Materials")
            mats = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
            for m in mats:
                st.markdown(f"📄 **{m['title']}** - [Download PDF]({m['file_url']})")
                
            st.divider()
            st.subheader("📅 Attendance History")
            att = supabase.table("attendance").select("*").eq("student_id", u['id']).execute().data
            if att:
                pres = sum(1 for a in att if a['status'] == 'Present')
                st.metric("Total Attendance", f"{pres}/{len(att)}")
