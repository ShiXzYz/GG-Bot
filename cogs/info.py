import discord
from discord.ext import commands
from discord import app_commands

# Replace these with your own rule images when you have them
RULES_BANNER = "https://via.placeholder.com/800x200.png?text=RULES+IMAGE+PLACEHOLDER"
RULES_THUMBNAIL = "https://via.placeholder.com/128.png?text=ICON+PLACEHOLDER"

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

    @app_commands.command(name="rules", description="Displays the server rules")
    async def rules(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="SERVER RULES",
            description=(
                "- Be nice!\n"
                "- Be respectful\n"
                "- Don't advertise other servers\n"
                "- Have fun!\n"
                "- Don't discriminate/bully people\n"
                "- Don't spam\n"
                "- Use channels in their appropriate way\n"
                "- You will get a warning for breaking a rule, 3 strikes and you're gone\n"
                "- If you say admin abuse, I'm coming over\n"
                "- a"
            ),
            color=0x5865F2
        )
        embed.set_thumbnail(url=RULES_THUMBNAIL)
        embed.set_image(url=RULES_BANNER)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))
