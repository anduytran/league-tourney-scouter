import discord
import sqlite3
from discord.ext import commands
import requests
from dotenv import load_dotenv, find_dotenv
import os
import json

def get_champion_name(champion_id):
    """
    Given a champion id (e.g., 266), return the champion name.
    Note: champion_id can be int or str. The JSON 'key' values are strings.
    """
    target = str(champion_id)
    for champ in champion_data.values():
        if champ["key"] == target:
            return champ["name"]
    return None
    
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

with open("data/championFull.json", "r") as file:
    data = json.load(file)
champion_data = data["data"]

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
async def player(ctx, *, summoner_name):
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
    
    # Get ranked info using League V4
    ranked_url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    ranked_response = requests.get(ranked_url, headers=headers)
    ranked_data = ranked_response.json()

    summoner_url = f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    summoner_response = requests.get(summoner_url, headers=headers)
    summoner_data = summoner_response.json()
    level = summoner_data["summonerLevel"]

    mastery_url = f"https://na1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=3"
    master_response = requests.get(mastery_url, headers=headers)
    mastery_data = master_response.json()
    champion_ids = [entry["championId"] for entry in mastery_data]
    champion_pts = [entry["championPoints"] for entry in mastery_data]

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
    if not ranked_data:
        await ctx.send(f"{summoner_name} is unranked.")
        top3 = "\n".join([f"{get_champion_name(champ_id)} with {pts} points" for champ_id, pts in zip(champion_ids, champion_pts)])
        final_message = "\n\nTop 3 Champion Masteries:\n" + top3
        await ctx.send(final_message)
        return
    else:
        final_message = f"**{summoner_name}** (Level {level}):\n" + "\n".join(rank_messages)
        top3 = "\n".join([f"{get_champion_name(champ_id)} with {pts} points" for champ_id, pts in zip(champion_ids, champion_pts)])
        final_message += "\n\nTop 3 Champion Masteries:\n" + top3
        await ctx.send(final_message)
    
@bot.command()
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
