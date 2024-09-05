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

# Ensure environment variables are properly loaded
if not TOKEN or not CHANNEL_ID:
    raise ValueError("Missing Discord token or channel ID in environment variables.")

# Define intents for the bot
intents = discord.Intents.default()
intents.typing = True
intents.presences = True
intents.messages = True
intents.members = True
intents.message_content = True

# Create a bot instance with the defined intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to track ongoing games per user (for single or multiplayer)
active_games = {"singleplayer": {}, "multiplayer": {}}

# Dictionary for leaderboard stats
leaderboard = {}

# Dictionary to store game history for each user
game_history = {}


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Rock, Paper, Scissors!"))
    print(f"{bot.user.name} has connected to Discord!")


# Function to update leaderboard
def update_leaderboard(winner=None, loser=None, tie=False):
    if tie:
        for player in [winner, loser]:
            if player not in leaderboard:
                leaderboard[player] = {"wins": 0, "losses": 0, "ties": 0}
            leaderboard[player]["ties"] += 1
    else:
        if winner:
            if winner not in leaderboard:
                leaderboard[winner] = {"wins": 0, "losses": 0, "ties": 0}
            leaderboard[winner]["wins"] += 1
        if loser:
            if loser not in leaderboard:
                leaderboard[loser] = {"wins": 0, "losses": 0, "ties": 0}
            leaderboard[loser]["losses"] += 1


# Function to update game history
def update_game_history(user_id, result, opponent=None):
    if user_id not in game_history:
        game_history[user_id] = []
    game_history[user_id].append((result, opponent))


# Helper function to convert abbreviations to full choices
def get_full_choice(input_choice):
    abbreviations = {"r": "rock", "p": "paper", "s": "scissors"}
    return abbreviations.get(input_choice, input_choice)


# Command to show leaderboard
@bot.command(name="leaderboard", help="Show the leaderboard")
async def show_leaderboard(ctx):
    if not leaderboard:
        await ctx.send("Leaderboard is empty.")
        return

    leaderboard_message = "🏆 **Leaderboard** 🏆\n"
    for user_id, stats in leaderboard.items():
        user = bot.get_user(user_id)  # Use cached user info
        if user is not None:
            user = await bot.fetch_user(user_id)  # Fetch if not in cache
        leaderboard_message += f"{user.name}: {stats['wins']} Wins, {stats['losses']} Losses, {stats['ties']} Ties\n"

    await ctx.send(leaderboard_message)


# Command to show game history for the user
@bot.command(name="history", help="Show your game history")
async def show_history(ctx):
    user_id = ctx.author.id
    if user_id not in game_history or not game_history[user_id]:
        await ctx.send("You have no game history yet.")
        return

    history_message = f"**{ctx.author.name}'s Game History** 📜\n"
    for result, opponent in game_history[user_id]:
        if opponent:
            opponent_name = (await bot.fetch_user(opponent)).name
            history_message += f"Result: {result} against {opponent_name}\n"
        else:
            history_message += f"Result: {result} (against bot)\n"

    await ctx.send(history_message)


# Multiplayer rock, paper, scissors game
@bot.command(name="rps", help="Play rock, paper, scissors (against bot or challenge a user)")
async def rps(ctx, opponent: discord.Member = None):
    # Define choices and corresponding emojis
    rps_game = ["rock", "paper", "scissors"]
    emoji_map = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

    # Check if user is already in a game
    if ctx.author.id in active_games["singleplayer"] or ctx.author.id in active_games["multiplayer"]:
        await ctx.send("You are already in an ongoing game! Finish it first.")
        return

    # Multiplayer game logic
    if opponent:
        if opponent.id == ctx.author.id:
            await ctx.send("You can't challenge yourself!")
            return
        if opponent.id in active_games["multiplayer"]:
            await ctx.send(f"{opponent.name} is already in a game! Try again later.")
            return

        await ctx.send(f"{opponent.mention}, {ctx.author.name} has challenged you to Rock, Paper, Scissors! Type your choice.")

        # Track active multiplayer games
        active_games["multiplayer"][ctx.author.id] = opponent.id
        active_games["multiplayer"][opponent.id] = ctx.author.id

        player_choices = {}

        async def get_player_choice(player):
            def check(msg):
                return msg.author == player and msg.content.lower() in rps_game + list("rps")
            
            try:
                # Wait for player input
                player_msg = await bot.wait_for("message", check=check, timeout=30)
                choice = get_full_choice(player_msg.content.lower())
                return choice
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ {player.name} took too long to respond! Game canceled.")
                return None

        # Get player choices asynchronously
        player_1_choice = asyncio.create_task(get_player_choice(ctx.author))
        player_2_choice = asyncio.create_task(get_player_choice(opponent))

        # Mask inputs while waiting for both
        await ctx.send(f"{ctx.author.name}'s choice: ***\n{opponent.name}'s choice: ***")

        # Gather both players' choices
        user_choice = await player_1_choice
        opponent_choice = await player_2_choice

        # Check if any player timed out
        if user_choice is None or opponent_choice is None:
            active_games["multiplayer"].pop(ctx.author.id, None)
            active_games["multiplayer"].pop(opponent.id, None)
            return

        # Reveal choices after both inputs are received
        await ctx.send(f"{ctx.author.name}'s choice: {user_choice} {emoji_map[user_choice]}\n"
                       f"{opponent.name}'s choice: {opponent_choice} {emoji_map[opponent_choice]}")

        # Determine the winner
        if user_choice == opponent_choice:
            result = "It's a tie!"
            update_leaderboard(ctx.author.id, opponent.id, tie=True)
            update_game_history(ctx.author.id, "Tie", opponent.id)
            update_game_history(opponent.id, "Tie", ctx.author.id)
        elif (user_choice == "rock" and opponent_choice == "scissors") or \
             (user_choice == "scissors" and opponent_choice == "paper") or \
             (user_choice == "paper" and opponent_choice == "rock"):
            result = f"{ctx.author.name} wins!"
            update_leaderboard(ctx.author.id, opponent.id)
            update_game_history(ctx.author.id, "Win", opponent.id)
            update_game_history(opponent.id, "Loss", ctx.author.id)
        else:
            result = f"{opponent.name} wins!"
            update_leaderboard(opponent.id, ctx.author.id)
            update_game_history(ctx.author.id, "Loss", opponent.id)
            update_game_history(opponent.id, "Win", ctx.author.id)

        await ctx.send(result)

        # Remove players from active games
        active_games["multiplayer"].pop(ctx.author.id, None)
        active_games["multiplayer"].pop(opponent.id, None)


# Global error handler to catch unexpected errors
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That command doesn't exist!")
    else:
        await ctx.send(f"An error occurred: {str(error)}")


# Run the bot
bot.run(TOKEN)
