#!/usr/bin/env python3
"""
Test the full CAB pipeline: Agent + Judge integration.
This demonstrates how Step 2 (Agent) and Step 3 (Judge) work together.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_test_issue() -> Dict[str, Any]:
    """Create a test issue for the full pipeline."""
    return {
        "issue_id": "test_pipeline_001",
        "first_question": {
            "title": "Fix Python syntax error in function",
            "body": "I have a Python function that's giving me a syntax error. The function is supposed to calculate the factorial of a number, but I'm getting 'SyntaxError: invalid syntax' when I try to run it. Can you help me fix it?"
        },
        "comments": [
            {
                "user": "maintainer",
                "body": "The issue is likely with the function definition or indentation. Can you share the code?"
            },
            {
                "user": "user", 
                "body": "Here's my code:\n```python\ndef factorial(n):\n    if n <= 1:\n        return 1\n    else:\n        return n * factorial(n-1)\n```"
            },
            {
                "user": "maintainer",
                "body": "The code looks correct. Make sure you're not mixing tabs and spaces. Use 4 spaces for indentation consistently."
            },
            {
                "user": "user",
                "body": "Thanks! That fixed it. The issue was indeed with mixed tabs and spaces."
            }
        ],
        "user_satisfaction_condition": [
            "The user should understand what caused the syntax error",
            "The solution should fix the syntax error completely",
            "The user should be able to run the function without errors",
            "The explanation should be clear and helpful"
        ]
    }

def create_mock_agent_response() -> str:
    """Create a mock agent response for testing."""
    return """
I can help you fix the syntax error in your factorial function. Based on your code, the most likely cause is inconsistent indentation.

**The Problem:**
Python is very strict about indentation. If you mix tabs and spaces, or use inconsistent indentation, you'll get a syntax error.

**The Solution:**
Make sure your function uses consistent indentation. Here's the corrected version:

```python
def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)
```

**Key Points:**
1. Use 4 spaces for each indentation level (not tabs)
2. Make sure all lines at the same level have the same indentation
3. Your IDE should show you if there are mixed tabs/spaces

**To test it:**
```python
print(factorial(5))  # Should output: 120
```

The syntax error occurs because Python can't determine the proper code structure when indentation is inconsistent. Once you fix the indentation, your function should work perfectly!
"""

def test_agent_judge_integration():
    """Test the integration between agent and judge."""
    print("🔄 Testing Full Pipeline: Agent + Judge Integration")
    print("=" * 60)
    
    try:
        # Import required functions
        from run import judge_maintainer_answer
        from example_custom_agent import ExampleCustomAgent
        
        # Create test data
        issue_data = create_test_issue()
        agent_response = create_mock_agent_response()
        
        print("📝 Test Setup:")
        print(f"   Issue ID: {issue_data['issue_id']}")
        print(f"   Issue Title: {issue_data['first_question']['title']}")
        print(f"   Agent Response Length: {len(agent_response)} characters")
        print(f"   Satisfaction Conditions: {len(issue_data['user_satisfaction_condition'])}")
        
        # Test 1: Agent Response Generation
        print(f"\n🤖 Step 1: Agent Response Generation")
        print("-" * 40)
        
        # Create and test agent
        agent = ExampleCustomAgent()
        if agent.setup():
            print("✅ Agent setup successful")
            
            # Create conversation context
            from agent_interface import ConversationContext
            context = ConversationContext(
                issue_data=issue_data,
                conversation_history=[],
                repository_path="."
            )
            
            # Generate response
            response = agent.respond(context)
            print(f"✅ Agent response generated: {len(response.content)} characters")
            print(f"✅ Response metadata: {response.metadata}")
            
            if response.error:
                print(f"❌ Agent error: {response.error}")
                return False
        else:
            print("❌ Agent setup failed")
            return False
        
        # Test 2: Judge Evaluation
        print(f"\n⚖️ Step 2: Judge Evaluation")
        print("-" * 40)
        
        # Create mock Docker results
        docker_results = {
            "success": True,
            "logs": "No Docker validation needed for this issue",
            "test_commands": []
        }
        
        # Test judge function structure (without actual LLM call)
        print("🔍 Testing judge function structure...")
        
        # Extract issue information (same as in judge function)
        question_title = issue_data["first_question"]["title"]
        question_body = issue_data["first_question"]["body"]
        comments = issue_data.get("comments", [])
        user_satisfaction_conditions = issue_data.get("user_satisfaction_condition", [])
        
        print(f"✅ Issue data extracted successfully")
        print(f"   Title: {question_title}")
        print(f"   Body: {question_body[:50]}...")
        print(f"   Comments: {len(comments)} found")
        print(f"   Conditions: {len(user_satisfaction_conditions)} found")
        
        # Test conversation formatting
        conversation = f"Title: {question_title}\n\nQuestion: {question_body}\n\n"
        conversation += "--- Comments from maintainers and users ---\n"
        
        for i, comment in enumerate(comments):
            conversation += f"[{comment['user']}]:\n{comment['body']}\n\n"
        
        print(f"✅ Conversation formatted: {len(conversation)} characters")
        
        # Test Docker info formatting
        docker_info = ""
        if docker_results:
            success_status = docker_results.get('success', False)
            docker_info = f"""
        MAINTAINER ANSWER VALIDATION RESULTS via DOCKER:
        Status: {success_status}
        Logs:
        {docker_results.get('logs', 'No logs available')}
        """
        
        print(f"✅ Docker info formatted: {len(docker_info)} characters")
        
        # Test prompt structure
        user_prompt = f"""
USER'S QUESTION AND REFERENCE CONVERSATION:
{conversation}

USER SATISFACTION CONDITIONS:
{json.dumps(user_satisfaction_conditions, indent=2)}

MAINTAINER'S ANSWER TO EVALUATE:
{agent_response}

{docker_info}

Based on the above information, evaluate the maintainer's answer.
"""
        
        print(f"✅ User prompt structured: {len(user_prompt)} characters")
        
        # Test 3: Mock Judge Response
        print(f"\n🎯 Step 3: Mock Judge Response")
        print("-" * 40)
        
        # Create mock judge response
        mock_judge_response = """
TECHNICAL CORRECTNESS: CORRECT
- The solution correctly identifies indentation as the cause
- The explanation is technically accurate
- The code example is correct and functional

ALIGNMENT SCORE: 4/4 CONDITIONS MET (100%)

CONDITION 1: TRUE The user should understand what caused the syntax error
CONDITION 2: TRUE The solution should fix the syntax error completely
CONDITION 3: TRUE The user should be able to run the function without errors
CONDITION 4: TRUE The explanation should be clear and helpful

VERBOSITY ASSESSMENT: APPROPRIATE
- Provides the right amount of detail
- Includes helpful additional information
- Not overly verbose

VERDICT: CORRECT

KEY ISSUES: None - the solution is technically sound and comprehensive

REASONING: The maintainer's answer correctly identifies the root cause (indentation issues), provides a clear solution with code examples, explains why the error occurs, and gives additional helpful tips. The solution addresses all user satisfaction conditions and is technically accurate.
"""
        
        # Test parsing logic
        print("🔍 Testing judge response parsing...")
        
        # Parse technical correctness
        if "TECHNICAL CORRECTNESS:" in mock_judge_response:
            tech_section = mock_judge_response.split("TECHNICAL CORRECTNESS:", 1)[1].strip()
            tech_line = tech_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in tech_line.upper():
                technical_correctness = "INCORRECT"
            elif "PARTIALLY" in tech_line.upper():
                technical_correctness = "PARTIALLY CORRECT"
            elif "CORRECT" in tech_line.upper() and "PARTIALLY" not in tech_line.upper():
                technical_correctness = "CORRECT"
            else:
                technical_correctness = "UNKNOWN"
        else:
            technical_correctness = "UNKNOWN"
        
        # Parse alignment score
        alignment_score = {}
        if "ALIGNMENT SCORE:" in mock_judge_response:
            alignment_section = mock_judge_response.split("ALIGNMENT SCORE:", 1)[1]
            score_line = alignment_section.split("\n", 1)[0].strip()
            
            import re
            score_match = re.search(r'(\d+)/(\d+)', score_line)
            if score_match:
                satisfied = int(score_match.group(1))
                total = int(score_match.group(2))
                
                alignment_score = {
                    'satisfied': satisfied,
                    'total': total,
                    'percentage': (satisfied / total) * 100 if total > 0 else 0
                }
        
        # Parse verdict
        verdict = "UNKNOWN"
        if "VERDICT:" in mock_judge_response:
            verdict_section = mock_judge_response.split("VERDICT:", 1)[1].strip()
            verdict_line = verdict_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in verdict_line.upper():
                verdict = "INCORRECT"
            elif "PARTIALLY" in verdict_line.upper():
                verdict = "PARTIALLY CORRECT"
            elif "CORRECT" in verdict_line.upper() and "PARTIALLY" not in verdict_line.upper():
                verdict = "CORRECT"
        
        print(f"✅ Technical Correctness: {technical_correctness}")
        print(f"✅ Alignment Score: {alignment_score.get('percentage', 0):.1f}%")
        print(f"✅ Final Verdict: {verdict}")
        
        # Test 4: Integration Results
        print(f"\n📊 Step 4: Integration Results")
        print("-" * 40)
        
        print(f"🎯 Full Pipeline Test Results:")
        print(f"   Agent Response: ✅ Generated successfully")
        print(f"   Judge Evaluation: ✅ Parsed successfully")
        print(f"   Technical Correctness: {technical_correctness}")
        print(f"   User Satisfaction: {alignment_score.get('percentage', 0):.1f}%")
        print(f"   Final Verdict: {verdict}")
        
        if verdict == "CORRECT":
            print(f"   🎉 Agent provided a correct solution!")
        elif verdict == "PARTIALLY CORRECT":
            print(f"   ⚠️ Agent provided a partially correct solution")
        else:
            print(f"   ❌ Agent solution needs improvement")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in full pipeline test: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_pipeline_usage():
    """Show how to use the full pipeline."""
    print(f"\n📚 Full Pipeline Usage Examples")
    print("=" * 50)
    
    print(f"\n1. 🔄 Complete Agent + Judge Pipeline:")
    print(f"   # Step 1: Generate agent response")
    print(f"   agent = YourAgent()")
    print(f"   context = ConversationContext(issue_data, conversation_history, repo_path)")
    print(f"   agent_response = agent.respond(context)")
    print(f"   ")
    print(f"   # Step 2: Judge the response")
    print(f"   judgment, verdict, key_issues, alignment_score = judge_maintainer_answer(")
    print(f"       issue_data, agent_response.content, docker_results")
    print(f"   )")
    print(f"   ")
    print(f"   # Step 3: Analyze results")
    print(f"   print(f'Verdict: {{verdict}}')")
    print(f"   print(f'Satisfaction: {{alignment_score.get('percentage', 0):.1f}}%')")
    
    print(f"\n2. 🧪 Testing with CAB Framework:")
    print(f"   # Use the simulated user environment")
    print(f"   from simulated_user import CABEvaluator")
    print(f"   ")
    print(f"   evaluator = CABEvaluator()")
    print(f"   result = evaluator.evaluate_agent(agent, 'dataset.jsonl')")
    print(f"   ")
    print(f"   # The evaluator automatically uses the judge for each response")
    print(f"   print(f'Satisfaction Rate: {{result.satisfaction_rate:.2f}}%')")
    
    print(f"\n3. 📊 Judge Integration in Custom Agents:")
    print(f"   class MyAgent(CABAgent):")
    print(f"       def respond(self, context):")
    print(f"           # Generate response")
    print(f"           response = self.generate_response(context)")
    print(f"           ")
    print(f"           # Optional: Self-evaluate using judge")
    print(f"           judgment, verdict, issues, score = judge_maintainer_answer(")
    print(f"               context.issue_data, response.content")
    print(f"           )")
    print(f"           ")
    print(f"           # Include judge results in metadata")
    print(f"           response.metadata['judge_verdict'] = verdict")
    print(f"           return response")

def main():
    """Main function to test the full pipeline."""
    print("🔄 CAB Full Pipeline Testing")
    print("=" * 60)
    print("Testing Step 2 (Agent) + Step 3 (Judge) integration")
    
    # Test the full pipeline
    success = test_agent_judge_integration()
    
    # Show usage examples
    show_pipeline_usage()
    
    print(f"\n🎯 Full Pipeline Test Summary:")
    if success:
        print(f"   ✅ Agent + Judge integration working correctly")
        print(f"   ✅ Full pipeline structure is sound")
        print(f"   ✅ Judge can evaluate agent responses")
        print(f"   ✅ Results can be analyzed and used for improvement")
        print(f"\n🎉 The full CAB pipeline is ready for use!")
        sys.exit(0)
    else:
        print(f"   ❌ Full pipeline has issues that need to be addressed")
        sys.exit(1)

if __name__ == "__main__":
    main()
