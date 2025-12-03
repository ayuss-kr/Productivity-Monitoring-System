# ui_app.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer

from db import verify_user, start_session, end_session
from monitor import ProductivityMonitor

main_window = None  # global reference so window is not garbage collected


# ------------------ Login Window ------------------

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Productivity Monitor - Login")
        self.setFixedSize(300, 200)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)

        layout = QVBoxLayout()
        title_label = QLabel("Login")
        title_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addStretch()

        self.setLayout(layout)

    def handle_login(self):
        global main_window  # 👈 use global

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password.")
            return

        try:
            user = verify_user(username, password)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database error:\n{e}")
            return

        if user is None:
            QMessageBox.warning(self, "Error", "Invalid credentials.")
            return

        # Debug print so you see it in terminal
        print(f"Login success for user id={user['id']}")

        # Keep dashboard in a global so it doesn't get garbage-collected
        main_window = DashboardWindow(user)
        main_window.show()
        self.close()



# ------------------ Dashboard Window ------------------

class DashboardWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        print("DashboardWindow created for", self.user.get('username') or self.user) 
        self.current_session_id = None
        self.monitor: ProductivityMonitor | None = None

        self.setWindowTitle(f"Dashboard - {self.user.get('username', 'User')}")
        self.setFixedSize(420, 260)

        central = QWidget()
        self.setCentralWidget(central)

        # Labels
        self.name_label = QLabel(f"Welcome, {self.user.get('full_name') or self.user.get('username')}")
        self.name_label.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("Status: Not Punched In")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.time_label = QLabel("Productive Time: 00:00:00")
        self.time_label.setAlignment(Qt.AlignCenter)

        # Buttons
        self.punch_in_btn = QPushButton("Punch In")
        self.punch_out_btn = QPushButton("Punch Out")
        self.punch_out_btn.setEnabled(False)

        self.punch_in_btn.clicked.connect(self.on_punch_in)
        self.punch_out_btn.clicked.connect(self.on_punch_out)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.punch_in_btn)
        btn_layout.addWidget(self.punch_out_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.time_label)
        layout.addLayout(btn_layout)

        central.setLayout(layout)

        # Timer to refresh UI from monitor thread
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.refresh_monitor_status)
        self.ui_timer.start(1000)

    # -------- Punch In / Out handlers --------

    def on_punch_in(self):
        if self.current_session_id is not None:
            QMessageBox.information(self, "Info", "You already have an active session.")
            return

        try:
            # Create new session in DB
            session_id = start_session(self.user["id"])
            self.current_session_id = session_id

            # Start background monitoring thread
            self.monitor = ProductivityMonitor(session_id=session_id, show_window=True)
            self.monitor.start()

            self.status_label.setText("Status: Working (Punched In)")
            self.punch_in_btn.setEnabled(False)
            self.punch_out_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start session:\n{e}")

    def on_punch_out(self):
        if self.current_session_id is None:
            QMessageBox.information(self, "Info", "No active session.")
            return

        try:
            # Stop monitor thread if running
            if self.monitor is not None:
                self.monitor.stop()
                self.monitor.join(timeout=3)
                self.monitor = None

            # Close DB session
            end_session(self.current_session_id)
            self.current_session_id = None

            self.status_label.setText("Status: Punched Out")
            self.time_label.setText("Productive Time: 00:00:00")
            self.punch_in_btn.setEnabled(True)
            self.punch_out_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to end session:\n{e}")

    # -------- UI refresh from monitor --------

    def refresh_monitor_status(self):
        """Poll the monitor thread and update labels."""
        if self.monitor is not None and self.monitor.is_alive():
            self.status_label.setText(f"Status: {self.monitor.current_status_text}")
            self.time_label.setText(f"Productive Time: {self.monitor.current_total_time_str}")

    # -------- Handle window close --------

    def closeEvent(self, event):
        """Ensure monitor thread is stopped when window closes."""
        try:
            if self.monitor is not None:
                self.monitor.stop()
                self.monitor.join(timeout=3)
                self.monitor = None
        except Exception:
            pass
        event.accept()


# ------------------ Entrypoint ------------------

def main():
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
