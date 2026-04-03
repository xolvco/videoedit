from pathlib import Path

from videoedit.commands import COMMAND_MODULES


def test_every_command_has_docs_and_tests() -> None:
    project_root = Path(__file__).resolve().parents[1]

    missing_docs: list[str] = []
    missing_tests: list[str] = []

    for module in COMMAND_MODULES:
        command_stem = module.COMMAND_NAME.replace("-", "_")
        doc_path = project_root / "docs" / "commands" / f"{command_stem}.md"
        test_path = project_root / "tests" / f"test_{command_stem}.py"

        if not doc_path.exists():
            missing_docs.append(str(doc_path))
        if not test_path.exists():
            missing_tests.append(str(test_path))

    assert not missing_docs, f"Missing command docs: {missing_docs}"
    assert not missing_tests, f"Missing command tests: {missing_tests}"

