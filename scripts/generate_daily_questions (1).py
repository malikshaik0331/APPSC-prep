import difflib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
SUPABASE_URL = os.environ["SUPABASE_URL"].strip().rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()
TARGET_SUBJECT = os.environ.get("TARGET_SUBJECT", "Auto (Calendar Schedule)").strip()

IST = timezone(timedelta(hours=5, minutes=30))
PRIMARY_MODEL = "gemini-3.8-flash"

# Strictly aligned to APPSC Group-II Notification No. 37/2026 (Dated 10/11/2026), Annexure-II (Pages 42-46)
# Excludes Current Affairs and Mental Ability as requested.
SUBJECT_BATCH_TOPICS = {
    "Ancient Indian History": [
        "Salient features of Indus Valley Civilization: town planning, economy, trade, script, seals, and religion",
        "Vedic Age: Rigvedic vs Later Vedic polity, economy, social structure, religion, and Vedic literature",
        "Emergence of Buddhism: teachings, Four Noble Truths, Eightfold Path, Buddhist Councils, sects, and literature",
        "Emergence of Jainism: Tirthankaras, doctrines (Anekantavada, Syadvada), councils, sects, and literature",
        "Mauryan Empire: administration, Arthashastra, Ashoka's Dhamma, inscriptions, and socio-economic conditions",
        "Mauryan Empire: art, architecture (pillars, stupas, caves), literature, and causes of decline",
        "Gupta Empire: political achievements, administration, land grants, and socio-economic & religious conditions",
        "Gupta Empire: art, temple architecture, Sanskrit literature, and science/mathematics",
        "Harshavardhana and his Achievements: military campaigns, administration, Kannauj/Prayag assemblies, and Xuanzang's account",
        "Harshavardhana's cultural & literary contributions (Banabhatta, Harsha's plays, Nalanda patronage) & comparative Gupta-Harsha administration",
    ],
    "Medieval Indian History (Basic)": [
        "The Chola Administrative System (basic): central/provincial governance, Kudavolai/village assemblies, and navy",
        "Delhi Sultanate (basic): major dynasties & rulers from Slave to Lodi, Iqta system, and basic administration",
        "Delhi Sultanate (basic): socio-economic and religious conditions, Indo-Islamic art, architecture, and literature",
        "The Mughal Empire (basic): major rulers from Babur to Aurangzeb, Mansabdari & Jagirdari basics, and revenue",
        "The Mughal Empire (basic): socio-economic & religious policies (Sulh-i-kul), art, architecture, and Persian/regional literature",
        "Bhakti Movement (basic): Alvars, Nayanars, Nirguna & Saguna saints (Kabir, Nanak, Mirabai, Chaitanya, Ramananda)",
        "Sufi Movement (basic): Chishti and Suhrawardi silsilas, major saints, khanqahs, and cultural synthesis",
        "Shivaji and the rise of Maratha Empire (basic): Ashtapradhan, Chauth & Sardeshmukhi, and military/fort administration",
        "Advent of Europeans (basic): Portuguese, Dutch, English, and French arrival, early factories, and trade rivalry",
        "Integrated Basic Medieval Revision: Chola, Sultanate, Mughal, Bhakti-Sufi, and Maratha foundational concepts",
    ],
    "Modern Indian History": [
        "1857 Revolt and its Impact: causes, major centres, leaders, suppression, and Government of India Act 1858",
        "Rise and Consolidation of British Power in India: Plassey, Buxar, Subsidiary Alliance, Doctrine of Lapse, and annexations",
        "Changes in Administration, Social and Cultural Spheres under British Rule: Acts (1773-1935), civil services, judiciary, education, press",
        "Social and Religious Reform Movements in the 19th and 20th Century: Brahmo Samaj, Arya Samaj, Satyashodhak, Aligarh, Ramakrishna, and temple entry",
        "Indian National Movement (1885-1915): INC founding, Moderates vs Extremists, Swadeshi & Boycott, Surat Split, Revolutionary Phase I",
        "Indian National Movement (1916-1929): Home Rule, Lucknow Pact, Gandhian Satyagrahas, Non-Cooperation, Swarajists, Simon Commission, Nehru Report",
        "Indian National Movement (1930-1942): Civil Disobedience, Round Table Conferences, 1935 Act, 1937 Elections, August Offer, Cripps Mission",
        "Indian National Movement (1942-1947): Quit India, Subhas Chandra Bose & INA, RIN Mutiny, Cabinet Mission, Mountbatten Plan & key contributors across regions",
        "Post-Independence Consolidation and Reorganization within the country: integration of princely states, Patel, Hyderabad/Junagadh/Kashmir",
        "Post-Independence Reorganization: Linguistic Provinces Commission, JVP, SRC 1953, States Reorganisation Act 1956, and language policy",
    ],
    "Indian Geography": [
        "General & Physical Geography: The Earth in our Solar System, Interior of the Earth, and Major Landforms and their features",
        "Climatology & Oceanography: Structure and Composition of Atmosphere, Weather/Climate, Ocean Water (Tides, Waves, Currents)",
        "India Physical Geography: Major Physiographic features (Himalayas, Northern Plains, Peninsular Plateau, Coastal Plains, Islands)",
        "India Drainage, Climate, Soils & Vegetation: Himalayan & Peninsular rivers, Monsoon, Indian soils, and natural vegetation",
        "Natural Hazards and Disasters in India and their Management (earthquakes, cyclones, floods, droughts, landslides)",
        "Economic Geography of India: Natural resources (minerals & energy) and their distribution across India",
        "Economic Geography of India: Agriculture and Agro-based Activities, cropping patterns, Green Revolution, and irrigation",
        "Economic Geography of India: Distribution of Major Industries, Major Industrial Regions, Transport, Communication, Tourism and Trade",
        "Human Geography of India: Human Development, Demographics, Census patterns, Urbanization and Migration",
        "Human Geography of India: Racial, Tribal, Religious and Linguistic groups across India",
    ],
    "AP Geography": [
        "Andhra Pradesh Physical Geography: Major Physiographic features (Coastal Plains, Eastern Ghats, Rayalaseema plateau)",
        "Andhra Pradesh Climate, Drainage System (Godavari, Krishna, Penna, Vamsadhara, Nagavali), Soils and Vegetation",
        "Natural Hazards and Disasters in Andhra Pradesh (cyclones, coastal erosion, droughts, floods) and their Management",
        "Economic Geography of AP: Natural resources (barytes, limestone, bauxite, mica, uranium, KG Basin gas) and their distribution",
        "Economic Geography of AP: Agriculture and Agro-based Activities, cropping patterns, horticulture, aquaculture, and irrigation projects",
        "Economic Geography of AP: Distribution of Major Industries, Industrial Corridors (VCIC, CBIC), and SEZs",
        "Economic Geography of AP: Transport, Communication, Major/Minor Ports, Tourism and Trade",
        "Human Geography of AP: Human Development indicators, Demographics, Urbanization and Migration trends",
        "Human Geography of AP: Tribal, Religious and Linguistic groups (Agency tracts, PVTGs, 26-district demographic profile)",
        "Integrated AP Physical, Economic & Human Geography synthesis (resource-industry-district linkages)",
    ],
    "Indian Society": [
        "Structure of Indian Society: Family and Marriage (types, functions, changing patterns, legal frameworks)",
        "Structure of Indian Society: Kinship systems (North vs South India), Caste (varna, jati, mobility, Sanskritisation)",
        "Structure of Indian Society: Tribe, Ethnicity, Religion and Women in Indian Society",
        "Social Issues: Casteism, Communalism and Regionalisation in India (causes, manifestations, remedies)",
        "Social Issues: Crime against Women, legal protections, and gender-based violence",
        "Social Issues: Child Abuse and Child Labour (causes, constitutional & statutory safeguards, POCSO/CLPR)",
        "Social Issues: Youth Unrest and Agitation (educational, employment, and socio-political dimensions)",
        "Welfare Mechanism: Public Policies and Welfare Programmes for inclusive social development",
        "Welfare Mechanism: Constitutional and Statutory Provisions for Scheduled Castes (SCs), Scheduled Tribes (STs), and BCs",
        "Welfare Mechanism: Constitutional and Statutory Provisions for Minorities, Women, Disabled (RPwD) and Children",
    ],
    "AP History": [
        "Unit 1: Pre-Historic Cultures, The Satavahanas & The Ikshvakus — Socio-Economic and Religious Conditions, Literature, Art and Architecture",
        "Unit 1: The Vishnukundins, The Eastern Chalukyas of Vengi, and Andhra Cholas — Society, Religion, Telugu Language, Art and Architecture",
        "Unit 2: Major and Minor dynasties of Andhradesa (11th to 16th centuries A.D.) — Kakatiyas, Reddis, Velamas, Vijayanagara polity",
        "Unit 2: Socio-Religious & Economic Conditions, Growth of Telugu Language & Literature, Art and Architecture in Andhradesa (11th-16th c.)",
        "Unit 3: Advent of Europeans, Trade centers, Andhra under the Company, 1857 Revolt & its Impact on Andhra, Establishment of British Rule",
        "Unit 3: Socio-Cultural Awakening, Justice Party/Self-Respect Movement, Growth of Nationalist Movement in Andhra (1885-1947)",
        "Unit 3: Role of Socialists, Communists, Anti-Zamindari & Kisan Movements, Nationalist Poetry, Revolutionary Literature, Nataka Samasthalu & Women",
        "Unit 4: Origin and Growth of Andhra Movement, Role of Andhra Mahasabhas, Prominent Leaders, Events leading to Andhra State 1953",
        "Unit 4: Role of Press & News Papers in Andhra Movement, Role of Library Movement, and Folk and Tribal Culture",
        "Unit 5: Formation of AP State — Visalandhra Mahasabha, SRC Recommendations, Gentlemen Agreement, and Social & Cultural Events (1956-2014)",
    ],
    "Polity": [
        "Unit 6: Nature of Indian Constitution, Constitutional Development, Salient features, and Preamble",
        "Unit 6: Fundamental Rights, Directive Principles of State Policy and their relationship, Fundamental Duties, Amendment & Basic Structure",
        "Unit 7: Structure & Functions of Indian Government — Legislative (Unicameral, Bicameral) & Executive (Parliamentary system)",
        "Unit 7: Judiciary — Supreme Court, High Courts, Judicial Review, and Judicial Activism",
        "Unit 8: Distribution of Legislative & Executive Powers between Union and States; Legislative, Administrative & Financial Relations",
        "Unit 8: Powers and Functions of Constitutional Bodies, Human Rights Commission, RTI, Lokpal and Lok Ayukta",
        "Unit 9: Center-State Relations & Need for Reforms — Rajmannar Committee, Sarkaria Commission, M.M. Punchchi Commission, Unitary & Federal features",
        "Unit 9: Indian Political Parties, Party System, Recognition of National & State Parties, Elections, Electoral Reforms, and Anti-Defection Law",
        "Unit 10: Centralization vs Decentralization, Community Development Programme, Balwant Rai Mehta & Ashok Mehta Committees",
        "Unit 10: 73rd and 74th Constitutional Amendment Acts and their Implementation (Panchayati Raj & Urban Local Bodies)",
    ],
    "Indian Economy": [
        "Unit 1: National Income of India — Concept, Measurement, Occupational Pattern & Sectoral Distribution of Income",
        "Unit 1: Economic Growth & Development, Strategy of Planning in India, New Economic Reforms 1991, Decentralization of Financial Resources, NITI Aayog",
        "Unit 2: Functions and Measures of Money Supply, RBI (Functions, Monetary Policy and Control of Credit), Indian Banking Structure & Reforms",
        "Unit 2: Inflation (Causes & Remedies), India's Fiscal Policy (Fiscal Imbalance, Deficit Finance, FRBM)",
        "Unit 2: Indian Tax Structure, Goods and Services Tax (GST), Recent Indian Budget, India's Balance of Payments (BOP) & FDI",
        "Unit 3: Indian Agriculture — Cropping Pattern, Agricultural Production & Productivity",
        "Unit 3: Agricultural Finance and Marketing in India (Issues & Initiatives), Agricultural Pricing & Policy (MSP, Procurement, Issue Price, PDS)",
        "Unit 3: Industrial Development in India — Patterns and Problems, New Industrial Policy 1991, Disinvestment",
        "Unit 3: Ease of Doing Business, Industrial Sickness (Causes, Consequences and Remedial Measures)",
        "Unit 3: Services Sector — Growth and Contribution of Services Sector in India, Role of IT and ITES Industry in Development",
    ],
    "AP Economy": [
        "Unit 4: Structure and Growth of AP Economy — Gross State Domestic Product (GSDP) and Sectoral Contribution, AP Per Capita Income (PCI)",
        "Unit 4: AP State Revenue (Tax and Non-Tax Revenue), AP State Expenditure, Debts and Interest Payments",
        "Unit 4: Central Assistance, Projects of External Assistance, and Recent AP Budget",
        "Unit 5: Production Trends of Agriculture and Allied Sectors in AP, Cropping Pattern, and Rural Credit Cooperatives",
        "Unit 5: Agricultural Marketing in AP; Strategies, Schemes & Programmes for Agriculture & Allied Sectors (Horticulture, Animal Husbandry, Fisheries, Forests)",
        "Unit 5: Growth and Structure of Industries in AP, Recent AP Industrial Development Policy, Single Window Mechanism",
        "Unit 5: Industrial Incentives, MSMEs, and Industrial Corridors in Andhra Pradesh",
        "Unit 5: Structure and Growth of Services Sector in Andhra Pradesh",
        "Unit 5: Information Technology, Electronics and Communications in Andhra Pradesh, and Recent AP IT Policy",
        "Integrated AP Economy Synthesis: GSDP, State Public Finance, Agriculture-Industry-Services linkages in AP",
    ],
    "Science and Technology": [
        "Unit 1: National S&T Policy, Recent Science, Technology and Innovation Policy, National Strategies & Missions, Emerging Technology Frontiers",
        "Unit 1: Space Technology — Launch Vehicles of India, Recent Indian Satellite Launches & applications, Indian Space Science Missions",
        "Unit 1: Defence Technology — DRDO Structure, Vision & Mission, Technologies Developed by DRDO, Integrated Guided Missile Development Programme (IGMDP)",
        "Unit 1: ICT — National Policy on IT, Digital India Mission (Initiatives & Impact), E-Governance Programmes, Cyber Security & National Cyber Security Policy",
        "Unit 1: Nuclear Technology — Indian Nuclear Reactors and Nuclear Power Plants, Applications of Radioisotopes, India's Nuclear Programme",
        "Unit 2: Energy Management — Policy and Projections, Installed Energy Capacities and Demand in India, National Energy Policy",
        "Unit 2: National Policy on Biofuels, Bharat Stage Norms, and Non-Renewable Energy sources & capacities in India",
        "Unit 2: Renewable Energy in India — Sources, Installed Capacities, New Initiatives, Recent Programmes, Schemes and Achievements",
        "Unit 5 (Health): Recent Trends in Disease Burden, Epidemic and Pandemic Challenges in India",
        "Unit 5 (Health): Preparedness and Response — Healthcare Delivery and Outcomes in India, Recent Public Health Initiatives and Programmes",
    ],
    "Environment and Ecology": [
        "Unit 3: Ecology and Ecosystem — Basic concepts of Ecology, Ecosystem Components and Types",
        "Unit 3: Biodiversity — Meaning, Components, Biodiversity Hotspots, Loss of Biodiversity, Conservation Methods, Recent Plans, Targets, Conventions & Protocols",
        "Unit 3: Wildlife Conservation — CITES and Endangered Species with reference to India, Biosphere Reserves, Indian Wildlife Conservation efforts, projects & acts",
        "Unit 4: Solid Waste — Solid Wastes and their Classification, Methods of Disposal and Management of Solid Wastes in India",
        "Unit 4: Environmental Pollution — Types, Sources and Impacts; Pollution Control, Regulation & Alternatives (recent projects, acts & initiatives)",
        "Unit 4: Impact of Transgenics on Environment and their Regulation, Eco-Friendly Technologies in Agriculture, Bioremediation (Types & Scope in India)",
        "Unit 5: Environment Challenges — Global Warming, Climate Change, Acid Rain, Ozone Layer Depletion, Ocean Acidification",
        "Unit 5: Environmental Initiatives — Recent International Initiatives, Protocols, Conventions to tackle Climate Change (India's Participation & Role)",
        "Unit 5: Sustainable Development — Meaning, Nature, Scope, Components and Goals of Sustainable Development",
        "Integrated Environment & Ecology Synthesis: Biodiversity acts, pollution control, climate protocols, and sustainable development",
    ],
    "Prelims Full-Length Mock": [
        "Ancient History: Indus Valley Civilization, Vedic Age, Buddhism & Jainism",
        "Ancient History: Mauryan Empire, Gupta Empire & Harshavardhana (Admin, Society, Art, Literature)",
        "Medieval History (BASIC level only): Chola Admin, Delhi Sultanate, Mughal Empire, Bhakti-Sufi, Shivaji & Advent of Europeans",
        "Modern History: 1857 Revolt, British Power Consolidation, Administrative/Social Reforms (19th-20th c.)",
        "Modern History: Indian National Movement (1885-1947) & Post-Independence Consolidation and Reorganization",
        "General & Physical Geography: Solar System, Earth Interior, Landforms, Atmosphere, Oceans, India & AP Physical/Drainage/Soils/Hazards",
        "Economic & Human Geography (India): Resources, Agriculture, Industries, Transport, Demographics, Urbanization, Tribal/Linguistic groups",
        "Economic & Human Geography (Andhra Pradesh): AP Resources, Agriculture, Industries, Transport, Demographics & Tribes",
        "Indian Society: Structure (Family, Marriage, Kinship, Caste, Tribe, Ethnicity, Religion, Women) & Social Issues",
        "Indian Society: Welfare Mechanisms, Public Policies & Constitutional/Statutory Provisions (SC, ST, Minorities, BCs, Women, Disabled, Children)",
    ],
}

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
    if TARGET_SUBJECT in SUBJECT_BATCH_TOPICS:
        return TARGET_SUBJECT
    if today_ist >= date(2026, 12, 15):
        return "Prelims Full-Length Mock"
    return CALENDAR_WEEKDAY_MAP[today_ist.weekday()]


def normalize_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def fetch_existing_questions(subject: str) -> list[str]:
    encoded = urllib.parse.quote(subject, safe="")
    url = f"{SUPABASE_URL}/rest/v1/questions?subject=eq.{encoded}&select=question_text&order=created_at.desc&limit=200"
    req = urllib.request.Request(
        url,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
            return [r["question_text"] for r in rows if r.get("question_text")]
    except Exception as exc:
        print(f"Warning: could not fetch existing questions for dedup ({exc})")
        return []


def is_duplicate(candidate_text: str, seen_normalized: list[str]) -> bool:
    cand_norm = normalize_text(candidate_text)
    if not cand_norm:
        return True
    cand_head = cand_norm[:140]
    for prev in seen_normalized:
        if cand_head == prev[:140]:
            return True
        if difflib.SequenceMatcher(None, cand_norm[:220], prev[:220]).ratio() >= 0.72:
            return True
    return False


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
            "temperature": 0.8,
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


def fetch_questions_from_gemini(
    subject: str,
    batch_focus: str,
    count: int,
    batch_num: int,
    total_batches: int,
    forbidden_snippets: list[str],
) -> list[dict]:
    basic_note = ""
    if "Medieval" in subject or "Medieval" in batch_focus:
        basic_note = "- IMPORTANT: Keep Medieval Indian History questions strictly at a BASIC foundational level (major dynasties, rulers, monuments, Bhakti/Sufi basics).\n"

    forbidden_block = ""
    if forbidden_snippets:
        sample = "\n".join(f"- {s[:110]}" for s in forbidden_snippets[-45:])
        forbidden_block = f"\nDO NOT REPEAT OR PARAPHRASE ANY OF THESE ALREADY-ASKED QUESTIONS:\n{sample}\n"

    prompt = f"""Generate {count} UNIQUE, Degree-standard APPSC Group-II (Notification No. 37/2026) multiple-choice questions strictly within this official syllabus unit:
Subject: "{subject}"
Official Syllabus Unit (Batch {batch_num}/{total_batches}): "{batch_focus}"

STRICT SYLLABUS & QUALITY RULES:
1. Stay 100% INSIDE the official syllabus unit above. Do NOT drift into out-of-syllabus dynasties, eras, or topics not listed in "{batch_focus}".
2. Every single one of the {count} questions MUST test a DIFFERENT concept, sub-topic, ruler, article, or fact within "{batch_focus}". Never ask two questions on the same ruler, inscription, or event in this batch.
3. At least 80% MUST be analytical/multi-statement questions:
   - "Consider the following statements: 1... 2... 3... Which of the statements given above is/are correct?"
   - "How many of the above pairs are correctly matched?"
   - "Assertion (A) and Reason (R)"
   - "Arrange the following in chronological order"
   - "Match List-I with List-II" (use unique, non-cliche items; DO NOT repeat common textbook sets like Aihole/Hathigumpha/Junagadh/Allahabad Pillar unless specifically required by the unit).
4. Put subtle conceptual traps in statements (e.g., swapping two rulers/committees, changing an administrative term, inverting cause-and-effect, or mixing up provisions).
5. Format multi-statement questions with clean \\n line breaks before each numbered statement.
{basic_note}{forbidden_block}
Return ONLY a valid JSON array of {count} objects with these exact keys:
- "subject": "{subject}"
- "topic": short specific sub-topic string
- "difficulty": "Moderate" or "Hard" (use "Easy" for basic Medieval India)
- "question_text": full question text with \\n line breaks
- "option_a": string
- "option_b": string
- "option_c": string
- "option_d": string
- "correct_option": "A", "B", "C", or "D"
- "explanation": concise 2-sentence explanation clarifying why each statement is right or wrong
- "source": standard reference (e.g., "RS Sharma", "Bipan Chandra", "Laxmikanth", "Ramesh Singh", "NCERT", "Telugu Akademi")
"""

    data = None
    try:
        data = call_gemini_model(PRIMARY_MODEL, prompt)
    except Exception as primary_err:
        print(f"Primary model {PRIMARY_MODEL} unavailable ({primary_err}); discovering live backup models...")
        for backup in discover_backup_models():
            try:
                data = call_gemini_model(backup, prompt)
                print(f"Succeeded with backup model: {backup}")
                break
            except Exception:
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
    if not questions:
        return
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
    batch_topics = SUBJECT_BATCH_TOPICS[subject]
    total_batches = len(batch_topics)
    batch_size = 10

    existing_texts = fetch_existing_questions(subject)
    seen_normalized = [normalize_text(t) for t in existing_texts]
    forbidden_snippets = list(existing_texts)
    total_inserted = 0

    print(f"[{now_ist.isoformat()}] Generating 100 syllabus-aligned questions across {total_batches} units for: {subject} (existing in DB: {len(existing_texts)})")

    for idx, batch_focus in enumerate(batch_topics, start=1):
        for attempt in (1, 2):
            try:
                raw_batch = fetch_questions_from_gemini(
                    subject=subject,
                    batch_focus=batch_focus,
                    count=batch_size,
                    batch_num=idx,
                    total_batches=total_batches,
                    forbidden_snippets=forbidden_snippets,
                )
                unique_batch = []
                for q in raw_batch:
                    if not is_duplicate(q["question_text"], seen_normalized):
                        seen_normalized.append(normalize_text(q["question_text"]))
                        forbidden_snippets.append(q["question_text"])
                        unique_batch.append(q)
                    else:
                        print(f"Filtered duplicate question in batch {idx}: {q['question_text'][:80]}...")

                insert_into_supabase(unique_batch)
                total_inserted += len(unique_batch)
                print(f"Batch {idx}/{total_batches} ({batch_focus[:40]}...): inserted {len(unique_batch)} unique questions (total={total_inserted}).")
                break
            except Exception as exc:
                print(f"Batch {idx} attempt {attempt} failed: {exc}")
                if attempt == 2:
                    raise
                time.sleep(15)

    print(f"Successfully inserted {total_inserted} unique {subject} questions into Supabase.")


if __name__ == "__main__":
    main()
