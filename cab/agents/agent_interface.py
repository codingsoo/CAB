#!/usr/bin/env python3
"""
Agent Interface for CAB (CodeAssistBench)
Defines the interface that any AI agent must implement to be tested by CAB.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentResponse:
    """Response from an AI agent"""
    content: str
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

@dataclass
class ConversationContext:
    """Context for agent conversations"""
    issue_data: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    repository_path: str
    docker_results: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None

class CABAgent(ABC):
    """
    Abstract base class for AI agents to be tested by CAB.
    
    Any AI agent that wants to be evaluated by CAB must implement this interface.
    """
    
    def __init__(self, name: str, model_name: str = None):
        """
        Initialize the agent.
        
        Args:
            name: Human-readable name for the agent
            model_name: Name of the underlying model (e.g., "gpt-4", "claude-3")
        """
        self.name = name
        self.model_name = model_name or name
    
    @abstractmethod
    def respond(self, context: ConversationContext) -> AgentResponse:
        """
        Generate a response to a user question or conversation.
        
        Args:
            context: The conversation context including issue data, history, etc.
            
        Returns:
            AgentResponse: The agent's response with content and metadata
        """
        pass
    
    @abstractmethod
    def setup(self) -> bool:
        """
        Setup the agent (e.g., initialize API clients, load models).
        
        Returns:
            bool: True if setup successful, False otherwise
        """
        pass
    
    def cleanup(self):
        """
        Cleanup resources used by the agent.
        Override if needed.
        """
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the agent.
        
        Returns:
            Dict with agent information
        """
        return {
            "name": self.name,
            "model_name": self.model_name,
            "type": self.__class__.__name__
        }

class OpenAIAgent(CABAgent):
    """
    Example implementation of CABAgent using OpenAI API.
    """
    
    def __init__(self, model_name: str = "gpt-4", api_key: str = None):
        super().__init__(name=f"OpenAI-{model_name}", model_name=model_name)
        self.api_key = api_key
        self.client = None
    
    def setup(self) -> bool:
        """Setup OpenAI client"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            return True
        except Exception as e:
            print(f"Failed to setup OpenAI agent: {e}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response using OpenAI API"""
        try:
            # Build conversation messages
            messages = []
            
            if context.system_prompt:
                messages.append({"role": "system", "content": context.system_prompt})
            
            # Add conversation history
            for msg in context.conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current issue context
            issue = context.issue_data["first_question"]
            current_message = f"Question: {issue['title']}\n\n{issue['body']}"
            messages.append({"role": "user", "content": current_message})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            return AgentResponse(
                content=content,
                metadata={
                    "model": self.model_name,
                    "tokens_used": response.usage.total_tokens,
                    "finish_reason": response.choices[0].finish_reason
                }
            )
            
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"OpenAI API error: {str(e)}"
            )

class ClaudeAgent(CABAgent):
    """
    Example implementation of CABAgent using AWS Bedrock Claude.
    """
    
    def __init__(self, model_name: str = "claude-3-sonnet", region: str = "us-east-2"):
        super().__init__(name=f"Claude-{model_name}", model_name=model_name)
        self.region = region
        self.client = None
    
    def setup(self) -> bool:
        """Setup AWS Bedrock client"""
        try:
            import boto3
            self.client = boto3.client('bedrock-runtime', region_name=self.region)
            return True
        except Exception as e:
            print(f"Failed to setup Claude agent: {e}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response using Claude API"""
        try:
            # Build prompt
            prompt = ""
            if context.system_prompt:
                prompt += f"System: {context.system_prompt}\n\n"
            
            # Add conversation history
            for msg in context.conversation_history:
                role = "Human" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n\n"
            
            # Add current issue
            issue = context.issue_data["first_question"]
            prompt += f"Human: Question: {issue['title']}\n\n{issue['body']}\n\nAssistant:"
            
            # Call Claude API
            body = {
                "prompt": prompt,
                "max_tokens_to_sample": 2000,
                "temperature": 0.7
            }
            
            response = self.client.invoke_model(
                modelId=f"us.anthropic.{self.model_name}-20240229-v1:0",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['completion']
            
            return AgentResponse(
                content=content,
                metadata={
                    "model": self.model_name,
                    "region": self.region
                }
            )
            
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"Claude API error: {str(e)}"
            )

class MockAgent(CABAgent):
    """
    Mock agent for testing purposes (no API calls required).
    """
    
    def __init__(self, name: str = "MockAgent"):
        super().__init__(name=name, model_name="mock")
    
    def setup(self) -> bool:
        """Mock setup always succeeds"""
        return True
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate mock response"""
        issue = context.issue_data["first_question"]
        
        mock_response = f"""I understand you're asking about: {issue['title']}

Based on the issue description: {issue['body'][:100]}...

Here's my suggested solution:
1. First, let's analyze the problem
2. Then implement a fix
3. Finally, test the solution

This should resolve the issue you're experiencing."""
        
        return AgentResponse(
            content=mock_response,
            metadata={
                "model": "mock",
                "response_type": "mock"
            }
        )

# Agent registry for easy access
AGENT_REGISTRY = {
    "openai-gpt4": lambda: OpenAIAgent("gpt-4"),
    "openai-gpt3.5": lambda: OpenAIAgent("gpt-3.5-turbo"),
    "claude-sonnet": lambda: ClaudeAgent("claude-3-sonnet"),
    "claude-haiku": lambda: ClaudeAgent("claude-3-haiku"),
    "mock": lambda: MockAgent()
}

def create_agent(agent_type: str, **kwargs) -> CABAgent:
    """
    Create an agent instance by type.
    
    Args:
        agent_type: Type of agent to create
        **kwargs: Additional arguments for agent initialization
        
    Returns:
        CABAgent instance
    """
    if agent_type not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_REGISTRY.keys())}")
    
    return AGENT_REGISTRY[agent_type](**kwargs)
