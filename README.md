# AI Tutor — Class 1 to 12, All Subjects

An end-to-end AI-powered tutoring application built as a capstone project. One system
serves every class (1-12) and subject by tagging retrieved content with class + subject
metadata, rather than building a separate tutor per subject.

## Features

- **2 LLM integrations**: Groq (Llama 3.1, free tier, primary tutoring answers) + Google
  Gemini (quiz generation, safety check, and automatic fallback if Groq fails)
- **RAG pipeline**: Upload textbook/notes PDFs → chunked → embedded (locally, free) →
  stored in ChromaDB, filtered per class/subject/topic at query time
- **Agentic feature**: Autonomous quiz generation — the system decides quiz questions
  based on studied content without the student writing them
- **Safety guardrails**: Keyword filter + Gemini-based content classification on every
  question before it reaches the tutor LLM
- **Progress tracking**: SQLite database logs questions asked and quiz scores per student
- **Web interface**: Streamlit app with chat, quiz, and progress tabs
- **Evaluation report**: `evaluate.py` runs test cases and outputs metrics

## Project Structure

```
ai_tutor/
├── app.py              # Main Streamlit application
├── rag_engine.py        # PDF ingestion, chunking, embedding, retrieval
├── llm_utils.py          # OpenAI + Gemini calls, safety moderation, quiz generation
├── db.py                 # SQLite progress tracking
├── evaluate.py            # Test cases + evaluation report generator
├── requirements.txt
├── .env.example
└── data/                  # Uploaded PDFs get saved here
```

## Setup Instructions

1. **Clone the repo and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your API keys.** Copy `.env.example` to `.env` and fill in:
   ```
   GROQ_API_KEY=gsk_...
   GEMINI_API_KEY=AI...
   ```
   Get a free Groq key at https://console.groq.com/keys (no card required)
   Get a Gemini key at https://aistudio.google.com/apikey (no card required)

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```
   Or enter your API keys directly in the sidebar if you don't want a `.env` file.

4. **Add study material:** In the sidebar, select a class + subject, upload a PDF
   (e.g. an NCERT chapter), give it a topic name, and click "Ingest into knowledge base."
   The chatbot will now use that content when answering questions for that class/subject.

5. **Run the evaluation:**
   ```bash
   python evaluate.py
   ```
   This produces `evaluation_report.md` with test case results and metrics.

## Deployment

Deploy for free on [Streamlit Community Cloud](https://streamlit.io/cloud):
1. Push this repo to GitHub
2. Connect the repo on share.streamlit.io
3. Add `OPENAI_API_KEY` and `GEMINI_API_KEY` as secrets in the Streamlit Cloud dashboard
4. Deploy — you'll get a public URL to share/demo

## Documented Prompts

**Tutor system prompt** (in `llm_utils.ask_tutor`):
> "You are a patient, encouraging tutor for a Class {class_level} student studying
> {subject}. Explain concepts simply, using age-appropriate language and examples.
> Use the CONTEXT below (from the student's textbook) when relevant..."

**Quiz generation prompt** (in `llm_utils.generate_quiz`):
> "Create a {num_questions}-question multiple choice quiz for a Class {class_level}
> student on the topic '{topic}' in {subject}. Base questions on this content if
> relevant... Respond ONLY in JSON format..."

## Safety Design

Every question passes through two checks before reaching the LLM:
1. A keyword blocklist for obviously unsafe terms
2. OpenAI's moderation endpoint for nuanced harmful content detection

If either check flags the input, the question is never sent to the tutor LLM and
the student receives a safe redirect message instead.

## Known Limitations / Future Work

- Currently requires manual PDF upload per class/subject; could pre-load full NCERT
  syllabus for all classes
- Quiz answer-matching is string-based and could be made more robust
- No user authentication — student name is self-entered
