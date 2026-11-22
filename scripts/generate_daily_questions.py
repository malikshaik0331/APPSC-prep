import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
SUPABASE_URL = os.environ["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()
TARGET_SUBJECT = os.environ.get("TARGET_SUBJECT", "Auto (Calendar Schedule)").strip()

IST = timezone(timedelta(hours=5, minutes=30))
PRIMARY_MODEL = "gemini-3.8-flash"

# Individual Subject Focus Definitions (Static Prelims & Mains strictly separated; Current Affairs handled via personal notes)
SUBJECT_FOCUS = {
    # --- STATIC PRELIMS SUBJECTS ---
    "Ancient Indian History": "Indus Valley, Vedic age, Buddhism & Jainism, Mauryas, Guptas, Harshavardhana, art, architecture, and inscriptions",
    "Medieval Indian History (Basic)": "BASIC foundational level only (NCERT/introductory): Delhi Sultanate chronology, major Mughal rulers (Babur to Aurangzeb), Bhakti & Sufi saints, and Vijayanagara/Bahmani basics—no obscure minutiae",
    "Modern Indian History": "1857 Revolt, socio-religious reforms, INC phases, Gandhian movements, revolutionary nationalism, Constitutional Acts (1773-1947), and freedom struggle in Andhra",
    "Indian Geography": "Physiography, drainage systems, Indian monsoon, soils, natural vegetation, agriculture, minerals, energy resources, and demographics",
    "AP Geography": "Andhra Pradesh physiography, Godavari/Krishna/Penna river basins, soils, cropping patterns, irrigation projects, minerals, ports, and 26-district geography",
    "Indian Society": "Family, marriage, kinship, caste & tribe dynamics, women/SC/ST/OBC constitutional safeguards, secularism, regionalism, and welfare policies",
    # --- MAINS SUBJECTS (Individual Subject-Wise Tests Only - Never mixed into Prelims) ---
    "AP History": "Satavahanas, Ikshvakus, Eastern Chalukyas of Vengi, Kakatiyas, Reddis, Vijayanagara Empire, Qutb Shahis, and Modern Andhra / Andhra Movement",
    "Polity": "Preamble, Fundamental Rights, DPSP, Fundamental Duties, Parliament & State Legislature, Judiciary, Federalism, Panchayati Raj (73rd/74th), and Constitutional/Statutory bodies",
    "Indian Economy": "National income, RBI & monetary policy, fiscal policy & Union Budget, inflation, banking reforms, WTO/external sector, NITI Aayog, and flagship schemes",
    "AP Economy": "AP Socio-Economic Survey, GSDP & sectoral composition, AP state budget, Navaratnalu & welfare schemes, industrial corridors, and agriculture/MSMEs in AP",
    "Science and Technology": "ISRO missions, DRDO defence tech, biotechnology & vaccines, AI/quantum computing, nuclear energy, ICT/digital public infrastructure, and space/cyber policy",
    "Environment and Ecology": "Biodiversity hotspots, protected areas (AP & India), Wildlife Protection Act, climate change treaties (COP/Paris), EIA, pollution control, and Ramsar wetlands",
    # --- COMBINED STATIC PRELIMS FULL-LENGTH MOCK ---
    "Prelims Full-Length Mock": (
        "Full-length APPSC Group 2 Prelims mock covering ONLY static Prelims subjects: "
        "(1) Ancient Indian History, (2) BASIC-level Medieval Indian History only, "
        "(3) Modern Indian History, (4) Geography of India & Andhra Pradesh, and "
        "(5) Indian Society. "
        "DO NOT include Current Affairs (handled separately) and DO NOT include Mains-only subjects (no AP History, Polity, Economy, S&T, or Environment)."
    ),
}

# Calendar-Synced Static Prelims Weekday Rotation (through Dec 14, 2026)
# Mon: AP Geography | Tue: Ancient History | Wed: Indian Geography | Thu: Indian Society | Fri: Modern History
CALENDAR_WEEKDAY_MAP = {
    0: "AP Geography",
    1: "Ancient Indian History",
    2: "Indian Geography",
    3: "Indian Society",
    4: "Modern Indian History",
    5: "Prelims Full-Length Mock",
    6: "Prelims Full-Length Mock",
}


def resolve_subject_for_today(today_ist: date) -> str:
    if TARGET_SUBJECT in SUBJECT_FOCUS:
        return TARGET_SUBJECT
    if today_ist >= date(2026, 12, 15):
        return "Prelims Full-Length Mock"
    return CALENDAR_WEEKDAY_MAP[today_ist.weekday()]


def discover_backup_models() -> list[str]:
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    req = urllib.request.Request(
        url,
        headers={"x-goog-api-key": GEMINI_API_KEY, "User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    models = []
    for m in data.get("models", []):
        name = m.get("name", "").replace("models/", "")
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods and name != PRIMARY_MODEL and ("flash" in name or "pro" in name):
            if "tts" not in name and "image" not in name and "audio" not in name:
                models.append(name)
    return sorted(models, reverse=True)


def call_gemini_model(model: str, prompt: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
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

    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_questions_from_gemini(subject: str, focus: str, count: int = 10, batch_num: int = 1, total_batches: int = 10) -> list[dict]:
    basic_note = ""
    if "Medieval" in subject or subject == "Prelims Full-Length Mock":
        basic_note = "- IMPORTANT: For Medieval Indian History questions, keep them strictly at a BASIC foundational level (major dynasties, rulers, monuments, Bhakti/Sufi basics).\n"

    prompt = f"""Generate {count} analytical, APPSC Group 2-standard multiple-choice questions on "{subject}" ({focus}) — Batch {batch_num} of {total_batches}.

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
- "source": standard reference (e.g., "NCERT", "Bipan Chandra", "Telugu Akademi", "Ram Ahuja")
"""

    data = None
    try:
        data = call_gemini_model(PRIMARY_MODEL, prompt)
    except Exception as primary_err:
        print(f"Primary model {PRIMARY_MODEL} unavailable ({primary_err}); discovering live backup models...")
        for backup in discover_backup_models():
            try:
                print(f"Trying backup model: {backup}")
                data = call_gemini_model(backup, prompt)
                print(f"Succeeded with backup model: {backup}")
                break
            except Exception as err:
                print(f"Backup model {backup} failed: {err}")
                continue
        if data is None:
            raise RuntimeError(f"Primary and all backup models failed. Primary error: {primary_err}")

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

    total_batches = 10
    batch_size = 10
    total_inserted = 0

    print(f"[{now_ist.isoformat()}] Generating 100 analytical questions ({total_batches}x{batch_size}) for: {subject}")
    for batch in range(1, total_batches + 1):
        for attempt in (1, 2):
            try:
                batch_q = fetch_questions_from_gemini(
                    subject, focus, count=batch_size, batch_num=batch, total_batches=total_batches
                )
                insert_into_supabase(batch_q)
                total_inserted += len(batch_q)
                print(f"Batch {batch}/{total_batches}: inserted {len(batch_q)} questions (total={total_inserted}).")
                break
            except Exception as exc:
                print(f"Batch {batch} attempt {attempt} failed: {exc}")
                if attempt == 2:
                    raise
                time.sleep(15)
    print(f"Successfully inserted {total_inserted} {subject} questions into Supabase.")


if __name__ == "__main__":
    main()
