import json
from pathlib import Path
import discord
from discord.ext import commands, tasks
from discord import app_commands

STORE_PATH = Path(__file__).resolve().parent.parent / "vc_points.json"


def load_store():
    if STORE_PATH.exists():
        try:
            with open(STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_store(data):
    try:
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class VCLeaderboard(commands.Cog):
    """Tracks voice participation and exposes leaderboard commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = load_store()
        self.cache = {}
        self._save_tick = 0
        self.second_update.start()
        self.hourly_update.start()

    def _ensure_guild(self, guild_id: str):
        if guild_id not in self.store:
            self.store[guild_id] = {}

    # -------------------- HOURLY CACHE UPDATE --------------------

    @tasks.loop(hours=1)
    async def hourly_update(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            gid = str(guild.id)
            self._ensure_guild(gid)
            data = self.store.get(gid, {})
            self.cache[gid] = sorted(
                data.items(), key=lambda x: x[1], reverse=True
            )[:10]

    @hourly_update.before_loop
    async def before_hourly(self):
        await self.bot.wait_until_ready()

    # -------------------- VOICE XP TRACKER --------------------

    @tasks.loop(seconds=1)
    async def second_update(self):
        await self.bot.wait_until_ready()
        changed_any = False

        for guild in self.bot.guilds:
            gid = str(guild.id)
            self._ensure_guild(gid)
            changed = False

            for channel in guild.voice_channels:
                # Skip AFK channel
                if guild.afk_channel and channel.id == guild.afk_channel.id:
                    continue

                for member in channel.members:
                    if member.bot:
                        continue

                    voice = member.voice
                    if not voice:
                        continue

                    # Skip muted or deafened users (self or server)
                    if (
                        voice.self_mute
                        or voice.self_deaf
                        or voice.mute
                        or voice.deaf
                    ):
                        continue

                    uid = str(member.id)
                    self.store[gid].setdefault(uid, 0)
                    self.store[gid][uid] += 1
                    changed = True

            if changed:
                changed_any = True

        # Save once per minute
        self._save_tick += 1
        if self._save_tick >= 60:
            if changed_any:
                save_store(self.store)
            self._save_tick = 0

    @second_update.before_loop
    async def before_second(self):
        await self.bot.wait_until_ready()

    # -------------------- COMMANDS --------------------

    @app_commands.command(name="vc-lb", description="Show the voice XP leaderboard")
    async def vc_lb(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)
        self._ensure_guild(gid)

        items = self.cache.get(gid)
        if not items:
            data = self.store.get(gid, {})
            if not data:
                await interaction.response.send_message(
                    "No voice XP recorded yet.", ephemeral=True
                )
                return
            items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

        embed = discord.Embed(
            title="Voice XP Leaderboard", color=0x5865F2
        )

        lines = []
        for rank, (uid, pts) in enumerate(items, start=1):
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"User ID {uid}"
            lines.append(f"`#{rank}` {name} — **{pts}** pts")

        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="vc-reset",
        description="Reset voice XP (guild or a single user)",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        user="Optional user to reset; leave empty to reset guild"
    )
    async def vc_reset(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        gid = str(interaction.guild.id)
        self._ensure_guild(gid)

        if user:
            uid = str(user.id)
            if uid in self.store[gid]:
                del self.store[gid][uid]
                save_store(self.store)
                await interaction.response.send_message(
                    f"Reset voice XP for {user.display_name}."
                )
            else:
                await interaction.response.send_message(
                    "That user has no recorded XP."
                )
        else:
            self.store[gid] = {}
            save_store(self.store)
            await interaction.response.send_message(
                "Reset all voice XP for this server."
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(VCLeaderboard(bot))
