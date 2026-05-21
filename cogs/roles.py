import discord
from discord.ext import commands
from discord import app_commands
from config import AUTO_ROLE_ID
from database import load_roles_data as load_data, save_roles_data as save_data


# =========================
# BUTTON ROLE VIEW
# =========================

class RoleButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Get Survival Role",
        emoji="🌲",
        style=discord.ButtonStyle.success,
        custom_id="role_survival"
    )
    async def survival(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = discord.utils.get(interaction.guild.roles, name="Survival")

        if role:
            await interaction.user.add_roles(role)

            embed = discord.Embed(
                title="✅ Role Added",
                description=f"You now have {role.mention}",
                color=0x57F287
            )

            embed.set_footer(text="Role updated instantly")

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        else:
            embed = discord.Embed(
                title="⚠️ Role Not Found",
                description="The configured role does not exist.",
                color=0xED4245
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )


# =========================
# COG
# =========================

class Roles(commands.Cog):
    """Professional reaction role system."""

    roles = app_commands.Group(
        name="roles",
        description="Manage reaction role menus"
    )

    def __init__(self, bot):
        self.bot = bot
        bot.add_view(RoleButtons())
        self.data = load_data()

    async def cog_unload(self):
        save_data(self.data)

    # =========================
    # ADMIN CHECK
    # =========================

    def admin_or_owner_check():
        async def predicate(interaction: discord.Interaction):

            if interaction.guild is None:
                return False

            if interaction.user == interaction.guild.owner:
                return True

            return interaction.user.guild_permissions.administrator

        return app_commands.check(predicate)

    # =========================
    # ENSURE GUILD DATA
    # =========================

    async def ensure_guild(self, guild_id: str):

        if guild_id not in self.data:
            self.data[guild_id] = {
                "messages": {},
                "auto_role": None
            }

    # =========================
    # PROFESSIONAL EMBED BUILDER
    # =========================

    def build_menu_embed(
        self,
        title: str,
        description: str,
        mappings: dict,
        guild: discord.Guild | None = None
    ):

        embed = discord.Embed(
            title=f"✨ {title}",
            description=(
                f"{description}\n\n"
                "## Select Your Roles\n"
                "React below to customize your access."
            ),
            color=0x5865F2
        )

        # Banner Image
        embed.set_image(
            url="https://i.imgur.com/AfFp7pu.png"
        )

        # Server Icon Thumbnail
        if guild and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Role List
        if mappings:

            role_lines = []

            for emoji, role_id in mappings.items():

                role = guild.get_role(role_id) if guild else None

                if role:
                    role_lines.append(
                        f"{emoji}  •  **{role.mention}**"
                    )

                else:
                    role_lines.append(
                        f"{emoji}  •  **<@&{role_id}>**"
                    )

            embed.add_field(
                name="🎮 **Available Roles**",
                value="\n".join(role_lines),
                inline=False
            )

        else:

            embed.add_field(
                name="🎮 Available Roles",
                value="No roles configured yet.",
                inline=False
            )

        # Info Section
        embed.add_field(
            name="ℹ️ Information",
            value=(
                "• React to gain a role\n"
                "• Remove your reaction to remove it"
            ),
            inline=False
        )

        # Footer
        if guild:
            embed.set_footer(
                text=f"{guild.name} Role System",
                icon_url=guild.icon.url if guild.icon else None
            )

        return embed

    # =========================
    # AUTO ROLE ON JOIN
    # =========================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        guild_id = str(member.guild.id)

        await self.ensure_guild(guild_id)

        role_id = (
            self.data[guild_id].get("auto_role")
            or AUTO_ROLE_ID
        )

        try:
            role_id = int(role_id)
        except Exception:
            pass

        role = member.guild.get_role(role_id)

        if role:
            await member.add_roles(role)

    # =========================
    # REACTION ADD
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent
    ):

        if payload.user_id == self.bot.user.id:
            return

        guild_id = str(payload.guild_id)
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)

        await self.ensure_guild(guild_id)

        msg_entry = self.data[guild_id]["messages"].get(message_id)

        if not msg_entry:
            return

        role_id = msg_entry["mappings"].get(emoji)

        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        member = guild.get_member(payload.user_id)

        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception:
                return

        role = guild.get_role(int(role_id))

        if role:
            try:
                await member.add_roles(role)
            except Exception:
                pass

    # =========================
    # REACTION REMOVE
    # =========================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent
    ):

        guild_id = str(payload.guild_id)
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)

        await self.ensure_guild(guild_id)

        msg_entry = self.data[guild_id]["messages"].get(message_id)

        if not msg_entry:
            return

        role_id = msg_entry["mappings"].get(emoji)

        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        try:
            member = await guild.fetch_member(payload.user_id)
        except Exception:
            return

        role = guild.get_role(int(role_id))

        if role:
            try:
                await member.remove_roles(role)
            except Exception:
                pass

    # =========================
    # CREATE MENU
    # =========================

    @roles.command(name="create")
    @app_commands.describe(
        title="Embed title",
        description="Embed description"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()

    async def create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str = ""
    ):

        embed = self.build_menu_embed(
            title,
            description,
            {},
            interaction.guild
        )

        msg = await interaction.channel.send(embed=embed)

        guild_id = str(interaction.guild_id)

        await self.ensure_guild(guild_id)

        self.data[guild_id]["messages"][str(msg.id)] = {
            "channel_id": msg.channel.id,
            "mappings": {},
            "title": title,
            "description": description,
        }

        save_data(self.data)

        success = discord.Embed(
            title="✅ Role Menu Created",
            description=f"Message ID: `{msg.id}`",
            color=0x57F287
        )

        await interaction.response.send_message(
            embed=success,
            ephemeral=True
        )

    # =========================
    # ADD ROLE MAPPING
    # =========================

    @roles.command(name="add")
    @app_commands.describe(
        message_id="ID of the menu message",
        emoji="Emoji to react with",
        role="Role to assign"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()

    async def add(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str,
        role: discord.Role
    ):

        message_id = message_id.strip()

        if not message_id.isdigit():

            await interaction.response.send_message(
                "❌ Invalid message ID.",
                ephemeral=True
            )

            return

        guild_id = str(interaction.guild_id)

        await self.ensure_guild(guild_id)

        msg_entry = self.data[guild_id]["messages"].get(message_id)

        if not msg_entry:

            await interaction.response.send_message(
                "❌ Message not found.",
                ephemeral=True
            )

            return

        # Save Mapping
        msg_entry["mappings"][emoji] = role.id

        save_data(self.data)

        # Update Embed
        channel = (
            self.bot.get_channel(msg_entry["channel_id"])
            or await self.bot.fetch_channel(msg_entry["channel_id"])
        )

        try:

            msg = await channel.fetch_message(int(message_id))

            title = msg_entry.get("title", "")
            description = msg_entry.get("description", "")

            await msg.edit(
                embed=self.build_menu_embed(
                    title,
                    description,
                    msg_entry["mappings"],
                    interaction.guild
                )
            )

            await msg.add_reaction(emoji)

        except Exception:
            pass

        success = discord.Embed(
            title="✅ Role Added",
            description=f"{emoji} → {role.mention}",
            color=0x57F287
        )

        await interaction.response.send_message(
            embed=success,
            ephemeral=True
        )

    # =========================
    # REMOVE ROLE MAPPING
    # =========================

    @roles.command(name="remove")
    @app_commands.describe(
        message_id="ID of the menu message",
        emoji="Emoji to remove"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()

    async def remove(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str
    ):

        guild_id = str(interaction.guild_id)

        await self.ensure_guild(guild_id)

        msg_entry = self.data[guild_id]["messages"].get(message_id)

        if not msg_entry or emoji not in msg_entry["mappings"]:

            await interaction.response.send_message(
                "❌ Mapping not found.",
                ephemeral=True
            )

            return

        msg_entry["mappings"].pop(emoji)

        save_data(self.data)

        try:

            channel = (
                self.bot.get_channel(msg_entry["channel_id"])
                or await self.bot.fetch_channel(msg_entry["channel_id"])
            )

            msg = await channel.fetch_message(int(message_id))

            title = msg_entry.get("title", "")
            description = msg_entry.get("description", "")

            await msg.edit(
                embed=self.build_menu_embed(
                    title,
                    description,
                    msg_entry["mappings"],
                    interaction.guild
                )
            )

            await msg.clear_reaction(emoji)

        except Exception:
            pass

        success = discord.Embed(
            title="✅ Mapping Removed",
            description=f"Removed {emoji}",
            color=0xED4245
        )

        await interaction.response.send_message(
            embed=success,
            ephemeral=True
        )

    # =========================
    # LIST MAPPINGS
    # =========================

    @roles.command(name="list")
    @app_commands.describe(
        message_id="ID of the menu message"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()

    async def _list(
        self,
        interaction: discord.Interaction,
        message_id: str
    ):

        guild_id = str(interaction.guild_id)

        await self.ensure_guild(guild_id)

        msg_entry = self.data[guild_id]["messages"].get(message_id)

        if not msg_entry:

            await interaction.response.send_message(
                "❌ Menu not found.",
                ephemeral=True
            )

            return

        mappings = msg_entry["mappings"]

        if not mappings:

            await interaction.response.send_message(
                "No mappings configured.",
                ephemeral=True
            )

            return

        lines = []

        for emoji, rid in mappings.items():

            role = interaction.guild.get_role(rid)

            lines.append(
                f"{emoji} → {role.mention if role else rid}"
            )

        embed = discord.Embed(
            title="📋 Role Mappings",
            description="\n".join(lines),
            color=0x5865F2
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =========================
    # SET AUTO ROLE
    # =========================

    @roles.command(name="set_auto")
    @app_commands.describe(
        role="Role to give new members automatically"
    )
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()

    async def set_auto(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):

        guild_id = str(interaction.guild_id)

        await self.ensure_guild(guild_id)

        self.data[guild_id]["auto_role"] = role.id

        save_data(self.data)

        embed = discord.Embed(
            title="✅ Auto Role Updated",
            description=f"New members will receive {role.mention}",
            color=0x57F287
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =========================
    # UNSET AUTO ROLE
    # =========================

    @roles.command(name="unset_auto")
    @app_commands.default_permissions(administrator=True)
    @admin_or_owner_check()

    async def unset_auto(
        self,
        interaction: discord.Interaction
    ):

        guild_id = str(interaction.guild_id)

        await self.ensure_guild(guild_id)

        self.data[guild_id]["auto_role"] = None

        save_data(self.data)

        embed = discord.Embed(
            title="✅ Auto Role Cleared",
            description="Using default configuration again.",
            color=0xFEE75C
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# =========================
# LOAD COG
# =========================

async def setup(bot):
    await bot.add_cog(Roles(bot))