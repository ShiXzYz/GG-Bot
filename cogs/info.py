import discord
from discord.ext import commands
from discord import app_commands

# Replace these with your own rule images when you have them
RULES_BANNER = "https://github.com/ShiXzYz/GG-Bot/blob/main/images/rules_head.jpg?raw=true"
RULES_THUMBNAIL = "https://github.com/ShiXzYz/GG-Bot/blob/main/images/law_rules.jpg?raw=true"

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
        banner = discord.Embed(color=0x5865F2)
        banner.set_image(url=RULES_BANNER)

        rules_embed = discord.Embed(
            title="Server Rules",
            description="Follow these rules to keep the server safe, friendly, and fun for everyone.",
            color=0x5865F2
        )
        rules_embed.set_thumbnail(url=RULES_THUMBNAIL)
        rules_embed.add_field(
            name="Community Behavior",
            value=(
                "• Be nice!\n"
                "• Be respectful\n"
                "• Don't discriminate/bully people"
            ),
            inline=False
        )
        rules_embed.add_field(
            name="What Not to Do",
            value=(
                "• Don't advertise other servers\n"
                "• Don't spam\n"
                "• Use channels in their appropriate way"
            ),
            inline=False
        )
        rules_embed.add_field(
            name="Consequences",
            value=(
                "• You will get a warning for breaking a rule\n"
                "• 3 strikes and you're gone\n"
                "• If you say admin abuse, I'm coming over"
            ),
            inline=False
        )
        rules_embed.set_footer(text="Server rules are enforced by staff. Please read carefully.")

        await interaction.response.send_message(embed=banner)
        await interaction.followup.send(embed=rules_embed)

async def setup(bot):
    await bot.add_cog(Info(bot))
