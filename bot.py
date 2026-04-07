import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
import asyncio
from dotenv import load_dotenv
import requests
import random

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Database file - use persistent volume path on Railway, local path otherwise
DB_FILE = os.getenv('MOVIES_DATA_PATH', 'movies.json')

# Channel ID where bot will respond (set to None to allow all channels)
ALLOWED_CHANNEL_ID = 1481502489625886923  # Replace with your channel ID, e.g., 1234567890
ADMIN_USER_IDS = ['131235386763509760', '130528077271793664']

def is_allowed_channel(interaction: discord.Interaction) -> bool:
    """Check if command is in allowed channel"""
    print(f'Channel check: interaction.channel.id={interaction.channel.id}, ALLOWED_CHANNEL_ID={ALLOWED_CHANNEL_ID}')
    if ALLOWED_CHANNEL_ID is None:
        return True
    return interaction.channel.id == ALLOWED_CHANNEL_ID

def is_admin(interaction: discord.Interaction) -> bool:
    """Check if user is an admin"""
    return str(interaction.user.id) in ADMIN_USER_IDS

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
                'actors': data.get('Actors'),
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
                    'actors': data.get('Actors'),
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

async def get_tmdb_similar(movie_name):
    """Get movie recommendations from TMDB based on movie name"""
    if not TMDB_API_KEY:
        return []

    try:
        # First search for the movie
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
        response = requests.get(search_url, timeout=5)
        data = response.json()

        if data.get('results') and len(data['results']) > 0:
            tmdb_id = data['results'][0]['id']

            # Get recommendations (movies people who liked this also watched)
            similar_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/recommendations?api_key={TMDB_API_KEY}"
            response = requests.get(similar_url, timeout=5)
            similar_data = response.json()

            if similar_data.get('results'):
                return similar_data['results'][:10]  # Return top 10
    except Exception as e:
        print(f"TMDB error: {e}")

    return []


async def get_imdb_id_from_tmdb(tmdb_id: int) -> str:
    """Get IMDb ID from TMDB ID"""
    if not TMDB_API_KEY:
        return None
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data.get('imdb_id')
    except:
        return None


def get_star_display(rating):
    """Generate star display - just shows number with star"""
    return f"⭐ {rating:.1f}"

def get_rating_value(rating_entry):
    """Extract numeric rating from rating entry (handles both old int and new dict formats)"""
    if rating_entry is None:
        return 0
    if isinstance(rating_entry, dict):
        return rating_entry.get('rating', 0)
    return rating_entry  # Legacy support for old int format
def get_rating_avg(ratings):
    """Calculate average rating from ratings dict (handles both old int and new dict formats)"""
    if not ratings:
        return 0
    return sum(get_rating_value(r) for r in ratings.values()) / len(ratings)

def load_movies():
    """Load movies from JSON file"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            # Convert old format (just list) to new format (dict with imdb_id)
            converted = {'watched': [], 'want_to_watch': []}
            for movie in data.get('watched', []):
                if isinstance(movie, dict):
                    # Ensure new fields exist for backwards compatibility
                    movie['added_by'] = movie.get('added_by')
                    movie['added_username'] = movie.get('added_username')
                    movie['ratings'] = movie.get('ratings', {})
                    converted['watched'].append(movie)
                else:
                    converted['watched'].append({'title': movie, 'imdb_id': None, 'added_by': None, 'added_username': None, 'ratings': {}})
            for movie in data.get('want_to_watch', []):
                if isinstance(movie, dict):
                    # Ensure new fields exist for backwards compatibility
                    movie['added_by'] = movie.get('added_by')
                    movie['added_username'] = movie.get('added_username')
                    movie['ratings'] = movie.get('ratings', {})
                    converted['want_to_watch'].append(movie)
                else:
                    converted['want_to_watch'].append({'title': movie, 'imdb_id': None, 'added_by': None, 'added_username': None, 'ratings': {}})
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

        # If no commands synced, clear and retry
        if len(synced) == 0:
            print('No commands synced, clearing and retrying...')
            bot.tree.clear_commands(guild=None)
            await asyncio.sleep(1)
            synced = await bot.tree.sync()
            print(f'Retry synced {len(synced)} commands: {[cmd.name for cmd in synced]}')
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

    # Add movie with IMDb ID and user info
    imdb_id = movie_info.get('imdb_id') if movie_info else None
    movies['watched'].append({
        'title': actual_name,
        'imdb_id': imdb_id,
        'added_by': str(interaction.user.id),
        'added_username': interaction.user.name
    })
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

    # Add movie with IMDb ID and user info
    imdb_id = movie_info.get('imdb_id') if movie_info else None
    movies['want_to_watch'].append({
        'title': actual_name,
        'imdb_id': imdb_id,
        'added_by': str(interaction.user.id),
        'added_username': interaction.user.name
    })
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


async def movie_name_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocomplete movie names from the movie lists"""
    movies = load_movies()
    all_movies = []

    # Collect all movie titles from both lists
    for movie in movies['watched'] + movies['want_to_watch']:
        title = movie.get('title') if isinstance(movie, dict) else movie
        if title:
            all_movies.append(title)

    # Filter by current input and return up to 25 choices
    if current:
        all_movies = [m for m in all_movies if current.lower() in m.lower()]

    return [app_commands.Choice(name=movie, value=movie) for movie in sorted(all_movies)[:25]]


@bot.tree.command(name='movie_info', description='Get IMDb info about a movie')
@app_commands.check(is_allowed_channel)
@app_commands.autocomplete(movie_name=movie_name_autocomplete)
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

        # Get local ratings from our database
        movies = load_movies()
        local_ratings = {}

        def get_title(m):
            return m.get('title') if isinstance(m, dict) else m

        for movie in movies['watched'] + movies['want_to_watch']:
            if get_title(movie).lower() == movie_name.lower():
                local_ratings = movie.get('ratings', {})
                break

        if local_ratings:
            avg = get_rating_avg(local_ratings)
            stars = get_star_display(avg)
            embed.add_field(name="Community Rating", value=f"{stars} from {len(local_ratings)} user(s)", inline=False)

            # Show each user's rating
            ratings_lines = []
            for user_id, rating in local_ratings.items():
                username = rating.get('username', 'Unknown') if isinstance(rating, dict) else 'Unknown'
                rating_val = rating.get('rating', rating) if isinstance(rating, dict) else rating
                ratings_lines.append(f"• {username}: {rating_val}/5")
            embed.add_field(name="User Ratings", value="\n".join(ratings_lines), inline=False)

        embed.set_footer(text=f"IMDb ID: {movie_data['imdb_id']}")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f'❌ Movie "{movie_name}" not found on IMDb!')


async def movie_name_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocomplete movie names from the movie lists"""
    movies = load_movies()
    all_movies = []

    # Collect all movie titles from both lists
    for movie in movies['watched'] + movies['want_to_watch']:
        title = movie.get('title') if isinstance(movie, dict) else movie
        if title:
            all_movies.append(title)

    # Filter by current input and return up to 25 choices
    if current:
        all_movies = [m for m in all_movies if current.lower() in m.lower()]

    return [app_commands.Choice(name=movie, value=movie) for movie in sorted(all_movies)[:25]]


@bot.tree.command(name='rate', description='Rate a movie (0-5 stars)')
@app_commands.check(is_allowed_channel)
@app_commands.autocomplete(movie_name=movie_name_autocomplete)
@app_commands.describe(rating="Rating from 0 to 5 (decimals allowed, 0 to remove)")
async def rate(interaction: discord.Interaction, movie_name: str, rating: float = None, user: discord.User = None):
    """Rate a movie from 0 to 5 stars (0 removes your rating) - only works on watched movies"""
    # If user is specified, only admins can use it
    if user and not is_admin(interaction):
        await interaction.response.send_message('❌ Only admins can remove other users\' ratings!')
        return

    movies = load_movies()

    # Determine whose rating to modify
    if user:
        target_id = str(user.id)
        target_name = user.name
    else:
        target_id = str(interaction.user.id)
        target_name = interaction.user.name

    def get_title(movie):
        return movie.get('title') if isinstance(movie, dict) else movie

    # Check if movie is in want_to_watch - can't rate from there
    want_titles = [get_title(m).lower() for m in movies['want_to_watch']]
    if movie_name.lower() in want_titles:
        await interaction.response.send_message('❌ You can only rate movies in your watched list! Move it to watched first to rate.')
        return

    # Search only in watched list
    found = False

    for movie in movies['watched']:
        if get_title(movie).lower() == movie_name.lower():
            if 'ratings' not in movie:
                movie['ratings'] = {}

            if rating == 0 or rating is None:
                # Remove rating
                if target_id in movie['ratings']:
                    del movie['ratings'][target_id]
            else:
                movie['ratings'][target_id] = {"rating": rating, "username": target_name}

            found = True
            break

    if found:
        save_movies(movies)

        # Handle removal case
        if rating == 0 or rating is None:
            await interaction.response.send_message(f'✅ Removed **{target_name}**\'s rating from **{movie_name}**!')
        else:
            # Calculate average
            ratings = movie.get('ratings', {})
            avg = get_rating_avg(ratings)
            await interaction.response.send_message(f'✅ Rated **{movie_name}** {rating}/5 stars! (avg: {avg:.1f})')
    else:
        await interaction.response.send_message(f'❌ "{movie_name}" not found in any list!')


@bot.tree.command(name='my_ratings', description='Show movies you have rated')
@app_commands.check(is_allowed_channel)
async def my_ratings(interaction: discord.Interaction):
    """Show all movies you have rated"""
    movies = load_movies()
    user_id = str(interaction.user.id)

    rated_movies = []

    for movie in movies['watched'] + movies['want_to_watch']:
        title = movie.get('title') if isinstance(movie, dict) else movie
        ratings = movie.get('ratings', {})
        if user_id in ratings:
            user_rating = get_rating_value(ratings[user_id])
            avg = get_rating_avg(ratings)
            rated_movies.append({
                'title': title,
                'your_rating': user_rating,
                'avg_rating': avg,
                'ratings': ratings
            })

    if not rated_movies:
        await interaction.response.send_message('📝 You haven\'t rated any movies yet!')
        return

    lines = []
    for m in sorted(rated_movies, key=lambda x: x['title']):
        stars = get_star_display(m['your_rating'])
        avg_stars = get_star_display(m['avg_rating'])
        lines.append(f"**{m['title']}** — You: {stars} | Avg: {avg_stars}")

    embed = discord.Embed(title="📊 Your Ratings", description="\n".join(lines), color=discord.Color.gold())
    embed.set_footer(text=f"You have rated {len(rated_movies)} movies")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='random_movie', description='Pick a random movie from your want to watch list')
@app_commands.check(is_allowed_channel)
async def random_movie(interaction: discord.Interaction):
    """Pick a random movie from the want to watch list"""
    await interaction.response.defer()

    movies = load_movies()

    if not movies['want_to_watch']:
        await interaction.followup.send('📋 Your want to watch list is empty! Add some movies first.')
        return

    # DEBUG: Show what we're picking from
    await interaction.followup.send(f"DEBUG - Raw want_to_watch: {movies['want_to_watch']}")
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


async def get_tmdb_similar(movie_name):
    """Get movie recommendations from TMDB based on movie name"""
    if not TMDB_API_KEY:
        return []

    try:
        # First search for the movie
        search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
        response = requests.get(search_url, timeout=5)
        data = response.json()

        if data.get('results') and len(data['results']) > 0:
            tmdb_id = data['results'][0]['id']

            # Get recommendations (movies people who liked this also watched)
            similar_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/recommendations?api_key={TMDB_API_KEY}"
            response = requests.get(similar_url, timeout=5)
            similar_data = response.json()

            if similar_data.get('results'):
                return similar_data['results'][:20]  # Return top 20
    except Exception as e:
        print(f"TMDB error: {e}")

    return []


async def get_imdb_id_from_tmdb(tmdb_id: int) -> str:
    """Get IMDb ID from TMDB ID"""
    if not TMDB_API_KEY:
        return None
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data.get('imdb_id')
    except:
        return None


@bot.tree.command(name='recommend', description='Get movie recommendations based on 1-3 movies')
@app_commands.check(is_allowed_channel)
@app_commands.autocomplete(movie1=movie_name_autocomplete, movie2=movie_name_autocomplete, movie3=movie_name_autocomplete)
@app_commands.describe(
    movie1="First movie to base recommendations on",
    movie2="Optional second movie",
    movie3="Optional third movie"
)
async def recommend(interaction: discord.Interaction, movie1: str, movie2: str = None, movie3: str = None):
    """Get movie recommendations based on 1-3 movies"""
    await interaction.response.defer()

    if not TMDB_API_KEY:
        await interaction.followup.send('❌ TMDB API not configured!')
        return

    # Collect movies to base recommendations on
    base_movies = [movie1]
    if movie2:
        base_movies.append(movie2)
    if movie3:
        base_movies.append(movie3)

    # Get similar movies for each base movie
    all_similar = {}
    titles_searched = []

    for base_movie in base_movies:
        similar = await get_tmdb_similar(base_movie)
        titles_searched.append(base_movie)

        for m in similar:
            title = m.get('title', 'Unknown')
            tmdb_id = m.get('id')
            if title not in all_similar:
                all_similar[title] = {
                    'year': m.get('release_date', '')[:4] if m.get('release_date') else 'N/A',
                    'rating': m.get('vote_average', 0),
                    'count': 0,
                    'tmdb_id': tmdb_id
                }
            all_similar[title]['count'] += 1

    if not all_similar:
        await interaction.followup.send(f'❌ Could not find recommendations for "{movie1}"')
        return

    # Sort by count (appears in more similar lists = higher rank), then by rating
    sorted_movies = sorted(all_similar.items(), key=lambda x: (x[1]['count'], x[1]['rating']), reverse=True)

    # Build the response with IMDb links
    lines = []
    for title, info in sorted_movies[:10]:
        # Fetch IMDb ID for each movie
        imdb_id = await get_imdb_id_from_tmdb(info['tmdb_id']) if info.get('tmdb_id') else None
        if imdb_id:
            imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
            lines.append(f"**[{title}]({imdb_url})** ({info['year']}) - ⭐ {info['rating']:.1f} ({info['count']}x)")
        else:
            lines.append(f"**{title}** ({info['year']}) - ⭐ {info['rating']:.1f} ({info['count']}x)")

    embed = discord.Embed(
        title=f"🎬 Recommendations based on {len(base_movies)} movie(s)",
        description="\n".join(lines),
        color=discord.Color.gold()
    )
    embed.add_field(name="Based on", value=", ".join(titles_searched), inline=False)
    embed.set_footer(text="Movies appearing in more similar lists ranked higher • Powered by TMDB")

    await interaction.followup.send(embed=embed)


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

    # Build movie list with IMDb links, ratings, and who added
    movie_lines = []
    for movie in sorted(movies['watched'], key=lambda x: x.get('title', '') if isinstance(x, dict) else x):
        title = movie.get('title') if isinstance(movie, dict) else movie
        imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
        added_username = movie.get('added_username') if isinstance(movie, dict) else None
        ratings = movie.get('ratings', {})

        # Calculate average rating
        rating_str = ""
        if ratings:
            avg = get_rating_avg(ratings)
            stars = get_star_display(avg)
            rating_str = f" {stars}"

        if imdb_id:
            movie_lines.append(f"✅ [{title}](https://www.imdb.com/title/{imdb_id}/){rating_str}" + (f" *(added by {added_username})*" if added_username else ""))
        else:
            movie_lines.append(f"✅ {title}{rating_str}" + (f" *(added by {added_username})*" if added_username else ""))

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

    # Build movie list with IMDb links, ratings, and who added
    movie_lines = []
    for movie in sorted(movies['want_to_watch'], key=lambda x: x.get('title', '') if isinstance(x, dict) else x):
        title = movie.get('title') if isinstance(movie, dict) else movie
        imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
        added_username = movie.get('added_username') if isinstance(movie, dict) else None
        ratings = movie.get('ratings', {})

        # Calculate average rating
        rating_str = ""
        if ratings:
            avg = get_rating_avg(ratings)
            stars = get_star_display(avg)
            rating_str = f" {stars}"

        if imdb_id:
            movie_lines.append(f"📝 [{title}](https://www.imdb.com/title/{imdb_id}/){rating_str}" + (f" *(added by {added_username})*" if added_username else ""))
        else:
            movie_lines.append(f"📝 {title}{rating_str}" + (f" *(added by {added_username})*" if added_username else ""))

    movie_list = '\n'.join(movie_lines)
    embed = discord.Embed(title="🎬 Want to Watch", description=movie_list, color=discord.Color.blue())
    embed.set_footer(text=f"Total: {len(movies['want_to_watch'])} movies")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='all_movies', description='Show all movies in both lists')
@app_commands.check(is_allowed_channel)
@app_commands.describe(sort_by="Sort by alphabetical or rating")
async def all_movies(interaction: discord.Interaction, sort_by: str = "alpha"):
    """Show all movies in both lists"""
    movies = load_movies()

    watched_count = len(movies['watched'])
    want_count = len(movies['want_to_watch'])

    # Sort movies
    def get_rating(movie):
        ratings = movie.get('ratings', {})
        return get_rating_avg(ratings)

    def get_sort_key(movie):
        title = movie.get('title', '') if isinstance(movie, dict) else movie
        if sort_by == "rating":
            return -get_rating(movie)  # Negative for descending order
        return title.lower()

    embed = discord.Embed(title="🎬 Movie Collection", color=discord.Color.purple())

    if movies['watched']:
        movie_lines = []
        for movie in sorted(movies['watched'], key=get_sort_key):
            title = movie.get('title') if isinstance(movie, dict) else movie
            imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
            added_username = movie.get('added_username') if isinstance(movie, dict) else None
            ratings = movie.get('ratings', {})

            # Calculate average rating
            rating_str = ""
            if ratings:
                avg = get_rating_avg(ratings)
                stars = get_star_display(avg)
                rating_str = f" {stars}"

            if imdb_id:
                movie_lines.append(f"✅ [{title}](https://www.imdb.com/title/{imdb_id}/){rating_str}" + (f" *(added by {added_username})*" if added_username else ""))
            else:
                movie_lines.append(f"✅ {title}{rating_str}" + (f" *(added by {added_username})*" if added_username else ""))
        watched_list = '\n'.join(movie_lines)
        embed.add_field(name="Watched 🎥", value=watched_list, inline=False)

    if movies['want_to_watch']:
        movie_lines = []
        for movie in sorted(movies['want_to_watch'], key=get_sort_key):
            title = movie.get('title') if isinstance(movie, dict) else movie
            imdb_id = movie.get('imdb_id') if isinstance(movie, dict) else None
            added_username = movie.get('added_username') if isinstance(movie, dict) else None
            ratings = movie.get('ratings', {})

            # Calculate average rating
            rating_str = ""
            if ratings:
                avg = get_rating_avg(ratings)
                stars = get_star_display(avg)
                rating_str = f" {stars}"

            if imdb_id:
                movie_lines.append(f"📝 [{title}](https://www.imdb.com/title/{imdb_id}/){rating_str}" + (f" *(added by {added_username})*" if added_username else ""))
            else:
                movie_lines.append(f"📝 {title}{rating_str}" + (f" *(added by {added_username})*" if added_username else ""))
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
@app_commands.check(is_admin)
async def clear_all(interaction: discord.Interaction):
    """Clear all movies - requires confirmation"""
    view = ConfirmView()
    await interaction.response.send_message('⚠️ Are you sure you want to clear all movies?', view=view)

@bot.tree.command(name='claim_movie', description='Claim a movie as added by a user')
@app_commands.check(is_allowed_channel)
@app_commands.check(is_admin)
async def claim_movie(interaction: discord.Interaction, movie_name: str, claimed_by: discord.User = None):
    """Claim a movie as added by a specific user"""
    movies = load_movies()

    def get_title(movie):
        return movie.get('title') if isinstance(movie, dict) else movie

    # Determine who to claim as
    claim_username = claimed_by.name if claimed_by else interaction.user.name
    claim_id = str(claimed_by.id) if claimed_by else str(interaction.user.id)

    # Search in both lists
    found = False

    for movie in movies['watched']:
        if get_title(movie).lower() == movie_name.lower():
            movie['added_by'] = claim_id
            movie['added_username'] = claim_username
            found = True
            break

    if not found:
        for movie in movies['want_to_watch']:
            if get_title(movie).lower() == movie_name.lower():
                movie['added_by'] = claim_id
                movie['added_username'] = claim_username
                found = True
                break

    if found:
        save_movies(movies)
        await interaction.response.send_message(f'✅ Claimed "{movie_name}" as added by **{claim_username}**!')
    else:
        await interaction.response.send_message(f'❌ "{movie_name}" not found in any list!')

    if found:
        save_movies(movies)
        await interaction.response.send_message(f'✅ Claimed "{movie_name}" as added by **{claim_username}**!')
    else:
        await interaction.response.send_message(f'❌ "{movie_name}" not found in any list!')

@bot.tree.command(name='help', description='Show available commands')
@app_commands.check(is_allowed_channel)
async def help_command(interaction: discord.Interaction):
    """Show help message"""
    embed = discord.Embed(title="🎬 Movie Tracker Bot - Commands", color=discord.Color.gold())

    # Regular commands
    regular_commands = [
        ("/add_watched <movie>", "Add a movie to watched list"),
        ("/add_want <movie>", "Add a movie to want to watch list"),
        ("/all_movies", "Show all movies in both lists"),
        ("/help", "Show this help message"),
        ("/movie_info <movie>", "Get IMDb info about a movie"),
        ("/my_ratings", "Show movies you have rated"),
        ("/random_movie", "Pick a random movie from want to watch list"),
        ("/recommend <movie1> [movie2] [movie3]", "Get recommendations based on 1-3 movies"),
        ("/rate <movie> [rating] [user]", "Rate a movie (0-5, 0 to remove, admin can target user)"),
        ("/remove_movie <movie> [watched|want]", "Remove a movie from any list"),
        ("/want_to_watch", "Show all movies in want to watch list"),
        ("/watched", "Show all watched movies"),
    ]

    for command, description in regular_commands:
        embed.add_field(name=command, value=description, inline=False)

    # Admin commands - add header as part of first command description
    admin_commands = [
        ("/claim_movie <movie> [claimed_by]", "Claim ownership of a movie"),
        ("/clear_all", "Clear all movies (requires confirmation)"),
        ("/refresh_imdb", "Update IMDb IDs for all movies"),
    ]

    # Add admin header with divider above it
    embed.add_field(name="​", value="────────────────────────────────", inline=False)
    embed.add_field(name="Admin Commands 🔧", value="​", inline=False)
    for command, description in admin_commands:
        embed.add_field(name=command, value=description, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='refresh_imdb', description='Update IMDb IDs for all movies')
@app_commands.check(is_allowed_channel)
@app_commands.check(is_admin)
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
        # Check if it's channel or admin failure
        if hasattr(error, 'original'):
            # Could be admin check failure
            await interaction.response.send_message('❌ You do not have permission to use this command.', ephemeral=True)
        else:
            await interaction.response.send_message('❌ movie-tracker-bot commands only work in movie-tracker-bot text channel', ephemeral=True)
    else:
        await interaction.response.send_message(f'❌ An error occurred: {error}', ephemeral=True)

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)