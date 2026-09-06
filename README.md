# 💼 LinkedIn Market Intelligence Platform

An automated data pipeline and real-time analytical dashboard that extracts, enriches, and visualizes LinkedIn job market trends.

**Developed by:** [Chamchi Rabie](https://chamchirabie.com/)

---

## ⚡ Key Features

- **Guest Ingestion Pipeline:** Extracts LinkedIn job postings without requiring user authentication or a headless browser.
- **Deep Skill & Language Extraction:** Scrapes full posting bodies to categorize required tools (e.g., Python, Docker, React) and spoken/written languages.
- **Persistent Storage:** Upserts unique postings by LinkedIn Job ID into an SQLite database (`jobs.db`) to avoid duplicate records.
- **Interactive Analytics:** Real-time metrics, hiring company rankings, seniority distribution, and skill cross-tabulations built with Plotly.
- **Search & Export:** Multi-filter query tool with instant CSV and JSON export options.

---

## 🚀 Quickstart

### 1. Clone the Repository
\`\`\`bash
git clone https://github.com/<your-username>/linkedin-market-intelligence.git
cd linkedin-market-intelligence
\`\`\`

### 2. Install Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 3. Launch Dashboard
\`\`\`bash
streamlit run dashboard.py
\`\`\`