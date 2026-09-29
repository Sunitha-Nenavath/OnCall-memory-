"""
OnCallMemory Streamlit Web Application.
Interactive UI for Incident Response Agent powered by Hindsight Persistent Memory.
Supports side-by-side comparison, memory panel inspection, resolution feedback retention,
and recurring pattern reflection.
"""

import os
import sys
import json
import time
import requests
import streamlit as st
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import settings
from backend.agent import agent
from backend.schemas import DiagnosisResult, CompareAnalysisResponse
from backend.memory import memory_engine
from data.seed_memory import seed_memory

# Page Configuration
st.set_page_config(
    page_title="OnCallMemory | Hindsight AI Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design & High Visual Impact
st.markdown("""
<style>
    /* Dark glassmorphism & accent themes */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    .main-header {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.4rem;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .badge-off {
        background-color: #f43f5e;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-on {
        background-color: #10b981;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .citation-box {
        background-color: rgba(56, 189, 248, 0.1);
        border-left: 4px solid #38bdf8;
        padding: 10px 14px;
        border-radius: 4px;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    .memory-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .telemetry-log {
        font-family: 'Courier New', monospace;
        background-color: #0f172a;
        color: #38bdf8;
        padding: 10px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "alert_input" not in st.session_state:
    st.session_state.alert_input = ""
if "service_input" not in st.session_state:
    st.session_state.service_input = "checkout-api"
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None
if "compare_analysis" not in st.session_state:
    st.session_state.compare_analysis = None


# Load Demo Alerts
def load_demo_alerts():
    demo_file = ROOT_DIR / "data" / "demo_alerts.json"
    if demo_file.exists():
        with open(demo_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


demo_alerts = load_demo_alerts()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/server.png", width=60)
    st.markdown("### OnCallMemory Control Panel")
    st.caption("Powered by Vectorize Hindsight Persistent Memory Engine")

    st.divider()

    # Memory ON/OFF Toggle
    memory_enabled = st.toggle("🧠 Hindsight Memory Layer", value=True, help="Enable or Disable persistent memory retrieval")
    
    if memory_enabled:
        is_conn, conn_msg = memory_engine.check_hindsight_connectivity()
        if is_conn:
            st.markdown("<span class='badge-on'>🟢 HINDSIGHT CONNECTED</span>", unsafe_allow_html=True)
            st.caption(f"Cloud API: `{settings.HINDSIGHT_BASE_URL}`")
        else:
            st.markdown("<span class='badge-off'>🔴 HINDSIGHT UNAVAILABLE</span>", unsafe_allow_html=True)
            st.caption("🟡 Local Fallback Mode Active")
    else:
        st.markdown("<span class='badge-off'>⚪ MEMORY BYPASSED (OFF)</span>", unsafe_allow_html=True)

    st.divider()

    # Team / Memory Bank Selector
    bank_id = st.selectbox(
        "Select Memory Bank (Team)",
        options=["oncall-incidents-team-alpha", "payments-team-beta", "infra-team-gamma"],
        index=0,
        help="One Hindsight memory bank per engineering team"
    )

    # Memory Stats Counter
    incident_count = memory_engine.get_memory_stats(bank_id)
    st.markdown(f"""
    <div class='metric-card'>
        <div style='font-size: 0.85rem; color: #94a3b8;'>Hindsight Stored Memories</div>
        <div style='font-size: 2rem; font-weight: 700; color: #38bdf8;'>{incident_count} Incidents</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # Seed Memory Button
    if st.button("🌱 Seed Hindsight Memory", use_container_width=True, help="Populates memory bank with 30 synthetic incidents from data/incidents.json"):
        with st.spinner("Seeding incidents into Hindsight memory..."):
            res = seed_memory(bank_id=bank_id)
            if res.get("status") in ["success", "completed"]:
                st.success(f"Retained {res.get('retained_count', 30)} incidents into '{bank_id}'!")
            else:
                st.warning(f"Memory initialized with local fallback ({res.get('errors', 0)} server errors logged).")
            st.rerun()

    st.divider()

    # How it Works Expander
    with st.expander("📖 How Hindsight Memory Works"):
        st.markdown("""
        **Biomimetic Memory Architecture**:
        1. **Retain (`client.retain`)**: When an incident is resolved, symptoms, root cause, fix steps, and outcome feedback are indexed into Hindsight.
        2. **Recall (`client.recall`)**: On incoming alerts, semantic and temporal search pulls the top matching past incidents.
        3. **Reflect (`client.reflect`)**: Synthesizes reasoning across memories to answer pattern questions (e.g. Friday deploy risks).
        """)


# --- MAIN INTERFACE ---
st.markdown("<div class='main-header'>⚡ OnCallMemory Agent</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Persistent Memory Incident Response for On-Call SREs — Grounded in past resolution history.</div>", unsafe_allow_html=True)

# Tabs Navigation
tab_triage, tab_compare, tab_patterns, tab_logs = st.tabs([
    "🚨 Alert Triage",
    "⚖️ Side-by-Side Comparison",
    "📊 Incident Patterns (Reflect)",
    "📡 Hindsight Call Logs"
])


# --- TAB 1: ALERT TRIAGE ---
with tab_triage:
    st.subheader("1. Incoming Production Alert")
    
    # Quick Load Scripted Demo Alerts
    st.caption("Load a pre-scripted demo alert to test semantic memory recall:")
    d_col1, d_col2, d_col3 = st.columns(3)
    
    if demo_alerts and len(demo_alerts) >= 3:
        if d_col1.button("📌 Demo 1: Checkout Latency (Connection Pool)", use_container_width=True):
            st.session_state.alert_input = demo_alerts[0]["alert_text"]
            st.session_state.service_input = demo_alerts[0]["service"]
        if d_col2.button("💥 Demo 2: Payments OOMKilled Pod", use_container_width=True):
            st.session_state.alert_input = demo_alerts[1]["alert_text"]
            st.session_state.service_input = demo_alerts[1]["service"]
        if d_col3.button("❓ Demo 3: New Corrupted GeoIP Alert", use_container_width=True):
            st.session_state.alert_input = demo_alerts[2]["alert_text"]
            st.session_state.service_input = demo_alerts[2]["service"]

    # Input form
    col_svc, col_blank = st.columns([1, 2])
    service_name = col_svc.text_input("Affected Service Name", value=st.session_state.service_input)
    
    alert_text = st.text_area(
        "Paste Alert Body / Log Output / Metrics",
        value=st.session_state.alert_input,
        height=140,
        placeholder="Paste incident alert description, stack trace, or log metrics here..."
    )

    col_btn, col_chk = st.columns([1, 2])
    analyze_click = col_btn.button("🔍 Diagnose Alert", type="primary", use_container_width=True)

    if analyze_click and alert_text.strip():
        with st.spinner("Querying Hindsight memory & generating diagnosis..."):
            start_t = time.time()
            res = agent.analyze_alert(
                alert_text=alert_text,
                service=service_name,
                bank_id=bank_id,
                memory_on=memory_enabled
            )
            st.session_state.last_analysis = res

    # Render Diagnosis Results
    if st.session_state.last_analysis:
        res: DiagnosisResult = st.session_state.last_analysis
        st.divider()

        st.subheader("2. Agent Diagnosis & Remediation Plan")
        
        mode_badge = "<span class='badge-on'>MEMORY GROUNDED</span>" if res.memory_enabled else "<span class='badge-off'>UNGROUNDED (MEMORY OFF)</span>"
        st.markdown(f"**Agent Status**: {mode_badge} | **Confidence**: `{int(res.confidence * 100)}%`", unsafe_allow_html=True)

        col_res1, col_res2 = st.columns([2, 1])

        with col_res1:
            st.markdown("#### 🎯 Likely Root Cause")
            st.error(res.likely_root_cause)

            st.markdown("#### 🛠️ Ordered Remediation Steps")
            for idx, step in enumerate(res.remediation_steps, start=1):
                st.markdown(f"**{idx}.** {step}")

            if res.citations:
                st.markdown("#### 📌 Citations to Past Incidents")
                for cit in res.citations:
                    st.markdown(f"""
                    <div class='citation-box'>
                        <strong>Based on incident #{cit.incident_id}</strong> ({cit.date})<br/>
                        <em>Reason</em>: {cit.reason}
                    </div>
                    """, unsafe_allow_html=True)
            elif res.memory_enabled:
                st.info("ℹ️ No past incidents matched this alert with sufficient confidence. Showing general recommendations.")

        with col_res2:
            st.markdown("#### 🧠 Recalled Hindsight Memories")
            if res.recalled_memories:
                for mem in res.recalled_memories:
                    st.markdown(f"""
                    <div class='memory-card'>
                        <strong>#{mem.incident_id}</strong> - {mem.service} <span style='float:right; color:#38bdf8;'>Similarity: {mem.similarity_score}</span><br/>
                        <small style='color:#94a3b8;'>Date: {mem.timestamp}</small><br/>
                        <div style='margin-top:6px; font-size:0.85rem;'><strong>Past Root Cause:</strong> {mem.root_cause[:120]}...</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("No memories recalled for this query.")

            if res.hindsight_log:
                st.markdown("#### 📡 Hindsight Call Telemetry")
                log = res.hindsight_log
                st.markdown(f"""
                <div class='telemetry-log'>
                    OP: {log.operation.upper()}<br/>
                    BANK: {log.bank_id}<br/>
                    RESULTS: {log.num_results}<br/>
                    LATENCY: {log.latency_ms} ms<br/>
                    STATUS: {log.status}
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # --- RESOLVE INCIDENT FORM ---
        st.subheader("3. Resolve & Retain into Hindsight Memory")
        st.caption("Once triage is complete, confirm resolution to update the agent's persistent memory bank.")

        with st.form("resolve_form"):
            r_col1, r_col2 = st.columns(2)
            root_cause_input = r_col1.text_input("Actual Confirmed Root Cause", value=res.likely_root_cause)
            engineer_input = r_col2.text_input("On-Call Engineer", value="Elena Rostova (Primary)")

            fix_input = st.text_area("Remediation Steps Taken (one per line)", value="\n".join(res.remediation_steps))
            
            f_col1, f_col2 = st.columns(2)
            worked_choice = f_col1.radio("Did the Agent's Suggested Fix Work?", ["Yes - Worked Effectively", "No - Needed Alternative Fix"], index=0)
            resolution_time = f_col2.number_input("Time to Resolve (Minutes)", min_value=5, max_value=480, value=25)

            submit_resolve = st.form_submit_button("✅ Retain Incident into Memory", type="primary", use_container_width=True)

            if submit_resolve:
                worked_bool = "Yes" in worked_choice
                incident_payload = {
                    "service": service_name,
                    "severity": "SEV2",
                    "alert_text": alert_text,
                    "root_cause": root_cause_input,
                    "fix_steps": [s.strip() for s in fix_input.split("\n") if s.strip()],
                    "runbook_used": "https://runbooks.internal/triage",
                    "engineer_name": engineer_input,
                    "time_to_resolve_minutes": int(resolution_time),
                    "postmortem_note": f"Resolution confirmed by {engineer_input}."
                }
                
                log_ret = memory_engine.retain_incident(
                    bank_id=bank_id,
                    incident=incident_payload,
                    worked=worked_bool
                )
                
                st.success(f"🎉 Incident retained in Hindsight memory! Stored count updated to {memory_engine.get_memory_stats(bank_id)}.")
                st.toast("Memory updated successfully!", icon="🧠")
                time.sleep(1)
                st.rerun()


# --- TAB 2: SIDE-BY-SIDE COMPARISON MODE ---
with tab_compare:
    st.subheader("Side-by-Side Evaluation: Memory OFF vs Memory ON")
    st.caption("Demonstrates the exact difference between generic AI advice (Memory OFF) and grounded Hindsight memory recall (Memory ON).")

    comp_alert = st.text_area(
        "Alert Payload to Compare",
        value=st.session_state.alert_input or (demo_alerts[0]["alert_text"] if demo_alerts else ""),
        height=100
    )

    if st.button("⚖️ Run Side-by-Side Comparison", type="primary"):
        with st.spinner("Running dual evaluation (Memory OFF vs Memory ON)..."):
            comp_res = agent.compare_alert(
                alert_text=comp_alert,
                service=st.session_state.service_input,
                bank_id=bank_id
            )
            st.session_state.compare_analysis = comp_res

    if st.session_state.compare_analysis:
        comp: CompareAnalysisResponse = st.session_state.compare_analysis
        
        c_off, c_on = st.columns(2)

        with c_off:
            st.markdown("### 🔴 Memory OFF (Generic AI Advice)")
            st.markdown("<span class='badge-off'>UNGROUNDED</span>", unsafe_allow_html=True)
            st.write("")
            st.markdown("**Root Cause Hypothesis:**")
            st.warning(comp.memory_off.likely_root_cause)

            st.markdown("**Suggested Steps:**")
            for idx, s in enumerate(comp.memory_off.remediation_steps, 1):
                st.markdown(f"{idx}. {s}")

            st.markdown("**Citations:** None (0 past incidents cited)")
            st.caption("Notice: Generic, high-level advice without specific corporate runbook context.")

        with c_on:
            st.markdown("### 🟢 Memory ON (Hindsight Memory Grounded)")
            st.markdown("<span class='badge-on'>GROUNDED IN HINDSIGHT</span>", unsafe_allow_html=True)
            st.write("")
            st.markdown("**Root Cause Hypothesis:**")
            st.success(comp.memory_on.likely_root_cause)

            st.markdown("**Suggested Steps:**")
            for idx, s in enumerate(comp.memory_on.remediation_steps, 1):
                st.markdown(f"{idx}. {s}")

            st.markdown("**Citations:**")
            if comp.memory_on.citations:
                for cit in comp.memory_on.citations:
                    st.markdown(f"📌 **Based on incident #{cit.incident_id}** ({cit.date}): {cit.reason}")
            else:
                st.write("No matching past incidents found.")

            st.caption("Notice: Cites the exact past incident, root cause, and verified fix steps.")


# --- TAB 3: PATTERNS (REFLECT) ---
with tab_patterns:
    st.subheader("Hindsight Reflect: Recurring Incident Pattern Analytics")
    st.caption("Asks Hindsight memory engine to reason across all stored incident memories to spot system vulnerabilities.")

    pattern_query = st.text_input(
        "Reflection Question",
        value="What are the most frequent root causes and risky deployment patterns across past incidents?"
    )

    if st.button("🔍 Run Hindsight Reflect Analysis", type="primary"):
        with st.spinner("Hindsight reasoning across memory bank..."):
            insights, based_on, call_log = memory_engine.reflect_patterns(
                bank_id=bank_id,
                query=pattern_query
            )
            
            st.markdown("### 📈 Reflect Synthesis Report")
            st.markdown(insights)

            if based_on:
                st.markdown("#### Memories Analyzed in Reflection")
                st.json(based_on)

            if call_log:
                st.caption(f"Reflect Execution Latency: {call_log.latency_ms} ms | Status: {call_log.status}")


# --- TAB 4: HINDSIGHT CALL LOGS ---
with tab_logs:
    st.subheader("Hindsight API Execution Telemetry")
    st.caption("Real-time telemetry log of all Hindsight Retain, Recall, and Reflect operations.")

    logs = memory_engine.call_logs
    if logs:
        for l in reversed(logs):
            op_color = "#10b981" if l.operation == "retain" else ("#38bdf8" if l.operation == "recall" else "#c084fc")
            if l.status == "success":
                status_badge = "<span style='color:#10b981; font-weight:600;'>🟢 SUCCESS (HINDSIGHT CLOUD)</span>"
            elif "fallback" in l.status.lower():
                status_badge = f"<span style='color:#f59e0b; font-weight:600;'>🟡 LOCAL FALLBACK ({l.status})</span>"
            else:
                status_badge = f"<span style='color:#f43f5e; font-weight:600;'>🔴 FAILED ({l.status})</span>"

            st.markdown(f"""
            <div class='memory-card'>
                <span style='background-color:{op_color}; color:black; padding:2px 8px; border-radius:4px; font-weight:bold;'>{l.operation.upper()}</span>
                <strong style='margin-left:10px;'>Bank: {l.bank_id}</strong>
                <span style='float:right;'>Latency: <strong>{l.latency_ms} ms</strong> | {status_badge}</span>
                <div style='margin-top:6px; font-family:monospace; color:#cbd5e1;'>Query/Content: {l.query_or_content}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No Hindsight API calls logged yet in this session.")
