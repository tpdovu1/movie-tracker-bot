import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
from dotenv import load_dotenv
import requests
import random

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Database file - use persistent volume path on Railway, local path otherwise
DB_FILE = os.getenv('MOVIES_DATA_PATH', 'movies.json')

# Channel ID where bot will respond (set to None to allow all channels)
ALLOWED_CHANNEL_ID = 1481502489625886923  # Replace with your channel ID, e.g., 1234567890

def is_allowed_channel(interaction: discord.Interaction) -> bool:
    """Check if command is in allowed channel"""
    if ALLOWED_CHANNEL_ID is None:
        return True
    return interaction.channel.id == ALLOWED_CHANNEL_ID

async def get_movie_info(movie_name):
    """Fetch movie info from OMDb API"""
    if not OMDB_API_KEY:
        return None

    # Check if input is a URL and extract movie info
    movie_info = await extract_from_url(movie_name)
    if movie_info:
        return movie_info

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


async def extract_from_url(input_str):
    """Extract movie info from IMDb or other URLs"""
    if not OMDB_API_KEY or not input_str:
        return None

    # IMDb URL patterns
    imdb_pattern = r'(?:https?://)?(?:www\.)?imdb\.com/title/([a-zA-Z0-9]+)/?'
    match = re.search(imdb_pattern, input_str, re.IGNORECASE)

    if match:
        imdb_id = match.group(1)
        try:
            url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"
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
            print(f"Error extracting from URL: {e}")

    return None


def is_url(input_str):
    """Check if input string is a URL"""
    url_pattern = r'https?://'
    return bool(re.search(url_pattern, input_str, re.IGNORECASE))

def load_movies():
    """Load movies from JSON file"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            # Convert old format (just list) to new format (dict with imdb_id)
            converted = {'watched': [], 'want_to_watch': []}
            for movie in data.get('watched', []):
                if isinstance(movie, dict):
                    converted['watched'].append(movie)
                else:
                    converted['watched'].append({'title': movie, 'imdb_id': None})
            for movie in data.get('want_to_watch', []):
                if isinstance(movie, dict):
                    converted['want_to_watch'].append(movie)
                else:
                    converted['want_to_watch'].append({'title': movie, 'imdb_id': None})
            return converted
    return {'watched': [], 'want_to_watch': []}

def save_movies(data):
    """Save movies to JSON file"""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    """Called when bot is ready"""
    print('Syncing slash commands...')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands: {[cmd.name for cmd in synced]}')
    except Exception as e:
        print(f'Sync error: {e}')
    print(f'{bot.user} has connected to Discord!')
    print('------')

@bot.tree.command(name='add_watched', description='Add a movie to watched list')
@app_commands.check(is_allowed_channel)
async def add_watched(interaction: discord.Interaction, movie_name: str):
    """Add a movie to the watched list"""
    await interaction.response.defer()

    movies = load_movies()

    # Fetch IMDb data (handles URL extraction automatically)
    movie_info = await get_movie_info(movie_name)

    # Determine actual name to store
    actual_name = movie_info['title'] if movie_info else movie_name

    # Check if movie already in watched (handle both dict and string formats)
    watched_titles = [m.get('title') if isinstance(m, dict) else m for m in movies['watched']]
    if actual_name in watched_titles:
        await interaction.followup.send(f'"{actual_name}" is already in your watched list!')
        return

    # Remove from want_to_watch if it's there
    movies['want_to_watch'] = [m for m in movies['want_to_watch'] if (m.get('title') if isinstance(m, dict) else m) != actual_name]

    # Add movie with IMDb ID
    imdb_id = movie_info.get('imdb_id') if movie_info else None
    movies['watched'].append({'title': actual_name, 'imdb_id': imdb_id})
    save_movies(movies)

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
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f'✅ Added "{actual_name}" to watched list!')

@bot.tree.command(name='add_want', description='Add a movie to want to watch list')
@app_commands.check(is_allowed_channel)
async def add_want(interaction: discord.Interaction, movie_name: str):
    """Add a movie to the want to watch list"""
    await interaction.response.defer()

    movies = load_movies()

    # Fetch IMDb data (handles URL extraction automatically)
    movie_info = await get_movie_info(movie_name)

    # Determine actual name to store
    actual_name = movie_info['title'] if movie_info else movie_name

    # Check if movie already in want_to_watch (handle both dict and string formats)
    want_titles = [m.get('title') if isinstance(m, dict) else m for m in movies['want_to_watch']]
    if actual_name in want_titles:
        await interaction.followup.send(f'"{actual_name}" is already in your want to watch list!')
        return

    # Remove from watched if it's there
    movies['watched'] = [m for m in movies['watched'] if (m.get('title') if isinstance(m, dict) else m) != actual_name]

    # Add movie with IMDb ID
    imdb_id = movie_info.get('imdb_id') if movie_info else None
    movies['want_to_watch'].append({'title': actual_name, 'imdb_id': imdb_id})
    save_movies(movies)

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
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f'📝 Added "{actual_name}" to want to watch list!')

@bot.tree.command(name='movie_info', description='Get IMDb info about a movie')
@app_commands.check(is_allowed_channel)
async def movie_info(interaction: discord.Interaction, movie_name: str):
    """Get IMDb information about a movie"""
    await interaction.response.defer()

    if not OMDB_API_KEY:
        await interaction.followup.send('❌ IMDb API key not configured!')
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
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f'❌ Movie "{movie_name}" not found on IMDb!')

@bot.tree.command(name='random_movie', description='Pick a random movie from your want to watch list')
@app_commands.check(is_allowed_channel)
async def random_movie(interaction: discord.Interaction):
    """Pick a random movie from the want to watch list"""
    await interaction.response.defer()

    movies = load_movies()

    if not movies['want_to_watch']:
        await interaction.followup.send('📋 Your want to watch list is empty! Add some movies first.')
        return

    # Pick a random movie (handle both dict and string formats)
    movie = random.choice(movies['want_to_watch'])
    chosen_movie = movie.get('title') if isinstance(movie, dict) else movie

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
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f'🎲 Random Pick: **{chosen_movie}**\n*(IMDb data not available for this movie)*')

@bot.tree.command(name='remove_movie', description='Remove a movie from your lists')
@app_commands.check(is_allowed_channel)
async def remove_movie(interaction: discord.Interaction, movie_name: str, list_type: str = None):
    """Remove a movie from a specific list or auto-detect"""
    if list_type:
        list_type = list_type.lower()

    movies = load_movies()

    # Helper function to get title from movie (handles both dict and string)
    def get_title(movie):
        return movie.get('title') if isinstance(movie, dict) else movie

    if list_type is None:
        # Auto-detect which list to remove from
        watched_titles = [get_title(m) for m in movies['watched']]
        want_titles = [get_title(m) for m in movies['want_to_watch']]

        if movie_name in watched_titles:
            movies['watched'] = [m for m in movies['watched'] if get_title(m) != movie_name]
            save_movies(movies)
            await interaction.response.send_message(f'🗑️ Removed "{movie_name}" from watched list!')
        elif movie_name in want_titles:
            movies['want_to_watch'] = [m for m in movies['want_to_watch'] if get_title(m) != movie_name]
            save_movies(movies)
            await interaction.response.send_message(f'🗑️ Removed "{movie_name}" from want to watch list!')
        else:
            await interaction.response.send_message(f'❌ "{movie_name}" not found in any list!')
    else:
        if list_type in ['watched', 'w']:
            watched_titles = [get_title(m) for m in movies['watched']]
            if movie_name in watched_titles:
                movies['watched'] = [m for m in movies['watched'] if get_title(m) != movie_name]
                save_movies(movies)
                await interaction.response.send_message(f'🗑️ Removed "{movie_name}" from watched list!')
            else:
                await interaction.response.send_message(f'❌ "{movie_name}" not in watched list!')
        elif list_type in ['want', 'w2w', 'want_to_watch']:
            want_titles = [get_title(m) for m in movies['want_to_watch']]
            if movie_name in want_titles:
                movies['want_to_watch'] = [m for m in movies['want_to_watch'] if get_title(m) != movie_name]
                save_movies(movies)
                await interaction.response.send_message(f'🗑️ Removed "{movie_name}" from want to watch list!')
            else:
                await interaction.response.send_message(f'❌ "{movie_name}" not in want to watch list!')
        else:
            await interaction.response.send_message('❌ Use `watched` or `want` to specify the list!')

@bot.tree.command(name='watched', description='Show all watched movies')
@app_commands.check(is_allowed_channel)
async def watched(interaction: discord.Interaction):
    """Show all watched movies"""
    movies = load_movies()

    if not movies['watched']:
        await interaction.response.send_message('📽️ No movies watched yet!')
        return

    # Build movie list with IMDb links
    movie_lines = []
    for movie in sorted(movies['watched'], key=lambda x: x.get('title', '') if isinstance(x, dict) else x):
        title = movie.get('title') if isinstance(movie, dict) else movie
        imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
        if imdb_id:
            movie_lines.append(f"✅ [{title}](https://www.imdb.com/title/{imdb_id}/)")
        else:
            movie_lines.append(f"✅ {title}")

    movie_list = '\n'.join(movie_lines)
    embed = discord.Embed(title="🎬 Watched Movies", description=movie_list, color=discord.Color.green())
    embed.set_footer(text=f"Total: {len(movies['watched'])} movies")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='want_to_watch', description='Show all movies in want to watch list')
@app_commands.check(is_allowed_channel)
async def want_to_watch(interaction: discord.Interaction):
    """Show all movies in want to watch list"""
    movies = load_movies()

    if not movies['want_to_watch']:
        await interaction.response.send_message('📋 Want to watch list is empty!')
        return

    # Build movie list with IMDb links
    movie_lines = []
    for movie in sorted(movies['want_to_watch'], key=lambda x: x.get('title', '') if isinstance(x, dict) else x):
        title = movie.get('title') if isinstance(movie, dict) else movie
        imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
        if imdb_id:
            movie_lines.append(f"📝 [{title}](https://www.imdb.com/title/{imdb_id}/)")
        else:
            movie_lines.append(f"📝 {title}")

    movie_list = '\n'.join(movie_lines)
    embed = discord.Embed(title="🎬 Want to Watch", description=movie_list, color=discord.Color.blue())
    embed.set_footer(text=f"Total: {len(movies['want_to_watch'])} movies")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='all_movies', description='Show all movies in both lists')
@app_commands.check(is_allowed_channel)
async def all_movies(interaction: discord.Interaction):
    """Show all movies in both lists"""
    movies = load_movies()

    watched_count = len(movies['watched'])
    want_count = len(movies['want_to_watch'])

    embed = discord.Embed(title="🎬 Movie Collection", color=discord.Color.purple())

    if movies['watched']:
        movie_lines = []
        for movie in sorted(movies['watched'], key=lambda x: x.get('title', '') if isinstance(x, dict) else x):
            title = movie.get('title') if isinstance(movie, dict) else movie
            imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
            if imdb_id:
                movie_lines.append(f"✅ [{title}](https://www.imdb.com/title/{imdb_id}/)")
            else:
                movie_lines.append(f"✅ {title}")
        watched_list = '\n'.join(movie_lines)
        embed.add_field(name="Watched 🎥", value=watched_list, inline=False)

    if movies['want_to_watch']:
        movie_lines = []
        for movie in sorted(movies['want_to_watch'], key=lambda x: x.get('title', '') if isinstance(x, dict) else x):
            title = movie.get('title') if isinstance(movie, dict) else movie
            imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
            if imdb_id:
                movie_lines.append(f"📝 [{title}](https://www.imdb.com/title/{imdb_id}/)")
            else:
                movie_lines.append(f"📝 {title}")
        want_list = '\n'.join(movie_lines)
        embed.add_field(name="Want to Watch 📋", value=want_list, inline=False)

    if not movies['watched'] and not movies['want_to_watch']:
        embed.description = "No movies added yet!"

    embed.set_footer(text=f"Watched: {watched_count} | Want to Watch: {want_count}")
    await interaction.response.send_message(embed=embed)

class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.confirmed = None

    @discord.ui.button(label='✅ Confirm', style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        save_movies({'watched': [], 'want_to_watch': []})
        await interaction.response.send_message('🗑️ All movies cleared!')
        self.stop()

    @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.send_message('❌ Cancelled!')
        self.stop()

@bot.tree.command(name='clear_all', description='Clear all movies (requires confirmation)')
@app_commands.check(is_allowed_channel)
async def clear_all(interaction: discord.Interaction):
    """Clear all movies - requires confirmation"""
    view = ConfirmView()
    await interaction.response.send_message('⚠️ Are you sure you want to clear all movies?', view=view)

@bot.tree.command(name='help', description='Show available commands')
@app_commands.check(is_allowed_channel)
async def help_command(interaction: discord.Interaction):
    """Show help message"""
    embed = discord.Embed(title="🎬 Movie Tracker Bot - Commands", color=discord.Color.gold())

    commands_list = [
        ("/add_watched <movie>", "Add a movie to watched list"),
        ("/add_want <movie>", "Add a movie to want to watch list"),
        ("/movie_info <movie>", "Get IMDb info about a movie"),
        ("/random_movie", "Pick a random movie from want to watch list"),
        ("/remove_movie <movie> [watched|want]", "Remove a movie from any list"),
        ("/watched", "Show all watched movies"),
        ("/want_to_watch", "Show all movies in want to watch list"),
        ("/all_movies", "Show all movies in both lists"),
        ("/refresh_imdb", "Update IMDb IDs for all movies"),
        ("/clear_all", "Clear all movies (requires confirmation)"),
        ("/help", "Show this help message"),
    ]

    for command, description in commands_list:
        embed.add_field(name=command, value=description, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='refresh_imdb', description='Update IMDb IDs for all movies')
@app_commands.check(is_allowed_channel)
async def refresh_imdb(interaction: discord.Interaction):
    """Update IMDb IDs for all movies in the database"""
    await interaction.response.defer()

    if not OMDB_API_KEY:
        await interaction.followup.send('❌ IMDb API key not configured!')
        return

    movies = load_movies()
    updated_count = 0
    errors = []

    for list_name in ['watched', 'want_to_watch']:
        for movie in movies[list_name]:
            if isinstance(movie, dict):
                title = movie.get('title', '')
                current_imdb_id = movie.get('imdb_id')

                # Skip if already has IMDb ID
                if current_imdb_id:
                    continue

                # Fetch IMDb ID
                try:
                    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
                    response = requests.get(url, timeout=5)
                    data = response.json()

                    if data.get('Response') == 'True':
                        movie['imdb_id'] = data.get('imdbID')
                        updated_count += 1
                        print(f"Updated: {title} -> {movie['imdb_id']}")
                except Exception as e:
                    errors.append(f"{title}: {str(e)}")

    if updated_count > 0:
        save_movies(movies)

    await interaction.followup.send(f"✅ Updated IMDb IDs for {updated_count} movies!" + (f"\nErrors: {', '.join(errors)}" if errors else ""))

# Error handler for app commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle app command errors"""
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message('❌ movie-tracker-bot commands only work in movie-tracker-bot text channel', ephemeral=True)
    else:
        await interaction.response.send_message(f'❌ An error occurred: {error}', ephemeral=True)

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)