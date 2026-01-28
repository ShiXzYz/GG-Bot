import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
from config import SERVERS, STATUS_CHANNEL_ID

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_id = None
        self.update_status.start()

    def build_embed(self):
        embed = discord.Embed(
            title="🟢 Minecraft Network Status",
            color=0x2ecc71
        )

        for srv in SERVERS:
            try:
                server = JavaServer.lookup(f"{srv['address']}:{srv['port']}")
                status = server.status()
                value = (
                    f"**Status:** Online\n"
                    f"**Players:** {status.players.online}/{status.players.max}\n"
                    f"**Ping:** {round(status.latency)} ms"
                )
            except:
                value = "**Status:** 🔴 Offline"

            embed.add_field(name=srv["name"], value=value, inline=False)

        embed.set_footer(text="Auto-updating")
        return embed

    @tasks.loop(minutes=1)
    async def update_status(self):
        channel = self.bot.get_channel(STATUS_CHANNEL_ID)
        if not channel:
            return

        embed = self.build_embed()

        if self.message_id:
            msg = await channel.fetch_message(self.message_id)
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            self.message_id = msg.id

async def setup(bot):
    await bot.add_cog(Status(bot))

