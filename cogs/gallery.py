import discord
from discord.ext import commands
from utils import config, data_manager

class Gallery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) != config.TRIGGER_EMOJI:
            return

        try:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            print(f"无法找到频道 {payload.channel_id} 或消息 {payload.message_id}。")
            return
        
        if not message.attachments or message.author.bot:
            return

        for reaction in message.reactions:
            if reaction.emoji == config.PROCESSED_EMOJI and reaction.me:
                print(f"消息 {message.id} 已被标记为处理过，跳过。")
                return

        gallery_channel = discord.utils.get(message.guild.channels, name=config.GALLERY_CHANNEL_NAME)
        if not gallery_channel or not isinstance(gallery_channel, discord.ForumChannel):
            print(f"错误：未找到名为 '{config.GALLERY_CHANNEL_NAME}' 的论坛频道。")
            return

        author = message.author
        author_id = str(author.id)
        
        author_threads = data_manager.load_data(config.AUTHOR_THREADS_FILE)
        thread_id = author_threads.get(author_id)
        thread = None

        if thread_id:
            try:
                thread = await self.bot.fetch_channel(thread_id)
            except discord.NotFound:
                print(f"找不到帖子 ID: {thread_id}，将为 {author.name} 创建新帖。")
                thread_id = None

        if not thread_id:
            try:
                thread, _ = await gallery_channel.create_thread(
                    name=f"{author.display_name}的个人作品集",
                    content=f"欢迎来到 {author.mention} 的个人作品集！这里会收录他/她被点赞的优秀作品。",
                )
                author_threads[author_id] = thread.id
                data_manager.save_data(author_threads, config.AUTHOR_THREADS_FILE)
                print(f"为 {author.name} 创建了新的作品集帖子。")
            except Exception as e:
                print(f"创建帖子时出错: {e}")
                return
        
        if thread:
            try:
                image_url = message.attachments[0].url
                embed = discord.Embed(
                    description=f"**原消息链接：** [点击跳转]({message.jump_url})",
                    color=discord.Color.blue()
                )
                embed.set_image(url=image_url)
                embed.set_author(name=f"作者：{author.display_name}", icon_url=author.display_avatar.url)
                embed.set_footer(text=f"发布于：{message.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                await thread.send(embed=embed)
                print(f"已将 {author.name} 的作品添加到其作品集中。")
                
                await message.add_reaction(config.PROCESSED_EMOJI)

            except Exception as e:
                print(f"发送作品到帖子时出错: {e}")

async def setup(bot):
    await bot.add_cog(Gallery(bot))
