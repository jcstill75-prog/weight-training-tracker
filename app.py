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
ROUTINES = {
    "Monday (Push Focus)": {
        "core": ["Bench Press Machine", "Leg Press Machine", "Dumbbell Shoulder Press", "Cable Tricep Pushdown", "Seated Dip Machine"],
        "optional": ["Dumbbell Lateral Raises"]
    },
    "Wednesday (Pull Focus)": {
        "core": ["Lat Pulldown Machine", "Seated Row Machine", "Dumbbell Bicep Curl"],
        "optional": ["Hammer Curls", "Face Pulls"]
    },
    "Saturday (Isolation & Core)": {
        "core": ["Leg Press Machine", "Chest Fly Machine", "Captain's Chair Leg Raises"],
        "optional": ["Calf Raises", "Dumbbell Shrugs"]
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
has_extra_time = st.checkbox("➕ I have extra time today! Show bonus exercises.")

available_exercises = ROUTINES[routine_choice]["core"].copy()
if has_extra_time:
    st.subheader("🔥 Optional Bonus Movements")
    for ex in ROUTINES[routine_choice]["optional"]:
        st.markdown(f"**• {ex}**")
    available_exercises.extend(ROUTINES[routine_choice]["optional"])

# --- LIVE WORKOUT LOGGING ---
st.write("---")
st.subheader("Log Your Sets")

# Select exercise lift first (placed outside the form so the coaching advice can update dynamically)
exercise_input = st.selectbox("Select Exercise Lift:", available_exercises)

# --- SMART PROGRESSIVE OVERLOAD COACHING ---
if not existing_df.empty:
    # Filter history for just this exercise
    ex_history = existing_df[existing_df["Exercise"] == exercise_input].copy()
    
    if not ex_history.empty:
        # Get the most recent date this exercise was performed
        ex_history["Date"] = pd.to_datetime(ex_history["Date"])
        latest_date = ex_history["Date"].max()
        latest_session = ex_history[ex_history["Date"] == latest_date]
        
        # Find the max weight used in that last session
        last_max_weight = pd.to_numeric(latest_session["Weight (lbs)"]).max()
        
        # Calculate progression target based on muscle group rules
        # Leg press gets a 5% bump, upper body gets a 2.5% bump
        if exercise_input == "Leg Press Machine":
            calc_target = last_max_weight * 1.05
        else:
            calc_target = last_max_weight * 1.025
            
        # Round to the nearest 5 lbs to match gym increments
        recommended_target = int(5 * round(calc_target / 5))
        if recommended_target == last_max_weight:
            recommended_target += 5 # Force at least a 5lb increase if rounding stalls it
            
        st.info(f"💡 **AI Coach Advice:** Last time you performed this exercise, your max weight was **{int(last_max_weight)} lbs**. Today, aim for **{recommended_target} lbs** to stay on track with progressive overload!")
    else:
        st.info("💡 **AI Coach Advice:** First time logging this movement! Pick a comfortable baseline weight to establish your starting metric.")

if "session_log" not in st.session_state:
    st.session_state.session_log = []

# Form handles remaining inputs
with st.form("log_form", clear_on_submit=True):
    date_input = st.date_input("Date", datetime.date.today())
    weight_input = st.number_input("Weight (lbs)", min_value=0, step=5, value=100)
    reps_input = st
