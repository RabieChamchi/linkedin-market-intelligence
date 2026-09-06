import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from pipeline import run_scrape, DB_PATH, init_db

st.set_page_config(page_title="LinkedIn Market Intelligence", page_icon="💼", layout="wide")
init_db()

# Fetch data from SQLite
def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("SELECT * FROM jobs ORDER BY scraped_at DESC", conn)

st.title("💼 LinkedIn Market Intelligence Platform")

# ---------------------------------------------------------
# SIDEBAR: LIVE RUNNER & FILTERS
# ---------------------------------------------------------
st.sidebar.header("🎯 Scrape New Postings")
keyword_input = st.sidebar.text_input("Role / Keyword", "Data Engineer")
location_input = st.sidebar.text_input("Location", "Remote")
limit_input = st.sidebar.slider("Number of Postings", min_value=10, max_value=100, value=25, step=5)

if st.sidebar.button("Run Extraction"):
    status_box = st.sidebar.empty()
    progress_bar = st.sidebar.progress(0)

    def update_ui(current, total, current_title):
        pct = current / total
        progress_bar.progress(pct)
        status_box.caption(f"Saved ({current}/{total}): {current_title[:28]}...")

    count = run_scrape(keyword_input, location_input, limit_input, update_ui)
    st.sidebar.success(f"Added {count} new postings to database!")
    st.rerun()

# ---------------------------------------------------------
# DASHBOARD BODY
# ---------------------------------------------------------
df = load_data()

if df.empty:
    st.info("The database is currently empty. Run a scrape using the sidebar to start collecting market data.")
    st.stop()

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total Postings Tracked", len(df))
kpi2.metric("Unique Companies", df["company"].nunique())
kpi3.metric("Remote Roles", df["location"].str.contains("Remote", case=False).sum())
kpi4.metric("Senior / Lead Roles", df["seniority"].isin(["Senior", "Lead / Principal"]).sum())

st.markdown("---")

# Analytics Tabs
tab1, tab2, tab3 = st.tabs(["📊 Market Analytics", "🛠️ In-Demand Tech", "🔍 Job Explorer"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Hiring Companies")
        top_comp = df["company"].value_counts().head(10).reset_index()
        top_comp.columns = ["Company", "Postings"]
        fig = px.bar(top_comp, x="Postings", y="Company", orientation="h", template="plotly_white")
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Seniority Distribution")
        fig_pie = px.pie(df, names="seniority", hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("Most Requested Skills & Tools")
    all_skills = df["skills"].str.split(", ").explode()
    all_skills = all_skills[all_skills != "None Listed"]
    
    if not all_skills.empty:
        skill_counts = all_skills.value_counts().reset_index()
        skill_counts.columns = ["Skill", "Count"]
        fig_skills = px.bar(skill_counts, x="Skill", y="Count", color="Count", color_continuous_scale="Blues")
        st.plotly_chart(fig_skills, use_container_width=True)
    else:
        st.write("No matching tech stack keywords found yet.")

with tab3:
    st.subheader("Database Explorer")
    
    # Filter controls
    f1, f2 = st.columns(2)
    with f1:
        comp_filter = st.multiselect("Filter by Company", options=df["company"].unique())
    with f2:
        sen_filter = st.multiselect("Filter by Seniority", options=df["seniority"].unique())

    filtered_df = df.copy()
    if comp_filter:
        filtered_df = filtered_df[filtered_df["company"].isin(comp_filter)]
    if sen_filter:
        filtered_df = filtered_df[filtered_df["seniority"].isin(sen_filter)]

    st.dataframe(
        filtered_df[["title", "company", "location", "seniority", "skills", "url", "scraped_at"]],
        column_config={"url": st.column_config.LinkColumn("Apply Link")},
        use_container_width=True,
        hide_index=True
    )