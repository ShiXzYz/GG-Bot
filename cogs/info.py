import discord
from discord.ext import commands
from discord import app_commands

RULES_BANNER = "https://github.com/ShiXzYz/GG-Bot/blob/main/images/rules_head.jpg?raw=true"
RULES_SECTION_BANNER = "https://github.com/ShiXzYz/GG-Bot/blob/main/images/banner.jpg?raw=true"
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

        # =========================
        # TOP HEADER BANNER
        # =========================
        header = discord.Embed(color=EMBED_COLOR)
        header.set_image(url=RULES_BANNER)

        # =========================
        # MAIN RULES EMBED
        # =========================
        rules_embed = discord.Embed(
            title="📜 Group Gathering • Community Guidelines",
            description=(
                "Welcome to **Group Gathering**.\n\n"
                "Our goal is to create a respectful, organized, and enjoyable "
                "environment for everyone. By participating in this server, "
                "you agree to follow the guidelines below."
            ),
            color=EMBED_COLOR
        )

        rules_embed.set_thumbnail(url=RULES_THUMBNAIL)
        rules_embed.set_image(url=RULES_SECTION_BANNER)

        # =========================
        # RULE SECTIONS
        # =========================

        rules_embed.add_field(
            name="🤝 Respect & Conduct",
            value=(
                "• Treat all members with respect.\n"
                "• Harassment, bullying, or discrimination is prohibited.\n"
                "• Excessive toxicity or drama is not tolerated.\n"
                "• Keep conversations civil and mature."
            ),
            inline=False
        )

        rules_embed.add_field(
            name="💬 Chat Guidelines",
            value=(
                "• Use channels for their intended purpose.\n"
                "• Avoid spam, flooding, or excessive caps.\n"
                "• Keep discussions relevant to the topic.\n"
                "• Do not intentionally disrupt conversations."
            ),
            inline=False
        )

        rules_embed.add_field(
            name="🚫 Prohibited Content",
            value=(
                "• No NSFW, hateful, or illegal content.\n"
                "• No scams, phishing, or malicious links.\n"
                "• No advertising or self-promotion without permission.\n"
                "• No impersonation of staff or members."
            ),
            inline=False
        )

        rules_embed.add_field(
            name="🎤 Voice Channel Rules",
            value=(
                "• Avoid mic spam or disruptive audio.\n"
                "• Respect others in voice chats.\n"
                "• Soundboards/music should not disturb channels.\n"
                "• Do not intentionally troll or ear-rape users."
            ),
            inline=False
        )

        rules_embed.add_field(
            name="🛡️ Staff & Enforcement",
            value=(
                "• Staff decisions should be respected.\n"
                "• Punishments may include warnings, mutes, or bans.\n"
                "• Severe violations may result in immediate removal.\n"
                "• Appeals can be discussed respectfully with staff."
            ),
            inline=False
        )

        rules_embed.add_field(
            name="✨ Final Reminder",
            value=(
                "Use common sense and help maintain a welcoming community.\n"
                "If you see rule-breaking behavior, report it to staff."
            ),
            inline=False
        )

        rules_embed.set_footer(
            text="Group Gathering • Community Rules",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        await interaction.response.send_message(
            embeds=[header, rules_embed]
        )


async def setup(bot):
    await bot.add_cog(Info(bot))