import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class ScriptRow(QWidget):
    def __init__(self, player_index: int, parent=None):
        super().__init__(parent)
        self.player_index = player_index
        self.file_path = ""

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        self.player_label = QLabel(f"Player {player_index}")
        self.path_label = QLabel("No file selected")
        self.path_label.setWordWrap(True)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.pick_file)

        row.addWidget(self.player_label, stretch=0)
        row.addWidget(self.path_label, stretch=1)
        row.addWidget(self.browse_button, stretch=0)

    def pick_file(self):
        app = QApplication.instance()
        original_style = app.styleSheet() if app else ""
        if app:
            # Temporarily clear app stylesheet so dialog uses normal system colors.
            app.setStyleSheet("")

        # Use a top-level dialog (no parent) so menu page styles don't bleed into it.
        dialog = QFileDialog(None, f"Select script for Player {self.player_index}")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Python Files (*.py)")
        # Force native dialog so it does not inherit themed colors.
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
        # Fallback styling in case non-native dialog is used under WSL.
        dialog.setStyleSheet(
            """
            QWidget { color: black; background-color: white; }
            QLineEdit, QListView, QTreeView, QComboBox {
                color: black;
                background-color: white;
            }
            QPushButton {
                color: black;
                background-color: #efefef;
                border: 1px solid #888;
            }
            """
        )

        file_path = ""
        try:
            if dialog.exec():
                files = dialog.selectedFiles()
                if files:
                    file_path = files[0]
        finally:
            if app:
                app.setStyleSheet(original_style)
        if file_path:
            self.file_path = file_path
            self.path_label.setText(file_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Torcs Setup")
        self.setFixedSize(1000, 700)

        self.repo_root = Path(__file__).resolve().parents[1]
        self.scripts_dir = self.repo_root / "gym_torcs"

        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        self.torcs_font = self._load_font()

        self.main_page = self._build_main_page()
        self.multiplayer_page = self._build_multiplayer_page()

        self.stacked.addWidget(self.main_page)
        self.stacked.addWidget(self.multiplayer_page)
        self.stacked.setCurrentWidget(self.main_page)

        self._apply_styles()
        self._update_script_rows()

    def _load_font(self):
        font_path = str(self.repo_root / "launch_menu" / "fonts" / "Serpentine Bold.otf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                return families[0]
        return "Arial"

    def _build_main_page(self):
        page = QWidget()
        page.setObjectName("backgroundImage")

        title = QLabel("Torcs Setup")
        title.setFont(QFont(self.torcs_font, 46))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        single_button = QPushButton("Singleplayer")
        multi_button = QPushButton("Multiplayer")
        single_button.setFont(QFont(self.torcs_font, 38))
        multi_button.setFont(QFont(self.torcs_font, 38))

        single_button.clicked.connect(self.launch_singleplayer)
        multi_button.clicked.connect(self.show_multiplayer_page)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        layout.addWidget(single_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(multi_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        return page

    def _build_multiplayer_page(self):
        page = QWidget()
        page.setObjectName("backgroundImage")

        title = QLabel("Multiplayer Setup")
        title.setFont(QFont(self.torcs_font, 34))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Select players and upload one Python script per player.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Arial", 12))

        count_wrap = QHBoxLayout()
        count_label = QLabel("Player Count:")
        count_label.setFont(QFont("Arial", 12))
        self.player_count_spin = QSpinBox()
        self.player_count_spin.setRange(1, 6)
        self.player_count_spin.setValue(2)
        self.player_count_spin.valueChanged.connect(self._update_script_rows)
        count_wrap.addStretch()
        count_wrap.addWidget(count_label)
        count_wrap.addWidget(self.player_count_spin)
        count_wrap.addStretch()

        self.script_rows = []
        rows_layout = QVBoxLayout()
        rows_layout.setSpacing(8)
        for i in range(1, 7):
            row = ScriptRow(i)
            self.script_rows.append(row)
            rows_layout.addWidget(row)

        rows_holder = QWidget()
        rows_holder.setLayout(rows_layout)

        back_button = QPushButton("Back")
        launch_button = QPushButton("Launch Multiplayer")
        back_button.clicked.connect(self.show_main_page)
        launch_button.clicked.connect(self.launch_multiplayer)

        action_row = QHBoxLayout()
        action_row.addWidget(back_button)
        action_row.addStretch()
        action_row.addWidget(launch_button)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(count_wrap)
        layout.addWidget(rows_holder)
        layout.addStretch()
        layout.addLayout(action_row)
        return page

    def _apply_styles(self):
        self.setStyleSheet(
            """
            #backgroundImage {
                border-image: url(launch_menu/assets/splash-qrtrk-blue.png) 0 0 0 0 stretch stretch;
            }
            #backgroundImage, #backgroundImage QWidget {
                color: yellow;
            }
            #backgroundImage QLabel {
                background: transparent;
            }
            #backgroundImage QPushButton {
                border: 2px solid transparent;
                padding: 8px 14px;
                font-size: 18px;
                color: rgb(255, 255, 0);
                background-color: rgba(0, 0, 0, 0);
            }
            #backgroundImage QPushButton:hover {
                border: 2px solid rgb(255, 0, 0);
                color: red;
                background-color: rgba(0, 0, 0, 20);
            }
            #backgroundImage QPushButton:pressed {
                color: rgb(255, 180, 180);
            }
            #backgroundImage QSpinBox {
                min-width: 70px;
                font-size: 16px;
                color: yellow;
                background-color: rgba(0, 0, 0, 150);
                border: 1px solid rgba(255, 255, 0, 120);
                padding: 2px;
            }
            """
        )

    def show_main_page(self):
        self.stacked.setCurrentWidget(self.main_page)

    def show_multiplayer_page(self):
        self.stacked.setCurrentWidget(self.multiplayer_page)

    def _update_script_rows(self):
        visible_rows = self.player_count_spin.value()
        for idx, row in enumerate(self.script_rows, start=1):
            row.setVisible(idx <= visible_rows)

    def _validate_selected_scripts(self):
        player_count = self.player_count_spin.value()
        selected = []

        for i in range(player_count):
            row = self.script_rows[i]
            file_path = row.file_path.strip()
            if not file_path:
                QMessageBox.warning(
                    self,
                    "Missing Script",
                    f"Please select a Python file for Player {i + 1}.",
                )
                return None
            if not file_path.lower().endswith(".py"):
                QMessageBox.warning(
                    self,
                    "Invalid File",
                    f"Player {i + 1} file must be a .py script.",
                )
                return None
            if not Path(file_path).exists():
                QMessageBox.warning(
                    self,
                    "Missing File",
                    f"Selected file for Player {i + 1} was not found.",
                )
                return None
            selected.append(file_path)
        return selected

    def launch_singleplayer(self):
        self._run_backend(player_count=1)

    def launch_multiplayer(self):
        scripts = self._validate_selected_scripts()
        if scripts is None:
            return
        self._run_backend(player_count=self.player_count_spin.value(), scripts=scripts)

    def _run_backend(self, player_count: int, scripts=None):
        scripts = scripts or []
        cmd = [sys.executable, "test.py", "--players", str(player_count)]
        if scripts:
            cmd += ["--scripts", *scripts]

        # Backend currently prompts for count through stdin; scripts are
        # forwarded as optional args for future backend handling.
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.repo_root,
                input=f"{player_count}\n",
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                QMessageBox.information(
                    self,
                    "Launch Started",
                    f"Started backend for {player_count} player(s).",
                )
            else:
                error_text = proc.stderr.strip() or proc.stdout.strip() or "Unknown error."
                QMessageBox.critical(
                    self,
                    "Launch Failed",
                    f"Backend returned an error:\n\n{error_text}",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Unable to start backend:\n\n{exc}",
            )


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
