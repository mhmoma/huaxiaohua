# -*- coding: utf-8 -*-

"""
集中管理所有配置常量
"""

# --- 核心配置 ---
GALLERY_CHANNEL_NAME = "作品精选"
TRIGGER_EMOJI = "👍"
PROCESSED_EMOJI = "✅"

# --- 文件路径 ---
AUTHOR_THREADS_FILE = "author_threads.json"
CURRENCY_DATA_FILE = "currency_data.json"

# --- 角色名称 ---
SPECTATOR_ROLE_NAME = "👀 观众"
CREATOR_ROLE_NAME = "🎨 创作者"
STAR_ROLE_NAME = "✨周星" # 注意：原bot.py中此项为空格，这里修改为更具可读性的名称

# --- 经济系统 ---
SIGN_IN_REWARD = 10
STAR_ROLE_COST = 10
STAR_ROLE_DURATION_DAYS = 7
