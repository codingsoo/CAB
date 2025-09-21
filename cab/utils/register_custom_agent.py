#!/usr/bin/env python3
"""
Script to help users register and test their custom agents with CAB.
"""

import sys
import importlib.util
from pathlib import Path

def register_custom_agent(agent_file: str, agent_class: str, agent_name: str):
    """
    Register a custom agent with CAB.
    
    Args:
        agent_file: Path to the Python file containing your agent
        agent_class: Name of the agent class
        agent_name: Name to use for the agent in CAB
    """
    try:
        # Load the agent module
        spec = importlib.util.spec_from_file_location("custom_agent", agent_file)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)
        
        # Get the agent class
        agent_class_obj = getattr(agent_module, agent_class)
        
        # Register with external agents
        from external_agents import EXTERNAL_AGENT_REGISTRY
        EXTERNAL_AGENT_REGISTRY[agent_name] = lambda: agent_class_obj()
        
        print(f"✅ Successfully registered {agent_name} from {agent_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to register agent: {e}")
        return False

def test_custom_agent(agent_name: str, dataset_path: str = "data/converted_dataset.jsonl", max_issues: int = 1):
    """
    Test a custom agent with CAB.
    
    Args:
        agent_name: Name of the registered agent
        dataset_path: Path to the dataset
        max_issues: Maximum number of issues to test
    """
    try:
        import subprocess
        
        cmd = [
            "python", "test_agent.py",
            "--agent", agent_name,
            "--dataset", dataset_path,
            "--max-issues", str(max_issues)
        ]
        
        print(f"🧪 Testing {agent_name}...")
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f"✅ {agent_name} test completed successfully!")
            print(f"\n📊 Results:")
            print(result.stdout)
        else:
            print(f"❌ {agent_name} test failed!")
            print(f"Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {agent_name} test timed out after 2 minutes")
    except Exception as e:
        print(f"❌ Error testing {agent_name}: {e}")

def list_registered_agents():
    """List all registered agents."""
    try:
        from external_agents import EXTERNAL_AGENT_REGISTRY
        from agent_interface import AGENT_REGISTRY
        
        print("🤖 Available Agents:")
        print("=" * 40)
        
        print("\n📦 Built-in Agents:")
        for name in AGENT_REGISTRY.keys():
            print(f"  • {name}")
        
        print("\n🔧 External Agents:")
        for name in EXTERNAL_AGENT_REGISTRY.keys():
            print(f"  • {name}")
        
        print(f"\n💡 Total: {len(AGENT_REGISTRY) + len(EXTERNAL_AGENT_REGISTRY)} agents available")
        
    except Exception as e:
        print(f"❌ Error listing agents: {e}")

def main():
    """Main function with command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Register and test custom agents with CAB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register a custom agent
  python register_custom_agent.py register example_custom_agent.py ExampleCustomAgent my-custom
  
  # Test a custom agent
  python register_custom_agent.py test my-custom
  
  # List all available agents
  python register_custom_agent.py list
  
  # Register and test in one command
  python register_custom_agent.py register-test example_custom_agent.py ExampleCustomAgent my-custom
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Register command
    register_parser = subparsers.add_parser('register', help='Register a custom agent')
    register_parser.add_argument('agent_file', help='Path to the agent Python file')
    register_parser.add_argument('agent_class', help='Name of the agent class')
    register_parser.add_argument('agent_name', help='Name to use for the agent in CAB')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test a registered agent')
    test_parser.add_argument('agent_name', help='Name of the agent to test')
    test_parser.add_argument('--dataset', default='data/converted_dataset.jsonl', help='Dataset path')
    test_parser.add_argument('--max-issues', type=int, default=1, help='Maximum issues to test')
    
    # List command
    subparsers.add_parser('list', help='List all available agents')
    
    # Register and test command
    register_test_parser = subparsers.add_parser('register-test', help='Register and test a custom agent')
    register_test_parser.add_argument('agent_file', help='Path to the agent Python file')
    register_test_parser.add_argument('agent_class', help='Name of the agent class')
    register_test_parser.add_argument('agent_name', help='Name to use for the agent in CAB')
    register_test_parser.add_argument('--dataset', default='data/converted_dataset.jsonl', help='Dataset path')
    register_test_parser.add_argument('--max-issues', type=int, default=1, help='Maximum issues to test')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🚀 CAB Custom Agent Manager")
    print("=" * 40)
    
    if args.command == 'register':
        success = register_custom_agent(args.agent_file, args.agent_class, args.agent_name)
        if success:
            print(f"\n💡 You can now test your agent with:")
            print(f"   python register_custom_agent.py test {args.agent_name}")
    
    elif args.command == 'test':
        test_custom_agent(args.agent_name, args.dataset, args.max_issues)
    
    elif args.command == 'list':
        list_registered_agents()
    
    elif args.command == 'register-test':
        print("📝 Registering agent...")
        success = register_custom_agent(args.agent_file, args.agent_class, args.agent_name)
        if success:
            print("\n🧪 Testing agent...")
            test_custom_agent(args.agent_name, args.dataset, args.max_issues)
        else:
            print("❌ Registration failed, skipping test")

if __name__ == "__main__":
    main()
