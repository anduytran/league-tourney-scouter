import discord
import sqlite3
from discord.ext import commands
import requests
from dotenv import load_dotenv, find_dotenv
import os

conn = sqlite3.connect("botdata.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_searches (
    puuid TEXT,
    summoner_name TEXT,
    search_count INTEGER,
    PRIMARY KEY (puuid, summoner_name)
)
''')

conn.commit()
conn.close()

# Replace with your tokens
RIOT_API_KEY = 'YOUR_RIOT_API_KEY'
DISCORD_TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
load_dotenv(find_dotenv(), override=True)
RIOT_API_KEY = os.getenv('RIOT_API_KEY')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
REGION = 'na1'  # or 'euw1', 'kr', etc.

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='l!', intents=intents)
print(RIOT_API_KEY)
print(DISCORD_TOKEN)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # Define a Player class to hold player information
class Player:
    def __init__(self, name, rank, mastery_champions):
        self.name = name
        self.rank = rank  # Assume this is a numeric value (e.g., LP or a mapped rank score)
        self.mastery_champions = mastery_champions  # List of top three mastery champions

    def __repr__(self):
        return f"Player(name={self.name}, rank={self.rank}, mastery={self.mastery_champions})"

# Define a Team class to hold team information including a list of players
class Team:
    def __init__(self, team_name, players):
        self.team_name = team_name
        self.players = players  # A list of Player objects

    def average_rank(self):
        # Calculate average rank assuming rank is a numeric value
        if not self.players:
            return 0
        total = sum(player.rank for player in self.players)
        return total / len(self.players)

    def __repr__(self):
        return f"Team(team_name={self.team_name}, players={self.players})"

@bot.command()
async def rank(ctx, *, summoner_name):
    # Get account info from account
    account = summoner_name.split("#")

    account_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{account[0]}/{account[1]}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    account_response = requests.get(account_url, headers=headers)

    if account_response.status_code != 200:
        await ctx.send("Summoner not found.")
        return

    account_data = account_response.json()
    puuid = account_data["puuid"]

    print(f"{account[0]}#{account[1]}\npuuid = {puuid}")

    # Get ranked info using League V4
    ranked_url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    ranked_response = requests.get(ranked_url, headers=headers)
    ranked_data = ranked_response.json()

    summoner_url = f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    summoner_response = requests.get(summoner_url, headers=headers)
    summoner_data = summoner_response.json()
    level = summoner_data["summonerLevel"]

    if not ranked_data:
        await ctx.send(f"{summoner_name} is unranked.")
        return

    rank_messages = []
    for queue in ranked_data:
        queue_type = queue["queueType"].replace("_", " ").title()
        tier = queue["tier"].title()
        rank = queue["rank"]
        lp = queue["leaguePoints"]
        wins = queue["wins"]
        losses = queue["losses"]
        winrate = round((wins / (wins + losses)) * 100, 2)

        rank_messages.append(
            f"**{queue_type}**: {tier} {rank} - {lp} LP ({wins}W/{losses}L, {winrate}% WR)"
        )

    final_message = f"**{summoner_name}** (Level {level}):\n" + "\n".join(rank_messages)
    await ctx.send(final_message)

async def teamadd(ctx, *, team_name):
    """
    Creates a new team with the provided team_name and 5 placeholder players.
    Each player currently has default placeholder data (name, rank, and mastery champions).
    """
    players = []
    # Create 5 player objects with placeholder values
    for i in range(5):
        player_name = f"Player{i+1}"
        rank_value = 0  # Replace with actual rank value when available
        mastery_champions = ["Champion1", "Champion2", "Champion3"]
        players.append(Player(name=player_name, rank=rank_value, mastery_champions=mastery_champions))
    
    # Create the team object
    team = Team(team_name=team_name, players=players)
    # Store the team in our in-memory dictionary (or later in your persistent database)
    teams_storage[team_name] = team

    # Calculate the average rank from the player objects
    avg_rank = team.average_rank()
    await ctx.send(f"Team '{team_name}' created with 5 players. Average rank: {avg_rank}")



bot.run(DISCORD_TOKEN)
