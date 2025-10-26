# GitHub Copilot CLI Telegram Bot

Control GitHub Copilot CLI and execute commands on your VPS from Telegram with AI Agent Mode!

## Features

- 🤖 **AI Agent Mode** - Multi-step task automation with session persistence
- 💡 Get command suggestions from GitHub Copilot
- 📚 Explain shell commands
- ⚙️ Execute shell commands remotely on your VPS
- 📊 Check system status
- 🎯 Inline keyboard menu for easy navigation
- 🔒 User authorization support

## Commands

### Agent Mode (NEW!)
- `/agent <task>` - Start AI agent for complex multi-step tasks
- `/agentc <task>` - Continue previous agent session
- `/clear` - Clear agent session and start fresh

### Regular Commands
- `/start` - Show menu and get your user ID
- `/help` - Show help message
- `/suggest <query>` - Get command suggestions
- `/explain <command>` - Explain a command
- `/run <command>` - Execute command on VPS
- `/status` - Check system status

## Agent Mode Examples

The agent can perform complex, multi-step tasks:

```bash
/agent analyze disk usage and create cleanup script
/agent find all log files older than 30 days and compress them
/agent create a monitoring script for CPU and memory
/agent setup a backup system for /var/www
```

## Quick Setup

```bash
cd /root/copilot-telegram-bot

# Install dependencies (already done)
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Run as service
sudo systemctl start copilot-bot
sudo systemctl status copilot-bot
```

## Service Management

```bash
sudo systemctl status copilot-bot   # Check status
sudo systemctl restart copilot-bot  # Restart bot
sudo systemctl stop copilot-bot     # Stop bot
sudo journalctl -u copilot-bot -f   # View live logs
```

## Security

⚠️ The bot is restricted to user ID: `7557962281`

To add more users, edit `.env`:
```
ALLOWED_USERS=7557962281,1234567890
```

## How It Works

**Agent Mode:**
- Creates isolated workspace per user
- Supports session continuity with `--continue`
- Can create files, run commands, and perform multi-step tasks
- Sessions persist until cleared with `/clear`

**Regular Mode:**
- Single-shot command suggestions and explanations
- Direct command execution
- System monitoring
