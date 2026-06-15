import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

st.set_page_config(page_title="60-Min Workout Tracker", page_icon="🏋️‍♂️", layout="centered")
st.title("🏋️‍♂️ 60-Min Workout Tracker")

# --- INITIALIZE GOOGLE SHEETS CONNECTION ---
# This automatically looks for the [connections.gsheets] settings in your secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# Fetch existing data from the "Logs" worksheet
try:
    existing_df = conn.read(worksheet="Logs", ttl="0d") # ttl=0 ensures it pulls live data every refresh
    # Clean up empty rows if any exist
    existing_df = existing_df.dropna(how="all")
except Exception:
    # Fallback if the sheet is completely empty
    existing_df = pd.DataFrame(columns=["Date", "Exercise", "Weight (lbs)", "Reps"])

# --- WORKOUT ROUTINE DEFINITIONS ---
ROUTINES = {
    "Monday (Push Focus)": {
        "core": ["Bench Press Machine", "Leg Press Machine", "Dumbbell Shoulder Press"],
        "optional": ["Dumbbell Lateral Raise", "Overhead Dumbbell Tricep Extension"]
    },
    "Wednesday (Pull Focus)": {
        "core": ["Lat Pulldown Machine", "Seated Row Machine", "Dumbbell Bicep Curl"],
        "optional": ["Hammer Curls", "Face Pulls"]
    },
    "Saturday (Isolation Focus)": {
        "core": ["Leg Press Machine", "Chest Fly Machine"],
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

st.subheader("📋 Core Minimum Exercises (Do these first)")
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

if "session_log" not in st.session_state:
    st.session_state.session_log = []

with st.form("log_form", clear_on_submit=True):
    date_input = st.date_input("Date", datetime.date.today())
    exercise_input = st.selectbox("Select Exercise Lift:", available_exercises)
    weight_input = st.number_input("Weight (lbs)", min_value=0, step=5, value=100)
    reps_input = st.number_input("Reps Completed", min_value=0, step=1, value=10)
    
    submit_set = st.form_submit_button("Record Set")

if submit_set:
    set_data = {
        "Date": date_input.strftime("%Y-%m-%d"),
        "Exercise": exercise_input,
        "Weight (lbs)": int(weight_input),
        "Reps": int(reps_input)
    }
    st.session_state.session_log.append(set_data)
    st.success(f"Recorded: {exercise_input} — {weight_input} lbs x {reps_input} reps")

# Live screen display of the ongoing session
if st.session_state.session_log:
    st.subheader("Current Session Live View")
    session_df = pd.DataFrame(st.session_state.session_log)
    st.dataframe(session_df, use_container_width=True)
    
    # Save button handles appending to Google Sheets
    if st.button("💾 Save Entire Workout to Google Sheets"):
        with st.spinner("Pushing workout to the cloud..."):
            # Combine historical data with new data
            new_sets_df = pd.DataFrame(st.session_state.session_log)
            updated_df = pd.concat([existing_df, new_sets_df], ignore_index=True)
            
            # Update the Google Sheet
            conn.update(worksheet="Logs", data=updated_df)
            
            st.success("Workout safely saved to Google Sheets!")
            st.session_state.session_log = [] # Wipe temporary local memory cache
            st.rerun()

# --- HISTORICAL PROGRESS VISUALIZATION ---
if not existing_df.empty:
    st.write("---")
    st.header("📈 Progress History")
    
    # Make sure formatting is correct for mapping
    existing_df["Date"] = pd.to_datetime(existing_df["Date"])
    
    filter_exercise = st.selectbox("View Progress Chart For:", existing_df["Exercise"].unique())
    filtered_df = existing_df[existing_df["Exercise"] == filter_exercise].sort_values(by="Date")
    
    if not filtered_df.empty:
        # Group by date and take the maximum weight lifted that day
        progress_df = filtered_df.groupby("Date")["Weight (lbs)"].max().reset_index()
        st.line_chart(data=progress_df, x="Date", y="Weight (lbs)")
        
        st.subheader("Raw History Table")
        st.dataframe(filtered_df.sort_values(by="Date", ascending=False), use_container_width=True, hide_index=True)
