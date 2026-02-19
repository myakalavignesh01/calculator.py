# calci.py
# Calci.py — Creative Professional GPA Companion (single-file)
# Author: Myakala Vignesh
# School: School of Computer Science and Engineering
# Year: 2025
#
# Features:
# - Top-left logo and sidebar student info (School, name, hallticket)
# - Welcome -> greeting "Hello, <name>"
# - Step-by-step features: Calculate GPA/SGPA, Track CGPA, Multi-country conversion,
#   Target & Planner (difficulty-based study plans), Saved history, Admin panel
# - Auto-save CSV and optional PDF (reportlab)
# - Admin: view history, ratings, export all, reset/delete
# - Neutral professional charts, dark theme, success popups
#
# Save a professional logo as 'calci_logo.png' in the same folder.

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from io import BytesIO
from datetime import datetime
import json
import os

# Optional PDF generator
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# Excel export support
try:
    import openpyxl  # may be used by pandas ExcelWriter
except:
    pass

# Image
try:
    from PIL import Image
except Exception:
    Image = None

# -------------------------
# Config / Constants
# -------------------------
APP_TITLE = "Calci.py"
SCHOOL = "School of Computer Science and Engineering"
AUTHOR = "Myakala Vignesh"
YEAR = 2025
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)
HISTORY_FILE = RESULTS_DIR / "history.json"

# Initialize history file
if not HISTORY_FILE.exists():
    HISTORY_FILE.write_text("[]", encoding="utf-8")

MAX_SEM = 8
GPA_DECIMALS = 3

# Grade mapping percentage -> label, grade point (10-point)
PERCENT_TO_GRADE = [
    (90,100,"O",10.0),
    (80,89.99,"A+",9.0),
    (70,79.99,"A",8.0),
    (60,69.99,"B+",7.0),
    (50,59.99,"B",6.0),
    (45,49.99,"C",5.0),
    (40,44.99,"D",4.0),
    (0,39.99,"F",0.0)
]

# Top 10 countries for higher studies (for display & conversion)
TOP_COUNTRIES = [
    "United States","Canada","United Kingdom","Germany","Australia",
    "Netherlands","Sweden","France","Singapore","New Zealand"
]

# -------------------------
# Helpers
# -------------------------
def now_ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def load_history():
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")

def percent_to_grade_point(percent):
    try:
        p = float(percent)
    except:
        return "", np.nan
    for mn, mx, lbl, gp in PERCENT_TO_GRADE:
        if mn <= p <= mx:
            return lbl, float(gp)
    return "", np.nan

def sgpa_from_df(df):
    df2 = df.copy()
    df2["Credits"] = pd.to_numeric(df2["Credits"], errors="coerce").fillna(0)
    df2["Grade_Point"] = pd.to_numeric(df2["Grade_Point"], errors="coerce")
    used = df2[df2["Grade_Point"].notna()]
    total_credits = used["Credits"].sum()
    if total_credits == 0:
        return None
    sgpa = (used["Grade_Point"] * used["Credits"]).sum() / total_credits
    return round(sgpa, GPA_DECIMALS)

def convert_cgpa_to_countries(cgpa10):
    """Return approximate mapping for top countries"""
    if cgpa10 is None:
        return {}
    cg = float(cgpa10)
    pct = cg * 10
    out = {}
    # US
    out["United States"] = {"scale":"4.0", "gpa": round((cg/10.0)*4.0,2)}
    # Canada approx
    if pct>=90: can=4.0
    elif pct>=85: can=3.7
    elif pct>=80: can=3.3
    elif pct>=75: can=3.0
    elif pct>=70: can=2.7
    else: can=2.0
    out["Canada"] = {"scale":"4.0", "gpa": can}
    # UK classification
    if pct>=70: uk="First"
    elif pct>=60: uk="2:1"
    elif pct>=50: uk="2:2"
    elif pct>=40: uk="Third"
    else: uk="Fail"
    out["United Kingdom"] = {"classification": uk}
    # Germany approx
    ger = round(1 + 3*(100-pct)/100,2); out["Germany"] = {"grade": ger}
    # Australia (7 point)
    if pct>=85: aus=7
    elif pct>=75: aus=6
    elif pct>=65: aus=5
    elif pct>=50: aus=4
    else: aus=2
    out["Australia"] = {"scale":"7", "gpa": aus}
    out["Netherlands"] = {"scale":"10", "score": round(pct/10,2)}
    # Sweden
    if pct>=90: sw=5
    elif pct>=75: sw=4
    elif pct>=60: sw=3
    elif pct>=50: sw=2
    else: sw=1
    out["Sweden"] = {"grade": sw}
    out["France"] = {"percent": pct}
    out["Singapore"] = {"scale":"4.0", "gpa": round((cg/10.0)*4.0,2)}
    out["New Zealand"] = {"scale":"7", "gpa": aus}
    return out

def save_csv(df, filename):
    path = RESULTS_DIR / filename
    df.to_csv(path, index=False)
    return path

def generate_pdf_report(df, meta):
    """Return BytesIO PDF buffer if reportlab available otherwise None"""
    if not REPORTLAB_AVAILABLE:
        return None
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    x = 50; y = h - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Calci.py — GPA Report")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Student: {meta.get('student','-')}     Hallticket: {meta.get('hallticket','-')}")
    y -= 14
    c.drawString(x, y, f"Program: {meta.get('program','-')}    Semester: {meta.get('semester_label','-')}    SGPA: {meta.get('sgpa','-')}")
    y -= 18
    # table header
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "Subject"); c.drawString(x+220, y, "Credits"); c.drawString(x+270, y, "CIE"); c.drawString(x+320, y, "SEE"); c.drawString(x+370, y, "Total"); c.drawString(x+430, y, "Grade")
    y -= 12
    c.setFont("Helvetica", 10)
    for _, row in df.iterrows():
        if y < 80:
            c.showPage(); y = h - 60
        c.drawString(x, y, str(row.get("Subject","")))
        c.drawString(x+220, y, str(row.get("Credits","")))
        c.drawString(x+270, y, str(row.get("CIE_out_of_50","")))
        c.drawString(x+320, y, str(row.get("SEE_out_of_50","")))
        c.drawString(x+370, y, str(row.get("Total_out_of_100","")))
        c.drawString(x+430, y, str(row.get("Grade","")))
        y -= 14
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.save()
    buf.seek(0)
    return buf

# -------------------------
# UI: Page config & CSS
# -------------------------
st.set_page_config(page_title=APP_TITLE, page_icon="🎓", layout="wide")
# Dark + blue accent CSS
st.markdown("""
    <style>
      .stApp { background: #0b0c0e; color: #e6eef8; }
      .stSidebar { background: #0f1720; color: #cfd8e3; }
      .stButton>button { background-color:#1f6feb; color:white; }
      .css-1d391kg { color: #e6eef8; }
      .stDownloadButton>button { background-color:#16a34a; color:white; }
      /* admin premium card tweaks */
      .admin-card { background: rgba(255,255,255,0.04); padding: 18px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06); }
    </style>
""", unsafe_allow_html=True)

# Load and display logo in header + sidebar if available
logo_path = Path("calci_logo.png")
if Image is not None and logo_path.exists():
    try:
        logo_img = Image.open(logo_path)
    except Exception:
        logo_img = None
else:
    logo_img = None

# Header with logo top-left (wide) - improved layout
head_col1, head_col2 = st.columns([0.18, 1])
with head_col1:
    if logo_img:
        st.image(logo_img, width=88)
    else:
        st.markdown(f"**{APP_TITLE}**")
with head_col2:
    st.markdown(f"<h1 style='color:#4db8ff; margin:0'>{APP_TITLE}</h1>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:gray; margin-top:-8px'>{SCHOOL}</div>", unsafe_allow_html=True)

# -------------------------
# Sidebar: student info + logo
# -------------------------
with st.sidebar:
    if logo_img:
        st.image(logo_img, width=160)
    st.markdown("## Student Info")
    st.text("Fill details then Start")
    student_name = st.text_input("Student Name (e.g., D. Soumith)", key="sid_name")
    hallticket = st.text_input("Hallticket No (e.g., 25EU08R0111)", key="sid_ht")
    program = st.selectbox("Program", ["B.Tech","M.Tech","MBA"])
    start = st.button("Start", key="start_button")
    st.markdown("---")
    st.markdown("### Quick features")
    st.write("• Calculate SGPA (per semester)\n\n• Track CGPA (up to 8 sems)\n\n• Multi-country conversion\n\n• Target & Planner")
    st.markdown("---")
    st.caption(f"© {YEAR} {APP_TITLE} — Public app")

# Start guard: require student details
if not st.session_state.get("app_started", False):
    if start:
        if not student_name or not hallticket:
            st.sidebar.error("Please enter student name and hallticket to start.")
        else:
            st.session_state["student_name"] = student_name
            st.session_state["hallticket"] = hallticket
            st.session_state["program"] = program
            st.session_state["app_started"] = True
            st.session_state.setdefault("semesters", {})  # keep saved sems
            st.experimental_rerun()
    else:
        st.stop()

# After start: greeting and options
st.markdown(f"### Hello, **{st.session_state.get('student_name','Student')}**")
st.markdown(f"**Hallticket:** {st.session_state.get('hallticket','-')}  •  **Program:** {st.session_state.get('program','-')}")
st.markdown("---")

# Feature selector
choice = st.selectbox("Choose feature (step-by-step):", [
    "Calculate GPA (per semester)",
    "Track CGPA (multi-semester)",
    "Multi-country conversion",
    "Target & Planner (SEE required)",
    "View Saved Results",
    "Admin"
])

# -------------------------
# Feature: Calculate GPA per semester
# -------------------------
if choice == "Calculate GPA (per semester)":
    st.header("Step 1 — Calculate SGPA for a Semester")
    st.info("Enter number of semesters (up to 8). For each semester choose number of subjects and enter marks. Mids are out of 40 each; average them, add presentation/assignment (out of 10) => CIE/50. SEE is out of 50. Total = CIE + SEE (100).")

    sem = st.selectbox("Select semester (1-8):", list(range(1, MAX_SEM+1)))
    default_subjects = 6
    num_subjects = st.number_input("Number of subjects for this semester", min_value=1, max_value=12, value=default_subjects, key=f"numsub_{sem}")
    st.markdown("Enter subject details below:")
    subjects = []
    for i in range(int(num_subjects)):
        subj = st.text_input(f"Subject {i+1} name", value=f"Subject_{i+1}", key=f"sub_{sem}_{i}")
        credits = st.number_input(f"Credits for {subj} (S{sem}#{i+1})", min_value=0, max_value=10, value=3, key=f"cred_{sem}_{i}")
        mid1 = st.number_input(f"Mid1 (out of 40) for {subj}", min_value=0, max_value=40, value=20, key=f"mid1_{sem}_{i}")
        mid2 = st.number_input(f"Mid2 (out of 40) for {subj}", min_value=0, max_value=40, value=20, key=f"mid2_{sem}_{i}")
        pres = st.number_input(f"Presentation/Assignment (out of 10) for {subj}", min_value=0, max_value=10, value=5, key=f"pres_{sem}_{i}")
        see = st.number_input(f"SEE (out of 50) for {subj}", min_value=0, max_value=50, value=25, key=f"see_{sem}_{i}")
        subjects.append({
            "Subject": subj or f"S{sem}_{i+1}",
            "Credits": credits,
            "Mid1_out_of_40": mid1,
            "Mid2_out_of_40": mid2,
            "Presentation_out_of_10": pres,
            "CIE_out_of_50": None,
            "SEE_out_of_50": see,
            "Total_out_of_100": None,
            "Grade": "",
            "Grade_Point": None
        })

    if st.button("Compute Semester SGPA & Save"):
        rows = []
        for s in subjects:
            m1 = float(s["Mid1_out_of_40"]); m2 = float(s["Mid2_out_of_40"])
            avg_mid = (m1 + m2) / 2.0  # out of 40
            pres = float(s["Presentation_out_of_10"])
            cie = avg_mid + pres
            if cie > 50.0: cie = 50.0
            see = float(s["SEE_out_of_50"])
            total = cie + see
            if total > 100.0: total = 100.0
            grade_label, gp = percent_to_grade_point(total)
            rows.append({
                "Subject": s["Subject"],
                "Credits": s["Credits"],
                "Mid1_out_of_40": m1,
                "Mid2_out_of_40": m2,
                "Avg_mid_out_of_40": round(avg_mid, 2),
                "Presentation_out_of_10": pres,
                "CIE_out_of_50": round(cie, 2),
                "SEE_out_of_50": round(see,2),
                "Total_out_of_100": round(total,2),
                "Grade": grade_label,
                "Grade_Point": gp
            })
        sem_df = pd.DataFrame(rows)
        sgpa = sgpa_from_df(sem_df)
        if sgpa is None:
            st.error("Could not compute SGPA (check credits).")
        else:
            st.success(f"✅ Semester {sem} SGPA: {sgpa}")
            # save into session and history
            st.session_state["semesters"].setdefault(str(sem), {})
            st.session_state["semesters"][str(sem)]["df"] = sem_df.to_dict(orient="records")
            st.session_state["semesters"][str(sem)]["sgpa"] = sgpa
            st.session_state["semesters"][str(sem)]["credits"] = int(sem_df["Credits"].sum())
            # save CSV
            fname = f"{st.session_state.get('student_name')}_Sem{sem}_{now_ts()}.csv".replace(" ", "_")
            csv_path = save_csv(sem_df, fname)
            st.info(f"Saved CSV: {csv_path}")
            # optional PDF
            meta = {"student": st.session_state.get("student_name"), "hallticket": st.session_state.get("hallticket"),
                    "program": st.session_state.get("program"), "semester_label": f"Sem{sem}", "sgpa": sgpa}
            pdf_buf = generate_pdf_report(sem_df, meta)
            pdf_path = None
            if pdf_buf:
                pdf_name = f"{st.session_state.get('student_name')}_Sem{sem}_{now_ts()}.pdf".replace(" ", "_")
                pdf_path = RESULTS_DIR / pdf_name
                pdf_path.write_bytes(pdf_buf.getvalue())
                st.info(f"Saved PDF: {pdf_path}")
            # append to history.json with rating placeholder None
            history = load_history()
            history.append({
                "timestamp": now_ts(),
                "student": st.session_state.get("student_name"),
                "hallticket": st.session_state.get("hallticket"),
                "program": st.session_state.get("program"),
                "semester": f"Sem{sem}",
                "sgpa": sgpa,
                "csv": str(csv_path),
                "pdf": str(pdf_path) if pdf_path else None,
                "rating": None
            })
            save_history(history)
            # display table & chart
            st.dataframe(sem_df)
            fig, ax = plt.subplots(figsize=(8,3))
            ax.bar(sem_df["Subject"], sem_df["Grade_Point"], color="#dfe6ee", edgecolor="#aab6c8")
            ax.set_ylim(0,10); ax.set_ylabel("Grade Point (10)")
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig)
            st.balloons()

# -------------------------
# Feature: Track CGPA (multi-semester)
# -------------------------
elif choice == "Track CGPA (multi-semester)":
    st.header("Step 2 — CGPA Tracker")
    st.info("Use saved semester SGPAs or enter them manually. CGPA is credit-weighted.")
    # collect up to 8 sems
    sems_data = []
    saved_semesters = st.session_state.get("semesters", {})
    for i in range(1, MAX_SEM+1):
        s_key = str(i)
        default_sgpa = saved_semesters.get(s_key, {}).get("sgpa", 0.0)
        default_cred = saved_semesters.get(s_key, {}).get("credits", 0)
        cols = st.columns([1,1])
        sg = cols[0].number_input(f"SGPA Sem {i}", min_value=0.0, max_value=10.0, value=float(default_sgpa or 0.0), step=0.01, key=f"track_sgpa_{i}")
        cr = cols[1].number_input(f"Credits Sem {i}", min_value=0, max_value=80, value=int(default_cred or 0), step=1, key=f"track_cred_{i}")
        sems_data.append({"sem": i, "sgpa": sg, "credits": cr})
    if st.button("Compute CGPA"):
        df_sem = pd.DataFrame(sems_data)
        df_valid = df_sem[df_sem["sgpa"] > 0]
        total_credits = df_valid["credits"].sum()
        if total_credits == 0:
            st.error("No credits entered. CGPA requires credit-weighted average.")
        else:
            cgpa = round((df_valid["sgpa"] * df_valid["credits"]).sum() / total_credits, GPA_DECIMALS)
            st.success(f"✅ CGPA (10-point): {cgpa}")
            # bar chart (neutral)
            fig2, ax2 = plt.subplots(figsize=(8,3))
            ax2.bar(df_valid["sem"].astype(str), df_valid["sgpa"], color="#dfe6ee", edgecolor="#aab6c8")
            ax2.set_xlabel("Semester"); ax2.set_ylabel("SGPA")
            st.pyplot(fig2)
            # allow save CGPA summary
            if st.button("Save CGPA Summary"):
                out = df_valid.copy()
                out["student"] = st.session_state.get("student_name")
                out["cgpa"] = cgpa
                fname = f"{st.session_state.get('student_name')}_CGPA_{now_ts()}.csv".replace(" ", "_")
                p = save_csv(out, fname)
                st.info(f"Saved CGPA CSV: {p}")

# -------------------------
# Feature: Multi-country conversion
# -------------------------
elif choice == "Multi-country conversion":
    st.header("Step 3 — Multi-country GPA Conversion")
    st.info("Select a country and convert CGPA/GPA. You can enter computed CGPA or type manually.")
    cgpa_input = st.number_input("Enter CGPA (10-point)", min_value=0.0, max_value=10.0, value=float(st.session_state.get("last_cgpa", 8.0)), step=0.01)
    country = st.selectbox("Select country", TOP_COUNTRIES)
    if st.button("Convert"):
        conv = convert_cgpa_to_countries(cgpa_input)
        if country in conv:
            st.subheader(f"{country} conversion")
            st.json(conv[country])
        else:
            st.info("Conversion not found.")
        # show small guidance/advice
        if country == "United States":
            usg = conv.get("United States", {}).get("gpa")
            if usg and usg >= 3.5:
                st.success("Excellent — competitive for many US master's programs.")
            elif usg and usg >= 3.0:
                st.info("Good — many programs accept this range with strong SOP.")
            else:
                st.warning("Consider improving CGPA or highlighting projects/research.")

# -------------------------
# Feature: Target & Planner
# -------------------------
elif choice == "Target & Planner (SEE required)":
    st.header("Step 4 — Target & Planner")
    st.info("Enter current CIE (out of 50) and select target grade point per subject. Choose difficulty to get a study-plan suggestion and required SEE.")
    cie = st.number_input("Enter current CIE total (out of 50)", min_value=0.0, max_value=50.0, value=20.0)
    target_gp = st.selectbox("Target grade point (10-point)", [10.0,9.0,8.0,7.0,6.0,5.0,4.0])
    # topic difficulty options
    st.markdown("Enter subjects and difficulty (Easy / Moderate / Hard).")
    n = st.number_input("Number of subjects in plan", min_value=1, max_value=12, value=5, key="plan_n")
    plan_rows = []
    for i in range(int(n)):
        cols = st.columns([3,1])
        sub = cols[0].text_input(f"Subject {i+1} name", value=f"Subject_{i+1}", key=f"plan_sub_{i}")
        diff = cols[1].selectbox("Difficulty", ["Easy","Moderate","Hard"], key=f"plan_diff_{i}")
        plan_rows.append({"subject": sub, "difficulty": diff})
    # determine lower percent threshold for target_gp
    lower = None
    for mn, mx, lbl, gp in PERCENT_TO_GRADE:
        if abs(gp - target_gp) < 1e-6:
            lower = mn
            break
    if lower is None:
        st.error("Target not valid.")
    else:
        # compute required SEE per subject
        needed = lower - cie
        needed = max(0.0, min(50.0, needed))
        if st.button("Create Plan & Save Rating"):
            st.success(f"You need approximately {needed:.2f}/50 in SEE to reach grade point {target_gp} (per subject).")
            # produce study plan suggestions by difficulty
            plans_text = {}
            for r in plan_rows:
                subj = r["subject"]
                diff = r["difficulty"]
                if diff == "Easy":
                    steps = [
                        "Revise lecture notes (2 sessions of 1 hour)",
                        "Practice 10 MCQs & 2 previous year problems",
                        "Quick concept map & 30-min flashcards"
                    ]
                elif diff == "Moderate":
                    steps = [
                        "Detailed notes + 3 practice problems",
                        "Timed mock test (40 mins) + review mistakes",
                        "Group study session (60 mins) focusing on weak topics"
                    ]
                else:  # Hard
                    steps = [
                        "Deep dive: textbook chapters + worked examples",
                        "Daily problem set (5 problems) for 7 days",
                        "One-on-one coaching or peer tutoring"
                    ]
                plans_text[subj] = {"difficulty": diff, "steps": steps}
                # show each
                st.markdown(f"**{subj}** — {diff}")
                for s in steps:
                    st.write(f"- {s}")
            # rating input to record perceived usefulness (1-5)
            rating = st.slider("Rate this plan's usefulness (1 = low, 5 = high)", 1, 5, 4, key="plan_rating")
            # store rating in history
            history = load_history()
            entry = {
                "timestamp": now_ts(),
                "student": st.session_state.get("student_name"),
                "hallticket": st.session_state.get("hallticket"),
                "program": st.session_state.get("program"),
                "action": "planner",
                "target_gp": target_gp,
                "needed_in_see": needed,
                "plan_items": plans_text,
                "rating": int(rating)
            }
            history.append(entry)
            save_history(history)
            st.success("Plan saved to history. Admin can view ratings in Admin panel.")

# -------------------------
# Feature: View Saved Results
# -------------------------
elif choice == "View Saved Results":
    st.header("Saved Results & Files")
    st.info("All saved CSV/PDF files are in the 'results/' folder (server-side). Use download or delete.")
    files = sorted(RESULTS_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        st.info("No saved files yet.")
    else:
        for f in files[:100]:
            cols = st.columns([3,1,1])
            cols[0].write(f.name)
            if cols[1].button(f"Download", key=f"dl_{f.name}"):
                cols[1].download_button("Download", data=f.read_bytes(), file_name=f.name, mime=("application/pdf" if f.suffix==".pdf" else "text/csv"))
            if cols[2].button(f"Delete", key=f"del_{f.name}"):
                try:
                    f.unlink()
                    st.success(f"Deleted {f.name}")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")

# -------------------------
# Feature: Admin (Premium Auto-fill + Auto-login)
# -------------------------
elif choice == "Admin":
    # Premium admin card and auto-login (Option B)
    st.header("Admin — Secure Panel (Export / Ratings / Reset)")

    # --- Auto-admin credentials (kept here for local use) ---
    AUTO_ADMIN_USER = "Myakala.Vignesh"
    AUTO_ADMIN_PASS = "Vignesh@2025"

    # Try to read from secrets or env if available (but auto-fill still works)
    try:
        ADMIN_USER = st.secrets.get('admin', {}).get('username', AUTO_ADMIN_USER)
        ADMIN_PASS = st.secrets.get('admin', {}).get('password', AUTO_ADMIN_PASS)
    except Exception:
        ADMIN_USER = os.environ.get('ADMIN_USER', AUTO_ADMIN_USER)
        ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', AUTO_ADMIN_PASS)

    # Premium UI CSS
    st.markdown("""
    <style>
      .admin-card { background: rgba(255,255,255,0.04); padding: 20px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06); }
      .admin-title { font-size: 26px; font-weight:700; color:#E8F1FF }
      .logged-banner { padding: 12px; background: linear-gradient(90deg, #4e54c8, #8f94fb); color: white; border-radius: 10px; font-size: 16px; text-align:center; }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.get("admin_authenticated", False):
        st.markdown(f'<div class="logged-banner">👑 Welcome back, {st.session_state.get("admin_user")} (Admin)</div>', unsafe_allow_html=True)
        history = load_history()
        if not history:
            st.info("No history entries yet.")
        else:
            hist_df = pd.json_normalize(history)
            st.dataframe(hist_df.fillna("").head(200))
            if st.button("Export All History to Excel"):
                out_path = RESULTS_DIR / f"all_history_{now_ts()}.xlsx"
                try:
                    hist_df.to_excel(out_path, index=False)
                    st.success(f"Saved: {out_path}")
                    st.download_button("Download Excel", data=out_path.read_bytes(), file_name=out_path.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as e:
                    st.error(f"Export failed: {e}")
            ratings = [h.get("rating") for h in history if h.get("rating") is not None]
            if ratings:
                avg_rating = sum(ratings)/len(ratings)
                st.metric("Average Plan Rating", f"{avg_rating:.2f} / 5", delta=f"{len(ratings)} ratings")
            else:
                st.info("No ratings recorded yet.")
            if st.button("Reset History (delete files & records)"):
                for f in RESULTS_DIR.glob("*"):
                    try:
                        f.unlink()
                    except:
                        pass
                save_history([])
                st.success("History reset and files deleted.")
                st.experimental_rerun()
    else:
        # show login card with pre-filled values
        st.markdown('<div class="admin-card">', unsafe_allow_html=True)
        st.markdown('<div class="admin-title">Admin Login</div>', unsafe_allow_html=True)
        username = st.text_input("Admin username", value=ADMIN_USER)
        password = st.text_input("Admin password", value=ADMIN_PASS, type="password")
        st.info("Auto-filled credentials detected. Logging you in…")
        if username == ADMIN_USER and password == ADMIN_PASS:
            st.session_state["admin_authenticated"] = True
            st.session_state["admin_user"] = ADMIN_USER
            st.success("Admin logged in automatically!")
            st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown(f"""
<div style='text-align:center; color:gray;'>
© {YEAR} • {APP_TITLE} • Built by <b>{AUTHOR}</b> • Public App — {SCHOOL} &bull; 
<a href='https://github.com/myakalavignesh01/calci' target='_blank' style='color:#9CDCFE'>GitHub</a> &nbsp; • Made with <a href='https://streamlit.io' target='_blank'>Streamlit</a>
</div>
""", unsafe_allow_html=True)

# -------------------------
# Persistent User Rating Section (saved to history.json)
# -------------------------
st.markdown("---")
st.markdown("### ⭐ Rate This App")
st.write("Help us improve Calci.py — your rating and short feedback will be saved locally (visible to Admin).")

rating = st.slider("Rate this App (1 to 5 Stars)", 1, 5, 5, key="ui_rating_slider")
feedback = st.text_area("Optional feedback (short)", value="", key="ui_rating_feedback")

if st.button("Submit Rating"):
    entry = {
        "timestamp": now_ts(),
        "student": st.session_state.get("student_name") or "",
        "hallticket": st.session_state.get("hallticket") or "",
        "program": st.session_state.get("program") or "",
        "action": "app_rating",
        "rating": int(rating),
        "feedback": feedback or ""
    }
    hist = load_history()
    hist.append(entry)
    save_history(hist)
    st.success("Thank you — your rating has been saved. 🎉")
    # optional immediate CSV download of this rating
    try:
        one_row = pd.DataFrame([entry])
        csv_bytes = one_row.to_csv(index=False).encode("utf-8")
        st.download_button("Download rating CSV", data=csv_bytes, file_name=f"rating_{now_ts()}.csv", mime="text/csv")
    except Exception:
        pass

# End of file
