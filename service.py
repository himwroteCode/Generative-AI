# laptop_guide/service.py – RAG + Gemini laptop Q&A and config recommendations
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

_load_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_load_env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

LAPTOP_SYSTEM_PROMPT = """You are an expert laptop advisor. You help users in two ways:

1) **Q&A (technical and theoretical)**: Answer any question about laptops clearly and accurately. Topics include:
   - Technical: CPU, GPU, RAM, storage (SSD/HDD/NVMe), display (resolution, refresh rate, panel types), ports, battery life, Intel vs AMD, integrated vs dedicated GPU, etc.
   - Theoretical: how things work, when to upgrade, what matters for different uses (coding, gaming, office, content creation), why battery varies, etc.
   Explain in simple terms when the user seems new to laptops. Be concise and accurate.

2) **Recommendations**: When the user wants buying advice or asks what laptop to get, ask 1–2 clarifying questions if needed (primary use case, budget, portability/screen size). Then suggest a **configuration** (not specific product names): e.g. CPU tier (budget/mid/high), RAM (8/16/32 GB), storage (256/512 GB SSD, NVMe if relevant), display size and resolution, and whether a dedicated GPU is needed. Use this rough budget guide: Budget under $600; Mid $600–1000; High $1000+.

Keep answers focused on laptops. If the question is off-topic, briefly say you're here for laptop help and offer to answer laptop questions."""

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.4,
            google_api_key=GEMINI_API_KEY,
        )
    return _llm


# Marker for LLM to request web search when it lacks enough info (saves Tavily credits)
NEED_WEB_SEARCH_MARKER = "[NEED_WEB_SEARCH]"


def get_laptop_answer(query: str) -> str:
    """
    Answer using RAG when available. If no RAG context, ask the LLM first;
    only call Tavily when the LLM signals it needs more info, to reduce cost.
    """
    if not (query and query.strip()):
        return "Please ask a question about laptops or describe what you need (e.g. use case and budget)."

    from laptop_guide.rag import get_rag_context_only, web_search_context

    q = query.strip()
    context = get_rag_context_only(q)

    if context:
        # We have RAG context: use it and return
        augmented_prompt = (
            "Use the following context to answer the user's question. "
            "If the context does not contain relevant information, say so and answer from general knowledge.\n\n"
            "Context:\n" + context + "\n\n---\n\nUser question: " + q
        )
        llm = _get_llm()
        messages = [
            SystemMessage(content=LAPTOP_SYSTEM_PROMPT),
            HumanMessage(content=augmented_prompt),
        ]
        response = llm.invoke(messages)
        answer = response.content if hasattr(response, "content") else str(response)
        return answer.replace(NEED_WEB_SEARCH_MARKER, "").strip()

    # No RAG: try LLM first; only use Tavily if the model says it falls short
    llm = _get_llm()
    system_with_marker = (
        LAPTOP_SYSTEM_PROMPT
        + "\n\nIf you lack sufficient or up-to-date information to answer the question well, "
        "end your reply with exactly: " + NEED_WEB_SEARCH_MARKER
    )
    messages = [
        SystemMessage(content=system_with_marker),
        HumanMessage(content=q),
    ]
    response = llm.invoke(messages)
    answer = response.content if hasattr(response, "content") else str(response)

    if NEED_WEB_SEARCH_MARKER not in answer:
        return answer.strip()

    # LLM asked for more: call Tavily and re-ask with web context
    web_context = web_search_context(q, max_results=2)
    if not web_context:
        return answer.replace(NEED_WEB_SEARCH_MARKER, "").strip()

    augmented_prompt = (
        "Use the following context to answer the user's question.\n\n"
        "Context:\n" + web_context + "\n\n---\n\nUser question: " + q
    )
    messages = [
        SystemMessage(content=LAPTOP_SYSTEM_PROMPT),
        HumanMessage(content=augmented_prompt),
    ]
    response = llm.invoke(messages)
    final = response.content if hasattr(response, "content") else str(response)
    return final.replace(NEED_WEB_SEARCH_MARKER, "").strip()
