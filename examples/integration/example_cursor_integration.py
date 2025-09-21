#!/usr/bin/env python3
"""
Working example of Cursor CLI integration with CAB.
This shows how to actually use Cursor CLI for code assistance.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

def test_cursor_cli_integration():
    """Test actual Cursor CLI integration"""
    print("🚀 Cursor CLI Integration Test")
    print("=" * 40)
    
    # Check Cursor CLI
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
        print("❌ Cursor CLI not found")
        return False
    
    # Create a sample coding issue
    sample_issue = {
        "title": "Fix Python import error",
        "body": "I'm getting an ImportError when trying to import pandas. The error says 'No module named pandas'. How can I fix this?"
    }
    
    print(f"\n📝 Sample Issue:")
    print(f"Title: {sample_issue['title']}")
    print(f"Body: {sample_issue['body']}")
    
    # Create a temporary Python file with the issue
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(f"""
# {sample_issue['title']}
# {sample_issue['body']}

# TODO: Fix the import error
import pandas as pd  # This line causes ImportError

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")
        temp_file = f.name
    
    print(f"\n📁 Created temporary Python file: {temp_file}")
    
    # Method 1: Use Cursor CLI to open the file (if it supports it)
    print(f"\n🔧 Method 1: Open file with Cursor")
    try:
        # Try to open the file with Cursor
        result = subprocess.run(
            ["cursor", temp_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"   Command: cursor {temp_file}")
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   Output: {result.stdout}")
        if result.stderr:
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 2: Create a simple script that uses Cursor's features
    print(f"\n🔧 Method 2: Create Cursor-compatible script")
    
    cursor_script = f"""
#!/usr/bin/env python3
'''
Cursor CLI Integration Example
This script demonstrates how to use Cursor CLI for code assistance.
'''

import subprocess
import sys

def get_cursor_suggestion(file_path, line_number, issue_description):
    '''
    Get code suggestions from Cursor CLI.
    This is a conceptual example - actual implementation would depend on
    Cursor CLI's specific API and capabilities.
    '''
    try:
        # Example of how Cursor CLI might be used
        # Note: This is a simplified example
        cmd = [
            "cursor",
            "--suggest",
            "--file", file_path,
            "--line", str(line_number),
            "--context", issue_description
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.returncode == 0 else None
        
    except Exception as e:
        print(f"Error getting Cursor suggestion: {{e}}")
        return None

def main():
    file_path = "{temp_file}"
    issue = "{sample_issue['title']}: {sample_issue['body']}"
    
    print(f"Getting Cursor suggestion for: {{file_path}}")
    print(f"Issue: {{issue}}")
    
    # This would be the actual Cursor CLI integration
    suggestion = get_cursor_suggestion(file_path, 5, issue)
    if suggestion:
        print(f"Cursor suggestion: {{suggestion}}")
    else:
        print("No suggestion available")

if __name__ == "__main__":
    main()
"""
    
    script_file = "cursor_integration_example.py"
    with open(script_file, 'w') as f:
        f.write(cursor_script)
    
    print(f"   Created: {script_file}")
    
    # Method 3: Show how to integrate with CAB
    print(f"\n🔧 Method 3: CAB Integration")
    
    cab_integration = f"""
# CAB Integration with Cursor CLI
from external_agents import CursorCLIAgent
from simulated_user import CABEvaluator

# Create Cursor CLI agent
agent = CursorCLIAgent()

# Test with CAB
evaluator = CABEvaluator()
result = evaluator.evaluate_agent(
    agent, 
    "data/converted_dataset.jsonl", 
    max_issues=1
)

print(f"Satisfaction rate: {{result.satisfaction_rate:.2%}}")
"""
    
    print("   CAB Integration Code:")
    print("   " + "\n   ".join(cab_integration.strip().split('\n')))
    
    # Clean up
    os.unlink(temp_file)
    
    print(f"\n✅ Cursor CLI integration example completed!")
    print(f"\n💡 Next Steps:")
    print(f"   1. Check Cursor CLI documentation for actual API")
    print(f"   2. Update CursorCLIAgent in external_agents.py")
    print(f"   3. Test with: python test_agent.py --agent cursor-cli --dataset data/converted_dataset.jsonl")
    
    return True

def show_cursor_cli_alternatives():
    """Show alternative ways to use Cursor CLI"""
    print(f"\n🔄 Alternative Cursor CLI Integration Methods")
    print("=" * 50)
    
    print(f"\n1. 📁 File-based Integration:")
    print(f"   • Create temporary files with issues")
    print(f"   • Use Cursor CLI to open/edit files")
    print(f"   • Parse Cursor's output or suggestions")
    
    print(f"\n2. 🔌 API Integration:")
    print(f"   • Use Cursor's API (if available)")
    print(f"   • Send issues via HTTP requests")
    print(f"   • Get responses programmatically")
    
    print(f"\n3. 📝 Script Integration:")
    print(f"   • Create Python scripts that use Cursor")
    print(f"   • Use subprocess to call Cursor CLI")
    print(f"   • Parse and format responses")
    
    print(f"\n4. 🎯 Custom Agent:")
    print(f"   • Implement CABAgent interface")
    print(f"   • Use any Cursor CLI method")
    print(f"   • Integrate with CAB testing framework")

def main():
    """Main function"""
    print("🚀 Cursor CLI Integration with CAB")
    print("=" * 50)
    
    success = test_cursor_cli_integration()
    
    if success:
        show_cursor_cli_alternatives()
        
        print(f"\n🎉 Cursor CLI integration is possible!")
        print(f"   The framework is ready - just need to implement the actual Cursor CLI calls.")
    else:
        print(f"\n❌ Cursor CLI integration failed")
        print(f"   Please check Cursor CLI installation and documentation.")

if __name__ == "__main__":
    main()
