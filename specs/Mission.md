# Mission

## Problem

Commercial banks receive unstructured underwriting packages from borrowers. Before a loan moves to manual underwriting, a compliance check must verify:

- All required documents are present
- Financial covenants align with the bank's credit policy
- No red flags or policy violations exist

Doing this manually creates a significant backlog, introduces human error, and slows the loan pipeline.

## Goal

Build an automated compliance pre-screening tool that ingests an unstructured loan package, extracts key metadata, cross-references it against the bank's credit policy, and surfaces any violations — all before the file reaches a human underwriter.

## Who This Is For

- **Compliance officers** who need consistent, auditable pre-screening
- **Underwriters** who receive a structured summary instead of raw documents
- **Risk managers** who need confidence scoring and flagged exceptions

## What the System Does

1. Accepts an uploaded loan package as an unstructured text file
2. Extracts structured metadata (borrower info, financials, loan terms, document checklist)
3. Retrieves relevant credit policy sections using RAG
4. Checks extracted data against policy thresholds and flags violations
5. Produces a structured compliance report with a confidence score
6. Presents the report to a human reviewer for approval or rejection

## What the System Never Does

- **Never approves or rejects a loan.** The system surfaces findings only. All final decisions are made by a human reviewer.
- **Never stores sensitive borrower data** beyond the active session without explicit controls.
- **Never silently fails.** All error states are caught, logged, and surfaced to the user with clear guidance.

## Core Principles

| Principle | Description |
|---|---|
| **Human oversight** | Every report requires a human review step before any action is taken |
| **Transparency** | Confidence scores and evidence citations accompany every finding |
| **Privacy first** | Borrower data is treated as sensitive; no unnecessary persistence |
| **Graceful failure** | Partial extractions, missing fields, and model errors are handled explicitly |
| **Structured output** | Raw unstructured input always yields a clean, auditable structured report |
