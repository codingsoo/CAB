#!/usr/bin/env python3
"""
CAB Command Line Interface
Simple CLI tool for running the CAB dataset generation pipeline.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List

from pipeline_runner import CABPipelineRunner
from cab_config import get_config

def print_banner():
    """Print CAB banner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    🚀 CAB - CodeAssistBench                 ║
║              NeurIPS 2024 - AI Coding Assistant Benchmark   ║
╚══════════════════════════════════════════════════════════════╝
""")

def print_help():
    """Print help information"""
    print("""
📚 CAB Dataset Generation Pipeline

This tool helps you generate a comprehensive dataset for evaluating AI coding assistants
using real GitHub issues and conversations.

🔧 Setup:
  1. Configure your API keys in .env file
  2. Run: python cab_cli.py setup
  3. Run: python cab_cli.py generate --languages python javascript

📊 Available Commands:
  setup     - Setup and validate configuration
  generate  - Generate dataset from GitHub issues
  status    - Check pipeline status
  demo      - Run with sample data
  test      - Run pipeline tests
  help      - Show this help message

🌐 Supported Languages:
  python, javascript, typescript, java, c, c++, c#

📖 Examples:
  python cab_cli.py setup
  python cab_cli.py generate --languages python javascript --demo
  python cab_cli.py status
  python cab_cli.py test
""")

async def cmd_setup():
    """Setup and validate configuration"""
    print("🔧 Setting up CAB configuration...")
    
    try:
        config = get_config()
        
        # Check API keys
        validation = config.validate_api_keys()
        
        print("\n📋 Configuration Status:")
        print(f"  GitHub Token: {'✅ Configured' if validation['github_token'] else '❌ Missing'}")
        print(f"  OpenAI API Key: {'✅ Configured' if validation['openai_api_key'] else '❌ Missing'}")
        print(f"  AWS Bedrock: {'✅ Configured' if validation['aws_configured'] else '❌ Missing'}")
        
        # Check directories
        print(f"\n📁 Directories:")
        print(f"  Base: {config.directories.base}")
        print(f"  Data: {config.directories.issue_data}")
        print(f"  Results: {config.directories.results}")
        print(f"  Logs: {config.directories.logs}")
        
        # Create directories
        for dir_name, dir_path in [
            ("Base", config.directories.base),
            ("Data", config.directories.issue_data),
            ("Results", config.directories.results),
            ("Logs", config.directories.logs)
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {dir_name}: {dir_path}")
        
        if not validation['github_token']:
            print("\n⚠️  GitHub token is required for full functionality")
            print("   Get one at: https://github.com/settings/tokens")
            print("   Add to .env file: GITHUB_TOKEN=your_token")
        
        if not validation['openai_api_key']:
            print("\n⚠️  OpenAI API key is recommended for some features")
            print("   Get one at: https://platform.openai.com/api-keys")
            print("   Add to .env file: OPENAI_API_KEY=your_key")
        
        print("\n✅ Setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    return True

async def cmd_generate(languages: List[str], demo: bool = False, resume: bool = True):
    """Generate dataset"""
    print(f"🚀 Starting dataset generation for languages: {', '.join(languages)}")
    
    if demo:
        print("🎮 Running in demo mode with sample data")
    
    try:
        runner = CABPipelineRunner()
        summary = await runner.run_pipeline(languages, resume=resume)
        
        if summary.get("status") == "cancelled":
            print("\n⏹️  Generation cancelled")
            return False
        elif summary.get("status") == "failed":
            print(f"\n❌ Generation failed: {summary.get('error')}")
            return False
        else:
            print("\n🎉 Dataset generation completed successfully!")
            
            # Print dataset information
            if "shared_data" in summary:
                dataset_info = summary["shared_data"].get("dataset_info", {})
                if dataset_info:
                    print(f"\n📊 Dataset Information:")
                    print(f"  📄 File: {dataset_info.get('dataset_file', 'N/A')}")
                    print(f"  📈 Entries: {dataset_info.get('total_entries', 0)}")
                    print(f"  🌐 Languages: {', '.join(dataset_info.get('languages', []))}")
            
            return True
            
    except KeyboardInterrupt:
        print("\n⏹️  Generation interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return False

async def cmd_status():
    """Check pipeline status"""
    print("📊 Checking pipeline status...")
    
    try:
        runner = CABPipelineRunner()
        status = runner.get_status()
        
        if not status or status.get("status") == "not_started":
            print("ℹ️  No pipeline execution found")
            return
        
        print(f"\n📋 Pipeline Status: {status.get('status', 'unknown')}")
        print(f"🌐 Languages: {', '.join(status.get('languages', []))}")
        print(f"📈 Overall Progress: {status.get('progress', 0):.1%}")
        
        current_step = status.get('current_step')
        if current_step:
            print(f"🔄 Current Step: {current_step}")
        
        print(f"\n📊 Step Results:")
        for step_name, result in status.get('step_results', {}).items():
            status_emoji = {
                'completed': '✅',
                'failed': '❌',
                'skipped': '⏭️',
                'running': '🔄',
                'pending': '⏳'
            }.get(result['status'], '❓')
            
            progress = result.get('progress', 0)
            duration = result.get('duration', 0)
            
            print(f"  {status_emoji} {step_name}: {result['status']} "
                  f"({progress:.1%}, {duration:.2f}s)")
        
    except Exception as e:
        print(f"❌ Failed to get status: {e}")

async def cmd_demo():
    """Run demo with sample data"""
    print("🎮 Running CAB demo with sample data...")
    
    try:
        # Generate demo data first
        from demo_data_generator import create_demo_dataset
        demo_dir = create_demo_dataset()
        
        print(f"✅ Demo data generated in: {demo_dir}")
        
        # Run pipeline in demo mode
        success = await cmd_generate(["python"], demo=True, resume=False)
        
        if success:
            print("\n🎉 Demo completed successfully!")
            print("📁 Check the results directory for generated files")
        else:
            print("\n❌ Demo failed")
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def cmd_test():
    """Run pipeline tests"""
    print("🧪 Running pipeline tests...")
    
    try:
        from test_pipeline import run_tests
        success = run_tests()
        
        if success:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed")
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="CAB - CodeAssistBench Dataset Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    subparsers.add_parser('setup', help='Setup and validate configuration')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate dataset')
    generate_parser.add_argument(
        '--languages', 
        nargs='+', 
        default=['python', 'javascript', 'typescript'],
        help='Programming languages to process'
    )
    generate_parser.add_argument(
        '--demo', 
        action='store_true',
        help='Run in demo mode with sample data'
    )
    generate_parser.add_argument(
        '--no-resume', 
        action='store_true',
        help="Don't resume from previous execution"
    )
    
    # Status command
    subparsers.add_parser('status', help='Check pipeline status')
    
    # Demo command
    subparsers.add_parser('demo', help='Run demo with sample data')
    
    # Test command
    subparsers.add_parser('test', help='Run pipeline tests')
    
    # Help command
    subparsers.add_parser('help', help='Show help information')
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Handle commands
    if args.command == 'setup':
        success = asyncio.run(cmd_setup())
        sys.exit(0 if success else 1)
    
    elif args.command == 'generate':
        success = asyncio.run(cmd_generate(
            args.languages, 
            demo=args.demo, 
            resume=not args.no_resume
        ))
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        asyncio.run(cmd_status())
    
    elif args.command == 'demo':
        asyncio.run(cmd_demo())
    
    elif args.command == 'test':
        cmd_test()
    
    elif args.command == 'help':
        print_help()
    
    else:
        print("❌ Unknown command. Use 'python cab_cli.py help' for usage information.")
        sys.exit(1)

if __name__ == "__main__":
    main()
