"""
llm_utils.py - Wraps calls to both LLMs (requirement: at least 2 LLM integrations)
and implements a safety/moderation layer (requirement: safety guardrails).

- Groq (Llama 3.1, free tier) = primary tutoring answers
- Gemini = quiz generation, safety check, + fallback if Groq fails

Groq is used via the OpenAI-compatible SDK (same `openai` package, pointed at
Groq's endpoint), so no OpenAI account or billing is required.
"""

from openai import OpenAI
import google.generativeai as genai

BLOCKED_KEYWORDS = [
    "bomb", "suicide", "self harm", "kill myself", "weapon", "drugs",
    "hack password", "cheat in exam using ai without teacher knowing"
]

GROQ_MODEL = "llama-3.1-8b-instant"


def moderate_input(text, gemini_configured=True):
    """
    Two-layer safety check:
    1. Simple keyword filter (fast, catches obvious cases)
    2. Gemini-based content classification (catches nuanced harmful content,
       reuses the second LLM instead of needing a separate paid moderation API)
    Returns (is_safe: bool, reason: str)
    """
    lower_text = text.lower()
    for word in BLOCKED_KEYWORDS:
        if word in lower_text:
            return False, f"Question blocked: contains restricted term related to '{word}'."

    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        check_prompt = (
            "Is the following message from a school student a safe, study-related "
            "question, or does it request harmful/inappropriate content (violence, "
            "self-harm, weapons, drugs, hacking, etc.)? "
            "Reply with exactly one word: SAFE or UNSAFE.\n\n"
            f"Message: {text}"
        )
        response = model.generate_content(check_prompt)
        verdict = response.text.strip().upper()
        if "UNSAFE" in verdict:
            return False, "Question blocked by AI safety filter as potentially harmful."
    except Exception:
        # If the check itself fails, fall back to allowing (keyword filter already ran)
        pass

    return True, ""


def get_groq_client(api_key):
    """Groq exposes an OpenAI-compatible API, so we reuse the openai SDK, just
    pointed at Groq's base_url. This is our first LLM integration and is free."""
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def configure_gemini(api_key):
    genai.configure(api_key=api_key)


def ask_tutor(question, context_chunks, class_level, subject, groq_client):
    """
    Main tutoring answer, using Groq's Llama 3.1 with retrieved RAG context.
    """
    context_text = "\n\n".join(context_chunks) if context_chunks else "No specific textbook content found; answer from general knowledge."

    system_prompt = f"""You are a patient, encouraging tutor for a Class {class_level} student studying {subject}.
Explain concepts simply, using age-appropriate language and examples.

IMPORTANT LANGUAGE RULE: Always reply in the SAME language/style the student used in their question.
- If they write in Hinglish (Hindi mixed with English, in Roman/English script), reply in Hinglish the same way.
- If they write in Hindi (Devanagari script), reply in Hindi.
- If they write in English, reply in English.
Match their language naturally, like a friendly Indian tutor would.

Use the CONTEXT below (from the student's textbook) when relevant. If the context doesn't cover the question, say so and answer from general knowledge, but keep it appropriate for their class level.
Keep answers focused and not too long. End with a short follow-up question to check understanding (in the same language as your answer).

CONTEXT:
{context_text}
"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.4,
            max_tokens=500
        )
        return response.choices[0].message.content, "groq (llama-3.1)"
    except Exception as e:
        # Fallback to Gemini if Groq fails (this also satisfies "2 LLM integrations" working together)
        try:
            model = genai.GenerativeModel("gemini-flash-latest")
            full_prompt = system_prompt + "\n\nStudent question: " + question
            gem_response = model.generate_content(full_prompt)
            return gem_response.text, "gemini (fallback)"
        except Exception as e2:
            return f"Sorry, both AI services are unavailable right now. Error: {e2}", "error"


def generate_quiz(topic, class_level, subject, context_chunks, num_questions=5):
    """
    AGENTIC FEATURE: The system autonomously decides quiz questions based on
    topic content already studied, without the user having to write the quiz themselves.
    Uses Gemini (second LLM) to generate structured quiz JSON.
    """
    context_text = "\n\n".join(context_chunks) if context_chunks else ""

    prompt = f"""Create a {num_questions}-question multiple choice quiz for a Class {class_level} student on the topic "{topic}" in {subject}.
Base questions on this content if relevant:
{context_text}

Respond ONLY in this exact JSON format, no extra text:
[
  {{"question": "...", "options": ["A", "B", "C", "D"], "correct_answer": "A"}}
]
"""

    model = genai.GenerativeModel("gemini-flash-latest")
    response = model.generate_content(prompt)

    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return raw
