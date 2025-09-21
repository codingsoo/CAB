"""
Simplified CAB Pipeline Runner
Provides a unified interface to run the entire CAB pipeline with proper error handling.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import time

from cab_config import get_config

logger = logging.getLogger(__name__)

class PipelineStep(Enum):
    """Enumeration of pipeline steps"""
    REPO_COLLECTION = "repo_collection"
    ISSUE_EXTRACTION = "issue_extraction"
    CONVERSATION_FILTERING = "conversation_filtering"
    MESSAGE_FILTERING = "message_filtering"
    SATISFACTION_EXTRACTION = "satisfaction_extraction"
    DOCKER_CLASSIFICATION = "docker_classification"
    COMMIT_FETCHING = "commit_fetching"
    DOCKERFILE_GENERATION = "dockerfile_generation"
    DATASET_GENERATION = "dataset_generation"
    BENCHMARK_RUNNING = "benchmark_running"
    RESULTS_ANALYSIS = "results_analysis"

@dataclass
class PipelineStatus:
    """Status of a pipeline step"""
    step: PipelineStep
    status: str  # "pending", "running", "completed", "failed", "skipped"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    details: Dict[str, Any] = None

class CABPipeline:
    """Main pipeline orchestrator for CAB"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = get_config()
        self.status: Dict[PipelineStep, PipelineStatus] = {}
        self.results: Dict[str, Any] = {}
        
        # Initialize all steps as pending
        for step in PipelineStep:
            self.status[step] = PipelineStatus(step=step, status="pending")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        return {
            step.value: {
                "status": status.status,
                "progress": status.progress,
                "start_time": status.start_time,
                "end_time": status.end_time,
                "error_message": status.error_message,
                "details": status.details or {}
            }
            for step, status in self.status.items()
        }
    
    def _update_status(self, step: PipelineStep, status: str, **kwargs):
        """Update status of a pipeline step"""
        if step in self.status:
            self.status[step].status = status
            for key, value in kwargs.items():
                if hasattr(self.status[step], key):
                    setattr(self.status[step], key, value)
        
        logger.info(f"Step {step.value}: {status}")
    
    def _run_step(self, step: PipelineStep, func, *args, **kwargs):
        """Run a pipeline step with proper error handling"""
        self._update_status(step, "running", start_time=time.time())
        
        try:
            result = func(*args, **kwargs)
            self._update_status(
                step, 
                "completed", 
                end_time=time.time(),
                progress=1.0,
                details={"result": result}
            )
            return result
        except Exception as e:
            self._update_status(
                step,
                "failed",
                end_time=time.time(),
                error_message=str(e)
            )
            logger.error(f"Step {step.value} failed: {e}")
            raise
    
    def run_full_pipeline(self, languages: List[str] = None, skip_steps: List[PipelineStep] = None) -> Dict[str, Any]:
        """Run the complete CAB pipeline"""
        if languages is None:
            languages = ["python", "javascript", "typescript", "java", "c", "c++", "c#"]
        
        if skip_steps is None:
            skip_steps = []
        
        logger.info(f"Starting CAB pipeline for languages: {languages}")
        
        try:
            # Step 1: Repository Collection
            if PipelineStep.REPO_COLLECTION not in skip_steps:
                self._run_step(PipelineStep.REPO_COLLECTION, self._collect_repositories, languages)
            
            # Step 2: Issue Extraction
            if PipelineStep.ISSUE_EXTRACTION not in skip_steps:
                self._run_step(PipelineStep.ISSUE_EXTRACTION, self._extract_issues, languages)
            
            # Step 3: Conversation Filtering
            if PipelineStep.CONVERSATION_FILTERING not in skip_steps:
                self._run_step(PipelineStep.CONVERSATION_FILTERING, self._filter_conversations, languages)
            
            # Step 4: Message Filtering
            if PipelineStep.MESSAGE_FILTERING not in skip_steps:
                self._run_step(PipelineStep.MESSAGE_FILTERING, self._filter_messages, languages)
            
            # Step 5: Satisfaction Extraction
            if PipelineStep.SATISFACTION_EXTRACTION not in skip_steps:
                self._run_step(PipelineStep.SATISFACTION_EXTRACTION, self._extract_satisfaction, languages)
            
            # Step 6: Docker Classification
            if PipelineStep.DOCKER_CLASSIFICATION not in skip_steps:
                self._run_step(PipelineStep.DOCKER_CLASSIFICATION, self._classify_docker, languages)
            
            # Step 7: Commit Fetching
            if PipelineStep.COMMIT_FETCHING not in skip_steps:
                self._run_step(PipelineStep.COMMIT_FETCHING, self._fetch_commits, languages)
            
            # Step 8: Dockerfile Generation
            if PipelineStep.DOCKERFILE_GENERATION not in skip_steps:
                self._run_step(PipelineStep.DOCKERFILE_GENERATION, self._generate_dockerfiles, languages)
            
            # Step 9: Dataset Generation
            if PipelineStep.DATASET_GENERATION not in skip_steps:
                self._run_step(PipelineStep.DATASET_GENERATION, self._generate_dataset, languages)
            
            # Step 10: Benchmark Running
            if PipelineStep.BENCHMARK_RUNNING not in skip_steps:
                self._run_step(PipelineStep.BENCHMARK_RUNNING, self._run_benchmark, languages)
            
            # Step 11: Results Analysis
            if PipelineStep.RESULTS_ANALYSIS not in skip_steps:
                self._run_step(PipelineStep.RESULTS_ANALYSIS, self._analyze_results, languages)
            
            logger.info("CAB pipeline completed successfully!")
            return self.get_status()
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def run_demo_mode(self) -> Dict[str, Any]:
        """Run pipeline in demo mode with pre-computed data"""
        logger.info("Running CAB pipeline in demo mode")
        
        # In demo mode, we'll use pre-computed results
        demo_results = {
            "languages": ["python", "javascript", "typescript"],
            "total_issues": 150,
            "total_repos": 45,
            "pipeline_status": "completed",
            "demo_mode": True
        }
        
        # Mark all steps as completed
        for step in PipelineStep:
            self._update_status(step, "completed", progress=1.0)
        
        return demo_results
    
    # Step implementations (these would call the existing scripts)
    def _collect_repositories(self, languages: List[str]) -> Dict[str, Any]:
        """Collect repository data"""
        # This would call get_github_repo.py with proper configuration
        logger.info("Collecting repository data...")
        # Implementation would go here
        return {"repos_collected": len(languages) * 10}
    
    def _extract_issues(self, languages: List[str]) -> Dict[str, Any]:
        """Extract GitHub issues"""
        # This would call get_github_issue.py
        logger.info("Extracting GitHub issues...")
        return {"issues_extracted": len(languages) * 50}
    
    def _filter_conversations(self, languages: List[str]) -> Dict[str, Any]:
        """Filter conversations using LLM"""
        # This would call conv_filter.py
        logger.info("Filtering conversations...")
        return {"conversations_filtered": len(languages) * 30}
    
    def _filter_messages(self, languages: List[str]) -> Dict[str, Any]:
        """Filter irrelevant messages"""
        # This would call msg_filter.py
        logger.info("Filtering messages...")
        return {"messages_filtered": len(languages) * 25}
    
    def _extract_satisfaction(self, languages: List[str]) -> Dict[str, Any]:
        """Extract satisfaction conditions"""
        # This would call scon_filter.py
        logger.info("Extracting satisfaction conditions...")
        return {"satisfaction_conditions": len(languages) * 20}
    
    def _classify_docker(self, languages: List[str]) -> Dict[str, Any]:
        """Classify Docker requirements"""
        # This would call docker_filter.py
        logger.info("Classifying Docker requirements...")
        return {"docker_classified": len(languages) * 15}
    
    def _fetch_commits(self, languages: List[str]) -> Dict[str, Any]:
        """Fetch GitHub commits"""
        # This would call get_github_commit.py
        logger.info("Fetching commits...")
        return {"commits_fetched": len(languages) * 100}
    
    def _generate_dockerfiles(self, languages: List[str]) -> Dict[str, Any]:
        """Generate Dockerfiles"""
        # This would call generate_dockerfile.py
        logger.info("Generating Dockerfiles...")
        return {"dockerfiles_generated": len(languages) * 5}
    
    def _generate_dataset(self, languages: List[str]) -> Dict[str, Any]:
        """Generate final dataset"""
        # This would call generate_dataset.py
        logger.info("Generating dataset...")
        return {"dataset_entries": len(languages) * 20}
    
    def _run_benchmark(self, languages: List[str]) -> Dict[str, Any]:
        """Run the benchmark"""
        # This would call run.py
        logger.info("Running benchmark...")
        return {"benchmark_completed": True}
    
    def _analyze_results(self, languages: List[str]) -> Dict[str, Any]:
        """Analyze results"""
        # This would call produce_results.py
        logger.info("Analyzing results...")
        return {"results_analyzed": True}

def main():
    """Main entry point for the pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run CAB Pipeline")
    parser.add_argument("--languages", nargs="+", default=["python"], 
                       help="Programming languages to process")
    parser.add_argument("--demo", action="store_true", 
                       help="Run in demo mode with pre-computed data")
    parser.add_argument("--skip-steps", nargs="+", 
                       help="Steps to skip")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    pipeline = CABPipeline()
    
    if args.demo:
        results = pipeline.run_demo_mode()
    else:
        skip_steps = [PipelineStep(step) for step in args.skip_steps] if args.skip_steps else []
        results = pipeline.run_full_pipeline(args.languages, skip_steps)
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
