import os
import sys
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

# Ensure src directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator import query_policy_oracle

# 1. Page Configuration & Title
st.set_page_config(
    page_title="Brentwood Policy Oracle",
    page_icon="🏛️",
    layout="wide"
)

# 2. Inject Custom CSS Styles
css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    # Inline fallback stylesheet in case static/style.css is not found
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif !important;
        background-color: #f7f9fc !important;
        color: #1e293b !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Render Header
st.markdown("""
<div class="app-header">
    <h1>🏛️ The Brentwood Policy Oracle</h1>
    <p>A professional, grounded policy query assistant for Brentwood Borough Council housing staff and citizens.</p>
    <span class="badge">Grounded RAG • Powered by Claude 4.5 Sonnet</span>
</div>
""", unsafe_allow_html=True)

# 4. Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_sources" not in st.session_state:
    st.session_state.session_sources = set()

# 5. Sidebar Layout
with st.sidebar:
    st.markdown("## 🏛️ Policy Console")
    st.markdown(
        "Welcome to **The Brentwood Policy Oracle**. This system answers queries "
        "concerning Council Housing Policies using verified documents."
    )
    st.divider()

    st.markdown("### 🔍 Active Policy Sources")
    if st.session_state.session_sources:
        st.markdown("The current session has referenced information from:")
        for source in sorted(st.session_state.session_sources):
            st.markdown(f"📄 **{source}**")
    else:
        st.info("No sources referenced yet. Ask a policy query to retrieve information.")
    
    st.divider()

    # Clear Conversation Action
    if st.button("Clear Conversation History", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.session_sources = set()
        st.rerun()

# 6. Render Chat Messages from History
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🏛️"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        
        # If assistant has citations, render them in an expander
        if message["role"] == "assistant" and message.get("citations"):
            citations = message["citations"]
            num_citations = len(citations)
            with st.expander(f"🔍 Grounded References ({num_citations} source segments)"):
                for idx, citation in enumerate(citations, 1):
                    st.markdown(f"**Reference #{idx}:** `{citation['source_file']}` (Page {citation['page_number']}) — Relevance: {citation['score']:.2f}")
                    st.markdown(f"> *{citation['text'].strip()}*")
                    if idx < num_citations:
                        st.divider()

# 7. Query input & Orchestration Execution
if query_input := st.chat_input("Enter your policy question (e.g., 'What is the policy on pets?')..."):
    # Render user query immediately
    st.session_state.messages.append({"role": "user", "content": query_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(query_input)

    # Process and Query
    with st.chat_message("assistant", avatar="🏛️"):
        status_placeholder = st.empty()
        status_placeholder.markdown("*Searching official policy documents...*")
        
        try:
            # Query the orchestrator
            response = query_policy_oracle(query_input)
            answer = response.get("answer", "No response generated.")
            citations = response.get("citations", [])
            
            # Update sidebar sources
            for cit in citations:
                if cit.get("source_file"):
                    st.session_state.session_sources.add(cit["source_file"])
            
            # Clear searching text
            status_placeholder.empty()
            
            # Render response content
            st.markdown(answer)
            
            # Render citations
            if citations:
                num_citations = len(citations)
                with st.expander(f"🔍 Grounded References ({num_citations} source segments)"):
                    for idx, citation in enumerate(citations, 1):
                        st.markdown(f"**Reference #{idx}:** `{citation['source_file']}` (Page {citation['page_number']}) — Relevance: {citation['score']:.2f}")
                        st.markdown(f"> *{citation['text'].strip()}*")
                        if idx < num_citations:
                            st.divider()
            
            # Save assistant message to session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "citations": citations
            })
            
            # Trigger rerun to update the sidebar dynamic references
            st.rerun()

        except Exception as e:
            status_placeholder.empty()
            error_msg = f"⚠️ An error occurred while retrieving information: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
