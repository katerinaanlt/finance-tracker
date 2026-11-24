"""Settings dialog: profile management, theme, currency and daily spending limit."""
from __future__ import annotations

from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QInputDialog,
                             QLineEdit, QMessageBox, QPushButton, QVBoxLayout)

from .models import ProfileStore


class SettingsDialog(QDialog):
    def __init__(self, store: ProfileStore, current_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.store = store
        self.selected_name = current_name

        self.profile_combo = QComboBox()
        self.new_button = QPushButton("New profile…")
        self.delete_button = QPushButton("Delete")
        profile_row = QHBoxLayout()
        profile_row.addWidget(self.profile_combo, 1)
        profile_row.addWidget(self.new_button)
        profile_row.addWidget(self.delete_button)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(store.theme))

        self.currency_edit = QLineEdit()
        self.currency_edit.setMaxLength(3)
        self.limit_edit = QLineEdit()
        self.limit_edit.setPlaceholderText("0 = disabled")

        form = QFormLayout()
        form.addRow("Profile:", profile_row)
        form.addRow("Theme:", self.theme_combo)
        form.addRow("Currency symbol:", self.currency_edit)
        form.addRow("Daily spending limit (streaks):", self.limit_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._reload_profiles(current_name)
        self.profile_combo.currentTextChanged.connect(self._load_fields)
        self.new_button.clicked.connect(self._new_profile)
        self.delete_button.clicked.connect(self._delete_profile)

    # ---- helpers ----------------------------------------------------------
    def _reload_profiles(self, select: str) -> None:
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self.store.names())
        self.profile_combo.setCurrentText(select)
        self.profile_combo.blockSignals(False)
        self._load_fields(self.profile_combo.currentText())

    def _load_fields(self, name: str) -> None:
        if name not in self.store.profiles:
            return
        profile = self.store.profiles[name]
        self.currency_edit.setText(profile.currency)
        self.limit_edit.setText(f"{profile.daily_limit:g}")

    def _new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New profile", "Profile name:")
        if not ok:
            return
        try:
            self.store.create_profile(name)
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self.store.save()
        self._reload_profiles(name.strip())

    def _delete_profile(self) -> None:
        name = self.profile_combo.currentText()
        if QMessageBox.question(self, "Delete profile",
                                f"Delete '{name}' and all of its transactions?") != QMessageBox.Yes:
            return
        try:
            self.store.delete_profile(name)
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        self.store.save()
        self._reload_profiles(self.store.get(None).name)

    def _save(self) -> None:
        try:
            limit = float(self.limit_edit.text().strip().replace(",", ".") or 0)
            if limit < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Error", "Daily limit must be a non-negative number.")
            return
        profile = self.store.profiles[self.profile_combo.currentText()]
        profile.currency = self.currency_edit.text().strip() or "€"
        profile.daily_limit = limit
        self.store.theme = self.theme_combo.currentData()
        self.selected_name = profile.name
        self.accept()
