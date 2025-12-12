import discord
from discord.ext import commands, tasks
from utils import config, data_manager
import datetime

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='签到')
    async def sign_in(self, ctx):
        """每日签到获取画泥"""
        user_id = str(ctx.author.id)
        currency_data = data_manager.load_data(config.CURRENCY_DATA_FILE)
        if user_id not in currency_data:
            currency_data[user_id] = {"balance": 0, "last_signed": ""}

        today = str(datetime.date.today())
        if currency_data[user_id].get("last_signed") != today:
            currency_data[user_id]["balance"] += config.SIGN_IN_REWARD
            currency_data[user_id]["last_signed"] = today
            data_manager.save_data(currency_data, config.CURRENCY_DATA_FILE)
            await ctx.send(f"签到成功！你获得了 {config.SIGN_IN_REWARD} 个画泥，现在共有 {currency_data[user_id]['balance']} 个画泥。")
        else:
            await ctx.send("你今天已经签过到了，明天再来吧！")

    @commands.command(name='我的画泥')
    async def my_currency(self, ctx):
        """查询当前画泥余额"""
        user_id = str(ctx.author.id)
        currency_data = data_manager.load_data(config.CURRENCY_DATA_FILE)
        balance = currency_data.get(user_id, {}).get("balance", 0)
        await ctx.send(f"你当前拥有 {balance} 个画泥。")

    @commands.command(name='购买周星')
    async def buy_star_role(self, ctx):
        """花费画泥购买“周星”角色"""
        user_id = str(ctx.author.id)
        currency_data = data_manager.load_data(config.CURRENCY_DATA_FILE)
        if user_id not in currency_data:
            currency_data[user_id] = {"balance": 0}

        user_balance = currency_data[user_id].get("balance", 0)
        cost = config.STAR_ROLE_COST

        if user_balance >= cost:
            currency_data[user_id]["balance"] -= cost
            star_role = discord.utils.get(ctx.guild.roles, name=config.STAR_ROLE_NAME)
            if not star_role:
                await ctx.send(f"错误：未找到名为 '{config.STAR_ROLE_NAME}' 的角色。")
                return
            try:
                await ctx.author.add_roles(star_role)
                expiry_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=config.STAR_ROLE_DURATION_DAYS)
                if "temp_roles" not in currency_data[user_id]:
                    currency_data[user_id]["temp_roles"] = {}
                currency_data[user_id]["temp_roles"]["star_of_the_week"] = expiry_time.isoformat()
                data_manager.save_data(currency_data, config.CURRENCY_DATA_FILE)
                await ctx.send(f"恭喜！你已成功购买 '{config.STAR_ROLE_NAME}' 角色，有效期{config.STAR_ROLE_DURATION_DAYS}天。消费 {cost} 画泥，剩余 {currency_data[user_id]['balance']} 画泥。")
            except discord.Forbidden:
                await ctx.send("错误：机器人权限不足，无法为你添加角色。")
        else:
            await ctx.send(f"你的画泥不足！购买需要 {cost} 画泥，你只有 {user_balance} 画泥。")

async def setup(bot):
    await bot.add_cog(Currency(bot))
