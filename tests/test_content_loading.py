from pathlib import Path

from services.content import ContentManager


def test_content_loader_reads_texts_and_menus(tmp_path: Path) -> None:
    base = tmp_path / "content"
    base.mkdir()

    (base / "texts.ru.yml").write_text("greeting:\n  start: 'Здравствуйте'\n", encoding="utf-8")
    (base / "menus.ru.yml").write_text(
        "segment_menu:\n  - label: 'Test'\n    callback_data: 'segment_test'\n",
        encoding="utf-8",
    )

    manager = ContentManager(base_path=base)
    manager.load()

    assert manager.get_text("greeting.start") == "Здравствуйте"
    menu = manager.get_menu("segment_menu")
    assert isinstance(menu, list)
    assert menu[0]["label"] == "Test"
