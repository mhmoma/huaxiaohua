import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

from utils import config

# 加载 .env 文件中的环境变量
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 创建一个 Intents 对象并启用所需权限
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True
intents.voice_states = True

# --- Prefix Logic ---
# 允许在不带前缀的情况下，通过完整的消息内容调用特定命令
async def get_prefix(bot, message):
    # 对于我们已知的中文命令，如果消息内容完全匹配或以特定词开头，则使用空字符串作为前缀
    if message.content.startswith('搜索 '):
        return ''
    if message.content in ['签到', '我的画泥', '购买周星', '设置初始角色', 'ping']:
        return ""
    # 对于其他命令或提及机器人，则使用 '!' 或 @机器人 作为前缀
    return commands.when_mentioned_or("!")(bot, message)

# 定义 Bot (已移除代理逻辑，适配云端部署)
bot = commands.Bot(command_prefix=get_prefix, intents=intents)

bot.first_on_ready = True

@bot.command(name='ping')
async def ping(ctx):
    """检查机器人是否在线"""
    await ctx.send('pong')


# --- 主函数 ---
async def main():
    # 加载所有 cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'成功加载模块: {filename[:-3]}')
            except Exception as e:
                print(f'加载模块 {filename[:-3]} 失败: {e}')

    # 启动机器人
    await bot.start(TOKEN)

@bot.event
async def on_ready():
    # 防止重连时重复打印启动信息
    if not bot.first_on_ready:
        print("机器人已重新连接。")
        return

    bot.first_on_ready = False
    
    print(f'我们已经以 {bot.user} 身份登录')
    if bot.guilds:
        main_guild = bot.guilds[0]
        print(f"机器人已在服务器 '{main_guild.name}' (ID: {main_guild.id}) 中准备就绪。")
        
        print("\n--- 机器人功能列表 ---")
        print("【自动功能】")
        print(f"  - 新成员自动分配“{config.SPECTATOR_ROLE_NAME}”角色。")
        print(f"  - “{config.SPECTATOR_ROLE_NAME}”发布图片后自动升级为“{config.CREATOR_ROLE_NAME}”。")
        print(f"  - 在任意频道对图片点赞“{config.TRIGGER_EMOJI}”即可自动收录到“{config.GALLERY_CHANNEL_NAME}”论坛。")
        print("\n【用户命令】")
        print("  - `签到`：每日签到获取画泥。")
        print("  - `我的画泥`：查询当前画泥余额。")
        print(f"  - `购买周星`：花费画泥购买“{config.STAR_ROLE_NAME}”角色（有效期{config.STAR_ROLE_DURATION_DAYS}天）。")
        print("\n【管理员命令】")
        print("  - `设置初始角色`：为服务器内所有无角色的成员批量分配初始角色。")
        print("-----------------------\n")
    else:
        print("错误：机器人未加入任何服务器。")

if __name__ == '__main__':
    asyncio.run(main())
