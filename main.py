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
            return [champ["name"]]
    return None

def get_account(summoner_name):
    account = summoner_name.split("#")
    account_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{account[0]}/{account[1]}"
    account_response = requests.get(account_url, headers=headers)
    if account_response.status_code != 200:
        return 404
    return account_response.json()

def get_account_by_puuid(puuid):
    account_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    account_response = requests.get(account_url, headers=headers)
    if account_response.status_code != 200:
        return 404
    return account_response.json()

def get_rank(puuid):
    ranked_url = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    ranked_response = requests.get(ranked_url, headers=headers)
    return ranked_response.json()

def get_summoner(puuid):
    summoner_url = f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    summoner_response = requests.get(summoner_url, headers=headers)
    return summoner_response.json()

def get_mastery(puuid, count):
    mastery_url = f"https://na1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={count}"
    master_response = requests.get(mastery_url, headers=headers)
    return master_response.json()

conn = sqlite3.connect("botdata.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    puuid TEXT PRIMARY KEY,
    name TEXT,
    tag TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS teams (
    team_name TEXT PRIMARY KEY,
    puuid1 TEXT,
    puuid2 TEXT,
    puuid3 TEXT,
    puuid4 TEXT,
    puuid5 TEXT
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
headers = {"X-Riot-Token": RIOT_API_KEY}
REGION = 'na1'  # or 'euw1', 'kr', etc.
puuids = [None, None, None, None, None]

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
    # Get account info from Account API
    account_data = get_account(summoner_name)
    if account_data == 404:
        await ctx.send("Summoner not found.")
        return
    puuid = account_data["puuid"]
    name = account_data["gameName"]
    tag = account_data["tagLine"]
    
    # Get ranked info using League V4 API
    ranked_data = get_rank(puuid)

    # Get summoner info using Summoner API
    summoner_data = get_summoner(puuid)
    level = summoner_data["summonerLevel"]

    mastery_data = get_mastery(puuid, 3)
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
        await ctx.send(f"{name}#{tag} is unranked.")
        top3 = "\n".join([f"**{get_champion_name(champ_id)[2:-2]}** with {pts} points" for champ_id, pts in zip(champion_ids, champion_pts)])
        final_message = "\n\nTop 3 Champion Masteries:\n" + top3
        await ctx.send(final_message)
        return
    else:
        final_message = f"**{name}#{tag}** (Level {level}):\n" + "\n".join(rank_messages)
        top3 = "\n".join([f"**{get_champion_name(champ_id)[2:-2]}** with {pts} points" for champ_id, pts in zip(champion_ids, champion_pts)])
        final_message += "\n\nTop 3 Champion Masteries:\n" + top3
        await ctx.send(final_message)
    
@bot.command()
async def team(ctx, subcommand: str, team_name: str, *players: str):
    """
    Creates a new team with the provided team_name and 5 placeholder players.
    Each player currently has default placeholder data (name, rank, and mastery champions).
    """
    conn = sqlite3.connect("botdata.db")
    cursor = conn.cursor()

    if subcommand.lower() == "add":
        cursor.execute("SELECT team_name FROM teams WHERE team_name = ?", (team_name,))
        if cursor.fetchone() is not None:
            await ctx.send(f"Team '{team_name}' already exists.")
            conn.close()
            return
        # Check that exactly 5 player names were provided.
        if len(players) != 5:
            await ctx.send("Please provide exactly 5 player names for team creation.\nFormat: `!team add teamname player1 player2 player3 player4 player5`")
            conn.close()
            return
        
        
        puuids = [None, None, None, None, None]
        for i in range(5):
            name_value = players[i].split('#')[0]
            tag_value = players[i].split('#')[1]
            cursor.execute("SELECT puuid FROM players WHERE REPLACE(LOWER(name), ' ', '') = ? AND LOWER(tag) = ?", (name_value.lower().replace(" ", ""), tag_value.lower()))
            if cursor.fetchone() is None:
                account_data = get_account(players[i])
                print(account_data)
                puuid = account_data["puuid"]
                name = account_data["gameName"]
                tag = account_data["tagLine"]
                player_query = f"INSERT INTO players (puuid, name, tag) VALUES (?, ?, ?)"
                player_data = (puuid, name, tag)
                cursor.execute(player_query, player_data)
                
                conn.commit()
            else:
                puuids[i] = cursor.fetchone()
        cursor.execute(f"INSERT INTO teams (team_name, puuid1, puuid2, puuid3, puuid4, puuid5) VALUES (?, ?, ?, ?, ?, ?)", (team_name, puuids[0], puuids[1], puuids[2], puuids[3], puuids[4]))
        await ctx.send(f"Team {team_name} successfully added!")
        puuids = [None, None, None, None, None]
        conn.commit()
        conn.close()
        return
    if subcommand.lower() == "info":
        cursor.execute("SELECT * FROM teams WHERE team_name = ?", (team_name,))
        row = cursor.fetchone()
        if row is None:
            await ctx.send("Team not found.")
            return
        # row[0] is the team name, row[1]..row[5] are the puuid values.
        puuids = row[1:]
        final_message = f"**{row[0]}**:"
        for i in range(5):
            cursor.execute("SELECT name, tag FROM players WHERE puuid = ?", (f"{puuids[i]}"))
            name = cursor.fetchone()
            tag = cursor.fetchone()
            summoner_data = get_summoner(puuids[i])
            level = summoner_data["summonerLevel"]
            mastery_data = get_mastery(puuids[i], 1)
            champion_ids = [entry["championId"] for entry in mastery_data]
            # champion_pts = [entry["championPoints"] for entry in mastery_data]
            ranked_data = get_rank(puuids[i])
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
                final_message += f"\n{i} **{name}#{tag} (Level {level}**): Rank: Unranked - Best Champ: **{get_champion_name(champion_ids)[2:-2]}**"
            else:
                final_message += f"\n{i}. **{name}#{tag} (Level {level}**): Rank: {rank_messages} - Best Champ: **{get_champion_name(champion_ids)[2:-2]}**"
        await ctx.send(final_message)
    elif subcommand.lower() == "remove":
        # Remove the team if it exists.
        if team_name in teams_storage:
            del teams_storage[team_name]
            await ctx.send(f"Team '{team_name}' has been removed.")
        else:
            await ctx.send(f"Team '{team_name}' does not exist.")

    else:
        await ctx.send("Invalid subcommand. Please use 'add' or 'remove'.")



bot.run(DISCORD_TOKEN)
