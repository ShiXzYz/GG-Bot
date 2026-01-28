import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
from config import SERVERS, STATUS_CHANNEL_ID
from discord import NotFound
from datetime import datetime

def progress_bar(current, maximum, length=12):
    """Refined progress bar with 'rounded' endcaps."""
    if maximum == 0: return "｢░░░░░░░░░░░░｣"
    filled_chars = int(length * current / maximum)
    bar = "█" * filled_chars + "░" * (length - filled_chars)
    return f"｢`{bar}`｣"

class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_id = None
        self.update_status.start()

    def build_embed(self) -> discord.Embed:
        all_online = True
        
        # Web-style Header using thin space characters and bold caps
        embed = discord.Embed(
            title="S Y S T E M  ·  D A S H B O A R D",
            description="` 🟢 ONLINE ` | ` 🟡 MAINTENANCE ` | ` 🔴 OFFLINE `\n" + "─" * 35,
            color=0x2b2d31, # Dark 'Discord Gray' for a modern UI look
            timestamp=datetime.utcnow()
        )

        for srv in SERVERS:
            try:
                # Optimized lookup (async is better but keeping your structure)
                server = JavaServer.lookup(f"{srv['address']}:{srv['port']}")
                status = server.status()
                
                players_online = status.players.online
                players_max = status.players.max
                ping = round(status.latency)
                
                # Logic for status dot
                status_dot = "🟢" if ping < 100 else "🟡"
                bar = progress_bar(players_online, players_max)

                # UI Layout for the field
                content = (
                    f"> **Network State:** {status_dot} Operational\n"
                    f"> **User Load:** `{players_online}`/`{players_max}`\n"
                    f"{bar}\n"
                    f"**Latency:** `{ping}ms`"
                )

                # Try to get player names (Query must be enabled in server.properties)
                try:
                    query = server.query()
                    names = ", ".join(query.players[:3]) if query.players else "Empty"
                    content += f"  |  **Active:** *{names}*"
                except:
                    pass

            except Exception:
                content = "> **Network State:** 🔴 Offline\n> *Connection refused by host.*"
                all_online = False

            embed.add_field(
                name=f"📡 {srv['name'].upper()}", 
                value=content + "\n" + "─" * 25, 
                inline=False
            )

        # Set specific UI Color: Green if all up, Red if any are down
        if not all_online:
            embed.color = discord.Color.red()
        else:
            embed.color = 0x2ecc71 # Emerald Green

        embed.set_author(name="NETWORK MONITOR v2.4", icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(text="LIVE TELEMETRY • Next refresh")
        
        return embed

    @tasks.loop(minutes=1)
    async def update_status(self):
        channel = self.bot.get_channel(STATUS_CHANNEL_ID)
        if not channel: return

        embed = self.build_embed()

        try:
            if self.message_id:
                msg = await channel.fetch_message(self.message_id)
                await msg.edit(embed=embed)
            else:
                msg = await channel.send(embed=embed)
                self.message_id = msg.id
        except NotFound:
            msg = await channel.send(embed=embed)
            self.message_id = msg.id

    @update_status.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))
