# ServerLimitTrackerBot

Simple Python monitor that checks machine stats every 20 minutes and sends a Telegram alert when any threshold is exceeded.

## Setup

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in your Telegram bot token and user ID.
4. Run `python monitor.py`.

## Notes

- `TELEGRAM_USER_ID` must be a chat the bot can message.
- CPU temperature depends on sensor support from the operating system.