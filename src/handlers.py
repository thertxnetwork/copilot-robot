from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from config.settings import ALLOWED_USERS
from src.copilot import CopilotCLI
from src.formatter import create_copilot_result, format_for_telegram, split_response, parse_copilot_response
import logging
import re
import asyncio
import os

logger = logging.getLogger(__name__)

# Conversation states
WAITING_TASK, WAITING_SUGGEST, WAITING_EXPLAIN, WAITING_RUN = range(4)

# Store user context and settings
user_context = {}
user_settings = {}  # Store user preferences


def get_user_setting(user_id: int, key: str, default=True):
    """Get user setting"""
    if user_id not in user_settings:
        user_settings[user_id] = {}
    return user_settings[user_id].get(key, default)


def set_user_setting(user_id: int, key: str, value):
    """Set user setting"""
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id][key] = value


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    if not ALLOWED_USERS or not ALLOWED_USERS[0]:
        return True
    return str(user_id) in ALLOWED_USERS


def get_main_menu():
    """Get main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🤖 Agent Mode", callback_data="agent"),
            InlineKeyboardButton("💬 AI Chat", callback_data="chat")
        ],
        [
            InlineKeyboardButton("💡 Suggest Command", callback_data="suggest"),
            InlineKeyboardButton("📚 Explain Command", callback_data="explain")
        ],
        [
            InlineKeyboardButton("⚙️ Run Command", callback_data="run"),
            InlineKeyboardButton("📊 System Status", callback_data="status")
        ],
        [
            InlineKeyboardButton("📥 Download File", callback_data="download"),
            InlineKeyboardButton("🔄 Clear Agent", callback_data="clear")
        ],
        [
            InlineKeyboardButton("🔄 Clear Chat", callback_data="clear_chat"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_menu(user_id: int):
    """Get settings menu keyboard"""
    auto_approve = get_user_setting(user_id, 'auto_approve', True)
    approve_text = "✅ Auto-Approve: ON" if auto_approve else "❌ Auto-Approve: OFF"
    
    current_model = CopilotCLI.get_user_model(user_id)
    model_name = CopilotCLI.MODELS.get(current_model, current_model)
    
    keyboard = [
        [InlineKeyboardButton(approve_text, callback_data="toggle_approve")],
        [InlineKeyboardButton(f"🤖 Model: {model_name}", callback_data="model_menu")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_menu():
    """Get back to menu keyboard"""
    keyboard = [[InlineKeyboardButton("🏠 Back to Menu", callback_data="menu")]]
    return InlineKeyboardMarkup(keyboard)


def get_model_menu(user_id: int):
    """Get model selection menu"""
    current_model = CopilotCLI.get_user_model(user_id)
    
    keyboard = []
    for model_id, model_name in CopilotCLI.MODELS.items():
        prefix = "✅ " if model_id == current_model else "⚪ "
        keyboard.append([InlineKeyboardButton(
            f"{prefix}{model_name}",
            callback_data=f"set_model_{model_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings")])
    return InlineKeyboardMarkup(keyboard)





async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ *Access Denied*", parse_mode='Markdown')
        return
    
    welcome_text = """🤖 *COPILOT AI ASSISTANT*

*Available Options:*

🤖 *Agent Mode* - AI executes multi-step tasks
💬 *AI Chat* - Continuous conversation with AI
💡 *Suggest* - Get command recommendations
📚 *Explain* - Understand any command
⚙️ *Run* - Execute commands directly

📥 *Download File* - Download files from server
📊 *Status* - Monitor system resources
🔄 *Clear Agent/Chat* - Reset sessions
⚙️ *Settings* - Configure bot behavior
❓ *Help* - View detailed guide

Select an option below:"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_authorized(user_id):
        await query.message.edit_text("⛔ *Access Denied*", parse_mode='Markdown')
        return
    
    try:
        if query.data == "menu":
            await show_main_menu(query)
        elif query.data == "agent":
            await show_agent_prompt(query, context)
        elif query.data == "chat":
            await show_chat_prompt(query, context)
        elif query.data == "suggest":
            await show_suggest_prompt(query, context)
        elif query.data == "explain":
            await show_explain_prompt(query, context)
        elif query.data == "run":
            await show_run_prompt(query, context)
        elif query.data == "download":
            await show_download_prompt(query, context)
        elif query.data == "status":
            await show_status(query, context)
        elif query.data == "clear":
            await clear_session(query, context)
        elif query.data == "clear_chat":
            await clear_chat_session(query, context)
        elif query.data == "settings":
            await show_settings(query)
        elif query.data == "toggle_approve":
            await toggle_auto_approve(query)
        elif query.data == "model_menu":
            await show_model_menu(query)
        elif query.data.startswith("set_model_"):
            await set_model(query)
        elif query.data == "help":
            await show_help(query)
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        error_text = str(e).replace('`', "'")
        await query.message.edit_text(
            f"❌ *Error*\n\n```\n{error_text}\n```\n\nPlease try again.",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )


async def show_main_menu(query):
    menu_text = """🤖 *COPILOT AI ASSISTANT*

*Available Options:*

🤖 *Agent Mode* - AI executes multi-step tasks
💬 *AI Chat* - Continuous conversation with AI
💡 *Suggest* - Get command recommendations
📚 *Explain* - Understand any command
⚙️ *Run* - Execute commands directly

📥 *Download File* - Download files from server
📊 *Status* - Monitor system resources
🔄 *Clear Agent/Chat* - Reset sessions
⚙️ *Settings* - Configure bot behavior
❓ *Help* - View detailed guide

Select an option below:"""
    
    await query.message.edit_text(
        menu_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )


async def show_agent_prompt(query, context):
    user_id = query.from_user.id
    model = CopilotCLI.get_user_model(user_id)
    model_name = CopilotCLI.MODELS.get(model, model)
    
    text = f"""🤖 *AGENT MODE*
🧠 *Model:* {model_name}

AI assistant that can execute complex multi-step tasks. It can create files, run commands, and maintain context across messages.

*Examples:*
• "Create a Python web scraper"
• "Set up a Docker container for Node.js"
• "Analyze logs and fix errors"
• "Create a backup script"
• "Install and configure nginx"

📎 *You can upload files!*
💡 *Use Download File to get files from server*

*Send your task or file:*"""
    await query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_menu())
    context.user_data['waiting_for'] = 'agent'


async def show_chat_prompt(query, context):
    user_id = query.from_user.id
    model = CopilotCLI.get_user_model(user_id)
    model_name = CopilotCLI.MODELS.get(model, model)
    
    text = f"""💬 *AI CHAT*
🧠 *Model:* {model_name}

Simple conversation mode with AI. Ask questions, get explanations, or have a discussion. Messages are remembered in this session.

*Examples:*
• "Explain how Docker works"
• "What's the difference between RAM and storage?"
• "How do I improve Python code performance?"

💡 *Just keep chatting!* The conversation continues automatically.

*Send your message:*"""
    await query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_menu())
    context.user_data['waiting_for'] = 'chat'


async def show_suggest_prompt(query, context):
    text = """💡 *SUGGEST COMMAND*

Get command recommendations for your task. Describe what you want to do and get the best command suggestions.

*Examples:*
• "Find large files over 100MB"
• "Monitor CPU usage in real-time"
• "Compress a folder to tar.gz"

*What do you want to do?*"""
    await query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_menu())
    context.user_data['waiting_for'] = 'suggest'


async def show_explain_prompt(query, context):
    text = """📚 *EXPLAIN COMMAND*

Get detailed explanations of any Linux/shell command. Understand what it does, its flags, and how it works.

*Examples:*
• `docker ps -a`
• `tar -xzf file.tar.gz`
• `find . -name "*.log" -mtime +7`

*Send the command:*"""
    await query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_menu())
    context.user_data['waiting_for'] = 'explain'


async def show_run_prompt(query, context):
    text = """⚙️ *RUN COMMAND*

Execute commands directly on your server with real-time output. Dangerous commands are automatically blocked.

*Examples:*
• `ls -la /var/log`
• `ps aux | grep python`
• `df -h`

*Send the command:*"""
    await query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_menu())
    context.user_data['waiting_for'] = 'run'


async def show_download_prompt(query, context):
    text = """📥 *DOWNLOAD FILE*

Download any file from the server by providing the full path.

*Examples:*
• `/etc/nginx/nginx.conf`
• `/var/log/syslog`
• `/root/myfile.zip`
• `/tmp/backup.tar.gz`

*Maximum file size:* 500 MB

*Send the file path:*"""
    await query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_menu())
    context.user_data['waiting_for'] = 'download'


async def show_help(query):
    """Show help"""
    text = """

       ❓ *HELP GUIDE*       


*🤖 Agent Mode*
Complex multi-step tasks with AI
• Can create files and scripts
• Executes multiple commands
• Maintains session context
• *Upload files* 📎
• Just keep messaging to continue
• Use "Clear Session" for fresh start

*📎 File Upload*
Send files to Agent Mode
• Documents, images, code files
• Max size: 20 MB
• Files saved to agent workspace
• Agent can read, analyze, modify

*📥 Download File*
Download any file from server
• Use the Download File button
• Provide full file path
• Max 500 MB per file
• Progress shown during upload
• Example: /etc/nginx/nginx.conf

*💬 AI Chat*
Continuous conversation with AI
• Ask questions and get answers
• *Conversation is remembered*
• Just keep chatting naturally
• No command execution
• Use "Clear Chat" to reset
• Perfect for learning and discussion

*💡 Command Suggestions*
Get command recommendations
• Describe what you want to do
• AI suggests best commands
• Includes explanations

*📚 Explain Command*
Understand any command
• Paste any Linux command
• Get detailed breakdown
• Learn flags and options

*⚙️ Run Command*
Execute commands remotely
• Direct VPS access
• Real-time output
• Safety checks enabled

*📊 System Status*
Monitor your VPS
• CPU, Memory, Disk usage
• System uptime
• Load average

*🔄 Clear Session*
Reset agent context
• Start fresh session
• Clear all memory
• Begin new tasks

*⚙️ Settings*
Configure bot behavior
• Auto-approve prompts
• Switch AI models
• Customize preferences
"""
    await query.message.edit_text(text, parse_mode='Markdown', reply_markup=get_back_menu())


async def show_settings(query):
    """Show settings menu"""
    user_id = query.from_user.id
    auto_approve = get_user_setting(user_id, 'auto_approve', True)
    model = CopilotCLI.get_user_model(user_id)
    model_name = CopilotCLI.MODELS.get(model, model)
    
    text = "\n"
    text += "      ⚙️ *SETTINGS*         \n"
    text += "\n\n"
    text += "*Bot Configuration*\n\n"
    text += f"*Auto-Approve Prompts:* {'✅ ON' if auto_approve else '❌ OFF'}\n"
    text += "_Automatically approve copilot prompts_\n"
    text += "_(directory access, tool usage, etc.)_\n\n"
    text += f"*AI Model:* {model_name}\n"
    text += "_Select which language model to use_\n\n"
    text += "Click the buttons below to configure:"
    
    await query.message.edit_text(
        text,
        parse_mode='Markdown',
        reply_markup=get_settings_menu(user_id)
    )


async def toggle_auto_approve(query):
    """Toggle auto-approve setting"""
    user_id = query.from_user.id
    current = get_user_setting(user_id, 'auto_approve', True)
    new_value = not current
    set_user_setting(user_id, 'auto_approve', new_value)
    
    # Update settings display
    await show_settings(query)
    
    # Send notification
    status = "enabled" if new_value else "disabled"
    await query.answer(f"Auto-approve {status}!", show_alert=True)


async def show_model_menu(query):
    """Show model selection menu"""
    user_id = query.from_user.id
    
    text = "\n"
    text += "      🤖 *AI MODEL*         \n"
    text += "\n\n"
    text += "*Available Models:*\n\n"
    text += "• *Claude Sonnet 4.5* - Most capable (Default)\n"
    text += "• *Claude Sonnet 4* - Balanced performance\n"
    text += "• *Claude Haiku 4.5* - Fast and efficient\n"
    text += "• *GPT-5* - OpenAI's latest model\n\n"
    text += "_Select a model:_"
    
    await query.message.edit_text(
        text,
        parse_mode='Markdown',
        reply_markup=get_model_menu(user_id)
    )


async def set_model(query):
    """Set user's AI model"""
    user_id = query.from_user.id
    model_id = query.data.replace("set_model_", "")
    
    CopilotCLI.set_user_model(user_id, model_id)
    
    # Update model menu
    await show_model_menu(query)
    
    # Send notification
    model_name = CopilotCLI.MODELS.get(model_id, model_id)
    await query.answer(f"Model set to {model_name}!", show_alert=True)



async def show_status(query, context):
    """Show system status"""
    user_id = query.from_user.id
    
    status_msg = await query.message.edit_text(
        "\n"
        "   📊 *SYSTEM STATUS*       \n"
        "\n\n"
        "⏳ *Gathering system information...*",
        parse_mode='Markdown'
    )
    
    try:
        commands = {
            'Uptime': 'uptime -p',
            'CPU Load': 'cat /proc/loadavg | awk \'{print $1" "$2" "$3}\'',
            'Memory': 'free -h | grep Mem | awk \'{print "Used: "$3" / Total: "$2}\'',
            'Disk': 'df -h / | tail -1 | awk \'{print "Used: "$3" / Total: "$2" ("$5" full)"}\'',
            'Processes': 'ps aux | wc -l'
        }
        
        status_text = "\n"
        status_text += "   📊 *SYSTEM STATUS*       \n"
        status_text += "\n\n"
        
        for name, cmd in commands.items():
            result = await CopilotCLI.execute_command(cmd, timeout=5)
            if result['success']:
                value = result['output'].strip()
                status_text += f"*{name}:*\n`{value}`\n\n"
            else:
                status_text += f"*{name}:* ❌ Error\n\n"
        
        status_text += "_Updated: " + "now" + "_"
        
        await status_msg.edit_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        error_text = str(e).replace('`', "'")
        await status_msg.edit_text(
            f"❌ *Error gathering status*\n\n```\n{error_text}\n```",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )


async def clear_session(query, context):
    """Clear agent session"""
    user_id = query.from_user.id
    CopilotCLI.clear_session(user_id)
    
    await query.message.edit_text(
        "\n"
        "   🔄 *SESSION CLEARED*     \n"
        "\n\n"
        "✅ Agent session has been reset\n\n"
        "_You can now start fresh with new tasks_",
        parse_mode='Markdown',
        reply_markup=get_back_menu()
    )


async def clear_chat_session(query, context):
    """Clear chat session"""
    user_id = query.from_user.id
    CopilotCLI.clear_chat_session(user_id)
    
    # Clear waiting state
    context.user_data['waiting_for'] = None
    
    await query.message.edit_text(
        "\n"
        "   🔄 *CHAT CLEARED*        \n"
        "\n\n"
        "✅ Chat session has been reset\n\n"
        "_Conversation history cleared_",
        parse_mode='Markdown',
        reply_markup=get_back_menu()
    )



async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /suggest command"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a query.\n\nExample: /suggest how to find large files")
        return
    
    query = ' '.join(context.args)
    await update.message.reply_text(f"🤔 Thinking about: {query}...")
    
    response = await CopilotCLI.suggest(query)
    await update.message.reply_text(f"💡 Suggestion:\n\n```\n{response}\n```", parse_mode='Markdown')


async def explain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /explain command"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a command to explain.\n\nExample: /explain docker ps -a")
        return
    
    command = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Analyzing: `{command}`...", parse_mode='Markdown')
    
    response = await CopilotCLI.explain(command)
    await update.message.reply_text(f"📚 Explanation:\n\n{response}")


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /run command"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a command to run.\n\nExample: /run ls -la")
        return
    
    command = ' '.join(context.args)
    
    # Security warning for dangerous commands
    dangerous_keywords = ['rm -rf', 'mkfs', 'dd if=', '> /dev/', 'format', 'shutdown', 'reboot']
    if any(keyword in command.lower() for keyword in dangerous_keywords):
        await update.message.reply_text("⚠️ This command appears dangerous. Execution blocked for safety.")
        return
    
    await update.message.reply_text(f"⚙️ Executing: `{command}`...", parse_mode='Markdown')
    
    response = await CopilotCLI.run_shell_command(command, timeout=60)
    
    # Split long responses
    if len(response) > 4000:
        chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for chunk in chunks:
            await update.message.reply_text(f"```\n{chunk}\n```", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"```\n{response}\n```", parse_mode='Markdown')


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE, from_button: bool = False):
    """Handle the /status command"""
    if not is_authorized(update.effective_user.id):
        message = update.callback_query.message if from_button else update.message
        await message.reply_text("⛔ You are not authorized to use this bot.")
        return
    
    message = update.callback_query.message if from_button else update.message
    await message.reply_text("📊 Checking system status...")
    
    commands = {
        'uptime': 'uptime',
        'disk': 'df -h /',
        'memory': 'free -h',
        'load': 'cat /proc/loadavg'
    }
    
    status_text = "🖥️ *System Status*\n\n"
    
    for name, cmd in commands.items():
        result = await CopilotCLI.run_shell_command(cmd, timeout=10)
        status_text += f"*{name.capitalize()}:*\n```\n{result}\n```\n"
    
    # Split if too long
    if len(status_text) > 4000:
        chunks = [status_text[i:i+4000] for i in range(0, len(status_text), 4000)]
        for chunk in chunks:
            await message.reply_text(chunk, parse_mode='Markdown')
    else:
        await message.reply_text(status_text, parse_mode='Markdown')


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands"""
    await update.message.reply_text(
        "❓ *Unknown command*\n\nPlease use the menu buttons or /start",
        parse_mode='Markdown',
        reply_markup=get_main_menu()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on conversation state"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ *Access Denied*", parse_mode='Markdown')
        return
    
    waiting_for = context.user_data.get('waiting_for')
    
    if not waiting_for:
        # Check if user has an active agent session
        if user_id in CopilotCLI.sessions:
            # User has active agent session, continue it automatically
            await process_agent(update, context, update.message.text.strip(), continue_session=True)
        elif user_id in CopilotCLI.chat_sessions:
            # User has active chat session, continue it automatically
            await process_chat(update, context, update.message.text.strip(), continue_session=True)
        else:
            # No active task, show menu
            await update.message.reply_text(
                "Please use the menu buttons to select an action:",
                reply_markup=get_main_menu()
            )
        return
    
    text = update.message.text.strip()
    
    try:
        if waiting_for == 'agent':
            await process_agent(update, context, text, continue_session=False)
        elif waiting_for == 'chat':
            await process_chat(update, context, text, continue_session=False)
        elif waiting_for == 'suggest':
            await process_suggest(update, context, text)
        elif waiting_for == 'explain':
            await process_explain(update, context, text)
        elif waiting_for == 'run':
            await process_run(update, context, text)
        elif waiting_for == 'download':
            await process_download(update, context, text)
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        error_text = str(e).replace('`', "'")
        await update.message.reply_text(
            f"❌ *Error*\n\n```\n{error_text}\n```\n\nPlease try again.",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
    finally:
        # Don't clear waiting_for if it's agent or chat (to allow continuous conversation)
        if waiting_for not in ['agent', 'chat']:
            context.user_data['waiting_for'] = None


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads"""
    user_id = update.effective_user.id
    
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ *Access Denied*", parse_mode='Markdown')
        return
    
    waiting_for = context.user_data.get('waiting_for')
    
    # Only accept files in agent mode or if user has active session
    if waiting_for != 'agent' and user_id not in CopilotCLI.sessions:
        await update.message.reply_text(
            "📎 *File Upload*\n\n"
            "Files can only be processed in *Agent Mode*.\n\n"
            "Please select 🤖 Agent Mode from the menu first.",
            parse_mode='Markdown',
            reply_markup=get_main_menu()
        )
        return
    
    status_msg = await update.message.reply_text(
        "📎 *Processing File...*\n\n⏳ Downloading file...",
        parse_mode='Markdown'
    )
    
    try:
        # Get file object
        if update.message.document:
            file = await update.message.document.get_file()
            file_name = update.message.document.file_name
            file_size = update.message.document.file_size
        elif update.message.photo:
            file = await update.message.photo[-1].get_file()
            file_name = f"photo_{file.file_id}.jpg"
            file_size = update.message.photo[-1].file_size
        elif update.message.video:
            file = await update.message.video.get_file()
            file_name = update.message.video.file_name or f"video_{file.file_id}.mp4"
            file_size = update.message.video.file_size
        elif update.message.audio:
            file = await update.message.audio.get_file()
            file_name = update.message.audio.file_name or f"audio_{file.file_id}.mp3"
            file_size = update.message.audio.file_size
        else:
            await status_msg.edit_text("❌ Unsupported file type", parse_mode='Markdown')
            return
        
        # Check file size (limit to 20MB)
        if file_size and file_size > 20 * 1024 * 1024:
            await status_msg.edit_text(
                "❌ *File Too Large*\n\n"
                f"File size: {file_size / 1024 / 1024:.1f} MB\n"
                "Maximum allowed: 20 MB",
                parse_mode='Markdown',
                reply_markup=get_back_menu()
            )
            return
        
        # Download file to agent workspace
        workspace = f"/tmp/copilot_agent_{user_id}"
        os.makedirs(workspace, exist_ok=True)
        
        file_path = os.path.join(workspace, file_name)
        await file.download_to_drive(file_path)
        
        await status_msg.edit_text(
            f"📎 *File Received*\n\n"
            f"*Name:* `{file_name}`\n"
            f"*Size:* {file_size / 1024:.1f} KB\n"
            f"*Location:* `{file_path}`\n\n"
            "✅ File saved to agent workspace!\n\n"
            "_Send a message to tell the agent what to do with this file._",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
        
        # Set waiting for agent if not already set
        if waiting_for != 'agent':
            context.user_data['waiting_for'] = 'agent'
            
    except Exception as e:
        logger.error(f"Error handling file: {e}")
        error_text = str(e).replace('`', "'")
        await status_msg.edit_text(
            f"❌ *Error Processing File*\n\n```\n{error_text}\n```",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )


async def process_agent(update: Update, context: ContextTypes.DEFAULT_TYPE, task: str, continue_session: bool):
    """Process agent task with live streaming updates"""
    user_id = update.effective_user.id
    
    # Initial status message
    status_msg = await update.message.reply_text(
        "\n"
        "   🤖 *AGENT PROCESSING*    \n"
        "\n\n"
        f"*Task:* {task}\n\n"
        "⏳ *Status:* Initializing agent...",
        parse_mode='Markdown'
    )
    
    # Track actions and last update time
    actions_list = []
    last_update_time = [asyncio.get_event_loop().time()]  # Use list to make it mutable in closure
    current_content = [""]
    
    async def stream_callback(event_type: str, data: str, all_data: list):
        """Callback for streaming updates"""
        nonlocal actions_list, last_update_time, current_content
        
        current_time = asyncio.get_event_loop().time()
        
        # Update every 2 seconds or on action
        if event_type == 'action' or (current_time - last_update_time[0]) > 2:
            try:
                if event_type == 'action':
                    actions_list.append(data.replace('✓', '✅'))
                else:
                    current_content[0] = data
                
                # Build live update message
                live_msg = "\n"
                live_msg += "   🤖 *AGENT WORKING...*    \n"
                live_msg += "\n\n"
                live_msg += f"*Task:* {task}\n\n"
                
                if actions_list:
                    live_msg += "*🔄 Live Progress:*\n"
                    # Show last 5 actions
                    for action in actions_list[-5:]:
                        live_msg += f"{action}\n"
                    
                    if len(actions_list) > 5:
                        live_msg += f"\n_...and {len(actions_list) - 5} more actions_\n"
                
                if current_content[0]:
                    live_msg += f"\n💬 {current_content[0][:100]}..."
                
                await status_msg.edit_text(
                    live_msg,
                    parse_mode='Markdown'
                )
                last_update_time[0] = current_time
                
            except Exception as e:
                # Ignore edit errors (message not modified)
                if "message is not modified" not in str(e).lower():
                    logger.debug(f"Stream update error: {e}")
    
    try:
        # Execute agent with streaming
        auto_approve = get_user_setting(user_id, 'auto_approve', True)
        
        result = await CopilotCLI.agent_mode_streaming(
            user_id, 
            task, 
            stream_callback, 
            continue_session=continue_session,
            auto_approve=auto_approve
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Unknown error'))
        
        response = result['output']
        
        # Parse final response
        actions, content, stats, commands = parse_copilot_response(response)
        
        # Create final formatted result
        result_text = "\n"
        result_text += "   ✅ *AGENT COMPLETED*     \n"
        result_text += "\n\n"
        result_text += f"*Task:* {task}\n\n"
        
        # Add actions performed
        if actions or actions_list:
            result_text += "*Actions Completed:*\n"
            final_actions = actions_list if actions_list else actions.replace('✓', '✅').split('\n')
            for action in final_actions[:8]:  # Show first 8 actions
                if action.strip():
                    result_text += f"{action}\n"
            if len(final_actions) > 8:
                result_text += f"_...and {len(final_actions) - 8} more_\n"
            result_text += "\n"
        
        # Add commands executed in quote blocks
        if commands:
            result_text += "*Commands Executed:*\n"
            for cmd_info in commands[:5]:  # Show first 5 commands
                lines = cmd_info.split('\n')
                for line in lines:
                    if line.startswith('$'):
                        # Command line in quote
                        cmd = line[1:].strip()
                        result_text += f"> `$ {cmd}`\n"
                    elif line.startswith('↪'):
                        # Output indicator
                        output = line[1:].strip()
                        result_text += f"> _{output}_\n"
            result_text += "\n"
        
        # Add content with proper markdown formatting
        if content:
            try:
                formatted_content = format_for_telegram(content, truncate=1800)
                result_text += f"{formatted_content}\n\n"
            except Exception as e:
                logger.error(f"Error formatting content: {e}")
                # Use plain text if formatting fails
                plain_content = content[:1800].replace('`', "'").replace('*', '').replace('_', '')
                result_text += f"{plain_content}\n\n"
        
        # Add stats
        if stats:
            duration_match = re.search(r'Total duration \(wall\): ([\d.]+s)', stats)
            if duration_match:
                result_text += f"⏱️ Completed in: {duration_match.group(1)}\n"
        
        # Add session continuation hint
        result_text += "\n💬 Just send another message to continue this session"
        
        # Send final result
        try:
            await status_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=get_back_menu()
            )
        except Exception as e:
            # If markdown parsing fails, try without parse_mode
            logger.warning(f"Markdown parse error: {e}")
            try:
                # Remove all markdown formatting
                plain_text = result_text.replace('*', '').replace('_', '').replace('`', "'")
                await status_msg.edit_text(
                    plain_text,
                    reply_markup=get_back_menu()
                )
            except Exception as e2:
                # If still fails, split it
                logger.warning(f"Message too long, splitting: {e2}")
                chunks = split_response(result_text, max_length=3500)
                plain_chunk = chunks[0].replace('*', '').replace('_', '').replace('`', "'")
                await status_msg.edit_text(
                    plain_chunk,
                    reply_markup=get_back_menu()
                )
                for chunk in chunks[1:]:
                    plain_chunk = chunk.replace('*', '').replace('_', '').replace('`', "'")
                    await update.message.reply_text(plain_chunk)
        
        # Check if user is asking for files to be sent
        # Commenting out auto file sending - let agent handle it explicitly
        # if any(keyword in task.lower() for keyword in ['send me', 'send the', 'send file', 'zip and send', 'download']):
        #     await send_requested_files(update, user_id)
                
    except Exception as e:
        logger.error(f"Agent error: {e}")
        error_text = str(e).replace('`', "'").replace('*', '').replace('_', '')
        await status_msg.edit_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "│   ❌ TASK FAILED         │\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Task: {task}\n\n"
            f"Error:\n{error_text}",
            reply_markup=get_back_menu()
        )


async def process_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """Process suggest query with live updates"""
    user_id = update.effective_user.id
    
    status_msg = await update.message.reply_text(
        "\n"
        "   💡 *ANALYZING QUERY*     \n"
        "\n\n"
        f"*Query:* {query}\n\n"
        "⏳ *Processing...*",
        parse_mode='Markdown'
    )
    
    try:
        response = await CopilotCLI.suggest(query, user_id)
        
        # Format the response properly
        formatted_response = format_for_telegram(response, truncate=3000)
        
        result_text = "\n"
        result_text += "   💡 *SUGGESTION*          \n"
        result_text += "\n\n"
        result_text += f"*Query:* {query}\n\n"
        result_text += f"{formatted_response}"
        
        await status_msg.edit_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
    except Exception as e:
        logger.error(f"Suggest error: {e}")
        error_text = str(e).replace('`', "'")
        await status_msg.edit_text(
            f"❌ *Error*\n\n```\n{error_text}\n```",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )


async def process_explain(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    """Process explain command with live updates"""
    user_id = update.effective_user.id
    
    status_msg = await update.message.reply_text(
        "\n"
        "   📚 *ANALYZING COMMAND*   \n"
        "\n\n"
        f"*Command:* `{command}`\n\n"
        "⏳ *Processing...*",
        parse_mode='Markdown'
    )
    
    try:
        response = await CopilotCLI.explain(command, user_id)
        
        # Format the explanation properly
        formatted_response = format_for_telegram(response, truncate=3000)
        
        result_text = "\n"
        result_text += "   📚 *EXPLANATION*         \n"
        result_text += "\n\n"
        result_text += f"*Command:* `{command}`\n\n"
        result_text += f"{formatted_response}"
        
        await status_msg.edit_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
    except Exception as e:
        logger.error(f"Explain error: {e}")
        error_text = str(e).replace('`', "'")
        await status_msg.edit_text(
            f"❌ *Error*\n\n```\n{error_text}\n```",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )


async def process_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, continue_session: bool = False):
    """Process AI chat message"""
    user_id = update.effective_user.id
    model = CopilotCLI.get_user_model(user_id)
    model_name = CopilotCLI.MODELS.get(model, model)
    
    status_msg = await update.message.reply_text(
        "💬 *Thinking...*",
        parse_mode='Markdown'
    )
    
    try:
        response = await CopilotCLI.ai_chat(user_id, message, continue_session=continue_session)
        
        # Format the response properly
        formatted_response = format_for_telegram(response, truncate=3500)
        
        # Create result with reply options
        result_text = f"💬 {formatted_response}"
        
        # Create inline keyboard for actions
        keyboard = [
            [InlineKeyboardButton("🔄 Clear Chat", callback_data="clear_chat")],
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await status_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            # If markdown fails, send as plain text
            logger.warning(f"Markdown error in chat: {e}")
            plain_text = result_text.replace('*', '').replace('_', '').replace('`', "'")
            await status_msg.edit_text(
                plain_text,
                reply_markup=reply_markup
            )
        
        # Keep chat session active
        if not continue_session:
            context.user_data['waiting_for'] = 'chat'
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        error_text = str(e).replace('`', "'")
        await status_msg.edit_text(
            f"❌ Error\n\n{error_text}",
            reply_markup=get_back_menu()
        )



async def process_run(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    """Process run command with live updates and safety checks"""
    # Security check
    dangerous_keywords = ['rm -rf', 'mkfs', 'dd if=', '> /dev/', 'format', 'shutdown', 'reboot', 'init 0', 'init 6', 'poweroff', 'halt']
    if any(keyword in command.lower() for keyword in dangerous_keywords):
        await update.message.reply_text(
            "\n"
            "   ⚠️ *BLOCKED*             \n"
            "\n\n"
            "*Reason:* Dangerous command detected\n\n"
            f"*Command:* `{command}`\n\n"
            "This command has been blocked for safety.",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
        return
    
    status_msg = await update.message.reply_text(
        "\n"
        "   ⚙️ *EXECUTING*           \n"
        "\n\n"
        f"*Command:* `{command}`\n\n"
        "⏳ *Status:* Executing...",
        parse_mode='Markdown'
    )
    
    try:
        response = await CopilotCLI.run_shell_command(command, timeout=60)
        
        result_text = "\n"
        result_text += "   ✅ *EXECUTION COMPLETE*  \n"
        result_text += "\n\n"
        result_text += f"*Command:* `{command}`\n\n"
        result_text += f"```\n{response[:3800] if len(response) > 3800 else response}\n```"
        
        await status_msg.edit_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
        
        if len(response) > 3800:
            chunks = [response[i:i+4000] for i in range(3800, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(f"```\n{chunk}\n```", parse_mode='Markdown')
                
    except Exception as e:
        logger.error(f"Run error: {e}")
        error_text = str(e).replace('`', "'")
        await status_msg.edit_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "│   ❌ EXECUTION FAILED    │\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Command: `{command}`\n\n"
            f"Error:\n```\n{error_text}\n```",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )


async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    """Process file download with progress updates"""
    file_path = file_path.strip()
    
    # Initial status message
    status_msg = await update.message.reply_text(
        "\n"
        "   📥 *DOWNLOADING FILE*     \n"
        "\n\n"
        f"*Path:* `{file_path}`\n\n"
        "⏳ *Status:* Checking file...",
        parse_mode='Markdown'
    )
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            await status_msg.edit_text(
                "\n"
                "   ❌ *FILE NOT FOUND*      \n"
                "\n\n"
                f"*Path:* `{file_path}`\n\n"
                "The file does not exist on the server.",
                parse_mode='Markdown',
                reply_markup=get_back_menu()
            )
            return
        
        # Check if it's a file (not a directory)
        if not os.path.isfile(file_path):
            await status_msg.edit_text(
                "\n"
                "   ❌ *NOT A FILE*          \n"
                "\n\n"
                f"*Path:* `{file_path}`\n\n"
                "The path is a directory, not a file.",
                parse_mode='Markdown',
                reply_markup=get_back_menu()
            )
            return
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        # Check file size (500MB limit)
        max_size = 500 * 1024 * 1024  # 500 MB
        if file_size > max_size:
            await status_msg.edit_text(
                "\n"
                "   ❌ *FILE TOO LARGE*      \n"
                "\n\n"
                f"*Path:* `{file_path}`\n"
                f"*Size:* {file_size / 1024 / 1024:.2f} MB\n\n"
                "*Maximum allowed:* 500 MB\n\n"
                "_Please compress or split the file._",
                parse_mode='Markdown',
                reply_markup=get_back_menu()
            )
            return
        
        # Update status - preparing to send
        await status_msg.edit_text(
            "\n"
            "   📥 *DOWNLOADING FILE*     \n"
            "\n\n"
            f"*File:* `{file_name}`\n"
            f"*Size:* {file_size / 1024:.2f} KB\n"
            f"*Path:* `{file_path}`\n\n"
            "⏳ *Status:* Preparing file...",
            parse_mode='Markdown'
        )
        
        # Send the file
        with open(file_path, 'rb') as f:
            # Update status - uploading
            await status_msg.edit_text(
                "\n"
                "   📤 *UPLOADING*           \n"
                "\n\n"
                f"*File:* `{file_name}`\n"
                f"*Size:* {file_size / 1024:.2f} KB\n\n"
                "⏳ *Status:* Uploading to Telegram...",
                parse_mode='Markdown'
            )
            
            caption = f"📄 {file_name}\n💾 Size: {file_size / 1024:.2f} KB\n📂 Path: {file_path}"
            
            await update.message.reply_document(
                document=f,
                filename=file_name,
                caption=caption
            )
        
        # Update status - complete
        await status_msg.edit_text(
            "\n"
            "   ✅ *DOWNLOAD COMPLETE*   \n"
            "\n\n"
            f"*File:* `{file_name}`\n"
            f"*Size:* {file_size / 1024:.2f} KB\n"
            f"*Path:* `{file_path}`\n\n"
            "✅ File sent successfully!",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        error_text = str(e).replace('`', "'")
        await status_msg.edit_text(
            "\n"
            "   ❌ *DOWNLOAD FAILED*     \n"
            "\n\n"
            f"*Path:* `{file_path}`\n\n"
            f"*Error:* {error_text}",
            parse_mode='Markdown',
            reply_markup=get_back_menu()
        )
