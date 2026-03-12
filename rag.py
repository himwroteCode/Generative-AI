# RAG: Google embeddings, Chroma, retrieval, and web search fallback
import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")

# Config (tuned for free tier: Gemini 100 embed/min, Tavily 1000 credits trial)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR") or str(APP_DIR / "chroma_db")
COLLECTION_NAME = "laptop_guide"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
RETRIEVAL_TOP_K = 3
RELEVANCE_SCORE_THRESHOLD = 0.0  # optional: skip RAG if max score below this
WEB_SEARCH_MAX_RESULTS = 2  # spare Tavily credits (free trial 1000)

_embeddings = None
_vector_store = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=GEMINI_API_KEY,
        )
    return _embeddings


def get_vector_store():
    """Return Chroma vector store (read-only for query path). Creates if missing."""
    global _vector_store
    if _vector_store is None:
        from langchain_chroma import Chroma
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=CHROMA_PERSIST_DIR,
        )
    return _vector_store


def retrieve_context(query: str, top_k: int = RETRIEVAL_TOP_K):
    """
    Retrieve top-k chunks from Chroma for the query.
    Returns (list of document page_content strings, whether we had any results).
    """
    if not (query and query.strip()):
        return [], False
    try:
        store = get_vector_store()
        # similarity_search_with_score if we want threshold; else similarity_search
        docs = store.similarity_search(query.strip(), k=top_k)
    except Exception:
        return [], False
    if not docs:
        return [], False
    texts = [d.page_content for d in docs]
    return texts, True


def web_search_context(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS):
    """
    Fallback: run web search and return concatenated snippets for context.
    Kept low (2 results) to spare Tavily free-trial credits.
    Returns empty string if TAVILY_API_KEY is missing or search fails.
    """
    if not TAVILY_API_KEY or not (query and query.strip()):
        return ""
    try:
        from langchain_community.retrievers import TavilySearchAPIRetriever
        retriever = TavilySearchAPIRetriever(
            api_key=TAVILY_API_KEY,
            k=max_results,
            include_answer=True,
        )
        docs = retriever.invoke(query.strip())
    except Exception:
        return ""
    if not docs:
        return ""
    parts = []
    for d in docs:
        content = getattr(d, "page_content", None) or getattr(d, "content", str(d))
        if content and content.strip():
            parts.append(content.strip())
    return "\n\n".join(parts[:max_results]) if parts else ""


def get_rag_context_only(query: str) -> str:
    """
    Return only RAG (Chroma) context for the query. No web search.
    Use this first; call web_search_context only when the LLM signals it needs more.
    """
    chunks, has_rag = retrieve_context(query, top_k=RETRIEVAL_TOP_K)
    if has_rag and chunks:
        return "\n\n---\n\n".join(chunks)
    return ""


def get_context_for_query(query: str) -> str:
    """
    Returns RAG context only. Tavily is not called here;
    the service layer calls the LLM first and uses web search only if the LLM signals need.
    """
    return get_rag_context_only(query)
