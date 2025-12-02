import discord
import os
from dotenv import load_dotenv
import json
import datetime
from discord.ext import tasks

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

# 根据环境变量决定是否使用代理
proxy_url = os.getenv('HTTP_PROXY')
if proxy_url:
    print(f"检测到代理，将使用: {proxy_url}")
    client = discord.Client(intents=intents, proxy=proxy_url)
else:
    print("未检测到代理，将直接连接")
    client = discord.Client(intents=intents)

# --- 配置 ---
GALLERY_CHANNEL_NAME = "作品精选"
TRIGGER_EMOJI = "👍"
PROCESSED_EMOJI = "✅"
AUTHOR_THREADS_FILE = "author_threads.json"
CURRENCY_DATA_FILE = "currency_data.json"
STAR_ROLE_NAME = "✨ 本周之星"
main_guild = None # 用于存储服务器对象

# --- 辅助函数：数据读写 ---
def load_data(filename):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# --- 事件监听 ---
@client.event
async def on_ready():
    global main_guild
    print(f'我们已经以 {client.user} 身份登录')
    if client.guilds:
        main_guild = client.guilds[0]
        print(f"机器人已在服务器 '{main_guild.name}' (ID: {main_guild.id}) 中准备就绪。")
        check_temp_roles.start()
    else:
        print("错误：机器人未加入任何服务器。")

@client.event
async def on_member_join(member):
    try:
        role = discord.utils.get(member.guild.roles, name="👀 观众")
        if role:
            await member.add_roles(role)
            print(f'已为 {member.name} 分配角色 "👀 观众"')
    except Exception as e:
        print(f'分配角色时出错: {e}')

@client.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.text_channels, name="聊天")
    if channel is not None:
        await channel.send(f'成员 {member.name}#{member.discriminator} 已经离开了服务器。')

@client.event
async def on_message(message):
    if message.author == client.user or not message.guild:
        return

    # --- 中文命令处理 ---
    user_id = str(message.author.id)
    currency_data = load_data(CURRENCY_DATA_FILE)
    if user_id not in currency_data:
        currency_data[user_id] = {"balance": 0, "last_signed": ""}

    # 签到
    if message.content == '签到':
        today = str(datetime.date.today())
        if currency_data[user_id].get("last_signed") != today:
            currency_data[user_id]["balance"] += 10
            currency_data[user_id]["last_signed"] = today
            save_data(currency_data, CURRENCY_DATA_FILE)
            await message.channel.send(f"签到成功！你获得了 10 个画泥，现在共有 {currency_data[user_id]['balance']} 个画泥。")
        else:
            await message.channel.send("你今天已经签过到了，明天再来吧！")
        return

    # 我的画泥
    if message.content == '我的画泥':
        balance = currency_data[user_id].get("balance", 0)
        await message.channel.send(f"你当前拥有 {balance} 个画泥。")
        return

    # 购买周星
    if message.content == '购买周星':
        user_balance = currency_data[user_id].get("balance", 0)
        cost = 10
        if user_balance >= cost:
            currency_data[user_id]["balance"] -= cost
            star_role = discord.utils.get(message.guild.roles, name=STAR_ROLE_NAME)
            if not star_role:
                await message.channel.send(f"错误：未找到名为 '{STAR_ROLE_NAME}' 的角色。")
                return
            try:
                await message.author.add_roles(star_role)
                expiry_time = datetime.datetime.utcnow() + datetime.timedelta(days=7)
                if "temp_roles" not in currency_data[user_id]:
                    currency_data[user_id]["temp_roles"] = {}
                currency_data[user_id]["temp_roles"]["star_of_the_week"] = expiry_time.isoformat()
                save_data(currency_data, CURRENCY_DATA_FILE)
                await message.channel.send(f"恭喜！你已成功购买 '{STAR_ROLE_NAME}' 角色，有效期7天。消费 10 画泥，剩余 {currency_data[user_id]['balance']} 画泥。")
            except discord.Forbidden:
                await message.channel.send("错误：机器人权限不足，无法为你添加角色。")
        else:
            await message.channel.send(f"你的画泥不足！购买需要 {cost} 画泥，你只有 {user_balance} 画泥。")
        return
    
    # 设置初始角色
    if message.content == '设置初始角色':
        if not message.author.guild_permissions.administrator:
            await message.channel.send("抱歉，只有管理员才能执行此命令。")
            return

        spectator_role = discord.utils.get(message.guild.roles, name="👀 观众")
        creator_role = discord.utils.get(message.guild.roles, name="🎨 创作者")

        if not spectator_role:
            await message.channel.send("错误：未找到“👀 观众”角色，请先创建。")
            return

        updated_count = 0
        await message.channel.send("正在为现有成员分配初始角色，这可能需要一些时间...")

        for member in message.guild.members:
            if member.bot:
                continue
            
            if spectator_role not in member.roles and (not creator_role or creator_role not in member.roles):
                try:
                    await member.add_roles(spectator_role)
                    updated_count += 1
                    print(f"已为现有成员 {member.name} 分配角色 '👀 观众'")
                except Exception as e:
                    print(f"为 {member.name} 分配角色时出错: {e}")
        
        await message.channel.send(f"操作完成！共为 {updated_count} 名现有成员分配了“👀 观众”角色。")
        return
    
    # ping
    if message.content == 'ping':
        await message.channel.send('pong')
        return

    # --- 角色自动升级逻辑 ---
    if message.attachments:
        spectator_role = discord.utils.get(message.guild.roles, name="👀 观众")
        creator_role = discord.utils.get(message.guild.roles, name="🎨 创作者")
        if spectator_role and creator_role and spectator_role in message.author.roles:
            try:
                await message.author.remove_roles(spectator_role)
                await message.author.add_roles(creator_role)
                await message.channel.send(f'恭喜 {message.author.mention} 发布了作品，成功晋级为 🎨 创作者！')
            except Exception as e:
                print(f'为 {message.author.name} 升级角色时出错: {e}')

# ... (on_raw_reaction_add 和 on_voice_state_update 保持不变)

# --- 后台任务：检查临时角色到期 ---
@tasks.loop(hours=1)
async def check_temp_roles():
    if not main_guild:
        return
    print("[TASK] 开始检查临时角色到期...")
    currency_data = load_data(CURRENCY_DATA_FILE)
    current_time = datetime.datetime.utcnow()
    users_to_update = list(currency_data.keys())
    for user_id in users_to_update:
        user_data = currency_data.get(user_id, {})
        if "temp_roles" in user_data:
            roles_to_remove = []
            for role_key, expiry_iso in list(user_data["temp_roles"].items()):
                expiry_time = datetime.datetime.fromisoformat(expiry_iso)
                if current_time >= expiry_time:
                    roles_to_remove.append(role_key)
                    member = main_guild.get_member(int(user_id))
                    if member and role_key == "star_of_the_week":
                        role_to_remove = discord.utils.get(main_guild.roles, name=STAR_ROLE_NAME)
                        if role_to_remove and role_to_remove in member.roles:
                            try:
                                await member.remove_roles(role_to_remove)
                                print(f"用户 {member.name} 的 '{STAR_ROLE_NAME}' 角色已到期并移除。")
                            except discord.Forbidden:
                                print(f"权限不足，无法移除 {member.name} 的到期角色。")
            for role_key in roles_to_remove:
                del currency_data[user_id]["temp_roles"][role_key]
            if not currency_data[user_id]["temp_roles"]:
                del currency_data[user_id]["temp_roles"]
    save_data(currency_data, CURRENCY_DATA_FILE)
    print("[TASK] 临时角色检查完成。")

# 运行机器人
client.run(TOKEN)
