# ServerLimitTrackerBot

Simple Python monitor that checks machine stats once per run and sends a Telegram alert when any threshold is exceeded.

## Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies with:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your Telegram bot token and user ID.
4. Run `python monitor.py` inside the venv, or let cron execute it periodically.

## Crontab

Example to run it every 20 minutes:

```cron
*/20 * * * * cd /home/errazkin/repos/ServerLimitTrackerBot && /home/errazkin/repos/ServerLimitTrackerBot/.venv/bin/python monitor.py >> /home/errazkin/repos/ServerLimitTrackerBot/monitor.log 2>&1
```

If your virtual environment lives somewhere else, replace the path to `.venv/bin/python` with the interpreter inside that venv.

## Notes

- `TELEGRAM_USER_ID` must be a chat the bot can message.
- CPU temperature depends on sensor support from the operating system.
- Disk usage is checked per mounted filesystem and the alert includes the used percentage and free space.