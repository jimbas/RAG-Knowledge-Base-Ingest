# Airflow Knowledge Base — Ingest

Loads Airflow operational knowledge (error catalog, runbooks, incidents, DAG registry) into a local [ChromaDB](https://docs.trychroma.com/) vector store using a locally-hosted sentence-transformer model.

---

## Requirements

- Python 3.10+
- [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli) (`pip install huggingface_hub[cli]`)

### Python dependencies

```
langchain-community
langchain-text-splitters
langchain-huggingface
langchain-chroma
```

---

## Model setup

Download the embedding model locally before running ingest:

```bash
hf download sentence-transformers/all-MiniLM-L6-v2 --local-dir ./all-MiniLM-L6-v2
```

The script expects the model at `./all-MiniLM-L6-v2` relative to `ingest.py`.

---

## Usage

**First run / full ingest:**

```bash
python ingest.py
```

**Re-ingest after data changes (wipes existing ChromaDB first):**

```bash
python ingest.py --clean
```

The vector store is written to `./chroma_db/`.

---

## Data directory layout

```
data/
├── dag_registry/
│   ├── etl_dags.txt            # ETL DAG definitions (customer orders, inventory sync)
│   └── reporting_dags.txt      # Reporting DAG definitions (daily revenue, weekly inventory)
├── error_catalog/
│   ├── kubernetes_executor_errors.txt   # OOMKilled, ImagePullBackOff, Pod Evicted
│   ├── postgres_operator_errors.txt     # Connection refused, connection reset, relation missing
│   ├── python_operator_errors.txt       # ModuleNotFoundError, TypeError, task timeout
│   └── trino_errors.txt                 # JDBC connection failures, query timeouts
├── incidents/
│   └── 2025_q1_incidents.txt   # Q1 2025 incident summaries (free-text)
├── runbooks/
│   ├── database_issues.txt     # PostgreSQL connection issues, BigQuery quota exceeded
│   └── infrastructure_issues.txt  # Airflow worker OOMKilled, scheduler not triggering
└── incidents_structured.json   # (optional) structured incidents auto-appended by agent
```

### Metadata categories

Each ingested document is tagged with a `category` metadata field:

| Category        | Source path         |
|-----------------|---------------------|
| `error_catalog` | `data/error_catalog/` |
| `incident`      | `data/incidents/` and `incidents_structured.json` |
| `runbook`       | `data/runbooks/` |
| `dag_registry`  | `data/dag_registry/` |

---

## Structured incidents (`incidents_structured.json`)

Incidents resolved by an agent can be appended as structured JSON entries. Each entry must have:

```json
{
  "date": "2025-03-10",
  "dag_id": "etl_customer_orders",
  "task_id": "load_to_bq",
  "error_summary": "...",
  "root_cause": "...",
  "resolution": "..."
}
```

These are ingested alongside the plain-text files and tagged with `category: incident`, `dag_id`, and `task_id` metadata for filtered retrieval.

---

## Chunking & embedding config

| Setting            | Value                         |
|--------------------|-------------------------------|
| Chunk size         | 500 tokens                    |
| Chunk overlap      | 80 tokens                     |
| Embedding model    | `all-MiniLM-L6-v2` (local)    |
| Vector similarity  | Cosine                        |
| Vector store       | ChromaDB (`./chroma_db/`)     |
