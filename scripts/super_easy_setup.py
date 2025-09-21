#!/usr/bin/env python3
"""
Super Easy Setup for CAB - Get everything running in one command!
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_banner():
    """Print the CAB banner"""
    print("🚀" + "="*60 + "🚀")
    print("   CAB: CodeAssistBench - Super Easy Setup")
    print("   NeurIPS 2025 Datasets & Benchmarks Track")
    print("🚀" + "="*60 + "🚀")

def check_python_version():
    """Check if Python version is compatible"""
    print("\n🔍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_directories():
    """Create necessary directories"""
    print("\n📁 Setting up directories...")
    directories = [
        "data",
        "data/results",
        "data/results/dataset",
        "data/results/agent_evaluations",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")
    return True

def create_sample_dataset():
    """Create a sample dataset for testing"""
    print("\n📊 Creating sample dataset...")
    
    sample_issues = [
        {
            "issue_id": "sample_001",
            "first_question": {
                "title": "Python function returning None instead of expected value",
                "body": "I have a Python function that should return a list, but it's returning None. Can you help me debug this?"
            },
            "comments": [
                {
                    "user": "maintainer",
                    "body": "Can you share the function code? It sounds like there might be a missing return statement."
                },
                {
                    "user": "user",
                    "body": "Here's my function:\n```python\ndef process_data(data):\n    result = []\n    for item in data:\n        result.append(item * 2)\n    # Missing return statement!\n```"
                },
                {
                    "user": "maintainer",
                    "body": "I see the issue! You're missing the `return result` statement at the end of your function."
                }
            ],
            "user_satisfaction_condition": [
                "The user should understand what caused the function to return None",
                "The solution should fix the missing return statement",
                "The explanation should be clear and include code examples"
            ]
        },
        {
            "issue_id": "sample_002",
            "first_question": {
                "title": "Docker build failing with permission error",
                "body": "I'm getting a permission error when building my Docker image. The error says 'permission denied' when trying to copy files."
            },
            "comments": [
                {
                    "user": "maintainer",
                    "body": "This is usually a file permission issue. Can you share your Dockerfile?"
                },
                {
                    "user": "user",
                    "body": "Here's my Dockerfile:\n```dockerfile\nFROM ubuntu:20.04\nCOPY . /app\nWORKDIR /app\nRUN chmod +x script.sh\nCMD [\"./script.sh\"]\n```"
                },
                {
                    "user": "maintainer",
                    "body": "The issue is that you're copying files before setting proper permissions. Try this:\n```dockerfile\nFROM ubuntu:20.04\nWORKDIR /app\nCOPY --chown=root:root . /app\nRUN chmod +x script.sh\nCMD [\"./script.sh\"]\n```"
                }
            ],
            "user_satisfaction_condition": [
                "The user should understand what caused the permission error",
                "The solution should fix the Docker build issue",
                "The explanation should include the corrected Dockerfile"
            ]
        }
    ]
    
    # Save sample dataset
    dataset_path = Path("data/converted_dataset.jsonl")
    with open(dataset_path, 'w') as f:
        for issue in sample_issues:
            f.write(json.dumps(issue) + '\n')
    
    print(f"✅ Sample dataset created: {dataset_path}")
    return True

def test_setup():
    """Test that everything is working"""
    print("\n🧪 Testing setup...")
    
    try:
        # Test importing main modules
        from agent_interface import MockAgent
        from simulated_user import CABEvaluator
        print("✅ Core modules imported successfully")
        
        # Test creating a mock agent
        agent = MockAgent()
        if agent.setup():
            print("✅ Mock agent created and setup successfully")
        else:
            print("❌ Mock agent setup failed")
            return False
        
        # Test dataset exists
        dataset_path = Path("data/converted_dataset.jsonl")
        if dataset_path.exists():
            print("✅ Sample dataset found")
        else:
            print("❌ Sample dataset not found")
            return False
        
        print("✅ Setup test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        return False

def show_next_steps():
    """Show what the user can do next"""
    print("\n🎉 Setup Complete! Here's what you can do next:")
    print("="*60)
    
    print("\n🚀 Quick Tests (No API keys required):")
    print("   # Test with mock agent")
    print("   python test_agent.py --agent mock --dataset data/converted_dataset.jsonl --max-issues 1")
    print("")
    print("   # Test judge functionality")
    print("   python test_judge.py")
    print("")
    print("   # Test full pipeline")
    print("   python test_full_pipeline.py")
    
    print("\n🤖 Test External Agents (if you have them installed):")
    print("   # Test Cursor CLI")
    print("   python test_agent.py --agent cursor-cli --dataset data/converted_dataset.jsonl --max-issues 1")
    print("")
    print("   # Test Amazon Q CLI")
    print("   python test_agent.py --agent amazon-q --dataset data/converted_dataset.jsonl --max-issues 1")
    
    print("\n⚖️ Test External Judges:")
    print("   # Test all judge agents")
    print("   python test_judge_agents.py")
    print("")
    print("   # Compare different judges")
    print("   python example_judge_comparison.py")
    
    print("\n📚 Learn More:")
    print("   # Read the main guide")
    print("   cat README.md")
    print("")
    print("   # Learn about custom agents")
    print("   cat CUSTOM_AGENT_GUIDE.md")
    print("")
    print("   # See all available commands")
    print("   python test_agent.py --help")
    
    print("\n🎯 Success! CAB is ready to use!")
    print("   Try running: python test_agent.py --agent mock --dataset data/converted_dataset.jsonl --max-issues 1")

def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed at dependency installation")
        sys.exit(1)
    
    # Setup directories
    if not setup_directories():
        print("\n❌ Setup failed at directory creation")
        sys.exit(1)
    
    # Create sample dataset
    if not create_sample_dataset():
        print("\n❌ Setup failed at dataset creation")
        sys.exit(1)
    
    # Test setup
    if not test_setup():
        print("\n❌ Setup failed at testing")
        sys.exit(1)
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    main()
