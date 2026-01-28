import discord
from discord.ext import commands
from discord import app_commands

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serverinfo", description="Displays information about the server")
    # This line ensures only members with 'Manage Server' permissions can use it
    @app_commands.default_permissions(manage_guild=True)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"Server Info: {guild.name}",
            color=0x5865F2
        )
        
        # Adding more useful fields for your network management
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Owner", value=guild.owner, inline=True)
        embed.add_field(name="Created On", value=guild.created_at.strftime("%b %d, %Y"), inline=False)

        # Safety check: only set thumbnail if the server actually has an icon
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))
