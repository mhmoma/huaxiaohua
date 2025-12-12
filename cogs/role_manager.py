import discord
from discord.ext import commands, tasks
from utils import config, data_manager
import datetime

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_temp_roles.start()

    def cog_unload(self):
        self.check_temp_roles.cancel()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """为新成员自动分配“观众”角色"""
        if member.bot:
            return
        try:
            role = discord.utils.get(member.guild.roles, name=config.SPECTATOR_ROLE_NAME)
            if role:
                await member.add_roles(role)
                print(f'已为 {member.name} 分配角色 "{config.SPECTATOR_ROLE_NAME}"')
        except Exception as e:
            print(f'为新成员分配角色时出错: {e}')

    @commands.Cog.listener()
    async def on_message(self, message):
        """观众发图后自动升级为创作者"""
        if message.author.bot or not message.guild or not message.attachments:
            return

        spectator_role = discord.utils.get(message.guild.roles, name=config.SPECTATOR_ROLE_NAME)
        creator_role = discord.utils.get(message.guild.roles, name=config.CREATOR_ROLE_NAME)
        
        if spectator_role and creator_role and spectator_role in message.author.roles and creator_role not in message.author.roles:
            try:
                await message.author.remove_roles(spectator_role, reason="升级为创作者")
                await message.author.add_roles(creator_role, reason="发布了第一个作品")
                await message.channel.send(f'恭喜 {message.author.mention} 发布了作品，成功晋级为 {config.CREATOR_ROLE_NAME}！')
                print(f"用户 {message.author.name} 已从 '{config.SPECTATOR_ROLE_NAME}' 升级为 '{config.CREATOR_ROLE_NAME}'。")
            except discord.Forbidden:
                print(f"[权限错误] 无法为 {message.author.name} 升级角色。请检查机器人角色位置和'管理角色'权限。")
            except Exception as e:
                print(f'为 {message.author.name} 升级角色时发生未知错误: {e}')

    @tasks.loop(hours=1)
    async def check_temp_roles(self):
        """每小时检查并移除到期的临时角色"""
        await self.bot.wait_until_ready()
        
        main_guild = self.bot.guilds[0] if self.bot.guilds else None
        if not main_guild:
            print("[TASK] 机器人未加入任何服务器，无法检查临时角色。")
            return

        print("[TASK] 开始检查临时角色到期...")
        currency_data = data_manager.load_data(config.CURRENCY_DATA_FILE)
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        users_to_update = list(currency_data.keys())
        for user_id in users_to_update:
            user_data = currency_data.get(user_id, {})
            if "temp_roles" in user_data:
                roles_to_remove_keys = []
                for role_key, expiry_iso in list(user_data["temp_roles"].items()):
                    try:
                        expiry_time = datetime.datetime.fromisoformat(expiry_iso)
                        if expiry_time.tzinfo is None:
                            expiry_time = expiry_time.replace(tzinfo=datetime.timezone.utc)

                        if current_time >= expiry_time:
                            roles_to_remove_keys.append(role_key)
                            member = main_guild.get_member(int(user_id))
                            if member and role_key == "star_of_the_week":
                                role_to_remove = discord.utils.get(main_guild.roles, name=config.STAR_ROLE_NAME)
                                if role_to_remove and role_to_remove in member.roles:
                                    await member.remove_roles(role_to_remove)
                                    print(f"用户 {member.name} 的 '{config.STAR_ROLE_NAME}' 角色已到期并移除。")
                    except (ValueError, discord.Forbidden) as e:
                        print(f"处理用户 {user_id} 的到期角色 {role_key} 时出错: {e}")

                if roles_to_remove_keys:
                    for role_key in roles_to_remove_keys:
                        del currency_data[user_id]["temp_roles"][role_key]
                    if not currency_data[user_id]["temp_roles"]:
                        del currency_data[user_id]["temp_roles"]
        
        data_manager.save_data(currency_data, config.CURRENCY_DATA_FILE)
        print("[TASK] 临时角色检查完成。")

async def setup(bot):
    await bot.add_cog(RoleManager(bot))
