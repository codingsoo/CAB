#!/usr/bin/env python3
"""
Example Custom Agent for CAB (CodeAssistBench)
This is a template that users can modify to create their own agents.
"""

from agent_interface import CABAgent, ConversationContext, AgentResponse
import json
import random

class ExampleCustomAgent(CABAgent):
    """
    Example custom agent that demonstrates how to create your own agent.
    Modify this class to implement your own AI agent logic.
    """
    
    def __init__(self, name: str = "ExampleCustomAgent", model_name: str = "example-model"):
        super().__init__(name=name, model_name=model_name)
        self.response_templates = [
            "I can help you with that issue. Here's what I suggest:",
            "Based on your problem, I recommend the following solution:",
            "Let me analyze your issue and provide a solution:",
            "I understand your problem. Here's how to fix it:"
        ]
    
    def setup(self) -> bool:
        """
        Initialize your agent.
        This method is called once when the agent is created.
        Return True if setup is successful, False otherwise.
        """
        print(f"🚀 Setting up {self.name}...")
        
        # Example: Load configuration, initialize models, etc.
        try:
            # Simulate loading some configuration
            self.config = {
                "max_response_length": 500,
                "include_code_examples": True,
                "response_style": "helpful"
            }
            
            print(f"✅ {self.name} setup completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ {self.name} setup failed: {e}")
            return False
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """
        Generate a response to the given issue.
        This is the main method that will be called for each issue.
        
        Args:
            context: Contains the issue data and conversation history
            
        Returns:
            AgentResponse: Your agent's response to the issue
        """
        try:
            # Extract issue information
            issue = context.issue_data["first_question"]
            title = issue["title"]
            body = issue["body"]
            issue_id = context.issue_data.get("issue_id", "unknown")
            
            # Build response based on issue content
            response = self._generate_response(title, body, context.conversation_history)
            
            # Create metadata (optional but useful for debugging)
            metadata = {
                "agent_type": "custom",
                "model": self.model_name,
                "issue_id": issue_id,
                "response_length": len(response),
                "conversation_round": len(context.conversation_history) + 1
            }
            
            return AgentResponse(
                content=response,
                metadata=metadata
            )
            
        except Exception as e:
            # Always handle errors gracefully
            return AgentResponse(
                content="",
                error=f"Error generating response: {str(e)}"
            )
    
    def _generate_response(self, title: str, body: str, conversation_history: list) -> str:
        """
        Generate the actual response content.
        Modify this method to implement your agent's logic.
        """
        # Choose a random template
        template = random.choice(self.response_templates)
        
        # Build the response
        response = f"{template}\n\n"
        response += f"**Issue:** {title}\n\n"
        response += f"**Description:** {body[:200]}{'...' if len(body) > 200 else ''}\n\n"
        
        # Add some basic analysis based on keywords
        analysis = self._analyze_issue(title, body)
        response += f"**Analysis:** {analysis}\n\n"
        
        # Add a solution
        solution = self._generate_solution(title, body)
        response += f"**Solution:** {solution}\n\n"
        
        # Add code example if relevant
        if self._needs_code_example(title, body):
            code_example = self._generate_code_example(title, body)
            response += f"**Code Example:**\n```python\n{code_example}\n```\n\n"
        
        # Consider conversation history
        if conversation_history:
            response += f"**Note:** This is round {len(conversation_history) + 1} of our conversation. "
            response += "I'm building on our previous discussion.\n\n"
        
        response += "Let me know if you need any clarification or have additional questions!"
        
        return response
    
    def _analyze_issue(self, title: str, body: str) -> str:
        """Analyze the issue and provide insights."""
        text = (title + " " + body).lower()
        
        if "error" in text:
            return "This appears to be an error-related issue. Let's identify the root cause."
        elif "performance" in text or "slow" in text:
            return "This seems to be a performance issue. Optimization strategies will be needed."
        elif "import" in text or "module" in text:
            return "This looks like a dependency or import issue. Let's check the imports."
        elif "syntax" in text:
            return "This appears to be a syntax error. Let's review the code structure."
        else:
            return "This is a general coding issue. Let's work through it step by step."
    
    def _generate_solution(self, title: str, body: str) -> str:
        """Generate a solution based on the issue."""
        text = (title + " " + body).lower()
        
        if "error" in text:
            return "1. Check the error message carefully\n2. Verify your code syntax\n3. Ensure all dependencies are installed\n4. Test with a minimal example"
        elif "performance" in text:
            return "1. Profile your code to identify bottlenecks\n2. Consider using more efficient algorithms\n3. Optimize data structures\n4. Use caching where appropriate"
        elif "import" in text:
            return "1. Check if the module is installed\n2. Verify the import path\n3. Check for typos in module names\n4. Ensure Python path is correct"
        else:
            return "1. Break down the problem into smaller parts\n2. Test each component individually\n3. Use debugging tools\n4. Consult documentation and examples"
    
    def _needs_code_example(self, title: str, body: str) -> bool:
        """Determine if a code example would be helpful."""
        text = (title + " " + body).lower()
        code_keywords = ["code", "function", "class", "method", "variable", "loop", "if", "for", "while"]
        return any(keyword in text for keyword in code_keywords)
    
    def _generate_code_example(self, title: str, body: str) -> str:
        """Generate a relevant code example."""
        text = (title + " " + body).lower()
        
        if "function" in text:
            return """def example_function(param1, param2):
    \"\"\"Example function to solve your issue.\"\"\"
    result = param1 + param2
    return result

# Usage
result = example_function(1, 2)
print(result)"""
        elif "class" in text:
            return """class ExampleClass:
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        return self.value

# Usage
obj = ExampleClass(42)
print(obj.get_value())"""
        elif "error" in text:
            return """try:
    # Your code here
    result = risky_operation()
except Exception as e:
    print(f"Error occurred: {e}")
    # Handle the error appropriately"""
        else:
            return """# Example solution
def solve_problem():
    # Your implementation here
    pass

# Test the solution
if __name__ == "__main__":
    solve_problem()"""


# Example of how to use this custom agent
def main():
    """Example usage of the custom agent."""
    print("🤖 Example Custom Agent Demo")
    print("=" * 40)
    
    # Create the agent
    agent = ExampleCustomAgent()
    
    # Test setup
    if agent.setup():
        print("✅ Agent setup successful!")
        
        # Create a mock conversation context
        mock_context = ConversationContext(
            issue_data={
                "issue_id": "test_001",
                "first_question": {
                    "title": "Python import error",
                    "body": "I'm getting an ImportError when trying to import pandas. How can I fix this?"
                }
            },
            conversation_history=[],
            repository_path="."
        )
        
        # Test response generation
        print("\n🧪 Testing response generation...")
        response = agent.respond(mock_context)
        
        print(f"\n📝 Agent Response:")
        print("-" * 40)
        print(response.content)
        print(f"\n📊 Metadata: {response.metadata}")
        
        if response.error:
            print(f"❌ Error: {response.error}")
    
    else:
        print("❌ Agent setup failed!")


if __name__ == "__main__":
    main()
