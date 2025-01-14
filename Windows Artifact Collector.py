import os
import sys
import platform
import psutil
import re

from PyQt5.QtWidgets import QLineEdit, QFrame, QFormLayout, QProgressBar, QRadioButton, QDialogButtonBox, QHeaderView, QFileDialog, QApplication, QDialog, QProxyStyle, QHBoxLayout, QDateTimeEdit, QTreeView, QPushButton, QCheckBox, QMainWindow, QLabel, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsTextItem, QGraphicsPixmapItem, QGraphicsProxyWidget, QGraphicsLineItem, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtGui import QColor, QPixmap, QFont, QStandardItem, QPen, QStandardItemModel, QIcon
from PyQt5.QtCore import QThread, QRectF, Qt, QPointF, QDateTime, QSize, QRect, QRegExp, QSortFilterProxyModel, pyqtSignal
from datetime import datetime

from utils.Artifacts import Artifacts
from utils import check_artifact
import WAC_back

# EXE 패키징 경로 문제 해결
def resource_path(relative_path):
    try: # pyinstaller로 실행될 때 경로 설정
        base_path = sys._MEIPASS
    except AttributeError: # 개발 환경에서 현재 경로 사용
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class OptionSelector:
    Antivirus = False
    Browser = False
    Windows = False
    Apps = False
    Logs = False
    P2P = False
    WSA = False
    WSL = False

class SystemInfoWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Information")
        self.setWindowFlags(Qt.Window)
        # Set style sheet for the window
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
            }
            QLabel {
                color: #ffffff; 
            }
        """)
        
        # Get system information
        self.system_info = self.get_systeminfo()

        # Create layout and add widgets
        layout = QFormLayout()
        for key, value in self.system_info.items():
            layout.addRow(QLabel(f"{key}: "), QLabel(value))
        
        self.setLayout(layout)
        self.resize(400, 300)

    def get_systeminfo(self):
        boot_time = psutil.boot_time()
        boot_time_str = datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S')

        info = {
            "OS": platform.system(),
            "OS Version": platform.version(),
            "Architecture": platform.architecture()[0],
            "Processor": platform.processor(),
            "CPU Cores": str(psutil.cpu_count(logical=False)),
            "Logical CPUs": str(psutil.cpu_count(logical=True)),
            "RAM": f"{psutil.virtual_memory().total / (1024 ** 3):.2f} GB",
            "Available RAM": f"{psutil.virtual_memory().available / (1024 ** 3):.2f} GB",
            "Disk Usage": f"{psutil.disk_usage('/').percent}%",
            "Boot Time": boot_time_str
        }
        return info

class OptionsDialog(QDialog):
    def __init__(self, options, parent=None):
        filter_image_path = resource_path(os.path.join('assets', 'frame0', 'filter.png'))
        super().__init__(parent)
        self.setWindowTitle("카테고리 선택")
        self.setWindowFlags(Qt.Dialog | Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint)
        self.setWindowIcon(QIcon(filter_image_path))

        self.selected_options = {}
        self.check_boxes = []

        # Layout for the dialog
        layout = QFormLayout()
        
        # Create checkboxes for each option
        for option in options:
            chk = QCheckBox(option)
            self.check_boxes.append(chk)
            layout.addRow(chk)
        
        # Set initial states
        self.check_boxes[0].setChecked(OptionSelector.Antivirus)
        self.check_boxes[1].setChecked(OptionSelector.Browser)
        self.check_boxes[2].setChecked(OptionSelector.Windows)
        self.check_boxes[3].setChecked(OptionSelector.Apps)
        self.check_boxes[4].setChecked(OptionSelector.Logs)
        self.check_boxes[5].setChecked(OptionSelector.P2P)
        self.check_boxes[6].setChecked(OptionSelector.WSA)
        self.check_boxes[7].setChecked(OptionSelector.WSL)

        # Create buttons for the dialog
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addRow(button_box)
        self.setLayout(layout)
        self.resize(160, 200)
    
    def accept(self):
        self.selected_options = {chk.text(): chk.isChecked() for chk in self.check_boxes}
        OptionSelector.Antivirus = self.selected_options["Antivirus"]
        OptionSelector.Browser = self.selected_options["Browser"]
        OptionSelector.Windows = self.selected_options["Windows"]
        OptionSelector.Apps = self.selected_options["Apps"]
        OptionSelector.Logs = self.selected_options["Logs"]
        OptionSelector.P2P = self.selected_options["P2P"]
        OptionSelector.WSA = self.selected_options["WSA"]
        OptionSelector.WSL = self.selected_options["WSL"]
        super().accept()

class ArtifactCollectorThread(QThread):
    progress_changed = pyqtSignal(int, str)

    def __init__(self, checked_items, output_path, export_type, zip_name=None):
        super().__init__()
        self.checked_items = checked_items
        self.output_path = output_path
        self.export_type = export_type
        self.zip_name = zip_name

    def run(self):
        WAC_back.collect_main(self.checked_items, self.output_path, self.export_type, self.zip_name, self.update_progress)
    
    def update_progress(self, progress, message):
        self.progress_changed.emit(progress, message)

class ProgressWindowCollect(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Windows Artifact Collector")
        self.setGeometry(500, 350, 400, 100)
        
        self.layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.center_on_parent()

    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            self.move(
                parent_geometry.center() - self.rect().center()
            )
        


# 프로그레스바
class Worker(QThread):
    progress = pyqtSignal(int)

    def __init__(self, parent=None):
        super(Worker, self).__init__(parent)
        self._is_running = True

    def run(self):
        check_artifact.check_all_config(self.update_progress, self.is_running)
    
    def update_progress(self, percentage):
        self.progress.emit(percentage)

    def stop(self):
        self._is_running = False
    
    def is_running(self):
        return self._is_running

class ProgressWindow(QWidget):
    finished = pyqtSignal() # 작업 완료 시그널

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로컬 아티팩트 검사 중...")
        self.setGeometry(500, 350, 400, 100)

        self.layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.center_on_parent()
    
    def center_on_parent(self):
        if self.parent():
            parent_geometry = self.parent().geometry()
            self.move(
                parent_geometry.center() - self.rect().center()
            )

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        if value >= 100:
            self.finished.emit()
            self.close()
    
    def closeEvent(self, event):
        self.parent().worker.stop()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    exist_checked = False # 현재 수집 가능 체크박스 상태
    from_time_checked = False # (시간옵션) from 체크박스 상태
    until_time_checked = False # (시간옵션) until 체크박스 상태
    checked_item = [] # 리스트에서 체크된 항목의 이름 저장
    output_path = None # 출력 경로 저장
    export_checked = False # 컨테이너 선택 상태

    def __init__(self):
        super().__init__()

        
        self.setGeometry(100, 100, 1133, 645)
        self.setWindowTitle("Windows Artifact Collector")
        self.setFixedSize(1133, 645)  # Set fixed size to prevent resizing
        #프로그램 아이콘 삽입 위치s
        logo_navy_image_path = resource_path(os.path.join('assets', 'frame0', '케쉴주_navy.ico'))
        self.setWindowIcon(QIcon(logo_navy_image_path))

    
        # Create QGraphicsView and QGraphicsScene
        self.graphics_view = QGraphicsView(self)
        self.graphics_view.setGeometry(0, 0, 1133, 645)  # Set size and position
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setStyleSheet("border: none;")  # Remove border

        # 메인 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 1133, 645)  # Set the scene size to match the view
        self.graphics_view.setScene(self.scene)
        
        # Add rectangles to the scene
        self.create_rectangles()

        # Add image to the scene
        logo_white_image_path = resource_path(os.path.join('assets', 'frame0', 'logo_white.png'))
        entry_image_path = resource_path(os.path.join('assets', 'frame0', 'entry.png'))
        self.add_image_to_scene(logo_white_image_path, 120.0, 40.0)
        self.add_image_to_scene(entry_image_path, 40.0, 150.0)
    

        class Output:
            # 출력 경로 불러오기
            self.button_path_pdf = QPushButton('경로 선택', self)
            self.button_path_pdf.setGeometry(245, 155, 70, 30)  # x, y, width, height 설정
            self.button_path_pdf.setStyleSheet(
                '''
                QPushButton {
                    background-color: #FFFFFF;
                    color: #000000;               
                    font-family: Arial;        
                    font-size: 9pt;
                    border: 1px solid #C8C8C8;         
                    border-radius: 3px;        
                }
                QPushButton:pressed {
                    background-color: #C8C8C8;
                    color: #FFFFFF;
                }
                QPushButton:disabled {
                    background-color: #E0E0E0; 
                    color: #A0A0A0;             
                    border: 1px solid #B0B0B0; 
                }
                QPushButton:focus {
                    outline: none;             
                    border: 1px solid #BDBDBD; 
                }
            ''')
            self.button_path_pdf.clicked.connect(self.click_folder_path) # 함수

            self.result_label = QLabel('No file or folder selected.', self)
            self.result_label.setGeometry(QRect(48, 155, 195, 30))
            self.result_label.setWordWrap(False) 

        # 로컬 아티팩트 검사하기
        self.export_button = QPushButton('로컬 아티팩트 검사하기', self)
        self.export_button.setStyleSheet('''
            QPushButton {
                background-color: #ACB3CE;
                color: white;               
                font-family: Arial;        
                font-size: 9pt;            
                font-weight: bold;          
                padding: 2px 5px;          
                border-radius: 4px;        
            }
            QPushButton:hover {
                background-color: #9A9EC0;
                border: 1px solid #7A8BCC;
            }
            QPushButton:pressed {
                background-color: #7A8BCC;
            }
            QPushButton:disabled {
                background-color: #E0E0E0; 
                color: #A0A0A0;             
                border: 1px solid #B0B0B0; 
            }
            QPushButton:focus {
                outline: none;             
                border: 1px solid #4A6C8C; 
            }
        ''')
        self.export_button.setFont(QFont('Arial', 9, QFont.Bold))
        self.export_button.setGeometry(40, 198, 280, 30) 
        self.export_button.clicked.connect(self.check_localArtifacts) 

        # 텍스트 출력
        self.create_text_item("▶  출력 위치", 40.0, 123.0, 9, "#1E1E1E", tooltip=None)
        self.create_text_item("▶ 시간 옵션 활성화", 40.0, 273.0, 9, "#1E1E1E", tooltip=None)
        self.create_text_item("~", 149.0, 350.0, 13, "#7F7F7F", tooltip=None)
        self.create_text_item("Container", 40.0, 433.0, 9, "#C8C8C8", tooltip="수집 시 생성되는 파일을 압축 형태로 내보낼지 결정합니다.")

         # 날짜/시간 선택
        self.datetime_edit1 = QDateTimeEdit(self)
        self.datetime_edit1.setGeometry(58, 322, 230, 30)
        self.datetime_edit1.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 날짜 및 시간 형식 설정
        #self.datetime_edit1.setDateTime(QDateTime.currentDateTime())  # 기본값을 현재 날짜와 시간으로 설정
        self.datetime_edit1.dateTimeChanged.connect(self.from_datetime_changed)
        self.datetime_edit1.setEnabled(False)

        self.datetime_edit2 = QDateTimeEdit(self)
        self.datetime_edit2.setGeometry(58, 392, 230, 30)
        self.datetime_edit2.setDisplayFormat("yyyy-MM-dd HH:mm:ss")  # 날짜 및 시간 형식 설정
        self.datetime_edit2.setDateTime(QDateTime.currentDateTime())  # 기본값을 현재 날짜와 시간으로 설정
        self.datetime_edit2.dateTimeChanged.connect(self.until_datetime_changed)
        self.datetime_edit2.setEnabled(False)

        class Checkbox:
            # 상태 저장 변수
            self.check_duplicate = QCheckBox()
            self.check_time = QCheckBox()
            self.check_all_file = QCheckBox()
            self.check_filter = QCheckBox()

            self.checkbox_existing = QCheckBox("현재 수집 가능한 아티팩트만 보기", self)
            self.checkbox_existing.setGeometry(42, 237, 210, 30)  # 위치와 크기 설정
            self.checkbox_existing.setStyleSheet("font-size: 12px;")
            self.checkbox_existing.setEnabled(False)
            self.checkbox_existing.setChecked(False)  # 초기 상태 설정
            self.checkbox_existing.stateChanged.connect(self.existing_checkbox)

            self.checkbox_time1 = QCheckBox("From (YYYY-MM-DD hh:mm:ss)", self)
            self.checkbox_time1.setGeometry(58, 298, 200, 30)  # 위치와 크기 설정
            self.checkbox_time1.setStyleSheet("font-size: 12px;")
            self.checkbox_time1.setEnabled(False)
            self.checkbox_time1.setChecked(False)  # 초기 상태 설정
            self.checkbox_time1.stateChanged.connect(self.toggle_time_from)

            self.checkbox_time2 = QCheckBox("Until (YYYY-MM-DD hh:mm:ss)", self)
            self.checkbox_time2.setGeometry(58, 368, 200, 30)  # 위치와 크기 설정
            self.checkbox_time2.setStyleSheet("font-size: 12px;")
            self.checkbox_time2.setEnabled(False)
            self.checkbox_time2.setChecked(False)  # 초기 상태 설정
            self.checkbox_time2.stateChanged.connect(self.toggle_time_until)

            self.checkbox_view = QCheckBox("체크된 항목만 보기", self)
            self.checkbox_view.setGeometry(401, 25, 130, 30)  # 위치와 크기 설정
            self.checkbox_view.setStyleSheet("font-size: 12px;")
            self.checkbox_view.setChecked(False)  # 초기 상태 설정
            self.checkbox_view.stateChanged.connect(self.toggle_filter)


        class RadioButton:
            self.frame = QFrame(self)
            self.frame.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                    border: 1px solid #C8C8C8;
                    padding: 10px;
                }
            """)
            self.frame.setGeometry(40, 454, 141, 30)


            # 라디오 버튼 생성
            self.radio_button1 = QRadioButton("None", self)
            self.radio_button1.move(62, 455)  # x, y 위치 설정
            self.radio_button1.setChecked(True)
            self.radio_button1.toggled.connect(self.Export_Option)
            self.radio_button1.setToolTip('출력 위치에 압축하지 않고 수집합니다.')

            self.radio_button2 = QRadioButton("Zip", self)
            self.radio_button2.move(122, 455)
            self.radio_button2.toggled.connect(self.Export_Option)
            self.radio_button2.setToolTip('출력 위치에 Zip형식으로 압축해서 수집합니다.')
        

        # 수집하기 버튼
        self.export_button = QPushButton('수집하기(Export)', self)
        self.export_button.setStyleSheet('''
            QPushButton {
                background-color: #ACB3CE;
                color: white;               
                font-family: Arial;        
                font-size: 9pt;            
                font-weight: bold;          
                padding: 2px 5px;          
                border-radius: 4px;        
            }
            QPushButton:hover {
                background-color: #9A9EC0;
                border: 1px solid #7A8BCC;
            }
            QPushButton:pressed {
                background-color: #7A8BCC;
            }
            QPushButton:disabled {
                background-color: #E0E0E0; 
                color: #A0A0A0;             
                border: 1px solid #B0B0B0; 
            }
            QPushButton:focus {
                outline: none;             
                border: 1px solid #4A6C8C; 
            }
        ''')
        self.export_button.setFont(QFont('Arial', 9, QFont.Bold))
        self.export_button.setGeometry(200, 550, 120, 30)  # x, y, width, height
        self.export_button.clicked.connect(self.exportArtifact) # 함수
        self.export_button.setToolTip('선택한 아티팩트를 수집하여 출력 위치에 저장합니다.')

        # 압축 파일명
        self.text_box = QLineEdit(self)
        self.text_box.setPlaceholderText("파일명")
        self.text_box.setGeometry(190, 454, 120, 30)
        self.text_box.setEnabled(False)


        # 구분선
        line_item = QGraphicsLineItem(35, 523, 335, 523)  # 시작과 끝 좌표
        line_item.setPen(QPen(QColor("#C8C8C8"), 1, Qt.SolidLine))  # 색상, 두께, 선 스타일 설정
        self.scene.addItem(line_item)

        # 시스템 정보
        systeminfo_button = QPushButton('시스템 정보', self)
        systeminfo_button.setStyleSheet('''
            QPushButton {
                background-color: #7881ab;
                color: white;               
                font-family: Arial;        
                font-size: 9pt;            
                font-weight: bold;          
                padding: 2px 5px;          
                border-radius: 4px;        
            }
            QPushButton:hover {
                background-color: #9A9EC0;
                border: 1px solid #7A8BCC;
            }
            QPushButton:pressed {
                background-color: #7A8BCC;
            }
            QPushButton:disabled {
                background-color: #E0E0E0; 
                color: #A0A0A0;             
                border: 1px solid #B0B0B0; 
            }
            QPushButton:focus {
                outline: none;             
                border: 1px solid #4A6C8C; 
            }
        ''')

        systeminfo_button.setFont(QFont('Arial', 9, QFont.Bold))
        systeminfo_button.setGeometry(40, 550, 110, 30)  # x, y, width, height
        systeminfo_button.clicked.connect(self.show_systeminfo) # 함수
        systeminfo_button.setToolTip('현재 컴퓨터 시스템의 정보를 출력합니다.')

        class LIST:
            # QTreeView 및 QStandardItemModel 설정
            self.tree_view = QTreeView()
            self.tree_view.resize(747, 582)
            self.model = QStandardItemModel(0, 3)
            self.tree_view.setModel(self.model)
            self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.tree_view.setHorizontalScrollMode(QTreeView.ScrollPerPixel)
            self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setup_header()

            self.model.itemChanged.connect(self.handle_item_changed)
            

            # 전체 선택 체크박스
            self.select_all_checkbox = QCheckBox()
            self.select_all_checkbox.setCheckState(Qt.Unchecked)
            self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)

            # 카테고리 필터
            filter_image_path = resource_path(os.path.join('assets', 'frame0', 'filter.png'))
            self.filter_button = QPushButton()
            self.filter_button.setIcon(QIcon(filter_image_path))  # Set your button icon here
            self.filter_button.setIconSize(QSize(15, 15))  # Adjust icon size if necessary
            self.filter_button.clicked.connect(self.open_options_dialog)
            self.filter_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
            

            # QGraphicsProxyWidget을 사용하여 위젯을 QGraphicsScene에 추가
            self.proxy_tree = QGraphicsProxyWidget()
            self.proxy_tree.setWidget(self.tree_view)
            self.scene.addItem(self.proxy_tree)

            self.proxy_checkbox = QGraphicsProxyWidget()
            self.proxy_checkbox.setWidget(self.select_all_checkbox)
            self.scene.addItem(self.proxy_checkbox)

            self.proxy_button = QGraphicsProxyWidget()
            self.proxy_button.setWidget(self.filter_button)
            self.scene.addItem(self.proxy_button)

            self.proxy_model = QSortFilterProxyModel(self)
            self.proxy_model.setSourceModel(self.model)

            # 정렬 방향을 기억할 변수 초기화 (오름차순으로 시작)
            self.sort_order = Qt.AscendingOrder

            # 위젯의 위치 조정
            self.proxy_checkbox.setPos(401, 60)
            self.proxy_tree.setPos(377, 53)
            self.proxy_button.setGeometry(QRectF(1080.0, 50.0, 32, 32))

            self.setCentralWidget(self.graphics_view)

            # 필터 모델 생성 및 설정
            self.proxy_model = QSortFilterProxyModel()
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)  # 대소문자 구분 없이 검색
            self.proxy_model.setFilterKeyColumn(-1)

            self.tree_view.setModel(self.proxy_model)

            # 데이터 추가
            self.load_init_data()

            # 검색어 입력
            self.search_input = QLineEdit(self)
            self.search_input.setGeometry(555, 26, 380, 25)  # 입력 필드 위치 및 크기 설정
            self.search_input.setPlaceholderText("Search...")
            self.search_input.setStyleSheet('font-size: 12px; padding: 3px')
            self.search_input.textChanged.connect(self.search_word)

        
    # ================= 리스트 재설정 시 리스트 모델 설정 다시 호출 ==========
    # 현재 수집 가능 아티팩트 기능 수행 시에 리스트 재설정하게 되면서 리스트 모델 관련 설정을 다시 해줘야 함
    def reset_model_conf(self):
        # QTreeView 및 QStandardItemModel 설정
            self.tree_view = QTreeView()
            self.tree_view.resize(747, 582)
            self.model = QStandardItemModel(0, 3)
            self.tree_view.setModel(self.model)
            self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.tree_view.setHorizontalScrollMode(QTreeView.ScrollPerPixel)
            self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setup_header()

            self.model.itemChanged.connect(self.handle_item_changed)

            # 전체 선택 체크박스
            self.select_all_checkbox = QCheckBox()
            self.select_all_checkbox.setCheckState(Qt.Unchecked)
            self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)

            # 카테고리 필터
            filter_image_path = resource_path(os.path.join('assets', 'frame0', 'filter.png'))
            self.filter_button = QPushButton()
            self.filter_button.setIcon(QIcon(filter_image_path))  # Set your button icon here
            self.filter_button.setIconSize(QSize(15, 15))  # Adjust icon size if necessary
            self.filter_button.clicked.connect(self.open_options_dialog)
            self.filter_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
            

            # QGraphicsProxyWidget을 사용하여 위젯을 QGraphicsScene에 추가
            self.proxy_tree = QGraphicsProxyWidget()
            self.proxy_tree.setWidget(self.tree_view)
            self.scene.addItem(self.proxy_tree)

            self.proxy_checkbox = QGraphicsProxyWidget()
            self.proxy_checkbox.setWidget(self.select_all_checkbox)
            self.scene.addItem(self.proxy_checkbox)

            self.proxy_button = QGraphicsProxyWidget()
            self.proxy_button.setWidget(self.filter_button)
            self.scene.addItem(self.proxy_button)

            self.proxy_model = QSortFilterProxyModel(self)
            self.proxy_model.setSourceModel(self.model)

            # 정렬 방향을 기억할 변수 초기화 (오름차순으로 시작)
            self.sort_order = Qt.AscendingOrder

            # 위젯의 위치 조정
            self.proxy_checkbox.setPos(401, 60)
            self.proxy_tree.setPos(377, 53)
            self.proxy_button.setGeometry(QRectF(1080.0, 50.0, 32, 32))

            self.setCentralWidget(self.graphics_view)

            # 필터 모델 생성 및 설정
            self.proxy_model = QSortFilterProxyModel()
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)  # 대소문자 구분 없이 검색
            self.proxy_model.setFilterKeyColumn(-1)

            self.tree_view.setModel(self.proxy_model)


            # 검색어 입력
            self.search_input = QLineEdit(self)
            self.search_input.setGeometry(500, 26, 425, 25)  # 입력 필드 위치 및 크기 설정
            self.search_input.setPlaceholderText("Search...")
            self.search_input.setStyleSheet('font-size: 12px; padding: 3px')
            self.search_input.textChanged.connect(self.search_word)
    

    # ================= 기본 레이아웃에 필요한 함수 ===============

    def create_text_item(self, text, x, y, font_size, color, tooltip=None):
        text_item = QGraphicsTextItem(text)
        text_item.setFont(QFont("Arial", font_size))  # 폰트 설정
        text_item.setDefaultTextColor(QColor(color))  # 텍스트 색상 설정
        text_item.setPos(x, y)  # 텍스트 위치 설정
        self.scene.addItem(text_item)
        if tooltip:
            text_item.setToolTip(tooltip)

    def add_image_to_scene(self, image_path, x, y):
        # Load the image
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return
        
        # Create QGraphicsPixmapItem and set position
        image_item = QGraphicsPixmapItem(pixmap)
        image_item.setPos(QPointF(x, y))
        
        # Add the image item to the scene
        self.scene.addItem(image_item)

    def create_rectangles(self):
        # Create rectangles with QGraphicsRectItem
        self.scene.addRect(QRectF(3.0, 0.0, 1133.0 - 3.0, 645.0), brush=QColor("#D9D9D9"), pen=QColor("#D9D9D9"))
        self.scene.addRect(QRectF(368.0, 0.0, 1133.0 - 368.0, 645.0), brush=QColor("#CED8E3"), pen=QColor("#CED8E3"))
        self.scene.addRect(QRectF(0.0, 0.0, 368.0, 645.0), brush=QColor("#F3F3F3"), pen=QColor("#F3F3F3"))
        self.scene.addRect(QRectF(378.0, 86.0, 1123.0 - 378.0, 630.0 - 86.0), brush=QColor("#FFFFFF"), pen=QColor("#FFFFFF"))

    def set_button_icon(self, button, image_path):
        # 버튼에 아이콘 설정
        button.setIcon(QIcon(image_path))
        button.setIconSize(QSize(100, 100))  # 아이콘 크기 설정

    # 리스트 헤더
    def setup_header(self):
        header = self.tree_view.header()
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.sort_by_column)

        # 헤더 스타일 및 크기 설정
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #F2F2F2;
                box-shadow: none;
                border: none;
            }
        """)

        widget = QWidget()
        layout = QHBoxLayout()

        self.header_checkbox = QCheckBox()
        self.header_checkbox.setTristate(False)
        self.header_checkbox.setCheckState(Qt.Unchecked)
        self.header_checkbox.stateChanged.connect(self.toggle_select_all)
        layout.addWidget(self.header_checkbox)

        layout.addSpacing(10)
        widget.setLayout(layout)
        widget.setFixedHeight(20)

        self.tree_view.setIndexWidget(self.model.index(0, 0), widget)
        
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 47)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.resizeSection(1, 350)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.resizeSection(2, 350)

        self.model.setHorizontalHeaderLabels(["", "Name", "Category"])


    # ==================== 옵션 영역 =====================

    def update_filter(self):
    # 체크된 카테고리를 기반으로 필터링
        selected_categories = [opt for opt in ["Antivirus", "Browser", "Windows", "Apps", "Logs", "P2P", "WSA", "WSL"]
                           if getattr(OptionSelector, opt, False)]
        
        if selected_categories:
            # 선택된 카테고리를 기반으로 정규 표현식 생성
            filter_pattern = r'\b(' + '|'.join(selected_categories) + r')\b'
            self.proxy_model.setFilterRegExp(QRegExp(filter_pattern, Qt.CaseInsensitive, QRegExp.RegExp))
        else:
            # 선택된 카테고리가 없으면 필터를 클리어
            self.proxy_model.setFilterRegExp(QRegExp())  # 모든 항목을 표시'''


    # 경로 선택하는 함수
    def click_folder_path(self):
        options = QFileDialog.Options()
        folder_path = QFileDialog.getExistingDirectory(self, "폴더 선택", "", QFileDialog.Options())
        if folder_path:
            self.result_label.setText(f'{folder_path}')
            self.output_path = folder_path



    # 로컬 아티팩트 검사하는 로직
    def check_localArtifacts(self, value):
        self.progress_window = ProgressWindow(self)
        self.worker = Worker()
        self.worker.progress.connect(self.progress_window.update_progress) # update_progress는 ProgressBarWindow에 있음

        self.progress_window.finished.connect(lambda:
                                              (self.checkbox_existing.setEnabled(True)))

        self.progress_window.show()
        self.worker.start() # 작업 스레드 시작
        

 # ---------------------[시간 옵션 기능]-------------------------- #
    def time_true_check(self, from_datetime=None, until_datetime=None, mft_datetime=None):
            
        for instance in Artifacts.instances:
            instance.time = False

            if from_datetime and not until_datetime:
                if ((instance.atime is not None and from_datetime <= instance.atime) or
                    (instance.mtime is not None and from_datetime <= instance.mtime) or
                    (instance.ctime is not None and from_datetime <= instance.ctime)):
                    instance.time = True
            
            elif until_datetime and not from_datetime:
                if ((instance.atime is not None and until_datetime >= instance.atime) or
                    (instance.mtime is not None and until_datetime >= instance.mtime) or
                    (instance.ctime is not None and until_datetime >= instance.ctime)):
                    instance.time = True

            elif from_datetime and until_datetime:
                if from_datetime > until_datetime:
                    instance.time = False  
                else:
                    if ((instance.atime is not None and from_datetime <= instance.atime <= until_datetime) or
                        (instance.mtime is not None and from_datetime <= instance.mtime <= until_datetime) or
                        (instance.ctime is not None and from_datetime <= instance.ctime <= until_datetime)):
                        instance.time = True

    # From 날짜 변경 시 함수
    def from_datetime_changed(self):
        selected_datetime = self.datetime_edit1.dateTime()
        year = selected_datetime.date().year()
        month = selected_datetime.date().month()
        day = selected_datetime.date().day()
        hour = selected_datetime.time().hour()
        minute = selected_datetime.time().minute()
        second = selected_datetime.time().second()
        from_datetime = datetime(year, month, day, hour, minute, second)
            
        if self.until_time_checked:
            selected_until_datetime = self.datetime_edit2.dateTime()
            until_year = selected_until_datetime.date().year()
            until_month = selected_until_datetime.date().month()
            until_day = selected_until_datetime.date().day()
            until_hour = selected_until_datetime.time().hour()
            until_minute = selected_until_datetime.time().minute()
            until_second = selected_until_datetime.time().second()
            until_datetime = datetime(until_year, until_month, until_day, until_hour, until_minute, until_second)
            self.time_true_check(from_datetime, until_datetime)
        else:
            self.time_true_check(from_datetime)
                
        self.model.clear()
        self.reset_model_conf()
        self.load_time_data() # time 조건 load_data        

    # Until 날짜 변경 시 함수
    def until_datetime_changed(self):
        selected_datetime = self.datetime_edit2.dateTime()
        year = selected_datetime.date().year()
        month = selected_datetime.date().month()
        day = selected_datetime.date().day()
        hour = selected_datetime.time().hour()
        minute = selected_datetime.time().minute()
        second = selected_datetime.time().second()
        until_datetime = datetime(year, month, day, hour, minute, second)
            
        if self.from_time_checked:
            selected_from_datetime = self.datetime_edit1.dateTime()
            from_year = selected_from_datetime.date().year()
            from_month = selected_from_datetime.date().month()
            from_day = selected_from_datetime.date().day()
            from_hour = selected_from_datetime.time().hour()
            from_minute = selected_from_datetime.time().minute()
            from_second = selected_from_datetime.time().second()
            from_datetime = datetime(from_year, from_month, from_day, from_hour, from_minute, from_second)

            self.time_true_check(from_datetime, until_datetime)
        else:
            self.time_true_check(None, until_datetime)
        
        self.model.clear()
        self.reset_model_conf()
        self.load_time_data() # time 조건 load_data


    # 시간 선택기 활성화/비활성화
    def toggle_time_from(self, state):
        if self.checkbox_time1.isChecked():
            self.from_time_checked = True
            self.datetime_edit1.setEnabled(True)
            self.from_datetime_changed()

        else:
            self.from_time_checked = False
            self.datetime_edit1.setEnabled(False)
            if self.until_time_checked:
                self.until_datetime_changed()

    def toggle_time_until(self, state):
        if self.checkbox_time2.isChecked():
            self.until_time_checked = True
            self.datetime_edit2.setEnabled(True)
            self.until_datetime_changed()
            
        else:
            self.until_time_checked = False
            self.datetime_edit2.setEnabled(False)
            if self.from_time_checked:
                self.from_datetime_changed()


        
# -------------------------------------------------------------- #


    # 현재 수집 가능한 아티팩트 체크박스 관련 함수
    def existing_checkbox(self, state):
        if state == Qt.Checked:
            self.exist_checked = True
            self.checkbox_time1.setEnabled(True)
            self.checkbox_time2.setEnabled(True)
            self.model.clear()
            self.reset_model_conf()
            self.load_exist_data() # exist 조건 load_data

        else:
            self.exist_checked = False
            self.checkbox_time1.setEnabled(False)
            self.checkbox_time1.setChecked(False)
            self.checkbox_time2.setEnabled(False)
            self.checkbox_time2.setChecked(False)
            self.datetime_edit1.setEnabled(False)
            self.datetime_edit2.setEnabled(False)
            self.model.clear()
            self.reset_model_conf()
            self.load_init_data()
    


    
    def Export_Option(self):
        if self.radio_button1.isChecked():
            self.export_checked = False
            self.text_box.setEnabled(False)
        elif self.radio_button2.isChecked(): 
            self.export_checked = True
            self.text_box.setEnabled(True)



#-------------------[수집 버튼 구현]-------------------------------------------------------
    def handle_item_changed(self, item):
        if item.column() == 0:
            item_name = self.model.item(item.row(), 1).text()

            if item.checkState() == Qt.Checked:
                if item_name not in self.checked_item:
                    self.checked_item.append(item_name)
            else:
                if item_name in self.checked_item:
                    self.checked_item.remove(item_name)

    def MessageBox_checking(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Windows Artifact Collector")
        msg_box.setText("수집할 항목을 선택하세요")
        msg_box.setStandardButtons(QMessageBox.Ok)

        msg_box.exec()

    def MessageBox_path(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Windows Artifact Collector")
        msg_box.setText("저장 경로를 선택하세요")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    def MessageBox_export(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Windows Artifact Collector")
        msg_box.setText("압축파일의 파일명을 입력하세요")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
    
    def MessageBox_collect_end(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Windows Artifact Collector")
        msg_box.setText("아티팩트 수집이 완료되었습니다")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    # 수집하기 버튼 클릭 시 실행
    def exportArtifact(self):
        zip_file_name = self.text_box.text()

        if not self.checked_item:
            self.MessageBox_checking()
        else:
            if self.output_path is None:
                self.MessageBox_path()
            else:
                if not self.export_checked:
                    self.progress_window = ProgressWindowCollect(self)  # 프로그레스바 창
                    self.worker = ArtifactCollectorThread(self.checked_item, self.output_path, self.export_checked)
                    self.worker.progress_changed.connect(self.update_progress_bar)  # 진행률 업데이트
                    self.worker.finished.connect(self.on_worker_finished)  # 작업 완료시 호출
                    self.progress_window.show()  # 프로그레스바 창 표시
                    self.worker.start()  # 백그라운드 작업 시작
                else:
                    if zip_file_name.strip() == "":
                        self.MessageBox_export()
                    else:
                        self.progress_window = ProgressWindowCollect(self)
                        self.worker = ArtifactCollectorThread(self.checked_item, self.output_path, self.export_checked, zip_file_name)
                        self.worker.progress_changed.connect(self.update_progress_bar)
                        self.worker.finished.connect(self.on_worker_finished)
                        self.progress_window.show()
                        self.worker.start()
    
    def update_progress_bar(self, value, message):
        self.progress_window.progress_bar.setValue(value)
        self.progress_window.setWindowTitle(f"진행 상태: {message}")
    
    def on_worker_finished(self):
        self.progress_window.close()
        self.MessageBox_collect_end()
#-----------------------------------------------------------------------------------------


    # 시스템 정보 출력하는 함수
    def show_systeminfo(self):
        self.sys_info_window = SystemInfoWindow(self)

        dialog_width = self.sys_info_window.width()
        dialog_height = self.sys_info_window.height()
        main_window_rect = self.geometry()
        dialog_x = main_window_rect.x() + ((main_window_rect.width() - dialog_width) // 4)
        dialog_y = main_window_rect.y() + ((main_window_rect.height() + dialog_height) // 4)
            
        self.sys_info_window.move(int(dialog_x), int(dialog_y))
        self.sys_info_window.show()   


    # ================= 리스트 영역 ===================

    # 전체 선택 버튼
    def toggle_select_all(self, state):
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for row in range(self.model.rowCount()):
            item = self.model.item(row, 0)
            item.setCheckState(check_state)


    # 검색 함수
    def search_word(self, text):
        escaped_text = re.escape(text)
        filter_reg_exp = QRegExp(escaped_text, Qt.CaseInsensitive)
        self.proxy_model.setFilterRegExp(filter_reg_exp)
    

    # 깔때기 클릭 시 나타나는 창(카테고리 선택 창)
    def open_options_dialog(self):
        options = ["Antivirus", "Browser", "Windows", "Apps", "Logs", "P2P", "WSA", "WSL"]
        dialog = OptionsDialog(options, self)
            
        # Position the dialog at the center of the main window
        dialog_width = dialog.width()
        dialog_height = dialog.height()
        main_window_rect = self.geometry()
        dialog_x = main_window_rect.x() + main_window_rect.width() - dialog_width - 65.0
        dialog_y = main_window_rect.y() + ((main_window_rect.height() - dialog_height) // 4) - 15.0
        dialog.move(int(dialog_x), int(dialog_y))

        if dialog.exec_() == QDialog.Accepted:
            self.update_filter()


    # Name 클릭 시 오름/내림차순 정렬하는 함수
    def sort_by_column(self, index):
        if index == 1:  
            self.proxy_model.sort(index, self.sort_order)
            
            # 다음 클릭 시 반대 방향으로 정렬되도록 설정
            if self.sort_order == Qt.AscendingOrder:
                self.sort_order = Qt.DescendingOrder
            else:
                self.sort_order = Qt.AscendingOrder

    def sort_by_category(self):
        self.proxy_model.sort(1, Qt.AscendingOrder)
        self.proxy_model.sort(2, Qt.AscendingOrder)

    # 전체 리스트 load
    def load_init_data(self):  
        
        for instance in Artifacts.instances:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            checkbox_item.setCheckState(Qt.Unchecked)
            name_item = QStandardItem(instance.name)
            name_item.setEditable(False)
            category_item = QStandardItem(instance.category)
            category_item.setEditable(False)
            self.model.appendRow([checkbox_item, name_item, category_item])

        self.proxy_model.setDynamicSortFilter(True) # <- 불러온 인스턴스 정렬 가능하게끔 만들어주는 코드라고 함

        for row in range(self.model.rowCount()):
            for column in range(self.model.columnCount()):
                item = self.model.item(row, column)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        
        self.checked_item.clear()

    # exist 조건부 리스트 load
    def load_exist_data(self):
        
        for instance in Artifacts.instances:
            if instance.exist:  # exist가 True인지 확인
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Unchecked)
                name_item = QStandardItem(instance.name)
                name_item.setEditable(False)
                category_item = QStandardItem(instance.category)
                category_item.setEditable(False)
                self.model.appendRow([checkbox_item, name_item, category_item])

        self.proxy_model.setDynamicSortFilter(True)  # 정렬 가능하게끔 설정

        for row in range(self.model.rowCount()):
            for column in range(self.model.columnCount()):
                item = self.model.item(row, column)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        
        self.checked_item.clear()

    # time 조건부 리스트 load
    def load_time_data(self):
        
        for instance in Artifacts.instances:
            if instance.time:  # time이 True인지 확인
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Unchecked)
                name_item = QStandardItem(instance.name)
                name_item.setEditable(False)
                category_item = QStandardItem(instance.category)
                category_item.setEditable(False)
                self.model.appendRow([checkbox_item, name_item, category_item])

        self.proxy_model.setDynamicSortFilter(True)  # 정렬 가능하게끔 설정

        for row in range(self.model.rowCount()):
            for column in range(self.model.columnCount()):
                item = self.model.item(row, column)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        
        self.checked_item.clear()

#==========================체크박스=====================

    def toggle_filter(self, state):
        if state == Qt.Checked:
            self.apply_filter()  # 체크된 경우 필터 적용
        else:
            self.remove_filter()  # 체크 해제된 경우 필터 제거
       # 체크박스의 상태 변경 신호를 연결
    
    def apply_filter(self):
        checked_rows = []
        for row in range(self.model.rowCount()):
            checkbox_item = self.model.item(row, 0)
            if checkbox_item.checkState() == Qt.Checked:
                checked_rows.append(self.model.item(row, 1).text())


        if checked_rows:
            # 필터링을 위한 문자열 설정
            filter_pattern = [f'^{re.escape(row)}$' for row in checked_rows]

            # '|'로 연결된 패턴을 사용하지 않고, 각 항목에 대해 개별적으로 체크
            self.proxy_model.setFilterFixedString("")  # 초기화

            # 필터링을 위한 조건 생성
            self.proxy_model.setFilterRegExp(QRegExp('|'.join(filter_pattern)))  # 정규 표현식으로 패턴 설정
            self.proxy_model.invalidateFilter()
            filtered_rows = [self.proxy_model.index(i, 1).data() for i in range(self.proxy_model.rowCount())]
            
        else:
            self.proxy_model.setFilterRegExp("")  # 모든 항목 표시

        self.proxy_model.invalidateFilter()
        
        for opt in ["Antivirus", "Browser", "Windows", "Apps", "Logs", "P2P", "WSA", "WSL"]:
            setattr(OptionSelector, opt, False)# 체크빼기
        

    def remove_filter(self):
        # 필터를 제거하고 모든 항목 표시
        self.proxy_model.setFilterRegExp("")
        self.proxy_model.invalidateFilter()
#===============================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())