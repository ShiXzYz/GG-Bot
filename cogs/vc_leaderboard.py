import json
from pathlib import Path
from io import BytesIO
import discord
from discord.ext import commands, tasks
from discord import app_commands
from PIL import Image

STORE_PATH = Path(__file__).resolve().parent.parent / "vc_points.json"
META_PATH = Path(__file__).resolve().parent.parent / "vc_lb_meta.json"
IMAGE_SOURCE = Path(__file__).resolve().parent.parent / "vc-embed.jpg"

# -------------------- STORAGE --------------------

def load_json(path):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# -------------------- COG --------------------

class VCLeaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = load_json(STORE_PATH)
        self.meta = load_json(META_PATH)
        self._save_tick = 0
        self.second_update.start()
        self.refresh_lb.start()

    def cog_unload(self):
        self.second_update.cancel()
        self.refresh_lb.cancel()

    # -------------------- VOICE XP (1 Point Per Second) --------------------

    @tasks.loop(seconds=1)
    async def second_update(self):
        await self.bot.wait_until_ready()
        changed_any = False

        for guild in self.bot.guilds:
            gid = str(guild.id)
            self.store.setdefault(gid, {})
            guild_changed = False

            for channel in guild.voice_channels:
                if guild.afk_channel and channel.id == guild.afk_channel.id:
                    continue

                for member in channel.members:
                    if member.bot:
                        continue

                    v = member.voice
                    if not v or v.self_mute or v.self_deaf or v.mute or v.deaf:
                        continue

                    uid = str(member.id)
                    self.store[gid][uid] = self.store[gid].get(uid, 0) + 1
                    guild_changed = True

            if guild_changed:
                changed_any = True

        # Save every 60 seconds
        self._save_tick += 1
        if self._save_tick >= 60:
            if changed_any:
                save_json(STORE_PATH, self.store)
            self._save_tick = 0

    # -------------------- LEADERBOARD AUTO-REFRESH --------------------

    @tasks.loop(minutes=30)
    async def refresh_lb(self):
        await self.bot.wait_until_ready()

        for gid, meta in list(self.meta.items()):
            guild = self.bot.get_guild(int(gid))
            if not guild:
                continue

            channel = guild.get_channel(meta["channel_id"])
            if not channel:
                self.meta.pop(gid, None)
                save_json(META_PATH, self.meta)
                continue

            try:
                message = await channel.fetch_message(meta["message_id"])
                attachment_url = None
                if message.attachments:
                    attachment_url = message.attachments[0].url

                embed = self.build_embed(guild, image_url=attachment_url)
                await message.edit(embed=embed)

            except (discord.NotFound, discord.Forbidden):
                # Leaderboard message was deleted or inaccessible — clean up
                self.meta.pop(gid, None)
                save_json(META_PATH, self.meta)

    # -------------------- EMBED BUILDER --------------------

    def build_embed(self, guild: discord.Guild, image_url=None):
        gid = str(guild.id)
        data = self.store.get(gid, {})
        items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

        embed = discord.Embed(
            title="🎙️ Voice XP Leaderboard",
            color=0x5865F2,
            timestamp=discord.utils.utcnow(),
        )

        # Set image at the top (displays before description content)
        if image_url:
            embed.set_image(url=image_url)

        # Build leaderboard entries
        if not items:
            embed.description = "No voice XP recorded yet."
        else:
            lines = []
            for i, (uid, pts) in enumerate(items, start=1):
                member = guild.get_member(int(uid))
                name = member.display_name if member else f"User {uid}"
                lines.append(f"`#{i}` **{name}** — `{pts:,}` pts")

            embed.description = "\n".join(lines)

        embed.set_footer(text="Auto-refreshes every 30m • Refreshed at")
        return embed

    # -------------------- COMMANDS --------------------

    @app_commands.command(name="vc-lb", description="Post the live voice XP leaderboard")
    @app_commands.checks.has_permissions(administrator=True)
    async def vc_lb(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)

        # Prevent multiple leaderboards per server
        if gid in self.meta:
            await interaction.response.send_message(
                "❌ A leaderboard already exists for this server.",
                ephemeral=True,
            )
            return

        # Prepare the embed image (resize local image and attach it)
        file = None
        attachment_name = None
        if IMAGE_SOURCE.exists():
            try:
                img = Image.open(IMAGE_SOURCE).convert("RGBA")
                base_width = 800
                wpercent = base_width / float(img.width)
                hsize = int((float(img.height) * float(wpercent)))
                img = img.resize((base_width, hsize), Image.LANCZOS)

                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                attachment_name = "vc-embed.png"
                file = discord.File(fp=buf, filename=attachment_name)
            except Exception:
                file = None

        image_url = f"attachment://{attachment_name}" if attachment_name else None
        embed = self.build_embed(interaction.guild, image_url=image_url)

        await interaction.response.send_message(
            "✅ Leaderboard set! It will auto-refresh every 30 minutes.",
            ephemeral=True,
        )

        if file:
            msg = await interaction.channel.send(embed=embed, file=file)
        else:
            msg = await interaction.channel.send(embed=embed)

        self.meta[gid] = {
            "channel_id": interaction.channel.id,
            "message_id": msg.id,
        }
        save_json(META_PATH, self.meta)

    @app_commands.command(name="vc-reset", description="Reset all voice XP for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def vc_reset(self, interaction: discord.Interaction):
        self.store[str(interaction.guild.id)] = {}
        save_json(STORE_PATH, self.store)

        await interaction.response.send_message(
            "✅ Voice XP has been reset for this server.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VCLeaderboard(bot))