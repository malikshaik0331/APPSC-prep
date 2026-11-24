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

# 10 Distinct Sub-Topic Pillars per Subject so Batches 1..10 NEVER overlap
SUBJECT_BATCH_TOPICS = {
    "Ancient Indian History": [
        "Pre-Historic India (Palaeolithic, Mesolithic, Neolithic, Chalcolithic) & Indus Valley town planning, trade, seals, and decline theories",
        "Early & Later Vedic Period: Rigvedic vs Later Vedic polity, sabha/samiti, varna evolution, sacrifices, and Upanishadic philosophy",
        "Heterodox Sects: Buddhism (Hinayana/Mahayana/Vajrayana, Councils, Bodhisattvas), Jainism (Tirthankaras, Syadvada, Anekantavada), and Ajivikas",
        "Mahajanapadas, Magadhan Imperialism, Alexander's invasion, and Mauryan administration (Arthashastra, Ashokan Dhamma, provincial officials)",
        "Post-Mauryan Era: Indo-Greeks, Shakas, Parthians, Kushanas (Kanishka, Silk Route, coinage) and Satavahana economy & society",
        "Sangam Age: Cheras, Cholas, Pandyas, Sangam literature (Ettuthogai, Pattuppattu, Tolkappiyam), tinai ecological zones, and Roman trade",
        "Gupta Empire: Samudragupta to Skandagupta, land grants (agrahara/brahmadeya), guild system, gold coinage, Aryabhata/Varahamihira",
        "Post-Gupta North & Deccan: Harshavardhana (administration, Xuanzang, Banabhatta), Badami Chalukyas, Pallavas of Kanchi, and Tripartite Struggle",
        "Ancient Art & Architecture: Stupas, Chaityas, Viharas, Gandhara vs Mathura vs Amaravati schools, Nagara/Dravida/Vesara temple origins",
        "Ancient Literature, Science & Epigraphy: Sanskrit/Prakrit/Pali texts, foreign accounts (Megasthenes, Faxian, Periplus), and lesser-known inscriptions",
    ],
    "Modern Indian History": [
        "18th-Century Regional States, Carnatic Wars, Plassey, Buxar, Subsidiary Alliance & Doctrine of Lapse",
        "British Land Revenue Systems (Permanent, Ryotwari, Mahalwari), Deindustrialisation, Drain of Wealth & Famines",
        "Tribal, Peasant & Civil Uprisings pre-1857 (Santhal, Kol, Indigo, Pabna, Deccan Riots) and Revolt of 1857 regional leaders",
        "19th-Century Socio-Religious Reforms (Brahmo Samaj, Arya Samaj, Satyashodhak, Aligarh, Ramakrishna, Temple Entry)",
        "Early Nationalism (1885-1905), Moderate vs Extremist split, Swadeshi & Boycott Movement, Surat Split, Revolutionary Phase I",
        "Home Rule League, Lucknow Pact, Champaran, Kheda, Ahmedabad Mill Strike, Rowlatt Satyagraha & Khilafat-Non-Cooperation",
        "Swarajists, Simon Commission, Nehru Report, Lahore Session (1929), Civil Disobedience, Gandhi-Irwin Pact & Round Table Conferences",
        "Revolutionary Phase II (HSRA, Bhagat Singh, Surya Sen), Trade Union & Peasant Sabhas (1920s-30s), Princely States Praja Mandal",
        "Provincial Elections (1937), August Offer, Cripps Mission, Quit India Movement (parallel governments), INA & RIN Mutiny",
        "Cabinet Mission, Mountbatten Plan, Partition, Constitutional Acts (1773-1947) & Freedom Struggle in Andhra",
    ],
    "Medieval Indian History (Basic)": [
        "Early Medieval Rajput kingdoms, Mahmud of Ghazni, Muhammad Ghori (basic chronology & battles)",
        "Delhi Sultanate: Slave & Khilji dynasties (Qutbuddin Aibak, Iltutmish, Balban, Alauddin Khilji market basics)",
        "Delhi Sultanate: Tughlaq, Sayyid & Lodi dynasties (Muhammad bin Tughlaq projects, Firoz Shah Tughlaq)",
        "Delhi Sultanate basic administration, Iqta system & Indo-Islamic architecture (Qutb Minar, Alai Darwaza)",
        "Vijayanagara Empire basics: four dynasties, Harihara-Bukka, Krishnadevaraya & Hampi monuments",
        "Bahmani Kingdom & Deccan Sultanates (five splinter states, Mahmud Gawan basics)",
        "Bhakti Movement basics: Kabir, Nanak, Mirabai, Chaitanya, Vallabhacharya, Alvars & Nayanars",
        "Sufi Movement basics: Chishti & Suhrawardi silsilas, Nizamuddin Auliya, Amir Khusrau",
        "Early Mughals: Babur, Humayun, Sher Shah Suri (administration & GT Road), Akbar's major policies",
        "Later Great Mughals (Jahangir, Shah Jahan, Aurangzeb), basic Mansabdari, Mughal architecture & Marathas (Shivaji basics)",
    ],
    "Indian Geography": [
        "Geological structure of India, Himalayas (divisions & passes) and Northern Plains physiography",
        "Peninsular Plateau, Western & Eastern Ghats, Coastal Plains & Indian Islands (Andaman, Nicobar, Lakshadweep)",
        "Himalayan vs Peninsular Drainage Systems, river disputes, interlinking & major multipurpose projects",
        "Indian Monsoon mechanism (ITCZ, El Nino, IOD, jet streams), Koppen climate classification & rainfall distribution",
        "Soils of India (ICAR classification), soil erosion/conservation & Natural Vegetation (forest types)",
        "Indian Agriculture: cropping seasons, Green Revolution, major crops, irrigation & agro-climatic zones",
        "Mineral & Energy Resources: coal, iron ore, bauxite, mica, petroleum, nuclear & renewable corridors",
        "Manufacturing Industries (iron-steel, cotton, IT, Petrochemicals) & Industrial Regions of India",
        "Transport & Communication: National Highways, Dedicated Freight Corridors, Inland Waterways & Major Ports",
        "Demographics, Census patterns, urbanization, tribes of India & natural hazards (cyclones, landslides, earthquakes)",
    ],
    "AP Geography": [
        "Andhra Pradesh physiography: Coastal Plains, Eastern Ghats (Nallamala, Papi, Horsley Hills) & Rayalaseema plateau",
        "26-District reorganization of Andhra Pradesh, boundaries, coastal length & neighbouring state borders",
        "Godavari & Krishna river basins in AP, tributaries, deltas, Polavaram, Nagarjuna Sagar & Srisailam projects",
        "Penna, Vamsadhara, Nagavali & minor coastal rivers, Handri-Neeva, Galeru-Nagari & Veligonda projects",
        "Climate, monsoon patterns, cyclones along AP coast, drought-prone Rayalaseema & agro-climatic zones",
        "Soils of Andhra Pradesh (red, black cotton, alluvial, laterite), forests, mangroves (Coringa) & wildlife sanctuaries",
        "Agriculture & Horticulture in AP: paddy, chilli, tobacco, cotton, aquaculture & GI-tagged AP products",
        "Minerals & Energy in AP: barytes (Mangampeta), limestone, bauxite, mica, uranium (Tummalapalle) & KG Basin gas",
        "Ports, Maritime Infrastructure & Industrial Corridors (Visakhapatnam, Krishnapatnam, Gangavaram, VCIC, CBIC)",
        "AP Demographics, urbanization, tribal belts (Agency areas, Particularly Vulnerable Tribal Groups) & transport network",
    ],
    "Indian Society": [
        "Salient features of Indian Society, unity in diversity, linguistic/religious/regional pluralism",
        "Family, Marriage & Kinship structures in India: changing patterns, nuclearisation & legal reforms",
        "Caste system: origin theories, varna vs jati, Sanskritisation, dominant caste & constitutional safeguards",
        "Tribal communities in India: classification, PESA Act, Forest Rights Act, Fifth & Sixth Schedules",
        "Women's status, gender inequality, constitutional/legal protections (POSH, Domestic Violence, 106th Amendment)",
        "Religious Minorities, Secularism, Communalism & Constitutional Articles (Articles 25-30)",
        "Regionalism, Linguism, Casteism & Social Stratification / Mobility in contemporary India",
        "Social Exclusion & Vulnerable Sections: SC, ST, OBC, Differently Abled, Elderly & Transgender rights",
        "Population dynamics, demographic dividend, urbanisation challenges, slums & migration",
        "Social Welfare Policies & Institutions: NCW, NCSC, NCST, NCBC, NHRC & flagship social security schemes",
    ],
    "AP History": [
        "Pre-Historic AP & Satavahana Dynasty: Gautamiputra Satakarni, administration, Amaravati art & Prakrit literature",
        "Ikshvakus of Vijayapuri, Brihatphalayanas, Salankayanas & Vishnukundinas: inscriptions & Buddhist centres",
        "Eastern Chalukyas of Vengi: Kubja Vishnuvardhana to Rajaraja Narendra, Nannaya, Bezawada/Rajahmundry culture",
        "Kakatiya Dynasty: Rudradeva, Ganapatideva, Rudramadevi, Prataparudra, Nayankara system, tanks & Motupalli",
        "Reddi Kingdoms of Kondavidu & Rajahmundry, Musunuri Nayakas & Gajapati rule in Coastal Andhra",
        "Vijayanagara Empire in Andhra: Sri Krishnadevaraya, Ashtadiggajas, Lepakshi, Rayalaseema polity & foreign travelers",
        "Qutb Shahis of Golconda, Asaf Jahis & Advent of Europeans (Machilipatnam, Pulicat, Bheemunipatnam, Nizampatnam)",
        "19th-Century Social Reform & Literary Awakening in Andhra: Veeresalingam, Gurajada, Gidugu, Raghupati Venkataratnam",
        "Freedom Struggle in Andhra: Vandemataram, Home Rule, Chirala-Perala, Palnadu, Rampa Rebellion (Alluri), Salt Satyagraha",
        "Andhra Movement (1913-1956): Andhra Mahasabha, Sri Bagh Pact, Potti Sreeramulu, Gentlemen's Agreement & AP Bifurcation",
    ],
    "Polity": [
        "Historical background, Constituent Assembly, Preamble & Salient Features of the Indian Constitution",
        "Union & its Territory (Art 1-4), Citizenship (Art 5-11) & Basic Structure Doctrine",
        "Fundamental Rights (Art 12-35): Equality, Freedom, Life & Liberty, Minority rights & Writs",
        "Directive Principles of State Policy (DPSP), Fundamental Duties & FR-DPSP harmony",
        "Parliament: Lok Sabha/Rajya Sabha powers, legislative procedures, Money vs Financial bills & Parliamentary Committees",
        "Union Executive & State Executive: President, Governor, PM, CM, Council of Ministers & Ordinance powers",
        "Judiciary: Supreme Court, High Courts, Judicial Review, PIL, Collegium, Tribunals & Basic Structure cases",
        "Federalism, Centre-State Relations (Legislative, Administrative, Financial), GST Council & Inter-State Council",
        "Panchayati Raj (73rd Amendment), Municipalities (74th Amendment), PESA & Co-operative Societies (97th Amendment)",
        "Constitutional & Statutory Bodies: ECI, CAG, UPSC, Finance Commission, NCSC/NCST/NCBC, Lokpal & Anti-Defection Law",
    ],
    "Indian Economy": [
        "National Income Accounting (GDP, GNP, GVA, base year, inclusive growth & Human Development indices)",
        "Monetary Policy & RBI: Repo/Reverse Repo, SDF, CRR/SLR, MPC, inflation targeting & liquidity management",
        "Banking & Financial Sector Reforms: NPA resolution, IBC 2016, NARCL, Basel norms, NBFCs & SEBI/capital markets",
        "Fiscal Policy & Union Budget: Fiscal/Revenue/Primary deficit, FRBM Act, Finance Commission & GST architecture",
        "Agriculture & Allied Sectors: MSP, e-NAM, food processing, PDS, subsidies & agricultural credit",
        "Industry, MSMEs & Infrastructure: Make in India, PLI schemes, PM Gati Shakti, disinvestment & logistics",
        "External Sector: Balance of Payments, Forex reserves, exchange rate, FDI/FPI, WTO & FTAs",
        "Poverty, Unemployment & Inequality: Tendulkar/Rangarajan committees, PLFS metrics & gig economy",
        "NITI Aayog, Planning transition, SDG India Index & Sustainable Finance",
        "Major Flagship Central Schemes: PM-KISAN, MGNREGA, Ayushman Bharat, Jal Jeevan, PM Awas & Financial Inclusion",
    ],
    "AP Economy": [
        "AP Socio-Economic Survey: GSDP growth, per capita income & sectoral share (Agriculture, Industry, Services)",
        "AP State Budget, revenue vs capital expenditure, fiscal deficit, state debt & 16th Finance Commission devolution",
        "AP Agriculture & Irrigation: cropping intensity, horticulture, aquaculture, Rythu Bharosa & Polavaram impact",
        "AP Industrial Policy, MSMEs, Visakhapatnam-Chennai & Chennai-Bengaluru Industrial Corridors & IT/Electronics",
        "AP Energy Sector, renewable energy parks, ports-led development & Maritime Board initiatives",
        "AP Welfare & Social Security Schemes (Navaratnalu / state flagship programs) & targeting mechanisms",
        "AP Education & Health indicators, Nadu-Nedu, IMR/MMR trends & skill development initiatives",
        "AP Urbanization, Smart Cities, Amaravati/Visakhapatnam/Tirupati growth nodes & rural infrastructure",
        "AP Employment, SHGs (SERP/MEPMA), women empowerment & financial inclusion in AP",
        "AP Tribal & Regional Development disparities (Coastal Andhra vs Rayalaseema economic indicators)",
    ],
    "Science and Technology": [
        "ISRO Space Missions: Chandrayaan, Aditya-L1, Gaganyaan, PSLV/GSLV/LVM3, NavIC & private space startups (IN-SPACe)",
        "Defence Technology & DRDO: Agni/Prithvi/BrahMos missiles, LCA Tejas, submarines, air defence & indigenisation",
        "Biotechnology & Health: CRISPR/gene editing, mRNA/DNA vaccines, stem cells, GM crops & antimicrobial resistance",
        "Artificial Intelligence, Quantum Computing (National Quantum Mission), Semiconductors (ISM) & 5G/6G",
        "Nuclear Energy: India's 3-stage nuclear programme, PHWRs, thorium cycle, fusion (ITER) & nuclear liability",
        "Renewable & Clean Tech: Green Hydrogen Mission, battery storage (Li-ion/Na-ion), solar PV & biofuels",
        "Digital Public Infrastructure: UPI, Aadhaar, ONDC, DigiLocker, BHASHINI & Cybersecurity (CERT-In)",
        "Communicable & Non-Communicable Diseases, diagnostics, Genome India & One Health",
        "Intellectual Property Rights (Patents Act, GI tags, compulsory licensing) & R&D policy (ANRF)",
        "Emerging Materials, Robotics, Drones, Deep Ocean Mission (Samudrayaan) & Nanotechnology",
    ],
    "Environment and Ecology": [
        "Ecosystem concepts: food webs, ecological pyramids, biogeochemical cycles & biodiversity indices",
        "Biodiversity in India & AP: Western Ghats, Eastern Ghats, hotspots, endemic species & IUCN Red List",
        "Protected Area Network: National Parks, Wildlife Sanctuaries, Biosphere Reserves, Tiger Reserves & AP sites",
        "Wetlands & Mangroves: Ramsar sites in India/AP (Kolleru, Coringa), Montreux Record & MISHTI",
        "Environmental Legislation: Wildlife Protection Act 1972 (2022 amendment), EPA 1986, Forest Conservation Act & CAMPA",
        "Climate Change Science & Treaties: UNFCCC, Paris Agreement, COP summits, NDCs, Net Zero 2070 & Carbon Markets",
        "Pollution & Waste Management: Air Quality Index, CPCB/NGT, e-waste, plastic ban, bioremediation & fly ash",
        "Environmental Impact Assessment (EIA), Coastal Regulation Zone (CRZ) & Ecologically Sensitive Areas",
        "International Conventions: CBD (Kunming-Montreal), CITES, CMS, Basel/Rotterdam/Stockholm & ISA",
        "Disaster Management: NDMA framework, cyclones, heatwaves, urban floods, landslides & Sendai Framework",
    ],
    "Prelims Full-Length Mock": [
        "Ancient Indian History: IVC, Vedic, Buddhism, Jainism & Mauryan administration",
        "Ancient Indian History: Post-Mauryan, Guptas, Sangam Age, Art & Architecture",
        "Medieval Indian History (BASIC level only): Delhi Sultanate, Bhakti/Sufi, Vijayanagara & Mughal basics",
        "Modern Indian History: 1857 Revolt, Socio-Religious Reforms & British Economic Policies",
        "Modern Indian History: INC Phases, Gandhian Era, Revolutionaries & Constitutional Acts",
        "Indian Geography: Physiography, Drainage, Monsoon, Soils & Natural Vegetation",
        "Indian Geography: Agriculture, Minerals, Energy, Transport & Demographics",
        "AP Geography: Physiography, Rivers, Irrigation Projects, Soils, Minerals, Ports & 26 Districts",
        "Indian Society: Caste, Tribe, Family, Marriage, Kinship & Women's Safeguards",
        "Indian Society: Minorities, Secularism, Regionalism, Social Exclusion & Welfare Policies",
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
    # Check first 140 chars + full similarity against existing/batch questions
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

    prompt = f"""Generate {count} UNIQUE, UPSC / APPSC Group 2 Prelims-calibre multiple-choice questions strictly on this sub-topic:
Subject: "{subject}"
Assigned Sub-Topic for Batch {batch_num}/{total_batches}: "{batch_focus}"

STRICT QUALITY & NON-REPETITION RULES:
1. Every single one of the {count} questions MUST test a DIFFERENT concept, ruler, event, article, or fact within "{batch_focus}". Never ask two questions on the same ruler, inscription, or event in this batch.
2. At least 80% MUST be analytical/multi-statement questions:
   - "Consider the following statements: 1... 2... 3... Which of the statements given above is/are correct?"
   - "How many of the above pairs are correctly matched?"
   - "Assertion (A) and Reason (R)"
   - "Arrange the following in chronological order"
   - "Match List-I with List-II" (use unique, non-cliche items; DO NOT repeat common textbook sets like Aihole/Hathigumpha/Junagadh/Allahabad Pillar unless specifically required by the sub-topic).
3. Put subtle conceptual traps in statements (e.g., swapping two rulers, changing an administrative term, inverting cause-and-effect, or mixing up centuries).
4. Format multi-statement questions with clean \\n line breaks before each numbered statement.
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
- "source": standard reference (e.g., "RS Sharma", "Upinder Singh", "Bipan Chandra", "Laxmikanth", "NCERT", "Telugu Akademi")
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

    print(f"[{now_ist.isoformat()}] Generating 100 UNIQUE questions across {total_batches} distinct sub-topics for: {subject} (existing in DB: {len(existing_texts)})")

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
