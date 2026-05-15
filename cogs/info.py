import discord
from discord.ext import commands
from discord import app_commands

RULES_BANNER = "https://github.com/ShiXzYz/GG-Bot/blob/main/images/rules_head.jpg?raw=true"
RULES_SECTION_BANNER = "https://github.com/ShiXzYz/GG-Bot/blob/main/images/banner.png?raw=true"
RULES_THUMBNAIL = "https://github.com/ShiXzYz/GG-Bot/blob/main/images/rules_law.jpg?raw=true"

EMBED_COLOR = 0x8B5CF6  # Purple theme matching your branding


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # SERVER INFO COMMAND
    # =========================================================
    @app_commands.command(
        name="serverinfo",
        description="Displays information about the server"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = discord.Embed(
            title=f"Server Info: {guild.name}",
            color=EMBED_COLOR
        )

        embed.add_field(
            name="👥 Members",
            value=guild.member_count,
            inline=True
        )

        embed.add_field(
            name="👑 Owner",
            value=guild.owner,
            inline=True
        )

        embed.add_field(
            name="📅 Created On",
            value=guild.created_at.strftime("%b %d, %Y"),
            inline=False
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(
            text="Group Gathering • Server Information"
        )

        await interaction.response.send_message(embed=embed)

    # =========================================================
    # RULES COMMAND
    # =========================================================
    @app_commands.command(
        name="rules",
        description="Displays the server rules"
    )
    async def rules(self, interaction: discord.Interaction):

        header = discord.Embed(color=EMBED_COLOR)
        header.set_image(url=RULES_BANNER)

        rules_embed = discord.Embed(
            title="📜 Group Gathering • Community Guidelines",
            description=(
                "Welcome to **Group Gathering**.\n\n"
                "Our goal is to create a chill, organized, and enjoyable "
                "environment for everyone. By being in this server, "
                "you must follow the guidelines below."
            ),
            color=EMBED_COLOR
        )

        rules_embed.set_thumbnail(url=RULES_THUMBNAIL)

        # Main rules
        rules_embed.add_field(
            name="🤝 Respect Everyone",
            value=(
                "• No harassment or bullying\n"
                "• No hate speech\n"
                "• Don't start drama"
            ),
            inline=False
        )

        rules_embed.add_field(
            name="💬 Keep Chats Clean",
            value=(
                "• No spam or flooding\n"
                "• Stay on topic\n"
                "• Use channels correctly"
            ),
            inline=False
        )

        rules_embed.add_field(
            name="🚫 Don't Be Weird",
            value=(
                "• No NSFW content (only in designated channels)\n"
                "• No scams or malicious links\n"
                "• No advertising without permission"
            ),
            inline=False
        )

        rules_embed.add_field(
            name="🎤 VC Rules",
            value=(
                "• No mic spam\n"
                "• Don't disturb voice chats\n"
                "• Respect everyone in VC"
            ),
            inline=False
        )
        
        rules_embed.add_field(
            name="✨ Final Reminder",
            value=(
                "Use common sense and help maintain a welcoming community.\n"
                "Always talk things out and If you see any issues, let us know!\n"
                "**Most importantly, have fun and enjoy your time here!**"
            ),
            inline=False
        )

        rules_embed.set_image(url=RULES_SECTION_BANNER)

        rules_embed.set_footer(
            text="Group Gathering • Community Rules"
        )

        await interaction.response.send_message(
            embeds=[header, rules_embed]
        )


async def setup(bot):
    await bot.add_cog(Info(bot))