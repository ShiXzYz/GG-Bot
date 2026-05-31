import math
import discord
from discord.ext import commands
from discord import app_commands
import random
import time
from PIL import Image, ImageDraw, ImageFont
import io
import os

from database import load_money_data as load_data, save_money_data as save_data

EMBED_COLOR   = 0x5865F2
WIN_COLOR     = 0x2ECC71
LOSS_COLOR    = 0xE74C3C
PUSH_COLOR    = 0xF39C12
JACKPOT_COLOR = 0xF1C40F

WORK_COOLDOWN_SECONDS = 60

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
    "a bike tire", "some groceries", "a bouquet", "old collectibles",
    "a fresh-baked cake", "a stack of textbooks", "a new gadget",
    "a painting", "a bag of supplies", "a guitar",
    "a stack of letters", "a delivery package",
]
WORK_VERBS = [
    "fixing", "delivering", "organizing", "building", "repairing",
    "cleaning", "preparing", "painting", "writing",
    "taking care of", "moving", "assembling",
]
WORK_TOPICS = [
    "graphic design", "math homework", "creative writing", "cooking",
    "gardening", "a repair job", "a pet sitting shift", "a quick favor",
    "a tutoring session", "a delivery run",
]
WORK_ARTICLES = ["a ", "the ", ""]

COINFLIP_CHOICES = [
    app_commands.Choice(name="Heads", value="heads"),
    app_commands.Choice(name="Tails", value="tails"),
]

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "🔔", "⭐", "💎", "🎰"]
LEADERBOARD_MEDALS = ["🥇", "🥈", "🥉"]


# ─────────────────────────────────────────────────────────────────────────────
# Interactive Blackjack View
# ─────────────────────────────────────────────────────────────────────────────

class BlackjackView(discord.ui.View):

    def __init__(self, cog: "Economy", guild_id: str, user_id: str,
                 player_cards: list, dealer_cards: list, bet: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id
        self.player_cards = list(player_cards)
        self.dealer_cards = list(dealer_cards)
        self.bet = bet
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This isn't your game.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    # ── embed builders ────────────────────────────────────────────────────────

    def _active_embed(self) -> tuple[discord.Embed, discord.File]:
        pt = self.cog.score_hand(self.player_cards)
        embed = discord.Embed(title="🃏 Blackjack", color=EMBED_COLOR)
        embed.add_field(
            name="🎩 Dealer",
            value=f"{self.dealer_cards[0]}  🂠  *(one card hidden)*",
            inline=False,
        )
        embed.add_field(
            name="🖐 Your Hand",
            value=f"{'  '.join(self.player_cards)}\n**Score: {pt}**",
            inline=False,
        )
        embed.add_field(name="Bet", value=self.cog.format_money(self.bet), inline=True)
        f = self.cog.generate_blackjack_image(
            self.player_cards, [self.dealer_cards[0]], show_back=True
        )
        embed.set_image(url="attachment://blackjack.png")
        return embed, f

    def _result_embed(self, outcome: str, payout: int, new_bal: int) -> tuple[discord.Embed, discord.File]:
        pt = self.cog.score_hand(self.player_cards)
        dt = self.cog.score_hand(self.dealer_cards)

        TITLES = {
            "blackjack": "🃏 Blackjack — Natural Blackjack! 🎉",
            "win":       "🃏 Blackjack — You Win!",
            "push":      "🃏 Blackjack — Push",
            "loss":      "🃏 Blackjack — You Lose",
            "bust":      "🃏 Blackjack — Bust!",
        }
        COLORS = {
            "blackjack": JACKPOT_COLOR,
            "win":       WIN_COLOR,
            "push":      PUSH_COLOR,
            "loss":      LOSS_COLOR,
            "bust":      LOSS_COLOR,
        }

        embed = discord.Embed(
            title=TITLES.get(outcome, "🃏 Blackjack"),
            color=COLORS.get(outcome, EMBED_COLOR),
        )
        dealer_bust = "  💥" if dt > 21 else ""
        player_bust = "  💥" if pt > 21 else ""
        embed.add_field(
            name="🎩 Dealer",
            value=f"{'  '.join(self.dealer_cards)}\n**Score: {dt}**{dealer_bust}",
            inline=False,
        )
        embed.add_field(
            name="🖐 Your Hand",
            value=f"{'  '.join(self.player_cards)}\n**Score: {pt}**{player_bust}",
            inline=False,
        )
        if payout > 0:
            embed.add_field(name="Won",    value=f"+{self.cog.format_money(payout)}", inline=True)
        elif payout < 0:
            embed.add_field(name="Lost",   value=f"−{self.cog.format_money(abs(payout))}", inline=True)
        else:
            embed.add_field(name="Result", value="Bet returned",                      inline=True)
        embed.add_field(name="Balance", value=f"**{self.cog.format_money(new_bal)}**", inline=True)

        f = self.cog.generate_blackjack_image(self.player_cards, self.dealer_cards)
        embed.set_image(url="attachment://blackjack.png")
        return embed, f

    # ── game logic ────────────────────────────────────────────────────────────

    async def _finish(self, interaction: discord.Interaction):
        pt = self.cog.score_hand(self.player_cards)

        if pt <= 21:
            while self.cog.score_hand(self.dealer_cards) < 17:
                self.dealer_cards.append(self.cog.draw_card())

        dt = self.cog.score_hand(self.dealer_cards)

        if pt > 21:
            outcome, payout = "bust",      -self.bet
        elif dt > 21 or pt > dt:
            if pt == 21 and len(self.player_cards) == 2:
                outcome, payout = "blackjack", int(self.bet * 1.5)
            else:
                outcome, payout = "win",       self.bet
        elif pt == dt:
            outcome, payout = "push",      0
        else:
            outcome, payout = "loss",      -self.bet

        new_bal = self.cog.add_balance(self.guild_id, self.user_id, payout)

        for item in self.children:
            item.disabled = True
        self.stop()

        embed, f = self._result_embed(outcome, payout, new_bal)
        await interaction.response.edit_message(embed=embed, attachments=[f], view=self)

    # ── buttons ───────────────────────────────────────────────────────────────

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="🃏", row=0)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player_cards.append(self.cog.draw_card())
        # disable double-down after first action
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label == "Double Down":
                item.disabled = True

        if self.cog.score_hand(self.player_cards) >= 21:
            await self._finish(interaction)
        else:
            embed, f = self._active_embed()
            await interaction.response.edit_message(embed=embed, attachments=[f], view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋", row=0)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finish(interaction)

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.success, emoji="💰", row=0)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        balance = self.cog.get_balance(self.guild_id, self.user_id)
        if balance < self.bet * 2:
            await interaction.response.send_message(
                f"You need **{self.cog.format_money(self.bet * 2)}** to double down.", ephemeral=True
            )
            return
        self.bet *= 2
        self.player_cards.append(self.cog.draw_card())
        await self._finish(interaction)


# ─────────────────────────────────────────────────────────────────────────────
# Economy Cog
# ─────────────────────────────────────────────────────────────────────────────

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
        new_bal = current + amount
        self.data[guild_id][user_id] = new_bal
        save_data(self.data)
        return new_bal

    def format_money(self, amount: int) -> str:
        return f"{amount:,} coins"

    def build_embed(self, title: str, description: str = "", color: int = EMBED_COLOR) -> discord.Embed:
        return discord.Embed(title=title, description=description, color=color)

    # ── card logic ────────────────────────────────────────────────────────────

    def draw_card(self) -> str:
        values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        suits  = ["♠️", "♥️", "♦️", "♣️"]
        return f"{random.choice(values)}{random.choice(suits)}"

    def get_blackjack_value(self, card: str) -> int:
        value = card[:-2]
        if value in ("J", "Q", "K"):
            return 10
        if value == "A":
            return 11
        return int(value)

    def score_hand(self, cards: list) -> int:
        total = sum(self.get_blackjack_value(c) for c in cards)
        aces  = sum(1 for c in cards if c.startswith("A"))
        while total > 21 and aces:
            total -= 10
            aces  -= 1
        return total

    def generate_work_outcome(self) -> tuple:
        positive = random.random() < 0.75
        item     = random.choice(WORK_SUBJECTS)
        verb     = random.choice(WORK_VERBS)
        topic    = random.choice(WORK_TOPICS)
        article  = random.choice(WORK_ARTICLES)
        if positive:
            template = random.choice(WORK_POSITIVE_TEMPLATES)
            amount   = random.randint(25, 60)
        else:
            template = random.choice(WORK_NEGATIVE_TEMPLATES)
            amount   = -random.randint(10, 35)
        return template.format(verb=verb, item=item, topic=topic, article=article), amount

    # ── PIL helpers ───────────────────────────────────────────────────────────

    def _load_font(self, size: int):
        candidates = [
            os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "fonts", "Roboto-Regular.ttf")),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _tsz(self, draw, text: str, font) -> tuple:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]

    def _parse_card(self, card: str) -> tuple:
        clean = card.replace("️", "")   # strip variation selector
        suit  = clean[-1]
        value = clean[:-1]
        color = (200, 30, 30) if suit in ("♥", "♦") else (20, 20, 20)
        return value, suit, color

    def _draw_card_face(self, draw, x, y, w, h, value, suit, color, fnt_sm, fnt_lg):
        draw.rectangle([x + 5, y + 5, x + w + 5, y + h + 5], fill=(10, 70, 30))
        draw.rectangle([x, y, x + w, y + h], fill=(255, 255, 255), outline=(195, 195, 195), width=2)

        draw.text((x + 7, y + 5), value, fill=color, font=fnt_sm)
        _, vh = self._tsz(draw, value, fnt_sm)
        draw.text((x + 7, y + 5 + vh + 2), suit, fill=color, font=fnt_sm)

        sw, sh = self._tsz(draw, suit, fnt_lg)
        draw.text((x + w // 2 - sw // 2, y + h // 2 - sh // 2), suit, fill=color, font=fnt_lg)

        vw, _ = self._tsz(draw, value, fnt_sm)
        draw.text((x + w - 7 - vw, y + h - 5 - vh - 2),            suit,  fill=color, font=fnt_sm)
        draw.text((x + w - 7 - vw, y + h - 5 - vh - 2 - vh - 2),   value, fill=color, font=fnt_sm)

    def _draw_card_back(self, draw, x, y, w, h):
        draw.rectangle([x + 5, y + 5, x + w + 5, y + h + 5], fill=(10, 70, 30))
        draw.rectangle([x, y, x + w, y + h], fill=(25, 50, 160), outline=(60, 100, 210), width=2)
        step = 10
        for i in range(0, w + h, step):
            x1 = x + max(0, i - h);  y1 = y + min(h, i)
            x2 = x + min(w, i);      y2 = y + max(0, i - w)
            draw.line([x1, y1, x2, y2], fill=(35, 65, 175), width=1)
        draw.rectangle([x + 8, y + 8, x + w - 8, y + h - 8], outline=(80, 120, 220), width=1)

    def generate_blackjack_image(self, player_cards: list, dealer_cards: list, show_back: bool = False) -> discord.File:
        CW, CH   = 90, 130
        GAP      = 14
        PAD      = 24
        LABEL_H  = 30
        ROW_GAP  = 20

        max_dealer = len(dealer_cards) + (1 if show_back else 0)
        max_cols   = max(len(player_cards), max_dealer)

        img_w = PAD * 2 + max_cols * (CW + GAP) - GAP
        img_h = PAD + LABEL_H + CH + ROW_GAP + LABEL_H + CH + PAD

        img  = Image.new("RGB", (img_w, img_h), color=(21, 95, 47))
        draw = ImageDraw.Draw(img)

        fnt_lbl = self._load_font(19)
        fnt_sm  = self._load_font(20)
        fnt_lg  = self._load_font(38)

        def draw_row(cards, sy, label, add_back=False):
            draw.text((PAD, sy), label, fill=(225, 220, 160), font=fnt_lbl)
            for i, card in enumerate(cards):
                v, s, c = self._parse_card(card)
                self._draw_card_face(draw, PAD + i * (CW + GAP), sy + LABEL_H, CW, CH, v, s, c, fnt_sm, fnt_lg)
            if add_back:
                bx = PAD + len(cards) * (CW + GAP)
                self._draw_card_back(draw, bx, sy + LABEL_H, CW, CH)

        draw_row(dealer_cards, PAD,                              "  DEALER", add_back=show_back)
        draw_row(player_cards, PAD + LABEL_H + CH + ROW_GAP,   "  YOU")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="blackjack.png")

    def generate_coin_image(self, result: str) -> discord.File:
        W, H = 200, 200
        img  = Image.new("RGB", (W, H), color=(38, 38, 44))
        draw = ImageDraw.Draw(img)
        cx, cy, r = 100, 100, 72

        if result == "heads":
            fill, outline, edge = (212, 162, 30), (255, 210, 60), (140, 100, 15)
            letter, text_c = "H", (60, 40, 5)
        else:
            fill, outline, edge = (158, 158, 168), (205, 205, 215), (100, 100, 108)
            letter, text_c = "T", (70, 70, 80)

        draw.ellipse([cx - r + 3, cy - r + 6, cx + r + 3, cy + r + 6], fill=edge)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=4)
        draw.arc([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], start=210, end=330, fill=outline, width=7)

        fnt = self._load_font(72)
        tw, th = self._tsz(draw, letter, fnt)
        draw.text((cx - tw // 2, cy - th // 2), letter, fill=text_c, font=fnt)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="coin.png")

    # ── commands ──────────────────────────────────────────────────────────────

    @money.command(name="balance", description="Check your coins or another member's")
    @app_commands.describe(user="The member to check")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        bal  = self.get_balance(str(interaction.guild.id), str(user.id))
        embed = self.build_embed("💰 Wallet", color=EMBED_COLOR)
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.add_field(name="Balance", value=f"**{self.format_money(bal)}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @money.command(name="leaderboard", description="See who has the most coins")
    async def leaderboard(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        self.ensure_guild(guild_id)
        top = sorted(self.data[guild_id].items(), key=lambda x: x[1], reverse=True)[:10]
        if not top:
            await interaction.response.send_message("No coin data yet.", ephemeral=True)
            return
        lines = []
        for i, (uid, bal) in enumerate(top):
            medal = LEADERBOARD_MEDALS[i] if i < 3 else f"**{i + 1}.**"
            lines.append(f"{medal} <@{uid}> — {self.format_money(bal)}")
        embed = self.build_embed("💰 Coin Leaderboard", "\n".join(lines), color=JACKPOT_COLOR)
        await interaction.response.send_message(embed=embed)

    @money.command(name="transfer", description="Send coins to another member")
    @app_commands.describe(user="Recipient", amount="Amount to send")
    async def transfer(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        guild_id  = str(interaction.guild.id)
        sender_id = str(interaction.user.id)
        recip_id  = str(user.id)
        if recip_id == sender_id:
            await interaction.response.send_message("You can't send coins to yourself.", ephemeral=True)
            return
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than zero.", ephemeral=True)
            return
        if amount > self.get_balance(guild_id, sender_id):
            await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
            return
        self.add_balance(guild_id, sender_id, -amount)
        self.add_balance(guild_id, recip_id,  amount)
        embed = self.build_embed("💸 Transfer Complete", color=WIN_COLOR)
        embed.add_field(name="Sent to",  value=user.display_name,           inline=True)
        embed.add_field(name="Amount",   value=self.format_money(amount),    inline=True)
        embed.add_field(name="Balance",  value=f"**{self.format_money(self.get_balance(guild_id, sender_id))}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Work to earn (or lose) coins")
    async def work(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        user_id  = str(interaction.user.id)
        now      = time.time()
        key      = f"{guild_id}:{user_id}"
        last     = self.work_cooldowns.get(key, 0)
        if now - last < WORK_COOLDOWN_SECONDS:
            rem = WORK_COOLDOWN_SECONDS - (now - last)
            await interaction.response.send_message(
                f"Rest up — try again in **{int(rem//60)}m {int(rem%60)}s**.", ephemeral=True
            )
            return
        story, amount = self.generate_work_outcome()
        updated = self.add_balance(guild_id, user_id, amount)
        self.work_cooldowns[key] = now
        if amount >= 0:
            embed = self.build_embed("🛠️ Work Report", story, color=WIN_COLOR)
            embed.add_field(name="Earned",  value=f"+{self.format_money(amount)}", inline=True)
        else:
            embed = self.build_embed("🛠️ Work Report", story, color=LOSS_COLOR)
            embed.add_field(name="Lost",    value=f"−{self.format_money(abs(amount))}", inline=True)
        embed.add_field(name="Balance", value=f"**{self.format_money(updated)}**", inline=True)
        await interaction.response.send_message(embed=embed)

    @money.command(name="coinflip", description="Flip a coin — double or nothing")
    @app_commands.describe(amount="Amount to wager", guess="Heads or tails")
    @app_commands.choices(guess=COINFLIP_CHOICES)
    async def coinflip(self, interaction: discord.Interaction, amount: int, guess: app_commands.Choice[str]):
        guild_id = str(interaction.guild.id)
        user_id  = str(interaction.user.id)
        balance  = self.get_balance(guild_id, user_id)
        if amount <= 0:
            await interaction.response.send_message("Bet must be greater than zero.", ephemeral=True)
            return
        if amount > balance:
            await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
            return
        result    = random.choice(["heads", "tails"])
        coin_file = self.generate_coin_image(result)
        won = guess.value == result
        if won:
            updated = self.add_balance(guild_id, user_id, amount)
            embed = self.build_embed("🪙 Coinflip — Win!", color=WIN_COLOR)
            embed.add_field(name="Result",   value=f"**{result.title()}** ✅", inline=True)
            embed.add_field(name="Winnings", value=f"+{self.format_money(amount)}", inline=True)
        else:
            updated = self.add_balance(guild_id, user_id, -amount)
            embed = self.build_embed("🪙 Coinflip — Loss", color=LOSS_COLOR)
            embed.add_field(name="Result", value=f"**{result.title()}** ❌", inline=True)
            embed.add_field(name="Lost",   value=f"−{self.format_money(amount)}", inline=True)
        embed.add_field(name="Your Guess", value=guess.name,                           inline=True)
        embed.add_field(name="Balance",    value=f"**{self.format_money(updated)}**",  inline=True)
        embed.set_image(url="attachment://coin.png")
        await interaction.response.send_message(embed=embed, file=coin_file)

    @money.command(name="slots", description="Spin the slot machine")
    @app_commands.describe(amount="Amount to wager")
    async def slots(self, interaction: discord.Interaction, amount: int):
        guild_id = str(interaction.guild.id)
        user_id  = str(interaction.user.id)
        balance  = self.get_balance(guild_id, user_id)
        if amount <= 0:
            await interaction.response.send_message("Bet must be greater than zero.", ephemeral=True)
            return
        if amount > balance:
            await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
            return

        reel   = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        unique = len(set(reel))

        if unique == 1:
            payout       = amount * 5
            result_label = "🎉 **JACKPOT!** — Three of a kind!"
            color        = JACKPOT_COLOR
            title        = "🎰 Slots — Jackpot!"
        elif unique == 2:
            payout       = amount * 2
            result_label = "✨ **Nice!** — Two of a kind"
            color        = WIN_COLOR
            title        = "🎰 Slots — Win!"
        else:
            payout       = -amount
            result_label = "No match"
            color        = LOSS_COLOR
            title        = "🎰 Slots — Miss"

        updated = self.add_balance(guild_id, user_id, payout)

        # Slot display uses Discord's own emoji rendering — no PIL needed
        reel_display = f"> {reel[0]}  **|**  {reel[1]}  **|**  {reel[2]}"

        embed = self.build_embed(title, reel_display, color=color)
        embed.add_field(name="Result",  value=result_label, inline=False)
        if payout > 0:
            embed.add_field(name="Winnings", value=f"+{self.format_money(payout)}", inline=True)
        else:
            embed.add_field(name="Lost",     value=f"−{self.format_money(abs(payout))}", inline=True)
        embed.add_field(name="Balance", value=f"**{self.format_money(updated)}**", inline=True)
        await interaction.response.send_message(embed=embed)

    @money.command(name="blackjack", description="Play an interactive round of blackjack")
    @app_commands.describe(amount="Amount to wager")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
        guild_id = str(interaction.guild.id)
        user_id  = str(interaction.user.id)
        balance  = self.get_balance(guild_id, user_id)
        if amount <= 0:
            await interaction.response.send_message("Bet must be greater than zero.", ephemeral=True)
            return
        if amount > balance:
            await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
            return

        player_cards = [self.draw_card(), self.draw_card()]
        dealer_cards = [self.draw_card(), self.draw_card()]

        view = BlackjackView(self, guild_id, user_id, player_cards, dealer_cards, amount)

        # Check immediate natural blackjack
        if self.score_hand(player_cards) == 21:
            # Auto-finish — dealer draws out
            while self.score_hand(dealer_cards) < 17:
                dealer_cards.append(self.draw_card())
            view.player_cards = player_cards
            view.dealer_cards = dealer_cards
            dt = self.score_hand(dealer_cards)
            if dt == 21 and len(dealer_cards) == 2:
                payout, outcome = 0, "push"
            else:
                payout, outcome = int(amount * 1.5), "blackjack"
            new_bal = self.add_balance(guild_id, user_id, payout)
            for item in view.children:
                item.disabled = True
            embed, f = view._result_embed(outcome, payout, new_bal)
            await interaction.response.send_message(embed=embed, file=f)
            return

        embed, f = view._active_embed()
        await interaction.response.send_message(embed=embed, file=f, view=view)
        view.message = await interaction.original_response()

    @money.command(name="lottery", description="Buy lottery tickets for a chance to win big")
    @app_commands.describe(tickets="Number of tickets (1–5)")
    async def lottery(self, interaction: discord.Interaction, tickets: int = 1):
        guild_id = str(interaction.guild.id)
        user_id  = str(interaction.user.id)
        balance  = self.get_balance(guild_id, user_id)
        tickets  = max(1, min(5, tickets))
        cost     = 50 * tickets
        if cost > balance:
            await interaction.response.send_message("Not enough coins for that many tickets.", ephemeral=True)
            return
        won = random.random() < 0.1 * tickets
        if won:
            reward  = cost * random.randint(4, 8)
            updated = self.add_balance(guild_id, user_id, reward)
            embed   = self.build_embed("🎟️ Lottery — Winner!", color=JACKPOT_COLOR)
            embed.add_field(name="Tickets", value=str(tickets),                      inline=True)
            embed.add_field(name="Cost",    value=self.format_money(cost),           inline=True)
            embed.add_field(name="Prize",   value=f"🎉 +{self.format_money(reward)}", inline=False)
        else:
            updated = self.add_balance(guild_id, user_id, -cost)
            embed   = self.build_embed("🎟️ Lottery — No Luck", color=LOSS_COLOR)
            embed.add_field(name="Tickets", value=str(tickets),             inline=True)
            embed.add_field(name="Cost",    value=self.format_money(cost),  inline=True)
            embed.add_field(name="Result",  value="Better luck next time",  inline=False)
        embed.add_field(name="Balance", value=f"**{self.format_money(updated)}**", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))
