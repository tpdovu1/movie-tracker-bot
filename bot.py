import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import requests
import random

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')

# Initialize bot with command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Database file
DB_FILE = 'movies.json'

# Channel ID where bot will respond (set to None to allow all channels)
ALLOWED_CHANNEL_ID = 1481502489625886923  # Replace with your channel ID, e.g., 1234567890

def is_allowed_channel(ctx):
    """Check if command is in allowed channel"""
    if ALLOWED_CHANNEL_ID is None:
        return True
    return ctx.channel.id == ALLOWED_CHANNEL_ID

async def get_movie_info(movie_name):
    """Fetch movie info from OMDb API"""
    if not OMDB_API_KEY:
        return None
    
    try:
        url = f"http://www.omdbapi.com/?t={movie_name}&apikey={OMDB_API_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('Response') == 'True':
            return {
                'title': data.get('Title'),
                'year': data.get('Year'),
                'rating': data.get('imdbRating'),
                'plot': data.get('Plot'),
                'genre': data.get('Genre'),
                'director': data.get('Director'),
                'poster': data.get('Poster'),
                'imdb_id': data.get('imdbID')
            }
    except Exception as e:
        print(f"Error fetching movie data: {e}")
    
    return None

def load_movies():
    """Load movies from JSON file"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'watched': [], 'want_to_watch': []}

def save_movies(data):
    """Save movies to JSON file"""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    """Called when bot is ready"""
    print(f'{bot.user} has connected to Discord!')
    print('------')

@bot.command(name='add_watched', help='Add a movie to watched list: !add_watched <movie_name>')
@commands.check(is_allowed_channel)
async def add_watched(ctx, *, movie_name):
    """Add a movie to the watched list"""
    movies = load_movies()
    
    if movie_name in movies['watched']:
        await ctx.send(f'"{movie_name}" is already in your watched list!')
        return
    
    # Remove from want_to_watch if it's there
    if movie_name in movies['want_to_watch']:
        movies['want_to_watch'].remove(movie_name)
    
    movies['watched'].append(movie_name)
    save_movies(movies)
    
    # Fetch IMDb data
    movie_info = await get_movie_info(movie_name)
    
    if movie_info:
        embed = discord.Embed(title=f"✅ {movie_info['title']}", color=discord.Color.green())
        if movie_info['year']:
            embed.add_field(name="Year", value=movie_info['year'], inline=True)
        if movie_info['rating'] and movie_info['rating'] != 'N/A':
            embed.add_field(name="IMDb Rating", value=f"⭐ {movie_info['rating']}/10", inline=True)
        if movie_info['genre']:
            embed.add_field(name="Genre", value=movie_info['genre'], inline=True)
        if movie_info['director']:
            embed.add_field(name="Director", value=movie_info['director'], inline=False)
        if movie_info['plot']:
            embed.add_field(name="Plot", value=movie_info['plot'][:250] + "..." if len(movie_info['plot']) > 250 else movie_info['plot'], inline=False)
        if movie_info['poster'] and movie_info['poster'] != 'N/A':
            embed.set_thumbnail(url=movie_info['poster'])
        embed.description = "Added to watched list!"
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'✅ Added "{movie_name}" to watched list!')

@bot.command(name='add_want', help='Add a movie to want to watch list: !add_want <movie_name>')
@commands.check(is_allowed_channel)
async def add_want(ctx, *, movie_name):
    """Add a movie to the want to watch list"""
    movies = load_movies()
    
    if movie_name in movies['want_to_watch']:
        await ctx.send(f'"{movie_name}" is already in your want to watch list!')
        return
    
    # Remove from watched if it's there
    if movie_name in movies['watched']:
        movies['watched'].remove(movie_name)
    
    movies['want_to_watch'].append(movie_name)
    save_movies(movies)
    
    # Fetch IMDb data
    movie_info = await get_movie_info(movie_name)
    
    if movie_info:
        embed = discord.Embed(title=f"📝 {movie_info['title']}", color=discord.Color.blue())
        if movie_info['year']:
            embed.add_field(name="Year", value=movie_info['year'], inline=True)
        if movie_info['rating'] and movie_info['rating'] != 'N/A':
            embed.add_field(name="IMDb Rating", value=f"⭐ {movie_info['rating']}/10", inline=True)
        if movie_info['genre']:
            embed.add_field(name="Genre", value=movie_info['genre'], inline=True)
        if movie_info['director']:
            embed.add_field(name="Director", value=movie_info['director'], inline=False)
        if movie_info['plot']:
            embed.add_field(name="Plot", value=movie_info['plot'][:250] + "..." if len(movie_info['plot']) > 250 else movie_info['plot'], inline=False)
        if movie_info['poster'] and movie_info['poster'] != 'N/A':
            embed.set_thumbnail(url=movie_info['poster'])
        embed.description = "Added to want to watch list!"
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'📝 Added "{movie_name}" to want to watch list!')

@bot.command(name='movie_info', help='Get IMDb info about a movie: !movie_info <movie_name>')
@commands.check(is_allowed_channel)
async def movie_info(ctx, *, movie_name):
    """Get IMDb information about a movie"""
    if not OMDB_API_KEY:
        await ctx.send('❌ IMDb API key not configured!')
        return
    
    movie_data = await get_movie_info(movie_name)
    
    if movie_data:
        embed = discord.Embed(title=movie_data['title'], color=discord.Color.gold())
        if movie_data['year']:
            embed.add_field(name="Year", value=movie_data['year'], inline=True)
        if movie_data['rating'] and movie_data['rating'] != 'N/A':
            embed.add_field(name="IMDb Rating", value=f"⭐ {movie_data['rating']}/10", inline=True)
        if movie_data['genre']:
            embed.add_field(name="Genre", value=movie_data['genre'], inline=True)
        if movie_data['director']:
            embed.add_field(name="Director", value=movie_data['director'], inline=False)
        if movie_data['plot']:
            embed.add_field(name="Plot", value=movie_data['plot'], inline=False)
        if movie_data['poster'] and movie_data['poster'] != 'N/A':
            embed.set_image(url=movie_data['poster'])
        embed.set_footer(text=f"IMDb ID: {movie_data['imdb_id']}")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'❌ Movie "{movie_name}" not found on IMDb!')

@bot.command(name='random_movie', help='Pick a random movie from your want to watch list')
@commands.check(is_allowed_channel)
async def random_movie(ctx):
    """Pick a random movie from the want to watch list"""
    movies = load_movies()
    
    if not movies['want_to_watch']:
        await ctx.send('📋 Your want to watch list is empty! Add some movies first.')
        return
    
    # Pick a random movie
    chosen_movie = random.choice(movies['want_to_watch'])
    
    # Fetch IMDb data
    movie_info = await get_movie_info(chosen_movie)
    
    if movie_info:
        embed = discord.Embed(title=f"🎲 Random Pick: {movie_info['title']}", color=discord.Color.gold())
        if movie_info['year']:
            embed.add_field(name="Year", value=movie_info['year'], inline=True)
        if movie_info['rating'] and movie_info['rating'] != 'N/A':
            embed.add_field(name="IMDb Rating", value=f"⭐ {movie_info['rating']}/10", inline=True)
        if movie_info['genre']:
            embed.add_field(name="Genre", value=movie_info['genre'], inline=True)
        if movie_info['director']:
            embed.add_field(name="Director", value=movie_info['director'], inline=False)
        if movie_info['plot']:
            embed.add_field(name="Plot", value=movie_info['plot'][:250] + "..." if len(movie_info['plot']) > 250 else movie_info['plot'], inline=False)
        if movie_info['poster'] and movie_info['poster'] != 'N/A':
            embed.set_thumbnail(url=movie_info['poster'])
        embed.set_footer(text=f"Can't decide? Let me help! 🎬")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'🎲 Random Pick: **{chosen_movie}**\n*(IMDb data not available for this movie)*')

@bot.command(name='remove_movie', help='Remove a movie from any list: !remove_movie <movie_name>')
@commands.check(is_allowed_channel)
async def remove_movie(ctx, *, movie_name):
    """Remove a movie from either list"""
    movies = load_movies()
    removed = False
    
    if movie_name in movies['watched']:
        movies['watched'].remove(movie_name)
        removed = True
        location = 'watched'
    elif movie_name in movies['want_to_watch']:
        movies['want_to_watch'].remove(movie_name)
        removed = True
        location = 'want to watch'
    
    if removed:
        save_movies(movies)
        await ctx.send(f'🗑️ Removed "{movie_name}" from {location} list!')
    else:
        await ctx.send(f'❌ "{movie_name}" not found in any list!')

@bot.command(name='watched', help='Show all watched movies')
@commands.check(is_allowed_channel)
async def watched(ctx):
    """Show all watched movies"""
    movies = load_movies()
    
    if not movies['watched']:
        await ctx.send('📽️ No movies watched yet!')
        return
    
    movie_list = '\n'.join([f"✅ {movie}" for movie in sorted(movies['watched'])])
    embed = discord.Embed(title="🎬 Watched Movies", description=movie_list, color=discord.Color.green())
    embed.set_footer(text=f"Total: {len(movies['watched'])} movies")
    await ctx.send(embed=embed)

@bot.command(name='want_to_watch', help='Show all movies in want to watch list')
@commands.check(is_allowed_channel)
async def want_to_watch(ctx):
    """Show all movies in want to watch list"""
    movies = load_movies()
    
    if not movies['want_to_watch']:
        await ctx.send('📋 Want to watch list is empty!')
        return
    
    movie_list = '\n'.join([f"📝 {movie}" for movie in sorted(movies['want_to_watch'])])
    embed = discord.Embed(title="🎬 Want to Watch", description=movie_list, color=discord.Color.blue())
    embed.set_footer(text=f"Total: {len(movies['want_to_watch'])} movies")
    await ctx.send(embed=embed)

@bot.command(name='all_movies', help='Show all movies in both lists')
@commands.check(is_allowed_channel)
async def all_movies(ctx):
    """Show all movies in both lists"""
    movies = load_movies()
    
    watched_count = len(movies['watched'])
    want_count = len(movies['want_to_watch'])
    
    embed = discord.Embed(title="🎬 Movie Collection", color=discord.Color.purple())
    
    if movies['watched']:
        watched_list = '\n'.join([f"✅ {movie}" for movie in sorted(movies['watched'])])
        embed.add_field(name="Watched 🎥", value=watched_list, inline=False)
    
    if movies['want_to_watch']:
        want_list = '\n'.join([f"📝 {movie}" for movie in sorted(movies['want_to_watch'])])
        embed.add_field(name="Want to Watch 📋", value=want_list, inline=False)
    
    if not movies['watched'] and not movies['want_to_watch']:
        embed.description = "No movies added yet!"
    
    embed.set_footer(text=f"Watched: {watched_count} | Want to Watch: {want_count}")
    await ctx.send(embed=embed)

@bot.command(name='clear_all', help='Clear all movies (use with caution!')
@commands.check(is_allowed_channel)
async def clear_all(ctx):
    """Clear all movies - requires confirmation"""
    def check(reaction, user):
        return user == ctx.author and reaction.emoji in ['✅', '❌']
    
    confirm = await ctx.send("⚠️ Are you sure you want to clear all movies? React with ✅ to confirm or ❌ to cancel")
    await confirm.add_reaction('✅')
    await confirm.add_reaction('❌')
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30, check=check)
        
        if reaction.emoji == '✅':
            save_movies({'watched': [], 'want_to_watch': []})
            await ctx.send('🗑️ All movies cleared!')
        else:
            await ctx.send('❌ Cancelled!')
    except:
        await ctx.send('⏰ Action timed out!')

@bot.command(name='commands', help='Show available commands')
@commands.check(is_allowed_channel)
async def help_command(ctx):
    """Show help message"""
    embed = discord.Embed(title="🎬 Movie Tracker Bot - Commands", color=discord.Color.gold())
    
    commands_list = [
        ("!add_watched <movie>", "Add a movie to watched list"),
        ("!add_want <movie>", "Add a movie to want to watch list"),
        ("!movie_info <movie>", "Get IMDb info about a movie"),
        ("!random_movie", "Pick a random movie from want to watch list"),
        ("!remove_movie <movie>", "Remove a movie from any list"),
        ("!watched", "Show all watched movies"),
        ("!want_to_watch", "Show all movies in want to watch list"),
        ("!all_movies", "Show all movies in both lists"),
        ("!clear_all", "Clear all movies (requires confirmation)"),
        ("!commands", "Show this help message"),
    ]
    
    for command, description in commands_list:
        embed.add_field(name=command, value=description, inline=False)
    
    await ctx.send(embed=embed)

# Error handler
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ movie-tracker-bot commands only work in movie-tracker-bot text channel')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ Missing argument! Use !commands for command syntax.')
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f'❌ Command not found! Use !commands to see available commands.')
    else:
        await ctx.send(f'❌ An error occurred: {error}')

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)
