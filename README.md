# 🤖 Telegram Trello Task Manager Bot

A Telegram bot that adds tasks to your Trello boards directly from chat messages.

## ✨ Features

- ✅ Add tasks to Trello with `/add Fix bug`
- 📋 List all your Trello boards with `/boards`
- 📊 View lists in any board with `/lists BOARD_ID`
- 🎯 Set default list with `/setlist LIST_ID`
- 🚀 Instant task creation in Trello

## 🛠️ Commands

| Command              | Description                 | Example                |
| -------------------- | --------------------------- | ---------------------- |
| `/start`             | Welcome message and help    | `/start`               |
| `/help`              | Show all commands           | `/help`                |
| `/add <task>`        | Add task to Trello          | `/add Fix login bug`   |
| `/boards`            | List all your Trello boards | `/boards`              |
| `/lists <board_id>`  | Show lists in a board       | `/lists 5f8d4e2c...`   |
| `/setlist <list_id>` | Set default list for /add   | `/setlist 5f8d4e2c...` |

## 📋 Prerequisites

- Python 3.7 or higher
- Telegram account (to create a bot)
- Trello account (free tier works)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/telegram-trello-bot.git
cd telegram-trello-bot
```
