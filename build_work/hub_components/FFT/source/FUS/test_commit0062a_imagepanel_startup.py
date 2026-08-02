from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_plot_created_before_focus_policy_is_applied():
    start = APP.index("class ImagePanel(QWidget):")
    end = APP.index("class ", start + 10)
    block = APP[start:end]
    create = block.index("self.plot = pg.PlotWidget()")
    focus = block.index("self.plot.setFocusPolicy(Qt.StrongFocus)")
    assert create < focus


def test_no_preinitialization_plot_access_in_constructor_prefix():
    start = APP.index("def __init__(self, title: str):", APP.index("class ImagePanel(QWidget):"))
    create = APP.index("self.plot = pg.PlotWidget()", start)
    prefix = APP[start:create]
    assert "self.plot." not in prefix
