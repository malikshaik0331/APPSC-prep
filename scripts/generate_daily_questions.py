import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
SUPABASE_URL = os.environ["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()

# Weekday rotation aligned to your 8:45 PM APPSC Group 2 Prelims schedule (IST)
IST = timezone(timedelta(hours=5, minutes=30))
ROTATION = {
    0: ("Geography", "Indian and Andhra Pradesh Geography, rivers, monsoons, soils, minerals, and demographics"),
    1: ("Modern Indian History", "Modern Indian History (1857-1947), social reform movements, and freedom struggle in Andhra"),
    2: ("Current Affairs", "Andhra Pradesh state schemes, PIB national highlights, Economy, Polity, and Science & Technology"),
    3: ("Indian Society", "Indian Society structure, constitutional provisions, welfare schemes, and social issues"),
    4: ("Ancient History", "Ancient Indian History, Indus Valley, Vedic age, Mauryas, Guptas, Satavahanas, and Ikshvakus"),
    5: ("AP History", "Social and Cultural History of Andhra Pradesh: Satavahanas, Eastern Chalukyas, Kakatiyas, and Vijayanagara"),
    6: ("AP History", "Mixed APPSC Group 2 Prelims high-yield revision across AP History, Polity, and Economy"),
}


def fetch_questions_from_gemini(subject: str, focus: str, count: int = 30) -> list[dict]:
    prompt = f"""Generate {count} original, high-yield APPSC Group 2 Prelims multiple-choice questions on "{subject}" ({focus}).
Follow APPSC Group 2 standard: include a mix of direct factual, statement-based ("Consider the following statements..."), and chronological/matching questions.

Return ONLY a valid JSON array of {count} objects. Each object must have these exact keys:
- "subject": "{subject}"
- "topic": short specific sub-topic string
- "difficulty": "Easy", "Moderate", or "Hard"
- "question_text": full question text
- "option_a": string
- "option_b": string
- "option_c": string
- "option_d": string
- "correct_option": "A", "B", "C", or "D"
- "explanation": concise 1-2 sentence explanation citing relevant facts, articles, or dates
- "source": standard reference (e.g., "NCERT", "Telugu Akademi", "Bipan Chandra", "PIB / AP Govt")
"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        print(f"Gemini API HTTP {err.code} response: {body}")
        raise

    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    questions = json.loads(raw_text)

    cleaned = []
    for q in questions:
        correct = str(q.get("correct_option", "A")).strip().upper()[:1]
        if correct not in {"A", "B", "C", "D"}:
            correct = "A"
        diff = str(q.get("difficulty", "Moderate")).strip().title()
        if diff not in {"Easy", "Moderate", "Hard"}:
            diff = "Moderate"
        cleaned.append(
            {
                "subject": subject,
                "topic": str(q.get("topic", subject))[:120],
                "difficulty": diff,
                "question_text": str(q["question_text"]),
                "option_a": str(q["option_a"]),
                "option_b": str(q["option_b"]),
                "option_c": str(q["option_c"]),
                "option_d": str(q["option_d"]),
                "correct_option": correct,
                "explanation": str(q.get("explanation", "")),
                "source": str(q.get("source", "AI Daily Mock")),
            }
        )
    return cleaned


def insert_into_supabase(questions: list[dict]) -> None:
    url = f"{SUPABASE_URL}/rest/v1/questions"
    req = urllib.request.Request(
        url,
        data=json.dumps(questions).encode("utf-8"),
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status not in (200, 201):
                raise RuntimeError(f"Supabase insert returned HTTP {resp.status}")
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        print(f"Supabase HTTP {err.code} response: {body}")
        raise


def main() -> None:
    now_ist = datetime.now(IST)
    subject, focus = ROTATION[now_ist.weekday()]
    print(f"[{now_ist.isoformat()}] Generating 30 questions for: {subject} (key len={len(GEMINI_API_KEY)})")
    questions = fetch_questions_from_gemini(subject, focus, count=30)
    insert_into_supabase(questions)
    print(f"Successfully inserted {len(questions)} {subject} questions into Supabase.")


if __name__ == "__main__":
    main()
