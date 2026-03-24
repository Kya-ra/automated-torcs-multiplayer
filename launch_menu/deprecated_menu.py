import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QFont

import pyperclip

from subprocess import call

player_count = 2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Torcs Setup")
        self.setFixedSize(800, 600)

        central = QWidget(self)
        central.setObjectName("backgroundImage")
        self.setCentralWidget(central)

        torcs_font_id = QFontDatabase.addApplicationFont("launch_menu/fonts/Serpentine Bold.otf")
        torcs_font = QFontDatabase.applicationFontFamilies(torcs_font_id)[0]

        title = QLabel("Torcs Setup", central)
        title.setFont(QFont(torcs_font, 48))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        singleplayer_button = QPushButton("Singleplayer", central)
        multiplayer_button = QPushButton("Multiplayer", central)
        singleplayer_button.setFont(QFont(torcs_font, 48))
        multiplayer_button.setFont(QFont(torcs_font, 48))
        singleplayer_button.clicked.connect(singleplayer)
        multiplayer_button.clicked.connect(multiplayer)

        menu_layout = QVBoxLayout()
        menu_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        menu_layout.addStretch()
        menu_layout.addWidget(singleplayer_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        menu_layout.addWidget(multiplayer_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        menu_layout.addStretch()

        central.setLayout(menu_layout)


        central.setStyleSheet("""
            #backgroundImage {
                border-image: url(launch_menu/assets/splash-qrtrk-blue.png) 0 0 0 0 stretch stretch;
            }
                              
            QWidget {

                color: yellow;                
            }
                              
            QPushButton {
                
                border: none;
                font-size: 32px;
                width: 300px;
            }
                              
            QPushButton:hover {
                border: 2px solid rgb(255, 0, 0);
                color: red;
            }
                              
            menu_layout {

                margin-bottom: 20px;                  
            }
        """)

def singleplayer():
    player_count = 1
    pyperclip.copy(player_count)
    call(["./launch.sh"])

def multiplayer():
    pyperclip.copy(player_count)
    call(["./launch.sh"])


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()