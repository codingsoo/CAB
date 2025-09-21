"""
Core Pipeline Framework for CAB Dataset Generation
Provides a robust, resumable, and well-monitored pipeline system.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from datetime import datetime

from cab_config import get_config

logger = logging.getLogger(__name__)

class StepStatus(Enum):
    """Status of a pipeline step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

@dataclass
class StepResult:
    """Result of a pipeline step execution"""
    step_name: str
    status: StepStatus
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.start_time and self.end_time:
            self.duration = self.end_time - self.start_time

@dataclass
class PipelineContext:
    """Context shared across pipeline steps"""
    config: Any
    languages: List[str]
    working_dir: Path
    data_dir: Path
    results_dir: Path
    logs_dir: Path
    temp_dir: Path
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False
    
    def get_step_result(self, step_name: str) -> Optional[StepResult]:
        """Get result of a specific step"""
        return self.step_results.get(step_name)
    
    def set_step_result(self, step_name: str, result: StepResult):
        """Set result of a specific step"""
        self.step_results[step_name] = result
    
    def is_step_completed(self, step_name: str) -> bool:
        """Check if a step is completed"""
        result = self.get_step_result(step_name)
        return result is not None and result.status == StepStatus.COMPLETED

class PipelineStep(ABC):
    """Abstract base class for pipeline steps"""
    
    def __init__(self, name: str, dependencies: List[str] = None):
        self.name = name
        self.dependencies = dependencies or []
        self.logger = logging.getLogger(f"pipeline.{name}")
    
    @abstractmethod
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute the pipeline step"""
        pass
    
    @abstractmethod
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that required inputs are available"""
        pass
    
    def can_run(self, context: PipelineContext) -> bool:
        """Check if this step can run based on dependencies"""
        if context.cancelled:
            return False
        
        for dep in self.dependencies:
            if not context.is_step_completed(dep):
                self.logger.warning(f"Step {self.name} cannot run: dependency {dep} not completed")
                return False
        
        return True
    
    def get_progress(self, context: PipelineContext) -> float:
        """Get current progress of this step (0.0 to 1.0)"""
        result = context.get_step_result(self.name)
        if result:
            return result.progress
        return 0.0

class PipelineExecutor:
    """Main pipeline executor with robust error handling and progress tracking"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = get_config()
        self.steps: Dict[str, PipelineStep] = {}
        self.context: Optional[PipelineContext] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._cancelled = False
        self._lock = threading.Lock()
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Setup pipeline-specific logging"""
        log_dir = Path(self.config.directories.logs)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create pipeline-specific logger
        self.logger = logging.getLogger("pipeline")
        self.logger.setLevel(logging.INFO)
        
        # File handler for pipeline logs
        log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def register_step(self, step: PipelineStep):
        """Register a pipeline step"""
        self.steps[step.name] = step
        logger.info(f"Registered pipeline step: {step.name}")
    
    def create_context(self, languages: List[str]) -> PipelineContext:
        """Create pipeline execution context"""
        working_dir = Path(self.config.directories.base)
        data_dir = Path(self.config.directories.issue_data)
        results_dir = Path(self.config.directories.results)
        logs_dir = Path(self.config.directories.logs)
        temp_dir = working_dir / "temp"
        
        # Create directories
        for dir_path in [working_dir, data_dir, results_dir, logs_dir, temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return PipelineContext(
            config=self.config,
            languages=languages,
            working_dir=working_dir,
            data_dir=data_dir,
            results_dir=results_dir,
            logs_dir=logs_dir,
            temp_dir=temp_dir
        )
    
    def save_context(self, context: PipelineContext):
        """Save pipeline context for resumability"""
        context_file = context.working_dir / "pipeline_context.json"
        
        # Convert context to serializable format
        context_data = {
            "languages": context.languages,
            "step_results": {
                name: {
                    "step_name": result.step_name,
                    "status": result.status.value,
                    "start_time": result.start_time,
                    "end_time": result.end_time,
                    "duration": result.duration,
                    "error_message": result.error_message,
                    "progress": result.progress,
                    "metadata": result.metadata
                }
                for name, result in context.step_results.items()
            },
            "shared_data": context.shared_data,
            "cancelled": context.cancelled,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(context_file, "w") as f:
            json.dump(context_data, f, indent=2)
        
        logger.info(f"Saved pipeline context to {context_file}")
    
    def load_context(self, languages: List[str]) -> Optional[PipelineContext]:
        """Load pipeline context for resumability"""
        context_file = Path(self.config.directories.base) / "pipeline_context.json"
        
        if not context_file.exists():
            return None
        
        try:
            with open(context_file, "r") as f:
                context_data = json.load(f)
            
            # Recreate context
            context = self.create_context(languages)
            
            # Restore step results
            for name, result_data in context_data.get("step_results", {}).items():
                result = StepResult(
                    step_name=result_data["step_name"],
                    status=StepStatus(result_data["status"]),
                    start_time=result_data.get("start_time"),
                    end_time=result_data.get("end_time"),
                    duration=result_data.get("duration"),
                    error_message=result_data.get("error_message"),
                    progress=result_data.get("progress", 0.0),
                    metadata=result_data.get("metadata", {})
                )
                context.set_step_result(name, result)
            
            context.shared_data = context_data.get("shared_data", {})
            context.cancelled = context_data.get("cancelled", False)
            
            logger.info(f"Loaded pipeline context from {context_file}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to load pipeline context: {e}")
            return None
    
    def get_execution_order(self) -> List[str]:
        """Get the order in which steps should be executed based on dependencies"""
        # Topological sort of steps based on dependencies
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(step_name: str):
            if step_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {step_name}")
            if step_name in visited:
                return
            
            temp_visited.add(step_name)
            
            if step_name in self.steps:
                step = self.steps[step_name]
                for dep in step.dependencies:
                    visit(dep)
            
            temp_visited.remove(step_name)
            visited.add(step_name)
            order.append(step_name)
        
        for step_name in self.steps:
            if step_name not in visited:
                visit(step_name)
        
        return order
    
    async def execute_step(self, step_name: str, context: PipelineContext) -> StepResult:
        """Execute a single pipeline step"""
        if step_name not in self.steps:
            return StepResult(
                step_name=step_name,
                status=StepStatus.FAILED,
                error_message=f"Step {step_name} not found"
            )
        
        step = self.steps[step_name]
        
        # Check if step can run
        if not step.can_run(context):
            return StepResult(
                step_name=step_name,
                status=StepStatus.SKIPPED,
                error_message="Dependencies not met or pipeline cancelled"
            )
        
        # Validate inputs
        if not step.validate_inputs(context):
            return StepResult(
                step_name=step_name,
                status=StepStatus.FAILED,
                error_message="Input validation failed"
            )
        
        # Create result object
        result = StepResult(
            step_name=step_name,
            status=StepStatus.RUNNING,
            start_time=time.time()
        )
        
        context.set_step_result(step_name, result)
        
        try:
            self.logger.info(f"Starting step: {step_name}")
            
            # Execute the step
            step_result = await step.execute(context)
            
            # Update result
            result.status = step_result.status
            result.end_time = time.time()
            result.output_data = step_result.output_data
            result.progress = step_result.progress
            result.metadata = step_result.metadata
            
            if step_result.error_message:
                result.error_message = step_result.error_message
                result.error_traceback = step_result.error_traceback
            
            context.set_step_result(step_name, result)
            
            if result.status == StepStatus.COMPLETED:
                duration_str = f"{result.duration:.2f}s" if result.duration else "unknown"
                self.logger.info(f"Completed step: {step_name} in {duration_str}")
            else:
                self.logger.error(f"Failed step: {step_name} - {result.error_message}")
            
            return result
            
        except Exception as e:
            result.status = StepStatus.FAILED
            result.end_time = time.time()
            result.error_message = str(e)
            result.error_traceback = traceback.format_exc()
            
            context.set_step_result(step_name, result)
            self.logger.error(f"Exception in step {step_name}: {e}")
            self.logger.error(traceback.format_exc())
            
            return result
    
    async def execute_pipeline(self, languages: List[str], resume: bool = True) -> Dict[str, Any]:
        """Execute the complete pipeline"""
        self.logger.info(f"Starting pipeline execution for languages: {languages}")
        
        # Load or create context
        if resume:
            self.context = self.load_context(languages)
        
        if self.context is None:
            self.context = self.create_context(languages)
        
        # Get execution order
        execution_order = self.get_execution_order()
        self.logger.info(f"Execution order: {execution_order}")
        
        # Execute steps in order
        for step_name in execution_order:
            if self._cancelled or self.context.cancelled:
                self.logger.info("Pipeline execution cancelled")
                break
            
            # Check if step is already completed
            if self.context.is_step_completed(step_name):
                self.logger.info(f"Skipping already completed step: {step_name}")
                continue
            
            # Execute step
            result = await self.execute_step(step_name, self.context)
            
            # Save context after each step
            self.save_context(self.context)
            
            # If step failed and it's critical, stop pipeline
            if result.status == StepStatus.FAILED:
                critical_steps = ["repo_collection", "issue_extraction", "dataset_generation"]
                if step_name in critical_steps:
                    self.logger.error(f"Critical step {step_name} failed, stopping pipeline")
                    break
        
        # Generate final summary
        summary = self.generate_summary()
        self.logger.info("Pipeline execution completed")
        
        return summary
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate execution summary"""
        if not self.context:
            return {"error": "No context available"}
        
        summary = {
            "languages": self.context.languages,
            "total_steps": len(self.steps),
            "completed_steps": len([r for r in self.context.step_results.values() 
                                  if r.status == StepStatus.COMPLETED]),
            "failed_steps": len([r for r in self.context.step_results.values() 
                               if r.status == StepStatus.FAILED]),
            "skipped_steps": len([r for r in self.context.step_results.values() 
                                if r.status == StepStatus.SKIPPED]),
            "total_duration": sum(r.duration or 0 for r in self.context.step_results.values()),
            "step_results": {
                name: {
                    "status": result.status.value,
                    "duration": result.duration,
                    "progress": result.progress,
                    "error_message": result.error_message
                }
                for name, result in self.context.step_results.items()
            },
            "shared_data": self.context.shared_data
        }
        
        return summary
    
    def cancel(self):
        """Cancel pipeline execution"""
        self._cancelled = True
        if self.context:
            self.context.cancelled = True
        self.logger.info("Pipeline cancellation requested")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        if not self.context:
            return {"status": "not_started"}
        
        return {
            "status": "running" if not self._cancelled else "cancelled",
            "languages": self.context.languages,
            "current_step": self.get_current_step(),
            "progress": self.get_overall_progress(),
            "step_results": {
                name: {
                    "status": result.status.value,
                    "progress": result.progress,
                    "duration": result.duration
                }
                for name, result in self.context.step_results.items()
            }
        }
    
    def get_current_step(self) -> Optional[str]:
        """Get the currently running step"""
        for name, result in self.context.step_results.items():
            if result.status == StepStatus.RUNNING:
                return name
        return None
    
    def get_overall_progress(self) -> float:
        """Get overall pipeline progress (0.0 to 1.0)"""
        if not self.context or not self.steps:
            return 0.0
        
        total_progress = sum(
            self.context.step_results.get(name, StepResult(name, StepStatus.PENDING)).progress
            for name in self.steps
        )
        
        return total_progress / len(self.steps)

# Utility functions for step implementations
def create_step_result(step_name: str, status: StepStatus, **kwargs) -> StepResult:
    """Create a step result with common fields"""
    return StepResult(step_name=step_name, status=status, **kwargs)

def log_step_progress(step_name: str, progress: float, message: str = ""):
    """Log step progress"""
    logger = logging.getLogger(f"pipeline.{step_name}")
    logger.info(f"Progress: {progress:.1%} - {message}")

def validate_file_exists(file_path: Union[str, Path], step_name: str) -> bool:
    """Validate that a file exists"""
    path = Path(file_path)
    if not path.exists():
        logger = logging.getLogger(f"pipeline.{step_name}")
        logger.error(f"Required file not found: {path}")
        return False
    return True

def validate_directory_exists(dir_path: Union[str, Path], step_name: str) -> bool:
    """Validate that a directory exists"""
    path = Path(dir_path)
    if not path.exists() or not path.is_dir():
        logger = logging.getLogger(f"pipeline.{step_name}")
        logger.error(f"Required directory not found: {path}")
        return False
    return True
