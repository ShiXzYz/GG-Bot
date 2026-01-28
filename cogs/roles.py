import discord
from discord.ext import commands
from config import AUTO_ROLE_ID

class RoleButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
    label="Survival", 
    style=discord.ButtonStyle.green, 
    custom_id="role_survival"  # ✅ required for persistent views
)
    async def survival(self, interaction: discord.Interaction, button: discord.ui.Button):
    	role = discord.utils.get(interaction.guild.roles, name="Survival")
    	if role:
        	await interaction.user.add_roles(role)
        	await interaction.response.send_message(
            		f"✅ You have been given the **{role.name}** role!",
            		ephemeral=True  # only visible to the user
        	)
    	else:
        	await interaction.response.send_message(
            		"⚠️ Role not found on this server.",
            		ephemeral=True
        	)

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(RoleButtons())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = member.guild.get_role(AUTO_ROLE_ID)
        await member.add_roles(role)

async def setup(bot):
    await bot.add_cog(Roles(bot))

