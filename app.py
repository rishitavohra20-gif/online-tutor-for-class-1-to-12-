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

st.set_page_config(page_title="AI Tutor - Class 1 to 12", page_icon="📚", layout="wide")
db.init_db()

CLASS_OPTIONS = [str(i) for i in range(1, 13)]
SUBJECT_OPTIONS = [
    "Mathematics", "Science", "English", "Hindi", "Social Science",
    "Physics", "Chemistry", "Biology", "Computer Science", "History", "Geography"
]

# ---------- Sidebar: Setup ----------
st.sidebar.title("📚 AI Tutor Setup")

groq_key = st.sidebar.text_input("Groq API Key (free at console.groq.com)", type="password", value=os.getenv("GROQ_API_KEY", ""))
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))

student_name = st.sidebar.text_input("Student Name", value="Student1")
class_level = st.sidebar.selectbox("Class", CLASS_OPTIONS, index=9)
subject = st.sidebar.selectbox("Subject", SUBJECT_OPTIONS)

if not groq_key or not gemini_key:
    st.sidebar.warning("Enter both API keys to use the tutor.")
    st.stop()

groq_client = llm_utils.get_groq_client(groq_key)
llm_utils.configure_gemini(gemini_key)

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Add Study Material (optional)")
uploaded_pdf = st.sidebar.file_uploader("Upload textbook/notes PDF", type=["pdf"])
topic_for_upload = st.sidebar.text_input("Topic name for this material", value="General")

if uploaded_pdf is not None and st.sidebar.button("Ingest into knowledge base"):
    temp_path = f"data/{uploaded_pdf.name}"
    os.makedirs("data", exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_pdf.getbuffer())
    n_chunks = rag_engine.ingest_pdf(temp_path, class_level, subject, topic_for_upload)
    st.sidebar.success(f"Ingested {n_chunks} chunks for Class {class_level} {subject} - {topic_for_upload}")

# ---------- Main tabs ----------
tab1, tab2, tab3 = st.tabs(["💬 Ask the Tutor", "📝 Quiz Me", "📊 My Progress"])

# ---- TAB 1: Chat ----
with tab1:
    st.header(f"Ask your Class {class_level} {subject} tutor")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("Type your question here...")

    if question:
        # Safety check first
        is_safe, reason = llm_utils.moderate_input(question)

        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        if not is_safe:
            answer = f"⚠️ {reason}\n\nPlease ask a study-related question."
            source = "safety-filter"
        else:
            context_chunks = rag_engine.retrieve_context(question, class_level, subject)
            answer, source = llm_utils.ask_tutor(question, context_chunks, class_level, subject, groq_client)
            db.log_question(student_name, class_level, subject, question)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)
            st.caption(f"Answered by: {source}")

# ---- TAB 2: Quiz (Agentic feature) ----
with tab2:
    st.header("Autonomous Quiz Generator")
    st.write("The AI will generate a quiz based on your class, subject, and topic — no need to write questions yourself.")

    quiz_topic = st.text_input("Topic to be quizzed on", value=topic_for_upload)
    num_q = st.slider("Number of questions", 3, 10, 5)

    if st.button("Generate Quiz"):
        context_chunks = rag_engine.retrieve_context(quiz_topic, class_level, subject, n_results=6)
        with st.spinner("Generating quiz..."):
            raw_quiz = llm_utils.generate_quiz(quiz_topic, class_level, subject, context_chunks, num_q)
        try:
            quiz_data = json.loads(raw_quiz)
            st.session_state.current_quiz = quiz_data
            st.session_state.quiz_topic = quiz_topic
        except json.JSONDecodeError:
            st.error("Could not parse quiz. Try again.")
            st.text(raw_quiz)

    if "current_quiz" in st.session_state:
        answers = {}
        with st.form("quiz_form"):
            for i, q in enumerate(st.session_state.current_quiz):
                st.write(f"**Q{i+1}. {q['question']}**")
                answers[i] = st.radio("Select answer:", q["options"], key=f"q_{i}", label_visibility="collapsed")
            submitted = st.form_submit_button("Submit Quiz")

        if submitted:
            score = 0
            for i, q in enumerate(st.session_state.current_quiz):
                if answers[i].strip().startswith(q["correct_answer"].strip()[0]) or answers[i] == q["correct_answer"]:
                    score += 1
            total = len(st.session_state.current_quiz)
            st.success(f"Score: {score}/{total}")
            db.log_quiz_result(student_name, class_level, subject, st.session_state.quiz_topic, score, total)

# ---- TAB 3: Progress ----
with tab3:
    st.header(f"Progress for {student_name}")
    progress = db.get_student_progress(student_name)

    st.subheader("Questions asked per subject")
    if progress["questions_per_subject"]:
        for subj, count in progress["questions_per_subject"]:
            st.write(f"- {subj}: {count} questions")
    else:
        st.write("No questions asked yet.")

    st.subheader("Quiz history")
    if progress["quiz_history"]:
        for subj, topic, score, total, ts in progress["quiz_history"]:
            st.write(f"- [{ts[:16]}] {subj} - {topic}: {score}/{total}")
    else:
        st.write("No quizzes taken yet.")
