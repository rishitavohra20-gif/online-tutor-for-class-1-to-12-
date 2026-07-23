"""
app.py - Main Streamlit interface for the Class 1-12 AI Tutor.

Run with: streamlit run app.py
"""

import streamlit as st
import json
import os
from dotenv import load_dotenv

import db
import rag_engine
import llm_utils

load_dotenv()

st.set_page_config(page_title="AI Tutor - Class 1 to 12", page_icon="🎈", layout="wide")
db.init_db()

# ---------- Fun, colorful styling for kids ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700;800&family=Nunito:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif;
}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Baloo 2', cursive !important;
}

/* Main app background */
.stApp {
    background: linear-gradient(135deg, #fef6e4 0%, #e0f7fa 50%, #fce4ec 100%);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffe0f0 0%, #e0f0ff 100%);
    border-right: 3px dashed #ff9ecf;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #ff6b9d 0%, #ff9a56 100%);
    color: white;
    border-radius: 20px;
    border: none;
    font-weight: 800;
    font-family: 'Baloo 2', cursive;
    font-size: 1.05rem;
    padding: 0.5rem 1.5rem;
    box-shadow: 0 4px 0 #d1477a;
    transition: transform 0.1s;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 0 #d1477a;
    color: white;
}
.stButton > button:active {
    transform: translateY(2px);
    box-shadow: 0 2px 0 #d1477a;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background-color: #ffffffaa;
    border-radius: 15px 15px 0 0;
    font-family: 'Baloo 2', cursive;
    font-weight: 700;
    font-size: 1.1rem;
    padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #a8e6cf, #dcedc1) !important;
    color: #2d4a2b !important;
}

/* Chat bubbles */
[data-testid="stChatMessage"] {
    border-radius: 20px;
    padding: 8px;
    margin-bottom: 8px;
}

/* Sliders and radio - rounded, colorful accents */
.stSlider [data-baseweb="slider"] > div > div {
    background: #ff9ecf !important;
}

/* Success/warning boxes rounder + colorful */
.stAlert {
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

SUBJECT_EMOJI = {
    "Mathematics": "🔢", "Science": "🔬", "English": "📖", "Hindi": "✒️",
    "Social Science": "🌍", "Physics": "⚛️", "Chemistry": "🧪", "Biology": "🌱",
    "Computer Science": "💻", "History": "🏛️", "Geography": "🗺️"
}

CLASS_OPTIONS = [str(i) for i in range(1, 13)]
SUBJECT_OPTIONS = [
    "Mathematics", "Science", "English", "Hindi", "Social Science",
    "Physics", "Chemistry", "Biology", "Computer Science", "History", "Geography"
]

# ---------- Sidebar: Setup ----------
st.sidebar.markdown("## 🎈 AI Tutor Setup 🎨")

# Try to load keys from Streamlit Cloud "Secrets" first (used after deployment).
# Falls back to manual entry for local testing.
def get_secret_or_env(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")

groq_key = get_secret_or_env("GROQ_API_KEY")
gemini_key = get_secret_or_env("GEMINI_API_KEY")

if not groq_key or not gemini_key:
    st.sidebar.info("🔑 No saved keys found — enter them below just for this session.")
    groq_key = st.sidebar.text_input("Groq API Key (free at console.groq.com)", type="password", value=groq_key)
    gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=gemini_key)

student_name = st.sidebar.text_input("🙋 Student Name", value="Student1")
class_level = st.sidebar.selectbox("🏫 Class", CLASS_OPTIONS, index=9)
subject = st.sidebar.selectbox("📘 Subject", SUBJECT_OPTIONS)

if not groq_key or not gemini_key:
    st.sidebar.warning("⚠️ Enter both API keys to use the tutor.")
    st.stop()

groq_client = llm_utils.get_groq_client(groq_key)
llm_utils.configure_gemini(gemini_key)

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Add Study Material (optional)")
uploaded_pdf = st.sidebar.file_uploader("Upload textbook/notes PDF", type=["pdf"])
topic_for_upload = st.sidebar.text_input("Topic name for this material", value="General")

if uploaded_pdf is not None and st.sidebar.button("✨ Ingest into knowledge base"):
    temp_path = f"data/{uploaded_pdf.name}"
    os.makedirs("data", exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_pdf.getbuffer())
    n_chunks = rag_engine.ingest_pdf(temp_path, class_level, subject, topic_for_upload)
    st.sidebar.success(f"🎉 Ingested {n_chunks} chunks for Class {class_level} {subject} - {topic_for_upload}")

# ---------- Main tabs ----------
tab1, tab2, tab3 = st.tabs(["💬 Ask the Tutor", "📝 Quiz Me", "🏆 My Progress"])

# ---- TAB 1: Chat ----
with tab1:
    emoji = SUBJECT_EMOJI.get(subject, "📚")
    st.markdown(f"### {emoji} Hey {student_name}! Ask your Class {class_level} {subject} tutor anything!")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        avatar = "🧒" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.write(msg["content"])

    question = st.chat_input("Type your question here... 😊")

    if question:
        # Safety check first
        is_safe, reason = llm_utils.moderate_input(question)

        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="🧒"):
            st.write(question)

        if not is_safe:
            answer = f"⚠️ {reason}\n\nPlease ask a study-related question."
            source = "safety-filter"
        else:
            context_chunks = rag_engine.retrieve_context(question, class_level, subject)
            answer, source = llm_utils.ask_tutor(question, context_chunks, class_level, subject, groq_client)
            db.log_question(student_name, class_level, subject, question)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant", avatar="🤖"):
            st.write(answer)
            st.caption(f"✨ Answered by: {source}")

# ---- TAB 2: Quiz (Agentic feature) ----
with tab2:
    st.markdown("### 🧠 Autonomous Quiz Time!")
    st.write("🤖 The AI will whip up a quiz based on your class, subject, and topic — just for you!")

    quiz_topic = st.text_input("📌 Topic to be quizzed on", value=topic_for_upload)
    num_q = st.slider("🔢 Number of questions", 3, 10, 5)

    if st.button("🎲 Generate Quiz"):
        context_chunks = rag_engine.retrieve_context(quiz_topic, class_level, subject, n_results=6)
        with st.spinner("🪄 Cooking up your quiz..."):
            raw_quiz = llm_utils.generate_quiz(quiz_topic, class_level, subject, context_chunks, num_q)
        try:
            quiz_data = json.loads(raw_quiz)
            st.session_state.current_quiz = quiz_data
            st.session_state.quiz_topic = quiz_topic
        except json.JSONDecodeError:
            st.error("😕 Could not parse quiz. Try again.")
            st.text(raw_quiz)

    if "current_quiz" in st.session_state:
        answers = {}
        with st.form("quiz_form"):
            for i, q in enumerate(st.session_state.current_quiz):
                st.markdown(f"**🙋 Q{i+1}. {q['question']}**")
                answers[i] = st.radio("Select answer:", q["options"], key=f"q_{i}", label_visibility="collapsed")
            submitted = st.form_submit_button("✅ Submit Quiz")

        if submitted:
            score = 0
            for i, q in enumerate(st.session_state.current_quiz):
                if answers[i].strip().startswith(q["correct_answer"].strip()[0]) or answers[i] == q["correct_answer"]:
                    score += 1
            total = len(st.session_state.current_quiz)
            percentage = score / total

            if percentage == 1:
                st.balloons()
                st.success(f"🏆 PERFECT SCORE! {score}/{total} — You're a superstar! 🌟")
            elif percentage >= 0.7:
                st.balloons()
                st.success(f"🎉 Great job! {score}/{total} — Keep it up! 💪")
            elif percentage >= 0.4:
                st.info(f"👍 Score: {score}/{total} — Good try, a little more practice! 📖")
            else:
                st.warning(f"🌱 Score: {score}/{total} — Don't worry, let's learn together! Ask the tutor for help. 🤗")

            db.log_quiz_result(student_name, class_level, subject, st.session_state.quiz_topic, score, total)

# ---- TAB 3: Progress ----
with tab3:
    st.markdown(f"### 🏆 {student_name}'s Progress Journey")
    progress = db.get_student_progress(student_name)

    st.markdown("#### 💬 Questions asked per subject")
    if progress["questions_per_subject"]:
        cols = st.columns(min(len(progress["questions_per_subject"]), 4))
        for i, (subj, count) in enumerate(progress["questions_per_subject"]):
            emoji = SUBJECT_EMOJI.get(subj, "📘")
            with cols[i % len(cols)]:
                st.metric(f"{emoji} {subj}", f"{count} 💬")
    else:
        st.info("🌱 No questions asked yet. Go say hi to your tutor!")

    st.markdown("#### 📝 Quiz history")
    if progress["quiz_history"]:
        for subj, topic, score, total, ts in progress["quiz_history"]:
            pct = score / total if total else 0
            badge = "🥇" if pct == 1 else "🥈" if pct >= 0.7 else "🥉" if pct >= 0.4 else "🌱"
            st.write(f"{badge} [{ts[:16]}] **{subj}** - {topic}: **{score}/{total}**")
    else:
        st.info("🌱 No quizzes taken yet. Try one in the Quiz Me tab!")
