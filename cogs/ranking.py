import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
import time
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

STORAGE_FILE = "ranking_data.json"


def load_data():
    if not os.path.exists(STORAGE_FILE):
        return {"users": {}, "rank_roles": {}}
    with open(STORAGE_FILE) as f:
        return json.load(f)


def save_data(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def xp_to_level(xp):
    return int((xp / 100) ** 0.5)


def level_to_xp(level):
    return (level ** 2) * 100


class Ranking(commands.Cog):

    rank = app_commands.Group(name="rank", description="Ranking commands")

    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()
        self.cooldowns = {}
        self.autosave.start()

    def cog_unload(self):
        save_data(self.data)

    @tasks.loop(seconds=30)
    async def autosave(self):
        save_data(self.data)

    def ensure_guild(self, guild_id):
        if guild_id not in self.data["users"]:
            self.data["users"][guild_id] = {}
        if guild_id not in self.data["rank_roles"]:
            self.data["rank_roles"][guild_id] = {}

    # -----------------------
    # RANK POSITION
    # -----------------------

    def get_rank_position(self, guild_id, user_id):

        users = self.data["users"][guild_id]

        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1]["xp"],
            reverse=True
        )

        for i, (uid, _) in enumerate(sorted_users, start=1):
            if uid == user_id:
                return i

        return "?"

    # -----------------------
    # ROLE UPDATE
    # -----------------------

    async def update_user_roles(self, member):

        guild_id = str(member.guild.id)
        user_id = str(member.id)

        self.ensure_guild(guild_id)

        if user_id not in self.data["users"][guild_id]:
            return

        xp = self.data["users"][guild_id][user_id]["xp"]

        rank_roles = self.data["rank_roles"][guild_id]

        highest_role = None
        highest_xp = -1

        for xp_req, role_id in rank_roles.items():
            xp_req = int(xp_req)

            if xp >= xp_req and xp_req > highest_xp:
                highest_xp = xp_req
                highest_role = role_id

        for role_id in rank_roles.values():
            role = member.guild.get_role(role_id)

            if role and role in member.roles:
                await member.remove_roles(role)

        if highest_role:
            role = member.guild.get_role(highest_role)

            if role:
                await member.add_roles(role)

    # -----------------------
    # MESSAGE XP SYSTEM
    # -----------------------

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        self.ensure_guild(guild_id)

        if user_id not in self.data["users"][guild_id]:
            return

        user = self.data["users"][guild_id][user_id]

        if not user["active"]:
            return

        cooldown_key = f"{guild_id}:{user_id}"

        now = time.time()

        if now - self.cooldowns.get(cooldown_key, 0) < 30:
            return

        xp_gain = random.randint(5, 10)

        user["xp"] += xp_gain

        self.cooldowns[cooldown_key] = now

        await self.update_user_roles(message.author)

        await self.bot.process_commands(message)

    # -----------------------
    # JOIN
    # -----------------------

    @rank.command(name="join")
    async def join(self, interaction: discord.Interaction):

        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        self.ensure_guild(guild_id)

        if user_id not in self.data["users"][guild_id]:
            self.data["users"][guild_id][user_id] = {
                "xp": 0,
                "active": True
            }
        else:
            self.data["users"][guild_id][user_id]["active"] = True

        await interaction.response.send_message(
            "✅ You joined the ranking system!",
            ephemeral=True
        )

    # -----------------------
    # LEAVE
    # -----------------------

    @rank.command(name="leave")
    async def leave(self, interaction: discord.Interaction):

        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        if user_id in self.data["users"][guild_id]:
            self.data["users"][guild_id][user_id]["active"] = False

        await interaction.response.send_message(
            "❌ You left the ranking system",
            ephemeral=True
        )

    # -----------------------
    # XP COMMAND
    # -----------------------

    @rank.command(name="xp")
    async def xp(self, interaction: discord.Interaction, user: discord.Member = None):

        user = user or interaction.user

        guild_id = str(interaction.guild.id)
        user_id = str(user.id)

        if user_id not in self.data["users"][guild_id]:
            await interaction.response.send_message("User not ranked.", ephemeral=True)
            return

        xp = self.data["users"][guild_id][user_id]["xp"]

        level = xp_to_level(xp)

        embed = discord.Embed(
            title=f"{user.display_name}'s XP",
            description=f"Level **{level}**\nTotal XP **{xp}**",
            color=0x5865F2
        )

        await interaction.response.send_message(embed=embed)

    # -----------------------
    # LEADERBOARD
    # -----------------------

    @rank.command(name="top")
    async def leaderboard(self, interaction: discord.Interaction):

        guild_id = str(interaction.guild.id)

        users = self.data["users"][guild_id]

        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1]["xp"],
            reverse=True
        )

        embed = discord.Embed(title="🏆 Server Leaderboard", color=0x5865F2)

        desc = ""

        for i, (uid, data) in enumerate(sorted_users[:10], start=1):

            member = interaction.guild.get_member(int(uid))

            name = member.display_name if member else "Unknown"

            desc += f"**{i}. {name}** — {data['xp']} XP\n"

        embed.description = desc

        await interaction.response.send_message(embed=embed)

    # -----------------------
    # MEE6 STYLE RANK CARD
    # -----------------------

    @rank.command(name="profile")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):

        user = user or interaction.user

        guild_id = str(interaction.guild.id)
        user_id = str(user.id)

        if user_id not in self.data["users"][guild_id]:
            await interaction.response.send_message("User not ranked.")
            return

        xp = self.data["users"][guild_id][user_id]["xp"]

        level = xp_to_level(xp)

        next_xp = level_to_xp(level + 1)
        current_xp = level_to_xp(level)

        progress = (xp - current_xp) / (next_xp - current_xp)

        rank = self.get_rank_position(guild_id, user_id)

        width = 900
        height = 280

        img = Image.new("RGB", (width, height), (32, 34, 37))
        draw = ImageDraw.Draw(img)

        bar_x = 260
        bar_y = 200
        bar_width = 580
        bar_height = 35

        draw.rectangle(
            [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
            fill=(54, 57, 63),
            radius=20
        )

        draw.rectangle(
            [bar_x, bar_y, bar_x + int(bar_width * progress), bar_y + bar_height],
            fill=(88, 101, 242),
            radius=20
        )

        try:
            font_big = ImageFont.truetype("arial.ttf", 45)
            font_small = ImageFont.truetype("arial.ttf", 28)
        except:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        draw.text((260, 60), user.display_name, font=font_big, fill=(255, 255, 255))

        draw.text(
            (260, 130),
            f"LEVEL {level}",
            font=font_small,
            fill=(255, 255, 255)
        )

        draw.text(
            (700, 130),
            f"RANK #{rank}",
            font=font_small,
            fill=(255, 255, 255)
        )

        draw.text(
            (260, 170),
            f"{xp} XP",
            font=font_small,
            fill=(200, 200, 200)
        )

        avatar = requests.get(user.display_avatar.url)

        avatar = Image.open(BytesIO(avatar.content)).resize((180, 180))

        mask = Image.new("L", (180, 180), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 180, 180), fill=255)

        img.paste(avatar, (40, 50), mask)

        buffer = BytesIO()

        img.save(buffer, "PNG")

        buffer.seek(0)

        file = discord.File(buffer, filename="rank.png")

        await interaction.response.send_message(file=file)

    # -----------------------
    # ROLE CONFIG
    # -----------------------

    @rank.command(name="set")
    @app_commands.default_permissions(manage_roles=True)
    async def set_rank(self, interaction: discord.Interaction, xp: int, role: discord.Role):

        guild_id = str(interaction.guild.id)

        self.ensure_guild(guild_id)

        self.data["rank_roles"][guild_id][str(xp)] = role.id

        await interaction.response.send_message(
            f"{role.mention} unlocks at {xp} XP"
        )


async def setup(bot):
    await bot.add_cog(Ranking(bot))