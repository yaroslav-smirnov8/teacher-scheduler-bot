# Deployment Guide

## Quick Start

### 1. Extract the archive
```bash
unzip TeacherHelper.zip
cd TeacherHelper
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure .env
Make sure your token is set correctly:
```
TELEGRAM_BOT_TOKEN="your_token_here"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/teacherhelper"
```

### 4. Run the bot
```bash
python 001n.py
```

## What the bot does

### Lesson Scheduling
- Schedule lessons for specific date and time
- Interactive calendar interface
- Conflict detection

### Reminder System 🔔

**For Students:**
- 24 hours before lesson
- 1 hour before lesson

**For Teachers:**
- Daily summary at 9:00 AM

**Optimization:**
- Checks every hour
- Minimal CPU and RAM usage
- Async processing

## Auto-start (optional)

### Linux (systemd)
```bash
sudo nano /etc/systemd/system/teacherbot.service
```

```ini
[Unit]
Description=Teacher Scheduler Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/TeacherHelper
ExecStart=/usr/bin/python3 001n.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable teacherbot
sudo systemctl start teacherbot
```

### Windows (Task Scheduler)
1. Task Scheduler → Create Basic Task
2. Trigger: At startup
3. Action: Start a program
4. Program: `python`
5. Arguments: `001n.py`
6. Start in: path to TeacherHelper

## Files

- `teacherdb.db` - created automatically
- Regularly backup `teacherdb.db`
- Keep `.env` secure

## Requirements

- Python 3.8+
- ~50 MB disk space
- Internet connection
