import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import time
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from database import load_ranking_data as load_data, save_ranking_data as save_data


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
            try:
                role_id = int(role_id)
            except Exception:
                pass

            if xp >= xp_req and xp_req > highest_xp:
                highest_xp = xp_req
                highest_role = role_id

        # Always keep the 0 XP role if it exists
        zero_role = rank_roles.get("0")

        # Remove roles that are not the highest_role and not the 0 XP role
        for role_id in rank_roles.values():
            try:
                rid = int(role_id)
            except Exception:
                rid = role_id
            if rid != highest_role and rid != zero_role:
                role = member.guild.get_role(rid)
                if role and role in member.roles:
                    await member.remove_roles(role)

        # Add the highest_role if not already have it
        if highest_role:
            role = member.guild.get_role(highest_role)
            if role and role not in member.roles:
                await member.add_roles(role)

        # Ensure the 0 XP role is always assigned if it exists
        if zero_role:
            role = member.guild.get_role(zero_role)
            if role and role not in member.roles:
                await member.add_roles(role)

    # -----------------------
    # MESSAGE XP SYSTEM
    # -----------------------

    @commands.Cog.listener()
    async def on_message(self, message):
        if len(message.content) < 3:
            return

        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        self.ensure_guild(guild_id)

        if user_id not in self.data["users"][guild_id]:
            self.data["users"][guild_id][user_id] = {
                "xp": 0,
                "active": True
            }

        user = self.data["users"][guild_id][user_id]

        cooldown_key = f"{guild_id}:{user_id}"

        now = time.time()

        if now - self.cooldowns.get(cooldown_key, 0) < 5:
            return

        xp_gain = random.randint(5, 10)

        user["xp"] += xp_gain

        self.cooldowns[cooldown_key] = now

        await self.update_user_roles(message.author)

        await self.bot.process_commands(message)

    # -----------------------
    # XP COMMAND
    # -----------------------

    @rank.command(name="xp")
    async def xp(self, interaction: discord.Interaction, user: discord.Member = None):

        user = user or interaction.user

        guild_id = str(interaction.guild.id)
        user_id = str(user.id)

        # make sure the guild has entries to avoid KeyError
        self.ensure_guild(guild_id)

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
        # ensure guild isinitialised so we don't crash when no data exists
        self.ensure_guild(guild_id)

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

        await interaction.response.defer()

        user = user or interaction.user

        guild_id = str(interaction.guild.id)
        user_id = str(user.id)

        # avoid KeyError and ensure a proper guild entry exists
        self.ensure_guild(guild_id)

        if user_id not in self.data["users"][guild_id]:
            # we already deferred so follow up instead
            await interaction.followup.send("User not ranked.", ephemeral=True)
            return

        xp = self.data["users"][guild_id][user_id]["xp"]

        level = xp_to_level(xp)

        next_xp = level_to_xp(level + 1)
        current_xp = level_to_xp(level)

        progress = (xp - current_xp) / (next_xp - current_xp)

        rank = self.get_rank_position(guild_id, user_id)

        # generate image inside try/except
        try:
            width = 900
            height = 280

            img = Image.new("RGB", (width, height), (32, 34, 37))
            draw = ImageDraw.Draw(img)

            bar_x = 260
            bar_y = 200
            bar_width = 580
            bar_height = 35

            # draw bars with rounded corners; use rounded_rectangle as radius parameter
            try:
                draw.rounded_rectangle(
                    [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                    fill=(54, 57, 63),
                    radius=20
                )

                draw.rounded_rectangle(
                    [bar_x, bar_y, bar_x + int(bar_width * progress), bar_y + bar_height],
                    fill=(88, 101, 242),
                    radius=20
                )
            except AttributeError:
                # older Pillow versions may not have rounded_rectangle
                draw.rectangle(
                    [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                    fill=(54, 57, 63)
                )
                draw.rectangle(
                    [bar_x, bar_y, bar_x + int(bar_width * progress), bar_y + bar_height],
                    fill=(88, 101, 242)
                )

            try:
                font_name = ImageFont.truetype("fonts/Roboto-Regular.ttf", 50)
                font_level = ImageFont.truetype("fonts/Roboto-Regular.ttf", 30)
                font_xp = ImageFont.truetype("fonts/Roboto-Regular.ttf", 20)
            except:
                font_name = ImageFont.load_default()
                font_level = ImageFont.load_default()
                font_xp = ImageFont.load_default()

            # Username
            draw.text(
                (260, 60),
                user.display_name,
                font=font_name,
                fill=(255, 255, 255)
            )

            # Level
            draw.text(
                (260, 135),
                f"LEVEL {level}",
                font=font_level,
                fill=(255, 255, 255)
            )

            # Rank
            draw.text(
                (650, 135),
                f"RANK #{rank}",
                font=font_level,
                fill=(255, 255, 255)
            )

            # XP text
            draw.text(
                (260, 170),
                f"{xp} XP",
                font=font_xp,
                fill=(200, 200, 200)
            )

            # fetch avatar with a timeout so the command doesn't hang indefinitely
            try:
                resp = requests.get(user.display_avatar.url, timeout=10)
                avatar = Image.open(BytesIO(resp.content)).resize((180, 180))
            except Exception:
                avatar = None

            if avatar:
                mask = Image.new("L", (180, 180), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 180, 180), fill=255)

                img.paste(avatar, (40, 50), mask)

            buffer = BytesIO()
            img.save(buffer, "PNG")
            buffer.seek(0)
            file = discord.File(buffer, filename="rank.png")

            await interaction.followup.send(file=file)
        except Exception:
            await interaction.followup.send("Failed to generate profile card.", ephemeral=True)

    # -----------------------
    # ROLE CONFIG
    # -----------------------

    def admin_or_owner_check():
        async def predicate(interaction: discord.Interaction):
            # allow server owner or anyone with administrator permission
            if interaction.guild is None:
                return False
            if interaction.user == interaction.guild.owner:
                return True
            return interaction.user.guild_permissions.administrator
        return app_commands.check(predicate)

    @rank.command(name="set")
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()
    async def set_rank(self, interaction: discord.Interaction, xp: int, role: discord.Role):

        guild_id = str(interaction.guild.id)

        self.ensure_guild(guild_id)

        self.data["rank_roles"][guild_id][str(xp)] = role.id

        # immediately ensure any existing users who already have enough XP get the new role
        for uid, udata in self.data["users"][guild_id].items():
            try:
                member = interaction.guild.get_member(int(uid))
            except Exception:
                member = None
            if member:
                await self.update_user_roles(member)

        await interaction.response.send_message(
            f"{role.mention} unlocks at {xp} XP"
        )

    @rank.command(name="remove")
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()
    async def remove_rank(self, interaction: discord.Interaction, xp: int):

        guild_id = str(interaction.guild.id)

        self.ensure_guild(guild_id)

        if str(xp) in self.data["rank_roles"][guild_id]:
            role_id = self.data["rank_roles"][guild_id][str(xp)]
            role = interaction.guild.get_role(role_id)
            role_name = role.name if role else "Unknown Role"
            del self.data["rank_roles"][guild_id][str(xp)]
            # after removal, rebuild roles for everyone in case they need to lose it
            for uid, udata in self.data["users"][guild_id].items():
                try:
                    member = interaction.guild.get_member(int(uid))
                except Exception:
                    member = None
                if member:
                    await self.update_user_roles(member)
            await interaction.response.send_message(
                f"Removed rank for {xp} XP ({role_name})"
            )
        else:
            await interaction.response.send_message(
                f"No rank set for {xp} XP",
                ephemeral=True
            )

    @rank.command(name="list")
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()
    async def list_ranks(self, interaction: discord.Interaction):

        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        rank_roles = self.data["rank_roles"][guild_id]

        if not rank_roles:
            await interaction.response.send_message(
                "No rank roles configured.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title="Rank Roles", color=0x5865F2)

        desc = ""

        for xp_req in sorted(rank_roles.keys(), key=int):
            role_id = rank_roles[xp_req]
            try:
                rid = int(role_id)
            except Exception:
                rid = role_id
            role = interaction.guild.get_role(rid)
            role_name = role.name if role else "Unknown Role"
            desc += f"**{xp_req} XP** — {role_name}\n"

        embed.description = desc

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Ranking(bot))