# 🤖 Custom Agent Development Guide

This guide shows you how to create and test your own AI agents with CAB (CodeAssistBench).

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Agent Interface](#agent-interface)
3. [Creating Custom Agents](#creating-custom-agents)
4. [Testing Your Agent](#testing-your-agent)
5. [Advanced Examples](#advanced-examples)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### 1. Create a Simple Custom Agent

```python
# my_custom_agent.py
from agent_interface import CABAgent, ConversationContext, AgentResponse

class MyCustomAgent(CABAgent):
    def __init__(self):
        super().__init__(name="MyCustomAgent", model_name="my-model")
    
    def setup(self) -> bool:
        """Initialize your agent (optional)"""
        print("Setting up MyCustomAgent...")
        return True
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response to the issue"""
        issue = context.issue_data["first_question"]
        
        # Your custom logic here
        response = f"I can help with: {issue['title']}\n\n"
        response += f"Here's my solution for: {issue['body'][:100]}..."
        
        return AgentResponse(
            content=response,
            metadata={"agent_type": "custom", "model": "my-model"}
        )
```

### 2. Test Your Agent

```bash
# Test your custom agent
python test_agent.py --agent my-custom --dataset data/converted_dataset.jsonl
```

## 🔧 Agent Interface

All agents must implement the `CABAgent` interface:

```python
from agent_interface import CABAgent, ConversationContext, AgentResponse

class YourAgent(CABAgent):
    def __init__(self):
        super().__init__(name="YourAgent", model_name="your-model")
    
    def setup(self) -> bool:
        """Optional: Initialize your agent"""
        return True
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Required: Generate response to the issue"""
        # Your implementation here
        pass
```

### Key Components:

- **`name`**: Display name for your agent
- **`model_name`**: Model identifier
- **`setup()`**: Optional initialization (return `True` if successful)
- **`respond()`**: Required method that generates responses

## 🛠️ Creating Custom Agents

### Example 1: Simple Rule-Based Agent

```python
# rule_based_agent.py
from agent_interface import CABAgent, ConversationContext, AgentResponse

class RuleBasedAgent(CABAgent):
    def __init__(self):
        super().__init__(name="RuleBasedAgent", model_name="rules")
    
    def setup(self) -> bool:
        # Load rules or patterns
        self.rules = {
            "import": "Try installing the missing package with pip install",
            "syntax": "Check for syntax errors in your code",
            "timeout": "Consider increasing timeout or optimizing the function"
        }
        return True
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        issue = context.issue_data["first_question"]
        title = issue["title"].lower()
        body = issue["body"].lower()
        
        # Simple rule matching
        response = "Based on your issue, here are some suggestions:\n\n"
        
        if "import" in title or "import" in body:
            response += f"• {self.rules['import']}\n"
        if "syntax" in title or "syntax" in body:
            response += f"• {self.rules['syntax']}\n"
        if "timeout" in title or "timeout" in body:
            response += f"• {self.rules['timeout']}\n"
        
        return AgentResponse(
            content=response,
            metadata={"agent_type": "rule_based", "rules_used": len(self.rules)}
        )
```

### Example 2: API-Based Agent

```python
# api_agent.py
import requests
from agent_interface import CABAgent, ConversationContext, AgentResponse

class APIAgent(CABAgent):
    def __init__(self, api_url: str, api_key: str):
        super().__init__(name="APIAgent", model_name="api-model")
        self.api_url = api_url
        self.api_key = api_key
    
    def setup(self) -> bool:
        # Test API connection
        try:
            response = requests.get(f"{self.api_url}/health", 
                                  headers={"Authorization": f"Bearer {self.api_key}"},
                                  timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        issue = context.issue_data["first_question"]
        
        # Prepare API request
        payload = {
            "prompt": f"Help solve this coding issue: {issue['title']}\n\n{issue['body']}",
            "conversation_history": context.conversation_history
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return AgentResponse(
                    content=result["response"],
                    metadata={"api_url": self.api_url, "status": "success"}
                )
            else:
                return AgentResponse(
                    content="",
                    error=f"API error: {response.status_code}"
                )
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"API request failed: {str(e)}"
            )
```

### Example 3: Local Model Agent

```python
# local_model_agent.py
import subprocess
from agent_interface import CABAgent, ConversationContext, AgentResponse

class LocalModelAgent(CABAgent):
    def __init__(self, model_path: str):
        super().__init__(name="LocalModelAgent", model_name="local-model")
        self.model_path = model_path
    
    def setup(self) -> bool:
        # Check if model file exists
        import os
        return os.path.exists(self.model_path)
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        issue = context.issue_data["first_question"]
        
        # Prepare input for local model
        prompt = f"Question: {issue['title']}\n\n{issue['body']}\n\nAnswer:"
        
        try:
            # Run local model (example with a hypothetical CLI tool)
            result = subprocess.run(
                ["python", "run_local_model.py", "--model", self.model_path, "--input", prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return AgentResponse(
                    content=result.stdout,
                    metadata={"model_path": self.model_path, "status": "success"}
                )
            else:
                return AgentResponse(
                    content="",
                    error=f"Local model error: {result.stderr}"
                )
        except Exception as e:
            return AgentResponse(
                content="",
                error=f"Local model failed: {str(e)}"
            )
```

## 🧪 Testing Your Agent

### Method 1: Direct Testing

```python
# test_my_agent.py
from my_custom_agent import MyCustomAgent
from simulated_user import CABEvaluator

# Create your agent
agent = MyCustomAgent()

# Test with CAB
evaluator = CABEvaluator()
result = evaluator.evaluate_agent(
    agent, 
    "data/converted_dataset.jsonl", 
    max_issues=5
)

print(f"Satisfaction rate: {result.satisfaction_rate:.2%}")
print(f"Average rounds: {result.average_rounds:.1f}")
```

### Method 2: Using the CLI

```bash
# Add your agent to the registry
python -c "
from external_agents import EXTERNAL_AGENT_REGISTRY
from my_custom_agent import MyCustomAgent
EXTERNAL_AGENT_REGISTRY['my-custom'] = lambda: MyCustomAgent()
"

# Test with CLI
python test_agent.py --agent my-custom --dataset data/converted_dataset.jsonl
```

### Method 3: Integration Testing

```python
# integration_test.py
import asyncio
from my_custom_agent import MyCustomAgent
from simulated_user import SimulatedUser

async def test_single_issue():
    # Load a single issue
    import json
    with open("data/converted_dataset.jsonl", "r") as f:
        issue_data = json.loads(f.readline())
    
    # Create agent and simulated user
    agent = MyCustomAgent()
    user = SimulatedUser(max_rounds=3)
    
    # Test conversation
    result = await user.interact(agent, issue_data, ".")
    print(f"Final satisfaction: {result['final_satisfaction']}")
    print(f"Rounds taken: {result['rounds_taken']}")

# Run test
asyncio.run(test_single_issue())
```

## 🔧 Advanced Examples

### Example 4: Multi-Model Agent

```python
# multi_model_agent.py
from agent_interface import CABAgent, ConversationContext, AgentResponse
import random

class MultiModelAgent(CABAgent):
    def __init__(self):
        super().__init__(name="MultiModelAgent", model_name="ensemble")
        self.models = ["model1", "model2", "model3"]
    
    def setup(self) -> bool:
        # Initialize multiple models
        self.model_weights = [0.4, 0.3, 0.3]  # Weighted ensemble
        return True
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        issue = context.issue_data["first_question"]
        
        # Get responses from multiple models
        responses = []
        for model in self.models:
            # Simulate getting response from each model
            response = f"Model {model} suggests: {issue['title'][:50]}..."
            responses.append(response)
        
        # Combine responses (simple example)
        combined_response = "Here are suggestions from multiple models:\n\n"
        for i, response in enumerate(responses):
            combined_response += f"{i+1}. {response}\n"
        
        return AgentResponse(
            content=combined_response,
            metadata={"models_used": self.models, "ensemble": True}
        )
```

### Example 5: Context-Aware Agent

```python
# context_aware_agent.py
from agent_interface import CABAgent, ConversationContext, AgentResponse

class ContextAwareAgent(CABAgent):
    def __init__(self):
        super().__init__(name="ContextAwareAgent", model_name="context-aware")
        self.conversation_memory = {}
    
    def setup(self) -> bool:
        return True
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        issue = context.issue_data["first_question"]
        issue_id = context.issue_data.get("issue_id", "unknown")
        
        # Build context from conversation history
        context_summary = ""
        if context.conversation_history:
            context_summary = "Previous conversation:\n"
            for msg in context.conversation_history[-3:]:  # Last 3 messages
                role = "User" if msg["role"] == "user" else "Assistant"
                context_summary += f"{role}: {msg['content'][:100]}...\n"
        
        # Generate response considering context
        response = f"Based on our conversation history:\n\n{context_summary}\n\n"
        response += f"Current issue: {issue['title']}\n\n"
        response += f"Here's my updated solution: {issue['body'][:100]}..."
        
        # Store in memory
        self.conversation_memory[issue_id] = context.conversation_history
        
        return AgentResponse(
            content=response,
            metadata={"context_used": True, "memory_size": len(self.conversation_memory)}
        )
```

## 📚 Best Practices

### 1. Error Handling

```python
def respond(self, context: ConversationContext) -> AgentResponse:
    try:
        # Your agent logic here
        response = self.generate_response(context)
        return AgentResponse(content=response)
    except Exception as e:
        return AgentResponse(
            content="",
            error=f"Agent error: {str(e)}"
        )
```

### 2. Timeout Management

```python
import signal

class TimeoutAgent(CABAgent):
    def respond(self, context: ConversationContext) -> AgentResponse:
        def timeout_handler(signum, frame):
            raise TimeoutError("Agent response timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout
        
        try:
            response = self.generate_response(context)
            signal.alarm(0)  # Cancel timeout
            return AgentResponse(content=response)
        except TimeoutError:
            return AgentResponse(
                content="",
                error="Response timeout"
            )
```

### 3. Resource Management

```python
class ResourceAwareAgent(CABAgent):
    def __init__(self):
        super().__init__(name="ResourceAwareAgent", model_name="resource-aware")
        self.resource_usage = {"memory": 0, "cpu": 0}
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        # Monitor resource usage
        import psutil
        process = psutil.Process()
        
        memory_before = process.memory_info().rss
        cpu_before = process.cpu_percent()
        
        # Generate response
        response = self.generate_response(context)
        
        # Track resource usage
        memory_after = process.memory_info().rss
        cpu_after = process.cpu_percent()
        
        self.resource_usage["memory"] += memory_after - memory_before
        self.resource_usage["cpu"] += cpu_after - cpu_before
        
        return AgentResponse(
            content=response,
            metadata={"resource_usage": self.resource_usage}
        )
```

## 🔍 Troubleshooting

### Common Issues

1. **Import Errors**
   ```python
   # Make sure to import from the correct module
   from agent_interface import CABAgent, ConversationContext, AgentResponse
   ```

2. **Setup Failures**
   ```python
   def setup(self) -> bool:
       try:
           # Your setup code
           return True
       except Exception as e:
           print(f"Setup failed: {e}")
           return False
   ```

3. **Response Format**
   ```python
   # Always return AgentResponse object
   return AgentResponse(
       content="Your response here",
       metadata={"key": "value"}  # Optional
   )
   ```

4. **Timeout Issues**
   ```python
   # Use reasonable timeouts
   result = subprocess.run(cmd, timeout=60)  # 60 seconds max
   ```

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test with verbose output
python test_agent.py --agent my-custom --dataset data/converted_dataset.jsonl --verbose
```

## 🎯 Next Steps

1. **Create your agent** following the examples above
2. **Test with a small dataset** first (`--max-issues 1`)
3. **Add error handling** and resource management
4. **Optimize performance** based on evaluation results
5. **Share your agent** with the community!

## 📞 Support

- Check the [README.md](README.md) for general usage
- Look at existing agents in `external_agents.py` for examples
- Test with the mock agent first to understand the interface
- Use `--verbose` flag for detailed debugging information

Happy coding! 🚀
