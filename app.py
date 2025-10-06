import streamlit as st
import requests
import json
import uuid
import pandas as pd
from datetime import datetime, time

API_ENDPOINT = "YOUR_API_GATEWAY_URL"

st.set_page_config(page_title="MoodFlow", page_icon="🌊", layout="wide")

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.current_schedule = None
    st.session_state.current_mood = None
    st.session_state.unscheduled_tasks = []
    st.session_state.schedule_history = []
    st.session_state.current_schedule_date = None

st.title("🌊 MoodFlow: Emotion-Aware AI Planner")
st.caption("AWS Bedrock + Knowledge Base + Guardrails | UCLA Gen AI Hackathon 2025")

with st.sidebar:
    st.header("Planning Parameters")
    
    selected_date = st.date_input(
        "Planning date",
        value=st.session_state.get('selected_date', datetime.now().date()),
        min_value=datetime.now().date()
    )
    st.session_state.selected_date = selected_date
    
    # Quick view button
    if st.button("📅 View Schedule for This Date"):
        date_display = selected_date.strftime('%A, %B %d, %Y')
        view_message = f"show me schedule\n\n[Planning for {date_display} | Start: {st.session_state.get('start_work_time', time(9, 0)).strftime('%I:%M %p')} | End by: {st.session_state.get('work_until', time(17, 0)).strftime('%I:%M %p')}]"
        
        with st.spinner("Fetching schedule..."):
            try:
                response = requests.post(
                    API_ENDPOINT,
                    params={'session_id': st.session_state.session_id},
                    json={'message': view_message},
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    schedule = data.get('schedule', [])
                    
                    if schedule:
                        st.session_state.current_schedule = schedule
                        st.session_state.current_mood = data.get('mood_detected', 'unknown')
                        st.session_state.current_schedule_date = selected_date
                        st.success(f"Loaded schedule for {selected_date.strftime('%B %d')}")
                        st.rerun()
                    else:
                        st.warning("No schedule found for this date")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    st.divider()
    
    start_work_time = st.time_input(
        "Start working at",
        value=st.session_state.get('start_work_time', time(9, 0)),
        help="Schedule will start from this time"
    )
    st.session_state.start_work_time = start_work_time
    
    work_until = st.time_input(
        "Work until",
        value=st.session_state.get('work_until', time(17, 0))
    )
    st.session_state.work_until = work_until
    
    st.divider()
    
    st.header("Tech Stack")
    st.markdown("""
    **AWS Services:**
    - Amazon Bedrock (Claude 3.5 Sonnet v2)
    - Bedrock Knowledge Base (RAG)
    - Bedrock Guardrails
    - DynamoDB
    - Lambda + API Gateway
    - OpenSearch Serverless
    """)
    
    st.divider()
    
    if st.button("Reset Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.current_schedule = None
        st.session_state.current_mood = None
        st.session_state.unscheduled_tasks = []
        st.session_state.schedule_history = []
        st.session_state.current_schedule_date = None
        st.rerun()

st.warning(f"⏰ Planning for **{selected_date.strftime('%A, %B %d')}** | Start: **{start_work_time.strftime('%I:%M %p')}** | End by: **{work_until.strftime('%I:%M %p')}**")

for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.write(msg['content'])

user_input = st.chat_input("Tell me about your tasks and how you're feeling...")

if user_input:
    date_display = selected_date.strftime('%A, %B %d, %Y')
    enhanced_message = f"{user_input}\n\n[Planning for {date_display} | Start: {start_work_time.strftime('%I:%M %p')} | End by: {work_until.strftime('%I:%M %p')}]"
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.write(user_input)
    
    with st.spinner("Planning your day..."):
        try:
            response = requests.post(
                API_ENDPOINT,
                params={'session_id': st.session_state.session_id},
                json={'message': enhanced_message},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                bot_message = data.get('response_message', 'Schedule created!')
                schedule = data.get('schedule', [])
                mood = data.get('mood_detected', 'unknown')
                unscheduled = data.get('unscheduled_tasks', [])
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": bot_message
                })
                
                st.session_state.current_schedule = schedule
                st.session_state.current_mood = mood
                st.session_state.unscheduled_tasks = unscheduled
                st.session_state.current_schedule_date = selected_date
                
                # Add to history
                st.session_state.schedule_history.append({
                    'timestamp': datetime.now(),
                    'date': selected_date,
                    'schedule': schedule,
                    'mood': mood
                })
                
                # Keep only last 10 versions
                if len(st.session_state.schedule_history) > 10:
                    st.session_state.schedule_history.pop(0)
                
                with st.chat_message("assistant"):
                    st.write(bot_message)
                    
                    mood_emoji = {
                        'stressed': '😰',
                        'energized': '⚡',
                        'anxious': '😟',
                        'focused': '🎯',
                        'tired': '😴',
                        'sad': '😢',
                        'happy': '😊',
                        'unknown': '❓'
                    }
                    st.write(f"**Detected mood:** {mood_emoji.get(mood, '❓')} {mood}")
                
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            st.error("Request timed out.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

if st.session_state.current_schedule:
    st.divider()
    
    # Show which date this schedule is for
    schedule_date = st.session_state.current_schedule_date if st.session_state.current_schedule_date else selected_date
    st.header(f"📅 Your Optimized Schedule for {schedule_date.strftime('%A, %B %d, %Y')}")
    
    df = pd.DataFrame(st.session_state.current_schedule)
    
    column_order = ['time', 'task', 'reasoning', 'wellness_note']
    existing_cols = [col for col in column_order if col in df.columns]
    df = df[existing_cols]
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "time": st.column_config.TextColumn("Time", width="small"),
            "task": st.column_config.TextColumn("Task", width="medium"),
            "reasoning": st.column_config.TextColumn("Why Here", width="medium"),
            "wellness_note": st.column_config.TextColumn("Wellness Tip", width="medium")
        }
    )
    
    mood_emoji = {
        'stressed': '😰 Stressed',
        'energized': '⚡ Energized',
        'anxious': '😟 Anxious',
        'focused': '🎯 Focused',
        'tired': '😴 Tired',
        'sad': '😢 Sad',
        'happy': '😊 Happy',
        'unknown': '❓ Unknown'
    }
    
    current_mood = st.session_state.get('current_mood', 'unknown')
    st.info(f"Planning optimized for: **{mood_emoji.get(current_mood, 'Unknown')}** mood")
    
    # Show schedule history with dates
    if len(st.session_state.schedule_history) > 1:
        with st.expander("📜 Previous versions"):
            for idx, hist in enumerate(reversed(st.session_state.schedule_history[:-1])):
                st.caption(f"{hist['date'].strftime('%A, %B %d')} - Version {len(st.session_state.schedule_history) - idx - 1} ({hist['timestamp'].strftime('%I:%M %p')}) - Mood: {hist['mood']}")
                hist_df = pd.DataFrame(hist['schedule'])
                if not hist_df.empty:
                    st.dataframe(hist_df, use_container_width=True, hide_index=True)
                st.divider()

if st.session_state.unscheduled_tasks:
    st.divider()
    st.warning("⚠️ These tasks didn't fit in today's schedule:")
    unscheduled_df = pd.DataFrame(st.session_state.unscheduled_tasks)
    st.dataframe(unscheduled_df, use_container_width=True, hide_index=True)

    st.info("💬 Tell me which date you'd like to schedule these for (e.g., 'Schedule documentation for Oct 8')")
