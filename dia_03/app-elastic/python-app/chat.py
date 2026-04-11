import os
import logging
import streamlit as st
from ibm_watson_machine_learning.foundation_models import Model as IBMModel
from elasticsearch import Elasticsearch

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

# ── Config from env ───────────────────────────────────────────────────────────
api_key    = os.getenv("API_KEY")
api_url    = os.getenv("API_URL")
es_host    = os.getenv("ELASTIC_HOST")
es_username= os.getenv("ELASTIC_USERNAME")
es_password= os.getenv("ELASTIC_PASSWORD")
es_index   = os.getenv("ELASTIC_INDEX", "search-cisco-catalyst-v2")
project_id = os.getenv("PROJECT_ID")

# ── Constants ─────────────────────────────────────────────────────────────────
ELSER_FIELD   = "ml.inference.title_expanded"
ELSER_MODEL   = ".elser_model_2_linux-x86_64"
LLM_MODEL     = "meta-llama/llama-3-3-70b-instruct"
CONTEXT_TOKENS = 400   # max tokens from ES body_content sent to LLM
MAX_NEW_TOKENS = 768   # max tokens LLM generates
ES_RESULTS     = 3     # number of ES hits to use as context

# ── Elasticsearch ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_es_client():
    return Elasticsearch(
        es_host,
        basic_auth=(es_username, es_password),
        ca_certs="/tmp/certs/ca.crt",
        request_timeout=30,
    )


import json
import re

def truncate_text(text: str, max_tokens: int) -> str:
    if not text:
        return ""
    tokens = text.split()
    return " ".join(tokens[:max_tokens])


def clean_body(body: str) -> str:
    """
    El body_content de los crawlers Cisco viene como JSON crudo.
    Intentamos parsearlo y extraer campos legibles; si no es JSON lo usamos tal cual.
    """
    if not body:
        return ""
    try:
        data = json.loads(body)
        parts = []
        # Campos útiles del JSON de Cisco DevNet / Meraki
        for key in ("title", "summary", "description", "content", "text",
                    "overview", "details", "body", "introduction"):
            val = data.get(key) or data.get("spec", {}).get(key, "")
            if val and isinstance(val, str):
                parts.append(val)
        # Si tiene spec.description (patrón Meraki API)
        spec = data.get("spec", {})
        if isinstance(spec, dict):
            if spec.get("summary"):
                parts.append(f"Summary: {spec['summary']}")
            if spec.get("description"):
                parts.append(f"Description: {spec['description']}")
        result = " ".join(parts) if parts else body
    except (json.JSONDecodeError, TypeError):
        result = body

    # Limpiar tags HTML residuales y espacios extra
    result = re.sub(r"<[^>]+>", " ", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def search(query_text: str):
    """Run ELSER semantic search and return (context, urls, titles)."""
    es = get_es_client()
    query = {
        "text_expansion": {
            ELSER_FIELD: {
                "model_id": ELSER_MODEL,
                "model_text": query_text,
            }
        }
    }
    try:
        resp = es.search(
            index=es_index,
            query=query,
            fields=["title", "body_content", "url"],
            size=ES_RESULTS,
            source=False,
        )
        hits = resp["hits"]["hits"]
        if not hits:
            return None, None, None

        context_parts = []
        urls   = []
        titles = []
        tokens_per_doc = CONTEXT_TOKENS // ES_RESULTS

        for hit in hits:
            f     = hit.get("fields", {})
            title = f.get("title", [""])[0]
            body  = f.get("body_content", [""])[0]
            url   = f.get("url", [""])[0]
            titles.append(title)
            urls.append(url)
            cleaned = clean_body(body)
            excerpt = truncate_text(cleaned, tokens_per_doc)
            context_parts.append(f"Source: {title}\n{excerpt}")
            logging.info(f"Context excerpt [{title}]: {excerpt[:120]}...")

        context = "\n\n---\n\n".join(context_parts)
        return context, urls, titles

    except Exception as e:
        logging.error(f"Elasticsearch error: {e}")
        return None, None, None


# ── LLM ───────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_llm():
    credentials = {"url": api_url, "apikey": api_key}
    gen_parms = {
        "decoding_method": "greedy",   # greedy = más rápido y determinístico
        "max_new_tokens": MAX_NEW_TOKENS,
        "min_new_tokens": 10,
        "repetition_penalty": 1.1,
        "stop_sequences": ["User:", "###"],
    }
    return IBMModel(LLM_MODEL, credentials, gen_parms, project_id, None, False)


def build_prompt(context: str, question: str) -> str:
    return (
        "You are a helpful technical assistant specialized in Cisco networking and APIs.\n"
        "Use the context below to answer the question. If the context is relevant but incomplete, "
        "complement with your general Cisco knowledge.\n"
        "Format your response in Markdown. Show commands and code in code blocks.\n"
        'If the context is completely unrelated, say "I could not find specific documentation for that."\n\n'
        f"### Context\n{context}\n\n"
        f"### Question\n{question}\n\n"
        "### Answer\n"
    )


def ask_llm(prompt: str) -> str:
    llm = get_llm()
    result = llm.generate(prompt)
    return result["results"][0]["generated_text"].strip()


# ── Streamlit UI ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Cisco AI Assistant", page_icon="🌐", layout="centered")
st.title("🌐 Cisco AI Assistant")
st.caption("Powered by IBM watsonx + Elasticsearch ELSER | Cisco Catalyst documentation")

# Chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# New user input
if query := st.chat_input("Ask me anything about Cisco Catalyst..."):

    # Show user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching documentation..."):
            context, top_url, titles = search(query)

        if context is None:
            answer = "I could not find relevant documentation for your question."
            st.markdown(answer)
        else:
            prompt = build_prompt(context, query)
            with st.spinner("Generating answer..."):
                answer = ask_llm(prompt)
            st.markdown(answer)

            # Show sources
            if titles and top_url:
                with st.expander("📚 Sources"):
                    for i, (t, u) in enumerate(zip(titles, top_url), 1):
                        st.markdown(f"{i}. [{t}]({u})")

    st.session_state.messages.append({"role": "assistant", "content": answer})
