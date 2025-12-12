import discord
from discord.ext import commands
import httpx
import os
import random
import json
import re
import io

# 敏感词检测列表
NSFW_KEYWORDS = ["nude", "naked", "nsfw", "裸体", "裸", "色情", "r18"]
QUALITY_TAGS = [
    "masterpiece", "best quality", "ultra-detailed", "8k", "4k",
    "photorealistic", "highly detailed", "realistic", "highres",
    "absurdres", "best_quality", "ultra_detailed",
]

# Civitai API 支持的排序方式
SUPPORTED_SORTS = ["Newest", "Most Reactions", "Most Downloads", "Most Comments"]

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

    async def download_image(self, url):
        """从 URL 下载图片并返回其字节数据"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                return response.content
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"[ERROR] 从 {url} 下载图片失败: {e}")
            return None

    @commands.command(name='搜索')
    async def search_image(self, ctx, *, query: str):
        """根据文本描述从 Civitai 搜索图片"""
        msg = await ctx.send("正在分析您的搜索请求...")

        # --- 关键词标准化处理 ---
        raw_parts = re.split(r'[,\s]+', query.replace('，', ','))
        query_parts = [part.strip().lower() for part in raw_parts if part.strip()]
        
        subject_parts = [part for part in query_parts if part not in QUALITY_TAGS and part]
        
        if not subject_parts:
            await msg.edit(content="**搜索失败!**\n您的搜索词只包含通用质量标签。请添加**具体的主题**，例如: `搜索 a girl, masterpiece`")
            return
        
        final_query = ",".join(subject_parts)
        
        is_nsfw_channel = isinstance(ctx.channel, discord.TextChannel) and ctx.channel.is_nsfw()
        contains_nsfw_keyword = any(keyword in query.lower() for keyword in NSFW_KEYWORDS)

        if contains_nsfw_keyword and not is_nsfw_channel:
            await msg.edit(content="抱歉，请在年龄限制频道（NSFW）中使用包含敏感词的搜索。")
            return

        # --- 随机选择排序方式 ---
        selected_sort = random.choice(SUPPORTED_SORTS)
        await msg.edit(content=f"正在使用优化后的关键词“**{final_query}**”按**{selected_sort}**进行搜索，请稍候...")

        params = {
            "query": final_query,
            "limit": 30,
            "sort": selected_sort,
            "nsfw": "Mature" if is_nsfw_channel else "None"
        }
        
        data = await self.fetch_civitai_data(f"{self.base_url}/images", params=params)

        if not data or not data.get("items"):
            await msg.edit(content="抱歉，没有找到相关的图片。请尝试更换关键词。")
            return

        valid_images = [img for img in data.get("items", []) if img.get("url") and img.get("meta") and 'prompt' in img.get("meta")]

        if not valid_images:
            await msg.edit(content="抱歉，找到的图片都缺少详细的生成信息。")
            return
        
        # --- 最终修复：弹性匹配机制 ---
        perfect_matches = []
        scored_matches = []
        for img in valid_images:
            prompt_text = img['meta'].get('prompt', '').lower()
            current_score = sum(1 for keyword in subject_parts if keyword in prompt_text)
            
            if current_score == len(subject_parts): # 100% 匹配
                perfect_matches.append(img)
            if current_score > 0: # 至少匹配一个关键词
                scored_matches.append({'score': current_score, 'image': img})

        image_data = None
        match_feedback = ""

        if perfect_matches:
            image_data = random.choice(perfect_matches)
            match_feedback = "（完美匹配您的所有关键词）"
        elif scored_matches:
            # 如果没有完美匹配，则从匹配度最高的图片中选择
            scored_matches.sort(key=lambda x: x['score'], reverse=True)
            highest_score = scored_matches[0]['score']
            top_scorers = [item['image'] for item in scored_matches if item['score'] == highest_score]
            image_data = random.choice(top_scorers)
            match_feedback = f"（匹配到 {highest_score}/{len(subject_parts)} 个关键词）"
        
        if not image_data:
            await msg.edit(content=f"抱歉，找不到与您的关键词“{final_query}”相关的图片。请尝试减少或更换关键词。")
            return
        
        await msg.edit(content="正在下载图片以便显示...")
        image_bytes = await self.download_image(image_data["url"])

        image_page_url = f"https://civitai.com/images/{image_data['id']}"
        embed = discord.Embed(title=f"Civitai 图片搜索结果 {match_feedback}", description=f"**原始链接:** [点击查看]({image_page_url})", color=discord.Color.blue())
        
        meta = image_data.get("meta")
        embed.add_field(name="✅ 正面提示词 (Prompt)", value=f"```{format_meta_field(meta, 'prompt')}```", inline=False)
        embed.add_field(name="❌ 负面提示词 (Negative Prompt)", value=f"```{format_meta_field(meta, 'negativePrompt')}```", inline=False)
        col1 = [f"**模型:** {format_meta_field(meta, 'Model')}", f"**采样器:** {format_meta_field(meta, 'sampler')}", f"**步数:** {format_meta_field(meta, 'steps')}"]
        col2 = [f"**CFG Scale:** {format_meta_field(meta, 'cfgScale')}", f"**种子 (Seed):** {format_meta_field(meta, 'seed')}"]
        if 'hashes' in meta and 'model' in meta['hashes']:
             col2.append(f"**模型哈希:** {format_meta_field(meta['hashes'], 'model')}")
        embed.add_field(name="⚙️ 参数 1", value="\n".join(col1), inline=True)
        embed.add_field(name="⚙️ 参数 2", value="\n".join(col2), inline=True)
        if meta.get("lora"):
            embed.add_field(name="🧩 LoRA", value="\n".join([f"- {lora}" for lora in meta["lora"]]), inline=False)
        embed.set_footer(text=f"由 {image_data.get('username', '未知作者')} 创建 | ⚡️ Civitai")

        if not image_bytes:
            await msg.edit(content="抱歉，无法下载图片进行预览，但这里是它的信息：", embed=embed)
        else:
            filename = os.path.basename(image_data["url"].split('?')[0])
            if not filename or '.' not in filename:
                filename = "image.jpeg"
            
            picture = discord.File(io.BytesIO(image_bytes), filename=filename)
            await ctx.send(embed=embed, file=picture)
            await msg.delete()

async def setup(bot):
    await bot.add_cog(Civitai(bot))
