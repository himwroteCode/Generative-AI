# Laptop Guide (RAG + Gemini)

Laptop Q&A and buying advice using RAG (Chroma + Google embeddings) with web search fallback when the index has no relevant results.

## Setup

1. **Install dependencies** (from the Django project root that contains this app):
   ```bash
   pip install -r laptop_guide/requirements.txt
   ```
   Or merge `laptop_guide/requirements.txt` into your project’s `requirements.txt`.

2. **Environment**  
   Copy `.env.example` to `.env` (in the project root or where your app loads it) and set:
   - `GEMINI_API_KEY` – for chat and embeddings
   - `TAVILY_API_KEY` – for web search fallback when RAG has no data

3. **Build the RAG index** (crawl laptop buying guide URLs and build Chroma):
   ```bash
   python manage.py build_laptop_rag
   ```
   Seed URLs are in `laptop_guide/config/seed_urls.txt`. Edit that file to add or remove URLs, then run the command again to refresh the index.

## Flow

- **Query**: (1) Retrieve top chunks from Chroma. If we have context → send it + question to Gemini → return answer. (2) If no RAG context → ask Gemini from its own knowledge first; only if the model signals it needs more (appends `[NEED_WEB_SEARCH]`) do we call Tavily and re-ask with web context. This keeps Tavily usage low.
- **Index**: `build_laptop_rag` crawls the seed URLs, chunks the text, embeds with Google, and stores in Chroma under `laptop_guide/chroma_db` (or `CHROMA_PERSIST_DIR`).

## Free tier (POC)

Tuned for learning / POC with free limits:

- **Gemini**: 100 embed requests per minute. The index build batches embeddings (50 chunks per batch, 35s delay) so `build_laptop_rag` stays under the limit. Larger chunks (1200 chars) and 4 seed URLs keep total chunks low.
- **Tavily**: Free trial has limited credits (e.g. 1000). Web search is used only when the LLM signals it lacks enough info (so most queries use RAG or LLM knowledge only). When used, **2 results per query**. Edit `WEB_SEARCH_MAX_RESULTS` in `rag.py` if needed.
- To add more seed URLs, uncomment lines in `config/seed_urls.txt`; the build will take longer due to rate limiting.

## Optional

- Set `CHROMA_PERSIST_DIR` in `.env` to change where the Chroma DB is stored.
