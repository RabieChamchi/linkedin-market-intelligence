import sqlite3
import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
from pipeline import DB_PATH, init_db, run_scrape

st.set_page_config(
    page_title="LinkedIn Intelligence | By Chamchi Rabie",
    page_icon="💼",
    layout="wide",
)

init_db()

# Custom Plotly Template
CHART_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(148, 163, 184, 0.15)"
TEXT_COLOR = "#94a3b8"
PRIMARY_GRADIENT = ["#1e1b4b", "#3b82f6", "#06b6d4", "#22d3ee"]

custom_template = pio.templates["plotly_white"]
custom_template.layout.update(
    paper_bgcolor=CHART_BG,
    plot_bgcolor=CHART_BG,
    font=dict(family="Inter, -apple-system, sans-serif", color=TEXT_COLOR, size=12),
    xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False),
    margin=dict(l=20, r=20, t=40, b=20),
)
pio.templates["custom_executive"] = custom_template
pio.templates.default = "custom_executive"

SENIORITY_COLORS = {
    "Intern": "#94a3b8",
    "Junior": "#38bdf8",
    "Mid-Level": "#6366f1",
    "Senior": "#a855f7",
    "Lead / Principal": "#ec4899",
}

WORKPLACE_COLORS = {
    "Remote": "#10b981",
    "Hybrid": "#06b6d4",
    "On-Site": "#64748b",
}


def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("SELECT * FROM jobs ORDER BY scraped_at DESC", conn)


def reset_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.cursor().execute("DELETE FROM jobs")
        conn.commit()


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 💼 **Job Intelligence Engine**")
    st.markdown(
        "By: [**Chamchi Rabie**](https://chamchirabie.com/)",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.subheader("🎯 Scrape Postings")
    keyword_input = st.text_input("Role / Keyword", "Frontend Engineer")
    location_input = st.text_input("Location", "Remote")
    limit_input = st.slider(
        "Max Postings to Fetch", min_value=10, max_value=100, value=25, step=5
    )

    if st.button("🚀 Run Extraction", use_container_width=True):
        status_box = st.empty()
        progress_bar = st.progress(0)

        def update_ui(current, total, current_title):
            pct = min(current / total, 1.0)
            progress_bar.progress(pct)
            status_box.caption(
                f"Extracting ({current}/{total}): {current_title[:25]}..."
            )

        count = run_scrape(keyword_input, location_input, limit_input, update_ui)
        st.success(f"Added {count} postings!")
        st.rerun()

    st.markdown("---")

    st.subheader("⚠️ Manage Data")
    with st.popover("🗑️ Reset All Data", use_container_width=True):
        st.warning("This will permanently wipe all stored queries and listings.")
        if st.button("Confirm Delete", type="primary", use_container_width=True):
            reset_database()
            st.success("Database cleared!")
            st.rerun()


# ---------------------------------------------------------
# HEADER SECTION
# ---------------------------------------------------------
st.markdown(
    """
    <div style="padding: 10px 0 20px 0;">
        <h1 style="font-size: 2.3rem; font-weight: 800; margin: 0; letter-spacing: -0.02em;">
            LinkedIn Market Intelligence
        </h1>
        <div style="font-size: 1rem; color: #64748b; margin-top: 4px;">
            Curated by <a href="https://chamchirabie.com/" target="_blank" style="text-decoration: none; font-weight: 600; color: #0284c7;">Chamchi Rabie</a> • Continuous Data Extraction & Trend Analysis
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

df = load_data()

if df.empty:
    st.info("👋 Database is empty. Configure a keyword search on the sidebar and click **Run Extraction**.")
    st.stop()

# Safety fallback if legacy records exist without languages
if "languages" not in df.columns:
    df["languages"] = "Not Specified"
else:
    df["languages"] = df["languages"].fillna("Not Specified")

# ---------------------------------------------------------
# DATA ENRICHMENT
# ---------------------------------------------------------
def categorize_workplace(loc):
    loc_lower = str(loc).lower()
    if "remote" in loc_lower:
        return "Remote"
    elif "hybrid" in loc_lower:
        return "Hybrid"
    return "On-Site"


df["workplace_type"] = df["location"].apply(categorize_workplace)
df["scraped_date"] = pd.to_datetime(df["scraped_at"]).dt.date

# ---------------------------------------------------------
# EXECUTIVE KPI ROW
# ---------------------------------------------------------
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Indexed Jobs", f"{len(df):,}")
kpi2.metric("Active Employers", df["company"].nunique())
kpi3.metric("Remote Roles", f"{(df['workplace_type'] == 'Remote').mean() * 100:.1f}%")
kpi4.metric("Senior & Lead Roles", df["seniority"].isin(["Senior", "Lead / Principal"]).sum())
kpi5.metric("Tracked Skills", df["skills"].str.split(", ").explode().nunique())

st.markdown("---")

# ---------------------------------------------------------
# TABS INTERFACE
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📊 Market & Roles",
        "🛠️ Skills & Seniority Matrix",
        "📍 Workplaces & Velocity",
        "🔍 Job Explorer & Export",
    ]
)

# TAB 1: MARKET & ROLES
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Actively Hiring Companies")
        top_comp = df["company"].value_counts().head(10).reset_index()
        top_comp.columns = ["Company", "Open Postings"]
        
        fig_comp = px.bar(
            top_comp,
            x="Open Postings",
            y="Company",
            orientation="h",
            color="Open Postings",
            color_continuous_scale=PRIMARY_GRADIENT,
        )
        fig_comp.update_traces(marker_line_width=0, opacity=0.9)
        fig_comp.update_layout(
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            height=380,
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    with col2:
        st.subheader("Seniority Distribution")
        sen_counts = df["seniority"].value_counts().reset_index()
        sen_counts.columns = ["Seniority", "Count"]
        
        fig_sen = px.pie(
            sen_counts,
            names="Seniority",
            values="Count",
            hole=0.6,
            color="Seniority",
            color_discrete_map=SENIORITY_COLORS,
        )
        fig_sen.update_traces(textposition="inside", textinfo="percent+label", hoverinfo="label+value")
        fig_sen.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig_sen, use_container_width=True)

# TAB 2: SKILLS & SENIORITY MATRIX (Tech only)
with tab2:
    st.subheader("Top In-Demand Technologies & Frameworks")
    exploded_skills = (
        df.assign(skill=df["skills"].str.split(", "))
        .explode("skill")
        .reset_index(drop=True)
    )
    exploded_skills = exploded_skills[
        (exploded_skills["skill"] != "None Listed")
        & (exploded_skills["skill"].notna())
        & (exploded_skills["skill"].str.strip() != "")
    ]

    if not exploded_skills.empty:
        skill_counts = exploded_skills["skill"].value_counts().head(12).reset_index()
        skill_counts.columns = ["Skill", "Mentions"]
        
        fig_skills = px.bar(
            skill_counts,
            x="Skill",
            y="Mentions",
            color="Mentions",
            color_continuous_scale=["#312e81", "#4f46e5", "#06b6d4"],
        )
        fig_skills.update_traces(marker_line_width=0, opacity=0.95)
        fig_skills.update_layout(coloraxis_showscale=False, height=360)
        st.plotly_chart(fig_skills, use_container_width=True)

        st.markdown("#### **Skill Demand Across Seniority Tiers**")
        top_skill_names = skill_counts["Skill"].tolist()
        top_skills_df = exploded_skills[exploded_skills["skill"].isin(top_skill_names)]

        cross_tab = (
            pd.crosstab(top_skills_df["skill"], top_skills_df["seniority"])
            .reindex(top_skill_names)
            .fillna(0)
        )

        fig_heatmap = px.imshow(
            cross_tab,
            text_auto=True,
            aspect="auto",
            color_continuous_scale=["#f8fafc", "#e0e7ff", "#6366f1", "#1e1b4b"],
            labels=dict(x="Seniority Level", y="Technology", color="Listings"),
        )
        fig_heatmap.update_layout(height=420)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.warning("No skill tags identified yet.")

# TAB 3: WORKPLACES & VELOCITY
with tab3:
    c_work, c_timeline = st.columns(2)
    with c_work:
        st.subheader("Workplace Policy Breakdown")
        work_counts = df["workplace_type"].value_counts().reset_index()
        work_counts.columns = ["Type", "Count"]
        
        fig_work = px.bar(
            work_counts,
            x="Type",
            y="Count",
            color="Type",
            color_discrete_map=WORKPLACE_COLORS,
        )
        fig_work.update_traces(marker_line_width=0, opacity=0.9)
        fig_work.update_layout(showlegend=False, height=360)
        st.plotly_chart(fig_work, use_container_width=True)

    with c_timeline:
        st.subheader("Ingestion Velocity (Postings Added)")
        time_counts = df.groupby("scraped_date").size().reset_index(name="Volume")
        
        fig_time = px.area(
            time_counts,
            x="scraped_date",
            y="Volume",
            markers=True,
        )
        fig_time.update_traces(
            line_color="#0ea5e9",
            fillcolor="rgba(14, 165, 233, 0.15)",
            marker=dict(size=7, color="#0284c7")
        )
        fig_time.update_layout(xaxis_title="Date", yaxis_title="Records Added", height=360)
        st.plotly_chart(fig_time, use_container_width=True)

# TAB 4: JOB EXPLORER & EXPORT (Languages retained here)
with tab4:
    st.subheader("Interactive Database Search")

    fil1, fil2, fil3, fil4 = st.columns(4)
    with fil1:
        comp_sel = st.multiselect("Filter by Company", options=sorted(df["company"].unique()))
    with fil2:
        sen_sel = st.multiselect("Filter by Seniority", options=sorted(df["seniority"].unique()))
    with fil3:
        work_sel = st.multiselect("Filter by Workplace", options=sorted(df["workplace_type"].unique()))
    with fil4:
        unique_langs = sorted(
            [l for l in df["languages"].str.split(", ").explode().unique() if l and l != "Not Specified"]
        )
        lang_sel = st.multiselect("Filter by Language", options=unique_langs)

    filtered = df.copy()
    if comp_sel:
        filtered = filtered[filtered["company"].isin(comp_sel)]
    if sen_sel:
        filtered = filtered[filtered["seniority"].isin(sen_sel)]
    if work_sel:
        filtered = filtered[filtered["workplace_type"].isin(work_sel)]
    if lang_sel:
        filtered = filtered[filtered["languages"].apply(lambda x: any(l in x for l in lang_sel))]

    st.markdown(f"**Showing {len(filtered)} matching postings**")

    st.dataframe(
        filtered[
            [
                "title",
                "company",
                "location",
                "workplace_type",
                "seniority",
                "skills",
                "languages",
                "url",
                "scraped_at",
            ]
        ],
        column_config={
            "url": st.column_config.LinkColumn("LinkedIn Posting"),
            "scraped_at": st.column_config.DatetimeColumn("Date Ingested", format="YYYY-MM-DD HH:mm"),
        },
        use_container_width=True,
        hide_index=True,
    )

    col_csv, col_json, _ = st.columns([1, 1, 4])
    with col_csv:
        csv_data = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Filtered CSV",
            csv_data,
            "linkedin_data_export.csv",
            "text/csv",
            use_container_width=True,
        )
    with col_json:
        json_data = filtered.to_json(orient="records", indent=2).encode("utf-8")
        st.download_button(
            "📥 Download Filtered JSON",
            json_data,
            "linkedin_data_export.json",
            "application/json",
            use_container_width=True,
        )

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #64748b; font-size: 0.9rem; padding: 15px 0 25px 0;">
        Designed & Built by <a href="https://chamchirabie.com/" target="_blank" style="color: #0284c7; text-decoration: none; font-weight: 600;">Chamchi Rabie</a> • LinkedIn Intelligence Engine
    </div>
""",
    unsafe_allow_html=True,
)