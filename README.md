# Telegram Movie Bot

A Python-based Telegram bot that helps users search for movies and discover available viewing and download options.

The bot uses **TMDB** to retrieve movie information and **Internet Archive** to search for available movie files.

## Features

- Search movies by title using TMDB.
- Display movie information, including:
  - Movie title
  - Release date
  - Rating
  - Overview
- Search Internet Archive for matching movie files.
- Filter available files based on their metadata and licensing information.
- Detect video quality using file metadata when available.
- Identify language information from filenames.
- Detect available subtitle files.
- Offer available viewing and download links.
- Provide an in-memory cache to reduce repeated API requests.
- Use concurrent requests to retrieve movie metadata more efficiently.
- Interactive Telegram inline keyboards for navigating movie options.

## Tech Stack

- Python 3.12+
- pyTelegramBotAPI
- Requests
- python-dotenv
- TMDB API
- Internet Archive API

## Project Structure

```text
Robat Telegram/
│
├── main.py
├── download_service.py
├── .env
├── .gitignore
└── README.md
```

## Requirements

- Python 3.12 or later
- A Telegram Bot Token
- A TMDB API Read Access Token
- Internet connection

## Installation

Clone the repository:

```cmd
git clone https://github.com/HOsouli/telegram-movie-bot.git
```

Navigate to the project directory:

```cmd
cd "Robat Telegram"
```

Create a virtual environment:

```cmd
python -m venv .venv
```

Activate the virtual environment on Windows:

```cmd
.venv\Scripts\activate
```

Install dependencies:

```cmd
pip install requests pyTelegramBotAPI python-dotenv
```

## Environment Variables

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TMDB_TOKEN=your_tmdb_api_read_access_token
```

Never commit your `.env` file or expose your API credentials.

## Running the Bot

Start the bot with:

```cmd
python main.py
```

The bot uses Telegram Long Polling to receive and process updates.

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Start the bot |
| `/help` | Display help information |
| `/membership` | Display membership options |

## Movie Search Workflow

1. The user sends a movie title.
2. The bot searches TMDB for matching movie information.
3. The user selects a movie.
4. The bot searches Internet Archive for matching items.
5. Available video files are evaluated using metadata and file information.
6. The user selects the preferred language and video quality.
7. The bot provides available viewing, download, and subtitle links.

## Performance

The project includes two basic performance improvements:

- **In-memory caching:** Movie search results are cached for 30 minutes to reduce repeated API requests.
- **Concurrent metadata retrieval:** ThreadPoolExecutor is used to retrieve metadata from multiple Internet Archive items concurrently.

## Content and Licensing

This project is intended to work with publicly accessible content that has appropriate usage and redistribution rights.

The current implementation checks licensing metadata such as Public Domain and CC0 indicators before accepting files.

However, metadata labels alone do not independently establish the legal status of a particular file. Content rights should be verified before distribution or commercial use.

TMDB is used only for movie metadata and does not provide movie video files.

## Current Limitations

- Internet Archive is currently the only integrated movie source.
- Movie availability depends on the content indexed by Internet Archive.
- Language detection is based primarily on filenames and may not always be accurate.
- Video quality detection depends on the metadata provided by the source.
- User sessions and cache are stored in memory and are lost when the bot restarts.
- Membership options are currently demonstrational; payment and subscription management are not implemented.

## Future Improvements

- Integrate additional legally authorized content sources.
- Improve movie search and title matching.
- Improve language and subtitle detection.
- Add persistent storage for user sessions and preferences.
- Implement subscription and payment management.
- Add more advanced movie filtering options.

## Author

**Hossein**

- GitHub: [HOsouli](https://github.com/HOsouli)

---

*This project is developed as a portfolio project to practice Python programming, API integration, Telegram bot development, and backend-oriented software design.*
