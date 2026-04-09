"""
CU-01 — Azure Service Recommender API (v2)

Backend del agente watsonx Orchestrate que recomienda servicios de Azure.
Tres fases:
  - TRIAGE    : recorrido del árbol de decisión
  - INTERVIEW : cuestionario profundo del servicio candidato
  - HANDOFF   : recomendación estructurada y payload para el siguiente agente

Endpoints adicionales:
  - /node/{id}/match   : fallback semántico para respuestas ambiguas
  - /events            : telemetría fire-and-forget
  - /metadata          : versión del árbol cargado en Cloudant
"""

import logging
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

load_dotenv()

CLOUDANT_URL    = os.environ["CLOUDANT_URL"]
CLOUDANT_APIKEY = os.environ["CLOUDANT_APIKEY"]
DB_NAME         = os.getenv("CLOUDANT_DB", "decision_tree")
API_PUBLIC_URL  = os.getenv("API_PUBLIC_URL", "http://localhost:8080")
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.5"))

METADATA_DOC_ID = "tree_metadata"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cu01")


# Schemas

class RecommendationRequest(BaseModel):
    service_id: str = Field(..., description="_id del nodo result (p. ej. 'result_container_apps').")
    tree_path: List[str] = Field(default_factory=list, description="IDs de los nodos recorridos en orden.")
    deep_dive_answers: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapa question_id -> respuesta del usuario acumulado durante INTERVIEW.",
    )


class Recommendation(BaseModel):
    service: str
    summary: str
    why_factors: List[str] = Field(default_factory=list)
    key_considerations: List[str] = Field(default_factory=list)
    pricing: Dict[str, Any] = Field(default_factory=dict)
    docs_url: Optional[str] = None
    user_context: Dict[str, Any] = Field(default_factory=dict)
    handoff: Dict[str, Any] = Field(default_factory=dict)


class ServiceSummary(BaseModel):
    id: str
    service: str
    summary: str
    docs_url: Optional[str] = None


class ServiceList(BaseModel):
    services: List[ServiceSummary]


class MatchRequest(BaseModel):
    user_answer: str = Field(..., description="Respuesta libre del usuario a una pregunta del árbol.")


class MatchCandidate(BaseModel):
    index: int
    label: str
    next: str
    score: float


class MatchResponse(BaseModel):
    matched: Optional[MatchCandidate] = None
    confidence: float
    strategy: str = Field(..., description="numeric | substring | yesno | keyword | fuzzy | none")
    candidates: List[MatchCandidate]


class EventRequest(BaseModel):
    session_id: str = Field(..., description="ID único de la sesión conversacional.")
    phase: str = Field(..., description="triage | interview | handoff")
    node_id: Optional[str] = None
    user_answer: Optional[str] = None
    matched_option: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class Metadata(BaseModel):
    version: str
    hash: str
    loaded_at: str
    node_count: int
    counts: Dict[str, int]


# Cloudant

@lru_cache(maxsize=1)
def get_cloudant() -> CloudantV1:
    auth = IAMAuthenticator(CLOUDANT_APIKEY)
    client = CloudantV1(authenticator=auth)
    client.set_service_url(CLOUDANT_URL)
    return client


def fetch_node(node_id: str) -> dict:
    """Obtiene un documento por _id. Lanza 404 si no existe."""
    try:
        doc = get_cloudant().get_document(db=DB_NAME, doc_id=node_id).get_result()
    except Exception as e:
        err = str(e)
        if "404" in err or "not_found" in err.lower():
            raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado.")
        raise HTTPException(status_code=500, detail=f"Error conectando a Cloudant: {err}")
    doc.pop("_rev", None)
    return doc


# FastAPI app

app = FastAPI(
    title="CU-01 Azure Service Recommender API",
    description=(
        "Backend del agente watsonx Orchestrate para recomendación de servicios Azure. "
        "Implementa las fases TRIAGE, INTERVIEW y HANDOFF, con fallback semántico para "
        "respuestas ambiguas y telemetría para análisis post-workshop."
    ),
    version="2.0.0",
    servers=[{"url": API_PUBLIC_URL}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Health & metadata

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "version": app.version}


@app.get(
    "/metadata",
    operation_id="get_tree_metadata",
    summary="version_decision_tree",
    description=(
        "Returns version, hash, timestamp and counts from the decision tree loaded in Cloudant. "
        "Helpfull to identify the exact versión active and log which decision tree reponse to each session."
    ),
    response_model=Metadata,
    tags=["meta"],
)
def get_metadata():
    doc = fetch_node(METADATA_DOC_ID)
    return Metadata(
        version=doc.get("version", "unknown"),
        hash=doc.get("hash", ""),
        loaded_at=doc.get("loaded_at", ""),
        node_count=doc.get("node_count", 0),
        counts=doc.get("counts", {}),
    )


# TRIAGE

@app.get(
    "/node/start",
    operation_id="get_decision_tree_start",
    summary="get_start_node",
    description=(
        "Returns the root node of the decision tree. "
        "MANDATORY: Call this at the start of every conversation. "
        "This is part of a deterministic flow. You must not stop until the next node is retrieved."
        "Do not ask the user anything before calling this."
    ),
    tags=["triage"],
)
def get_start_node():
    return fetch_node("node_start")


@app.get(
    "/node/{node_id}",
    operation_id="get_decision_node",
    summary="get_next_node",
    description=(
        "Returns the next node in the decision tree. "
        "MANDATORY: After selecting an option, you MUST call this using the `next` field. "
        "This is the ONLY valid way to continue the flow. "
        "Do not stop. Do not call other tools instead. "
        "Always continue the tree until a deep_dive or result node is reached."
        "This is part of a deterministic flow. You must not stop until the next node is retrieved."
    ),
    tags=["triage"],
)
def get_node(node_id: str):
    return fetch_node(node_id)


# LOOKUP / INTERVIEW

@app.get(
    "/services",
    operation_id="list_services",
    summary="list_services",
    description=(
        "Returns all available Azure services. "
        "Use ONLY if the FIRST user message explicitly names a service. "
        "FORBIDDEN during decision tree traversal. "
        "Do not use after calling the start node."
    ),
    response_model=ServiceList,
    tags=["lookup"],
)
def list_services():
    resp = get_cloudant().post_find(
        db=DB_NAME,
        selector={"type": {"$eq": "result"}},
        fields=["_id", "service", "summary", "docs_url"],
        limit=100,
    ).get_result()
    items = [
        ServiceSummary(
            id=d["_id"],
            service=d.get("service", ""),
            summary=d.get("summary", ""),
            docs_url=d.get("docs_url"),
        )
        for d in resp.get("docs", [])
    ]
    return ServiceList(services=items)


@app.get(
    "/services/{deep_dive_id}/questionnaire",
    operation_id="get_service_questionnaire",
    summary="get_questionnaire",
    description=(
        "Returns the full questionnaire for a service. "
        "Use ONLY in INTERVIEW phase. "
        "Call immediately after reaching a deep_dive node. "
        "Do not use during decision tree traversal."
    ),
    tags=["interview"],
)
def get_questionnaire(deep_dive_id: str):
    node = fetch_node(deep_dive_id)
    if node.get("type") != "deep_dive":
        raise HTTPException(
            status_code=400,
            detail=f"El nodo '{deep_dive_id}' no es un cuestionario (type={node.get('type')}).",
        )
    return node


# HANDOFF

@app.post(
    "/recommendation",
    operation_id="build_recommendation",
    summary="build_recommendation",
    description=(
        "Builds the final recommendation. "
        "Use ONLY after completing the interview. "
        "Call exactly once per conversation. "
        "Do not use during decision tree traversal."
    ),
    response_model=Recommendation,
    tags=["handoff"],
)
def build_recommendation(body: RecommendationRequest):
    result = fetch_node(body.service_id)
    if result.get("type") != "result":
        raise HTTPException(
            status_code=400,
            detail=f"El nodo '{body.service_id}' no es un resultado (type={result.get('type')}).",
        )
    return Recommendation(
        service=result.get("service", ""),
        summary=result.get("summary", ""),
        why_factors=result.get("why_factors", []),
        key_considerations=result.get("key_considerations", []),
        pricing=result.get("pricing", {}),
        docs_url=result.get("docs_url"),
        user_context={
            "tree_path": body.tree_path,
            "deep_dive_answers": body.deep_dive_answers,
        },
        handoff=result.get("handoff", {}),
    )


# Semantic fallback

_AFFIRMATIVE = {
    "si", "sí", "yes", "yeah", "yep", "claro", "correcto", "afirmativo",
    "obvio", "dale", "ok", "okay", "seguro", "absolutamente", "perfecto",
    "cierto", "exacto",
}
_NEGATIVE = {
    "no", "nope", "nada", "jamas", "jamás", "nunca", "negativo", "tampoco",
    "negative", "incorrecto",
}
_STOPWORDS = {
    "el", "la", "los", "las", "de", "en", "un", "una", "unos", "unas",
    "y", "o", "es", "se", "que", "con", "por", "para", "a", "al", "lo",
    "del", "mi", "tu", "su", "este", "esta", "ese", "esa", "me", "te",
    "si", "no", "muy",
}


def _normalize(s: str) -> str:
    """Minúsculas, strip accents, strip puntuación, colapsar espacios."""
    s = s.lower().strip()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _match_option(user_answer: str, options: List[dict]) -> MatchResponse:
    """
    Matchea la respuesta libre del usuario contra las opciones de un nodo question
    usando 4 estrategias en cascada: numeric → substring → yesno → fuzzy.
    """
    ua = _normalize(user_answer)

    # Precalcular todos los candidates con score fuzzy
    candidates: List[MatchCandidate] = []
    for i, opt in enumerate(options):
        score = SequenceMatcher(None, ua, _normalize(opt["label"])).ratio()
        candidates.append(MatchCandidate(
            index=i,
            label=opt["label"],
            next=opt["next"],
            score=round(score, 3),
        ))
    candidates_sorted = sorted(candidates, key=lambda c: c.score, reverse=True)

    if not ua:
        return MatchResponse(
            matched=None, confidence=0.0, strategy="none", candidates=candidates_sorted,
        )

    # Estrategia 1: número explícito ("1", "opcion 2")
    m = re.search(r"\b([1-9])\b", ua)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(options):
            c = candidates[idx]
            matched = MatchCandidate(index=c.index, label=c.label, next=c.next, score=1.0)
            return MatchResponse(
                matched=matched, confidence=1.0, strategy="numeric", candidates=candidates_sorted,
            )

    # Estrategia 2: substring exacto
    for c in candidates:
        label_norm = _normalize(c.label)
        if label_norm and (label_norm in ua or (len(ua) >= 4 and ua in label_norm)):
            matched = MatchCandidate(index=c.index, label=c.label, next=c.next, score=0.95)
            return MatchResponse(
                matched=matched, confidence=0.95, strategy="substring", candidates=candidates_sorted,
            )

    # Estrategia 3: yes/no detection (solo para preguntas de 2 opciones)
    if len(options) == 2:
        words = set(ua.split())
        is_aff = bool(words & _AFFIRMATIVE)
        is_neg = bool(words & _NEGATIVE)
        if is_aff != is_neg:  # exclusivo
            # Por convención del YAML, la opción afirmativa suele empezar con "Si/Sí"
            aff_idx = next(
                (i for i, o in enumerate(options)
                 if _normalize(o["label"]).split(" ")[:1] == ["si"]),
                0,
            )
            neg_idx = 1 - aff_idx
            chosen_idx = aff_idx if is_aff else neg_idx
            c = candidates[chosen_idx]
            matched = MatchCandidate(index=c.index, label=c.label, next=c.next, score=0.85)
            return MatchResponse(
                matched=matched, confidence=0.85, strategy="yesno", candidates=candidates_sorted,
            )

    # Estrategia 4: keyword overlap (respuestas cortas con palabras distintivas)
    # Ejemplo: 'es nueva' matchea 'Si, es una aplicacion nueva' por la keyword 'nueva'
    user_tokens = set(ua.split()) - _STOPWORDS
    if user_tokens:
        best_overlap = (-1, 0.0)
        for i, opt in enumerate(options):
            opt_tokens = set(_normalize(opt["label"]).split()) - _STOPWORDS
            if not opt_tokens:
                continue
            overlap = user_tokens & opt_tokens
            if overlap:
                # Fracción de tokens del usuario presentes en la opción
                ratio = len(overlap) / len(user_tokens)
                if ratio > best_overlap[1]:
                    best_overlap = (i, ratio)
        if best_overlap[0] >= 0 and best_overlap[1] >= 0.5:
            c = candidates[best_overlap[0]]
            score = round(0.70 + best_overlap[1] * 0.20, 2)  # 0.70..0.90
            matched = MatchCandidate(index=c.index, label=c.label, next=c.next, score=score)
            return MatchResponse(
                matched=matched, confidence=score, strategy="keyword", candidates=candidates_sorted,
            )

    # Estrategia 5: fuzzy sobre todos los labels
    best = candidates_sorted[0]
    if best.score >= MATCH_THRESHOLD:
        return MatchResponse(
            matched=best, confidence=best.score, strategy="fuzzy", candidates=candidates_sorted,
        )

    # Sin match confiable → el agente debe re-preguntar
    return MatchResponse(
        matched=None, confidence=best.score, strategy="none", candidates=candidates_sorted,
    )


@app.post(
    "/node/{node_id}/match",
    operation_id="match_user_answer",
    summary="match_user_answer",
    description=(
        "Matches a free-text answer to one of the available options. "
        "Use ONLY if the answer does not clearly match a number or label. "
        "MANDATORY: After this call, you MUST immediately call the next node using matched.next. "
        "Do not stop. Do not ask the user yet. Continue the flow."
    ),
    response_model=MatchResponse,
    tags=["triage"],
)
def match_answer(node_id: str, body: MatchRequest):
    node = fetch_node(node_id)
    if node.get("type") != "question":
        raise HTTPException(
            status_code=400,
            detail=f"El nodo '{node_id}' no es de tipo question (type={node.get('type')}).",
        )
    options = node.get("options", [])
    if not options:
        raise HTTPException(status_code=400, detail=f"El nodo '{node_id}' no tiene opciones.")
    return _match_option(body.user_answer, options)


# Telemetry (fire-and-forget)

@app.post(
    "/events",
    operation_id="log_event",
    summary="log_conversation_event",
    description=(
        "Logs a conversation step for analytics. "
        "This is fire-and-forget. "
        "MANDATORY: This must be the LAST action in the step. "
        "Call this only AFTER all other tool calls are completed. "
        "Never call this before getting the next node."
    ),
    status_code=status.HTTP_202_ACCEPTED,
    tags=["telemetry"],
)
def log_event(body: EventRequest):
    event_id = str(uuid.uuid4())
    doc = {
        "_id": f"event_{event_id}",
        "type": "event",
        "event_id": event_id,
        "session_id": body.session_id,
        "phase": body.phase,
        "node_id": body.node_id,
        "user_answer": body.user_answer,
        "matched_option": body.matched_option,
        "extra": body.extra,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        get_cloudant().post_document(db=DB_NAME, document=doc).get_result()
    except Exception as e:
        logger.warning(f"Event log failed (non-fatal) for session {body.session_id}: {e}")
    return {"accepted": True, "event_id": event_id}
