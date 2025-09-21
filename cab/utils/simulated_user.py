#!/usr/bin/env python3
"""
Simulated User Environment for CAB (CodeAssistBench)
Provides a testing framework that can evaluate any agent implementing the CABAgent interface.
"""

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from agent_interface import CABAgent, ConversationContext, AgentResponse

logger = logging.getLogger(__name__)

@dataclass
class ConversationResult:
    """Result of a conversation between user and agent"""
    issue_id: str
    agent_name: str
    conversation_history: List[Dict[str, str]]
    final_response: str
    user_satisfied: bool
    satisfaction_reason: str
    rounds: int
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvaluationResult:
    """Result of evaluating an agent on a dataset"""
    agent_name: str
    total_issues: int
    successful_conversations: int
    failed_conversations: int
    average_rounds: float
    average_duration: float
    satisfaction_rate: float
    results: List[ConversationResult] = field(default_factory=list)

class SimulatedUser:
    """
    Simulated user that interacts with AI agents to test their capabilities.
    """
    
    def __init__(self, max_rounds: int = 10, timeout: int = 300):
        """
        Initialize the simulated user.
        
        Args:
            max_rounds: Maximum number of conversation rounds
            timeout: Timeout in seconds for each conversation
        """
        self.max_rounds = max_rounds
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def conduct_conversation(self, agent: CABAgent, issue_data: Dict[str, Any], 
                           repository_path: str = None) -> ConversationResult:
        """
        Conduct a conversation between the simulated user and an agent.
        
        Args:
            agent: The agent to test
            issue_data: The issue data from the dataset
            repository_path: Path to the repository (optional)
            
        Returns:
            ConversationResult: The result of the conversation
        """
        start_time = time.time()
        issue_id = issue_data.get("id", "unknown")
        
        self.logger.info(f"Starting conversation with {agent.name} for issue {issue_id}")
        
        # Initialize conversation
        conversation_history = []
        user_satisfied = False
        satisfaction_reason = ""
        rounds = 0
        
        # Create initial context
        context = ConversationContext(
            issue_data=issue_data,
            conversation_history=conversation_history,
            repository_path=repository_path or "",
            system_prompt=self._get_system_prompt()
        )
        
        try:
            # Initial agent response
            agent_response = agent.respond(context)
            
            if agent_response.error:
                self.logger.error(f"Agent error: {agent_response.error}")
                return ConversationResult(
                    issue_id=issue_id,
                    agent_name=agent.name,
                    conversation_history=conversation_history,
                    final_response="",
                    user_satisfied=False,
                    satisfaction_reason=f"Agent error: {agent_response.error}",
                    rounds=0,
                    duration=time.time() - start_time,
                    metadata={"error": agent_response.error}
                )
            
            # Add agent response to history
            conversation_history.append({
                "role": "maintainer",
                "content": agent_response.content
            })
            rounds += 1
            
            # Simulate user responses and continue conversation
            for round_num in range(1, self.max_rounds):
                if user_satisfied:
                    break
                
                # Simulate user response
                user_response = self._simulate_user_response(
                    issue_data, conversation_history, agent_response.content
                )
                
                if user_response["satisfied"]:
                    user_satisfied = True
                    satisfaction_reason = user_response["reason"]
                    break
                
                # Add user response to history
                conversation_history.append({
                    "role": "user",
                    "content": user_response["content"]
                })
                
                # Get agent response
                context.conversation_history = conversation_history
                agent_response = agent.respond(context)
                
                if agent_response.error:
                    self.logger.error(f"Agent error in round {round_num}: {agent_response.error}")
                    break
                
                # Add agent response to history
                conversation_history.append({
                    "role": "maintainer",
                    "content": agent_response.content
                })
                rounds += 1
            
            duration = time.time() - start_time
            
            return ConversationResult(
                issue_id=issue_id,
                agent_name=agent.name,
                conversation_history=conversation_history,
                final_response=agent_response.content,
                user_satisfied=user_satisfied,
                satisfaction_reason=satisfaction_reason,
                rounds=rounds,
                duration=duration,
                metadata=agent_response.metadata or {}
            )
            
        except Exception as e:
            self.logger.error(f"Error in conversation: {e}")
            return ConversationResult(
                issue_id=issue_id,
                agent_name=agent.name,
                conversation_history=conversation_history,
                final_response="",
                user_satisfied=False,
                satisfaction_reason=f"Conversation error: {str(e)}",
                rounds=rounds,
                duration=time.time() - start_time,
                metadata={"error": str(e)}
            )
    
    def _simulate_user_response(self, issue_data: Dict[str, Any], 
                               conversation_history: List[Dict[str, str]], 
                               agent_response: str) -> Dict[str, Any]:
        """
        Simulate a user response based on satisfaction conditions.
        
        This is a simplified simulation. In a real implementation, this could
        use an LLM to generate more realistic user responses.
        """
        satisfaction_conditions = issue_data.get("user_satisfaction_condition", [])
        
        # Simple heuristic: if agent response is long and detailed, user is satisfied
        if len(agent_response) > 200 and any(keyword in agent_response.lower() 
                                           for keyword in ["solution", "fix", "code", "example"]):
            return {
                "satisfied": True,
                "reason": "Agent provided a detailed solution",
                "content": "Thank you! This solution looks good and addresses my issue."
            }
        
        # If not satisfied, ask for clarification
        if len(conversation_history) < 3:
            return {
                "satisfied": False,
                "reason": "Need more details",
                "content": "Could you provide more specific details about how to implement this solution?"
            }
        else:
            # After a few rounds, accept the solution
            return {
                "satisfied": True,
                "reason": "Accepting solution after clarification",
                "content": "I understand now. Thank you for the help!"
            }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """You are a helpful maintainer of this repository. 
Please provide clear, accurate, and helpful responses to user questions.
Focus on providing working solutions and explanations.
Be specific and include code examples when appropriate."""

class CABEvaluator:
    """
    Main evaluator that tests agents using the simulated user environment.
    """
    
    def __init__(self, simulated_user: SimulatedUser = None):
        """
        Initialize the evaluator.
        
        Args:
            simulated_user: The simulated user instance (creates default if None)
        """
        self.simulated_user = simulated_user or SimulatedUser()
        self.logger = logging.getLogger(__name__)
    
    def evaluate_agent(self, agent: CABAgent, dataset_path: str, 
                      max_issues: int = None) -> EvaluationResult:
        """
        Evaluate an agent on a dataset.
        
        Args:
            agent: The agent to evaluate
            dataset_path: Path to the dataset JSONL file
            max_issues: Maximum number of issues to test (None for all)
            
        Returns:
            EvaluationResult: The evaluation results
        """
        self.logger.info(f"Starting evaluation of {agent.name}")
        
        # Setup agent
        if not agent.setup():
            self.logger.error(f"Failed to setup agent {agent.name}")
            return EvaluationResult(
                agent_name=agent.name,
                total_issues=0,
                successful_conversations=0,
                failed_conversations=1,
                average_rounds=0,
                average_duration=0,
                satisfaction_rate=0.0
            )
        
        # Load dataset
        try:
            with open(dataset_path, 'r') as f:
                issues = [json.loads(line) for line in f]
            
            if max_issues:
                issues = issues[:max_issues]
            
            self.logger.info(f"Loaded {len(issues)} issues for evaluation")
            
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}")
            return EvaluationResult(
                agent_name=agent.name,
                total_issues=0,
                successful_conversations=0,
                failed_conversations=1,
                average_rounds=0,
                average_duration=0,
                satisfaction_rate=0.0
            )
        
        # Evaluate on each issue
        results = []
        successful = 0
        failed = 0
        
        for i, issue_data in enumerate(issues):
            self.logger.info(f"Evaluating issue {i+1}/{len(issues)}: {issue_data.get('id', 'unknown')}")
            
            try:
                result = self.simulated_user.conduct_conversation(agent, issue_data)
                results.append(result)
                
                if result.user_satisfied:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                self.logger.error(f"Error evaluating issue {i+1}: {e}")
                failed += 1
        
        # Cleanup agent
        try:
            agent.cleanup()
        except Exception as e:
            self.logger.warning(f"Error during agent cleanup: {e}")
        
        # Calculate statistics
        total_issues = len(issues)
        avg_rounds = sum(r.rounds for r in results) / len(results) if results else 0
        avg_duration = sum(r.duration for r in results) / len(results) if results else 0
        satisfaction_rate = successful / total_issues if total_issues > 0 else 0
        
        evaluation_result = EvaluationResult(
            agent_name=agent.name,
            total_issues=total_issues,
            successful_conversations=successful,
            failed_conversations=failed,
            average_rounds=avg_rounds,
            average_duration=avg_duration,
            satisfaction_rate=satisfaction_rate,
            results=results
        )
        
        self.logger.info(f"Evaluation completed for {agent.name}")
        self.logger.info(f"Success rate: {satisfaction_rate:.2%}")
        self.logger.info(f"Average rounds: {avg_rounds:.1f}")
        self.logger.info(f"Average duration: {avg_duration:.1f}s")
        
        return evaluation_result
    
    def save_results(self, result: EvaluationResult, output_path: str):
        """
        Save evaluation results to a file.
        
        Args:
            result: The evaluation result
            output_path: Path to save the results
        """
        # Convert to serializable format
        data = {
            "agent_name": result.agent_name,
            "total_issues": result.total_issues,
            "successful_conversations": result.successful_conversations,
            "failed_conversations": result.failed_conversations,
            "average_rounds": result.average_rounds,
            "average_duration": result.average_duration,
            "satisfaction_rate": result.satisfaction_rate,
            "timestamp": datetime.now().isoformat(),
            "results": [
                {
                    "issue_id": r.issue_id,
                    "conversation_history": r.conversation_history,
                    "final_response": r.final_response,
                    "user_satisfied": r.user_satisfied,
                    "satisfaction_reason": r.satisfaction_reason,
                    "rounds": r.rounds,
                    "duration": r.duration,
                    "metadata": r.metadata
                }
                for r in result.results
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Results saved to {output_path}")

def main():
    """Example usage of the simulated user environment"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CAB Simulated User Environment")
    parser.add_argument("--agent", required=True, help="Agent type to test")
    parser.add_argument("--dataset", required=True, help="Path to dataset JSONL file")
    parser.add_argument("--output", help="Path to save results")
    parser.add_argument("--max-issues", type=int, help="Maximum number of issues to test")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create agent
    from agent_interface import create_agent
    agent = create_agent(args.agent)
    
    # Create evaluator
    evaluator = CABEvaluator()
    
    # Run evaluation
    result = evaluator.evaluate_agent(agent, args.dataset, args.max_issues)
    
    # Print results
    print(f"\n🎯 Evaluation Results for {result.agent_name}")
    print("=" * 50)
    print(f"Total Issues: {result.total_issues}")
    print(f"Successful: {result.successful_conversations}")
    print(f"Failed: {result.failed_conversations}")
    print(f"Satisfaction Rate: {result.satisfaction_rate:.2%}")
    print(f"Average Rounds: {result.average_rounds:.1f}")
    print(f"Average Duration: {result.average_duration:.1f}s")
    
    # Save results if requested
    if args.output:
        evaluator.save_results(result, args.output)
        print(f"\nResults saved to: {args.output}")

if __name__ == "__main__":
    main()
