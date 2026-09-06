import sqlite3
import re
import time
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd

DB_PATH = "jobs.db"

# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                seniority TEXT,
                skills TEXT,
                languages TEXT,
                description TEXT,
                url TEXT,
                scraped_at TIMESTAMP
            )
        """)
        # Safe migration if table already exists without languages column
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        if "languages" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN languages TEXT")
        conn.commit()

# ---------------------------------------------------------
# ENRICHMENT HELPERS
# ---------------------------------------------------------
SKILL_PATTERNS = {
    "Python": r"\bpython\b",
    "JavaScript": r"\bjavascript\b|\bjs\b",
    "TypeScript": r"\btypescript\b|\bts\b",
    "React": r"\breact(\.js)?\b",
    "Node.js": r"\bnode(\.js)?\b",
    "SQL": r"\bsql\b|\bpostgres(ql)?\b|\bmysql\b",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\b(k8s|kubernetes)\b",
    "AWS": r"\baws\b|\bamazon web services\b",
    "GCP": r"\bgcp\b|\bgoogle cloud\b",
    "Azure": r"\bazure\b",
    "Tailwind": r"\btailwind\b",
    "Next.js": r"\bnext(\.js)?\b"
}

LANGUAGE_PATTERNS = {
    "English": r"\b(english|anglais|englisch|ingl[eé]s)\b",
    "French": r"\b(french|fran[cç]ais|franz[oö]sisch|franc[eé]s)\b",
    "German": r"\b(german|deutsch|allemand|alem[aá]n)\b",
    "Spanish": r"\b(spanish|espagnol|espa[nñ]ol|spanisch)\b",
    "Arabic": r"\b(arabic|arabe|arabisch|árabe)\b",
    "Italian": r"\b(italian|italien|italiano|italienisch)\b",
    "Portuguese": r"\b(portuguese|portugais|portugu[eê]s)\b",
    "Dutch": r"\b(dutch|n[eé]erlandais|holl[aä]ndisch|holand[eé]s)\b"
}

def extract_seniority(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["intern", "co-op"]):
        return "Intern"
    if any(k in t for k in ["junior", "jr", "entry", "associate"]):
        return "Junior"
    if any(k in t for k in ["lead", "principal", "staff", "architect", "head", "director"]):
        return "Lead / Principal"
    if any(k in t for k in ["senior", "sr"]):
        return "Senior"
    return "Mid-Level"

def extract_skills(text: str) -> str:
    found = []
    for skill, pattern in SKILL_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            found.append(skill)
    return ", ".join(found) if found else "None Listed"

def extract_languages(text: str) -> str:
    found = []
    for lang, pattern in LANGUAGE_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            found.append(lang)
    return ", ".join(found) if found else "Not Specified"

# ---------------------------------------------------------
# HTTP CLIENT
# ---------------------------------------------------------
def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    })
    return session

def fetch_job_details(session, job_id: str) -> str:
    desc_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        res = session.get(desc_url, timeout=(5, 12))
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            desc_el = soup.find("div", class_="description__text")
            return desc_el.get_text(separator=" ", strip=True) if desc_el else ""
    except Exception:
        pass
    return ""

# ---------------------------------------------------------
# MAIN PIPELINE SCRAPER
# ---------------------------------------------------------
def run_scrape(keyword: str, location: str = "Remote", limit: int = 25, progress_callback=None):
    init_db()
    session = get_session()
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    
    start = 0
    total_saved = 0
    
    while total_saved < limit:
        params = {"keywords": keyword, "location": location, "start": start}
        try:
            res = session.get(base_url, params=params, timeout=(10, 20))
            if res.status_code == 429:
                time.sleep(5)
                continue
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("li")
            if not cards:
                break

            for card in cards:
                title_el = card.find("h3", class_="base-search-card__title")
                comp_el = card.find("h4", class_="base-search-card__subtitle")
                loc_el = card.find("span", class_="job-search-card__location")
                link_el = card.find("a", class_="base-card__full-link")

                if not (title_el and link_el):
                    continue

                raw_url = link_el.get("href", "").split("?")[0]
                job_id_match = re.search(r"(\d+)", raw_url)
                if not job_id_match:
                    continue
                job_id = job_id_match.group(1)

                with sqlite3.connect(DB_PATH) as conn:
                    exists = conn.cursor().execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
                    if exists:
                        continue

                desc_text = fetch_job_details(session, job_id)
                full_text = f"{title_el.text} {desc_text}"

                job_data = (
                    job_id,
                    title_el.text.strip(),
                    comp_el.text.strip() if comp_el else "Unknown",
                    loc_el.text.strip() if loc_el else "Unknown",
                    extract_seniority(title_el.text),
                    extract_skills(full_text),
                    extract_languages(full_text),
                    desc_text[:1000],
                    raw_url,
                    datetime.now()
                )

                with sqlite3.connect(DB_PATH) as conn:
                    conn.cursor().execute("""
                        INSERT OR REPLACE INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, job_data)
                    conn.commit()

                total_saved += 1
                if progress_callback:
                    progress_callback(total_saved, limit, title_el.text.strip())

                if total_saved >= limit:
                    break

                time.sleep(random.uniform(0.8, 1.8))

            start += 25
        except Exception as err:
            print(f"[!] Scraper notice: {err}")
            break

    return total_saved