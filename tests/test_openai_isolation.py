import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_openai_is_only_imported_in_llm_client():
    files_to_check = [
        REPO_ROOT / "question_handler.py",
        REPO_ROOT / "burst.py",
        REPO_ROOT / "config.py",
        REPO_ROOT / "pricing.py",
        REPO_ROOT / "constants.py",
    ]

    offenders = []

    for path in files_to_check:
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "openai":
                        offenders.append(str(path.relative_to(REPO_ROOT)))

            if isinstance(node, ast.ImportFrom) and node.module == "openai":
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []
