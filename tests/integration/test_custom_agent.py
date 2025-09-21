#!/usr/bin/env python3
"""
Test custom agents with CAB in the same process.
This avoids the issue of registry changes not persisting across processes.
"""

import sys
import importlib.util
from pathlib import Path

def test_custom_agent_direct(agent_file: str, agent_class: str, dataset_path: str = "data/converted_dataset.jsonl", max_issues: int = 1):
    """
    Test a custom agent directly by importing and using it.
    """
    try:
        print(f"🚀 Testing Custom Agent: {agent_class}")
        print("=" * 50)
        
        # Load the agent module
        print(f"📁 Loading agent from: {agent_file}")
        spec = importlib.util.spec_from_file_location("custom_agent", agent_file)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)
        
        # Get the agent class
        agent_class_obj = getattr(agent_module, agent_class)
        
        # Create agent instance
        print(f"🤖 Creating {agent_class} instance...")
        agent = agent_class_obj()
        
        # Test setup
        print("🔧 Testing agent setup...")
        if not agent.setup():
            print("❌ Agent setup failed!")
            return False
        
        print("✅ Agent setup successful!")
        
        # Test with CAB
        print(f"🧪 Testing with CAB dataset: {dataset_path}")
        from simulated_user import CABEvaluator
        
        evaluator = CABEvaluator()
        result = evaluator.evaluate_agent(
            agent,
            dataset_path,
            max_issues=max_issues
        )
        
        # Print results
        print("\n" + "=" * 60)
        print(f"🎯 Evaluation Results for {agent.name}")
        print("=" * 60)
        print(f"📊 Total Issues: {result.total_issues}")
        print(f"✅ Successful: {result.successful_conversations}")
        print(f"❌ Failed: {result.failed_conversations}")
        print(f"📈 Satisfaction Rate: {result.satisfaction_rate:.2f}%")
        print(f"🔄 Average Rounds: {result.average_rounds:.1f}")
        
        # Show sample conversation
        if result.results:
            sample_result = result.results[0]
            print(f"\n📝 Sample Conversation (Issue: {sample_result.issue_id})")
            print("-" * 40)
            for msg in sample_result.conversation_history:
                role = "User" if msg['role'] == 'user' else "Agent"
                content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                print(f"{role}: {content}")
            print(f"\n🎯 Final Result: {'✅ Satisfied' if sample_result.user_satisfied else '❌ Not Satisfied'}")
            print(f"💭 Reason: {sample_result.satisfaction_reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing custom agent: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function with command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test custom agents with CAB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test the example custom agent
  python test_custom_agent.py example_custom_agent.py ExampleCustomAgent
  
  # Test with more issues
  python test_custom_agent.py example_custom_agent.py ExampleCustomAgent --max-issues 3
  
  # Test with different dataset
  python test_custom_agent.py my_agent.py MyAgent --dataset data/my_dataset.jsonl
        """
    )
    
    parser.add_argument('agent_file', help='Path to the agent Python file')
    parser.add_argument('agent_class', help='Name of the agent class')
    parser.add_argument('--dataset', default='data/converted_dataset.jsonl', help='Dataset path')
    parser.add_argument('--max-issues', type=int, default=1, help='Maximum issues to test')
    
    args = parser.parse_args()
    
    # Check if agent file exists
    if not Path(args.agent_file).exists():
        print(f"❌ Agent file not found: {args.agent_file}")
        sys.exit(1)
    
    # Check if dataset exists
    if not Path(args.dataset).exists():
        print(f"❌ Dataset file not found: {args.dataset}")
        print("💡 Make sure you have converted your dataset first:")
        print("   python convert_dataset.py <input_dataset> data/converted_dataset.jsonl")
        sys.exit(1)
    
    # Test the custom agent
    success = test_custom_agent_direct(
        args.agent_file,
        args.agent_class,
        args.dataset,
        args.max_issues
    )
    
    if success:
        print(f"\n🎉 Custom agent test completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Custom agent test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
