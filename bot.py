import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix="!",  # unused, but required
    intents=intents
)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

async def load_cogs():
    for cog in ["status", "roles", "info"]:
        await bot.load_extension(f"cogs.{cog}")

@bot.event
async def setup_hook():
    await load_cogs()

bot.run(os.getenv("DISCORD_TOKEN"))

