#!/usr/bin/env python3
"""
Simple CLI tool to test agents using the CAB simulated user environment.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from agent_interface import create_agent, MockAgent
from simulated_user import CABEvaluator, SimulatedUser
from external_agents import create_external_agent, EXTERNAL_AGENT_REGISTRY

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

def test_agent_cli():
    """Main CLI function for testing agents"""
    parser = argparse.ArgumentParser(
        description="Test AI agents using CAB simulated user environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with mock agent (no API calls)
  python test_agent.py --agent mock --dataset data/dataset.jsonl
  
  # Test with OpenAI GPT-4
  python test_agent.py --agent openai-gpt4 --dataset data/dataset.jsonl --max-issues 5
  
  # Test with Claude
  python test_agent.py --agent claude-sonnet --dataset data/dataset.jsonl --verbose
        """
    )
    
    # Get available agents dynamically
    from agent_interface import AGENT_REGISTRY
    # Import external agents to ensure registry is populated
    try:
        from external_agents import EXTERNAL_AGENT_REGISTRY
        all_agents = list(AGENT_REGISTRY.keys()) + list(EXTERNAL_AGENT_REGISTRY.keys())
    except ImportError:
        all_agents = list(AGENT_REGISTRY.keys())
    
    parser.add_argument(
        "--agent", 
        required=True,
        help="Type of agent to test"
    )
    
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to dataset JSONL file"
    )
    
    parser.add_argument(
        "--output",
        help="Path to save evaluation results (JSON format)"
    )
    
    parser.add_argument(
        "--max-issues",
        type=int,
        help="Maximum number of issues to test (default: all)"
    )
    
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=10,
        help="Maximum conversation rounds per issue (default: 10)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Check dataset exists
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error(f"Dataset file not found: {dataset_path}")
        sys.exit(1)
    
    # Create agent
    try:
        logger.info(f"Creating {args.agent} agent...")
        
        # Get current agent registries
        from agent_interface import AGENT_REGISTRY
        try:
            from external_agents import EXTERNAL_AGENT_REGISTRY
        except ImportError:
            EXTERNAL_AGENT_REGISTRY = {}
        
        # Try built-in agents first, then external agents
        if args.agent in AGENT_REGISTRY:
            agent = create_agent(args.agent)
        elif args.agent in EXTERNAL_AGENT_REGISTRY:
            agent = create_external_agent(args.agent)
        else:
            available_agents = list(AGENT_REGISTRY.keys()) + list(EXTERNAL_AGENT_REGISTRY.keys())
            raise ValueError(f"Unknown agent type: {args.agent}. Available agents: {available_agents}")
        
        logger.info(f"Agent created: {agent.get_info()}")
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        sys.exit(1)
    
    # Create simulated user
    simulated_user = SimulatedUser(max_rounds=args.max_rounds)
    
    # Create evaluator
    evaluator = CABEvaluator(simulated_user)
    
    # Run evaluation
    try:
        logger.info("Starting agent evaluation...")
        result = evaluator.evaluate_agent(agent, str(dataset_path), args.max_issues)
        
        # Print results
        print(f"\n🎯 Evaluation Results for {result.agent_name}")
        print("=" * 60)
        print(f"📊 Total Issues: {result.total_issues}")
        print(f"✅ Successful: {result.successful_conversations}")
        print(f"❌ Failed: {result.failed_conversations}")
        print(f"📈 Satisfaction Rate: {result.satisfaction_rate:.2%}")
        print(f"🔄 Average Rounds: {result.average_rounds:.1f}")
        print(f"⏱️  Average Duration: {result.average_duration:.1f}s")
        
        # Show sample conversation if available
        if result.results:
            sample_result = result.results[0]
            print(f"\n📝 Sample Conversation (Issue: {sample_result.issue_id})")
            print("-" * 40)
            for i, msg in enumerate(sample_result.conversation_history[:4]):  # Show first 4 messages
                role = "👤 User" if msg["role"] == "user" else "🤖 Agent"
                content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                print(f"{role}: {content}")
            
            if len(sample_result.conversation_history) > 4:
                print("... (conversation continues)")
            
            print(f"\n🎯 Final Result: {'✅ Satisfied' if sample_result.user_satisfied else '❌ Not Satisfied'}")
            print(f"💭 Reason: {sample_result.satisfaction_reason}")
        
        # Save results if requested
        if args.output:
            evaluator.save_results(result, args.output)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Exit with appropriate code
        sys.exit(0 if result.satisfaction_rate > 0.5 else 1)
        
    except KeyboardInterrupt:
        logger.info("Evaluation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    print("🚀 CAB Agent Testing Tool")
    print("=" * 40)
    
    try:
        test_agent_cli()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
