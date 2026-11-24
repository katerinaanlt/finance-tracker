"""Main application window (PyQt5 + embedded matplotlib pie chart)."""
from __future__ import annotations

import sys
from typing import Optional

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget)

from . import receipt_ocr
from .models import DEFAULT_CATEGORIES, InsufficientFundsError, ProfileStore, validate_amount
from .settings_dialog import SettingsDialog
from .themes import THEMES, stylesheet


class FinanceTracker(QWidget):
    def __init__(self, store: Optional[ProfileStore] = None):
        super().__init__()
        self.store = store or ProfileStore()
        if store is None:
            self.store.load()
        self.profile = self.store.get(self.store.last_profile)
        self._build_ui()
        self.apply_theme()
        self.refresh()

    # ---- UI construction ----------------------------------------------------
    def _build_ui(self) -> None:
        self.setWindowTitle("Finance Tracker")

        self.greeting_label = QLabel()
        self.greeting_label.setObjectName("greetingLabel")
        self.streak_label = QLabel()
        self.streak_label.setObjectName("streakLabel")
        self.streak_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header = QHBoxLayout()
        header.addWidget(self.greeting_label)
        header.addWidget(self.streak_label, 1)

        self.balance_label = QLabel()
        self.balance_label.setObjectName("balanceLabel")
        self.balance_label.setAlignment(Qt.AlignRight)
        self.balance_label.setFont(QFont("Arial", 14, QFont.Bold))

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("Enter amount")
        self.amount_edit.returnPressed.connect(self.log_expense)

        self.log_button = QPushButton("Log Expense")
        self.add_button = QPushButton("Add to Balance")
        self.scan_button = QPushButton("Scan Receipt…")
        buttons = QHBoxLayout()
        for button in (self.log_button, self.add_button, self.scan_button):
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            buttons.addWidget(button)

        self.category_combo = QComboBox()
        self.category_combo.addItems(DEFAULT_CATEGORIES)
        category_row = QHBoxLayout()
        category_row.addWidget(QLabel("Select Expense Category:"))
        category_row.addWidget(self.category_combo, 1)

        self.figure = Figure(figsize=(4, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumWidth(260)
        middle = QHBoxLayout()
        middle.addWidget(self.canvas, 3)
        middle.addWidget(self.log_edit, 1)

        self.settings_button = QPushButton("Settings")
        self.settings_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.amount_label = QLabel()
        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.balance_label)
        layout.addWidget(self.amount_label)
        layout.addWidget(self.amount_edit)
        layout.addLayout(buttons)
        layout.addLayout(category_row)
        layout.addLayout(middle, 1)
        layout.addWidget(self.settings_button, 0, Qt.AlignLeft)

        self.log_button.clicked.connect(self.log_expense)
        self.add_button.clicked.connect(self.add_to_balance)
        self.scan_button.clicked.connect(self.scan_receipt)
        self.settings_button.clicked.connect(self.open_settings)

    # ---- actions ------------------------------------------------------------
    def _read_amount(self) -> Optional[float]:
        try:
            return validate_amount(self.amount_edit.text())
        except ValueError as exc:
            self._message("Error", str(exc) if self.amount_edit.text().strip() else "Amount cannot be empty")
            return None

    def log_expense(self) -> None:
        amount = self._read_amount()
        if amount is None:
            return
        try:
            self.profile.add_expense(amount, self.category_combo.currentText())
        except InsufficientFundsError as exc:
            self._message("Error", str(exc))
            return
        self._commit()
        limit = self.profile.daily_limit
        if limit > 0:
            from datetime import date
            if self.profile.spent_on(date.today()) > limit:
                self._message("Warning", "You exceeded today's spending limit - your streak was reset.")

    def add_to_balance(self) -> None:
        amount = self._read_amount()
        if amount is None:
            return
        self.profile.add_income(amount)
        self._commit()

    def scan_receipt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select a receipt image", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = receipt_ocr.scan_receipt(path)
        except receipt_ocr.ReceiptOCRError as exc:
            self._message("Receipt scan failed", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        if result.total is None:
            self._message("Receipt scan", "No amount could be recognised. Try a sharper, well-lit photo.")
            return
        self.amount_edit.setText(f"{result.total:.2f}")
        self._message("Receipt scan", f"Detected total: {result.total:.2f}\n\n"
                                      "Pick a category and press 'Log Expense' to confirm.")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.store, self.profile.name, self)
        accepted = dialog.exec_() == SettingsDialog.Accepted
        name = dialog.selected_name if accepted else self.profile.name
        self.profile = self.store.get(name)
        self.store.last_profile = self.profile.name
        self.store.save()
        self.apply_theme()
        self.refresh()

    # ---- state -> UI --------------------------------------------------------
    def _commit(self) -> None:
        self.store.save()
        self.amount_edit.clear()
        self.refresh()

    def apply_theme(self) -> None:
        self.setStyleSheet(stylesheet(self.store.theme))

    def refresh(self) -> None:
        p = self.profile
        self.greeting_label.setText(f"Hello, {p.name}")
        self.balance_label.setText(f"Balance: {p.balance:.2f} {p.currency}")
        self.amount_label.setText(f"Enter an amount ({p.currency}):")
        if p.daily_limit > 0:
            days = p.streak()
            self.streak_label.setText(f"🔥 {days}-day streak" if days else "No streak yet")
        else:
            self.streak_label.setText("")
        lines = []
        for t in p.transactions:
            if t.kind == "expense":
                lines.append(f"{t.day}: {t.amount:.2f} {p.currency} for {t.category}")
            else:
                lines.append(f"{t.day}: +{t.amount:.2f} {p.currency} added")
        self.log_edit.setPlainText("\n".join(lines))
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())
        self.plot()

    def plot(self) -> None:
        colors = THEMES.get(self.store.theme, THEMES["light"])
        data = self.profile.expenses_by_category()
        self.figure.clear()
        self.figure.set_facecolor(colors["panel"])
        ax = self.figure.add_subplot(1, 1, 1)
        ax.set_title("Expenses Distribution:", color=colors["fg"])
        if not data:
            ax.pie([1], colors=["#9e9e9e"], startangle=90, wedgeprops={"edgecolor": "black"})
            ax.text(0, 0, "There are no expenses.", ha="center", va="center", color="#111111")
        else:
            patches, texts, autotexts = ax.pie(
                list(data.values()), labels=list(data.keys()), autopct="%1.1f%%", startangle=140,
                textprops={"color": colors["fg"]})
            for patch in patches:
                patch.set_edgecolor("black")
            for text in autotexts:
                text.set_color("black")  # sits on a coloured slice in both themes
        self.canvas.draw()

    def _message(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)


def run() -> None:
    app = QApplication(sys.argv)
    window = FinanceTracker()
    window.resize(1000, 700)
    window.show()
    sys.exit(app.exec_())
