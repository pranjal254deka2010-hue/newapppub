import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import random
import os
import requests
from io import BytesIO

# --- 1. CONNECTION ---
URL = st.secrets["supabase"]["url"]
KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(URL, KEY)

COURSES = ["DMLT", "OT Technician", "X-Ray Technician", "First Aid and Patient Care"]
YEARS = ["1st Year", "2nd Year"]
STANDARD_MONTHS = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]

# --- 2. DATA HELPERS ---
def fetch_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def get_monthly_report(student_id, year_status):
    try:
        res = supabase.table("fee_records").select("month, year").eq("student_id", student_id).execute()
        paid_list = [f"{r['month']} {r['year']}" for r in res.data]
    except:
        paid_list = []
    
    report = []
    if year_status == "1st Year":
        timeline = [(m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"]] + \
                   [(m, "2027") for m in STANDARD_MONTHS] + \
                   [(m, "2028") for m in ["January", "February", "March", "April", "May"]]
    else:
        timeline = [(m, "2026") for m in ["May", "June", "July", "August", "September", "October", "November", "December"]] + \
                   [(m, "2027") for m in ["January", "February", "March", "April", "May"]]

    for m, yr in timeline:
        label = f"{m} {yr}"
        report.append({"label": label, "status": "PAID" if label in paid_list else "PENDING"})
    return report

# --- 3. GENERATORS ---

def create_id_card(s_info, photo_url=None):
    """Generates a CR80 ID Card with a fix for the blank photo issue."""
    pdf = FPDF(format=(54, 86)) 
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(0, 51, 102) 
    pdf.rect(0, 0, 54, 20, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 8)
    pdf.text(5, 8, "OXFORD SKILL")
    pdf.text(5, 12, "DEVELOPMENT CENTRE")
    
    # Photo Logic (Fixed for image_cf271b.png)
    if photo_url:
        try:
            response = requests.get(photo_url)
            img_data = BytesIO(response.content)
            pdf.image(img_data, 17, 25, 20, 25) 
        except:
            pdf.set_fill_color(200, 200, 200)
            pdf.rect(17, 25, 20, 25, 'F')
    else:
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(17, 25, 20, 25, 'F')
        
    # Student Details
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 9)
    pdf.text(5, 58, s_info['name'].upper())
    pdf.set_font("Arial", '', 7)
    pdf.text(5, 63, f"ID: {s_info['id']}")
    pdf.text(5, 67, f"Course: {s_info['stream']}")
    pdf.text(5, 71, f"Valid Till: May 2028")
    
    return pdf.output(dest='S').encode('latin-1')

def create_receipt(s_info, bill):
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(5, 5, 200, 185)
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 10, 25)
    pdf.set_font("Arial", 'B', 18); pdf.cell(190, 10, "OXFORD SKILL DEVELOPMENT CENTRE", ln=True, align='C')
    pdf.ln(10)
    r_no = f"REC-{random.randint(100, 999)}"
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"FEE RECEIPT: {r_no}", ln=True, align='C', fill=True); pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Student: {s_info['name']}"); pdf.cell(95, 8, f"ID: {s_info['id']}", ln=True)
    pdf.cell(190, 10, f"TOTAL PAID: INR {bill['total']}/-", border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1'), r_no

# --- 4. MAIN APP ---
st.set_page_config(page_title="Oxford ERP", layout="wide")

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
        st.error("Access Denied")

else:
    # --- ADMIN SIDE ---
    if st.session_state.auth["role"] == "admin":
        df = fetch_data("students")
        st.sidebar.button("Logout", on_click=lambda: st.session_state.auth.update({"logged_in": False}))
        
        t1, t2, t3, t4, t5 = st.tabs(["Enrollment", "Billing", "ID Photo Setup", "Staff Control", "Detailed Records"])
        
        with t1:
            with st.form("en"):
                c1, c2, c3 = st.columns(3)
                sid, sname, sphone = c1.text_input("ID"), c2.text_input("Name"), c3.text_input("Phone")
                strm, yr, spass = c1.selectbox("Course", COURSES), c2.selectbox("Year", YEARS), c3.text_input("Pass")
                if st.form_submit_button("Enroll"):
                    supabase.table("students").insert({"id": sid, "name": sname, "pass": spass, "phone": sphone, "stream": strm, "year_of_study": yr}).execute()
                    st.success("Enrolled!"); st.rerun()

        with t2:
            if not df.empty:
                target = st.selectbox("Select Student", df['id'].tolist())
                s_info = df[df['id'] == target].iloc[0]
                p_spot = st.container()
                with st.form("bill"):
                    a, b = st.columns(2)
                    m_f, f_n = a.number_input("Monthly Fee", 0), b.number_input("Fine", 0)
                    s_m, s_y = a.selectbox("Month", STANDARD_MONTHS), b.selectbox("Year", ["2026", "2027", "2028"])
                    if st.form_submit_button("Generate Receipt"):
                        total_amt = m_f + f_n
                        bill = {"total": total_amt, "m": s_m, "y": s_y}
                        pdf, r_no = create_receipt(s_info, bill)
                        supabase.table("fee_records").insert({"student_id": target, "month": s_m, "year": s_y, "amount_paid": str(total_amt), "receipt_no": r_no}).execute()
                        st.success("Billed!"); p_spot.download_button("Print", pdf, f"Rec_{target}.pdf")

        with t3:
            st.subheader("Student Photo ID Setup")
            target_id = st.selectbox("Select Student ID", df['id'].tolist() if not df.empty else [])
            p_file = st.file_uploader("Upload JPG Profile Picture", type=['jpg', 'jpeg'])
            if st.button("Update Profile Photo") and p_file:
                path = f"photos/{target_id}.jpg"
                supabase.storage.from_("photos").upload(path, p_file.getvalue(), {"x-upsert": "true"})
                url = supabase.storage.from_("photos").get_public_url(path)
                supabase.table("students").update({"profile_photo_url": url}).eq("id", target_id).execute()
                st.success("Photo Updated Successfully!")

        with t4:
            with st.form("t_add"):
                tid, tname, tpas = st.text_input("Teacher ID"), st.text_input("Name"), st.text_input("Pass")
                if st.form_submit_button("Add Teacher"):
                    supabase.table("teachers").insert({"id": tid, "name": tname, "pass": tpas}).execute()
                    st.success("Teacher Added!")

        with t5:
            st.subheader("📂 Comprehensive Database")
            if not df.empty:
                for _, row in df.iterrows():
                    with st.expander(f"👤 {row['id']} | {row['name']} | Password: {row['pass']}"):
                        c_a, c_b = st.columns([2,1])
                        with c_a:
                            rep = get_monthly_report(row['id'], row['year_of_study'])
                            m_cols = st.columns(4)
                            for i, x in enumerate(rep):
                                with m_cols[i % 4]:
                                    if x['status'] == "PAID": st.success(x['label'])
                                    else: st.error(x['label'])
                        with c_b:
                            att = supabase.table("attendance").select("*").eq("student_id", row['id']).execute().data
                            if att: st.metric("Attendance Score", f"{sum(1 for a in att if a['status'] == 'Present')}/{len(att)}")

    # --- TEACHER SIDE ---
    elif st.session_state.auth["role"] == "teacher":
        st.title(f"👨‍🏫 Welcome, {st.session_state.auth['user']['name']}")
        t_a, t_b = st.tabs(["Attendance", "Notes"])
        with t_a:
            crs = st.selectbox("Course", COURSES)
            dt = st.date_input("Date")
            stds = supabase.table("students").select("id, name").eq("stream", crs).execute().data
            if stds:
                with st.form("att"):
                    att_list = []
                    for s in stds:
                        p = st.checkbox(f"{s['name']}", value=True)
                        att_list.append({"student_id": s['id'], "date": str(dt), "status": "Present" if p else "Absent"})
                    if st.form_submit_button("Submit Attendance"):
                        supabase.table("attendance").insert(att_list).execute()
                        st.success("Attendance Saved!")
        with t_b:
            f = st.file_uploader("Upload Notes (PDF)", type=['pdf'])
            title = st.text_input("Topic Title")
            if st.button("Share with Students") and f:
                path = f"notes/{random.randint(100,999)}_{f.name}"
                supabase.storage.from_("notes").upload(path, f.getvalue())
                url = supabase.storage.from_("notes").get_public_url(path)
                supabase.table("study_material").insert({"teacher_id": st.session_state.auth['user']['id'], "title": title, "course": crs, "file_url": url}).execute()
                st.success("Study Material Uploaded!")

    # --- STUDENT SIDE ---
    else:
        u = st.session_state.auth["user"]
        st.title(f"👋 Welcome Home, {u['name']}")
        cl1, cl2 = st.columns([1, 2])
        with cl1:
            st.subheader("Digital ID Card")
            if st.button("🪪 Download My ID"):
                res = supabase.table("students").select("profile_photo_url").eq("id", u['id']).execute()
                p_url = res.data[0]['profile_photo_url'] if res.data else None
                pdf_bytes = create_id_card(u, p_url)
                st.download_button("Download Now", pdf_bytes, f"ID_{u['id']}.pdf")
        with cl2:
            st.subheader("📚 Latest Study Material")
            nts = supabase.table("study_material").select("*").eq("course", u['stream']).execute().data
            if nts:
                for n in nts: st.info(f"📄 {n['title']} ([Download PDF]({n['file_url']}))")
            else:
                st.write("No study materials uploaded yet.")
