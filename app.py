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
# Abdominal list is now perfectly uniform across all 3 days
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
            recommended_target
