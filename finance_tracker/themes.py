"""Colour themes and the Qt stylesheet built from them."""
from string import Template

THEMES = {
    "light": {"bg": "#f0f0f0", "fg": "#111111", "panel": "#ffffff", "border": "#c8c8c8",
              "button": "#fafafa", "accent": "#2e7d32"},
    "dark": {"bg": "#1e1f22", "fg": "#e6e6e6", "panel": "#2b2d31", "border": "#4a4d52",
             "button": "#383b40", "accent": "#66bb6a"},
}

_QSS = Template("""
QWidget { background-color: $bg; color: $fg; }
QLineEdit, QTextEdit, QComboBox { background-color: $panel; border: 1px solid $border; padding: 3px; }
QComboBox QAbstractItemView { background-color: $panel; color: $fg; }
QPushButton { background-color: $button; border: 1px solid $border; padding: 5px 10px; }
QPushButton:hover { border-color: $accent; }
QLabel#balanceLabel { border: 1px solid $accent; padding: 2px 6px; }
QLabel#greetingLabel { font-size: 15px; font-weight: bold; }
QLabel#streakLabel { font-weight: bold; color: $accent; }
""")


def stylesheet(name: str) -> str:
    return _QSS.substitute(THEMES.get(name, THEMES["light"]))
