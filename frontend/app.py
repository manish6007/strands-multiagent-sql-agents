import os
import requests
import streamlit as st
import pandas as pd
import json
import plotly.io as pio

# Page configuration
st.set_page_config(
    page_title="Text-to-SQL Multi-Agent Analytics Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS styling loading Outfit fonts
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}
.metric-card {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}
.agent-step {
    border-left: 3px solid #6366F1;
    background-color: #0F172A;
    padding: 12px;
    margin-bottom: 10px;
    border-radius: 0 8px 8px 0;
}
.chat-bubble-user {
    background-color: #1E1B4B;
    border: 1px solid #4338CA;
    padding: 12px 16px;
    border-radius: 16px 16px 4px 16px;
    margin-bottom: 12px;
    max-width: 80%;
    margin-left: auto;
}
.chat-bubble-assistant {
    background-color: #1E293B;
    border: 1px solid #334155;
    padding: 12px 16px;
    border-radius: 16px 16px 16px 4px;
    margin-bottom: 12px;
    max-width: 80%;
}
</style>
""", unsafe_allow_html=True)

# Config backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# Init Session States
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# Title Banner
st.markdown("<h1 style='text-align: center; color: #FFFFFF;'>🤖 Enterprise Text-to-SQL Analytics Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 1.1rem;'>Ask questions of your Amazon Athena Data Lake in plain English</p>", unsafe_allow_html=True)
st.markdown("---")

# 1. SIDEBAR CONFIGURATION
with st.sidebar:
    st.image("https://img.icons8.com/color/144/database.png", width=70)
    st.markdown("### Settings & Controls")
    
    # Model Selection
    model_id = st.selectbox(
        "Bedrock Base Model",
        options=[
            "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "amazon.nova-pro-v1:0",
            "anthropic.claude-3-opus-20240229-v1:0"
        ],
        index=0
    )
    
    # Login Panel (Optional depending on backend settings)
    auth_enabled = st.checkbox("Enable Security JWT Authentication", value=False)
    if auth_enabled:
        st.markdown("---")
        st.markdown("#### Login Credentials")
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="admin123")
        
        if st.button("Authenticate Token", use_container_width=True):
            try:
                res = requests.post(f"{BACKEND_URL}/api/v1/login", json={"username": username, "password": password})
                if res.status_code == 200:
                    token_data = res.json()
                    st.session_state.token = token_data["access_token"]
                    st.session_state.role = token_data["role"]
                    st.success(f"Authenticated as {st.session_state.role}!")
                else:
                    st.error("Login failed. Check credentials.")
            except Exception as e:
                st.error(f"Cannot connect to backend: {e}")
                
        if st.session_state.token:
            st.info(f"Role Level: **{st.session_state.role}**")
            if st.button("Logout", use_container_width=True):
                st.session_state.token = None
                st.session_state.role = None
                st.info("Logged out.")
    
    st.markdown("---")
    st.markdown("### Ingest Knowledge base")
    st.write("Chunk and upload definitions into pgvector database:")
    
    # Ingestion Trigger Button
    if st.button("🚀 Trigger Ingestion Pipeline", use_container_width=True):
        headers = {}
        if auth_enabled and st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
            
        with st.spinner("Ingesting and embedding glossary docs..."):
            try:
                res = requests.post(f"{BACKEND_URL}/api/v1/ingest", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    st.success(f"Ingested {len(data['documents_ingested'])} glossary documents!")
                else:
                    st.error(f"Failed ingestion: {res.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Ingestion failed: {e}")

# MAIN LAYOUT PANELS
col_metrics, col_schema = st.columns([3, 1])

# Fetch Schema from backend
schema_tables = []
try:
    schema_res = requests.get(f"{BACKEND_URL}/api/v1/schema")
    if schema_res.status_code == 200:
        schema_tables = schema_res.json().get("tables", [])
except Exception:
    pass

with col_schema:
    st.markdown("### Schema Dictionary")
    if schema_tables:
        for t in schema_tables:
            with st.expander(f"📋 table: {t['name']}"):
                cols_df = pd.DataFrame(t["columns"])
                st.dataframe(cols_df, hide_index=True)
    else:
        st.info("Could not fetch schema from database API.")

with col_metrics:
    # Query input
    st.markdown("### Ask a Question")
    user_query = st.text_input(
        "Ask about sales growth, customer churn, regional revenue, top orders...",
        placeholder="e.g. Show monthly revenue growth for the last 12 months"
    )
    
    submit_btn = st.button("Generate Analytics insights", type="primary", use_container_width=True)

    if submit_btn and user_query:
        # Prepare Headers
        headers = {}
        if auth_enabled and st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
            
        payload = {
            "question": user_query,
            "session_id": st.session_state.session_id
        }
        
        with st.spinner("Multi-Agent reasoning in progress... Involving Supervisor, RAG, SQL Gen, SQL Review, and Execution agents."):
            # Add to chat history
            st.session_state.chat_history.append({"role": "user", "text": user_query})
            
            try:
                # Set environment variables overrides dynamically if needed
                os.environ["BEDROCK_MODEL_ID"] = model_id
                
                res = requests.post(f"{BACKEND_URL}/api/v1/query", json=payload, headers=headers)
                
                if res.status_code == 200:
                    response_data = res.json()
                    st.session_state.chat_history.append({"role": "assistant", "data": response_data})
                else:
                    st.error(f"Error {res.status_code}: {res.json().get('detail', 'System Execution failure')}")
            except Exception as e:
                st.error(f"Failed to query backend server: {e}")

    # RENDER THE LATEST RESULT OR HISTORY
    if st.session_state.chat_history:
        # Get the last assistant message
        last_resp = None
        for item in reversed(st.session_state.chat_history):
            if item["role"] == "assistant":
                last_resp = item["data"]
                break
                
        if last_resp:
            # 1. METRIC COUNTERS
            metrics = last_resp.get("metrics", {})
            st.markdown("#### Performance & Cost Tracking")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='metric-card'><h4>Execution Latency</h4><h2 style='color:#10B981;'>{metrics.get('latency_ms', 0):,.2f} ms</h2></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'><h4>Bedrock Call Cost</h4><h2 style='color:#6366F1;'>${metrics.get('cost_usd', 0.0):,.6f}</h2></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='metric-card'><h4>Bedrock Tokens</h4><h2 style='color:#F59E0B;'>{metrics.get('tokens', 0):,}</h2></div>", unsafe_allow_html=True)
            
            st.write("")
            
            # 2. OUTPUT TABS
            tab_summary, tab_chart, tab_sql, tab_data, tab_trace = st.tabs([
                "📄 Executive Report", 
                "📊 Interactive Chart", 
                "💻 SQL Query", 
                "💾 Query Result Data", 
                "🕵️ Agent Execution Trace"
            ])
            
            with tab_summary:
                st.markdown(last_resp.get("summary", ""))
                
            with tab_chart:
                chart_info = last_resp.get("chart", {})
                if chart_info and chart_info.get("fig_json") != "{}":
                    fig = pio.from_json(chart_info.get("fig_json"))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No visualization available for this query.")
                    
            with tab_sql:
                st.code(last_resp.get("sql", "No SQL generated"), language="sql")
                
            with tab_data:
                records = last_resp.get("records", [])
                if records:
                    res_df = pd.DataFrame(records)
                    st.dataframe(res_df, use_container_width=True)
                else:
                    st.info("No tabular data returned.")
                    
            with tab_trace:
                st.markdown("#### Agent Execution Steps & Telemetry")
                traces = last_resp.get("traces", [])
                for t in traces:
                    with st.expander(f"🔹 {t.get('agent')} - {t.get('step')} ({t.get('latency_ms')} ms)"):
                        st.json({
                            "agent": t.get("agent"),
                            "step": t.get("step"),
                            "status": t.get("status"),
                            "latency_ms": t.get("latency_ms"),
                            "tokens": t.get("tokens"),
                            "cost": t.get("cost"),
                            "input_payload": t.get("input"),
                            "output_payload": t.get("output")
                        })
