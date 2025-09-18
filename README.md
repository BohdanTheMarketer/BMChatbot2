# Business Match Telegram Bot

Telegram bot for business networking and professional matching.

## Features

- AI-powered professional matching using custom models
- Audio summaries with ElevenLabs TTS
- Admin panel for monitoring
- 24-hour search limits
- Ukrainian language support

## Deployment on Railway

This bot is configured for deployment on Railway.com with the following files:

- `railway.json` - Railway deployment configuration
- `Procfile` - Process definition
- `runtime.txt` - Python version specification
- `nixpacks.toml` - Build configuration
- `.railwayignore` - Files to exclude from deployment

## Environment Variables

Set these environment variables in Railway:

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `OPENAI_API_KEY` - Your OpenAI API key
- `ELEVENLABS_API_KEY` - Your ElevenLabs API key

## Local Development

```bash
pip install -r requirements.txt
python3 telegram_bot_simple.py
```

## Admin Panel

Access the admin panel at `/admin` after deployment.