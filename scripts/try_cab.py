#!/usr/bin/env python3
"""
Try CAB - See what CAB can do without any setup!
"""

import json
import sys
from pathlib import Path

def print_banner():
    """Print the CAB banner"""
    print("🚀" + "="*50 + "🚀")
    print("   Try CAB - See What It Can Do!")
    print("   NeurIPS 2025 Datasets & Benchmarks Track")
    print("🚀" + "="*50 + "🚀")

def show_sample_issue():
    """Show a sample issue from CAB"""
    print("\n📝 Sample Issue from CAB Dataset:")
    print("-" * 50)
    
    sample_issue = {
        "title": "Python function returning None instead of expected value",
        "body": "I have a Python function that should return a list, but it's returning None. Can you help me debug this?",
        "conversation": [
            {"role": "user", "content": "Here's my function:\n```python\ndef process_data(data):\n    result = []\n    for item in data:\n        result.append(item * 2)\n    # Missing return statement!\n```"},
            {"role": "maintainer", "content": "I see the issue! You're missing the `return result` statement at the end of your function."}
        ],
        "satisfaction_conditions": [
            "The user should understand what caused the function to return None",
            "The solution should fix the missing return statement",
            "The explanation should be clear and include code examples"
        ]
    }
    
    print(f"Title: {sample_issue['title']}")
    print(f"Description: {sample_issue['body']}")
    print(f"\nConversation:")
    for i, msg in enumerate(sample_issue['conversation'], 1):
        role = "👤 User" if msg['role'] == 'user' else "🤖 Maintainer"
        print(f"  {i}. {role}: {msg['content'][:100]}...")
    
    print(f"\nSatisfaction Conditions:")
    for i, condition in enumerate(sample_issue['satisfaction_conditions'], 1):
        print(f"  {i}. {condition}")

def show_agent_examples():
    """Show examples of different agents"""
    print("\n🤖 AI Agents CAB Can Test:")
    print("-" * 50)
    
    agents = [
        {
            "name": "Mock Agent",
            "description": "Simple rule-based agent for testing",
            "example_response": "I understand your problem. Here's how to fix it:\n\n**Issue:** Python function returning None\n\n**Solution:** Add `return result` at the end of your function.\n\n**Explanation:** The function processes the data but doesn't return the result."
        },
        {
            "name": "Cursor CLI Agent",
            "description": "Uses Cursor CLI for code assistance",
            "example_response": "Looking at your function, the issue is clear - you're missing the return statement. Here's the fix:\n\n```python\ndef process_data(data):\n    result = []\n    for item in data:\n        result.append(item * 2)\n    return result  # Add this line!\n```"
        },
        {
            "name": "Amazon Q CLI Agent",
            "description": "Uses Amazon Q CLI for AI-powered assistance",
            "example_response": "The problem is that your function doesn't return the processed data. In Python, functions that don't explicitly return a value return `None` by default. Add `return result` at the end of your function."
        }
    ]
    
    for i, agent in enumerate(agents, 1):
        print(f"\n{i}. {agent['name']}")
        print(f"   Description: {agent['description']}")
        print(f"   Example Response: {agent['example_response'][:100]}...")

def show_judge_examples():
    """Show examples of different judges"""
    print("\n⚖️ AI Judges CAB Can Use:")
    print("-" * 50)
    
    judges = [
        {
            "name": "Built-in LLM Judge",
            "description": "Uses Claude/OpenAI to evaluate responses",
            "evaluation": "TECHNICAL CORRECTNESS: CORRECT\nALIGNMENT SCORE: 3/3 CONDITIONS MET (100%)\nVERDICT: CORRECT"
        },
        {
            "name": "Amazon Q CLI Judge",
            "description": "Uses Amazon Q CLI to evaluate responses",
            "evaluation": "TECHNICAL CORRECTNESS: CORRECT\nALIGNMENT SCORE: 3/3 CONDITIONS MET (100%)\nVERDICT: CORRECT"
        },
        {
            "name": "Cursor CLI Judge",
            "description": "Uses Cursor CLI to evaluate responses",
            "evaluation": "TECHNICAL CORRECTNESS: CORRECT\nALIGNMENT SCORE: 3/3 CONDITIONS MET (100%)\nVERDICT: CORRECT"
        }
    ]
    
    for i, judge in enumerate(judges, 1):
        print(f"\n{i}. {judge['name']}")
        print(f"   Description: {judge['description']}")
        print(f"   Example Evaluation: {judge['evaluation']}")

def show_sample_results():
    """Show sample evaluation results"""
    print("\n📊 Sample Evaluation Results:")
    print("-" * 50)
    
    results = {
        "agent": "MockAgent",
        "total_issues": 3,
        "successful_conversations": 3,
        "failed_conversations": 0,
        "satisfaction_rate": 100.0,
        "average_rounds": 1.2,
        "average_duration": 0.5,
        "judge_verdicts": {
            "CORRECT": 2,
            "PARTIALLY_CORRECT": 1,
            "INCORRECT": 0
        }
    }
    
    print(f"Agent: {results['agent']}")
    print(f"Total Issues: {results['total_issues']}")
    print(f"Success Rate: {results['satisfaction_rate']:.1f}%")
    print(f"Average Rounds: {results['average_rounds']:.1f}")
    print(f"Average Duration: {results['average_duration']:.1f}s")
    print(f"\nJudge Verdicts:")
    for verdict, count in results['judge_verdicts'].items():
        print(f"  {verdict}: {count}")

def show_what_cab_does():
    """Show what CAB can do"""
    print("\n🎯 What CAB Can Do:")
    print("-" * 50)
    
    capabilities = [
        "🧪 Test any AI coding assistant",
        "📊 Evaluate responses with multiple AI judges",
        "🔄 Support multi-turn conversations",
        "🐳 Test in Docker environments",
        "📈 Compare different AI models",
        "🎮 Work with external tools (Cursor CLI, Amazon Q, etc.)",
        "📝 Use real GitHub issues as test cases",
        "⚖️ Provide objective, reproducible evaluations"
    ]
    
    for capability in capabilities:
        print(f"  {capability}")

def show_next_steps():
    """Show what the user can do next"""
    print("\n🚀 Ready to Try CAB?")
    print("-" * 50)
    
    print("\n1. 🚀 Super Easy Setup (Recommended):")
    print("   python super_easy_setup.py")
    
    print("\n2. 🎮 Quick Test (No setup required):")
    print("   python test_agent.py --agent mock --dataset data/converted_dataset.jsonl --max-issues 1")
    
    print("\n3. 📚 Learn More:")
    print("   cat README.md")
    print("   cat SUPER_EASY_START.md")
    
    print("\n4. 🤖 Test External Agents:")
    print("   python test_external_agents.py")
    
    print("\n5. ⚖️ Test External Judges:")
    print("   python test_judge_agents.py")

def main():
    """Main function"""
    print_banner()
    
    show_sample_issue()
    show_agent_examples()
    show_judge_examples()
    show_sample_results()
    show_what_cab_does()
    show_next_steps()
    
    print("\n🎉 CAB is ready to benchmark AI coding assistants!")
    print("   Try it now: python super_easy_setup.py")

if __name__ == "__main__":
    main()
