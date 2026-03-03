import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from config import AUTO_ROLE_ID

STORAGE_FILE = "roles_menus.json"


def load_data():
    if not os.path.exists(STORAGE_FILE):
        return {}
    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class RoleButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Survival",
        style=discord.ButtonStyle.green,
        custom_id="role_survival"  # required for persistent views
    )
    async def survival(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Survival")
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                f"✅ You have been given the **{role.name}** role!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "⚠️ Role not found on this server.",
                ephemeral=True,
            )


class Roles(commands.Cog):
    """Reaction role menu management and auto-role on join."""

    roles = app_commands.Group(name="roles", description="Manage reaction role menus")

    def __init__(self, bot):
        self.bot = bot
        bot.add_view(RoleButtons())
        self.data = load_data()

    async def cog_unload(self):
        save_data(self.data)

    async def ensure_guild(self, guild_id: str):
        if guild_id not in self.data:
            self.data[guild_id] = {"messages": {}}

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
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
        role = guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
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
        role = guild.get_role(role_id)
        if role:
            try:
                await member.remove_roles(role)
            except Exception:
                pass

    @roles.command(name="create")
    @app_commands.describe(title="Embed title", description="Embed description")
    @app_commands.default_permissions(manage_guild=True)
    async def create(self, interaction: discord.Interaction, title: str, description: str = ""):
        """Create a roles menu message in the current channel."""
        embed = discord.Embed(title=title, description=description, color=0x5865F2)
        msg = await interaction.channel.send(embed=embed)
        guild_id = str(interaction.guild_id)
        await self.ensure_guild(guild_id)
        self.data[guild_id]["messages"][str(msg.id)] = {"channel_id": msg.channel.id, "mappings": {}}
        save_data(self.data)
        await interaction.response.send_message(f"Created roles menu: {msg.id}", ephemeral=True)

    @roles.command(name="add")
    @app_commands.describe(message_id="ID of the menu message", emoji="Emoji to react with", role="Role to assign")
    @app_commands.default_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, message_id: int, emoji: str, role: discord.Role):
        """Add a reaction-role mapping to an existing menu."""
        guild_id = str(interaction.guild_id)
        await self.ensure_guild(guild_id)
        msg_entry = self.data[guild_id]["messages"].get(str(message_id))
        if not msg_entry:
            await interaction.response.send_message("Message ID not found for this server.", ephemeral=True)
            return
        # store mapping
        msg_entry["mappings"][emoji] = role.id
        save_data(self.data)
        # add reaction to the message
        channel = self.bot.get_channel(msg_entry["channel_id"]) or await self.bot.fetch_channel(msg_entry["channel_id"])
        try:
            msg = await channel.fetch_message(message_id)
            await msg.add_reaction(emoji)
        except Exception:
            pass
        await interaction.response.send_message(f"Added mapping {emoji} → {role.name}", ephemeral=True)

    @roles.command(name="remove")
    @app_commands.describe(message_id="ID of the menu message", emoji="Emoji to remove")
    @app_commands.default_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, message_id: int, emoji: str):
        """Remove a mapping from a menu."""
        guild_id = str(interaction.guild_id)
        await self.ensure_guild(guild_id)
        msg_entry = self.data[guild_id]["messages"].get(str(message_id))
        if not msg_entry or emoji not in msg_entry["mappings"]:
            await interaction.response.send_message("Mapping not found.", ephemeral=True)
            return
        role_id = msg_entry["mappings"].pop(emoji)
        save_data(self.data)
        # remove reaction from message
        try:
            channel = self.bot.get_channel(msg_entry["channel_id"]) or await self.bot.fetch_channel(msg_entry["channel_id"])
            msg = await channel.fetch_message(message_id)
            await msg.clear_reaction(emoji)
        except Exception:
            pass
        await interaction.response.send_message(f"Removed mapping {emoji} (role id {role_id}).", ephemeral=True)

    @roles.command(name="list")
    @app_commands.describe(message_id="ID of the menu message")
    @app_commands.default_permissions(manage_guild=True)
    async def _list(self, interaction: discord.Interaction, message_id: int):
        """List mappings for a menu message."""
        guild_id = str(interaction.guild_id)
        await self.ensure_guild(guild_id)
        msg_entry = self.data[guild_id]["messages"].get(str(message_id))
        if not msg_entry:
            await interaction.response.send_message("Message ID not found.", ephemeral=True)
            return
        mappings = msg_entry["mappings"]
        if not mappings:
            await interaction.response.send_message("No mappings set for this message.", ephemeral=True)
            return
        lines = []
        for em, rid in mappings.items():
            role = interaction.guild.get_role(rid)
            lines.append(f"{em} → {role.name if role else rid}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Roles(bot))

