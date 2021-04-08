#!/usr/bin/env python3
'''Astroncia IPTV - Cross platform IPTV player'''
# pylint: disable=invalid-name, global-statement, missing-docstring, wrong-import-position, c-extension-no-member, too-many-lines, too-many-statements, broad-except, line-too-long
#
# Icons by Font Awesome ( https://fontawesome.com/ )
# https://fontawesome.com/license
#
# ===
# BIG FAT WARNING: govnokod ahead!
# ===
from pathlib import Path
import sys
import os
import time
import datetime
import json
import locale
import signal
import base64
import argparse
import subprocess
import webbrowser
import multiprocessing
from tkinter import Tk, messagebox
import requests
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5 import QtGui
from data.modules.astroncia.ua import user_agent
from data.modules.astroncia.m3u import M3uParser
from data.modules.astroncia.epg import worker
from data.modules.astroncia.record import record, stop_record
from data.modules.astroncia.format import format_seconds_to_hhmmss
from data.modules.astroncia.conversion import convert_size
from data.modules.astroncia.providers import iptv_providers

if not sys.version_info >= (3, 7, 0):
    print("Incompatible Python version! Required >= 3.7")
    sys.exit(1)

if not (os.name == 'nt' or os.name == 'posix'):
    print("Unsupported platform!")
    sys.exit(1)

WINDOW_SIZE = (1200, 600)
DOCK_WIDGET2_HEIGHT = int(WINDOW_SIZE[1] / 6)
DOCK_WIDGET_WIDTH = int((WINDOW_SIZE[0] / 2) - 200)
TVGUIDE_WIDTH = int((WINDOW_SIZE[0] / 5))
BCOLOR = "#A2A3A3"

if DOCK_WIDGET2_HEIGHT < 0:
    DOCK_WIDGET2_HEIGHT = 0

if DOCK_WIDGET_WIDTH < 0:
    DOCK_WIDGET_WIDTH = 0

def show_exception(e):
    window = Tk()
    window.wm_withdraw()
    messagebox.showinfo(title="Ошибка", message="Ошибка Astroncia IPTV\n\n{}".format(str(e)))
    window.destroy()
    sys.exit(0)

parser = argparse.ArgumentParser(description='Astroncia IPTV')
parser.add_argument('--python')
args1 = parser.parse_args()

if os.name == 'nt':
    a0 = sys.executable
    if args1.python:
        a0 = args1.python
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(Path(os.path.dirname(a0), 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins'))

if __name__ == '__main__':
    try:
        print("Astroncia IPTV запускается...")
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        modules_path = str(Path(os.path.dirname(__file__), 'data', 'modules', 'binary'))
        if os.name == 'nt':
            os.environ["PATH"] = modules_path + os.pathsep + os.environ["PATH"]

        from data.modules import mpv

        m3u = ""

        if os.name == 'nt':
            if not (os.path.isfile(str(Path(modules_path, 'ffmpeg.exe'))) and os.path.isfile(str(Path(modules_path, 'mpv-1.dll')))):
                show_exception("Не найдены бинарные модули!")

        if not os.path.isdir('local'):
            os.mkdir('local')

        channel_sets = {}
        def save_channel_sets():
            global channel_sets
            file2 = open(str(Path('local', 'channels.json')), 'w')
            file2.write(json.dumps(channel_sets))
            file2.close()

        if not os.path.isfile(str(Path('local', 'channels.json'))):
            save_channel_sets()
        else:
            file1 = open(str(Path('local', 'channels.json')), 'r')
            channel_sets = json.loads(file1.read())
            file1.close()

        favourite_sets = []
        def save_favourite_sets():
            global favourite_sets
            file2 = open(str(Path('local', 'favourites.json')), 'w')
            file2.write(json.dumps(favourite_sets))
            file2.close()

        if not os.path.isfile(str(Path('local', 'favourites.json'))):
            save_favourite_sets()
        else:
            file1 = open(str(Path('local', 'favourites.json')), 'r')
            favourite_sets = json.loads(file1.read())
            file1.close()

        if os.path.isfile(str(Path('local', 'settings.json'))):
            settings_file = open(str(Path('local', 'settings.json')), 'r')
            settings = json.loads(settings_file.read())
            settings_file.close()
        else:
            settings = {
                "m3u": "",
                "epg": "",
                "deinterlace": True,
                "udp_proxy": "",
                "save_folder": "",
                "provider": "",
                "nocache": False
            }
            m3u = ""

        if os.path.isfile(str(Path('local', 'tvguide.json'))):
            tvguide_c = open(str(Path('local', 'tvguide.json')), 'r')
            tvguide_c1 = json.loads(tvguide_c.read())["tvguide_url"]
            tvguide_c.close()
            if tvguide_c1 != settings["epg"]:
                os.remove(str(Path('local', 'tvguide.json')))

        tvguide_sets = {}
        def save_tvguide_sets():
            global tvguide_sets
            if tvguide_sets:
                file2 = open(str(Path('local', 'tvguide.json')), 'w')
                file2.write(json.dumps({"tvguide_sets": tvguide_sets, "tvguide_url": str(settings["epg"])}))
                file2.close()

        if not os.path.isfile(str(Path('local', 'tvguide.json'))):
            save_tvguide_sets()
        else:
            file1 = open(str(Path('local', 'tvguide.json')), 'r')
            tvguide_sets = json.loads(file1.read())["tvguide_sets"]
            file1.close()

        def is_program_actual(sets0):
            found_prog = False
            if sets0:
                for prog1 in sets0:
                    pr1 = sets0[prog1]
                    for p in pr1:
                        if time.time() > p['start'] and time.time() < p['stop']:
                            found_prog = True
            return found_prog

        use_local_tvguide = True

        if not is_program_actual(tvguide_sets):
            use_local_tvguide = False

        app = QtWidgets.QApplication(sys.argv)
        main_icon = QtGui.QIcon(str(Path(os.path.dirname(__file__), 'data', 'icons', 'tv.png')))
        channels = {}
        programmes = {}

        save_folder = settings['save_folder']

        if not os.path.isdir(str(Path(save_folder))):
            os.mkdir(str(Path(save_folder)))

        if not os.path.isdir(str(Path(save_folder, 'screenshots'))):
            os.mkdir(str(Path(save_folder, 'screenshots')))

        if not os.path.isdir(str(Path(save_folder, 'recordings'))):
            os.mkdir(str(Path(save_folder, 'recordings')))

        array = {}
        groups = []

        use_cache = settings['m3u'].startswith('http://') or settings['m3u'].startswith('https://')
        if settings['nocache']:
            use_cache = False
        if not use_cache:
            print("Кэширование плейлиста отключено")
        if use_cache and os.path.isfile(str(Path('local', 'playlist.json'))):
            pj = open(str(Path('local', 'playlist.json')), 'r')
            pj1 = json.loads(pj.read())['url']
            pj.close()
            if pj1 != settings['m3u']:
                os.remove(str(Path('local', 'playlist.json')))
        if (not use_cache) and os.path.isfile(str(Path('local', 'playlist.json'))):
            os.remove(str(Path('local', 'playlist.json')))
        if not os.path.isfile(str(Path('local', 'playlist.json'))):
            print("Идёт загрузка плейлиста...")
            if settings['m3u']:
                if os.path.isfile(settings['m3u']):
                    file = open(settings['m3u'], 'r')
                    m3u = file.read()
                    file.close()
                else:
                    try:
                        m3u = requests.get(settings['m3u'], headers={'User-Agent': user_agent}, timeout=3).text
                    except: # pylint: disable=bare-except
                        m3u = ""

            m3u_parser = M3uParser(settings['udp_proxy'])
            if m3u:
                try:
                    m3u_data = m3u_parser.readM3u(m3u)
                    for m3u_line in m3u_data:
                        array[m3u_line['title']] = m3u_line
                        if not m3u_line['tvg-group'] in groups:
                            groups.append(m3u_line['tvg-group'])
                except: # pylint: disable=bare-except
                    print("Playlist parsing error!")
                    show_exception("Ошибка загрузки плейлиста!")

            a = 'hidden_channels'
            if settings['provider'] in iptv_providers and a in iptv_providers[settings['provider']]:
                h1 = iptv_providers[settings['provider']][a]
                h1 = json.loads(base64.b64decode(bytes(h1, 'utf-8')).decode('utf-8'))
                for ch2 in h1:
                    ch2['tvg-name'] = ch2['tvg-name'] if 'tvg-name' in ch2 else ''
                    ch2['tvg-ID'] = ch2['tvg-ID'] if 'tvg-ID' in ch2 else ''
                    ch2['tvg-logo'] = ch2['tvg-logo'] if 'tvg-logo' in ch2 else ''
                    ch2['tvg-group'] = ch2['tvg-group'] if 'tvg-group' in ch2 else 'Все каналы'
                    array[ch2['title']] = ch2
            print("Загрузка плейлиста завершена!")
            if use_cache:
                print("Кэширую плейлист...")
                cm3u = json.dumps({
                    'url': settings['m3u'],
                    'array': array,
                    'groups': groups,
                    'm3u': m3u
                })
                cm3uf = open(str(Path('local', 'playlist.json')), 'w')
                cm3uf.write(cm3u)
                cm3uf.close()
                print("Кэш плейлиста сохранён!")
        else:
            print("Использую кэшированный плейлист")
            cm3uf = open(str(Path('local', 'playlist.json')), 'r')
            cm3u = json.loads(cm3uf.read())
            cm3uf.close()
            array = cm3u['array']
            groups = cm3u['groups']
            m3u = cm3u['m3u']

        if 'Все каналы' in groups:
            groups.remove('Все каналы')
        groups = ['Все каналы', 'Избранное'] + groups

        icons_file = open(str(Path('data', 'channel_icons.json')), 'r')
        icons = json.loads(icons_file.read())
        icons_file.close()

        def sigint_handler(*args): # pylint: disable=unused-argument
            """Handler for the SIGINT signal."""
            app.quit()

        signal.signal(signal.SIGINT, sigint_handler)

        timer = QtCore.QTimer()
        timer.start(500)
        timer.timeout.connect(lambda: None)

        TV_ICON = QtGui.QIcon(str(Path('data', 'icons', 'tv.png')))
        ICONS_CACHE = {}

        settings_win = QtWidgets.QMainWindow()
        settings_win.resize(400, 200)
        settings_win.setWindowTitle('Настройки')
        settings_win.setWindowIcon(main_icon)

        help_win = QtWidgets.QMainWindow()
        help_win.resize(400, 400)
        help_win.setWindowTitle('Помощь')
        help_win.setWindowIcon(main_icon)

        chan_win = QtWidgets.QMainWindow()
        chan_win.resize(400, 250)
        chan_win.setWindowTitle('Настройки канала')
        chan_win.setWindowIcon(main_icon)

        time_stop = 0

        qr = settings_win.frameGeometry()
        qr.moveCenter(QtWidgets.QDesktopWidget().availableGeometry().center())
        settings_win.move(qr.topLeft())
        help_win.move(qr.topLeft())
        chan_win.move(qr.topLeft())

        def m3u_select():
            fname = QtWidgets.QFileDialog.getOpenFileName(
                settings_win,
                'Выберите m3u плейлист'
            )[0]
            if fname:
                sm3u.setText(fname)

        def epg_select():
            fname = QtWidgets.QFileDialog.getOpenFileName(
                settings_win,
                'Выберите файл телепрограммы (XMLTV EPG)'
            )[0]
            if fname:
                sepg.setText(fname)

        def save_folder_select():
            folder_name = QtWidgets.QFileDialog.getExistingDirectory(
                settings_win,
                'Выберите папку для записи и скриншотов',
                options=QtWidgets.QFileDialog.ShowDirsOnly
            )
            if folder_name:
                sfld.setText(folder_name)

        # Channel settings window
        wid = QtWidgets.QWidget()

        title = QtWidgets.QLabel()
        myFont2 = QtGui.QFont()
        myFont2.setBold(True)
        title.setFont(myFont2)
        title.setAlignment(QtCore.Qt.AlignCenter)

        deinterlace_lbl = QtWidgets.QLabel("Деинтерлейс:")
        deinterlace_chk = QtWidgets.QCheckBox()

        def doPlay(play_url1):
            loading.show()
            player.loop = False
            player.play(play_url1)

        def chan_set_save():
            chan_3 = title.text().replace("Канал: ", "")
            channel_sets[chan_3] = {"deinterlace": deinterlace_chk.isChecked()}
            save_channel_sets()
            if playing_chan == chan_3:
                player.deinterlace = deinterlace_chk.isChecked()
                player.stop()
                doPlay(playing_url)
            chan_win.close()

        save_btn = QtWidgets.QPushButton("Сохранить настройки")
        save_btn.clicked.connect(chan_set_save)

        horizontalLayout = QtWidgets.QHBoxLayout()
        horizontalLayout.addWidget(title)

        horizontalLayout2 = QtWidgets.QHBoxLayout()
        horizontalLayout2.addWidget(QtWidgets.QLabel("\n"))
        horizontalLayout2.addWidget(deinterlace_lbl)
        horizontalLayout2.addWidget(deinterlace_chk)
        horizontalLayout2.addWidget(QtWidgets.QLabel("\n"))
        horizontalLayout2.setAlignment(QtCore.Qt.AlignCenter)

        horizontalLayout3 = QtWidgets.QHBoxLayout()
        horizontalLayout3.addWidget(save_btn)

        verticalLayout = QtWidgets.QVBoxLayout(wid)
        verticalLayout.addLayout(horizontalLayout)
        verticalLayout.addLayout(horizontalLayout2)
        verticalLayout.addLayout(horizontalLayout3)
        verticalLayout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        wid.setLayout(verticalLayout)
        chan_win.setCentralWidget(wid)

        # Settings window
        def save_settings():
            global epg_thread, manager
            udp_proxy_text = sudp.text()
            udp_proxy_starts = udp_proxy_text.startswith('http://') or udp_proxy_text.startswith('https://')
            if udp_proxy_text and not udp_proxy_starts:
                udp_proxy_text = 'http://' + udp_proxy_text
            if udp_proxy_text:
                if os.path.isfile(str(Path('local', 'playlist.json'))):
                    os.remove(str(Path('local', 'playlist.json')))
            settings_arr = {
                "m3u": sm3u.text(),
                "epg": sepg.text(),
                "deinterlace": sdei.isChecked(),
                "udp_proxy": udp_proxy_text,
                "save_folder": sfld.text(),
                "provider": sprov.currentText() if sprov.currentText() != '--не выбрано--' else '',
                "nocache": supdate.isChecked()
            }
            settings_file1 = open(str(Path('local', 'settings.json')), 'w')
            settings_file1.write(json.dumps(settings_arr))
            settings_file1.close()
            settings_win.hide()
            if epg_thread:
                epg_thread.kill()
            if manager:
                manager.shutdown()
            win.close()
            settings_win.close()
            help_win.close()
            time.sleep(0.1)
            if not os.name == 'nt':
                if args1.python:
                    os.execv(args1.python, ['python'] + sys.argv)
                else:
                    os.execv(sys.executable, ['python'] + sys.argv + ['--python', sys.executable])
            stop_record()
            if not os.name == 'nt':
                sys.exit(0)
            else:
                sys.exit(23)

        wid2 = QtWidgets.QWidget()

        m3u_label = QtWidgets.QLabel('M3U плейлист:')
        update_label = QtWidgets.QLabel('Обновлять\nпри запуске:')
        epg_label = QtWidgets.QLabel('Адрес\nтелепрограммы\n(XMLTV):')
        dei_label = QtWidgets.QLabel('Деинтерлейс:')
        udp_label = QtWidgets.QLabel('UDP прокси:')
        fld_label = QtWidgets.QLabel('Папка для записей\nи скриншотов:')

        def reset_channel_settings():
            os.remove(str(Path('local', 'channels.json')))
            os.remove(str(Path('local', 'favourites.json')))
            save_settings()

        sm3u = QtWidgets.QLineEdit()
        sm3u.setText(settings['m3u'])
        sepg = QtWidgets.QLineEdit()
        sepg.setText(settings['epg'])
        sudp = QtWidgets.QLineEdit()
        sudp.setText(settings['udp_proxy'])
        sdei = QtWidgets.QCheckBox()
        sdei.setChecked(settings['deinterlace'])
        supdate = QtWidgets.QCheckBox()
        supdate.setChecked(settings['nocache'])
        sfld = QtWidgets.QLineEdit()
        sfld.setText(settings['save_folder'])
        sselect = QtWidgets.QLabel("Или выберите\nвашего провайдера:")
        sselect.setStyleSheet('color: #00008B;')
        ssave = QtWidgets.QPushButton("Сохранить настройки")
        ssave.setStyleSheet('font-weight: bold; color: green;')
        ssave.clicked.connect(save_settings)
        sreset = QtWidgets.QPushButton("Сбросить настройки каналов")
        sreset.clicked.connect(reset_channel_settings)
        sprov = QtWidgets.QComboBox()
        def close_settings():
            settings_win.hide()
            if not win.isVisible():
                sys.exit(0)
        def prov_select(self): # pylint: disable=unused-argument
            prov1 = sprov.currentText()
            if prov1 != '--не выбрано--':
                sm3u.setText(iptv_providers[prov1]['m3u'])
                sepg.setText(iptv_providers[prov1]['epg'])
        sprov.currentIndexChanged.connect(prov_select)
        sprov.addItem('--не выбрано--')
        provs = {}
        ic3 = 0
        for prov in iptv_providers:
            ic3 += 1
            provs[prov] = ic3
            sprov.addItem(prov)
        if settings['provider']:
            prov_d = provs[settings['provider']]
            if prov_d and prov_d != -1:
                try:
                    sprov.setCurrentIndex(prov_d)
                except: # pylint: disable=bare-except
                    pass
        sclose = QtWidgets.QPushButton("Закрыть")
        sclose.clicked.connect(close_settings)

        def force_update_epg():
            global use_local_tvguide, first_boot
            if os.path.exists(str(Path('local', 'tvguide.json'))):
                os.remove(str(Path('local', 'tvguide.json')))
            use_local_tvguide = False
            if not epg_updating:
                first_boot = False

        def update_m3u():
            if os.path.isfile(str(Path('local', 'playlist.json'))):
                os.remove(str(Path('local', 'playlist.json')))
            save_settings()

        sm3ufile = QtWidgets.QPushButton(settings_win)
        sm3ufile.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'file.png'))))
        sm3ufile.clicked.connect(m3u_select)
        sm3uupd = QtWidgets.QPushButton(settings_win)
        sm3uupd.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'update.png'))))
        sm3uupd.clicked.connect(update_m3u)

        sepgfile = QtWidgets.QPushButton(settings_win)
        sepgfile.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'file.png'))))
        sepgfile.clicked.connect(epg_select)
        sepgupd = QtWidgets.QPushButton(settings_win)
        sepgupd.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'update.png'))))
        sepgupd.clicked.connect(force_update_epg)

        sfolder = QtWidgets.QPushButton(settings_win)
        sfolder.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'file.png'))))
        sfolder.clicked.connect(save_folder_select)

        sframe = QtWidgets.QFrame()
        sframe.setFrameShape(QtWidgets.QFrame.HLine)
        sframe.setFrameShadow(QtWidgets.QFrame.Raised)
        sframe1 = QtWidgets.QFrame()
        sframe1.setFrameShape(QtWidgets.QFrame.HLine)
        sframe1.setFrameShadow(QtWidgets.QFrame.Raised)
        sframe2 = QtWidgets.QFrame()
        sframe2.setFrameShape(QtWidgets.QFrame.HLine)
        sframe2.setFrameShadow(QtWidgets.QFrame.Raised)
        sframe3 = QtWidgets.QFrame()
        sframe3.setFrameShape(QtWidgets.QFrame.HLine)
        sframe3.setFrameShadow(QtWidgets.QFrame.Raised)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(m3u_label, 1, 0)
        grid.addWidget(sm3u, 1, 1)
        grid.addWidget(sm3ufile, 1, 2)
        grid.addWidget(sm3uupd, 1, 3)

        grid.addWidget(update_label, 2, 0)
        grid.addWidget(supdate, 2, 1)

        grid.addWidget(epg_label, 3, 0)
        grid.addWidget(sepg, 3, 1)
        grid.addWidget(sepgfile, 3, 2)
        grid.addWidget(sepgupd, 3, 3)

        grid.addWidget(sselect, 4, 1)
        grid.addWidget(sprov, 5, 1)

        grid.addWidget(sframe, 6, 0)
        grid.addWidget(sframe1, 6, 1)
        grid.addWidget(sframe2, 6, 2)
        grid.addWidget(sframe3, 6, 3)

        grid.addWidget(fld_label, 7, 0)
        grid.addWidget(sfld, 7, 1)
        grid.addWidget(sfolder, 7, 2)

        grid.addWidget(udp_label, 8, 0)
        grid.addWidget(sudp, 8, 1)

        grid.addWidget(dei_label, 9, 0)
        grid.addWidget(sdei, 9, 1)

        grid.addWidget(ssave, 10, 1)
        grid.addWidget(sreset, 11, 1)
        grid.addWidget(sclose, 12, 1)
        wid2.setLayout(grid)
        settings_win.setCentralWidget(wid2)

        textbox = QtWidgets.QPlainTextEdit(help_win)
        textbox.resize(390, 370)
        textbox.setReadOnly(True)
        textbox.setPlainText('''Astroncia IPTV    (c) kestral / astroncia

Кроссплатформенный плеер
для просмотра интернет-телевидения

Поддерживается телепрограмма (EPG)
только в формате XMLTV!

Горячие клавиши:

F - полноэкранный режим
M - выключить звук
Q - выйти из программы
Пробел - пауза
S - остановить проигрывание
H - скриншот
G - телепрограмма
R - начать/остановить запись
P - предыдущий канал
N - следующий канал
T - показать/скрыть список каналов
        ''')
        close_btn = QtWidgets.QPushButton(help_win)
        close_btn.move(140, 370)
        close_btn.setText("Закрыть")
        close_btn.clicked.connect(help_win.close)

        btn_update = QtWidgets.QPushButton()
        btn_update.hide()

        def show_settings():
            if not settings_win.isVisible():
                settings_win.show()
            else:
                settings_win.hide()

        def show_help():
            if not help_win.isVisible():
                help_win.show()
            else:
                help_win.hide()

        # This is necessary since PyQT stomps over the locale settings needed by libmpv.
        # This needs to happen after importing PyQT before creating the first mpv.MPV instance.
        locale.setlocale(locale.LC_NUMERIC, 'C')

        fullscreen = False

        class MainWindow(QtWidgets.QMainWindow):
            def __init__(self):
                super().__init__()
                # Shut up pylint (attribute-defined-outside-init)
                self.windowWidth = self.width()
                self.windowHeight = self.height()
                self.main_widget = None
                self.listWidget = None
            def update(self):
                global l1, tvguide_lbl, fullscreen

                self.windowWidth = self.width()
                self.windowHeight = self.height()
                tvguide_lbl.move(2, 35)
                if not fullscreen:
                    lbl2.move(0, 35)
                    l1.setFixedWidth(self.windowWidth - dockWidget.width() + 58)
                    l1.move(
                        int(((self.windowWidth - l1.width()) / 2) - (dockWidget.width() / 1.7)),
                        int(((self.windowHeight - l1.height()) - dockWidget2.height() - 10))
                    )
                    h = dockWidget2.height()
                    h2 = 20
                else:
                    lbl2.move(0, 5)
                    l1.setFixedWidth(self.windowWidth)
                    l1.move(
                        int(((self.windowWidth - l1.width()) / 2)),
                        int(((self.windowHeight - l1.height()) - 20))
                    )
                    h = 0
                    h2 = 10
                if tvguide_lbl.isVisible() and not fullscreen:
                    lbl2.move(210, 0)
                if l1.isVisible():
                    l1_h = l1.height()
                else:
                    l1_h = 15
                tvguide_lbl.setFixedHeight(((self.windowHeight - l1_h - h) - 40 - l1_h + h2))
            def resizeEvent(self, event):
                try:
                    self.update()
                except: # pylint: disable=bare-except
                    pass
                QtWidgets.QMainWindow.resizeEvent(self, event)

        win = MainWindow()
        win.setWindowTitle('Astroncia IPTV')
        win.setWindowIcon(main_icon)
        win.resize(WINDOW_SIZE[0], WINDOW_SIZE[1])

        qr = win.frameGeometry()
        qr.moveCenter(QtWidgets.QDesktopWidget().availableGeometry().center())
        win.move(qr.topLeft())

        win.main_widget = QtWidgets.QWidget(win)
        win.main_widget.setFocus()
        win.main_widget.setStyleSheet('''
            background-color: #C0C6CA;
        ''')
        win.setCentralWidget(win.main_widget)

        win.setAttribute(QtCore.Qt.WA_DontCreateNativeAncestors)
        win.setAttribute(QtCore.Qt.WA_NativeWindow)

        chan = QtWidgets.QLabel("Не выбран канал", win)
        chan.setAlignment(QtCore.Qt.AlignCenter)
        chan.resize(200, 30)

        lbl2 = QtWidgets.QLabel(win)
        lbl2.setAlignment(QtCore.Qt.AlignCenter)
        lbl2.setStyleSheet('color: #e0071a')
        lbl2.setWordWrap(True)
        lbl2.resize(200, 30)
        lbl2.move(0, 35)
        lbl2.hide()

        playing = False
        playing_chan = ''

        def show_progress(prog):
            if prog:
                prog_percentage = round(
                    (time.time() - prog['start']) / (prog['stop'] - prog['start']) * 100
                )
                prog_title = prog['title']
                prog_start = prog['start']
                prog_stop = prog['stop']
                prog_start_time = datetime.datetime.fromtimestamp(prog_start).strftime('%H:%M')
                prog_stop_time = datetime.datetime.fromtimestamp(prog_stop).strftime('%H:%M')
                progress.setValue(prog_percentage)
                progress.setFormat(str(prog_percentage) + '% ' + prog_title)
                progress.setAlignment(QtCore.Qt.AlignLeft)
                start_label.setText(prog_start_time)
                stop_label.setText(prog_stop_time)
                progress.show()
                start_label.show()
                stop_label.show()
            else:
                progress.hide()
                start_label.hide()
                stop_label.hide()

        playing_url = ''

        def itemClicked_event(item):
            global playing, playing_chan, item_selected, playing_url
            j = item.data(QtCore.Qt.UserRole)
            playing_chan = j
            item_selected = j
            play_url = array[j]['url']
            chan.setText('  ' + j)
            current_prog = None
            if settings['epg'] and j in programmes:
                for pr in programmes[j]:
                    if time.time() > pr['start'] and time.time() < pr['stop']:
                        current_prog = pr
                        break
            show_progress(current_prog)
            dockWidget2.setFixedHeight(DOCK_WIDGET2_HEIGHT)
            playing = True
            win.update()
            playing_url = play_url
            if j in channel_sets:
                d = channel_sets[j]
                player.deinterlace = d['deinterlace']
            else:
                player.deinterlace = settings['deinterlace']
            doPlay(play_url)

        item_selected = ''

        def itemSelected_event(item):
            global item_selected
            try:
                n_1 = item.data(QtCore.Qt.UserRole)
                item_selected = n_1
                update_tvguide(n_1)
            except: # pylint: disable=bare-except
                pass

        def mpv_play():
            if player.pause:
                label3.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'pause.png'))))
                label3.setToolTip("Пауза")
                player.pause = False
            else:
                label3.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'play.png'))))
                label3.setToolTip("Воспроизвести")
                player.pause = True

        def mpv_stop():
            global playing, playing_chan, playing_url
            playing_chan = ''
            playing_url = ''
            chan.setText('')
            playing = False
            player.stop()
            player.loop = True
            player.play(str(Path('data', 'icons', 'main.png')))
            chan.setText("Не выбран канал")
            progress.hide()
            start_label.hide()
            stop_label.hide()
            dockWidget2.setFixedHeight(DOCK_WIDGET2_HEIGHT - 30)
            win.update()

        def esc_handler():
            global fullscreen
            if fullscreen:
                mpv_fullscreen()

        def mpv_fullscreen():
            global fullscreen, l1, time_stop
            if not fullscreen:
                l1.show()
                l1.setText2("Для выхода из полноэкранного режима нажмите клавишу F")
                time_stop = time.time() + 3
                fullscreen = True
                dockWidget.hide()
                chan.hide()
                #progress.hide()
                #start_label.hide()
                #stop_label.hide()
                dockWidget2.hide()
                dockWidget2.setFixedHeight(DOCK_WIDGET2_HEIGHT - 30)
                win.update()
                win.showFullScreen()
            else:
                fullscreen = False
                if l1.text().endswith('Для выхода из полноэкранного режима нажмите клавишу F'):
                    l1.setText2('')
                    if not gl_is_static:
                        l1.hide()
                        win.update()
                if not player.pause and playing and start_label.text():
                    progress.show()
                    start_label.show()
                    stop_label.show()
                    dockWidget2.setFixedHeight(DOCK_WIDGET2_HEIGHT)
                dockWidget2.show()
                dockWidget.show()
                chan.show()
                win.update()
                win.showNormal()

        old_value = 100

        def mpv_mute():
            global old_value, time_stop, l1
            time_stop = time.time() + 3
            l1.show()
            if player.mute:
                if old_value > 50:
                    label6.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'volume.png'))))
                else:
                    label6.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'volume-low.png'))))
                player.mute = False
                label7.setValue(old_value)
                l1.setText2("Громкость: {}%".format(int(old_value)))
            else:
                label6.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'mute.png'))))
                player.mute = True
                old_value = label7.value()
                label7.setValue(0)
                l1.setText2("Громкость выкл.")

        def mpv_volume_set():
            global time_stop, l1
            time_stop = time.time() + 3
            vol = int(label7.value())
            try:
                l1.show()
                if vol == 0:
                    l1.setText2("Громкость выкл.")
                else:
                    l1.setText2("Громкость: {}%".format(vol))
            except NameError:
                pass
            player.volume = vol
            if vol == 0:
                player.mute = True
                label6.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'mute.png'))))
            else:
                player.mute = False
                if vol > 50:
                    label6.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'volume.png'))))
                else:
                    label6.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'volume-low.png'))))

        dockWidget = QtWidgets.QDockWidget(win)
        win.listWidget = QtWidgets.QListWidget()

        class ScrollLabel(QtWidgets.QScrollArea):
            def __init__(self, *args, **kwargs):
                QtWidgets.QScrollArea.__init__(self, *args, **kwargs)
                self.setWidgetResizable(True)
                content = QtWidgets.QWidget(self)
                self.setWidget(content)
                lay = QtWidgets.QVBoxLayout(content)
                self.label = QtWidgets.QLabel(content)
                self.label.setAlignment(QtCore.Qt.AlignCenter)
                self.label.setWordWrap(True)
                self.label.setStyleSheet('background-color: ' + BCOLOR)
                lay.addWidget(self.label)

            def setText(self, text):
                self.label.setText(text)

            def getText1(self):
                return self.label.text()

            def getLabelHeight(self):
                return self.label.height()

        tvguide_lbl = ScrollLabel(win)
        tvguide_lbl.move(0, 35)
        tvguide_lbl.setFixedWidth(TVGUIDE_WIDTH)
        tvguide_lbl.hide()

        class QCustomQWidget(QtWidgets.QWidget): # pylint: disable=too-many-instance-attributes
            def __init__(self, parent=None):
                super(QCustomQWidget, self).__init__(parent)
                self.textQVBoxLayout = QtWidgets.QVBoxLayout()      # QtWidgets
                self.textUpQLabel = QtWidgets.QLabel()         # QtWidgets
                myFont = QtGui.QFont()
                myFont.setBold(True)
                self.textUpQLabel.setFont(myFont)
                self.textDownQLabel = QtWidgets.QLabel()         # QtWidgets
                self.textQVBoxLayout.addWidget(self.textUpQLabel)
                self.textQVBoxLayout.addWidget(self.textDownQLabel)
                self.allQHBoxLayout = QtWidgets.QGridLayout()      # QtWidgets
                self.iconQLabel = QtWidgets.QLabel()         # QtWidgets
                self.progressLabel = QtWidgets.QLabel()
                self.progressBar = QtWidgets.QProgressBar()
                self.endLabel = QtWidgets.QLabel()
                self.allQHBoxLayout.addWidget(self.iconQLabel, 0, 0)
                self.allQHBoxLayout.addLayout(self.textQVBoxLayout, 0, 1)
                self.allQHBoxLayout.addWidget(self.progressLabel, 3, 0)
                self.allQHBoxLayout.addWidget(self.progressBar, 3, 1)
                self.allQHBoxLayout.addWidget(self.endLabel, 3, 2)
                self.allQHBoxLayout.setSpacing(10)
                self.setLayout(self.allQHBoxLayout)
                # setStyleSheet
                #self.textUpQLabel.setStyleSheet('''
                #    color: rgb(0, 0, 255);
                #''')
                #self.textDownQLabel.setStyleSheet('''
                #    color: rgb(255, 0, 0);
                #''')
                self.progressBar.setStyleSheet('''
                  background-color: #C0C6CA;
                  border: 0px;
                  padding: 0px;
                  height: 5px;
                ''')
                self.setStyleSheet('''
                  QProgressBar::chunk {
                    background: #7D94B0;
                    width:5px
                  }
                ''')

            def setTextUp(self, text):
                self.textUpQLabel.setText(text)

            def setTextDown(self, text):
                self.textDownQLabel.setText(text)

            def setTextProgress(self, text):
                self.progressLabel.setText(text)

            def setTextEnd(self, text):
                self.endLabel.setText(text)

            def setIcon(self, image):
                self.iconQLabel.setPixmap(image.pixmap(QtCore.QSize(32, 32)))

            def setProgress(self, progress_val):
                self.progressBar.setFormat('')
                self.progressBar.setValue(progress_val)

        current_group = 'Все каналы'

        def gen_chans(ch_array): # pylint: disable=too-many-locals, too-many-branches
            global ICONS_CACHE, playing_chan, current_group
            res = {}
            l = -1
            k = 0
            for i in sorted(ch_array):
                group1 = array[i]['tvg-group']
                if current_group != 'Все каналы':
                    if current_group == 'Избранное':
                        if not i in favourite_sets:
                            continue
                    else:
                        if group1 != current_group:
                            continue
                l += 1
                k += 1
                prog = ''
                if i in programmes:
                    current_prog = {
                        'start': 0,
                        'stop': 0,
                        'title': '',
                        'desc': ''
                    }
                    for pr in programmes[i]:
                        if time.time() > pr['start'] and time.time() < pr['stop']:
                            current_prog = pr
                            break
                    if current_prog['start'] != 0:
                        start_time = datetime.datetime.fromtimestamp(
                            current_prog['start']
                        ).strftime('%H:%M')
                        stop_time = datetime.datetime.fromtimestamp(
                            current_prog['stop']
                        ).strftime('%H:%M')
                        t_t = time.time()
                        percentage = round(
                            (t_t - current_prog['start']) / (
                                current_prog['stop'] - current_prog['start']
                            ) * 100
                        )
                        prog = str(percentage) + '% ' + current_prog['title']
                    else:
                        start_time = ''
                        stop_time = ''
                        t_t = time.time()
                        percentage = 0
                        prog = ''
                # Create QCustomQWidget
                myQCustomQWidget = QCustomQWidget()
                myQCustomQWidget.setTextUp(str(k) + ". " + i)
                MAX_SIZE = 31
                if len(prog) > MAX_SIZE:
                    prog = prog[0:MAX_SIZE] + "..."
                if i in programmes:
                    myQCustomQWidget.setTextDown(prog)
                    myQCustomQWidget.setTextProgress(start_time)
                    myQCustomQWidget.setTextEnd(stop_time)
                    myQCustomQWidget.setProgress(int(percentage))
                if i in icons:
                    if not icons[i] in ICONS_CACHE:
                        ICONS_CACHE[icons[i]] = QtGui.QIcon(str(Path('data', 'channel_icons', icons[i])))
                    myQCustomQWidget.setIcon(ICONS_CACHE[icons[i]])
                else:
                    myQCustomQWidget.setIcon(TV_ICON)
                # Create QListWidgetItem
                myQListWidgetItem = QtWidgets.QListWidgetItem(win.listWidget)
                myQListWidgetItem.setData(QtCore.Qt.UserRole, i)
                # Set size hint
                myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
                res[l] = [myQListWidgetItem, myQCustomQWidget]
            if playing_chan:
                current_chan = None
                try:
                    cur = programmes[playing_chan]
                    for pr in cur:
                        if time.time() > pr['start'] and time.time() < pr['stop']:
                            current_chan = pr
                            break
                except: # pylint: disable=bare-except
                    pass
                show_progress(current_chan)
            return res

        row0 = -1

        def redraw_chans():
            global row0
            update_tvguide()
            row0 = win.listWidget.currentRow()
            val0 = win.listWidget.verticalScrollBar().value()
            win.listWidget.clear()
            channels_1 = gen_chans(array)
            for channel_1 in channels_1:
                # Add QListWidgetItem into QListWidget
                win.listWidget.addItem(channels_1[channel_1][0])
                win.listWidget.setItemWidget(channels_1[channel_1][0], channels_1[channel_1][1])
            win.listWidget.setCurrentRow(row0)
            win.listWidget.verticalScrollBar().setValue(val0)

        first_change = False

        def group_change(self):
            global current_group, first_change
            current_group = groups[self]
            if not first_change:
                first_change = True
            else:
                btn_update.click()

        btn_update.clicked.connect(redraw_chans)

        channels = gen_chans(array)
        for channel in channels:
            # Add QListWidgetItem into QListWidget
            win.listWidget.addItem(channels[channel][0])
            win.listWidget.setItemWidget(channels[channel][0], channels[channel][1])

        sel_item = None

        def select_context_menu():
            itemClicked_event(sel_item)

        def tvguide_context_menu():
            update_tvguide()
            tvguide_lbl.show()

        def settings_context_menu():
            if chan_win.isVisible():
                chan_win.close()
            title.setText("Канал: " + item_selected)
            if item_selected in channel_sets:
                deinterlace_chk.setChecked(channel_sets[item_selected]['deinterlace'])
            else:
                deinterlace_chk.setChecked(False)
            chan_win.show()

        def tvguide_favourites_add():
            if item_selected in favourite_sets:
                favourite_sets.remove(item_selected)
            else:
                favourite_sets.append(item_selected)
            save_favourite_sets()
            btn_update.click()

        def tvguide_start_record():
            url2 = array[item_selected]['url']
            if is_recording:
                start_record("", "")
            start_record(item_selected, url2)

        def show_context_menu(pos):
            global sel_item
            self = win.listWidget
            sel_item = self.selectedItems()[0]
            itemSelected_event(sel_item)
            menu = QtWidgets.QMenu()
            menu.addAction("Выбрать", select_context_menu)
            menu.addSeparator()
            menu.addAction("Телепрограмма", tvguide_context_menu)
            menu.addAction("Избранное", tvguide_favourites_add)
            menu.addAction("Начать запись", tvguide_start_record)
            menu.addAction("Настройки канала", settings_context_menu)
            menu.exec_(self.mapToGlobal(pos))

        win.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        win.listWidget.customContextMenuRequested.connect(show_context_menu)
        win.listWidget.currentItemChanged.connect(itemSelected_event)
        win.listWidget.itemClicked.connect(itemSelected_event)
        win.listWidget.itemDoubleClicked.connect(itemClicked_event)
        loading = QtWidgets.QLabel('Загрузка...')
        loading.setAlignment(QtCore.Qt.AlignCenter)
        loading.setStyleSheet('color: #778a30')
        loading.hide()
        myFont2 = QtGui.QFont()
        myFont2.setPointSize(12)
        myFont2.setBold(True)
        loading.setFont(myFont2)
        combobox = QtWidgets.QComboBox()
        combobox.currentIndexChanged.connect(group_change)
        for group in groups:
            combobox.addItem(group)
        layout = QtWidgets.QGridLayout()
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        widget.layout().addWidget(combobox)
        widget.layout().addWidget(win.listWidget)
        widget.layout().addWidget(loading)
        dockWidget.setFixedWidth(DOCK_WIDGET_WIDTH)
        dockWidget.setWidget(widget)
        dockWidget.setFloating(False)
        dockWidget.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        win.addDockWidget(QtCore.Qt.RightDockWidgetArea, dockWidget)

        FORBIDDEN_CHARS = ('"', '*', ':', '<', '>', '?', '\\', '/', '|', '[', ']')

        def do_screenshot():
            global l1, time_stop, playing_chan
            if playing_chan:
                l1.show()
                l1.setText2("Делаю скриншот...")
                ch = playing_chan.replace(" ", "_")
                for char in FORBIDDEN_CHARS:
                    ch = ch.replace(char, "")
                cur_time = datetime.datetime.now().strftime('%d%m%Y_%H%M%S')
                file_name = 'screenshot_-_' + cur_time + '_-_' + ch + '.png'
                file_path = str(Path(save_folder, 'screenshots', file_name))
                try:
                    pillow_img = player.screenshot_raw()
                    pillow_img.save(file_path)
                    l1.show()
                    l1.setText2("Скриншот сохранён!")
                except: # pylint: disable=bare-except
                    l1.show()
                    l1.setText2("Ошибка создания скриншота!")
                time_stop = time.time() + 1
            else:
                l1.show()
                l1.setText2("Не выбран канал!")
                time_stop = time.time() + 1

        def update_tvguide(chan_1=''):
            global item_selected
            if not chan_1:
                if item_selected:
                    chan_2 = item_selected
                else:
                    chan_2 = sorted(array.items())[0][0]
            else:
                chan_2 = chan_1
            txt = 'Нет телепрограммы для канала'
            if chan_2 in programmes:
                txt = '\n'
                prog = programmes[chan_2]
                for pr in prog:
                    if pr['stop'] > time.time() - 1:
                        start_2 = datetime.datetime.fromtimestamp(
                            pr['start']
                        ).strftime('%d.%m.%y %H:%M') + ' - '
                        stop_2 = datetime.datetime.fromtimestamp(
                            pr['stop']
                        ).strftime('%d.%m.%y %H:%M') + '\n'
                        title_2 = pr['title'] if 'title' in pr else ''
                        desc_2 = ('\n' + pr['desc'] + '\n') if 'desc' in pr else ''
                        txt += start_2 + stop_2 + title_2 + desc_2 + '\n'
            tvguide_lbl.setText(txt)

        def show_tvguide():
            if tvguide_lbl.isVisible():
                tvguide_lbl.setText('')
                tvguide_lbl.hide()
            else:
                update_tvguide()
                tvguide_lbl.show()

        is_recording = False
        recording_time = 0
        record_file = None

        def start_record(ch1, url3):
            global is_recording, record_file, time_stop, recording_time
            if not is_recording:
                is_recording = True
                lbl2.show()
                lbl2.setText("Подготовка записи")
                ch = ch1.replace(" ", "_")
                for char in FORBIDDEN_CHARS:
                    ch = ch.replace(char, "")
                cur_time = datetime.datetime.now().strftime('%d%m%Y_%H%M%S')
                out_file = str(Path(
                    save_folder,
                    'recordings',
                    'recording_-_' + cur_time + '_-_' + ch + '.mkv'
                ))
                record_file = out_file
                record(url3, out_file)
            else:
                is_recording = False
                recording_time = 0
                stop_record()
                lbl2.setText("")
                lbl2.hide()

        def do_record():
            global time_stop
            if playing_chan:
                start_record(playing_chan, playing_url)
            else:
                time_stop = time.time() + 1
                l1.show()
                l1.setText2("Не выбран канал для записи")

        def my_log(loglevel, component, message):
            print('[{}] {}: {}'.format(loglevel, component, message))

        player = mpv.MPV(
            wid=str(int(win.main_widget.winId())),
            ytdl=False,
            vo='' if os.name == 'nt' else 'gpu,direct3d,x11'
            #log_handler=my_log,
            #loglevel='info' # debug
        )
        player.user_agent = user_agent
        player.volume = 100
        player.loop = True
        player.play(str(Path('data', 'icons', 'main.png')))

        @player.event_callback('file_loaded')
        def ready_handler(event): # pylint: disable=unused-argument
            loading.hide()

        @player.event_callback('end_file')
        def ready_handler_2(event): # pylint: disable=unused-argument
            try:
                loading.hide()
            except RuntimeError:
                pass

        @player.on_key_press('MBTN_LEFT_DBL')
        def my_leftdbl_binding():
            mpv_fullscreen()

        @player.on_key_press('WHEEL_UP')
        def my_up_binding():
            global l1, time_stop
            volume = int(player.volume + 1)
            if volume > 100:
                volume = 100
            label7.setValue(volume)
            mpv_volume_set()

        @player.on_key_press('WHEEL_DOWN')
        def my_down_binding():
            global l1, time_stop
            volume = int(player.volume - 1)
            if volume < 0:
                volume = 0
            time_stop = time.time() + 3
            l1.show()
            l1.setText2("Громкость: {}%".format(volume))
            label7.setValue(volume)
            mpv_volume_set()

        dockWidget2 = QtWidgets.QDockWidget(win)

        def open_recording_folder():
            absolute_path = Path(save_folder).absolute()
            if os.name == 'nt':
                webbrowser.open('file:///' + str(absolute_path))
            else:
                subprocess.Popen(['xdg-open', str(absolute_path)])

        def go_channel(i1):
            row = win.listWidget.currentRow()
            if row == -1:
                row = row0
            next_row = row + i1
            if next_row < 0:
                next_row = 0
            if next_row > win.listWidget.count() - 1:
                next_row = win.listWidget.count() - 1
            win.listWidget.setCurrentRow(next_row)
            itemClicked_event(win.listWidget.currentItem())

        def prev_channel():
            go_channel(-1)

        def next_channel():
            go_channel(1)

        label3 = QtWidgets.QPushButton()
        label3.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'pause.png'))))
        label3.setToolTip("Пауза")
        label3.clicked.connect(mpv_play)
        label4 = QtWidgets.QPushButton()
        label4.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'stop.png'))))
        label4.setToolTip("Стоп")
        label4.clicked.connect(mpv_stop)
        label5 = QtWidgets.QPushButton()
        label5.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'fullscreen.png'))))
        label5.setToolTip("Полноэкранный режим")
        label5.clicked.connect(mpv_fullscreen)
        label5_0 = QtWidgets.QPushButton()
        label5_0.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'folder.png'))))
        label5_0.setToolTip("Открыть папку записей")
        label5_0.clicked.connect(open_recording_folder)
        label5_1 = QtWidgets.QPushButton()
        label5_1.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'record.png'))))
        label5_1.setToolTip("Запись")
        label5_1.clicked.connect(do_record)
        label6 = QtWidgets.QPushButton()
        label6.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'volume.png'))))
        label6.setToolTip("Громкость")
        label6.clicked.connect(mpv_mute)
        label7 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        label7.setMinimum(0)
        label7.setMaximum(100)
        label7.valueChanged.connect(mpv_volume_set)
        label7.setValue(100)
        label7_1 = QtWidgets.QPushButton()
        label7_1.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'screenshot.png'))))
        label7_1.setToolTip("Скриншот")
        label7_1.clicked.connect(do_screenshot)
        label8 = QtWidgets.QPushButton()
        label8.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'settings.png'))))
        label8.setToolTip("Настройки")
        label8.clicked.connect(show_settings)
        label8_1 = QtWidgets.QPushButton()
        label8_1.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'tvguide.png'))))
        label8_1.setToolTip("Телепрограмма")
        label8_1.clicked.connect(show_tvguide)
        label8_2 = QtWidgets.QPushButton()
        label8_2.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'prev.png'))))
        label8_2.setToolTip("Предыдущий канал")
        label8_2.clicked.connect(prev_channel)
        label8_3 = QtWidgets.QPushButton()
        label8_3.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'next.png'))))
        label8_3.setToolTip("Следующий канал")
        label8_3.clicked.connect(next_channel)
        label9 = QtWidgets.QPushButton()
        label9.setIcon(QtGui.QIcon(str(Path('data', 'icons', 'help.png'))))
        label9.setToolTip("Помощь")
        label9.clicked.connect(show_help)
        label10 = QtWidgets.QLabel('  (c) kestral / astroncia')
        label11 = QtWidgets.QLabel('  ' + datetime.datetime.today().strftime('%H:%M:%S'))
        myFont3 = QtGui.QFont()
        myFont3.setPointSize(11)
        myFont3.setBold(True)
        label11.setFont(myFont3)

        progress = QtWidgets.QProgressBar()
        progress.setValue(0)
        start_label = QtWidgets.QLabel()
        stop_label = QtWidgets.QLabel()

        vlayout3 = QtWidgets.QVBoxLayout()
        hlayout1 = QtWidgets.QHBoxLayout()
        hlayout2 = QtWidgets.QHBoxLayout()
        widget2 = QtWidgets.QWidget()
        widget2.setLayout(vlayout3)

        hlayout1.addWidget(start_label)
        hlayout1.addWidget(progress)
        hlayout1.addWidget(stop_label)

        hlayout2.addWidget(label3)
        hlayout2.addWidget(label4)
        hlayout2.addWidget(label5)
        hlayout2.addWidget(label5_1)
        hlayout2.addWidget(label5_0)
        hlayout2.addWidget(label6)
        hlayout2.addWidget(label7)
        hlayout2.addWidget(label7_1)
        hlayout2.addWidget(label8)
        hlayout2.addWidget(label8_1)
        hlayout2.addWidget(label8_2)
        hlayout2.addWidget(label8_3)
        hlayout2.addWidget(label9)
        hlayout2.addWidget(label11)
        hlayout2.addWidget(label10)

        #hlayout1.addStretch(1)
        vlayout3.addLayout(hlayout1)

        hlayout2.addStretch(1)
        vlayout3.addLayout(hlayout2)

        dockWidget2.setWidget(widget2)
        dockWidget2.setFloating(False)
        dockWidget2.setFixedHeight(DOCK_WIDGET2_HEIGHT)
        dockWidget2.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dockWidget2)

        progress.hide()
        start_label.hide()
        stop_label.hide()
        dockWidget2.setFixedHeight(DOCK_WIDGET2_HEIGHT - 30)

        l1 = QtWidgets.QLabel(win)
        myFont1 = QtGui.QFont()
        myFont1.setPointSize(12)
        myFont1.setBold(True)
        l1.setStyleSheet('background-color: ' + BCOLOR)
        l1.setFont(myFont1)
        l1.setWordWrap(True)
        l1.move(50, 50)
        l1.setAlignment(QtCore.Qt.AlignCenter)

        static_text = ""
        gl_is_static = False

        def set_text_l1(text):
            global static_text, gl_is_static
            if gl_is_static:
                br = "    "
                if not text or not static_text:
                    br = ""
                text = static_text + br + text
            win.update()
            l1.setText(text)

        def set_text_static(is_static):
            global gl_is_static, static_text
            static_text = ""
            gl_is_static = is_static

        l1.setText2 = set_text_l1
        l1.setStatic2 = set_text_static
        l1.hide()

        stopped = False

        def myExitHandler():
            global stopped
            stopped = True
            if epg_thread:
                epg_thread.kill()
            if manager:
                manager.shutdown()
            stop_record()

        first_boot = False

        epg_thread = None
        manager = None
        epg_updating = False
        return_dict = None
        waiting_for_epg = False
        epg_failed = False

        def thread_tvguide():
            global stopped, time_stop, first_boot, programmes, btn_update, \
            epg_thread, static_text, manager, tvguide_sets, epg_updating, ic, \
            return_dict, waiting_for_epg, epg_failed
            if not first_boot:
                first_boot = True
                if settings['epg'] and not epg_failed:
                    if not use_local_tvguide:
                        epg_updating = True
                        l1.setStatic2(True)
                        l1.show()
                        static_text = "Обновление телепрограммы..."
                        l1.setText2("")
                        time_stop = time.time() + 3
                        try:
                            manager = multiprocessing.Manager()
                            return_dict = manager.dict()
                            p = multiprocessing.Process(target=worker, args=(0, settings, return_dict))
                            epg_thread = p
                            p.start()
                            waiting_for_epg = True
                        except Exception as e1:
                            epg_failed = True
                            print("[TV guide, part 1] Caught exception: " + str(e1))
                            l1.setStatic2(False)
                            l1.show()
                            l1.setText2("Ошибка обновления телепрограммы!")
                            time_stop = time.time() + 3
                            epg_updating = False
                    else:
                        programmes = tvguide_sets
                        btn_update.click() # start update in main thread

            ic += 0.1 # pylint: disable=undefined-variable
            if ic > 14.9: # redraw every 15 seconds
                ic = 0
                btn_update.click()

        def thread_record():
            global time_stop, gl_is_static, static_text, recording_time, ic1
            ic1 += 0.1  # pylint: disable=undefined-variable
            if ic1 > 0.9:
                ic1 = 0
                # executing every second
                if is_recording:
                    if not recording_time:
                        recording_time = time.time()
                    record_time = format_seconds_to_hhmmss(time.time() - recording_time)
                    if os.path.isfile(record_file):
                        record_size = convert_size(os.path.getsize(record_file))
                        lbl2.setText("REC " + record_time + " - " + record_size)
                    else:
                        recording_time = time.time()
                        lbl2.setText("Ожидание записи")
            win.update()
            if(time.time() > time_stop) and time_stop != 0:
                time_stop = 0
                if not gl_is_static:
                    l1.hide()
                    win.update()
                else:
                    l1.setText2("")

        def thread_check_tvguide_obsolete():
            global first_boot, ic2
            ic2 += 0.1  # pylint: disable=undefined-variable
            if ic2 > 9.9:
                ic2 = 0
                if not epg_updating:
                    if not is_program_actual(programmes):
                        force_update_epg()

        thread_4_lock = False

        def thread_tvguide_2():
            global stopped, time_stop, first_boot, programmes, btn_update, \
            epg_thread, static_text, manager, tvguide_sets, epg_updating, ic, \
            return_dict, waiting_for_epg, thread_4_lock, epg_failed
            if not thread_4_lock:
                thread_4_lock = True
                if waiting_for_epg and return_dict and len(return_dict) == 5:
                    try:
                        if not return_dict[3]:
                            raise return_dict[4]
                        l1.setStatic2(False)
                        l1.show()
                        l1.setText2("Обновление телепрограммы завершено!")
                        time_stop = time.time() + 3
                        values = return_dict.values()
                        programmes = values[1]
                        tvguide_sets = programmes
                        save_tvguide_sets()
                        btn_update.click() # start update in main thread
                    except Exception as e2:
                        epg_failed = True
                        print("[TV guide, part 2] Caught exception: " + str(e2))
                        l1.setStatic2(False)
                        l1.show()
                        l1.setText2("Ошибка обновления телепрограммы!")
                        time_stop = time.time() + 3
                    epg_updating = False
                    waiting_for_epg = False
                thread_4_lock = False

        def thread_update_time():
            if label11:
                label11.setText('  ' + datetime.datetime.today().strftime('%H:%M:%S'))

        def key_t():
            if dockWidget.isVisible():
                dockWidget.hide()
            else:
                dockWidget.show()

        # Key bindings
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_T), win).activated.connect(key_t)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape), win).activated.connect(esc_handler) # escape key
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_F), win).activated.connect(mpv_fullscreen) # f - fullscreen
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_M), win).activated.connect(mpv_mute) # m - mute

        def key_quit():
            settings_win.close()
            win.close()

        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Q), win).activated.connect(key_quit) # q - quit
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), win).activated.connect(mpv_play) # space - pause
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_S), win).activated.connect(mpv_stop) # s - stop
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_H), win).activated.connect(do_screenshot) # h - screenshot
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_G), win).activated.connect(show_tvguide) # g - tv guide
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_R), win).activated.connect(do_record) # r - record
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_P), win).activated.connect(prev_channel) # p - prev channel
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_N), win).activated.connect(next_channel) # n - next channel

        app.aboutToQuit.connect(myExitHandler)

        if settings['m3u'] and m3u:
            win.show()
            win.raise_()
            win.setFocus(QtCore.Qt.PopupFocusReason)
            win.activateWindow()

            ic = 0
            x = QtCore.QTimer()
            x.timeout.connect(thread_tvguide)
            x.start(100)

            ic1 = 0
            x2 = QtCore.QTimer()
            x2.timeout.connect(thread_record)
            x2.start(100)

            ic2 = 0
            x3 = QtCore.QTimer()
            x3.timeout.connect(thread_check_tvguide_obsolete)
            x3.start(100)

            x4 = QtCore.QTimer()
            x4.timeout.connect(thread_tvguide_2)
            x4.start(1000)

            x5 = QtCore.QTimer()
            x5.timeout.connect(thread_update_time)
            x5.start(1000)
        else:
            settings_win.show()
            settings_win.raise_()
            settings_win.setFocus(QtCore.Qt.PopupFocusReason)
            settings_win.activateWindow()

        sys.exit(app.exec_())
    except Exception as e3:
        show_exception(e3)