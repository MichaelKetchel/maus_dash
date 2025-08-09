import asyncio
import json
import logging
import os
import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.module_loader import BaseModule
from backend.core.event_bus import EventBus

logger = logging.getLogger(__name__)


def is_url_safe(text: str) -> bool:
    """Check if a string contains only URL-safe characters"""
    return re.match(r'^[A-Za-z0-9\-_.~]*$', text) is not None


#
# class SystemInfoResponse(BaseModel):
#     """Response model for system info"""
#     hostname: str
#     platform: str
#     python_version: str
#     uptime: float
#     timestamp: str

class CLICommand(BaseModel):
    """Represents a CLI command"""
    name: str
    cmds: List[str]

class CLICommandResponse(BaseModel):
    """Represents a CLI command response"""
    execution_id: str
    name: str
    cmd: str
    code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""

class CommandExecutionRequest(BaseModel):
    """Request to execute a command"""
    stream_output: bool = False
    timeout: int = 30


class AsyncCommandExecutor:
    """Handles async execution of CLI commands with real-time communication"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running_processes: Dict[str, asyncio.subprocess.Process] = {}
    
    async def execute_command(
        self, 
        command: CLICommand, 
        execution_id: str,
        stream_output: bool = False,
        timeout: int = 30
    ) -> CLICommandResponse:
        """Execute a command asynchronously with real-time updates"""
        
        if not command.cmds:
            raise ValueError("No commands defined")
        
        cmd_string = command.cmds[0]  # Execute first command
        
        # Notify start
        await self.event_bus.emit("websocket.broadcast", {
            "message": {
                "type": "command_started",
                "execution_id": execution_id,
                "command": command.name,
                "cmd": cmd_string
            }
        })
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                cmd_string,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stream_output else None
            )
            
            self.running_processes[execution_id] = process
            
            stdout_data = ""
            stderr_data = ""
            
            if stream_output:
                # Stream output in real-time
                stdout_data, stderr_data = await self._stream_output(
                    process, execution_id, timeout
                )
            else:
                # Wait for completion
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                    stdout_data = stdout_bytes.decode() if stdout_bytes else ""
                    stderr_data = stderr_bytes.decode() if stderr_bytes else ""
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    raise
            
            # Clean up
            self.running_processes.pop(execution_id, None)
            
            response = CLICommandResponse(
                execution_id=execution_id,
                name=command.name,
                cmd=cmd_string,
                code=process.returncode,
                stdout=stdout_data,
                stderr=stderr_data
            )
            
            # Notify completion
            await self.event_bus.emit("websocket.broadcast", {
                "message": {
                    "type": "command_completed",
                    "execution_id": execution_id,
                    "command": command.name,
                    "exit_code": process.returncode,
                    "success": process.returncode == 0
                }
            })
            
            return response
            
        except Exception as e:
            # Clean up and notify error
            self.running_processes.pop(execution_id, None)
            
            await self.event_bus.emit("websocket.broadcast", {
                "message": {
                    "type": "command_error",
                    "execution_id": execution_id,
                    "command": command.name,
                    "error": str(e)
                }
            })
            
            raise
    
    async def _stream_output(
        self, 
        process: asyncio.subprocess.Process, 
        execution_id: str, 
        timeout: int
    ) -> tuple[str, str]:
        """Stream stdout/stderr in real-time"""
        stdout_data = ""
        stderr_data = ""
        
        async def read_stream(stream, stream_name: str):
            nonlocal stdout_data, stderr_data
            data = ""
            
            while True:
                try:
                    line = await stream.readline()
                    if not line:
                        break
                    
                    line_text = line.decode()
                    data += line_text
                    
                    if stream_name == "stdout":
                        stdout_data += line_text
                    else:
                        stderr_data += line_text
                    
                    # Send real-time output
                    await self.event_bus.emit("websocket.broadcast", {
                        "message": {
                            "type": "command_output",
                            "execution_id": execution_id,
                            "stream": stream_name,
                            "data": line_text.rstrip('\n\r')
                        }
                    })
                    
                except Exception as e:
                    logger.error(f"Error reading {stream_name}: {e}")
                    break
            
            return data
        
        try:
            # Read both streams concurrently
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, "stdout"),
                    read_stream(process.stderr, "stderr"),
                    process.wait()
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
        
        return stdout_data, stderr_data
    
    async def cancel_command(self, execution_id: str) -> bool:
        """Cancel a running command"""
        if execution_id in self.running_processes:
            process = self.running_processes[execution_id]
            process.kill()
            await process.wait()
            self.running_processes.pop(execution_id, None)
            
            await self.event_bus.emit("websocket.broadcast", {
                "message": {
                    "type": "command_cancelled",
                    "execution_id": execution_id
                }
            })
            
            return True
        return False


class CLIExecutorModule(BaseModule):
    """CLI Executor module with async command execution and real-time communication"""

    def __init__(self, event_bus: EventBus):
        super().__init__("cli_executor", event_bus)
        self.router = APIRouter()
        self.start_time = datetime.utcnow()
        self.available_commands: dict[str, CLICommand] = {}
        self.executor = AsyncCommandExecutor(event_bus)
        
        self._setup_routes()
        self._setup_event_handlers()

    async def pre_initialize(self):
        """Pre-initialization setup"""
        logger.info(f"Pre-initializing {self.__name__}")
        
    async def initialize(self):
        """Initialize the module"""
        logger.info(f"Initializing {self.__name__}")
        
        # Load commands from commands.json
        commands_file = os.path.join(os.path.dirname(__file__), "commands.json")
        try:
            with open(commands_file, 'r') as f:
                commands_data = json.load(f)
            
            for cmd_data in commands_data:
                cli_command = CLICommand(**cmd_data)
                self.available_commands[cli_command.name] = cli_command
            
            logger.info(f"Loaded {len(self.available_commands)} commands from {commands_file}")
        except FileNotFoundError:
            logger.warning(f"Commands file not found: {commands_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in commands file: {e}")
        except Exception as e:
            logger.error(f"Error loading commands: {e}")

        # Example of module initialization
        await self.event_bus.emit(f"{self.name}.initialized", {
            "module": self.name,
            "start_time": self.start_time.isoformat()
        })
        
    async def post_initialize(self):
        """Post-initialization setup"""
        logger.info(f"Post-initializing {self.__name__}")
        # Module is now fully ready

    def _setup_routes(self):
        """Setup FastAPI routes for this module"""
        
        @self.router.get("/commands")
        async def list_commands():
            """List all available CLI commands"""
            return {
                "commands": [
                    {
                        "name": cmd.name,
                        "cmds": cmd.cmds,
                        "url_safe": is_url_safe(cmd.name)
                    }
                    for cmd in self.available_commands.values()
                ]
            }
        
        @self.router.post("/execute/{command_name}", response_model=CLICommandResponse)
        async def execute_command(
            command_name: str,
            request: CommandExecutionRequest = CommandExecutionRequest()
        ):
            """Execute a CLI command by name"""
            if command_name not in self.available_commands:
                raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")
            
            if not is_url_safe(command_name):
                raise HTTPException(status_code=400, detail=f"Command name '{command_name}' is not URL safe")
            
            command = self.available_commands[command_name]
            execution_id = str(uuid.uuid4())
            
            try:
                # Execute command asynchronously
                result = await self.executor.execute_command(
                    command=command,
                    execution_id=execution_id,
                    stream_output=request.stream_output,
                    timeout=request.timeout
                )
                return result
                
            except asyncio.TimeoutError:
                raise HTTPException(status_code=408, detail="Command execution timed out")
            except Exception as e:
                logger.error(f"Error executing command '{command_name}': {e}")
                raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")
        
        @self.router.post("/cancel/{execution_id}")
        async def cancel_command(execution_id: str):
            """Cancel a running command by execution ID"""
            cancelled = await self.executor.cancel_command(execution_id)
            if cancelled:
                return {"status": "cancelled", "execution_id": execution_id}
            else:
                raise HTTPException(status_code=404, detail=f"Command execution '{execution_id}' not found")
        
        @self.router.get("/running")
        async def list_running_commands():
            """List currently running commands"""
            return {
                "running_commands": list(self.executor.running_processes.keys())
            }




    def _setup_event_handlers(self):
        """Setup event handlers for this module"""

        @self.event_bus.on(f"{self.name}.send_input")
        async def handle_send_input(data: Dict[str, Any]):
            """Handle stdin input for running commands"""
            execution_id = data.get("execution_id")
            input_data = data.get("input", "")
            
            if execution_id in self.executor.running_processes:
                process = self.executor.running_processes[execution_id]
                if process.stdin:
                    try:
                        process.stdin.write(f"{input_data}\n".encode())
                        await process.stdin.drain()
                        logger.info(f"Sent input to command {execution_id}: {input_data}")
                    except Exception as e:
                        logger.error(f"Error sending input to command {execution_id}: {e}")
                else:
                    logger.warning(f"Command {execution_id} does not accept input")
            else:
                logger.warning(f"Command {execution_id} not found or not running")

    def get_routes(self) -> List[APIRouter]:
        """Return FastAPI routes for this module"""
        return [self.router]

    async def pre_cleanup(self):
        """Pre-cleanup hook"""
        logger.info(f"Pre-cleanup {self.__name__}")
        
    async def cleanup(self):
        """Cleanup module resources"""
        logger.info(f"Cleaning up {self.__name__}")
        
        # Cancel any running commands
        for execution_id in list(self.executor.running_processes.keys()):
            await self.executor.cancel_command(execution_id)

        # Call parent cleanup for standard cleanup tasks
        await super().cleanup()

        # Emit cleanup event
        await self.event_bus.emit(f"{self.name}.cleanup", {
            "module": self.name,
            "cleanup_at": datetime.utcnow().isoformat()
        })
        
    async def post_cleanup(self):
        """Post-cleanup hook"""
        logger.info(f"Post-cleanup {self.__name__}")


def create_module(event_bus: EventBus) -> BaseModule:
    """Factory function to create the module instance"""
    return CLIExecutorModule(event_bus)