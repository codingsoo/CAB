"""
Main Pipeline Runner for CAB Dataset Generation
Provides a simple interface to run the complete dataset generation pipeline.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from pipeline_core import PipelineExecutor
from pipeline_steps import create_pipeline_steps
from cab_config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline_runner.log')
    ]
)

logger = logging.getLogger(__name__)

class CABPipelineRunner:
    """Main pipeline runner for CAB dataset generation"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = get_config()
        self.executor = PipelineExecutor(config_path)
        self._setup_pipeline()
    
    def _setup_pipeline(self):
        """Setup the pipeline with all steps"""
        steps = create_pipeline_steps()
        for step in steps:
            self.executor.register_step(step)
        
        logger.info(f"Registered {len(steps)} pipeline steps")
    
    async def run_pipeline(self, languages: List[str], resume: bool = True) -> dict:
        """Run the complete dataset generation pipeline"""
        logger.info(f"Starting CAB dataset generation pipeline for languages: {languages}")
        
        try:
            # Execute the pipeline
            summary = await self.executor.execute_pipeline(languages, resume=resume)
            
            # Print summary
            self._print_summary(summary)
            
            return summary
            
        except KeyboardInterrupt:
            logger.info("Pipeline execution interrupted by user")
            self.executor.cancel()
            return {"status": "cancelled"}
        
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _print_summary(self, summary: dict):
        """Print execution summary"""
        print("\n" + "="*60)
        print("🎉 CAB Dataset Generation Pipeline Summary")
        print("="*60)
        
        if "error" in summary:
            print(f"❌ Pipeline failed: {summary['error']}")
            return
        
        print(f"📊 Languages processed: {', '.join(summary.get('languages', []))}")
        print(f"📈 Total steps: {summary.get('total_steps', 0)}")
        print(f"✅ Completed steps: {summary.get('completed_steps', 0)}")
        print(f"❌ Failed steps: {summary.get('failed_steps', 0)}")
        print(f"⏭️  Skipped steps: {summary.get('skipped_steps', 0)}")
        print(f"⏱️  Total duration: {summary.get('total_duration', 0):.2f} seconds")
        
        print("\n📋 Step Results:")
        for step_name, result in summary.get('step_results', {}).items():
            status_emoji = {
                'completed': '✅',
                'failed': '❌',
                'skipped': '⏭️',
                'running': '🔄',
                'pending': '⏳'
            }.get(result['status'], '❓')
            
            duration = result.get('duration', 0)
            progress = result.get('progress', 0)
            
            duration_str = f"{duration:.2f}s" if duration else "unknown"
            print(f"  {status_emoji} {step_name}: {result['status']} "
                  f"({progress:.1%}, {duration_str})")
            
            if result.get('error_message'):
                print(f"    Error: {result['error_message']}")
        
        # Print dataset information
        if 'shared_data' in summary:
            dataset_info = summary['shared_data'].get('dataset_info', {})
            if dataset_info:
                print(f"\n📁 Dataset Information:")
                print(f"  📄 Dataset file: {dataset_info.get('dataset_file', 'N/A')}")
                print(f"  📊 Total entries: {dataset_info.get('total_entries', 0)}")
                print(f"  🌐 Languages: {', '.join(dataset_info.get('languages', []))}")
        
        print("\n" + "="*60)
    
    def get_status(self) -> dict:
        """Get current pipeline status"""
        return self.executor.get_status()
    
    def cancel(self):
        """Cancel pipeline execution"""
        self.executor.cancel()

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="CAB Dataset Generation Pipeline")
    parser.add_argument(
        "--languages", 
        nargs="+", 
        default=["python", "javascript", "typescript"],
        help="Programming languages to process"
    )
    parser.add_argument(
        "--no-resume", 
        action="store_true",
        help="Don't resume from previous execution"
    )
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--demo", 
        action="store_true",
        help="Run in demo mode with sample data"
    )
    
    args = parser.parse_args()
    
    # Validate configuration
    try:
        config = get_config()
        validation = config.validate_api_keys()
        
        if not validation['github_token'] and not args.demo:
            print("❌ GitHub token not configured")
            print("Please set GITHUB_TOKEN environment variable or run with --demo")
            sys.exit(1)
        
        if not validation['openai_api_key'] and not args.demo:
            print("⚠️  OpenAI API key not configured (some features may not work)")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    # Create and run pipeline
    runner = CABPipelineRunner(args.config)
    
    if args.demo:
        print("🎮 Running in demo mode with sample data")
        # In demo mode, we would use pre-computed data
        # For now, just run with a subset
        languages = ["python"]  # Demo with just Python
    else:
        languages = args.languages
    
    resume = not args.no_resume
    
    try:
        summary = await runner.run_pipeline(languages, resume=resume)
        
        if summary.get("status") == "cancelled":
            print("\n⏹️  Pipeline execution cancelled")
            sys.exit(130)
        elif summary.get("status") == "failed":
            print(f"\n❌ Pipeline execution failed: {summary.get('error')}")
            sys.exit(1)
        else:
            print("\n🎉 Pipeline execution completed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⏹️  Pipeline execution interrupted")
        runner.cancel()
        sys.exit(130)

if __name__ == "__main__":
    asyncio.run(main())
