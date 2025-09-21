#!/usr/bin/env python3
"""
Example script showing how to use Amazon Q CLI with CAB.
This script demonstrates how to integrate Amazon Q CLI as an agent.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

def test_amazon_q_integration():
    """Test actual Amazon Q CLI integration"""
    print("🚀 Amazon Q CLI Integration Test")
    print("=" * 40)
    
    # Check Amazon Q CLI
    try:
        result = subprocess.run(
            ["q", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Amazon Q CLI found: {result.stdout.strip()}")
        else:
            print("❌ Amazon Q CLI not working")
            return False
    except FileNotFoundError:
        print("❌ Amazon Q CLI not found")
        print("   Install from: https://aws.amazon.com/q/")
        return False
    
    # Create a sample coding issue
    sample_issue = {
        "title": "Fix AWS Lambda timeout error",
        "body": "My Lambda function is timing out after 3 seconds. The function processes a large dataset and needs more time. How can I increase the timeout and optimize the function?"
    }
    
    print(f"\n📝 Sample Issue:")
    print(f"Title: {sample_issue['title']}")
    print(f"Body: {sample_issue['body']}")
    
    # Create a temporary Python file with the issue
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(f"""
# {sample_issue['title']}
# {sample_issue['body']}

import json
import boto3

def lambda_handler(event, context):
    # TODO: Fix timeout issue
    # This function processes large datasets and times out
    
    # Simulate processing large dataset
    data = []
    for i in range(1000000):  # This might cause timeout
        data.append(i * 2)
    
    return {{
        'statusCode': 200,
        'body': json.dumps(f'Processed {{len(data)}} items')
    }}
""")
        temp_file = f.name
    
    print(f"\n📁 Created temporary Python file: {temp_file}")
    
    # Method 1: Use Amazon Q CLI to analyze the file
    print(f"\n🔧 Method 1: Analyze file with Amazon Q")
    try:
        # Try to analyze the file with Amazon Q
        result = subprocess.run(
            ["q", "analyze", temp_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"   Command: q analyze {temp_file}")
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   Output: {result.stdout[:200]}...")
        if result.stderr:
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 2: Use Amazon Q CLI for code suggestions
    print(f"\n🔧 Method 2: Get code suggestions from Amazon Q")
    try:
        # Try to get suggestions from Amazon Q
        result = subprocess.run(
            ["q", "suggest", "--file", temp_file, "--prompt", "How can I optimize this Lambda function to avoid timeouts?"],
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"   Command: q suggest --file {temp_file} --prompt 'How can I optimize this Lambda function to avoid timeouts?'")
        print(f"   Return code: {result.returncode}")
        if result.stdout:
            print(f"   Output: {result.stdout[:200]}...")
        if result.stderr:
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 3: Create a comprehensive Amazon Q integration script
    print(f"\n🔧 Method 3: Create Amazon Q integration script")
    
    amazon_q_script = f"""
#!/usr/bin/env python3
'''
Amazon Q CLI Integration Example
This script demonstrates how to use Amazon Q CLI for code assistance.
'''

import subprocess
import json
import tempfile
import os

def get_amazon_q_suggestion(file_path, issue_description):
    '''
    Get code suggestions from Amazon Q CLI.
    This is a conceptual example - actual implementation would depend on
    Amazon Q CLI's specific API and capabilities.
    '''
    try:
        # Example of how Amazon Q CLI might be used
        # Note: This is a simplified example
        cmd = [
            "q",
            "suggest",
            "--file", file_path,
            "--prompt", issue_description,
            "--context", "AWS Lambda optimization"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout if result.returncode == 0 else None
        
    except Exception as e:
        print(f"Error getting Amazon Q suggestion: {{e}}")
        return None

def analyze_code_with_amazon_q(file_path):
    '''
    Analyze code with Amazon Q CLI.
    '''
    try:
        cmd = ["q", "analyze", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        print(f"Error analyzing code with Amazon Q: {{e}}")
        return None

def main():
    file_path = "{temp_file}"
    issue = "{sample_issue['title']}: {sample_issue['body']}"
    
    print(f"Analyzing code with Amazon Q: {{file_path}}")
    print(f"Issue: {{issue}}")
    
    # Analyze the code
    analysis = analyze_code_with_amazon_q(file_path)
    if analysis:
        print(f"Amazon Q Analysis: {{analysis[:200]}}...")
    
    # Get suggestions
    suggestion = get_amazon_q_suggestion(file_path, issue)
    if suggestion:
        print(f"Amazon Q Suggestion: {{suggestion[:200]}}...")
    else:
        print("No suggestion available")

if __name__ == "__main__":
    main()
"""
    
    script_file = "amazon_q_integration_example.py"
    with open(script_file, 'w') as f:
        f.write(amazon_q_script)
    
    print(f"   Created: {script_file}")
    
    # Method 4: Show how to integrate with CAB
    print(f"\n🔧 Method 4: CAB Integration")
    
    cab_integration = f"""
# CAB Integration with Amazon Q CLI
from external_agents import AmazonQAgent
from simulated_user import CABEvaluator

# Create Amazon Q CLI agent
agent = AmazonQAgent()

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
    
    print(f"\n✅ Amazon Q CLI integration example completed!")
    print(f"\n💡 Next Steps:")
    print(f"   1. Check Amazon Q CLI documentation for actual API")
    print(f"   2. Update AmazonQAgent in external_agents.py")
    print(f"   3. Test with: python test_agent.py --agent amazon-q --dataset data/converted_dataset.jsonl")
    
    return True

def show_amazon_q_alternatives():
    """Show alternative ways to use Amazon Q CLI"""
    print(f"\n🔄 Alternative Amazon Q CLI Integration Methods")
    print("=" * 50)
    
    print(f"\n1. 📁 File-based Integration:")
    print(f"   • Create temporary files with issues")
    print(f"   • Use Amazon Q CLI to analyze files")
    print(f"   • Parse Amazon Q's output or suggestions")
    
    print(f"\n2. 🔌 API Integration:")
    print(f"   • Use Amazon Q's API (if available)")
    print(f"   • Send issues via HTTP requests")
    print(f"   • Get responses programmatically")
    
    print(f"\n3. 📝 Script Integration:")
    print(f"   • Create Python scripts that use Amazon Q")
    print(f"   • Use subprocess to call Amazon Q CLI")
    print(f"   • Parse and format responses")
    
    print(f"\n4. 🎯 Custom Agent:")
    print(f"   • Implement CABAgent interface")
    print(f"   • Use any Amazon Q CLI method")
    print(f"   • Integrate with CAB testing framework")
    
    print(f"\n5. ☁️ AWS Integration:")
    print(f"   • Use AWS SDK for Amazon Q")
    print(f"   • Integrate with AWS services")
    print(f"   • Use AWS credentials for authentication")

def main():
    """Main function"""
    print("🚀 Amazon Q CLI Integration with CAB")
    print("=" * 50)
    
    success = test_amazon_q_integration()
    
    if success:
        show_amazon_q_alternatives()
        
        print(f"\n🎉 Amazon Q CLI integration is possible!")
        print(f"   The framework is ready - just need to implement the actual Amazon Q CLI calls.")
    else:
        print(f"\n❌ Amazon Q CLI integration failed")
        print(f"   Please check Amazon Q CLI installation and documentation.")

if __name__ == "__main__":
    main()
