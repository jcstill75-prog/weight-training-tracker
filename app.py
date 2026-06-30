import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

st.set_page_config(page_title="60-Min Workout Tracker", page_icon="🏋️‍♂️", layout="centered")
st.title("🏋️‍♂️ 60-Min Workout Tracker")

# --- INITIALIZE GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch existing data from the "Logs" sheet
try:
    existing_df = conn.read(worksheet="Logs", ttl="0d") 
    existing_df = existing_df.dropna(how="all")
except Exception:
    existing_df = pd.DataFrame(columns=["Date", "Exercise", "Weight (lbs)", "Reps", "Difficulty"])

# --- WORKOUT ROUTINE DEFINITIONS ---
# All abdominal and core exercises are now moved strictly to the "optional" sections
ROUTINES = {
    "Monday (Push Focus)": {
        "core": ["Bench Press Machine", "Leg Press Machine", "Dumbbell Shoulder Press", "Cable Tricep Pushdown", "Seated Dip Machine"],
        "optional": ["Dumbbell Lateral Raises", "Crunches", "Plank"]
    },
    "Wednesday (Pull Focus)": {
        "core": ["Lat Pulldown Machine", "Seated Row Machine", "Dumbbell Bicep Curl"],
        "optional": ["Hammer Curls", "Face Pulls", "Russian Twists"]
    },
    "Saturday (Isolation Focus)": {
        "core": ["Leg Press Machine", "Chest Fly Machine"],
        "optional": ["Calf Raises", "Dumbbell Shrugs", "Captain's Chair Leg Raises", "Hanging Knee Raises"]
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

# Select exercise lift 
exercise_input = st.selectbox("Select Exercise Lift:", available_exercises)

# --- SMART PROGRESSIVE OVERLOAD COACHING ---
if not existing_df.empty:
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
            
        # Hide target weight advice for bodyweight core moves like Planks/Crunches where tracking weight isn't the primary goal
        if exercise_input in ["Plank", "Crunches", "Captain's Chair Leg Raises", "Hanging Knee Raises", "Russian Twists"] and last_max_weight == 0:
            st.info(f"💡 **AI Coach Advice:** Last time you did this, you logged bodyweight reps. Try to beat your previous repetition count or duration!")
        else:
            st.info(f"💡 **AI Coach Advice:** Last time you performed this exercise, your max weight was **{last_max_weight} lbs**. Today, aim for **{recommended_target} lbs** to stay on track with progressive overload!")
    else:
        st.info("💡 **AI Coach Advice:** First time logging this movement! Pick a comfortable baseline weight/reps to establish your starting metric.")

if "session_log" not in st.session_state:
    st.session_state.session_log = []

# Clean input layout
date_input = st.date_input("Date", datetime.date.today())

# Note: Set weight to 0.0 if doing standard bodyweight crunches/planks
weight_input = st.number_input("Weight (lbs) - Set to 0 for bodyweight", min_value=0.0, step=0.5, value=10.0 if exercise_input not in ["Plank", "Crunches", "Captain's Chair Leg Raises", "Hanging Knee Raises", "Russian Twists"] else 0.0)
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
            
            # Combine datasets first
            updated_df = pd.concat([existing_df, new_sets_df], ignore_index=True)
            
            # Explicitly convert the combined Date column to datetime first
            updated_df["Date"] = pd.to_datetime(updated_df["Date"])
            
            # Now format securely to strings for Google Sheets
            updated_df["Date"] = updated_df["Date"].dt.strftime("%Y-%m-%d")
            
            conn.update(worksheet="Logs", data=updated_df)
            
            st.success("Workout safely saved to Google Sheets!")
            st.session_state.session_log = [] 
            st.rerun()

# --- HISTORICAL PROGRESS VISUALIZATION ---
if not existing_df.empty:
    st.write("---")
    st.header("📈 Progress History")
    
    existing_df["Date"] = pd.to_datetime(existing_df["Date"])
    filter_exercise = st.selectbox("View Progress Chart For:", existing_df["Exercise"].unique(), key="viz_filter")
    filtered_df = existing_df[existing_df["Exercise"] == filter_exercise].sort_values(by="Date")
    
    if not filtered_df.empty:
        progress_df = filtered_df.groupby("Date")["Weight (lbs)"].max().reset_index()
        st.line_chart(data=progress_df, x="Date", y="Weight (lbs)")
        st.dataframe(filtered_df.sort_values(by="Date", ascending=False), use_container_width=True, hide_index=True)
