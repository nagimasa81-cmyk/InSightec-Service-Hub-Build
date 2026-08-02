from pathlib import Path


def test_compact_auto_ui_source_contract():
    text = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert 'self.comp_tabs = QTabWidget()' in text
    assert 'self.comp_tabs.addTab(auto_tab, "Auto")' in text
    assert 'self.comp_tabs.addTab(paint_tab, "Paint")' in text
    assert 'self.comp_tabs.addTab(expert_tab, "Expert")' in text
    assert 'AccordionSection("Quick Adjust", quick_group, False)' in text
    assert 'progress.setMinimumWidth(520)' in text
    assert 'Auto Correct Progress' in text
