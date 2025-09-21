#!/usr/bin/env python3
"""
Example script showing how to use Cursor CLI with CAB.
This script demonstrates how to integrate Cursor CLI as an agent.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

def cursor_cli_example():
    """Example of using Cursor CLI for code assistance"""
    print("🚀 Cursor CLI Integration Example")
    print("=" * 40)
    
    # Check if Cursor CLI is available
    try:
        result = subprocess.run(
            ["cursor", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Cursor CLI found: {result.stdout.strip()}")
        else:
            print("❌ Cursor CLI not working")
            return False
    except FileNotFoundError:
        print("❌ Cursor CLI not found. Please install Cursor CLI first.")
        print("   Visit: https://cursor.sh/")
        return False
    
    # Create a sample issue
    sample_issue = {
        "title": "Fix Python import error",
        "body": "I'm getting an ImportError when trying to import pandas. The error says 'No module named pandas'. How can I fix this?"
    }
    
    print(f"\n📝 Sample Issue:")
    print(f"Title: {sample_issue['title']}")
    print(f"Body: {sample_issue['body']}")
    
    # Create a temporary file with the issue
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(f"# {sample_issue['title']}\n\n")
        f.write(f"{sample_issue['body']}\n\n")
        f.write("Please provide a solution with code examples.")
        temp_file = f.name
    
    print(f"\n📁 Created temporary file: {temp_file}")
    
    # Example of how Cursor CLI might be used
    # Note: This is a simplified example - actual Cursor CLI commands
    # would depend on the specific Cursor CLI interface
    print(f"\n🔧 Example Cursor CLI command:")
    print(f"cursor chat --file {temp_file} --prompt 'Help solve this coding issue'")
    
    # Clean up
    os.unlink(temp_file)
    
    print(f"\n✅ Example completed!")
    print(f"💡 To use Cursor CLI with CAB:")
    print(f"   1. Install Cursor CLI")
    print(f"   2. Use: python test_agent.py --agent cursor-cli --dataset data/converted_dataset.jsonl")
    
    return True

if __name__ == "__main__":
    cursor_cli_example()
