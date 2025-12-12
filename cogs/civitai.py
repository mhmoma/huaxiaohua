import discord
from discord.ext import commands
import httpx
import os
import random
import json
import re

# 敏感词检测列表
NSFW_KEYWORDS = ["nude", "naked", "nsfw", "裸体", "裸", "色情", "r18"]
QUALITY_TAGS = [
    "masterpiece", "best quality", "ultra-detailed", "8k", "4k",
    "photorealistic", "highly detailed", "realistic", "highres",
    "absurdres", "best_quality", "ultra_detailed",
]

def format_meta_field(meta, field_name, max_length=1000):
    """安全地从 meta 字典中提取并格式化字段"""
    field_value = meta.get(field_name, "N/A")
    if isinstance(field_value, list):
        field_value = ", ".join(map(str, field_value))
    if len(str(field_value)) > max_length:
        return str(field_value)[:max_length] + "..."
    return str(field_value)

class Civitai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("CIVITAI_API_KEY")
        self.base_url = "https://civitai.com/api/v1"

    async def fetch_civitai_data(self, url, params=None):
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                print(f"[ERROR] Civitai API 请求失败: {e}")
                return None

    @commands.command(name='搜索')
    async def search_image(self, ctx, *, query: str):
        """根据文本描述从 Civitai 搜索图片"""
        msg = await ctx.send("正在分析您的搜索请求...")

        query_parts = [part.strip().lower() for part in query.replace(',', ' ').split()]
        subject_parts = [part for part in query_parts if part not in QUALITY_TAGS and part]
        
        if not subject_parts:
            await msg.edit(content="**搜索失败!**\n您的搜索词只包含通用质量标签。请添加**具体的主题**，例如: `搜索 a girl, masterpiece`")
            return
        
        final_query = " ".join(subject_parts)
        
        is_nsfw_channel = isinstance(ctx.channel, discord.TextChannel) and ctx.channel.is_nsfw()
        contains_nsfw_keyword = any(keyword in query.lower() for keyword in NSFW_KEYWORDS)

        if contains_nsfw_keyword and not is_nsfw_channel:
            await msg.edit(content="抱歉，请在年龄限制频道（NSFW）中使用包含敏感词的搜索。")
            return

        await msg.edit(content=f"正在使用优化后的关键词“**{final_query}**”进行搜索，请稍候...")

        params = {"query": final_query, "limit": 30, "sort": "Most Reactions", "nsfw": "None"}
        if is_nsfw_channel:
            params["nsfw"] = "X"

        data = await self.fetch_civitai_data(f"{self.base_url}/images", params=params)

        if not data or not data.get("items"):
            await msg.edit(content="抱歉，没有找到相关的图片。请尝试更换关键词。")
            return

        valid_images = [img for img in data.get("items", []) if img.get("url") and img.get("meta") and 'prompt' in img.get("meta")]

        if not valid_images:
            await msg.edit(content="抱歉，找到了相关的图片，但它们都缺少详细的生成信息。请尝试其他关键词。")
            return

        scored_images = []
        for img in valid_images:
            prompt_text = img['meta'].get('prompt', '').lower()
            score = sum(1 for keyword in subject_parts if keyword in prompt_text)
            scored_images.append({'score': score, 'image': img})

        scored_images.sort(key=lambda x: x['score'], reverse=True)

        highest_score = scored_images[0]['score']
        match_threshold = 0.5

        if len(subject_parts) > 1 and (highest_score / len(subject_parts)) < match_threshold:
            await msg.edit(content=f"抱歉，找不到与您的关键词“{final_query}”高度匹配的图片。")
            return
        
        top_scorers = [item['image'] for item in scored_images if item['score'] == highest_score]
        image_data = random.choice(top_scorers)
        
        image_page_url = f"https://civitai.com/images/{image_data['id']}"
        embed = discord.Embed(title="Civitai 图片搜索结果", description=f"**原始链接:** [点击查看]({image_page_url})", color=discord.Color.blue())
        
        embed.set_image(url=image_data["url"])

        meta = image_data.get("meta")
        
        embed.add_field(name="✅ 正面提示词 (Prompt)", value=f"```{format_meta_field(meta, 'prompt')}```", inline=False)
        embed.add_field(name="❌ 负面提示词 (Negative Prompt)", value=f"```{format_meta_field(meta, 'negativePrompt')}```", inline=False)
        
        col1 = [f"**模型:** {format_meta_field(meta, 'Model')}", f"**采样器:** {format_meta_field(meta, 'sampler')}", f"**步数:** {format_meta_field(meta, 'steps')}"]
        col2 = [f"**CFG Scale:** {format_meta_field(meta, 'cfgScale')}", f"**种子 (Seed):** {format_meta_field(meta, 'seed')}"]
        if 'hashes' in meta and 'model' in meta['hashes']:
             col2.append(f"**模型哈希:** {meta['hashes']['model']}")

        embed.add_field(name="⚙️ 参数 1", value="\n".join(col1), inline=True)
        embed.add_field(name="⚙️ 参数 2", value="\n".join(col2), inline=True)

        if meta.get("lora"):
            embed.add_field(name="🧩 LoRA", value="\n".join([f"- {lora}" for lora in meta["lora"]]), inline=False)
        
        embed.set_footer(text=f"由 {image_data.get('username', '未知作者')} 创建 | ⚡️ Civitai")

        await msg.edit(content="", embed=embed)

async def setup(bot):
    await bot.add_cog(Civitai(bot))
