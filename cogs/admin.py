import discord
from discord.ext import commands
from utils import config

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='设置初始角色')
    @commands.has_permissions(administrator=True)
    async def set_initial_role(self, ctx):
        """为服务器内所有无角色的成员批量分配“观众”角色"""
        spectator_role = discord.utils.get(ctx.guild.roles, name=config.SPECTATOR_ROLE_NAME)
        creator_role = discord.utils.get(ctx.guild.roles, name=config.CREATOR_ROLE_NAME)

        if not spectator_role:
            await ctx.send(f"错误：未找到“{config.SPECTATOR_ROLE_NAME}”角色，请先创建。")
            return

        updated_count = 0
        total_members_checked = 0
        await ctx.send("正在获取服务器成员列表并分配初始角色，这可能需要一些时间...")

        try:
            async for member in ctx.guild.fetch_members(limit=None):
                total_members_checked += 1
                if member.bot:
                    continue

                has_spectator = spectator_role in member.roles
                has_creator = creator_role and creator_role in member.roles

                if not has_spectator and not has_creator:
                    try:
                        await member.add_roles(spectator_role)
                        updated_count += 1
                        print(f"已为现有成员 {member.name} 分配角色 '{config.SPECTATOR_ROLE_NAME}'")
                    except discord.Forbidden:
                        print(f"[权限错误] 无法为 {member.name} 分配角色。请检查机器人的角色是否拥有'管理角色'权限，并且其位置高于'{config.SPECTATOR_ROLE_NAME}'角色。")
                    except Exception as e:
                        print(f"为 {member.name} 分配角色时发生未知错误: {e}")
        except discord.Forbidden:
            await ctx.send("错误：机器人缺少'查看服务器成员'的权限，无法获取成员列表。请检查机器人权限。")
            return
            
        await ctx.send(f"操作完成！共检查了 {total_members_checked} 名成员，为 {updated_count} 名成员分配了“{config.SPECTATOR_ROLE_NAME}”角色。")

    @set_initial_role.error
    async def set_initial_role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("抱歉，只有管理员才能执行此命令。")

async def setup(bot):
    await bot.add_cog(Admin(bot))
