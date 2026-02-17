import json
from pathlib import Path
import discord
from discord.ext import commands, tasks
from discord import app_commands

STORE_PATH = Path(__file__).resolve().parent.parent / "vc_points.json"
META_PATH = Path(__file__).resolve().parent.parent / "vc_lb_meta.json"

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
                embed = self.build_embed(guild)
                await message.edit(embed=embed)

            except (discord.NotFound, discord.Forbidden):
                # Leaderboard message was deleted or inaccessible — clean up
                self.meta.pop(gid, None)
                save_json(META_PATH, self.meta)

    # -------------------- EMBED BUILDER --------------------

    def build_embed(self, guild: discord.Guild):
        gid = str(guild.id)
        data = self.store.get(gid, {})
        items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

        embed = discord.Embed(
            title="🎙️ Voice XP Leaderboard",
            color=0x5865F2,
            timestamp=discord.utils.utcnow(),
        )

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

        embed = self.build_embed(interaction.guild)

        await interaction.response.send_message(
            "✅ Leaderboard set! It will auto-refresh every 30 minutes.",
            ephemeral=True,
        )

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
