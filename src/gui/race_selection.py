from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox
)
from PySide6.QtWidgets import QProgressDialog
from PySide6.QtCore import QThread, Signal, Qt, QTimer
#from PySide6.QtGui import QPixmap, QFont
import sys
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from src.f1_data import get_race_weekends_by_year, get_race_weekends_by_place, get_all_unique_race_names, load_session
from src.gui.settings_dialog import SettingsDialog
from src.lib.season import get_season

# Worker thread to fetch schedule without blocking UI
class FetchScheduleWorker(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, year, parent=None):
        super().__init__(parent)
        self.year = year

    def run(self): #check
        try:
            # enable cache if available in project
            try:
                from src.f1_data import enable_cache
                enable_cache()
            except Exception:
                pass
            events = get_race_weekends_by_year(self.year)
            self.result.emit(events)
        except Exception as e:
            self.error.emit(str(e))

class RaceSelectionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.loading_session = False
        self.selected_session_title = None
        self.current_year = get_season()
        self.selected_year=self.current_year 

        self.setWindowTitle("F1 Race Replay - Session Selection")
        self._apply_theme()
        self._setup_ui()
        self.resize(1100, 750)
        self.setMinimumSize(900, 650)
        self.setWindowState(self.windowState())

    def _apply_theme(self):
        """Apply a modern dark F1-branded stylesheet."""
        self.setStyleSheet("""
            /* ── Global ────────────────────────────────────── */
            QMainWindow, QWidget {
                background-color: #0f0f1a;
                color: #e0e0e0;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
            }

            /* ── Labels ────────────────────────────────────── */
            QLabel {
                color: #c8c8d0;
                font-size: 13px;
            }
            QLabel#headerLabel {
                color: #ffffff;
                font-size: 22px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLabel#sessionHeader {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }

            /* ── Buttons ───────────────────────────────────── */
            QPushButton {
                background-color: #1c1c2e;
                color: #e0e0e0;
                border: 1px solid #2a2a3e;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2a2a40;
                border: 1px solid #e10600;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #e10600;
                color: #ffffff;
                border: 1px solid #e10600;
            }
            QPushButton#settingsBtn {
                background-color: transparent;
                border: 1px solid #e10600;
                color: #e10600;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton#settingsBtn:hover {
                background-color: #e10600;
                color: #ffffff;
            }
            QPushButton#sessionBtn {
                background-color: #1a1a2e;
                border: 1px solid #30304a;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
                color: #e0e0e0;
            }
            QPushButton#sessionBtn:hover {
                background-color: #e10600;
                border: 1px solid #e10600;
                color: #ffffff;
            }
            QPushButton#sessionBtn:pressed {
                background-color: #b50500;
            }

            /* ── ComboBoxes ────────────────────────────────── */
            QComboBox {
                background-color: #1c1c2e;
                color: #e0e0e0;
                border: 1px solid #2a2a3e;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 28px;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #e10600;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid #2a2a3e;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1c1c2e;
                color: #e0e0e0;
                selection-background-color: #e10600;
                selection-color: #ffffff;
                border: 1px solid #2a2a3e;
                border-radius: 4px;
                padding: 4px;
            }

            /* ── Tree Widget (Schedule) ────────────────────── */
            QTreeWidget {
                background-color: #12121f;
                color: #d0d0d8;
                border: 1px solid #1e1e30;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
                outline: 0;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #1a1a2a;
            }
            QTreeWidget::item:hover {
                background-color: #1e1e32;
            }
            QTreeWidget::item:selected {
                background-color: #e10600;
                color: #ffffff;
            }
            QTreeWidget::item:alternate {
                background-color: #14141f;
            }
            QHeaderView::section {
                background-color: #16162a;
                color: #a0a0b0;
                border: none;
                border-bottom: 2px solid #e10600;
                padding: 8px 10px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
            }

            /* ── Scrollbars ────────────────────────────────── */
            QScrollBar:vertical {
                background: #0f0f1a;
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #2a2a3e;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #e10600;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal {
                background: #0f0f1a;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #2a2a3e;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #e10600;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }

            /* ── Progress Dialog ───────────────────────────── */
            QProgressDialog {
                background-color: #0f0f1a;
                color: #e0e0e0;
            }
            QProgressBar {
                background-color: #1c1c2e;
                border: 1px solid #2a2a3e;
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #e10600;
                border-radius: 5px;
            }

            /* ── Message Box ───────────────────────────────── */
            QMessageBox {
                background-color: #0f0f1a;
                color: #e0e0e0;
            }
        """)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Header (title)
        header_layout = QHBoxLayout()
        header_label = QLabel("F1 Race Replay 🏎️")
        header_label.setObjectName("headerLabel")
        font = header_label.font()
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("settingsBtn")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setFixedHeight(34)
        settings_btn.clicked.connect(self.open_settings)
        font.setPointSize(20)
        font.setBold(True)
        header_label.setFont(font)
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(settings_btn)
        main_layout.addLayout(header_layout)

        # Year selection
        year_layout = QHBoxLayout()
        year_label = QLabel("Select Year:")
        self.year_combo = QComboBox()
        self.year_combo.addItem("All Years")

        for year in range(2018, self.current_year + 1):
            self.year_combo.addItem(str(year))

        self.year_combo.setCurrentText(str(self.current_year))
        self.year_combo.currentTextChanged.connect(self.load_by_year)

        year_layout.addWidget(year_label)
        year_layout.addWidget(self.year_combo)
        main_layout.addLayout(year_layout)

        #Race Selection
        place_layout=QHBoxLayout()
        place_label=QLabel("Select Race:")
        self.place_combo=QComboBox()
        self.place_combo.addItem("All Races")
        self.place_combo.addItems(get_all_unique_race_names())
        self.place_combo.currentTextChanged.connect(self.load_by_place)


        place_layout.addWidget(place_label)
        place_layout.addWidget(self.place_combo)
        main_layout.addLayout(place_layout)

        # Main content: left = schedule, right = session list
        content_layout = QHBoxLayout()

        # Schedule tree (left)
        self.schedule_tree = QTreeWidget()
        self.schedule_tree.setHeaderLabels(["Round", "Event", "Country", "Start Date"])
        self.schedule_tree.setRootIsDecorated(False)
        content_layout.addWidget(self.schedule_tree, 3)
        self.schedule_tree.setColumnWidth(2, 180)

        # Session panel (right)
        self.session_panel = QWidget()
        self.session_panel_layout = QVBoxLayout()
        self.session_panel.setLayout(self.session_panel_layout)
        self.session_panel_layout.setAlignment(Qt.AlignTop)
        header_lbl = QLabel("Sessions")
        header_lbl.setObjectName("sessionHeader")
        hdr_font = header_lbl.font()
        hdr_font.setPointSize(15)
        hdr_font.setBold(True)
        header_lbl.setFont(hdr_font)
        self.session_panel_layout.addWidget(header_lbl)

        # placeholder spacer
        self.session_list_container = QWidget()
        self.session_list_layout = QVBoxLayout()
        self.session_list_container.setLayout(self.session_list_layout)
        self.session_panel_layout.addWidget(self.session_list_container)

        content_layout.addWidget(self.session_panel, 1)

        main_layout.addLayout(content_layout)

        # connect click handler
        self.schedule_tree.itemClicked.connect(self.on_race_clicked)

        # Load initial schedule
        # hide sessions panel until a weekend is selected
        self.session_panel.hide()
        self.load_schedule(year=self.current_year)
        
    def load_schedule(self, year=None, events=None):
        if self.loading_session:
            return
        
        self.schedule_tree.clear()
        # hide sessions panel while loading / when nothing selected
        try:
            self.session_panel.hide()
        except Exception:
            pass
        
        #Race filter
        if events is not None:
            self.populate_schedule(events)
            self.loading_session = False
            return
        
        #Year filter
        if year is not None:
            self.loading_session = True
            self.worker = FetchScheduleWorker(int(year))
            self.worker.result.connect(self.populate_schedule)
            self.worker.error.connect(self.show_error)
            self.worker.start()
            return
        
        self.loading_session=False

    def load_by_year(self, year_text):
        if self.loading_session:
            return
        
        #Reset by_race filter
        if year_text!="All Years":
            self.place_combo.blockSignals(True)
            self.place_combo.setCurrentText("All Races")
            self.place_combo.blockSignals(False)

        if year_text=="All Years":
            self.selected_year=None
            self.schedule_tree.clear()
            return
        
        if not year_text.isdigit():
            return
        
        self.selected_year=int(year_text)
        self.load_schedule(year=self.selected_year)

    def load_by_place(self,race_name):
        if race_name=="All Races":
            if self.selected_year is not None:
                self.load_schedule(year=self.selected_year)
            return
        
        #Reset year filter
        self.year_combo.blockSignals(True)
        self.year_combo.setCurrentText("All Years")
        self.year_combo.blockSignals(False)
        self.selected_year=None

        self.schedule_tree.clear()
        
        events=get_race_weekends_by_place(race_name)
        self.load_schedule(events=events)

    def populate_schedule(self, events):
        for event in events:
            # Ensure all columns are strings (QTreeWidgetItem expects text)
            round_str = str(event.get("round_number", ""))
            name = str(event.get("event_name", ""))
            country = str(event.get("country", ""))
            date = str(event.get("date", ""))

            event_item = QTreeWidgetItem([round_str, name, country, date])
            event_item.setData(0, Qt.UserRole, event)
            self.schedule_tree.addTopLevelItem(event_item)

        # Make sure the round column is wide enough to be visible
        try:
            self.schedule_tree.resizeColumnToContents(0)
            self.schedule_tree.resizeColumnToContents(1)
        except Exception:
            pass

        self.loading_session = False

    def on_race_clicked(self, item, column):
        ev = item.data(0, Qt.UserRole)
        # ensure the sessions panel is visible when a race is selected
        try:
            self.session_panel.show()
        except Exception:
            pass
        # determine sessions to show
        ev_type = (ev.get("type") or "").lower()
        sessions = ["Qualifying", "Race"]
        if "sprint" in ev_type:
            sessions.insert(0, "Sprint Qualifying")
            # show sprint-related session
            sessions.insert(2, "Sprint")

        # clear existing session widgets
        for i in reversed(range(self.session_list_layout.count())):
            w = self.session_list_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        # determine which sessions have already occurred (data available)
        now = datetime.now(timezone.utc)
        session_dates = ev.get("session_dates", {})

        available_sessions = []
        for s in sessions:
            session_date_str = session_dates.get(s)
            if session_date_str:
                try:
                    session_dt = datetime.fromisoformat(session_date_str)
                    if session_dt <= now:
                        available_sessions.append(s)
                except Exception:
                    available_sessions.append(s)
            else:
                # no date info means historical data — assume available
                available_sessions.append(s)

        if not available_sessions:
            label = QLabel("Sessions not available")
            label.setAlignment(Qt.AlignCenter)
            self.session_list_layout.addWidget(label)
        else:
            for s in sessions:
                if s in available_sessions:
                    btn = QPushButton(s)
                    btn.setObjectName("sessionBtn")
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.clicked.connect(
                        lambda _, sname=s, e=ev: self._on_session_button_clicked(e, sname)
                    )
                    self.session_list_layout.addWidget(btn)

    def _on_session_button_clicked(self, ev, session_label):
        """Launch main.py in a separate process to run the selected session.

        Uses the same CLI flags that `main.py` understands: `--qualifying`,
        `--sprint-qualifying`, `--sprint`. Runs the command detached so the
        Qt UI remains responsive.
        """
        try:
            year = ev.get("year") or self.selected_year
        except Exception:
            year = None

        try:
            round_no = int(ev.get("round_number"))
        except Exception:
            round_no = None

        # map button labels to CLI flags
        flag = None
        if session_label == "Qualifying":
            flag = "--qualifying"
        elif session_label == "Sprint Qualifying":
            flag = "--sprint-qualifying"
        elif session_label == "Sprint":
            flag = "--sprint"

        main_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "main.py")
        )
        cmd = [sys.executable, main_path, "--viewer"]
        if year is not None:
            cmd += ["--year", str(year)]
        if round_no is not None:
            cmd += ["--round", str(round_no)]
        if flag:
            cmd.append(flag)
        if "--verbose" in sys.argv:
            cmd.append("--verbose")
        # Show a modal loading dialog and load the session in a background thread.
        dlg = QProgressDialog("Loading session data...", None, 0, 0, self)
        dlg.setWindowTitle("Loading")
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setCancelButton(None)
        dlg.setMinimumDuration(0)
        dlg.setRange(0, 0)
        dlg.show()
        QApplication.processEvents()

        # Map label -> fastf1 session type code
        session_code = 'R'
        if session_label == "Qualifying":
            session_code = 'Q'
        elif session_label == "Sprint Qualifying":
            session_code = 'SQ'
        elif session_label == "Sprint":
            session_code = 'S'

        class FetchSessionWorker(QThread):
            result = Signal(object)
            error = Signal(str)

            def __init__(self, year, round_no, session_type, parent=None):
                super().__init__(parent)
                self.year = year
                self.round_no = round_no
                self.session_type = session_type

            def run(self):
                try:
                    try:
                        from src.f1_data import enable_cache
                        enable_cache()
                    except Exception:
                        pass
                    sess = load_session(self.year, self.round_no, self.session_type)
                    self.result.emit(sess)
                except Exception as e:
                    self.error.emit(str(e))

        def _on_loaded(session_obj):
            # create a unique ready-file path and pass it to the child
            ready_path = os.path.join(tempfile.gettempdir(), f"f1_ready_{uuid.uuid4().hex}")
            cmd_with_ready = list(cmd) + ["--ready-file", ready_path]

            try:
                proc = subprocess.Popen(cmd_with_ready)
            except Exception as exc:
                try:
                    dlg.close()
                except Exception:
                    pass
                QMessageBox.critical(self, "Playback error", f"Failed to start playback:\n{exc}")
                return

            # Poll for ready file or child exit
            timer = QTimer(self)

            def _check_ready():
                try:
                    if os.path.exists(ready_path):
                        try:
                            dlg.close()
                        except Exception:
                            pass
                        timer.stop()
                        try:
                            os.remove(ready_path)
                        except Exception:
                            pass
                        return
                    # if process exited early, show error
                    if proc.poll() is not None:
                        try:
                            dlg.close()
                        except Exception:
                            pass
                        timer.stop()
                        QMessageBox.critical(self, "Playback error", "Playback process exited before signaling readiness")
                except Exception:
                    # ignore transient file-system errors
                    pass

            timer.timeout.connect(_check_ready)
            timer.start(200)
            # keep references
            self._play_proc = proc
            self._ready_timer = timer

        def _on_error(msg):
            try:
                dlg.close()
            except Exception:
                pass
            QMessageBox.critical(self, "Load error", f"Failed to load session data:\n{msg}")

        worker = FetchSessionWorker(year, round_no, session_code)
        worker.result.connect(_on_loaded)
        worker.error.connect(_on_error)
        # Keep a reference so it doesn't get GC'd
        self._session_worker = worker
        worker.start()
    def show_error(self, message):
        QMessageBox.critical(self, "Error", f"Failed to load schedule: {message}")
        self.loading_session = False

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()
