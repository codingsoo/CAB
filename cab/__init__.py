"""
CAB: CodeAssistBench - Comprehensive Benchmark for AI Coding Assistants

NeurIPS 2025 Datasets & Benchmarks Track
"""

from .core.cab_config import get_config
from .agents.agent_interface import CABAgent, create_agent
from .judges.judge_agents import create_judge
from .utils.simulated_user import CABEvaluator

__version__ = "1.0.0"
__author__ = "Myeongsoo Kim et al."
__email__ = "contact@codeassistbench.org"

__all__ = [
    "CABAgent",
    "create_agent", 
    "create_judge",
    "CABEvaluator",
    "get_config"
]
