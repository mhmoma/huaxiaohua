# -*- coding: utf-8 -*-

"""
封装对 JSON 文件的读写操作
"""

import os
import json
import datetime

def load_data(filename):
    """
    从 JSON 文件加载数据。
    如果文件不存在或为空，返回一个空字典。
    如果文件损坏，会尝试备份并返回一个空字典。
    """
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"警告：读取或解析 {filename} 时出错: {e}。")
        if os.path.exists(filename):
            try:
                bak_filename = f"{filename}.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
                os.rename(filename, bak_filename)
                print(f"已将损坏的文件备份为: {bak_filename}")
            except Exception as bak_e:
                print(f"备份文件时出错: {bak_e}")
        return {}

def save_data(data, filename):
    """
    将数据以 JSON 格式保存到文件。
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
