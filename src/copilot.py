import subprocess
import asyncio
import logging
import os
from typing import Optional
import re

logger = logging.getLogger(__name__)


class CopilotCLI:
    """Interface to GitHub Copilot CLI"""
    
    # Store active sessions per user
    sessions = {}
    
    # Store chat sessions per user
    chat_sessions = {}
    
    # Store user model preferences
    user_models = {}
    
    # Available models
    MODELS = {
        'claude-sonnet-4.5': 'Claude Sonnet 4.5 (Default)',
        'claude-sonnet-4': 'Claude Sonnet 4',
        'claude-haiku-4.5': 'Claude Haiku 4.5 (Fast)',
        'gpt-5': 'GPT-5'
    }
    
    @staticmethod
    def get_user_model(user_id: int) -> str:
        """Get user's preferred model"""
        return CopilotCLI.user_models.get(user_id, 'claude-sonnet-4.5')
    
    @staticmethod
    def set_user_model(user_id: int, model: str):
        """Set user's preferred model"""
        CopilotCLI.user_models[user_id] = model
    
    @staticmethod
    async def execute_command(command: str, timeout: int = 30, cwd: str = None) -> dict:
        """Execute a shell command and return the result"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
                cwd=cwd
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    'success': process.returncode == 0,
                    'output': stdout.decode('utf-8', errors='ignore'),
                    'error': stderr.decode('utf-8', errors='ignore'),
                    'returncode': process.returncode
                }
            except asyncio.TimeoutError:
                process.kill()
                return {
                    'success': False,
                    'output': '',
                    'error': f'Command timed out after {timeout} seconds',
                    'returncode': -1
                }
                
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'returncode': -1
            }
    
    @staticmethod
    async def execute_with_streaming(command: str, callback, timeout: int = 120, cwd: str = None, auto_approve: bool = True):
        """Execute command and stream output line by line"""
        try:
            # If auto_approve, use yes but with proper handling
            if auto_approve:
                # Use printf to send multiple 'y' responses
                command = f"printf 'y\\ny\\ny\\ny\\ny\\ny\\n' | {command}"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                shell=True,
                cwd=cwd
            )
            
            output_lines = []
            actions = []
            
            try:
                async def read_stream():
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        
                        decoded = line.decode('utf-8', errors='ignore').rstrip()
                        output_lines.append(decoded)
                        
                        # Check if it's an action line (starts with ✓)
                        if decoded.strip().startswith('✓'):
                            actions.append(decoded.strip())
                            await callback('action', decoded.strip(), actions)
                        elif decoded.strip() and not decoded.startswith('Total') and not decoded.startswith('Usage by'):
                            # Regular content line
                            await callback('content', decoded.strip(), output_lines)
                
                # Read with timeout
                await asyncio.wait_for(read_stream(), timeout=timeout)
                await process.wait()
                
                return {
                    'success': process.returncode == 0,
                    'output': '\n'.join(output_lines),
                    'actions': actions,
                    'returncode': process.returncode
                }
                
            except asyncio.TimeoutError:
                process.kill()
                return {
                    'success': False,
                    'output': '\n'.join(output_lines),
                    'actions': actions,
                    'error': 'Command timed out',
                    'returncode': -1
                }
                
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            return {
                'success': False,
                'output': '',
                'actions': [],
                'error': str(e),
                'returncode': -1
            }
    
    @staticmethod
    async def suggest(query: str, user_id: int = None) -> str:
        """Get command suggestions using copilot CLI"""
        model = CopilotCLI.get_user_model(user_id) if user_id else 'claude-sonnet-4.5'
        result = await CopilotCLI.execute_command(
            f'copilot -p "{query}" --model {model} --allow-all-tools --allow-all-paths',
            timeout=60
        )
        
        if result['success']:
            return result['output'] or "No suggestion available"
        else:
            return f"Error: {result['error']}"
    
    @staticmethod
    async def explain(command: str, user_id: int = None) -> str:
        """Explain a command using copilot CLI"""
        model = CopilotCLI.get_user_model(user_id) if user_id else 'claude-sonnet-4.5'
        result = await CopilotCLI.execute_command(
            f'copilot -p "explain this command: {command}" --model {model} --allow-all-tools --allow-all-paths',
            timeout=60
        )
        
        if result['success']:
            return result['output'] or "No explanation available"
        else:
            return f"Error: {result['error']}"
    
    @staticmethod
    async def agent_mode(user_id: int, query: str, continue_session: bool = False) -> str:
        """Run copilot in agent mode with session persistence"""
        
        # Create user workspace
        workspace = f"/tmp/copilot_agent_{user_id}"
        os.makedirs(workspace, exist_ok=True)
        
        if continue_session and user_id in CopilotCLI.sessions:
            # Continue previous session
            cmd = f'cd {workspace} && copilot --continue -p "{query}" --allow-all-tools --allow-all-paths'
        else:
            # Start new session
            cmd = f'cd {workspace} && copilot -p "{query}" --allow-all-tools --allow-all-paths'
            CopilotCLI.sessions[user_id] = True
        
        result = await CopilotCLI.execute_command(cmd, timeout=120, cwd=workspace)
        
        if result['success']:
            return result['output'] or "Agent completed task"
        else:
            return f"Error: {result['error']}"
    
    @staticmethod
    async def agent_mode_streaming(user_id: int, query: str, callback, continue_session: bool = False, auto_approve: bool = True):
        """Run copilot in agent mode with live streaming updates"""
        
        # Create user workspace
        workspace = f"/tmp/copilot_agent_{user_id}"
        os.makedirs(workspace, exist_ok=True)
        
        model = CopilotCLI.get_user_model(user_id)
        
        if continue_session and user_id in CopilotCLI.sessions:
            cmd = f'cd {workspace} && copilot --continue -p "{query}" --model {model} --allow-all-tools --allow-all-paths'
        else:
            cmd = f'cd {workspace} && copilot -p "{query}" --model {model} --allow-all-tools --allow-all-paths'
            CopilotCLI.sessions[user_id] = True
        
        result = await CopilotCLI.execute_with_streaming(cmd, callback, timeout=180, cwd=workspace, auto_approve=auto_approve)
        return result
    
    @staticmethod
    def clear_session(user_id: int):
        """Clear user's copilot session"""
        if user_id in CopilotCLI.sessions:
            del CopilotCLI.sessions[user_id]
        workspace = f"/tmp/copilot_agent_{user_id}"
        if os.path.exists(workspace):
            import shutil
            shutil.rmtree(workspace, ignore_errors=True)
    
    @staticmethod
    def clear_chat_session(user_id: int):
        """Clear user's chat session"""
        if user_id in CopilotCLI.chat_sessions:
            del CopilotCLI.chat_sessions[user_id]
        chat_workspace = f"/tmp/copilot_chat_{user_id}"
        if os.path.exists(chat_workspace):
            import shutil
            shutil.rmtree(chat_workspace, ignore_errors=True)
    
    @staticmethod
    async def ai_chat(user_id: int, message: str, continue_session: bool = False) -> str:
        """Simple AI chat with session support"""
        model = CopilotCLI.get_user_model(user_id)
        
        # Create user chat workspace
        chat_workspace = f"/tmp/copilot_chat_{user_id}"
        os.makedirs(chat_workspace, exist_ok=True)
        
        if continue_session and user_id in CopilotCLI.chat_sessions:
            # Continue previous chat session
            cmd = f'cd {chat_workspace} && copilot --continue -p "{message}" --model {model}'
        else:
            # Start new chat session
            cmd = f'cd {chat_workspace} && copilot -p "{message}" --model {model}'
            CopilotCLI.chat_sessions[user_id] = True
        
        result = await CopilotCLI.execute_command(cmd, timeout=60, cwd=chat_workspace)
        
        if result['success']:
            return result['output'] or "No response available"
        else:
            return f"Error: {result['error']}"
    
    @staticmethod
    async def run_shell_command(command: str, timeout: int = 60) -> str:
        """Execute a shell command on the VPS"""
        result = await CopilotCLI.execute_command(command, timeout=timeout)
        
        output = result['output'].strip()
        error = result['error'].strip()
        
        response = ""
        if output:
            response += f"Output:\n{output}\n"
        if error:
            response += f"Error:\n{error}\n"
        if not output and not error:
            response = "Command executed successfully (no output)"
            
        response += f"\nReturn code: {result['returncode']}"
        return response
