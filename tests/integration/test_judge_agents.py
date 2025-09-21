#!/usr/bin/env python3
"""
Test script for Judge Agents (Amazon Q CLI, Cursor CLI, Local LLMs as judges).
This tests using external AI tools as judges for evaluating agent responses.
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
    """Create a test issue for judge testing."""
    return {
        "issue_id": "test_judge_001",
        "first_question": {
            "title": "Python function not working correctly",
            "body": "I have a Python function that's supposed to calculate the sum of a list, but it's returning 0 instead of the actual sum. Can you help me debug this?"
        },
        "comments": [
            {
                "user": "maintainer",
                "body": "Can you share the code? It sounds like there might be an issue with the function logic."
            },
            {
                "user": "user",
                "body": "Here's my code:\n```python\ndef sum_list(numbers):\n    total = 0\n    for num in numbers:\n        total += num\n    return total\n\nresult = sum_list([1, 2, 3, 4, 5])\nprint(result)  # This prints 0 instead of 15\n```"
            },
            {
                "user": "maintainer",
                "body": "The code looks correct. Are you sure the list `[1, 2, 3, 4, 5]` is being passed correctly? Try adding some debug prints to see what's happening."
            },
            {
                "user": "user",
                "body": "Thanks! I found the issue - I was accidentally passing an empty list. The function works fine now."
            }
        ],
        "user_satisfaction_condition": [
            "The user should understand what caused the function to return 0",
            "The solution should help debug the issue effectively",
            "The user should be able to fix the problem",
            "The explanation should be clear and helpful"
        ]
    }

def create_test_agent_response() -> str:
    """Create a test agent response for judge evaluation."""
    return """
I can help you debug this issue! Looking at your code, the function itself is actually correct. The problem is likely that you're passing an empty list or the list isn't being passed correctly.

**Debugging Steps:**

1. **Check what you're actually passing:**
   ```python
   def sum_list(numbers):
       print(f"Input: {numbers}")  # Debug print
       print(f"Type: {type(numbers)}")  # Debug print
       total = 0
       for num in numbers:
           total += num
       return total
   
   result = sum_list([1, 2, 3, 4, 5])
   print(result)
   ```

2. **Verify the list is not empty:**
   ```python
   numbers = [1, 2, 3, 4, 5]
   print(f"List length: {len(numbers)}")
   print(f"List contents: {numbers}")
   ```

3. **Test with a simple case:**
   ```python
   # Test with a known list
   test_list = [1, 2, 3]
   result = sum_list(test_list)
   print(f"Sum of {test_list} = {result}")  # Should print 6
   ```

**Common Causes:**
- Accidentally passing an empty list `[]`
- Variable name confusion (passing wrong variable)
- List being modified before the function call
- Indentation issues (though your code looks fine)

**The Fix:**
Once you identify what's actually being passed to the function, you can fix the root cause. The function logic itself is correct!

Let me know what the debug prints show and I can help you further.
"""

def test_judge_agent(judge_type: str, issue_data: Dict[str, Any], agent_response: str) -> bool:
    """Test a specific judge agent."""
    print(f"\n⚖️ Testing {judge_type} Judge")
    print("-" * 40)
    
    try:
        from judge_agents import create_judge
        
        # Create judge instance
        judge = create_judge(judge_type)
        
        # Test setup
        print(f"🔧 Testing {judge.name} setup...")
        if not judge.setup():
            print(f"❌ {judge.name} setup failed")
            return False
        
        print(f"✅ {judge.name} setup successful")
        
        # Test judgment
        print(f"🧪 Testing judgment...")
        judgment, verdict, key_issues, alignment_score = judge.judge_response(
            issue_data, agent_response
        )
        
        # Display results
        print(f"\n📊 Judge Results:")
        print(f"   Verdict: {verdict}")
        print(f"   Technical Correctness: {alignment_score.get('technical_correctness', 'UNKNOWN')}")
        print(f"   Satisfaction Rate: {alignment_score.get('percentage', 0):.1f}%")
        print(f"   Key Issues: {len(key_issues)} found")
        
        if key_issues:
            print(f"   Issues:")
            for i, issue in enumerate(key_issues[:3], 1):  # Show first 3 issues
                print(f"     {i}. {issue}")
        
        print(f"   Judgment Length: {len(judgment)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing {judge_type} judge: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_all_judges():
    """Test all available judge agents."""
    print("⚖️ Testing All Judge Agents")
    print("=" * 60)
    
    # Create test data
    issue_data = create_test_issue()
    agent_response = create_test_agent_response()
    
    print("📝 Test Data Created:")
    print(f"   Issue ID: {issue_data['issue_id']}")
    print(f"   Issue Title: {issue_data['first_question']['title']}")
    print(f"   Agent Response Length: {len(agent_response)} characters")
    print(f"   Satisfaction Conditions: {len(issue_data['user_satisfaction_condition'])}")
    
    # Test each judge
    from judge_agents import JUDGE_REGISTRY
    
    results = {}
    for judge_type in JUDGE_REGISTRY.keys():
        success = test_judge_agent(judge_type, issue_data, agent_response)
        results[judge_type] = success
    
    # Summary
    print(f"\n🎯 Judge Testing Summary:")
    print("=" * 40)
    
    successful_judges = []
    failed_judges = []
    
    for judge_type, success in results.items():
        if success:
            successful_judges.append(judge_type)
            print(f"   ✅ {judge_type}: Working")
        else:
            failed_judges.append(judge_type)
            print(f"   ❌ {judge_type}: Failed")
    
    print(f"\n📊 Results:")
    print(f"   Successful: {len(successful_judges)}/{len(results)}")
    print(f"   Failed: {len(failed_judges)}/{len(results)}")
    
    if successful_judges:
        print(f"\n🎉 Working Judges:")
        for judge in successful_judges:
            print(f"   • {judge}")
    
    if failed_judges:
        print(f"\n⚠️ Failed Judges:")
        for judge in failed_judges:
            print(f"   • {judge}")
    
    return len(successful_judges) > 0

def show_judge_usage_examples():
    """Show examples of how to use judge agents."""
    print(f"\n📚 Judge Agent Usage Examples")
    print("=" * 50)
    
    print(f"\n1. 🧪 Basic Judge Usage:")
    print(f"   from judge_agents import create_judge")
    print(f"   ")
    print(f"   # Create a judge")
    print(f"   judge = create_judge('amazon-q')")
    print(f"   ")
    print(f"   # Judge an agent response")
    print(f"   judgment, verdict, key_issues, alignment_score = judge.judge_response(")
    print(f"       issue_data, agent_response, docker_results")
    print(f"   )")
    print(f"   ")
    print(f"   print(f'Verdict: {{verdict}}')")
    print(f"   print(f'Satisfaction: {{alignment_score.get('percentage', 0):.1f}}%')")
    
    print(f"\n2. 🔄 Judge in Agent Evaluation:")
    print(f"   from judge_agents import create_judge")
    print(f"   from simulated_user import CABEvaluator")
    print(f"   ")
    print(f"   # Create judge and evaluator")
    print(f"   judge = create_judge('cursor-cli')")
    print(f"   evaluator = CABEvaluator()")
    print(f"   ")
    print(f"   # Evaluate agent with custom judge")
    print(f"   result = evaluator.evaluate_agent_with_judge(")
    print(f"       agent, 'dataset.jsonl', judge")
    print(f"   )")
    
    print(f"\n3. 📊 Compare Multiple Judges:")
    print(f"   judges = ['amazon-q', 'cursor-cli', 'local-llama2']")
    print(f"   results = {{}}")
    print(f"   ")
    print(f"   for judge_type in judges:")
    print(f"       judge = create_judge(judge_type)")
    print(f"       if judge.setup():")
    print(f"           judgment, verdict, issues, score = judge.judge_response(")
    print(f"               issue_data, agent_response")
    print(f"           )")
    print(f"           results[judge_type] = {{")
    print(f"               'verdict': verdict,")
    print(f"               'satisfaction': score.get('percentage', 0)")
    print(f"           }}")
    
    print(f"\n4. 🎯 Available Judges:")
    print(f"   • amazon-q: Amazon Q CLI judge")
    print(f"   • cursor-cli: Cursor CLI judge")
    print(f"   • local-llama2: Local LLM (Llama2) judge")
    print(f"   • local-codellama: Local LLM (CodeLlama) judge")
    print(f"   • local-mistral: Local LLM (Mistral) judge")

def main():
    """Main function to test judge agents."""
    print("⚖️ CAB Judge Agents Testing")
    print("=" * 60)
    print("Testing external AI tools as judges for agent evaluation")
    
    # Test all judges
    success = test_all_judges()
    
    # Show usage examples
    show_judge_usage_examples()
    
    print(f"\n🎯 Judge Agents Test Summary:")
    if success:
        print(f"   ✅ At least one judge agent is working")
        print(f"   ✅ External AI tools can be used as judges")
        print(f"   ✅ Judge agents provide structured evaluations")
        print(f"   ✅ Multiple judge types are available")
        print(f"\n🎉 Judge agents are ready for use!")
        sys.exit(0)
    else:
        print(f"   ❌ No judge agents are working")
        print(f"   ⚠️ Check that external tools are installed and configured")
        sys.exit(1)

if __name__ == "__main__":
    main()
