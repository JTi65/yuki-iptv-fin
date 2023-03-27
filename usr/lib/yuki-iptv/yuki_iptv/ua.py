# pylint: disable=missing-function-docstring, missing-module-docstring
# SPDX-License-Identifier: GPL-3.0-only
import os
import json
from pathlib import Path
user_agent = '' # pylint: disable=invalid-name
uas = [
    '',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36', # pylint: disable=line-too-long
    'Dalvik/2.1.0 (Linux; U; Android 10; AGS3-L09 Build/HUAWEIAGS3-L09)',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148', # pylint: disable=line-too-long
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36', # pylint: disable=line-too-long
    'OnlineTvAppDroid',
    'smartlabs',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)',
    'Mozilla/5.0',
    'VLC/3.0.16 LibVLC/3.0.16',
    'libmpv'
]
ua_names = [
    '',
    'Windows Browser',
    'Android',
    'iPhone',
    'Linux Browser',
    'OnlineTvAppDroid',
    'Smartlabs',
    'Mac OS X',
    'Mozilla/5.0',
    'VLC',
    'libmpv'
]

LOCAL_DIR = str(Path(os.environ['HOME'], '.config', 'yuki-iptv'))
if not os.path.isdir(str(Path(os.environ['HOME'], '.config'))):
    os.mkdir(str(Path(os.environ['HOME'], '.config')))
if not os.path.isdir(LOCAL_DIR):
    os.mkdir(LOCAL_DIR)

def get_default_user_agent():
    if os.path.isfile(str(Path(LOCAL_DIR, 'settings.json'))):
        settings_file1 = open(str(Path(LOCAL_DIR, 'settings.json')), 'r', encoding="utf8")
        settings1 = json.loads(settings_file1.read())
        settings_file1.close()
    else:
        settings1 = {
            "useragent": 2
        }
    if 'useragent' not in settings1:
        settings1['useragent'] = 2
    def_user_agent = uas[settings1['useragent']]
    return def_user_agent

def get_user_agent_for_channel(channel):
    ua1 = get_default_user_agent()
    channel_sets1 = {}
    if os.path.isfile(str(Path(LOCAL_DIR, 'channels.json'))):
        file2 = open(str(Path(LOCAL_DIR, 'channels.json')), 'r', encoding="utf8")
        channel_sets1 = json.loads(file2.read())
        file2.close()
    if channel in channel_sets1:
        ch_data = channel_sets1[channel]
        if 'useragent' in ch_data:
            try:
                ua1 = uas[ch_data['useragent']]
            except: # pylint: disable=bare-except
                ua1 = get_default_user_agent()
    return ua1
