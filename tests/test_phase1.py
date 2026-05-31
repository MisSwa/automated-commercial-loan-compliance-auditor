"""
tests/test_phase1.py

Automated verification for Phase 1: Core — Scaffolding & UI.
All assertions must pass before the phase1/core-scaffolding branch can be merged.

Run from the project root:
    pytest tests/test_phase1.py -v
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# 1. Required directories
# ---------------------------------------------------------------------------
def test_required_directories_exist():
    for d in ["app", "pipeline", "data", "specs", "tests"]:
        assert (PROJECT_ROOT / d).is_dir(), f"Directory '{d}' does not exist"


# ---------------------------------------------------------------------------
# 2. Required files
# ---------------------------------------------------------------------------
def test_required_files_exist():
    required = [
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "app/__init__.py",
        "app/main.py",
        "pipeline/__init__.py",
        "pipeline/ingest.py",
        "pipeline/retriever.py",
        "tests/__init__.py",
        "data/credit_policy.txt",
        "data/sample_loan_package.txt",
    ]
    for f in required:
        assert (PROJECT_ROOT / f).exists(), f"Required file missing: {f}"


# ---------------------------------------------------------------------------
# 3. Data files are non-empty
# ---------------------------------------------------------------------------
def test_credit_policy_non_empty():
    text = (PROJECT_ROOT / "data" / "credit_policy.txt").read_text(encoding="utf-8")
    assert len(text.strip()) > 500, "credit_policy.txt is too short to be valid"


def test_loan_package_non_empty():
    text = (PROJECT_ROOT / "data" / "sample_loan_package.txt").read_text(encoding="utf-8")
    assert len(text.strip()) > 500, "sample_loan_package.txt is too short to be valid"


def test_loan_package_contains_violation_marker():
    """The sample loan package must contain at least one deliberate policy violation."""
    text = (PROJECT_ROOT / "data" / "sample_loan_package.txt").read_text(encoding="utf-8")
    # The loan package documents a DSCR of 1.10x — below the 1.25x minimum
    assert "1.10x" in text, "Sample loan package should contain the deliberate DSCR violation (1.10x)"


# ---------------------------------------------------------------------------
# 4. Chroma collection is populated
# ---------------------------------------------------------------------------
def test_chroma_store_exists():
    assert (PROJECT_ROOT / "chroma_db").is_dir(), (
        "chroma_db/ directory not found. Run `python pipeline/ingest.py` to build it."
    )


def test_chroma_collection_populated():
    import chromadb
    client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "chroma_db"))
    collection = client.get_collection("credit_policy")
    assert collection.count() > 0, "Chroma collection 'credit_policy' is empty"


# ---------------------------------------------------------------------------
# 5 & 6. Retrieval returns relevant results
# ---------------------------------------------------------------------------
def test_retrieval_dscr():
    from pipeline.retriever import retrieve_policy_chunks
    results = retrieve_policy_chunks("DSCR requirement")
    assert len(results) >= 1, "DSCR query returned no results"
    assert any(len(r) > 0 for r in results), "DSCR results are empty strings"
    combined = " ".join(results).upper()
    assert "DSCR" in combined or "DEBT SERVICE" in combined, (
        "DSCR query did not return policy text mentioning DSCR or Debt Service"
    )


def test_retrieval_ltv():
    from pipeline.retriever import retrieve_policy_chunks
    results = retrieve_policy_chunks("LTV ratio limit")
    assert len(results) >= 1, "LTV query returned no results"
    assert any(len(r) > 0 for r in results), "LTV results are empty strings"
    combined = " ".join(results).upper()
    assert "LTV" in combined or "LOAN-TO-VALUE" in combined, (
        "LTV query did not return policy text mentioning LTV or Loan-to-Value"
    )


# ---------------------------------------------------------------------------
# 7. app/main.py is valid Python and importable with streamlit mocked
# ---------------------------------------------------------------------------
def test_app_main_valid_syntax():
    import ast
    source = (PROJECT_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise AssertionError(f"app/main.py has a syntax error: {e}")


def test_app_main_importable():
    from unittest.mock import MagicMock

    # Remove cached module if present from a previous test run
    for key in list(sys.modules.keys()):
        if key.startswith("app"):
            del sys.modules[key]

    # Mock streamlit so the module-level main() call doesn't require a server.
    # st.columns(n) must return an iterable of n MagicMocks so tuple-unpacking works.
    mock_st = MagicMock()
    mock_st.columns.side_effect = lambda n, **kw: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
    sys.modules["streamlit"] = mock_st

    try:
        import app.main  # noqa: F401 — import side-effect is the test
    except Exception as e:
        raise AssertionError(f"app/main.py raised an exception on import: {e}")
    finally:
        # Restore — don't pollute other tests
        del sys.modules["streamlit"]
        for key in list(sys.modules.keys()):
            if key.startswith("app"):
                del sys.modules[key]


# ---------------------------------------------------------------------------
# 8. .env is not tracked by git
# ---------------------------------------------------------------------------
def test_env_file_is_gitignored():
    gitignore_path = PROJECT_ROOT / ".gitignore"
    assert gitignore_path.exists(), ".gitignore does not exist"
    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content, ".env is not listed in .gitignore"


def test_env_example_exists_and_has_key():
    path = PROJECT_ROOT / ".env.example"
    assert path.exists(), ".env.example is missing"
    content = path.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in content, ".env.example does not contain ANTHROPIC_API_KEY"
