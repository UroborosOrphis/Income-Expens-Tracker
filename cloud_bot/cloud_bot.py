import os
import json
from pathlib import Path
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# ======================
# Environment Setup
# ======================
def load_env():
    """Manually load .env file"""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        raise FileNotFoundError(f".env file not found at {env_file}")

    with open(env_file, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value


# Load environment variables
load_env()
TOKEN = os.getenv("DISCORD_TOKEN")
# NOTE: Set this to 'True' for ONE RUN ONLY to clear old commands. Set back to 'False' after success.
CLEAR_COMMANDS_ON_START = os.getenv("CLEAR_COMMANDS_ON_START", "False").lower() == "true"

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env file")

print(f"Token loaded: {TOKEN[:10]}...")

# ======================
# Bot Setup
# ======================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# File paths
BUFFER_FILE = Path(__file__).parent / "expense_buffer.json"
CATEGORIES_FILE = Path(__file__).parent / "categories.json"
ACCOUNTS_FILE = Path(__file__).parent / "accounts.json"


# Load categories and accounts from JSON
def load_categories():
    """Load categories from JSON file"""
    if CATEGORIES_FILE.exists():
        with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    # Fallback defaults if file doesn't exist
    return [
        {"name": "Food", "emoji": "🍔", "type": "expense"},
        {"name": "Transport", "emoji": "🚗", "type": "expense"},
        {"name": "Bills", "emoji": "📄", "type": "expense"},
        {"name": "Other", "emoji": "📦", "type": "expense"}
    ]


def load_accounts():
    """Load accounts from JSON file"""
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    # Fallback defaults if file doesn't exist
    return [
        {"name": "Cash Wallet", "type": "wallet", "emoji": "💰"},
        {"name": "Credit Card", "type": "credit_card", "emoji": "💳"}
    ]


# Load initial data
CATEGORIES = load_categories()
ACCOUNTS = load_accounts()


# ======================
# Helper Functions
# ======================
def load_buffer():
    """Load expense buffer from JSON, safely handling empty or corrupted files."""
    if BUFFER_FILE.exists():
        # Use try/except to handle JSONDecodeError if the file is empty or malformed
        try:
            with open(BUFFER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # Handle JSON errors and encoding issues (e.g., invalid UTF-8)
            print(f"Warning: Expense buffer file ({BUFFER_FILE.name}) is corrupted or has encoding issues. Resetting buffer to []. Error: {e}")
            return []
    return [] # File doesn't exist, return empty list


def save_buffer(buffer):
    """Save expense buffer to JSON"""
    try:
        with open(BUFFER_FILE, "w", encoding="utf-8") as f:
            json.dump(buffer, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving buffer: {e}")


def add_expense_to_buffer(user, amount, category, account, description=""):
    """Add an expense entry to buffer with IDs from JSON"""
    buffer = load_buffer()
    
    # Get ID from JSON data
    category_id = next((cat["id"] for cat in CATEGORIES if cat["name"] == category), None)
    account_id = next((acc["id"] for acc in ACCOUNTS if acc["name"] == account), None)
    
    if not category_id or not account_id:
        raise ValueError(f"Invalid category or account: {category}, {account}")
    
    entry = {
        "account_id": account_id,
        "category_id": category_id,
        "amount": float(amount),
        "type": "expense",      # Default to expense
        "date": datetime.now().strftime("%Y-%m-%d"),
        "description": description,
        "notes": user,         # Map user to notes field
        "is_recurring": 0      # Default to non-recurring
    }
    buffer.append(entry)
    save_buffer(buffer)
    return entry


# ======================
# UI Components - Buttons
# ======================
class CategoryView(discord.ui.View):
    def __init__(self, amount, user_id):
        super().__init__(timeout=180)
        self.amount = amount
        self.user_id = user_id

        # Load categories dynamically
        categories = load_categories()

        for cat_data in categories:
            name = cat_data["name"]
            emoji = cat_data.get("emoji", "📦")
            button = discord.ui.Button(label=name, emoji=emoji, style=discord.ButtonStyle.primary)
            button.callback = self.make_callback(name)
            self.add_item(button)

    def make_callback(self, category):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your expense!", ephemeral=True)
                return

            view = AccountView(self.amount, category, interaction.user.id)
            await interaction.response.edit_message(
                content=f"Amount: {self.amount}\nCategory: {category}\n\nNow choose an account:",
                view=view
            )

        return callback


class AccountView(discord.ui.View):
    def __init__(self, amount, category, user_id):
        super().__init__(timeout=180)
        self.amount = amount
        self.category = category
        self.user_id = user_id

        # Load accounts dynamically
        accounts = load_accounts()

        for acc_data in accounts:
            name = acc_data["name"]
            emoji = acc_data.get("emoji", "💰")
            button = discord.ui.Button(label=name, emoji=emoji, style=discord.ButtonStyle.success)
            button.callback = self.make_callback(name)
            self.add_item(button)

    def make_callback(self, account):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your expense!", ephemeral=True)
                return

            view = DescriptionView(self.amount, self.category, account, interaction.user.id)
            await interaction.response.edit_message(
                content=f"Amount: {self.amount}\nCategory: {self.category}\nAccount: {account}\n\nAdd a description?",
                view=view
            )

        return callback


class DescriptionModal(discord.ui.Modal, title="Add Description"):
    description = discord.ui.TextInput(
        label="Description (optional)",
        placeholder="e.g., Lunch with colleagues",
        required=False,
        max_length=200
    )

    def __init__(self, amount, category, account, user):
        super().__init__()
        self.amount = amount
        self.category = category
        self.account = account
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        desc = self.description.value or ""

        # 1. Acknowledge and close the modal immediately by deferring the interaction
        await interaction.response.defer()

        # 2. Add expense (critical operation)
        try:
            add_expense_to_buffer(
                user=str(self.user),
                amount=self.amount,
                category=self.category,
                account=self.account,
                description=desc
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error saving expense to buffer: {e}", ephemeral=True)
            return

        # 3. Use interaction.edit_original_response() to update the message associated with the button/command
        await interaction.edit_original_response(
            content=f"Expense logged:\nAmount: {self.amount:.2f}\nCategory: {self.category}\nAccount: {self.account}\nDescription: {desc or 'None'}",
            view=None
        )


class DescriptionView(discord.ui.View):
    def __init__(self, amount, category, account, user_id):
        super().__init__(timeout=180)
        self.amount = amount
        self.category = category
        self.account = account
        self.user_id = user_id

    @discord.ui.button(label="Add Description", style=discord.ButtonStyle.primary)
    async def add_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your expense!", ephemeral=True)
            return
        modal = DescriptionModal(self.amount, self.category, self.account, interaction.user)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Skip Description", style=discord.ButtonStyle.secondary)
    async def skip_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your expense!", ephemeral=True)
            return

        # 1. Correct: Defer the interaction immediately
        # The response object can only be used once. defer() is the standard acknowledgement.
        await interaction.response.defer()

        # 2. Add expense (critical operation)
        try:
            add_expense_to_buffer(
                user=str(interaction.user),
                amount=self.amount,
                category=self.category,
                account=self.account,
                description=""
            )
        except Exception as e:
            # Report failure via followup message
            await interaction.followup.send(f"❌ Error saving expense to buffer: {e}", ephemeral=True)
            return

        # 3. Use interaction.edit_original_response() to update the original message.
        # This is the proper way to edit the message after deferring.
        await interaction.edit_original_response(
            content=f"Expense logged:\nAmount: {self.amount:.2f}\nCategory: {self.category}\nAccount: {self.account}\nDescription: None",
            view=None
        )


# ======================
# Bot Events
# ======================
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    print(f"Connected to {len(bot.guilds)} server(s)")
    try:
        if CLEAR_COMMANDS_ON_START:
            # Clear all commands globally for a clean slate
            bot.tree.clear_commands(guild=None)
            synced = await bot.tree.sync(guild=None)
            print(f"⚠️ CLEARED ALL GLOBAL COMMANDS. Synced 0 command(s).")
            # After clearing, we need to sync them back
            synced = await bot.tree.sync() # Syncs all commands defined below
            print(f"✅ Re-Synced {len(synced)} command(s) globally.")
        else:
            # Standard sync for new commands (should include /reload)
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} slash command(s) globally.")

    except Exception as e:
        print(f"Failed to sync commands: {e}")


# ======================
# Slash Commands
# ======================

@bot.tree.command(name="expense", description="Log an expense with interactive buttons")
@app_commands.describe(amount="Amount spent (e.g., 45.50)")
async def slash_expense(interaction: discord.Interaction, amount: float):
    """Interactive expense logging with buttons"""
    if amount <= 0:
        await interaction.response.send_message("Amount must be positive.", ephemeral=True)
        return

    view = CategoryView(amount, interaction.user.id)
    await interaction.response.send_message(
        f"Amount: {amount}\n\nChoose a category:",
        view=view,
        ephemeral=False
    )


@bot.tree.command(name="showbuffer", description="Show recent expenses in buffer")
async def slash_showbuffer(interaction: discord.Interaction):
    """Show current expense buffer"""
    buffer = load_buffer()

    if not buffer:
        await interaction.response.send_message("Buffer is empty.", ephemeral=True)
        return

    recent = buffer[-10:]
    lines = []
    for i, e in enumerate(recent, 1):
        # Map IDs back to names for display
        category_name = next((cat["name"] for cat in CATEGORIES if cat["id"] == e["category_id"]), "Unknown")
        account_name = next((acc["name"] for acc in ACCOUNTS if acc["id"] == e["account_id"]), "Unknown")
        
        lines.append(
            f"{i}. {e['amount']:.2f} | {category_name} | {account_name} | {e.get('description', '')}"
        )

    await interaction.response.send_message(
        f"Last {len(recent)} expense(s):\n" + "\n".join(lines),
        ephemeral=True
    )


@bot.tree.command(name="reload", description="Reload categories and accounts from files (admin only)")
async def slash_reload(interaction: discord.Interaction):
    """Reload categories and accounts"""
    if interaction.user.guild_permissions.administrator:
        global CATEGORIES, ACCOUNTS
        CATEGORIES = load_categories()
        ACCOUNTS = load_accounts()
        await interaction.response.send_message(
            f"Reloaded {len(CATEGORIES)} categories and {len(ACCOUNTS)} accounts.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("Admin only command.", ephemeral=True)


# ======================
# Legacy Prefix Commands (kept for compatibility)
# ======================

@bot.command()
async def ping(ctx):
    """Test if bot is alive"""
    await ctx.send("Pong! Use /expense for slash commands.")


WEBHOOK_CHANNEL_ID = int(os.getenv("WEBHOOK_CHANNEL_ID", "1424032376589385868"))

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself and other channels
    if message.author == bot.user or message.channel.id != WEBHOOK_CHANNEL_ID:
        # Crucial: Process prefix commands (like !ping) after ignoring the webhook.
        await bot.process_commands(message)
        return

    # Check if the message content looks like your expense format
    content = message.content.strip()
    if '|' in content and not content.startswith(('!', '$')):
        # Attempt to parse the content directly
        try:
            parts = [p.strip() for p in content.split('|')]

            if len(parts) >= 3:
                amount_str, category, account = parts[0], parts[1], parts[2]
                description = parts[3] if len(parts) > 3 else ""

                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError("Amount must be positive.")

                # Use the Webhook name as the user since message.author is the bot itself
                webhook_name = message.author.display_name if message.webhook_id else str(message.author)

                add_expense_to_buffer(
                    user=webhook_name,
                    amount=amount,
                    category=category,
                    account=account,
                    description=description
                )

                await message.add_reaction("✅")  # Send reaction for success

            else:
                await message.add_reaction("⚠️")  # Send reaction for failure (too few fields)

        except Exception:
            # Catch all errors (e.g., non-float amount) and react with an error emoji
            await message.add_reaction("❌")

    # Always process commands (in case a human user messages the channel)
    await bot.process_commands(message)

# ======================
# Run Bot
# ======================
if __name__ == "__main__":
    print("Starting bot...")
    bot.run(TOKEN)