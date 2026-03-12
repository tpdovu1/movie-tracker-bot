# 🎬 Movie Tracker Bot

A Discord bot to manage movies you've watched and want to watch with your friends!

## Features

- ✅ **Add to Watched List** - Track movies you've already watched
- 📝 **Add to Want to Watch** - Keep a list of movies to watch later
- 🗑️ **Remove Movies** - Remove movies from any list
- 📊 **View Lists** - See your watched movies, want to watch list, or all movies at once
- 🎨 **Beautiful Embeds** - Nice formatted messages with emojis
- 💾 **Persistent Storage** - Movies are saved to a JSON file and persist between bot restarts

## Setup Instructions

### Step 1: Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "Movie Tracker Bot")
3. Go to the "Bot" section and click "Add Bot"
4. Under "TOKEN", click "Copy" to copy your bot token
5. Paste it into the `.env` file (see Step 3)

### Step 2: Set Bot Permissions

1. In Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`
3. Select permissions:
   - Send Messages
   - Embed Links
   - Read Message History
   - Add Reactions
4. Copy the generated URL and open it in your browser
5. Select the server where you want to add the bot and authorize it

### Step 3: Configure Environment Variables

1. Open `.env.example` and rename it to `.env`
2. Replace `your_discord_bot_token_here` with your actual bot token from Step 1
3. Save the file

### Step 4: Install Dependencies

Open a terminal in this folder and run:

```bash
pip install -r requirements.txt
```

### Step 5: Run the Bot

```bash
python bot.py
```

You should see a message like:

```
YourBotName#1234 has connected to Discord!
```

## Commands

### Adding Movies

- `!add_watched <movie name>` - Add a movie to your watched list
- `!add_want <movie name>` - Add a movie to your want to watch list

### Viewing Movies

- `!watched` - Show all watched movies
- `!want_to_watch` - Show all movies you want to watch
- `!all_movies` - Show all movies in both lists

### Managing Movies

- `!remove_movie <movie name>` - Remove a movie from any list
- `!clear_all` - Clear all movies (requires confirmation with emoji reaction)
- `!help` - Show all available commands

## Examples

```
!add_watched The Shawshank Redemption
!add_want Inception
!watched
!all_movies
!remove_movie The Matrix
```

## Data Storage

Movies are stored in `movies.json` automatically. You can back it up or move it between servers.

Example `movies.json`:

```json
{
  "watched": ["The Shawshank Redemption", "Inception"],
  "want_to_watch": ["Oppenheimer", "Barbie"]
}
```

## Troubleshooting

### Bot doesn't respond to commands

- Make sure the bot has permissions to send messages in the channel
- Ensure your bot token is correct in the `.env` file
- Check that you're using the correct command prefix (`!`)

### Bot is offline

- Check the terminal for error messages
- Verify your bot token is valid
- Make sure you have the `python-dotenv` package installed

### Movies not saving

- Ensure the bot has read/write permissions in the folder
- Check that `movies.json` exists (it's created automatically on first run)

## Extending the Bot

Here are some ideas for additional features:

- Add ratings/scores for movies
- Add genre tags
- Add release year filtering
- Add a "currently watching" list
- Add movie ratings from an API (IMDb, TMDB)
- Share lists between multiple Discord servers

## Support

If you encounter issues, check the terminal output for error messages. Make sure:

1. Your bot token is correct
2. The bot has proper permissions in your Discord server
3. Python 3.8+ is installed
4. All packages are installed with `pip install -r requirements.txt`
