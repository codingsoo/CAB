#!/usr/bin/env python3
"""
Test script for external agents (Cursor CLI, GitHub Copilot, Local LLMs, etc.)
"""

import subprocess
import sys
from pathlib import Path

def check_cursor_cli():
    """Check if Cursor CLI is available"""
    print("🔍 Checking Cursor CLI...")
    try:
        result = subprocess.run(
            ["cursor", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Cursor CLI found: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Cursor CLI error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Cursor CLI not found")
        print("   Install from: https://cursor.sh/")
        return False
    except Exception as e:
        print(f"❌ Error checking Cursor CLI: {e}")
        return False

def check_github_copilot():
    """Check if GitHub Copilot CLI is available"""
    print("\n🔍 Checking GitHub Copilot CLI...")
    try:
        result = subprocess.run(
            ["gh", "copilot", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ GitHub Copilot CLI found: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ GitHub Copilot CLI error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ GitHub CLI not found")
        print("   Install from: https://cli.github.com/")
        return False
    except Exception as e:
        print(f"❌ Error checking GitHub Copilot CLI: {e}")
        return False

def check_amazon_q():
    """Check if Amazon Q CLI is available"""
    print("\n🔍 Checking Amazon Q CLI...")
    try:
        result = subprocess.run(
            ["q", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Amazon Q CLI found: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Amazon Q CLI error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Amazon Q CLI not found")
        print("   Install from: https://aws.amazon.com/q/")
        return False
    except Exception as e:
        print(f"❌ Error checking Amazon Q CLI: {e}")
        return False

def check_local_llm():
    """Check if local LLM (Ollama) is available"""
    print("\n🔍 Checking Local LLM (Ollama)...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]
            print(f"✅ Ollama found with models: {model_names}")
            return True
        else:
            print(f"❌ Ollama API not responding: {response.status_code}")
            return False
    except ImportError:
        print("❌ requests library not available")
        return False
    except Exception as e:
        print(f"❌ Ollama not found: {e}")
        print("   Install from: https://ollama.ai/")
        return False

def test_external_agents():
    """Test external agents with CAB"""
    print("\n🧪 Testing External Agents with CAB")
    print("=" * 50)
    
    # Check if dataset exists
    dataset_path = Path("data/converted_dataset.jsonl")
    if not dataset_path.exists():
        print("❌ Converted dataset not found. Please run:")
        print("   python convert_dataset.py <input_dataset> data/converted_dataset.jsonl")
        return False
    
    print(f"✅ Dataset found: {dataset_path}")
    
    # Test each external agent
    external_agents = [
        ("cursor-cli", "Cursor CLI"),
        ("github-copilot", "GitHub Copilot CLI"),
        ("amazon-q", "Amazon Q CLI"),
        ("local-llama2", "Local LLM (Llama2)"),
        ("local-codellama", "Local LLM (CodeLlama)"),
    ]
    
    for agent_type, agent_name in external_agents:
        print(f"\n🤖 Testing {agent_name}...")
        
        try:
            # Import and test the agent
            from external_agents import create_external_agent
            agent = create_external_agent(agent_type)
            
            if agent.setup():
                print(f"   ✅ {agent_name} setup successful")
                
                # Test with a single issue
                print(f"   🔄 Running evaluation...")
                import subprocess
                result = subprocess.run([
                    "python", "test_agent.py",
                    "--agent", agent_type,
                    "--dataset", str(dataset_path),
                    "--max-issues", "1"
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print(f"   ✅ {agent_name} evaluation successful")
                    # Extract satisfaction rate from output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "Satisfaction Rate:" in line:
                            print(f"   📊 {line.strip()}")
                            break
                else:
                    print(f"   ❌ {agent_name} evaluation failed: {result.stderr}")
            else:
                print(f"   ❌ {agent_name} setup failed")
                
        except Exception as e:
            print(f"   ❌ Error testing {agent_name}: {e}")
    
    return True

def show_usage_examples():
    """Show usage examples for external agents"""
    print("\n📚 Usage Examples for External Agents")
    print("=" * 50)
    
    print("\n🔧 Cursor CLI:")
    print("   # Test Cursor CLI agent")
    print("   python test_agent.py --agent cursor-cli --dataset data/converted_dataset.jsonl")
    
    print("\n🤖 GitHub Copilot:")
    print("   # Test GitHub Copilot CLI agent")
    print("   python test_agent.py --agent github-copilot --dataset data/converted_dataset.jsonl")
    
    print("\n☁️ Amazon Q:")
    print("   # Test Amazon Q CLI agent")
    print("   python test_agent.py --agent amazon-q --dataset data/converted_dataset.jsonl")
    
    print("\n🏠 Local LLM (Ollama):")
    print("   # Test with Llama2")
    print("   python test_agent.py --agent local-llama2 --dataset data/converted_dataset.jsonl")
    print("   ")
    print("   # Test with CodeLlama")
    print("   python test_agent.py --agent local-codellama --dataset data/converted_dataset.jsonl")
    
    print("\n📝 Custom Script:")
    print("   # Create a custom script agent")
    print("   from external_agents import CustomScriptAgent")
    print("   agent = CustomScriptAgent('my_script.py', 'MyCustomAgent')")
    
    print("\n💡 Tips:")
    print("   • Use --max-issues 1 for quick testing")
    print("   • Use --verbose for detailed logs")
    print("   • Check agent setup before running evaluations")

def main():
    """Main function"""
    print("🚀 CAB External Agents Test")
    print("=" * 40)
    
    # Check external tools
    cursor_ok = check_cursor_cli()
    copilot_ok = check_github_copilot()
    amazon_q_ok = check_amazon_q()
    llm_ok = check_local_llm()
    
    print(f"\n📊 External Tools Status:")
    print(f"   Cursor CLI: {'✅' if cursor_ok else '❌'}")
    print(f"   GitHub Copilot: {'✅' if copilot_ok else '❌'}")
    print(f"   Amazon Q CLI: {'✅' if amazon_q_ok else '❌'}")
    print(f"   Local LLM: {'✅' if llm_ok else '❌'}")
    
    if any([cursor_ok, copilot_ok, amazon_q_ok, llm_ok]):
        print(f"\n🎉 At least one external tool is available!")
        
        # Test external agents
        test_external_agents()
        
        # Show usage examples
        show_usage_examples()
    else:
        print(f"\n⚠️  No external tools found.")
        print(f"   You can still use built-in agents (mock, openai-gpt4, claude-sonnet)")
        print(f"   Or install external tools to test them with CAB.")
        
        show_usage_examples()

if __name__ == "__main__":
    main()
