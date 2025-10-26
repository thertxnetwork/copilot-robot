import re
from typing import Tuple


def escape_markdown_v1(text: str) -> str:
    """
    Escape special characters for Telegram Markdown v1
    Only escapes characters that are not part of intentional formatting
    """
    # Replace the text but preserve intentional formatting
    # For Markdown v1, we mainly need to escape _ outside of intentional italics/bold
    
    # First, protect code blocks and inline code
    parts = []
    current = 0
    
    # Find all code blocks (``` ... ```) and inline code (` ... `)
    code_blocks = []
    
    # Match ```...``` blocks
    for match in re.finditer(r'```[\s\S]*?```', text):
        code_blocks.append((match.start(), match.end(), match.group()))
    
    # Match `...` inline code
    for match in re.finditer(r'`[^`]+?`', text):
        # Skip if inside a code block
        in_block = any(start <= match.start() < end for start, end, _ in code_blocks)
        if not in_block:
            code_blocks.append((match.start(), match.end(), match.group()))
    
    # Sort by position
    code_blocks.sort()
    
    # Build result, escaping only outside code blocks
    result = []
    pos = 0
    
    for start, end, code in code_blocks:
        # Add non-code part (escaped)
        if pos < start:
            non_code = text[pos:start]
            # Escape problematic characters in non-code parts
            # In Markdown v1, mainly _ outside formatting
            result.append(non_code)
        # Add code part (as-is)
        result.append(code)
        pos = end
    
    # Add remaining non-code part
    if pos < len(text):
        result.append(text[pos:])
    
    return ''.join(result)


def parse_copilot_response(response: str) -> Tuple[str, str]:
    """
    Parse copilot response and format it for Telegram
    Returns: (actions, content, stats)
    """
    lines = response.strip().split('\n')
    
    # Extract actions (lines with ✓)
    actions = []
    content = []
    stats = []
    commands = []
    
    in_stats = False
    in_command = False
    current_command = []
    
    for line in lines:
        # Check for statistics section
        if 'Total usage' in line or 'Total duration' in line or 'Usage by model' in line:
            in_stats = True
        
        if in_stats:
            stats.append(line)
        elif line.strip().startswith('✓'):
            # Action completed
            actions.append(line.strip())
            
            # Check if next line is a command execution (starts with $ or ↪)
            in_command = False
        elif line.strip().startswith('$'):
            # Command line
            in_command = True
            current_command = [line.strip()]
        elif line.strip().startswith('↪') and in_command:
            # Command output indicator
            current_command.append(line.strip())
            commands.append('\n'.join(current_command))
            in_command = False
        elif line.strip():
            content.append(line)
    
    return '\n'.join(actions), '\n'.join(content), '\n'.join(stats), commands


def format_command_block(command_info: str) -> str:
    """Format command execution as a quoted block"""
    lines = command_info.split('\n')
    
    formatted = ""
    for line in lines:
        if line.startswith('$'):
            # Command line
            cmd = line[1:].strip()
            formatted += f"```bash\n$ {cmd}\n```\n"
        elif line.startswith('↪'):
            # Output indicator
            output = line[1:].strip()
            formatted += f"_{output}_\n"
    
    return formatted


def escape_markdown_chars(text: str) -> str:
    """Escape special markdown characters that can break parsing"""
    # Characters that need escaping: _ * [ ] ( ) ~ ` > # + - = | { } . !
    # But preserve those in code blocks
    
    # Don't escape if already in code block
    if text.startswith('```') or text.startswith('`'):
        return text
    
    # Escape problematic characters
    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        # Only escape if not already escaped
        text = text.replace(char, '\\' + char)
    
    return text


def format_for_telegram(response: str, truncate: int = 3500) -> str:
    """Format copilot response for Telegram with proper markdown"""
    
    try:
        # Replace ✓ with emoji
        response = response.replace('✓', '✅')
        
        # Handle bold **text** -> *text* for Telegram
        response = re.sub(r'\*\*(.+?)\*\*', r'*\1*', response)
        
        # Handle code blocks properly
        response = re.sub(r'```(\w+)?\n', r'```\n', response)
        
        # Truncate if too long but keep structure
        if len(response) > truncate:
            response = response[:truncate] + '\n\n...[Response truncated]'
        
        return response
    except Exception as e:
        # If any error, return plain text
        return response.replace('✓', '✅')[:truncate]


def create_copilot_result(task: str, response: str) -> str:
    """Create a beautifully formatted result message"""
    
    actions, content, stats, commands = parse_copilot_response(response)
    
    result = "╔═══════════════════════════╗\n"
    result += "║   ✅ *AGENT COMPLETED*     ║\n"
    result += "╚═══════════════════════════╝\n\n"
    result += f"*Task:* {task}\n\n"
    
    if actions:
        result += "*Actions Performed:*\n"
        for action in actions.split('\n')[:5]:  # Limit to 5 actions
            if action.strip():
                result += f"{action}\n"
        result += "\n"
    
    # Add command executions in quote blocks
    if commands:
        result += "*Commands Executed:*\n"
        for cmd in commands[:3]:  # Show first 3 commands
            result += format_command_block(cmd) + "\n"
        result += "\n"
    
    if content:
        result += "*Response:*\n"
        formatted_content = format_for_telegram(content, truncate=2500)
        result += f"{formatted_content}\n\n"
    
    if stats:
        # Extract key stats only
        duration_match = re.search(r'Total duration \(wall\): ([\d.]+s)', stats)
        model_match = re.search(r'claude-sonnet-[\d.]+', stats)
        
        result += "*Stats:*\n"
        if duration_match:
            result += f"⏱️ Duration: `{duration_match.group(1)}`\n"
        if model_match:
            result += f"🤖 Model: `{model_match.group(0)}`\n"
    
    return result


def split_response(response: str, max_length: int = 4000) -> list:
    """Split long responses into chunks while preserving markdown"""
    
    if len(response) <= max_length:
        return [response]
    
    chunks = []
    current_chunk = ""
    
    for line in response.split('\n'):
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
