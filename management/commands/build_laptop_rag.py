# Django management command: crawl laptop buying guide URLs and build Chroma RAG index
# Free-tier: batches embeddings with delay to stay under Gemini 100 embed/min
import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand

# App dir (laptop_guide)
APP_DIR = Path(__file__).resolve().parent.parent.parent
SEED_URLS_FILE = APP_DIR / "config" / "seed_urls.txt"

# Stay under Gemini free tier: 100 embed requests per minute
EMBED_BATCH_SIZE = 50
EMBED_DELAY_SECONDS = 35


def load_seed_urls():
    urls = []
    if not SEED_URLS_FILE.exists():
        return urls
    with open(SEED_URLS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and line.startswith("http"):
                urls.append(line)
    return urls


def crawl_urls(urls):
    from langchain_community.document_loaders import WebBaseLoader
    loader = WebBaseLoader(urls)
    loader.requests_per_second = 1
    try:
        return loader.load()
    except Exception:
        return []


def chunk_documents(docs, chunk_size=1200, chunk_overlap=150):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return splitter.split_documents(docs)


class Command(BaseCommand):
    help = "Crawl laptop buying guide URLs and build Chroma RAG index (Google embeddings)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-crawl",
            action="store_true",
            help="Skip crawl; only rebuild from existing data (not implemented).",
        )

    def handle(self, *args, **options):
        from dotenv import load_dotenv
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            self.stderr.write(self.style.ERROR("GEMINI_API_KEY not set. Set it in .env"))
            return

        urls = load_seed_urls()
        if not urls:
            self.stderr.write(self.style.ERROR(f"No URLs found in {SEED_URLS_FILE}"))
            return

        self.stdout.write(f"Crawling {len(urls)} URLs...")
        docs = crawl_urls(urls)
        if not docs:
            self.stderr.write(self.style.ERROR("No documents loaded from URLs"))
            return
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(docs)} document(s)"))

        # Use same chunk settings as rag.py (fewer chunks = fewer embed calls)
        from laptop_guide.rag import CHUNK_SIZE, CHUNK_OVERLAP
        chunks = chunk_documents(docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        self.stdout.write(f"Split into {len(chunks)} chunks (free-tier: batching embeddings)")

        from laptop_guide.rag import (
            CHROMA_PERSIST_DIR,
            COLLECTION_NAME,
            _get_embeddings,
        )
        import chromadb
        from langchain_chroma import Chroma

        # Clear existing collection so we don't duplicate
        try:
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            client.delete_collection(COLLECTION_NAME)
            self.stdout.write("Cleared existing Chroma collection")
        except Exception:
            pass

        embeddings = _get_embeddings()
        # Create store and add in batches to stay under 100 embed/min (Gemini free tier)
        store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[i : i + EMBED_BATCH_SIZE]
            store.add_documents(batch)
            self.stdout.write(f"  Indexed {min(i + EMBED_BATCH_SIZE, len(chunks))}/{len(chunks)} chunks")
            if i + EMBED_BATCH_SIZE < len(chunks):
                self.stdout.write(f"  Waiting {EMBED_DELAY_SECONDS}s for rate limit...")
                time.sleep(EMBED_DELAY_SECONDS)
        self.stdout.write(self.style.SUCCESS(f"Chroma index saved to {CHROMA_PERSIST_DIR}"))
