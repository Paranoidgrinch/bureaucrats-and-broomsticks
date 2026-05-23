import json
from pathlib import Path


TEMPLATE_DIR = Path("data/templates")


def test_authoring_templates_are_valid_json() -> None:
    template_paths = sorted(TEMPLATE_DIR.glob("*.json"))

    assert template_paths

    for template_path in template_paths:
        with template_path.open(encoding="utf-8") as file:
            json.load(file)


def test_authoring_docs_exist_for_main_content_types() -> None:
    doc_dir = Path("docs/content_authoring")

    expected_docs = {
        "overview.md",
        "cards.md",
        "enemies.md",
        "relics.md",
        "events.md",
        "statuses.md",
        "acts.md",
        "adding_new_effects.md",
    }

    existing_docs = {path.name for path in doc_dir.glob("*.md")}

    assert expected_docs <= existing_docs
