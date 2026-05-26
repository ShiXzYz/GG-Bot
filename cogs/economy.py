import discord
from discord.ext import commands
from discord import app_commands
import random
import time
from PIL import Image, ImageDraw, ImageFont
import io
import os

from database import load_money_data as load_data, save_money_data as save_data

EMBED_COLOR = 0x5865F2
WORK_COOLDOWN_SECONDS = 60 * 60  # 1 hour

WORK_POSITIVE_TEMPLATES = [
    "You {verb} {article}{item} and got paid for it.",
    "A neighbor paid you for {verb} {article}{item}.",
    "You {verb} {article}{item} on short notice and earned a nice tip.",
    "You sold {article}{item} you found and added the money to your wallet.",
    "You helped with {topic} and were rewarded with coins.",
    "You completed {article}{item} and received a small bonus.",
]

WORK_NEGATIVE_TEMPLATES = [
    "Your {item} broke while you were {verb} it, costing you money.",
    "You missed a deadline and had to pay a small fee.",
    "You got stuck in the rain and lost some cash on a canceled job.",
    "Your {item} got damaged while you were {verb} it.",
    "A small mistake during {verb} cost you a few coins.",
    "Your {item} was lost in transit and you covered the refund.",
]

WORK_SUBJECTS = [
    "a bike tire",
    "some groceries",
    "a bouquet",
    "old collectibles",
    "a fresh-baked cake",
    "a stack of textbooks",
    "a new gadget",
    "a painting",
    "a bag of supplies",
    "a guitar",
    "a stack of letters",
    "a delivery package",
]

WORK_VERBS = [
    "fixing",
    "delivering",
    "organizing",
    "building",
    "repairing",
    "cleaning",
    "preparing",
    "painting",
    "writing",
    "taking care of",
    "moving",
    "assembling",
]

WORK_TOPICS = [
    "graphic design",
    "math homework",
    "creative writing",
    "cooking",
    "gardening",
    "a repair job",
    "a pet sitting shift",
    "a quick favor",
    "a tutoring session",
    "a delivery run",
]

WORK_ARTICLES = ["a ", "the ", ""
]

COINFLIP_CHOICES = [
    app_commands.Choice(name="Heads", value="heads"),
    app_commands.Choice(name="Tails", value="tails")
]

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "🔔", "⭐", "💎", "🎰"]


class Economy(commands.Cog):

    money = app_commands.Group(name="money", description="Money economy commands")

    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()
        self.work_cooldowns = {}

    def cog_unload(self):
        save_data(self.data)

    def ensure_guild(self, guild_id: str):
        if guild_id not in self.data:
            self.data[guild_id] = {}

    def get_balance(self, guild_id: str, user_id: str) -> int:
        self.ensure_guild(guild_id)
        return self.data[guild_id].get(user_id, 0)

    def set_balance(self, guild_id: str, user_id: str, amount: int) -> int:
        self.ensure_guild(guild_id)
        self.data[guild_id][user_id] = amount
        save_data(self.data)
        return amount

    def add_balance(self, guild_id: str, user_id: str, amount: int) -> int:
        self.ensure_guild(guild_id)
        current = self.get_balance(guild_id, user_id)
        new_balance = current + amount
        self.data[guild_id][user_id] = new_balance
        save_data(self.data)
        return new_balance

    def format_money(self, amount: int) -> str:
        return f"{amount:,} coins"

    def is_valid_bet(self, amount: int, balance: int) -> bool:
        return amount > 0 and amount <= balance

    def build_embed(self, title: str, description: str) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=EMBED_COLOR)
        return embed

    def get_blackjack_value(self, card: str) -> int:
        value = card[:-2]
        if value in ["J", "Q", "K"]:
            return 10
        if value == "A":
            return 11
        return int(value)

    def score_hand(self, cards: list[str]) -> int:
        total = sum(self.get_blackjack_value(card) for card in cards)
        aces = sum(1 for card in cards if card.startswith("A"))
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def draw_card(self) -> str:
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        suits = ["♠️", "♥️", "♦️", "♣️"]
        return f"{random.choice(values)}{random.choice(suits)}"

    def generate_work_outcome(self) -> tuple[str, int]:
        positive = random.random() < 0.75
        item = random.choice(WORK_SUBJECTS)
        verb = random.choice(WORK_VERBS)
        topic = random.choice(WORK_TOPICS)
        article = random.choice(WORK_ARTICLES)

        if positive:
            template = random.choice(WORK_POSITIVE_TEMPLATES)
            amount = random.randint(25, 60)
        else:
            template = random.choice(WORK_NEGATIVE_TEMPLATES)
            amount = -random.randint(10, 35)

        story = template.format(verb=verb, item=item, topic=topic, article=article)
        return story, amount

    def generate_card_image(self, cards: list[str], title: str = "Hand") -> discord.File:
        """Generate a visual card image for a hand of cards."""
        card_width, card_height = 80, 120
        padding = 10
        width = len(cards) * card_width + (len(cards) + 1) * padding
        height = card_height + padding * 2
        
        img = Image.new("RGB", (width, height), color=(34, 139, 34))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        x = padding
        for card in cards:
            value = card[:-2]
            suit = card[-2:]
            
            suit_color = (255, 0, 0) if suit in ["♥️", "♦️"] else (0, 0, 0)
            draw.rectangle([x, padding, x + card_width, padding + card_height], outline="white", width=2)
            draw.text((x + 10, padding + 10), value, fill=suit_color, font=font)
            draw.text((x + 50, padding + 90), suit, fill=suit_color, font=font)
            x += card_width + padding
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="cards.png")

    def generate_slots_image(self, reel: list[str]) -> discord.File:
        """Generate a visual slot machine image."""
        slot_size = 120
        padding = 20
        width = slot_size * 3 + padding * 4
        height = slot_size + padding * 2
        
        img = Image.new("RGB", (width, height), color=(50, 50, 50))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        x = padding
        for symbol in reel:
            draw.rectangle([x, padding, x + slot_size, padding + slot_size], outline="gold", width=3, fill=(100, 100, 100))
            draw.text((x + 20, padding + 15), symbol, font=font)
            x += slot_size + padding
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="slots.png")

    # ===============================
    # Shared commands
    # ===============================

    @money.command(name="balance", description="Check your money or another member's money")
    @app_commands.describe(user="The member to check")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        guild_id = str(interaction.guild.id)
        user_id = str(user.id)
        balance = self.get_balance(guild_id, user_id)

        embed = self.build_embed(
            f"{user.display_name}'s Wallet",
            f"Current balance: **{self.format_money(balance)}**"
        )
        await interaction.response.send_message(embed=embed)

    @money.command(name="leaderboard", description="See who has the most money")
    async def leaderboard(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)

        leaderboard = sorted(
            self.data[guild_id].items(),
            key=lambda item: item[1],
            reverse=True
        )[:10]

        if not leaderboard:
            await interaction.response.send_message("No money data exists yet.")
            return

        description = "\n".join(
            f"**{i + 1}.** <@{user_id}> — {self.format_money(balance)}"
            for i, (user_id, balance) in enumerate(leaderboard)
        )

        embed = self.build_embed("💰 Money Leaderboard", description)
        await interaction.response.send_message(embed=embed)

    @money.command(name="transfer", description="Send coins to another member")
    @app_commands.describe(user="The member to send coins to", amount="Amount to transfer")
    async def transfer(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        guild_id = str(interaction.guild.id)
        sender_id = str(interaction.user.id)
        recipient_id = str(user.id)

        if recipient_id == sender_id:
            await interaction.response.send_message("You can't transfer coins to yourself.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("Transfer amount must be greater than zero.", ephemeral=True)
            return

        sender_balance = self.get_balance(guild_id, sender_id)
        if amount > sender_balance:
            await interaction.response.send_message("You don't have enough coins for that transfer.", ephemeral=True)
            return

        self.add_balance(guild_id, sender_id, -amount)
        self.add_balance(guild_id, recipient_id, amount)

        embed = self.build_embed(
            "💸 Transfer Successful",
            f"You sent {self.format_money(amount)} to {user.display_name}.\n"
            f"Your new balance is **{self.format_money(self.get_balance(guild_id, sender_id))}**."
        )
        await interaction.response.send_message(embed=embed)

    # ===============================
    # Work command
    # ===============================

    @app_commands.command(name="work", description="Work for a short story and earn or lose coins")
    async def work(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        now = time.time()
        cooldown_key = f"{guild_id}:{user_id}"
        last_used = self.work_cooldowns.get(cooldown_key, 0)

        if now - last_used < WORK_COOLDOWN_SECONDS:
            remaining = WORK_COOLDOWN_SECONDS - (now - last_used)
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            await interaction.response.send_message(
                f"You need to rest before working again. Try again in {minutes}m {seconds}s.",
                ephemeral=True
            )
            return

        story, amount = self.generate_work_outcome()
        updated_balance = self.add_balance(guild_id, user_id, amount)

        self.work_cooldowns[cooldown_key] = now

        result_text = (
            f"You earned {self.format_money(amount)}!"
            if amount >= 0
            else f"You lost {self.format_money(abs(amount))} during work."
        )

        embed = self.build_embed(
            "🛠️ Work Report",
            f"{story}\n\n{result_text}\nNew balance: **{self.format_money(updated_balance)}**"
        )

        await interaction.response.send_message(embed=embed)

    # ===============================
    # Coinflip
    # ===============================

    @money.command(name="coinflip", description="Flip a coin for a chance to double your bet")
    @app_commands.describe(amount="Amount to wager", guess="Heads or tails")
    @app_commands.choices(guess=COINFLIP_CHOICES)
    async def coinflip(
        self,
        interaction: discord.Interaction,
        amount: int,
        guess: app_commands.Choice[str]
    ):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        balance = self.get_balance(guild_id, user_id)

        if amount <= 0:
            await interaction.response.send_message("Bet amount must be greater than zero.", ephemeral=True)
            return

        if amount > balance:
            await interaction.response.send_message("You don't have enough coins to cover that bet.", ephemeral=True)
            return

        result = random.choice(["heads", "tails"])
        if guess.value == result:
            updated = self.add_balance(guild_id, user_id, amount)
            embed = self.build_embed(
                "🪙 Coinflip Win!",
                f"It landed on **{result.title()}**. You won {self.format_money(amount)}!\nNew balance: **{self.format_money(updated)}**"
            )
        else:
            updated = self.add_balance(guild_id, user_id, -amount)
            embed = self.build_embed(
                "🪙 Coinflip Loss",
                f"It landed on **{result.title()}**. You lost {self.format_money(amount)}.\nNew balance: **{self.format_money(updated)}**"
            )

        await interaction.response.send_message(embed=embed)

    # ===============================
    # Slots
    # ===============================

    @money.command(name="slots", description="Play the slot machine")
    @app_commands.describe(amount="Amount to wager")
    async def slots(self, interaction: discord.Interaction, amount: int):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        balance = self.get_balance(guild_id, user_id)

        if amount <= 0:
            await interaction.response.send_message("Bet amount must be greater than zero.", ephemeral=True)
            return

        if amount > balance:
            await interaction.response.send_message("You don't have enough coins to cover that bet.", ephemeral=True)
            return

        reel = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        result_text = ""
        payout = 0

        if len(set(reel)) == 1:
            payout = amount * 5
            result_text = f"Jackpot!"
        elif len(set(reel)) == 2:
            payout = amount * 2
            result_text = f"Nice hit!"
        else:
            payout = -amount
            result_text = f"No match."

        updated = self.add_balance(guild_id, user_id, payout)

        # Generate slot machine image
        slots_file = self.generate_slots_image(reel)

        if payout > 0:
            description = f"{result_text}\nYou won {self.format_money(payout)}!\nNew balance: **{self.format_money(updated)}**"
            title = "🎰 Slots Win"
        else:
            description = f"{result_text}\nYou lost {self.format_money(abs(payout))}.\nNew balance: **{self.format_money(updated)}**"
            title = "🎰 Slots Loss"

        embed = self.build_embed(title, description)
        embed.set_image(url="attachment://slots.png")
        
        await interaction.response.send_message(embed=embed, file=slots_file)

    # ===============================
    # Blackjack
    # ===============================

    @money.command(name="blackjack", description="Play a round of blackjack")
    @app_commands.describe(amount="Amount to wager")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        balance = self.get_balance(guild_id, user_id)

        if amount <= 0:
            await interaction.response.send_message("Bet amount must be greater than zero.", ephemeral=True)
            return

        if amount > balance:
            await interaction.response.send_message("You don't have enough coins to cover that bet.", ephemeral=True)
            return

        player_cards = [self.draw_card(), self.draw_card()]
        dealer_cards = [self.draw_card(), self.draw_card()]

        player_total = self.score_hand(player_cards)
        dealer_total = self.score_hand(dealer_cards)

        while dealer_total < 17:
            dealer_cards.append(self.draw_card())
            dealer_total = self.score_hand(dealer_cards)

        # Generate card images
        player_file = self.generate_card_image(player_cards, "Your Hand")
        dealer_file = self.generate_card_image(dealer_cards, "Dealer Hand")

        if player_total > 21:
            updated = self.add_balance(guild_id, user_id, -amount)
            description = (
                f"Your total: **{player_total}**\n"
                f"Dealer total: **{dealer_total}**\n"
                f"You busted and lost {self.format_money(amount)}.\nNew balance: **{self.format_money(updated)}**"
            )
            title = "🃏 Blackjack Bust"
        elif dealer_total > 21 or player_total > dealer_total:
            winnings = amount * 2
            updated = self.add_balance(guild_id, user_id, winnings)
            description = (
                f"Your total: **{player_total}**\n"
                f"Dealer total: **{dealer_total}**\n"
                f"You won {self.format_money(winnings)}!\nNew balance: **{self.format_money(updated)}**"
            )
            title = "🃏 Blackjack Win"
        elif player_total == dealer_total:
            description = (
                f"Your total: **{player_total}**\n"
                f"Dealer total: **{dealer_total}**\n"
                f"Push! Your bet was returned.\nBalance: **{self.format_money(balance)}**"
            )
            title = "🃏 Blackjack Push"
        else:
            updated = self.add_balance(guild_id, user_id, -amount)
            description = (
                f"Your total: **{player_total}**\n"
                f"Dealer total: **{dealer_total}**\n"
                f"You lost {self.format_money(amount)}.\nNew balance: **{self.format_money(updated)}**"
            )
            title = "🃏 Blackjack Loss"

        embed = self.build_embed(title, description)
        embed.set_image(url="attachment://cards.png")
        
        await interaction.response.send_message(embed=embed, files=[player_file, dealer_file])

    # ===============================
    # Lottery
    # ===============================

    @money.command(name="lottery", description="Buy a lottery ticket for a chance to win big")
    @app_commands.describe(tickets="Number of tickets to buy (1-5)")
    async def lottery(self, interaction: discord.Interaction, tickets: int = 1):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)
        balance = self.get_balance(guild_id, user_id)

        tickets = max(1, min(5, tickets))
        cost = 50 * tickets

        if cost > balance:
            await interaction.response.send_message("You don't have enough coins to buy that many tickets.", ephemeral=True)
            return

        chance = 0.1 * tickets
        won = random.random() < chance
        if won:
            reward = cost * random.randint(4, 8)
            updated = self.add_balance(guild_id, user_id, reward)
            description = (
                f"You bought {tickets} ticket(s) for {self.format_money(cost)}.\n"
                f"Lucky win! You received {self.format_money(reward)}.\n"
                f"New balance: **{self.format_money(updated)}**"
            )
            title = "🎟️ Lottery Win"
        else:
            updated = self.add_balance(guild_id, user_id, -cost)
            description = (
                f"You bought {tickets} ticket(s) for {self.format_money(cost)}.\n"
                f"No luck this time.\nNew balance: **{self.format_money(updated)}**"
            )
            title = "🎟️ Lottery Loss"

        await interaction.response.send_message(embed=self.build_embed(title, description))


async def setup(bot):
    await bot.add_cog(Economy(bot))
