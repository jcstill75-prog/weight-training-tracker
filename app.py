import streamlit as st
import pandas as pd
import datetime
import gspread
import math

st.set_page_config(page_title="Workout Tracker", page_icon="🏋️‍♂️", layout="centered")
st.title("🏋️‍♂️ Workout Tracker")

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
    "Push Focus": {
        "core": ["Bench Press Machine", "Leg Press Machine", "Dumbbell Shoulder Press", "Cable Tricep Pushdown", "Seated Dip Machine"],
        "optional": ["Dumbbell Lateral Raises"] + ALL_ABS
    },
    "Pull Focus": {
        "core": ["Lat Pulldown Machine", "Seated Row Machine", "Dumbbell Bicep Curl"],
        "optional": ["Hammer Curls", "Face Pulls"] + ALL_ABS
    },
    "Isolation Focus": {
        "core": ["Leg Press Machine", "Chest Fly Machine"],
        "optional": ["Calf Raises", "Dumbbell Shrugs"] + ALL_ABS
    }
}

REP_TARGETS = {
    "Bench Press Machine": "8–12 reps",
    "Lat Pulldown Machine": "8–12 reps",
    "Leg Press Machine": "10–12 reps (12–15 reps on Isolation days)",
    "Seated Row Machine": "10–12 reps",
    "Dumbbell Shoulder Press": "10–12 reps",
    "Cable Tricep Pushdown": "10–12 reps",
    "Seated Dip Machine": "10–12 reps",
    "Chest Fly Machine": "10–12 reps",
    "Dumbbell Bicep Curl": "12 reps",
    "Dumbbell Lateral Raises": "12–15 reps",
    "Hammer Curls": "10–12 reps",
    "Face Pulls": "12–15 reps",
    "Calf Raises": "12–15 reps",
    "Dumbbell Shrugs": "10–12 reps",
    "Captain's Chair Leg Raises": "10–12 reps",
    "Crunches": "12–15 reps",
    "Hanging Knee Raises": "10–12 reps",
    "Russian Twists": "12 reps each side",
    "Plank": "30–60 seconds"
}

# 🟢 REFACTOR: Rounds up total weight to the next possible 10-lb plate combination
def calculate_leg_press_plates(raw_target_weight):
    # Round up to the nearest multiple of 10 (since min increment per side is 5 lbs)
    total_target_weight = math.ceil(raw_target_weight / 10.0) * 10
    
    if total_target_weight <= 0:
        return total_target_weight, "Load nothing!"
        
    weight_per_side = total_target_weight / 2.0
    
    plates = {45: 0, 25: 0, 10: 0, 5: 0}
    remaining = weight_per_side
    
    for size in [45, 25, 10, 5]:
        count = int(remaining // size)
        plates[size] = count
        remaining -= count * size
        
    parts = []
    for size, count in plates.items():
        if count > 0:
            parts.append(f"{count}x {size} lb")
        
    return total_target_weight, f"Load **EACH SIDE** with: " + ", ".join(parts)

# --- USER INTERFACE ---
st.header("Today's Training Plan")
routine_choice = st.selectbox("Select Workout Routine:", list(ROUTINES.keys()), index=0)

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
target_rep_range = REP_TARGETS.get(exercise_input, "10–12 reps")

if not existing_df.empty and "Exercise" in existing_df.columns:
    ex_history = existing_df[existing_df["Exercise"] == exercise_input].copy()
    
    if not ex_history.empty:
        ex_history["Date"] = pd.to_datetime(ex_history["Date"])
        latest_date = ex_history["Date"].max()
        latest_session = ex_history[ex_history["Date"] == latest_date]
        
        last_max_weight = pd.to_numeric(latest_session["Weight (lbs)"]).max()
        
        if exercise_input == "Leg Press Machine":
            calc_target = last_max_weight * 1.05
            # Force at least a 10 lb total load increase if a 5% bump doesn't push past the rounding threshold
            if math.ceil(calc_target / 10.0) * 10 == last_max_weight:
                calc_target = last_max_weight + 10
        else:
            calc_target = last_max_weight * 1.025
            
        recommended_target = float(round(calc_target * 2) / 2)
        if recommended_target == last_max_weight and exercise_input != "Leg Press Machine":
            recommended_target += 0.5
            
        if exercise_input in ALL_ABS and last_max_weight == 0:
            st.info(f"💡 **AI Coach Advice:** Aim for **{target_rep_range}**. Try to beat your previous repetition count or duration!")
        else:
            # For leg press, compute rounded target and plate breakout text
            if exercise_input == "Leg Press Machine":
                recommended_target, plate_breakout = calculate_leg_press_plates(calc_target)
                advice_text = f"💡 **AI Coach Advice:** Aim for **{target_rep_range}**. Last time your max added weight was **{int(last_max_weight)} lbs**. Today, your rounded target is **{int(recommended_target)} lbs**!\n\n⚙️ **Plate Config:** {plate_breakout}"
            else:
                advice_text = f"💡 **AI Coach Advice:** Aim for **{target_rep_range}**. Last time your max weight was **{last_max_weight} lbs**. Today, your target is **{recommended_target} lbs**!"
                
            st.info(advice_text)
    else:
        st.info(f"💡 **AI Coach Advice:** First time logging this movement! Aim for **{target_rep_range}** at a comfortable baseline weight.")
else:
    st.info(f"💡 **AI Coach Advice:** Aim for **{target_rep_range}** at a comfortable baseline weight.")

if "session_log" not in st.session_state:
    st.session_state.session_log = []

date_input = st.date_input("Date", datetime.date.today())
weight_input = st.number_input("Weight (lbs) - Set to 0 for bodyweight", min_value=0.0, step=0.5, value=float(recommended_target) if (not existing_df.empty and not ex_history.empty and exercise_input not in ALL_ABS) else (10.0 if exercise_input not in ALL_ABS else 0.0))
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
