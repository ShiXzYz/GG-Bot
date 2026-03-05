import discord
from discord.ext import commands, tasks
from discord import app_commands
from mcstatus import JavaServer
from config import SERVERS
import asyncio
import json
from pathlib import Path

STATUS_META_PATH = Path(__file__).resolve().parent.parent / "status_meta.json"


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


def progress_bar(current, maximum, length=12):
    if maximum == 0:
        return "｢░░░░░░░░░░░░｣"
    filled_chars = int(length * current / maximum)
    bar = "█" * filled_chars + "░" * (length - filled_chars)
    return f"｢`{bar}`｣"


class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.meta = load_json(STATUS_META_PATH)
        self.refresh_status.start()

    def cog_unload(self):
        self.refresh_status.cancel()

    async def build_embed(self) -> discord.Embed:
        all_online = True

        embed = discord.Embed(
            description="**S Y S T E M  ·  D A S H B O A R D**\n` 🟢 ONLINE ` | ` 🟡 MAINTENANCE ` | ` 🔴 OFFLINE `\n" + "─" * 35,
            color=0x2B2D31,
            timestamp=discord.utils.utcnow()
        )
        embed.set_image(url="https://github.com/ShiXzYz/GG-Bot/blob/main/images/status_head.jpg?raw=true")

        for srv in SERVERS:
            try:
                server = JavaServer.lookup(f"{srv['address']}:{srv['port']}")

                # Run blocking mcstatus call in thread
                status = await asyncio.to_thread(server.status)

                players_online = status.players.online
                players_max = status.players.max
                ping = round(status.latency)

                status_dot = "🟢" if ping < 100 else "🟡"
                bar = progress_bar(players_online, players_max)

                content = (
                    f"> **Network State:** {status_dot} Operational\n"
                    f"> **User Load:** `{players_online}`/`{players_max}`\n"
                    f"{bar}\n"
                    f"**Latency:** `{ping}ms`"
                )

                try:
                    query = await asyncio.to_thread(server.query)
                    names = ", ".join(query.players[:3]) if query.players else "Empty"
                    content += f"  |  **Active:** *{names}*"
                except Exception:
                    pass

            except Exception:
                content = "> **Network State:** 🔴 Offline\n> *Connection refused by host.*"
                all_online = False

            embed.add_field(
                name=f"📡 {srv['name'].upper()}",
                value=content + "\n" + "─" * 25,
                inline=False
            )

        embed.color = discord.Color.dark_green()

        if self.bot.user:
            embed.set_author(
                name="NETWORK MONITOR v2.4",
                icon_url=self.bot.user.display_avatar.url
            )
        else:
            embed.set_author(name="NETWORK MONITOR v2.4")

        embed.set_footer(text="LIVE TELEMETRY")

        return embed

    @tasks.loop(minutes=30)
    async def refresh_status(self):
        await self.bot.wait_until_ready()

        for gid, meta in list(self.meta.items()):
            guild = self.bot.get_guild(int(gid))
            if not guild:
                continue

            channel = guild.get_channel(meta["channel_id"])
            if not channel:
                self.meta.pop(gid, None)
                save_json(STATUS_META_PATH, self.meta)
                continue

            try:
                message = await channel.fetch_message(meta["message_id"])
                embed = await self.build_embed()
                await message.edit(embed=embed)

            except (discord.NotFound, discord.Forbidden):
                self.meta.pop(gid, None)
                save_json(STATUS_META_PATH, self.meta)

    @app_commands.command(name="servers", description="Show server status dashboard")
    async def servers(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)

        if gid in self.meta:
            await interaction.response.send_message(
                "❌ A status dashboard already exists for this server.",
                ephemeral=True,
            )
            return

        # Prevent interaction timeout
        await interaction.response.defer(ephemeral=True)

        embed = await self.build_embed()

        msg = await interaction.channel.send(embed=embed)

        self.meta[gid] = {
            "channel_id": interaction.channel.id,
            "message_id": msg.id,
        }

        save_json(STATUS_META_PATH, self.meta)

        await interaction.followup.send(
            "✅ Status dashboard posted! It will auto-refresh every 30 minutes.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))