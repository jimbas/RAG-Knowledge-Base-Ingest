from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import json, os
import shutil
import argparse

PERSIST_DIR = "./chroma_db"
DATA_DIR = "./data"

def load_documents() -> list[Document]:
    docs = []

    # --- Plain .txt / .md files (error catalog, runbooks) ---
    loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader
    )
    raw = loader.load()

    # Tag each doc with its category based on subfolder
    # data/error_catalog/, data/runbooks/, data/incidents/, data/dag_registry/
    for doc in raw:
        path = doc.metadata.get("source", "")
        if "error_catalog" in path:
            doc.metadata["category"] = "error_catalog"
        elif "incidents" in path:
            doc.metadata["category"] = "incident"
        elif "runbooks" in path:
            doc.metadata["category"] = "runbook"
        elif "dag_registry" in path:
            doc.metadata["category"] = "dag_registry"
        else:
            doc.metadata["category"] = "general"
        docs.append(doc)

    # --- Structured incident JSON (auto-appended by agent after resolution) ---
    incident_path = os.path.join(DATA_DIR, "incidents_structured.json")
    if os.path.exists(incident_path):
        with open(incident_path) as f:
            incidents = json.load(f)
        for inc in incidents:
            content = f"""
Incident Date: {inc.get('date')}
DAG: {inc.get('dag_id')}
Task: {inc.get('task_id')}
Error: {inc.get('error_summary')}
Root Cause: {inc.get('root_cause')}
Resolution: {inc.get('resolution')}
""".strip()
            docs.append(Document(
                page_content=content,
                metadata={
                    "category": "incident",
                    "dag_id": inc.get("dag_id"),
                    "task_id": inc.get("task_id"),
                }
            ))

    return docs

def ingest(clean: bool = False):
    if clean and os.path.exists(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
        print(f"Cleared existing ChromaDB at {PERSIST_DIR}")
    
    docs = load_documents()
    print(f"Loaded {len(docs)} documents")

    # Slightly larger chunks — our docs are structured markdown, not raw logs
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
    )
    chunks = splitter.split_documents(docs)
    print(f"Total chunks: {len(chunks)}")

    embeddings = HuggingFaceEmbeddings(
        model_name=os.path.join(os.path.dirname(os.path.abspath(__file__)), "all-MiniLM-L6-v2")
    )
    vectorstore = Chroma.from_documents(
        chunks,
        embeddings,
        persist_directory=PERSIST_DIR,
        collection_metadata={"hnsw:space": "cosine"}  # cosine = better for text
    )
    print("Ingestion complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Delete existing ChromaDB before ingesting")
    args = parser.parse_args()
    ingest(clean=args.clean)
