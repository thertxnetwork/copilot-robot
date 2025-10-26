# 🤖 GitHub Copilot CLI Telegram Bot

A powerful Telegram bot that brings GitHub Copilot CLI to your fingertips! Execute AI-powered tasks, have intelligent conversations, and manage your VPS—all from Telegram.

## ✨ Features

- 🤖 **AI Agent Mode** - Multi-step task automation with session persistence
- 💬 **AI Chat** - Continuous conversation with context memory
- 💡 **Command Suggestions** - Get smart command recommendations
- 📚 **Command Explanations** - Understand any shell command
- ⚙️ **Remote Execution** - Run commands safely on your VPS
- 📎 **File Upload Support** - Process files in Agent Mode (max 20MB)
- 🧠 **Model Switching** - Choose between Claude Sonnet 4.5, Claude Sonnet 4, Claude Haiku 4.5, or GPT-5
- 📊 **System Monitoring** - Real-time VPS resource monitoring
- 🎯 **Intuitive UI** - Beautiful inline keyboard menu
- 🔒 **Security** - User authorization and dangerous command blocking
- ⚙️ **Customizable** - Auto-approve settings and model preferences

## 🎮 Usage

Simply send `/start` to the bot and use the interactive menu! All features are accessible through beautifully designed buttons.

### 🤖 Agent Mode
Execute complex, multi-step tasks with AI:
- Create scripts and files
- Analyze and modify code
- Set up systems and services
- Process uploaded files
- Maintains conversation context

**Examples:**
```
"Create a Python web scraper for news articles"
"Analyze this log file and fix the errors" (+ upload file)
"Set up a Docker container for Node.js app"
"Create a monitoring script for CPU and memory"
```

### 💬 AI Chat
Have natural conversations with AI:
- Ask technical questions
- Get explanations and tutorials
- Discuss programming concepts
- Conversation history is remembered
- No command execution (safe mode)

**Examples:**
```
"Explain how Docker networking works"
"What's the difference between async and sync in Python?"
"How do I optimize MySQL queries?"
```

### 📎 File Upload
Upload files directly in Agent Mode:
- Drag and drop files to bot
- Supports documents, images, code, logs
- Max 20 MB per file
- Files saved to agent workspace
- Tell the agent what to do with the file

### ⚙️ Other Features
- **Command Suggestions** - Describe what you want, get the command
- **Command Explanations** - Paste any command for detailed breakdown
- **Run Command** - Execute with real-time output
- **System Status** - Monitor CPU, RAM, disk, uptime
- **Settings** - Auto-approve, model selection

## 🚀 Installation

### Prerequisites
- Python 3.8+
- GitHub Copilot CLI (`npm install -g @githubnext/github-copilot-cli`)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Setup

1. **Clone the repository:**
```bash
git clone https://github.com/thertxnetwork/copilot-robot.git
cd copilot-robot
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
nano .env  # Edit with your tokens
```

Required variables:
```env
BOT_TOKEN=your_telegram_bot_token
GITHUB_TOKEN=your_github_token  # Optional
ALLOWED_USERS=123456789  # Comma-separated user IDs, empty = allow all
```

5. **Run the bot:**
```bash
python main.py
```

### 🐧 Running as System Service (Linux)

Create service file `/etc/systemd/system/copilot-bot.service`:
```ini
[Unit]
Description=GitHub Copilot Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/copilot-robot
Environment="PATH=/root/copilot-robot/venv/bin"
ExecStart=/root/copilot-robot/venv/bin/python /root/copilot-robot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable copilot-bot
sudo systemctl start copilot-bot
```

## 📋 Service Management

```bash
# Check status
sudo systemctl status copilot-bot

# Restart bot
sudo systemctl restart copilot-bot

# Stop bot
sudo systemctl stop copilot-bot

# View logs
sudo journalctl -u copilot-bot -f
```

## 🔒 Security

- **User Authorization**: Restrict access to specific Telegram user IDs
- **Dangerous Command Blocking**: Automatically blocks destructive commands (rm -rf, format, etc.)
- **File Size Limits**: Maximum 20MB uploads
- **Isolated Workspaces**: Each user gets their own workspace
- **No Secrets in Code**: All sensitive data in environment variables

Configure authorized users in `.env`:
```env
ALLOWED_USERS=123456789,987654321
# Leave empty to allow all users (not recommended for production)
```

## 🧠 AI Models

Choose from multiple AI models in Settings:

| Model | Description | Use Case |
|-------|-------------|----------|
| **Claude Sonnet 4.5** | Most capable (Default) | Complex tasks, analysis |
| **Claude Sonnet 4** | Balanced performance | General purpose |
| **Claude Haiku 4.5** | Fast and efficient | Quick responses |
| **GPT-5** | OpenAI's latest | Alternative option |

## 📂 Project Structure

```
copilot-robot/
├── main.py                 # Entry point
├── config/
│   └── settings.py        # Configuration
├── src/
│   ├── bot.py            # Bot initialization
│   ├── handlers.py       # Message & button handlers
│   ├── copilot.py        # Copilot CLI interface
│   └── formatter.py      # Response formatting
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (create from .env.example)
└── README.md             # This file
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use this project for personal or commercial purposes.

## 🙏 Credits

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Powered by [GitHub Copilot CLI](https://github.com/github/gh-copilot)

## ⚠️ Disclaimer

This bot executes commands on your server. Use with caution and only grant access to trusted users. Always review commands before execution in production environments.

---

Made with ❤️ by RTX Network
