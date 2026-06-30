import streamlit as st
import pandas as pd
import datetime
import gspread

st.set_page_config(page_title="60-Min Workout Tracker", page_icon="🏋️‍♂️", layout="centered")
st.title("🏋️‍♂️ 60-Min Workout Tracker")

# --- INITIALIZE NATIVE GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_gspread_client():
    creds = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }
    return gspread.service_account_from_dict(creds)

try:
    gc = get_gspread_client()
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = gc.open_by_url(spreadsheet_url)
    worksheet = sh.worksheet("Logs")
    
    records = worksheet.get_all_records()
    if records:
        existing_df = pd.DataFrame(records)
    else:
        existing_df = pd.DataFrame(columns=["Date", "Exercise", "Weight (lbs)", "Reps", "Difficulty"])
except Exception as e:
    st.error(f"Database connection error: {e}")
    existing_df = pd.DataFrame(columns=["Date", "Exercise", "Weight (lbs)", "Reps", "Difficulty"])

# --- WORKOUT ROUTINE DEFINITIONS ---
ALL_ABS = ["Captain's Chair Leg Raises", "Plank", "Crunches", "Hanging Knee Raises", "Russian Twists"]

ROUTINES = {
    "Monday (Push Focus)": {
        "core": ["Bench Press Machine", "Leg Press Machine", "Dumbbell Shoulder Press", "Cable Tricep Pushdown", "Seated Dip Machine"],
        "optional": ["Dumbbell Lateral Raises"] + ALL_ABS
    },
    "Wednesday (Pull Focus)": {
        "core": ["Lat Pulldown Machine", "Seated Row Machine", "Dumbbell Bicep Curl"],
        "optional": ["Hammer Curls", "Face Pulls"] + ALL_ABS
    },
    "Saturday (Isolation Focus)": {
        "core": ["Leg Press Machine", "Chest Fly Machine"],
        "optional": ["Calf Raises", "Dumbbell Shrugs"] + ALL_ABS
    }
}

# Auto-detect day of the week
current_day = datetime.datetime.now().strftime("%A")
default_index = 0
if current_day == "Monday": default_index = 0
elif current_day == "Wednesday": default_index = 1
elif current_day == "Saturday": default_index = 2

# --- USER INTERFACE ---
st.header("Today's Training Plan")
routine_choice = st.selectbox("Select Workout Routine:", list(ROUTINES.keys()), index=default_index)

st.subheader("📋 Core Minimum Exercises")
for ex in ROUTINES[routine_choice]["core"]:
    st.markdown(f"**• {ex}**")

st.write("---")
has_extra_time = st.checkbox("➕ I have extra time today! Show bonus & abdominal exercises.")

available_exercises = ROUTINES[routine_choice]["core"].copy()
if has_extra_time:
    st.subheader("🔥 Optional Bonus & Core Movements")
    for ex in ROUTINES[routine_choice]["optional"]:
        st.markdown(f"**• {ex}**")
    available_exercises.extend(ROUTINES[routine_choice]["optional"])

# --- LIVE WORKOUT LOGGING ---
st.write("---")
st.subheader("Log Your Sets")

exercise_input = st.selectbox("Select Exercise Lift:", available_exercises)

# --- SMART PROGRESSIVE OVERLOAD COACHING ---
if not existing_df.empty and "Exercise" in existing_df.columns:
    ex_history = existing_df[existing_df["Exercise"] == exercise_input].copy()
    
    if not ex_history.empty:
        ex_history["Date"] = pd.to_datetime(ex_history["Date"])
        latest_date = ex_history["Date"].max()
        latest_session = ex_history[ex_history["Date"] == latest_date]
        
        last_max_weight = pd.to_numeric(latest_session["Weight (lbs)"]).max()
        
        if exercise_input == "Leg Press Machine":
            calc_target = last_max_weight * 1.05
        else:
            calc_target = last_max_weight * 1.025
            
        recommended_target = float(round(calc_target * 2) / 2)
        if recommended_target == last_max_weight:
            recommended_target += 0.5
            
        if exercise_input in ALL_ABS and last_max_weight == 0:
            st.info(f"💡 **AI Coach Advice:** Last time you did this, you logged bodyweight reps. Try to beat your previous repetition count!")
        else:
            st.info(f"💡 **AI Coach Advice:** Last time you performed this exercise, your max weight was **{last_max_weight} lbs**. Today, aim for **{recommended_target} lbs** to stay on track with progressive overload!")
    else:
        st.info("💡 **AI Coach Advice:** First time logging this movement! Pick a comfortable baseline metric to establish your starting point.")

if "session_log" not in st.session_state:
    st.session_state.session_log = []

date_input = st.date_input("Date", datetime.date.today())
weight_input = st.number_input("Weight (lbs) - Set to 0 for bodyweight", min_value=0.0, step=0.5, value=10.0 if exercise_input not in ALL_ABS else 0.0)
reps_input = st.number_input("Reps Completed (or Seconds for Plank)", min_value=0, step=1, value=10)
difficulty_input = st.selectbox("Workout Intensity Feel:", ["Moderate", "Easy", "Hard"])

submit_set = st.button("Record Set")

if submit_set:
    set_data = {
        "Date": date_input.strftime("%Y-%m-%d"),
        "Exercise": exercise_input,
        "Weight (lbs)": float(weight_input),
        "Reps": int(reps_input),
        "Difficulty": difficulty_input
    }
    st.session_state.session_log.append(set_data)
    st.success(f"Recorded: {exercise_input} — {weight_input} lbs x {reps_input} reps ({difficulty_input})")

# Live screen display of the ongoing session
if st.session_state.session_log:
    st.subheader("Current Session Live View")
    session_df = pd.DataFrame(st.session_state.session_log)
    st.dataframe(session_df, use_container_width=True)
    
    if st.button("💾 Save Entire Workout to Google Sheets"):
        with st.spinner("Pushing workout to the cloud..."):
            new_sets_df = pd.DataFrame(st.session_state.session_log)
            updated_df = pd.concat([existing_df, new_sets_df], ignore_index=True)
            
            updated_df["Date"] = pd.to_datetime(updated_df["Date"]).dt.strftime("%Y-%m-%d")
            updated_df["Weight (lbs)"] = updated_df["Weight (lbs)"].astype(float)
            updated_df["Reps"] = updated_df["Reps"].astype(int)
            updated_df["Difficulty"] = updated_df["Difficulty"].astype(str)
            
            try:
                data_to_upload = [updated_df.columns.tolist()] + updated_df.values.tolist()
                
                worksheet.clear()
                worksheet.update(values=data_to_upload, range_name="A1")
                
                st.success("Workout safely saved to Google Sheets!")
                st.session_state.session_log = [] 
                
                # 🟢 THE FIX: Correct modern method to clear cache and refresh smoothly
                st.cache_resource.clear() 
                st.rerun()
            except Exception as save_error:
                st.error(f"Save failed: {save_error}")

# --- HISTORICAL PROGRESS VISUALIZATION ---
if not existing_df.empty and "Exercise" in existing_df.columns:
    st.write("---")
    st.header("📈 Progress History")
    
    existing_df["Date"] = pd.to_datetime(existing_df["Date"])
    filter_exercise = st.selectbox("View Progress Chart For:", existing_df["Exercise"].unique(), key="viz_filter")
    filtered_df = existing_df[existing_df["Exercise"] == filter_exercise].sort_values(by="Date")
    
    if not filtered_df.empty:
        progress_df = filtered_df.groupby("Date")["Weight (lbs)"].max().reset_index()
        st.line_chart(data=progress_df, x="Date", y="Weight (lbs)")
        st.dataframe(filtered_df.sort_values(by="Date", ascending=False), use_container_width=True, hide_index=True)
