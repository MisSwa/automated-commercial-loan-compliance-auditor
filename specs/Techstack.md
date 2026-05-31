# Tech Stack

## Overview

| Layer | Technology | Rationale |
|---|---|---|
| UI / Frontend | Streamlit | Rapid prototype UI; file upload, report rendering, human review controls |
| Pipeline Orchestration | LangGraph | Stateful, node-based graph for multi-step extraction and compliance checking |
| LLM | Claude (Anthropic) via `anthropic` SDK | Strong structured extraction, instruction-following, and document reasoning |
| Vector Store | Chroma (local persistent) | Local persistent RAG store; no external service required, easy to evolve |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Lightweight, runs locally, sufficient for policy document retrieval |
| Language | Python 3.11+ | Standard for ML/AI tooling ecosystem |
| Dependency Management | `pip` + `requirements.txt` | Simple and portable for prototyping |

## State Management

LangGraph pipeline state is defined using Python's built-in `TypedDict`. This is LangGraph's native pattern — state is passed between nodes as a plain typed dictionary, with each node returning a partial update. No external library needed for state; `TypedDict` is from the standard library (`typing`).

`Pydantic` is used only for the final `ComplianceReport` output schema (validation and serialization of the report object, not pipeline state).

## Key Libraries

```
streamlit
langgraph
langchain-core
anthropic
chromadb
sentence-transformers
pydantic
python-dotenv
```

## Architecture Layers

```
┌─────────────────────────────────────┐
│           Streamlit UI              │  ← File upload, report display, human review
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│         LangGraph Pipeline          │  ← Orchestrates nodes as a directed graph
│                                     │
│  [Extract Metadata]                 │
│       ↓                             │
│  [Retrieve Policy Sections]  ←──── Chroma (credit policy vector store)
│       ↓                             │
│  [Check Compliance]                 │
│       ↓                             │
│  [Score Confidence]                 │
│       ↓                             │
│  [Generate Report]                  │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│         Claude (Anthropic)          │  ← LLM for extraction, reasoning, flagging
└─────────────────────────────────────┘
```

## Environment Variables

```
ANTHROPIC_API_KEY=...
```

Loaded via `python-dotenv` from a `.env` file. Never committed to version control.

## Data Flow

1. User uploads a `.txt` loan package via Streamlit
2. Raw text is passed into the LangGraph pipeline as initial state
3. Each node mutates state and passes it to the next
4. Claude performs extraction and compliance reasoning at designated nodes
5. Chroma retrieves the most relevant credit policy chunks at the retrieval node
6. Final state is rendered as a structured compliance report in the UI
7. Human reviewer approves or rejects via the UI — no automated decision is emitted

## What Is Intentionally Excluded

- No database persistence of borrower data (session-only)
- No authentication layer (out of scope for prototype)
- No cloud deployment config (local prototype only)
- No streaming LLM responses (batch structured output preferred for auditability)
