import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
SUPABASE_URL = os.environ["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()
TARGET_SUBJECT = os.environ.get("TARGET_SUBJECT", "Auto (Calendar Schedule)").strip()

IST = timezone(timedelta(hours=5, minutes=30))

# Individual Subject Focus Definitions (Prelims & Mains strictly separated)
SUBJECT_FOCUS = {
    # --- PRELIMS SUBJECTS ---
    "Ancient Indian History": "Indus Valley, Vedic age, Buddhism & Jainism, Mauryas, Guptas, Harshavardhana, art, architecture, and inscriptions",
    "Medieval Indian History (Basic)": "BASIC foundational level only (NCERT/introductory): Delhi Sultanate chronology, major Mughal rulers (Babur to Aurangzeb), Bhakti & Sufi saints, and Vijayanagara/Bahmani basics—no obscure minutiae",
    "Modern Indian History": "1857 Revolt, socio-religious reforms, INC phases, Gandhian movements, revolutionary nationalism, Constitutional Acts (1773-1947), and freedom struggle in Andhra",
    "Indian Geography": "Physiography, drainage systems, Indian monsoon, soils, natural vegetation, agriculture, minerals, energy resources, and demographics",
    "AP Geography": "Andhra Pradesh physiography, Godavari/Krishna/Penna river basins, soils, cropping patterns, irrigation projects, minerals, ports, and 26-district geography",
    "Indian Society": "Family, marriage, kinship, caste & tribe dynamics, women/SC/ST/OBC constitutional safeguards, secularism, regionalism, and welfare policies",
    "Current Affairs (Aug-Dec 2026)": "National, International, and Andhra Pradesh current affairs from August 2026 to December 2026: schemes, summits, indices, awards, sports, and appointments",
    # --- MAINS SUBJECTS (Individual Subject-Wise Tests Only - Never mixed into Prelims) ---
    "AP History": "Satavahanas, Ikshvakus, Eastern Chalukyas of Vengi, Kakatiyas, Reddis, Vijayanagara Empire, Qutb Shahis, and Modern Andhra / Andhra Movement",
    "Polity": "Preamble, Fundamental Rights, DPSP, Fundamental Duties, Parliament & State Legislature, Judiciary, Federalism, Panchayati Raj (73rd/74th), and Constitutional/Statutory bodies",
    "Indian Economy": "National income, RBI & monetary policy, fiscal policy & Union Budget, inflation, banking reforms, WTO/external sector, NITI Aayog, and flagship schemes",
    "AP Economy": "AP Socio-Economic Survey, GSDP & sectoral composition, AP state budget, Navaratnalu & welfare schemes, industrial corridors, and agriculture/MSMEs in AP",
    "Science and Technology": "ISRO missions, DRDO defence tech, biotechnology & vaccines, AI/quantum computing, nuclear energy, ICT/digital public infrastructure, and space/cyber policy",
    "Environment and Ecology": "Biodiversity hotspots, protected areas (AP & India), Wildlife Protection Act, climate change treaties (COP/Paris), EIA, pollution control, and Ramsar wetlands",
    # --- COMBINED PRELIMS FULL-LENGTH MOCK ---
    "Prelims Full-Length Mock": (
        "Full-length APPSC Group 2 Prelims mock covering ONLY Prelims subjects: "
        "(1) Ancient Indian History, (2) BASIC-level Medieval Indian History only, "
        "(3) Modern Indian History, (4) Geography of India & Andhra Pradesh, "
        "(5) Indian Society, and (6) Current Affairs from August 2026 to December 2026. "
        "DO NOT include Mains-only subjects (no AP History, Polity, Economy, S&T, or Environment)."
    ),
}

# Calendar-Synced Weekday Rotation (through Dec 14, 2026)
# Mon: Current Affairs | Tue: Ancient History | Wed: Geography | Thu: Indian Society | Fri: Modern History
CALENDAR_WEEKDAY_MAP = {
    0: "Current Affairs (Aug-Dec 2026)",
    1: "Ancient Indian History",
    2: "Indian Geography",
    3: "Indian Society",
    4: "Modern Indian History",
    5: "Prelims Full-Length Mock",  # Weekend consolidation / mixed Prelims
    6: "Prelims Full-Length Mock",
}


def resolve_subject_for_today(today_ist: date) -> str:
    if TARGET_SUBJECT in SUBJECT_FOCUS:
        return TARGET_SUBJECT
    # On Dec 15 (Grand Prelims Mock) and Dec 16 - Dec 31: Full-Length Prelims Mock ONLY
    if today_ist >= date(2026, 12, 15):
        return "Prelims Full-Length Mock"
    # Through Dec 14: follow exact Google Calendar weekday rotation
    # Alternate Wednesday between Indian Geography and AP Geography
    if today_ist.weekday() == 2 and (today_ist.isocalendar()[1] % 2 == 0):
        return "AP Geography"
    return CALENDAR_WEEKDAY_MAP[today_ist.weekday()]


def fetch_questions_from_gemini(subject: str, focus: str, count: int = 25, batch_num: int = 1) -> list[dict]:
    basic_note = ""
    if "Medieval" in subject or subject == "Prelims Full-Length Mock":
        basic_note = "- IMPORTANT: For Medieval Indian History questions, keep them strictly at a BASIC foundational level (major dynasties, rulers, monuments, Bhakti/Sufi basics).\n"

    prompt = f"""Generate {count} analytical, APPSC Group 2-standard multiple-choice questions on "{subject}" ({focus}) — Batch {batch_num} of 4.

STRICT QUALITY RULES:
- At least 75% MUST be multi-statement or analytical questions (e.g., "Consider the following statements: 1... 2... 3... Which of the statements given above is/are correct?", "How many of the above pairs are correctly matched?", "Assertion (A) and Reason (R)", "Arrange in chronological order", or "Match List-I with List-II").
{basic_note}- Avoid simple one-line recall questions (except for basic Medieval India). Test conceptual linkages, exceptions, chronology, and cause-and-effect.
- Format multi-statement questions with clean line breaks (\\n) between numbered statements so they are easy to read on screen.

Return ONLY a valid JSON array of {count} objects. Each object must have these exact keys:
- "subject": "{subject}"
- "topic": short specific sub-topic string (for Full-Length Mock, put the Prelims subject name here, e.g. "Modern History", "AP Geography", "Indian Society")
- "difficulty": "Moderate" or "Hard" (use "Easy" for basic Medieval India)
- "question_text": full question text with \\n line breaks
- "option_a": string
- "option_b": string
- "option_c": string
- "option_d": string
- "correct_option": "A", "B", "C", or "D"
- "explanation": concise 2-sentence explanation clarifying why each statement is right or wrong
- "source": standard reference (e.g., "NCERT", "Bipan Chandra", "Telugu Akademi", "PIB / AP Govt")
"""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
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
        with urllib.request.urlopen(req, timeout=300) as resp:
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
                "source": str(q.get("source", "Standard Reference")),
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
    subject = resolve_subject_for_today(now_ist.date())
    focus = SUBJECT_FOCUS[subject]

    print(f"[{now_ist.isoformat()}] Generating 100 analytical questions (4x25) for: {subject}")
    all_questions = []
    for batch in range(1, 5):
        batch_q = fetch_questions_from_gemini(subject, focus, count=25, batch_num=batch)
        print(f"Batch {batch}/4: generated {len(batch_q)} questions.")
        all_questions.extend(batch_q)
    insert_into_supabase(all_questions)
    print(f"Successfully inserted {len(all_questions)} {subject} questions into Supabase.")


if __name__ == "__main__":
    main()
