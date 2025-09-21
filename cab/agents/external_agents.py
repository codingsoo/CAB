#!/usr/bin/env python3
"""
External Agent Integrations for CAB (CodeAssistBench)
Provides agents that interface with external tools like Cursor CLI, GitHub Copilot, etc.
"""

import json
import subprocess
import tempfile
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from agent_interface import CABAgent, ConversationContext, AgentResponse

logger = logging.getLogger(__name__)

class CursorCLIAgent(CABAgent):
    """
    Agent that interfaces with Cursor CLI for code assistance.
    """
    
    def __init__(self, cursor_path: str = "cursor", timeout: int = 60):
        """
        Initialize Cursor CLI agent.
        
        Args:
            cursor_path: Path to cursor CLI executable
            timeout: Timeout in seconds for cursor commands
        """
        super().__init__(name="CursorCLI", model_name="cursor-cli")
        self.cursor_path = cursor_path
        self.timeout = timeout
    
    def setup(self) -> bool:
        """Check if Cursor CLI is available"""
        try:
            result = subprocess.run(
                [self.cursor_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Cursor CLI found: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Cursor CLI not working: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error(f"Cursor CLI not found at: {self.cursor_path}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Cursor CLI timeout during setup")
            return False
        except Exception as e:
            logger.error(f"Error checking Cursor CLI: {e}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response using Cursor CLI"""
        try:
            # Create a temporary file with the issue
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                issue = context.issue_data["first_question"]
                
                # Write issue to file
                f.write(f"# {issue['title']}\n\n")
                f.write(f"{issue['body']}\n\n")
                
                # Add conversation history
                if context.conversation_history:
                    f.write("## Conversation History\n\n")
                    for msg in context.conversation_history:
                        role = "User" if msg["role"] == "user" else "Assistant"
                        f.write(f"**{role}:** {msg['content']}\n\n")
                
                temp_file = f.name
            
            # Use Cursor CLI to get assistance
            # Note: This is a simplified example - actual Cursor CLI integration
            # would depend on the specific Cursor CLI commands available
            cmd = [
                self.cursor_path,
                "chat",
                "--file", temp_file,
                "--prompt", "Please help solve this coding issue. Provide a clear solution with code examples."
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=context.repository_path if context.repository_path else "."
            )
            
            # Clean up temp file
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return AgentResponse(
                    content=result.stdout,
                    metadata={
                        "tool": "cursor-cli",
                        "command": " ".join(cmd),
                        "return_code": result.returncode
                    }
                )
            else:
                return AgentResponse(
                    content="",
                    error=f"Cursor CLI error: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return AgentResponse(
                content="",
                error=f"Cursor CLI timeout after {self.timeout} seconds"
            )
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"Cursor CLI error: {str(e)}"
            )

class GitHubCopilotAgent(CABAgent):
    """
    Agent that interfaces with GitHub Copilot CLI.
    """
    
    def __init__(self, copilot_path: str = "gh", timeout: int = 60):
        """
        Initialize GitHub Copilot agent.
        
        Args:
            copilot_path: Path to GitHub CLI (gh) executable
            timeout: Timeout in seconds for copilot commands
        """
        super().__init__(name="GitHubCopilot", model_name="copilot")
        self.copilot_path = copilot_path
        self.timeout = timeout
    
    def setup(self) -> bool:
        """Check if GitHub Copilot CLI is available"""
        try:
            result = subprocess.run(
                [self.copilot_path, "copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"GitHub Copilot CLI found: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"GitHub Copilot CLI not working: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error(f"GitHub CLI not found at: {self.copilot_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking GitHub Copilot CLI: {e}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response using GitHub Copilot CLI"""
        try:
            issue = context.issue_data["first_question"]
            prompt = f"{issue['title']}\n\n{issue['body']}"
            
            # Use GitHub Copilot CLI
            cmd = [
                self.copilot_path, "copilot", "suggest",
                "--prompt", prompt
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=context.repository_path if context.repository_path else "."
            )
            
            if result.returncode == 0:
                return AgentResponse(
                    content=result.stdout,
                    metadata={
                        "tool": "github-copilot",
                        "command": " ".join(cmd),
                        "return_code": result.returncode
                    }
                )
            else:
                return AgentResponse(
                    content="",
                    error=f"GitHub Copilot error: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return AgentResponse(
                content="",
                error=f"GitHub Copilot timeout after {self.timeout} seconds"
            )
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"GitHub Copilot error: {str(e)}"
            )

class LocalLLMAgent(CABAgent):
    """
    Agent that interfaces with local LLM models (Ollama, LM Studio, etc.).
    """
    
    def __init__(self, model_name: str = "llama2", api_url: str = "http://localhost:11434"):
        """
        Initialize local LLM agent.
        
        Args:
            model_name: Name of the local model
            api_url: URL of the local LLM API
        """
        super().__init__(name=f"Local-{model_name}", model_name=model_name)
        self.model_name = model_name
        self.api_url = api_url
    
    def setup(self) -> bool:
        """Check if local LLM API is available"""
        try:
            import requests
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if any(self.model_name in name for name in model_names):
                    logger.info(f"Local LLM {self.model_name} found")
                    return True
                else:
                    logger.error(f"Model {self.model_name} not found. Available: {model_names}")
                    return False
            else:
                logger.error(f"Local LLM API not responding: {response.status_code}")
                return False
        except ImportError:
            logger.error("requests library not available for local LLM")
            return False
        except Exception as e:
            logger.error(f"Error checking local LLM: {e}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response using local LLM"""
        try:
            import requests
            
            # Build prompt
            issue = context.issue_data["first_question"]
            prompt = f"Question: {issue['title']}\n\n{issue['body']}\n\n"
            
            if context.conversation_history:
                prompt += "Conversation History:\n"
                for msg in context.conversation_history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    prompt += f"{role}: {msg['content']}\n"
                prompt += "\n"
            
            prompt += "Please provide a helpful solution to this coding issue."
            
            # Call local LLM API
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return AgentResponse(
                    content=result.get("response", ""),
                    metadata={
                        "tool": "local-llm",
                        "model": self.model_name,
                        "api_url": self.api_url
                    }
                )
            else:
                return AgentResponse(
                    content="",
                    error=f"Local LLM API error: {response.status_code}"
                )
                
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"Local LLM error: {str(e)}"
            )

class AmazonQAgent(CABAgent):
    """
    Agent that interfaces with Amazon Q CLI for code assistance.
    """
    
    def __init__(self, q_path: str = "q", timeout: int = 60):
        """
        Initialize Amazon Q CLI agent.
        
        Args:
            q_path: Path to Amazon Q CLI executable
            timeout: Timeout in seconds for Q commands
        """
        super().__init__(name="AmazonQ", model_name="amazon-q")
        self.q_path = q_path
        self.timeout = timeout
    
    def setup(self) -> bool:
        """Check if Amazon Q CLI is available"""
        try:
            result = subprocess.run(
                [self.q_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Amazon Q CLI found: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Amazon Q CLI not working: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error(f"Amazon Q CLI not found at: {self.q_path}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Amazon Q CLI timeout during setup")
            return False
        except Exception as e:
            logger.error(f"Error checking Amazon Q CLI: {e}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response using Amazon Q CLI"""
        try:
            # Create a temporary file with the issue
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                issue = context.issue_data["first_question"]
                
                # Write issue to file
                f.write(f"# {issue['title']}\n\n")
                f.write(f"{issue['body']}\n\n")
                
                # Add conversation history
                if context.conversation_history:
                    f.write("## Conversation History\n\n")
                    for msg in context.conversation_history:
                        role = "User" if msg["role"] == "user" else "Assistant"
                        f.write(f"**{role}:** {msg['content']}\n\n")
                
                temp_file = f.name
            
            # Use Amazon Q CLI to get assistance
            # Amazon Q CLI uses 'qchat chat' command with input as argument
            issue = context.issue_data["first_question"]
            prompt = f"Please help solve this coding issue: {issue['title']}\n\n{issue['body']}\n\nProvide a clear solution with code examples."
            
            cmd = [
                "qchat", "chat",
                "--no-interactive",
                prompt
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=context.repository_path if context.repository_path else "."
            )
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                return AgentResponse(
                    content=result.stdout,
                    metadata={
                        "tool": "amazon-q",
                        "command": " ".join(cmd),
                        "return_code": result.returncode
                    }
                )
            else:
                return AgentResponse(
                    content="",
                    error=f"Amazon Q CLI error: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return AgentResponse(
                content="",
                error=f"Amazon Q CLI timeout after {self.timeout} seconds"
            )
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"Amazon Q CLI error: {str(e)}"
            )

class CustomScriptAgent(CABAgent):
    """
    Agent that runs custom scripts for code assistance.
    """
    
    def __init__(self, script_path: str, name: str = "CustomScript"):
        """
        Initialize custom script agent.
        
        Args:
            script_path: Path to the custom script
            name: Name for the agent
        """
        super().__init__(name=name, model_name="custom-script")
        self.script_path = script_path
    
    def setup(self) -> bool:
        """Check if custom script is available"""
        if Path(self.script_path).exists():
            logger.info(f"Custom script found: {self.script_path}")
            return True
        else:
            logger.error(f"Custom script not found: {self.script_path}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response using custom script"""
        try:
            issue = context.issue_data["first_question"]
            
            # Prepare input for script
            script_input = {
                "issue": {
                    "title": issue["title"],
                    "body": issue["body"]
                },
                "conversation_history": context.conversation_history,
                "repository_path": context.repository_path
            }
            
            # Run custom script
            result = subprocess.run(
                ["python", self.script_path],
                input=json.dumps(script_input),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                try:
                    response_data = json.loads(result.stdout)
                    return AgentResponse(
                        content=response_data.get("response", ""),
                        metadata={
                            "tool": "custom-script",
                            "script_path": self.script_path,
                            "return_code": result.returncode
                        }
                    )
                except json.JSONDecodeError:
                    return AgentResponse(
                        content=result.stdout,
                        metadata={
                            "tool": "custom-script",
                            "script_path": self.script_path,
                            "return_code": result.returncode
                        }
                    )
            else:
                return AgentResponse(
                    content="",
                    error=f"Custom script error: {result.stderr}"
                )
                
        except subprocess.TimeoutExpired:
            return AgentResponse(
                content="",
                error="Custom script timeout"
            )
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"Custom script error: {str(e)}"
            )

# Extended agent registry
EXTERNAL_AGENT_REGISTRY = {
    "cursor-cli": lambda: CursorCLIAgent(),
    "github-copilot": lambda: GitHubCopilotAgent(),
    "amazon-q": lambda: AmazonQAgent(),
    "local-llama2": lambda: LocalLLMAgent("llama2"),
    "local-codellama": lambda: LocalLLMAgent("codellama"),
    "local-mistral": lambda: LocalLLMAgent("mistral"),
}

def create_external_agent(agent_type: str, **kwargs) -> CABAgent:
    """
    Create an external agent instance by type.
    
    Args:
        agent_type: Type of external agent to create
        **kwargs: Additional arguments for agent initialization
        
    Returns:
        CABAgent instance
    """
    if agent_type not in EXTERNAL_AGENT_REGISTRY:
        raise ValueError(f"Unknown external agent type: {agent_type}. Available: {list(EXTERNAL_AGENT_REGISTRY.keys())}")
    
    return EXTERNAL_AGENT_REGISTRY[agent_type](**kwargs)

def list_available_agents():
    """List all available agents (built-in + external)"""
    from agent_interface import AGENT_REGISTRY
    
    print("🤖 Available Agents:")
    print("=" * 40)
    
    print("\n📦 Built-in Agents:")
    for name in AGENT_REGISTRY.keys():
        print(f"  • {name}")
    
    print("\n🔧 External Agents:")
    for name in EXTERNAL_AGENT_REGISTRY.keys():
        print(f"  • {name}")
    
    print("\n💡 Usage:")
    print("  python test_agent.py --agent <agent_name> --dataset <dataset>")

if __name__ == "__main__":
    list_available_agents()
