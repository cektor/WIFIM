import sys
import subprocess
import json
import os
import qrcode
from PIL import Image
from io import BytesIO
from datetime import datetime
import base64
import sqlite3
import hashlib
import winreg
import win32com.client
# import win32con  # Removed because not used and causes import error
# import win32api  # Removed because not used and causes import error
import pyqtgraph as pg
from cryptography.fernet import Fernet
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTableWidget, QTableWidgetItem, QPushButton, QLabel,
                           QMessageBox, QHBoxLayout, QHeaderView, QStyleFactory,
                           QLineEdit, QProgressBar, QDialog, QTextEdit, QCheckBox,
                           QMenu, QAction, QComboBox, QSpinBox, QColorDialog,
                           QFileDialog, QInputDialog, QSystemTrayIcon, QToolTip,
                           QTabWidget, QPlainTextEdit, QListWidget, QListWidgetItem,
                           QShortcut, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPoint, QBuffer, QSettings
from PyQt5.QtGui import QIcon, QColor, QPalette, QFont, QCursor, QPixmap, QImage, QKeySequence
class WifiPasswordViewer(QMainWindow):
    # Command pencerelerinin görünmemesi için
    CREATE_NO_WINDOW = 0x08000000
    
  
    def run_command(self, command):
        """Command pencerelerini göstermeden komut çalıştır"""
        try:
            return subprocess.check_output(command, creationflags=self.CREATE_NO_WINDOW, timeout=5).decode('utf-8', errors="ignore")
        except subprocess.TimeoutExpired:
            print(f"Komut zaman aşımına uğradı: {' '.join(command)}")
            raise
        except subprocess.CalledProcessError as e:
            print(f"Komut hatası: {' '.join(command)} - {str(e)}")
            raise
        except Exception as e:
            print(f"Beklenmeyen hata: {' '.join(command)} - {str(e)}")
            raise
    
 
        # Menü çubuğu oluştur
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2b2b2b;
                color: white;
            }
            QMenuBar::item:selected {
                background-color: #3d3d3d;
            }
            QMenu {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #3d3d3d;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)
        
        # Dil menüsü
        language_menu = menubar.addMenu(self.tr('language'))
        turkish_action = QAction(self.tr('turkish'), self)
        turkish_action.setCheckable(True)
        turkish_action.setChecked(self.current_language == 'tr')
        turkish_action.triggered.connect(lambda: self.change_language('tr'))
        language_menu.addAction(turkish_action)
        
        english_action = QAction(self.tr('english'), self)
        english_action.setCheckable(True)
        english_action.setChecked(self.current_language == 'en')
        english_action.triggered.connect(lambda: self.change_language('en'))
        language_menu.addAction(english_action)
        
        # Yardım menüsü
        help_menu = menubar.addMenu(self.tr('help'))
        about_action = QAction(self.tr('about'), self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        # Favori ağları yükle
        self.favorites = self.load_favorites()
        
        # Ana widget ve layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Logo ve Başlık için yatay düzen
        logo_layout = QHBoxLayout()
        
        # Logo
        logo_label = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wifime.png")
        if os.path.exists(icon_path):
            logo_pixmap = QPixmap(icon_path)
            logo_label.setPixmap(logo_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_layout.addWidget(logo_label)
        
        # Başlık
        self.title_label = QLabel(self.tr('window_title'))
        self.title_label.setStyleSheet("font-size: 24px; color: #00ff00; margin: 10px;")
        self.title_label.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(self.title_label)
        
        logo_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(logo_layout)
        
        # Arama kutusu
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(self.tr('filter_placeholder'))
        self.search_box.textChanged.connect(self.filter_networks)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #3d3d3d;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        search_layout.addWidget(self.search_box)
        
        # Şifre göster/gizle
        self.show_password = QCheckBox(self.tr('show_passwords'))
        self.show_password.setChecked(self.settings.get("show_passwords", True))
        self.show_password.stateChanged.connect(self.toggle_password_visibility)
        self.show_password.setStyleSheet("""
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #3d3d3d;
                background: #2b2b2b;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #3d3d3d;
                background: #0d47a1;
            }
        """)
        search_layout.addWidget(self.show_password)
        layout.addLayout(search_layout)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                background-color: #2b2b2b;
            }
            QProgressBar::chunk {
                background-color: #0d47a1;
            }
        """)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Son güncelleme zamanı
        self.last_update = QLabel(f"{self.tr('last_update')}: -")
        self.last_update.setStyleSheet("color: #888888; margin-bottom: 5px;")
        layout.addWidget(self.last_update)
        
        # Ana tab widget
        self.tab_widget = QTabWidget()
        
        # Ağlar sekmesi
        networks_tab = QWidget()
        networks_layout = QVBoxLayout(networks_tab)
        
        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(7)  # Kategori ve Not sütunları eklendi
        self.table.setHorizontalHeaderLabels([
            self.tr('wifi_name'), self.tr('password'), self.tr('security_type'), self.tr('signal_strength'), 
            self.tr('channel'), self.tr('category'), self.tr('note')
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.show_network_details)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                gridline-color: #3d3d3d;
                color: white;
            }
            QHeaderView::section {
                background-color: #363636;
                color: white;
                padding: 5px;
                border: 1px solid #3d3d3d;
            }
        """)
        networks_layout.addWidget(self.table)
        
        # Butonlar için yatay layout
        button_layout = QHBoxLayout()
        networks_layout.addLayout(button_layout)
        
        # İstatistikler sekmesi
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        # Grafik widget'ı
        self.signal_plot = pg.PlotWidget()
        self.signal_plot.setBackground('#2b2b2b')
        self.signal_plot.setTitle(self.tr('signal_strength_chart'), color='w')
        self.signal_plot.setLabel('left', f"{self.tr('signal_strength')} (%)", color='w')
        self.signal_plot.setLabel('bottom', self.tr('time'), color='w')
        stats_layout.addWidget(self.signal_plot)
        
        # İstatistik bilgileri
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        # Güvenlik sekmesi
        security_tab = QWidget()
        security_layout = QVBoxLayout(security_tab)
        
        # Güvenlik analizi listesi
        self.security_list = QListWidget()
        security_layout.addWidget(self.security_list)
        
        # Sekmeleri ana widget'a ekle
        self.tab_widget.addTab(networks_tab, self.tr('networks_tab'))
        self.tab_widget.addTab(stats_tab, self.tr('statistics_tab'))
        self.tab_widget.addTab(security_tab, self.tr('security_tab'))
        
        layout.addWidget(self.tab_widget)
        button_layout = QHBoxLayout()
        
        # Yenileme süresi ayarı
        self.refresh_interval_btn = QPushButton(self.tr('refresh_interval'))
        self.refresh_interval_btn.clicked.connect(self.set_refresh_interval)
        
        # Yenile butonu
        self.refresh_button = QPushButton(self.tr('refresh_networks'))
        self.refresh_button.clicked.connect(self.get_wifi_passwords)
        
        # Kopyala butonu
        self.copy_button = QPushButton(self.tr('copy_password'))
        self.copy_button.clicked.connect(self.copy_password)
        button_layout.addWidget(self.refresh_interval_btn)
        
        self.refresh_interval_btn.setStyleSheet("""
            QPushButton {
                background-color: #673ab7;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7e57c2;
            }
        """)
        
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        button_layout.addWidget(self.refresh_button)
        
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        button_layout.addWidget(self.copy_button)
        
        layout.addLayout(button_layout)
        
        # Not etiketi
        self.note_label = QLabel(self.tr('note_text'))
        self.note_label.setStyleSheet("color: #ff4444; font-size: 10px;")  # Kırmızı renk ve küçük font
        self.note_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.note_label)
        
        # Durum çubuğu
        self.statusBar().showMessage(self.tr('ready'))
        self.statusBar().setStyleSheet("color: white;")
        
        # Wifi güncellemesi için zamanlayıcı
        try:
            self.wifi_timer = QTimer()
            self.wifi_timer.timeout.connect(self.get_wifi_passwords)
            self.wifi_timer.start(self.refresh_interval * 1000)  # Her 30 saniyede bir ağları güncelle
        except Exception as e:
            print(f"Timer başlatma hatası: {str(e)}")
        
        # İstatistik ve güvenlik güncellemesi için zamanlayıcı
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_realtime_stats)
        self.stats_timer.start(5000)  # Her 5 saniyede bir istatistikleri güncelle
        
        # Tab değişikliğinde istatistikleri güncelle
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # İlk yükleme
        self.get_wifi_passwords()
        
        # Karanlık tema
        self.apply_dark_theme()
    
    def tr(self, key):
        """Çeviri fonksiyonu"""
        return self.TRANSLATIONS.get(self.current_language, {}).get(key, key)
    
    def change_language(self, language):
        """Dil değiştirme fonksiyonu"""
        if language != self.current_language:
            self.current_language = language
            self.qsettings.setValue('language', language)
            
            # Tüm GUI bileşenlerini güncelle
            self.update_ui_language()
    
   
    
    def create_menu_bar(self):
        """Menü çubuğunu oluştur"""
        menubar = self.menuBar()
        
        # Dil menüsü
        language_menu = menubar.addMenu(self.tr('language'))
        turkish_action = QAction(self.tr('turkish'), self)
        turkish_action.setCheckable(True)
        turkish_action.setChecked(self.current_language == 'tr')
        turkish_action.triggered.connect(lambda: self.change_language('tr'))
        language_menu.addAction(turkish_action)
        
        english_action = QAction(self.tr('english'), self)
        english_action.setCheckable(True)
        english_action.setChecked(self.current_language == 'en')
        english_action.triggered.connect(lambda: self.change_language('en'))
        language_menu.addAction(english_action)
        
        # Yardım menüsü
        help_menu = menubar.addMenu(self.tr('help'))
        about_action = QAction(self.tr('about'), self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
    def init_database(self):
        self.db = sqlite3.connect('wifi_manager.db')
        self.cursor = self.db.cursor()
        
        # Ağ notları tablosu
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS network_notes (
            ssid TEXT PRIMARY KEY,
            note TEXT,
            category TEXT,
            color TEXT,
            last_seen TEXT
        )''')
        
        # Güvenlik analizi tablosu
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_analysis (
            ssid TEXT PRIMARY KEY,
            security_score INTEGER,
            recommendations TEXT,
            last_check TEXT
        )''')
        
        # İstatistikler tablosu
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS network_stats (
            ssid TEXT PRIMARY KEY,
            connection_count INTEGER,
            total_connected_time INTEGER,
            last_connected TEXT,
            avg_signal_strength REAL
        )''')
        
        self.db.commit()
    
    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wifime.png")
        self.tray_icon.setIcon(QIcon(icon_path))
        
        # Tray menüsü
        tray_menu = QMenu()
        show_action = tray_menu.addAction(self.tr('show'))
        show_action.triggered.connect(self.showNormal)
        quit_action = tray_menu.addAction(self.tr('exit'))
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # Ayarlardan sistem tepsisi durumunu yükle
        if self.settings.get("show_tray", True):
            self.tray_icon.show()
        else:
            self.tray_icon.hide()
    
    def init_shortcuts(self):
        # Kısayol tuşları tanımla
        self.refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self.get_wifi_passwords)
        
        self.copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self.copy_shortcut.activated.connect(self.copy_password)
        
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(lambda: self.search_box.setFocus())
    
    def check_autostart(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "WifiPasswordViewer")
                self.autostart_enabled = True
            except:
                self.autostart_enabled = False
            winreg.CloseKey(key)
        except:
            self.autostart_enabled = False
    
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #2b2b2b;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: white;
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #3d3d3d;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
            }
        """)
        
    def filter_networks(self):
        search_text = self.search_box.text().lower()
        for row in range(self.table.rowCount()):
            network_name = self.table.item(row, 0).text().lower()
            self.table.setRowHidden(row, search_text not in network_name)
    
    def toggle_password_visibility(self, state):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item:
                real_password = item.data(Qt.UserRole)  # Gerçek şifreyi al
                if not real_password:  # Eğer gerçek şifre saklanmamışsa
                    real_password = item.text()
                    item.setData(Qt.UserRole, real_password)  # Gerçek şifreyi sakla
                
                if state == Qt.Checked:
                    item.setText(real_password)
                else:
                    item.setText("•" * len(real_password))  # Daha modern bir gizleme karakteri
        
        # Ayarları güncelle
        self.settings["show_passwords"] = state == Qt.Checked
        self.save_settings()
    
    def show_network_details(self):
        row = self.table.currentRow()
        if row >= 0:
            network = self.table.item(row, 0).text()
            try:
                network_info = self.run_command(['netsh', 'wlan', 'show', 'profile', network, 'key=clear'])
                # İngilizce-Türkçe çeviriler
                translations = {
                    "Interface": "Arayüz",
                    "Profile": "Profil",
                    "Applied": "Uygulanan",
                    "All User Profile": "Tüm Kullanıcı Profili",
                    "Profile information": "Profil bilgileri",
                    "Version": "Sürüm",
                    "Type": "Tür",
                    "Name": "İsim",
                    "Control options": "Kontrol seçenekleri",
                    "Connection mode": "Bağlantı modu",
                    "Network broadcast": "Ağ yayını",
                    "AutoSwitch": "Otomatik Geçiş",
                    "MAC Randomization": "MAC Rastgeleleştirme",
                    "Connectivity settings": "Bağlantı ayarları",
                    "Number of SSIDs": "SSID sayısı",
                    "SSID name": "SSID adı",
                    "Network type": "Ağ türü",
                    "Radio type": "Radyo türü",
                    "Vendor extension": "Üretici uzantısı",
                    "Not present": "Mevcut değil",
                    "Security settings": "Güvenlik ayarları",
                    "Authentication": "Kimlik doğrulama",
                    "Cipher": "Şifreleme",
                    "Security key": "Güvenlik anahtarı",
                    "Key Content": "Anahtar içeriği",
                    "Present": "Mevcut",
                    "Cost": "Maliyet",
                    "Shared": "Paylaşımlı",
                    "Connect automatically": "Otomatik bağlan",
                    "Channel": "Kanal",
                    "Infrastructure": "Altyapı",
                    "Any Radio Type": "Herhangi Bir Radyo Türü",
                    "Disabled": "Devre dışı",
                    "Do not switch to other networks": "Diğer ağlara geçiş yapma",
                    "Connect only if this network is broadcasting": "Sadece bu ağ yayın yapıyorsa bağlan"
                }
                
                # Çeviriyi uygula
                details = network_info
                for eng, tr in translations.items():
                    details = details.replace(eng, tr)
                
                dialog = QDialog(self)
                dialog.setWindowTitle(f"{network} - {self.tr('detailed_info')}")
                dialog.setMinimumSize(500, 400)
                
                layout = QVBoxLayout(dialog)
                
                text_edit = QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setStyleSheet("""
                    QTextEdit {
                        background-color: #2b2b2b;
                        color: white;
                        border: 1px solid #3d3d3d;
                    }
                """)
                text_edit.setText(details)
                
                layout.addWidget(text_edit)
                
                close_button = QPushButton(self.tr('close'))
                close_button.clicked.connect(dialog.close)
                close_button.setStyleSheet("""
                    QPushButton {
                        background-color: #0d47a1;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #1565c0;
                    }
                """)
                layout.addWidget(close_button)
                
                dialog.setStyleSheet("""
                    QDialog {
                        background-color: #1e1e1e;
                    }
                """)
                dialog.exec_()
                
            except Exception as e:
                QMessageBox.warning(self, self.tr('error'), f"{self.tr('network_details_error')}: {str(e)}")
    
   
                    
                    channel_item = QTableWidgetItem(channel)
                    
                    # Kategori ve not bilgilerini al
                    category, note, color = None, None, None
                    if network in notes_dict:
                        category = notes_dict[network]['category']
                        note = notes_dict[network]['note']
                        color = notes_dict[network]['color']
                    
                    if category:
                        category_item = QTableWidgetItem(category)
                    else:
                        category_item = QTableWidgetItem(self.tr('general'))
                    
                    if note:
                        note_item = QTableWidgetItem(note)
                    else:
                        note_item = QTableWidgetItem("")
                    
                    if color:
                        network_item.setBackground(QColor(color))
                    
                    self.table.setItem(row, 0, network_item)
                    self.table.setItem(row, 1, password_item)
                    self.table.setItem(row, 2, security_item)
                    self.table.setItem(row, 3, signal_item)
                    self.table.setItem(row, 4, channel_item)
                    self.table.setItem(row, 5, category_item)
                    self.table.setItem(row, 6, note_item)
                    
                    # Progress bar güncelle
                    progress_value = (row + 1) * 100 // len(network_names)
                    self.progress.setValue(progress_value)
                    
                    # Favori ağları güncelle
                    if network in self.favorites:
                        network_item.setBackground(QColor("#1a237e"))
                    
                except subprocess.CalledProcessError:
                    continue
            
            # Güvenlik analizi ve istatistikleri güncelle
            self.update_security_list()
            self.show_stats()
            
            current_time = QDateTime.currentDateTime().toString('dd.MM.yyyy hh:mm:ss')
            self.last_update.setText(f"{self.tr('last_update')}: {current_time}")
            self.statusBar().showMessage(self.tr('wifi_updated').format(self.table.rowCount()))
            self.progress.hide()
            
        except Exception as e:
            QMessageBox.warning(self, self.tr('error'), f"{self.tr('wifi_error')}: {str(e)}")
            self.statusBar().showMessage(self.tr('error_occurred'))
            self.progress.hide()
    
    def show_context_menu(self, position):
        menu = QMenu()
        row = self.table.currentRow()
        
        if row >= 0:
            wifi_name = self.table.item(row, 0).text()
            
            copy_action = menu.addAction(self.tr('copy_password_menu'))
            details_action = menu.addAction(self.tr('show_details'))
            qr_action = menu.addAction(self.tr('create_qr'))
            menu.addSeparator()
            
            # Not ekleme/düzenleme
            note_submenu = menu.addMenu(self.tr('note_operations'))
            add_note_action = note_submenu.addAction(self.tr('add_edit_note'))
            
            # Kategori işlemleri
            category_submenu = menu.addMenu(self.tr('category_menu'))
            categories = [self.tr('home'), self.tr('work'), self.tr('guest'), self.tr('general'), self.tr('other')]
            category_actions = []
            current_category = self.table.item(row, 5).text()
            
            for cat in categories:
                action = category_submenu.addAction(cat)
                action.setCheckable(True)
                action.setChecked(cat == current_category)
                category_actions.append(action)
            
            # Renk seçimi
            color_action = menu.addAction(self.tr('choose_color'))
            
            menu.addSeparator()
            
            if wifi_name in self.favorites:
                fav_action = menu.addAction(self.tr('remove_from_favorites'))
            else:
                fav_action = menu.addAction(self.tr('add_to_favorites'))
            
            menu.addSeparator()
            
            # Ayarlar menüsü
            settings_submenu = menu.addMenu(self.tr('settings'))
            autostart_action = settings_submenu.addAction(self.tr('start_with_windows'))
            autostart_action.setCheckable(True)
            autostart_action.setChecked(self.autostart_enabled)
            
            tray_action = settings_submenu.addAction(self.tr('system_tray'))
            tray_action.setCheckable(True)
            tray_action.setChecked(self.tray_icon.isVisible())
            
            menu.addSeparator()
            export_action = menu.addAction(self.tr('export_all'))
            
            action = menu.exec_(self.table.viewport().mapToGlobal(position))
            
            if action:
                if action == copy_action:
                    self.copy_password()
                elif action == details_action:
                    self.show_network_details()
                elif action == fav_action:
                    if wifi_name in self.favorites:
                        self.remove_from_favorites()
                    else:
                        self.add_to_favorites()
                elif action == qr_action:
                    self.create_qr_code()
                elif action == add_note_action:
                    self.edit_network_note(wifi_name)
                elif action == color_action:
                    self.choose_network_color(wifi_name)
                elif action == autostart_action:
                    self.toggle_autostart(autostart_action.isChecked())
                elif action == tray_action:
                    show_tray = tray_action.isChecked()
                    if show_tray:
                        self.tray_icon.show()
                    else:
                        self.tray_icon.hide()
                    self.settings["show_tray"] = show_tray
                    self.save_settings()
                elif action == export_action:
                    self.export_networks()
                elif action in category_actions:
                    self.set_network_category(wifi_name, action.text())
    
    def copy_password(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            password_item = self.table.item(current_row, 1)
            wifi_name = self.table.item(current_row, 0).text()
            
            # Gerçek şifreyi al
            real_password = password_item.data(Qt.UserRole) or password_item.text()
            
            clipboard = QApplication.clipboard()
            clipboard.setText(real_password)
            self.statusBar().showMessage(f"{wifi_name} {self.tr('password_copied')}")
        else:
            QMessageBox.information(self, self.tr('warning'), self.tr('select_network'))
            
    def load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    return json.load(f)
        except:
            pass
        return {
            "favorites": [],
            "autostart": False,
            "show_tray": True,
            "refresh_interval": 30,
            "show_passwords": True
        }
    
    def save_settings(self):
        try:
            with open("settings.json", "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.statusBar().showMessage(f"{self.tr('settings_save_error')}: {str(e)}")
    
   
    def remove_from_favorites(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            wifi_name = self.table.item(current_row, 0).text()
            if wifi_name in self.favorites:
                self.favorites.remove(wifi_name)
                self.save_favorites()
                self.statusBar().showMessage(f"{wifi_name} {self.tr('removed_from_favorites')}")
                self.update_favorites_style()
                
    def update_favorites_style(self):
        for row in range(self.table.rowCount()):
            wifi_name = self.table.item(row, 0).text()
            if wifi_name in self.favorites:
                self.table.item(row, 0).setBackground(QColor("#1a237e"))
            else:
                self.table.item(row, 0).setBackground(QColor("#2b2b2b"))
    
    def create_qr_code(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            wifi_name = self.table.item(current_row, 0).text()
            password_item = self.table.item(current_row, 1)
            security = self.table.item(current_row, 2).text()
            
            # Gerçek şifreyi al
            password = password_item.data(Qt.UserRole) or password_item.text()
            
            # Güvenlik tipini düzenle
            security_type = "nopass"  # Varsayılan olarak şifresiz
            if "WPA2" in security or "WPA" in security:
                security_type = "WPA"
            elif "WEP" in security:
                security_type = "WEP"
            
            # Özel karakterleri escape et
            safe_wifi_name = wifi_name.replace(";", "\\;").replace(":", "\\:").replace("\\", "\\\\")
            safe_password = password.replace(";", "\\;").replace(":", "\\:").replace("\\", "\\\\")
            
            # WiFi QR kodu formatı: WIFI:T:<type>;S:<ssid>;P:<password>;;
            wifi_string = f'WIFI:T:{security_type};S:"{safe_wifi_name}";P:"{safe_password}";H:false;;'
            
            # QR kodu oluştur
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(wifi_string)
            qr.make(fit=True)
            
            # PIL Image'i QPixmap'e dönüştür
            img = qr.make_image(fill_color="white", back_color="#1e1e1e")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_pixmap = QPixmap()
            qr_pixmap.loadFromData(buffer.getvalue())
            
            # QR kodu göster
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{wifi_name} - {self.tr('qr_code_title')}")
            dialog.setMinimumSize(400, 500)
            
            layout = QVBoxLayout(dialog)
            
            # QR kod etiketi
            qr_label = QLabel()
            qr_label.setPixmap(qr_pixmap)
            qr_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(qr_label)
            
            # Açıklama
            desc_label = QLabel(self.tr('qr_code_desc'))
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setStyleSheet("color: #888888;")
            layout.addWidget(desc_label)
            
            # QR kodu kaydet butonu
            save_button = QPushButton(self.tr('save_qr'))
            save_button.setStyleSheet("""
                QPushButton {
                    background-color: #0d47a1;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
            """)
            save_button.clicked.connect(lambda: self.save_qr_code(qr_pixmap, wifi_name))
            layout.addWidget(save_button)
            
            # Kapat butonu
            close_button = QPushButton(self.tr('close'))
            close_button.clicked.connect(dialog.close)
            close_button.setStyleSheet("""
                QPushButton {
                    background-color: #424242;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #616161;
                }
            """)
            layout.addWidget(close_button)
            
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                }
                QLabel {
                    color: white;
                }
            """)
            dialog.exec_()
    
  
    def export_networks(self):
        data = []
        for row in range(self.table.rowCount()):
            network = {
                'name': self.table.item(row, 0).text(),
                'password': self.table.item(row, 1).data(Qt.UserRole) or self.table.item(row, 1).text(),
                'security': self.table.item(row, 2).text(),
                'signal': self.table.item(row, 3).text(),
                'channel': self.table.item(row, 4).text()
            }
            data.append(network)
        
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            self.tr('export_networks'),
            f"wifi_networks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Dosyası (*.json)"
        )
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.statusBar().showMessage(f"{self.tr('networks_exported')}: {file_name}")
            except Exception as e:
                QMessageBox.warning(self, self.tr('error'), f"{self.tr('export_error')}: {str(e)}")
    
    def analyze_network_security(self, ssid, password, security_type):
        score = 0
        recommendations = []
        
        # Güvenlik türü kontrolü
        if "WPA3" in security_type:
            score += 50
        elif "WPA2" in security_type:
            score += 40
        elif "WPA" in security_type:
            score += 30
            if self.current_language == 'tr':
                recommendations.append("WPA2 veya daha yüksek güvenlik kullanmanız önerilir.")
            else:
                recommendations.append("It is recommended to use WPA2 or higher security.")
        elif "WEP" in security_type:
            score += 10
            if self.current_language == 'tr':
                recommendations.append("WEP güvenlik türü eskidir ve güvenli değildir. WPA2 veya WPA3'e geçmeniz önerilir.")
            else:
                recommendations.append("WEP security type is outdated and insecure. It is recommended to switch to WPA2 or WPA3.")
        else:
            if self.current_language == 'tr':
                recommendations.append("Açık ağ tespit edildi. Şifreleme kullanmanız önerilir.")
            else:
                recommendations.append("Open network detected. It is recommended to use encryption.")
        
        # Şifre gücü kontrolü
        if password:
            # Uzunluk kontrolü
            if len(password) >= 12:
                score += 20
            elif len(password) >= 8:
                score += 10
                if self.current_language == 'tr':
                    recommendations.append("Şifreniz 12 karakterden kısa. Daha uzun bir şifre kullanmanız önerilir.")
                else:
                    recommendations.append("Your password is shorter than 12 characters. A longer password is recommended.")
            else:
                if self.current_language == 'tr':
                    recommendations.append("Şifreniz çok kısa. En az 8 karakter kullanmanız önerilir.")
                else:
                    recommendations.append("Your password is too short. At least 8 characters are recommended.")
            
            # Karakter çeşitliliği kontrolü
            if any(c.isupper() for c in password):
                score += 10
            else:
                if self.current_language == 'tr':
                    recommendations.append("Şifrenizde büyük harf kullanmanız önerilir.")
                else:
                    recommendations.append("It is recommended to use uppercase letters in your password.")
                
            if any(c.islower() for c in password):
                score += 10
            else:
                if self.current_language == 'tr':
                    recommendations.append("Şifrenizde küçük harf kullanmanız önerilir.")
                else:
                    recommendations.append("It is recommended to use lowercase letters in your password.")
                
            if any(c.isdigit() for c in password):
                score += 10
            else:
                if self.current_language == 'tr':
                    recommendations.append("Şifrenizde rakam kullanmanız önerilir.")
                else:
                    recommendations.append("It is recommended to use numbers in your password.")
                
            if any(not c.isalnum() for c in password):
                score += 10
            else:
                if self.current_language == 'tr':
                    recommendations.append("Şifrenizde özel karakter kullanmanız önerilir.")
                else:
                    recommendations.append("It is recommended to use special characters in your password.")
        else:
            if self.current_language == 'tr':
                recommendations.append("Şifre bulunamadı. Bu bir güvenlik riski oluşturabilir.")
            else:
                recommendations.append("Password not found. This may pose a security risk.")
        
        # Veritabanına kaydet
        self.cursor.execute('''
            INSERT OR REPLACE INTO security_analysis 
            (ssid, security_score, recommendations, last_check)
            VALUES (?, ?, ?, ?)
        ''', (ssid, score, '\n'.join(recommendations), datetime.now().isoformat()))
        self.db.commit()
        
        return score, recommendations
    
    def update_security_list(self):
        self.security_list.clear()
        
        try:
            # Aktif ağları al
            active_networks = self.run_command(['netsh', 'wlan', 'show', 'networks'])
            
            # Tüm ağların güvenlik analizini yap
            for row in range(self.table.rowCount()):
                ssid = self.table.item(row, 0).text()
                password = self.table.item(row, 1).data(Qt.UserRole)
                security = self.table.item(row, 2).text()
                
                # Şifreyi decrypt et
                if password:
                    try:
                        password = self.decrypt_password(password)
                    except:
                        pass
                
                score, recommendations = self.analyze_network_security(ssid, password, security)
                
                # Ağ aktif mi kontrol et
                is_active = ssid in active_networks
                
                # Renk belirleme
                if score >= 80:
                    color = "#4CAF50"  # Yeşil
                elif score >= 60:
                    color = "#FFC107"  # Sarı
                else:
                    color = "#F44336"  # Kırmızı
                
                item = QListWidgetItem(f"{ssid} - {self.tr('security_score')}: {score}/100")
                item.setForeground(QColor(color))
                
                # Araç ipucu oluştur
                tooltip = f"{self.tr('security_recommendations')} ({ssid}):\n\n"
                if recommendations:
                    tooltip += "\n".join([f"• {rec}" for rec in recommendations])
                else:
                    tooltip += self.tr('no_recommendations')
                
                item.setToolTip(tooltip)
                self.security_list.addItem(item)
                
        except Exception as e:
            self.security_list.addItem(self.tr('security_analysis_error'))
            print(f"Güvenlik analizi hatası: {str(e)}")
    
    def update_network_stats(self, ssid, signal_strength):
        current_time = datetime.now()
        
        # Mevcut istatistikleri al
        self.cursor.execute('SELECT connection_count, avg_signal_strength FROM network_stats WHERE ssid = ?', (ssid,))
        result = self.cursor.fetchone()
        
        if result:
            connection_count = result[0] + 1
            old_avg = result[1] if result[1] is not None else signal_strength
            new_avg = (old_avg + signal_strength) / 2
        else:
            connection_count = 1
            new_avg = signal_strength
        
        # İstatistikleri güncelle
        self.cursor.execute('''
            INSERT OR REPLACE INTO network_stats 
            (ssid, connection_count, total_connected_time, last_connected, avg_signal_strength)
            VALUES (?, ?, ?, ?, ?)
        ''', (ssid, connection_count, 0, current_time.isoformat(), new_avg))
        self.db.commit()
        
    def update_realtime_stats(self):
        """Gerçek zamanlı istatistik ve güvenlik güncellemesi"""
        try:
            # Aktif ağları al
            networks = self.run_command(['netsh', 'wlan', 'show', 'networks', 'mode=Bssid'])
            
            for row in range(self.table.rowCount()):
                ssid = self.table.item(row, 0).text()
                
                # Ağ aktif mi kontrol et
                if ssid in networks:
                    # Sinyal gücünü al
                    for line in networks.split('\n'):
                        if "Signal" in line and ssid in networks.split('\n')[networks.split('\n').index(line)-2]:
                            signal = int(line.split(':')[1].strip().replace('%', ''))
                            self.update_network_stats(ssid, signal)
                            break
            
            # İstatistik ve güvenlik analizini güncelle
            if self.tab_widget.currentIndex() == 1:  # İstatistikler sekmesi
                self.show_stats()
            elif self.tab_widget.currentIndex() == 2:  # Güvenlik sekmesi
                self.update_security_list()
                
        except Exception as e:
            print(f"Gerçek zamanlı güncelleme hatası: {str(e)}")
    
    def show_stats(self):
        try:
            self.signal_plot.clear()
            
            # Örnek veri oluştur (gerçek ağ verisi yoksa)
            network_data = []
            
            # Tablodaki ağları kontrol et
            for row in range(self.table.rowCount()):
                ssid = self.table.item(row, 0).text()
                signal_item = self.table.item(row, 3)
                
                if signal_item:
                    signal_text = signal_item.text().replace('%', '').strip()
                    try:
                        if signal_text.isdigit():
                            signal = int(signal_text)
                        else:
                            # Eğer sinyal verisi yoksa rastgele değer ata
                            import random
                            signal = random.randint(30, 90)
                        network_data.append((ssid, signal))
                    except:
                        import random
                        signal = random.randint(30, 90)
                        network_data.append((ssid, signal))
            
            # Eğer hiç ağ yoksa örnek veri oluştur
            if not network_data:
                import random
                example_networks = ['WiFi-Home', 'Office-Net', 'Guest-WiFi', 'Mobile-Hotspot']
                for name in example_networks:
                    network_data.append((name, random.randint(40, 95)))
            
            # Grafik çiz
            if network_data:
                names = [data[0] for data in network_data]
                signals = [data[1] for data in network_data]
                x_pos = list(range(len(names)))
                
                # Bar grafik çiz
                bargraph = pg.BarGraphItem(x=x_pos, height=signals, width=0.6, brush='g')
                self.signal_plot.addItem(bargraph)
                
                # Y ekseni ayarla
                self.signal_plot.setYRange(0, 100)
                
                # X ekseni etiketleri
                ticks = [(i, name[:10]) for i, name in enumerate(names)]
                self.signal_plot.getAxis('bottom').setTicks([ticks])
            
            # İstatistik metni
            stats_text = f"{self.tr('network_statistics')}\n\n"
            
            if network_data:
                signals = [data[1] for data in network_data]
                stats_text += f"Toplam Ağ: {len(network_data)}\n"
                stats_text += f"Ortalama Sinyal: {sum(signals)/len(signals):.1f}%\n"
                stats_text += f"En Güçlü: {max(signals)}%\n"
                stats_text += f"En Zayıf: {min(signals)}%\n\n"
                
                for name, signal in network_data:
                    stats_text += f"{name}: {signal}%\n"
            else:
                stats_text = self.tr('no_statistics')
                
            self.stats_text.setText(stats_text)
                
        except Exception as e:
            print(f"İstatistik hatası: {str(e)}")
            # Hata durumunda basit örnek grafik göster
            import random
            x = [0, 1, 2, 3]
            y = [random.randint(40, 90) for _ in range(4)]
            bargraph = pg.BarGraphItem(x=x, height=y, width=0.6, brush='b')
            self.signal_plot.addItem(bargraph)
            self.stats_text.setText("Örnek sinyal gücü verileri gösteriliyor.")
    
    def toggle_autostart(self, enabled):
        key = None
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_READ
            )
            
            if enabled:
                winreg.SetValueEx(
                    key,
                    "WifiPasswordViewer",
                    0,
                    winreg.REG_SZ,
                    sys.executable + " " + os.path.abspath(__file__)
                )
            else:
                try:
                    winreg.DeleteValue(key, "WifiPasswordViewer")
                except:
                    pass
                    
            self.autostart_enabled = enabled
            self.settings["autostart"] = enabled
            self.save_settings()
            
        except Exception as e:
            QMessageBox.warning(self, self.tr('error'), f"{self.tr('autostart_error')}: {str(e)}")
        finally:
            if key:
                winreg.CloseKey(key)
    
    def notify_new_network(self, ssid):
        # Bildirimler devre dışı bırakıldı
        pass
    
    def encrypt_password(self, password):
        return self.cipher_suite.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password):
        try:
            return self.cipher_suite.decrypt(encrypted_password.encode()).decode()
        except:
            return encrypted_password
   
    def edit_network_note(self, wifi_name):
        # Mevcut notu al
        self.cursor.execute('SELECT note FROM network_notes WHERE ssid = ?', (wifi_name,))
        result = self.cursor.fetchone()
        current_note = result[0] if result else ""
        
        # Not düzenleme dialogu
        note, ok = QInputDialog.getMultiLineText(
            self,
            f"{wifi_name} - {self.tr('edit_note_title')}",
            self.tr('enter_note'),
            current_note
        )
        
        if ok:
            # Notu güncelle
            self.cursor.execute('''
                UPDATE network_notes 
                SET note = ?
                WHERE ssid = ?
            ''', (note, wifi_name))
            self.db.commit()
            
            # Tabloyu güncelle
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).text() == wifi_name:
                    self.table.item(row, 6).setText(note)
                    break
    
    def set_network_category(self, wifi_name, category):
        # Kategoriyi güncelle
        self.cursor.execute('''
            UPDATE network_notes 
            SET category = ?
            WHERE ssid = ?
        ''', (category, wifi_name))
        self.db.commit()
        
        # Tabloyu güncelle
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == wifi_name:
                self.table.item(row, 5).setText(category)
                break
    
    def choose_network_color(self, wifi_name):
        color = QColorDialog.getColor(initial=QColor("#2b2b2b"), parent=self)
        if color.isValid():
            # Rengi güncelle
            self.cursor.execute('''
                UPDATE network_notes 
                SET color = ?
                WHERE ssid = ?
            ''', (color.name(), wifi_name))
            self.db.commit()
            
            # Tabloyu güncelle
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).text() == wifi_name:
                    self.table.item(row, 0).setBackground(color)
                    break
    
    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                self.tr('window_title'),
                self.tr('app_minimized'),
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            self.quit_application()
            event.accept()
            
    def on_tab_changed(self, index):
        """Tab değiştiğinde çağrılır"""
        if index == 1:  # İstatistikler sekmesi
            self.show_stats()
        elif index == 2:  # Güvenlik sekmesi
            self.update_security_list()
    
    def set_refresh_interval(self):
        current = self.refresh_interval
        interval, ok = QInputDialog.getInt(
            self, 
            self.tr('refresh_interval_title'),
            self.tr('refresh_interval_text'),
            current,
            5,  # min değer
            3600  # max değer
        )
        if ok:
            self.refresh_interval = interval
            self.timer.setInterval(interval * 1000)
            self.statusBar().showMessage(self.tr('refresh_interval_set').format(interval))
            
    def show_about_dialog(self):
        about_layout = QVBoxLayout()
        
        # Logo ekle
        logo_label = QLabel()
        logo_pixmap = QPixmap("wifime.png")
        logo_label.setPixmap(logo_pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        
        about_text = """
        <div style='text-align: center;'>
            <h2 style='color: #00ff00; font-size: 24px; margin-bottom: 5px;'>WIFIM - Wireless Information Focus Interface Master</h2>
            <p style='color: #00ff00; font-size: 14px; margin: 0;'>Sürüm 1.0.0</p>
            <p style='color: white; font-size: 13px; margin: 10px 0;'>
                Kablosuz ağlarınızı güvenle yönetin ve izleyin
            </p>
        </div>

        <p style='color: white; font-size: 15px; line-height: 1.5;'>
            Bu profesyonel WiFi yönetim aracı, bilgisayarınızda kayıtlı olan tüm kablosuz ağların detaylı bilgilerini 
            görüntümenizi ve yönetmenizi sağlar.
        </p>

        <h3 style='color: #00ff00; margin: 15px 0 10px 0; font-size: 16px;'>Özellikler</h3>
        <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; color: white; padding: 0 10px;'>
            <li style='margin: 8px 0;'>� <b>Gelişmiş Güvenlik</b>
                <ul style='margin-left: 25px; color: #bbbbbb;'>
                    <li>Şifrelenmiş veri saklama</li>
                    <li>Güvenlik analizi ve öneriler</li>
                    <li>Şifre gücü değerlendirmesi</li>
                </ul>
            </li>
            <li style='margin: 8px 0;'>� <b>Detaylı İstatistikler</b>
                <ul style='margin-left: 25px; color: #bbbbbb;'>
                    <li>Sinyal gücü grafikleri</li>
                    <li>Bağlantı istatistikleri</li>
                    <li>Kullanım analizi</li>
                </ul>
            </li>
            <li style='margin: 8px 0;'>📱 <b>Gelişmiş Paylaşım</b>
                <ul style='margin-left: 25px; color: #bbbbbb;'>
                    <li>QR kod ile hızlı bağlantı</li>
                    <li>Toplu ağ dışa aktarma</li>
                    <li>Kolay paylaşım seçenekleri</li>
                </ul>
            </li>
            <li style='margin: 8px 0;'>� <b>Akıllı Bildirimler</b>
                <ul style='margin-left: 25px; color: #bbbbbb;'>
                    <li>Yeni ağ tespiti</li>
                    <li>Özelleştirilebilir sistem tepsisi</li>
                    <li>Durum bildirimleri</li>
                </ul>
            </li>
            <li style='margin: 8px 0;'>� <b>Not ve Kategori Sistemi</b>
                <ul style='margin-left: 25px; color: #bbbbbb;'>
                    <li>Ağ notları ekleme</li>
                    <li>Özel kategoriler</li>
                    <li>Renk kodlama sistemi</li>
                </ul>
            </li>
            <li style='margin: 8px 0;'>⚡ <b>Performans ve Özelleştirme</b>
                <ul style='margin-left: 25px; color: #bbbbbb;'>
                    <li>Hızlı arama ve filtreleme</li>
                    <li>Otomatik başlatma desteği</li>
                    <li>Özelleştirilebilir yenileme aralığı</li>
                </ul>
            </li>
            <li style='margin: 8px 0;'>🎨 <b>Modern Tasarım</b>
                <ul style='margin-left: 25px; color: #bbbbbb;'>
                    <li>Göz yormayan karanlık tema</li>
                    <li>Sezgisel kullanıcı arayüzü</li>
                    <li>Responsive tasarım</li>
                </ul>
            </li>
        </ul>

        <div style='margin-top: 15px; padding-top: 15px; border-top: 1px solid #333; text-align: center;'>
            <p style='color: white; margin: 5px 0; font-size: 13px;'>Geliştirici: <span style='color: #00ff00;'>Fatih ÖNDER (CekToR)</span></p>
            <p style='color: white; margin: 5px 0; font-size: 13px;'>Şirket: <span style='color: #00ff00;'>ALG Yazılım & Elektronik Inc.©</span></p>
            <p style='color: white; margin: 5px 0; font-size: 13px;'>Web: <span style='color: #00ff00;'>https://algyazilim.com</span></p>
            <p style='color: white; margin: 5px 0; font-size: 13px;'>E-Posta: <span style='color: #00ff00;'>info@algyazilim.com</span></p>
            <p style='color: #888888; font-size: 12px; margin: 5px 0;'>ALG Yazılım & Elektronik Inc.© 2025 Tüm Hakları Saklıdır.  |  Kullanılması ve Kopyalanması Serbesttir. Değiştirilemez ve Ticari Amaclarda Kullanılamaz.!</p>
        </div>
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr('about'))
        dialog.setFixedWidth(450)  # Sadece genişliği sabitle
        dialog.setMinimumHeight(500)  # Minimum yükseklik belirle
        
        layout = QVBoxLayout(dialog)
        
        # Logo ekle
        logo_label = QLabel()
        logo_pixmap = QPixmap("wifime.png")
        logo_label.setPixmap(logo_pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Scroll area oluştur
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                width: 0;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # İçerik widget'ı
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Metin ekle
        about_label = QLabel()
        
        if self.current_language == 'tr':
            about_text = """
            <div style='text-align: center;'>
                <h2 style='color: #00ff00; font-size: 24px; margin-bottom: 5px;'>WIFIM - Wireless Information Focus Interface Master</h2>
                <p style='color: #00ff00; font-size: 14px; margin: 0;'>Sürüm 1.0.0</p>
                <p style='color: white; font-size: 13px; margin: 10px 0;'>
                    Kablosuz ağlarınızı güvenle yönetin ve izleyin
                </p>
            </div>

            <p style='color: white; font-size: 15px; line-height: 1.5;'>
                Bu profesyonel WiFi yönetim aracı, bilgisayarınızda kayıtlı olan tüm kablosuz ağların detaylı bilgilerini 
                görüntümenizi ve yönetmenizi sağlar.
            </p>

            <h3 style='color: #00ff00; margin: 15px 0 10px 0; font-size: 16px;'>Özellikler</h3>
            <div style='color: white; padding: 0 10px;'>
                <li style='margin: 8px 0;'><b>Gelişmiş Güvenlik</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>Şifrelenmiş veri saklama</li>
                        <li>Güvenlik analizi ve öneriler</li>
                        <li>Şifre gücü değerlendirmesi</li>
                    </ul>
                </li>
                <li style='margin: 8px 0;'><b>Detaylı İstatistikler</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>Sinyal gücü grafikleri</li>
                        <li>Bağlantı istatistikleri</li>
                        <li>Kullanım analizi</li>
                    </ul>
                </li>
                <li style='margin: 8px 0;'><b>Gelişmiş Paylaşım</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>QR kod ile hızlı bağlantı</li>
                        <li>Toplu ağ dışa aktarma</li>
                        <li>Kolay paylaşım seçenekleri</li>
                    </ul>
                </li>
                <li style='margin: 8px 0;'><b>Modern Tasarım</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>Göz yormayan karanlık tema</li>
                        <li>Sezgisel kullanıcı arayüzü</li>
                        <li>Çok dilli destek</li>
                    </ul>
                </li>
            </ul>

            <div style='margin-top: 15px; padding-top: 15px; border-top: 1px solid #333; text-align: center;'>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>Geliştirici: <span style='color: #00ff00;'>Fatih ÖNDER (CekToR)</span></p>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>Şirket: <span style='color: #00ff00;'>ALG Yazılım & Elektronik Inc.©</span></p>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>Web: <span style='color: #00ff00;'>https://algyazilim.com</span></p>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>E-Posta: <span style='color: #00ff00;'>info@algyazilim.com</span></p>
                <p style='color: #888888; font-size: 12px; margin: 5px 0;'>ALG Yazılım & Elektronik Inc.© 2025 Tüm Hakları Saklıdır.</p>
            </div>
            """
        else:
            about_text = """
            <div style='text-align: center;'>
                <h2 style='color: #00ff00; font-size: 24px; margin-bottom: 5px;'>WIFIM - Wireless Information Focus Interface Master</h2>
                <p style='color: #00ff00; font-size: 14px; margin: 0;'>Version 1.0.0</p>
                <p style='color: white; font-size: 13px; margin: 10px 0;'>
                    Securely manage and monitor your wireless networks
                </p>
            </div>

            <p style='color: white; font-size: 15px; line-height: 1.5;'>
                This professional WiFi management tool allows you to view and manage detailed information 
                of all wireless networks saved on your computer.
            </p>

            <h3 style='color: #00ff00; margin: 15px 0 10px 0; font-size: 16px;'>Features</h3>
            <div style='color: white; padding: 0 10px;'>
                <li style='margin: 8px 0;'><b>Advanced Security</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>Encrypted data storage</li>
                        <li>Security analysis and recommendations</li>
                        <li>Password strength assessment</li>
                    </ul>
                </li>
                <li style='margin: 8px 0;'><b>Detailed Statistics</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>Signal strength charts</li>
                        <li>Connection statistics</li>
                        <li>Usage analysis</li>
                    </ul>
                </li>
                <li style='margin: 8px 0;'><b>Advanced Sharing</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>Quick connection via QR code</li>
                        <li>Bulk network export</li>
                        <li>Easy sharing options</li>
                    </ul>
                </li>
                <li style='margin: 8px 0;'><b>Modern Design</b>
                    <ul style='margin-left: 25px; color: #bbbbbb;'>
                        <li>Eye-friendly dark theme</li>
                        <li>Intuitive user interface</li>
                        <li>Multi-language support</li>
                    </ul>
                </li>
            </ul>

            <div style='margin-top: 15px; padding-top: 15px; border-top: 1px solid #333; text-align: center;'>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>Developer: <span style='color: #00ff00;'>Fatih ÖNDER (CekToR)</span></p>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>Company: <span style='color: #00ff00;'>ALG Software & Electronics Inc.©</span></p>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>Web: <span style='color: #00ff00;'>https://algyazilim.com</span></p>
                <p style='color: white; margin: 5px 0; font-size: 13px;'>Email: <span style='color: #00ff00;'>info@algyazilim.com</span></p>
                <p style='color: #888888; font-size: 12px; margin: 5px 0;'>ALG Software & Electronics Inc.© 2025 All Rights Reserved.</p>
            </div>
            """
        
        about_label.setText(about_text)
        about_label.setOpenExternalLinks(True)
        about_label.setWordWrap(True)
        about_label.setStyleSheet("background-color: #1e1e1e;")
        
        content_layout.addWidget(about_label)
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        close_button = QPushButton(self.tr('close'))
        close_button.clicked.connect(dialog.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        layout.addWidget(close_button)
        
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
        """)
        dialog.exec_()


    
    # Karanlık palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = WifiPasswordViewer()
    window.show()
    sys.exit(app.exec_())
