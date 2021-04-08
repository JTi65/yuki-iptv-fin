# Astroncia IPTV
### Кроссплатформенный плеер для просмотра интернет-телевидения

## Информация

**32-битная Windows не поддерживается!**  

Программа предоставляется **as is**, никаких гарантий.  

## Зависимости

- Python 3 (3.7 или более новая версия)
- Qt 5
- libmpv
- PyQt5 (python3-pyqt5)
- Pillow (python3-pil)
- Tkinter (python3-tk)
- python3-requests
- ffmpeg

## Установка

**Устанавливаем зависимости:**

на Debian/Ubuntu:  
```sudo apt install ffmpeg git libmpv1 python3 python3-requests python3-pyqt5 python3-pil python3-tk```

на Windows:  
Устанавливаем Git с [официального сайта](https://git-scm.com/download/win)  
Устанавливаем Python 3 с [официального сайта](https://www.python.org/downloads/windows/) - Windows Installer (64-bit) (Recommended)  
(**поставьте галочку Add Python 3 to PATH при установке**)  
Устанавливаем Python модули:  
```pip install requests PyQt5 Pillow```

**Клонируем репозиторий:**

```git clone --depth=1 https://gitlab.com/astroncia/iptv.git astroncia_iptv```  
```cd astroncia_iptv```

**Устанавливаем бинарные зависимости (только для Windows):**

Скачайте файлы  
[ffmpeg.exe](https://gitlab.com/astroncia/iptv-binary-deps/-/raw/master/ffmpeg.exe)  
[mpv-1.dll](https://gitlab.com/astroncia/iptv-binary-deps/-/raw/master/mpv-1.dll)  
и поместите их в папку **astroncia_iptv\data\modules\binary**

**Запускаем:**

на Windows: запускайте файл ```start_windows.vbs```  
( можете создать ярлык: **ПКМ** -> **Отправить** -> **Рабочий стол (создать ярлык)** )

на Linux: ```./start_linux.sh```

## Просмотр записей

Для записей телепередач используется контейнер MKV  
Для просмотра записей рекомендуется использовать [VLC media player](https://www.videolan.org/).  