import asyncio
import os
import random
import discord

from dotenv import load_dotenv
from discord.ext import commands


# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
API_KEY = os.getenv("API_KEY")

# Define intents for the bot
intents = discord.Intents.default()
intents.typing = True
intents.presences = True
intents.messages = True
intents.members = True
intents.message_content = True

# Create a bot instance with the defined intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to track ongoing games per user
active_games = {}


@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")


@bot.command(name="rps", help="Play rock, paper, scissors with the bot using '!rps'")
async def rps(ctx):
    # Define choices and corresponding emojis
    rps_game = ["rock", "paper", "scissors"]
    abbreviations = {"r": "rock", "p": "paper", "s": "scissors"}
    emoji_map = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

    # Check if the user is already in an active game
    if ctx.author.id in active_games:
        await ctx.send("You are already in an ongoing game! Finish it first.")
        return

    await ctx.send("Rock 🪨, Paper 📄, or Scissors ✂️ (You can also use 'r', 'p', or 's')")

    # Check function to ensure the response is valid
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.lower() in rps_game + list(abbreviations.keys())

    # Register the game state for the user
    active_games[ctx.author.id] = True

    # Wait for the user's response
    try:
        user_msg = await bot.wait_for("message", check=check, timeout=30)  # Wait for 30 seconds for a response
    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to respond! Please try again.")
        active_games.pop(ctx.author.id)  # Remove the user from active games
        return

    # Normalize user input to full names
    user_choice_input = user_msg.content.lower()
    user_choice = abbreviations.get(user_choice_input, user_choice_input)

    bot_choice = random.choice(rps_game)

    # Define comments for different outcomes with emojis
    tie_comments = [
        "Well, that was awkward... We tied! 🤔",
        "Great minds think alike... Or maybe we're both just lucky? 😅",
        "A tie! Guess we're evenly matched! 😎",
        "It's a stalemate! Let's go again! 🌀",
        "We tied! Did we just become best friends? 😆"
    ]

    user_win_comments = [
        "No way! You actually beat me! 😱",
        "Lucky shot, human... Don't get used to it! 😤",
        "Alright, alright... You win this round! 😒",
        "You got me this time! Beginner's luck? 😉",
        "Impressive! But I'm just warming up! 🔥"
    ]

    bot_win_comments = [
        "Haha! I win! Better luck next time! 😜",
        "Did you really think you could beat me? 🤖",
        "Nice try, but the bot always wins! 🏆",
        "Easy win for me! Ready for a rematch? 😏",
        "You fought bravely, but I prevailed! 💪"
    ]

    # Determine the outcome and select a random comment
    if user_choice == bot_choice:
        result = "It's a tie!"
        comment = random.choice(tie_comments)
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "scissors" and bot_choice == "paper") or \
         (user_choice == "paper" and bot_choice == "rock"):
        result = "You win!"
        comment = random.choice(user_win_comments)
    else:
        result = "I win!"
        comment = random.choice(bot_win_comments)

    # Send the results with emojis and a funny comment
    await ctx.send(f"Your choice: {user_choice} {emoji_map[user_choice]}\n"
                   f"My choice: {bot_choice} {emoji_map[bot_choice]}\n"
                   f"{result} {comment}")

    # Remove the user from active games after completion
    active_games.pop(ctx.author.id, None)


# Start the bot asynchronously
async def start_bot():
    await bot.start(TOKEN)


asyncio.run(start_bot())
