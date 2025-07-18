import streamlit as st
import google.generativeai as genai
import re
import speech_recognition as sr
import datetime
import json
import sounddevice as sd
import numpy as np


 
# Configure API key
genai.configure(api_key="AIzaSyAVBpl80sSDlYv_qvo0QuEgKEvD88JpV8k")

# Use the correct model path
model = genai.GenerativeModel(model_name="gemini-1.5-flash")




# --- Language Mapping ---
language_map = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Marathi": "mr-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
}

# --- Daily Question Limit --- 
QUESTIONS_PER_DAY = 30

# --- Initialize Session State ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = {}

if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def get_current_date():
    return datetime.date.today().isoformat()

def load_chat_log():
    try:
        with open("chat_log.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_chat_log(chat_log):
    with open("chat_log.json", "w") as f:
        json.dump(chat_log, f)

chat_log = load_chat_log()

def is_within_daily_limit(mobile_number):
    today = get_current_date()
    if mobile_number in chat_log and today in chat_log[mobile_number]:
        return len(chat_log[mobile_number][today]) < QUESTIONS_PER_DAY
    return True

def increment_question_count(mobile_number, question, answer, language):
    today = get_current_date()
    timestamp = datetime.datetime.now().isoformat()
    if mobile_number not in chat_log:
        chat_log[mobile_number] = {}  
    if today not in chat_log[mobile_number]:
        chat_log[mobile_number][today] = []
    chat_log[mobile_number][today].append({"question": question, "answer": answer, "language": language, "timestamp": timestamp})
    save_chat_log(chat_log)

def reset_session():
    st.session_state["current_user"] = None
    st.session_state["chat_history"] = []

# --- User Registration ---
if not st.session_state["current_user"]:
    st.title("TAC AI Registration")
    name = st.text_input("Your Name:")
    mobile_number = st.text_input("Mobile Number:")
    register_button = st.button("Register/Login")

    if register_button:
        if name and mobile_number and re.match(r"^[6-9]\d{9}$", mobile_number):
            st.session_state["current_user"] = mobile_number
            st.session_state["user_data"][mobile_number] = {"name": name}
            st.success(f"Welcome, {name}!")
            st.session_state["chat_history"] = chat_log.get(mobile_number, {}).get(get_current_date(), [])
        else:
            st.error("Please enter a valid name and 10-digit Indian mobile number.")

else:
    st.sidebar.title("TAC AI")
    st.sidebar.button("Logout", on_click=reset_session)
    st.sidebar.markdown(f"Logged in as: **{st.session_state['user_data'][st.session_state['current_user']]['name']}**")

    language = st.selectbox("Select Language", list(language_map.keys()))
    selected_language_code = language_map[language]

    question = st.text_input("Ask your farming question:")

    if st.button("Speak your question"):
        try:
            duration = 10  # Record for 10 seconds
            sample_rate = 44100  # Standard sample rate
            st.info("Speak now...")
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
            sd.wait()
            audio_data = (recording * 32767).astype(np.int16)
            
            r = sr.Recognizer()
            audio = sr.AudioData(audio_data.tobytes(), sample_rate, 2)
            spoken_question = r.recognize_google(audio, language=selected_language_code)
            st.session_state["spoken_question"] = spoken_question
        except Exception as e:
            st.error(f"Voice are not clear : {e}")

    if "spoken_question" in st.session_state and st.session_state["spoken_question"]:
        question = st.session_state["spoken_question"]
        del st.session_state["spoken_question"]

    if question:
        if is_within_daily_limit(st.session_state["current_user"]):
            try:
                response = model.generate_content(question)
                answer = response.text

                # --- Gemini-style answer (already the default for gemini-pro) ---
                st.info(f"**Question ({language}):** {question}")
                st.success(f"**Answer:** {answer}") 

                # --- Store chat history ---
                increment_question_count(st.session_state["current_user"], question, answer, language)
                st.session_state["chat_history"] = chat_log.get(st.session_state["current_user"], {}).get(get_current_date(), [])

                # --- Show related info links (basic example - needs more sophisticated logic) ---
                if "disease" in question.lower() or "pest" in question.lower():
                    st.markdown("[Find more information on crop diseases and pests](https://agritech.tnau.ac.in/crop_protection/)")
                elif "fertilizer" in question.lower() or "nutrient" in question.lower():
                    st.markdown("[Learn about fertilizer management](https://www.fao.org/land-water/databases-and-software/drup/drup-home/en/)")

            except Exception as e:
                st.error(f"An error occurred while fetching the answer: {e}")
        else:
            st.warning(f"For more information contact TAC{QUESTIONS_PER_DAY} subscription .")

    # --- Display Chat History ---
    st.subheader("Chat History")
    if st.session_state["current_user"] and get_current_date() in chat_log.get(st.session_state["current_user"], {}):
        for chat in chat_log[st.session_state["current_user"]][get_current_date()]:
            st.markdown(f"**({chat['language']}) You:** {chat['question']}")
            st.info(f"**Bot:** {chat['answer']}")
    elif st.session_state["chat_history"]: # Fallback for current session before saving
        for chat in st.session_state["chat_history"]:
            st.markdown(f"**({chat['language']}) You:** {chat['question']}")
            st.info(f"**Bot:** {chat['answer']}")
    else:
        st.info("No chat history for today.")


# Optional: suppress the warnings
import logging
logging.getLogger('streamlit.runtime.scriptrunner.script_run_context').setLevel(logging.ERROR)