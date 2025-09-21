#!/usr/bin/env python3
"""
Judge Agents for CAB (CodeAssistBench)
Provides different AI models as judges for evaluating agent responses.
"""

import json
import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class JudgeAgent:
    """Base class for judge agents that evaluate agent responses."""
    
    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name
    
    def setup(self) -> bool:
        """Check if the judge agent is available and ready to use."""
        raise NotImplementedError
    
    def judge_response(
        self, 
        issue_data: Dict[str, Any], 
        agent_response: str, 
        docker_results: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, List[str], Dict[str, Any]]:
        """
        Judge an agent response.
        
        Args:
            issue_data: The original issue data
            agent_response: The agent's response to evaluate
            docker_results: Optional Docker validation results
            
        Returns:
            Tuple of (judgment, verdict, key_issues, alignment_score)
        """
        raise NotImplementedError

class AmazonQJudge(JudgeAgent):
    """Judge agent using Amazon Q CLI."""
    
    def __init__(self, q_path: str = "q", timeout: int = 120):
        super().__init__(name="AmazonQJudge", model_name="amazon-q")
        self.q_path = q_path
        self.timeout = timeout
    
    def setup(self) -> bool:
        """Check if Amazon Q CLI is available"""
        try:
            result = subprocess.run(
                [self.q_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Amazon Q CLI found: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Amazon Q CLI not working: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error(f"Amazon Q CLI not found at: {self.q_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking Amazon Q CLI: {e}")
            return False
    
    def judge_response(
        self, 
        issue_data: Dict[str, Any], 
        agent_response: str, 
        docker_results: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, List[str], Dict[str, Any]]:
        """Judge response using Amazon Q CLI"""
        try:
            # Prepare the evaluation prompt
            prompt = self._create_judge_prompt(issue_data, agent_response, docker_results)
            
            # Use Amazon Q CLI to get judgment
            cmd = [
                "qchat", "chat",
                "--no-interactive",
                prompt
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                judgment = result.stdout
                verdict, key_issues, alignment_score = self._parse_judgment(judgment)
                return judgment, verdict, key_issues, alignment_score
            else:
                error_msg = f"Amazon Q CLI error: {result.stderr}"
                return error_msg, "UNKNOWN", [error_msg], {}
                
        except subprocess.TimeoutExpired:
            error_msg = f"Amazon Q CLI timeout after {self.timeout} seconds"
            return error_msg, "UNKNOWN", [error_msg], {}
        except Exception as e:
            error_msg = f"Amazon Q CLI error: {str(e)}"
            return error_msg, "UNKNOWN", [error_msg], {}
    
    def _create_judge_prompt(self, issue_data: Dict[str, Any], agent_response: str, docker_results: Optional[Dict[str, Any]]) -> str:
        """Create the judge prompt for Amazon Q CLI"""
        question_title = issue_data["first_question"]["title"]
        question_body = issue_data["first_question"]["body"]
        comments = issue_data.get("comments", [])
        user_satisfaction_conditions = issue_data.get("user_satisfaction_condition", [])
        
        # Format the original conversation
        conversation = f"Title: {question_title}\n\nQuestion: {question_body}\n\n"
        conversation += "--- Comments from maintainers and users ---\n"
        
        for comment in comments:
            conversation += f"[{comment['user']}]:\n{comment['body']}\n\n"
        
        # Include Docker results if available
        docker_info = ""
        if docker_results:
            success_status = docker_results.get('success', False)
            docker_info = f"""
DOCKER VALIDATION RESULTS:
Status: {success_status}
Logs: {docker_results.get('logs', 'No logs available')}
"""
        
        prompt = f"""You are a judge evaluating an AI agent's response to a technical question.

ORIGINAL ISSUE AND CONVERSATION:
{conversation}

USER SATISFACTION CONDITIONS:
{json.dumps(user_satisfaction_conditions, indent=2)}

AGENT'S RESPONSE TO EVALUATE:
{agent_response}

{docker_info}

Please evaluate the agent's response and provide your assessment in this EXACT format:

TECHNICAL CORRECTNESS: [CORRECT/PARTIALLY CORRECT/INCORRECT]
- CORRECT: The solution is completely accurate
- PARTIALLY CORRECT: The core solution works but has minor technical issues
- INCORRECT: The solution has significant errors or would fail if implemented

ALIGNMENT SCORE: X/Y CONDITIONS MET (Z%)

CONDITION 1: [TRUE/FALSE] <brief description of condition>
CONDITION 2: [TRUE/FALSE] <brief description of condition>
...and so on for each condition

VERBOSITY ASSESSMENT: [CONCISE/APPROPRIATE/VERBOSE]
- CONCISE: The answer lacks some potentially helpful context
- APPROPRIATE: The answer contains just the right amount of information
- VERBOSE: The answer contains unnecessary information

VERDICT: [CORRECT/PARTIALLY CORRECT/INCORRECT]
- CORRECT: Technically correct AND meets ALL user conditions
- PARTIALLY CORRECT: Minor technical issues OR meets SOME conditions
- INCORRECT: Significant technical flaws OR fails to meet ANY conditions

KEY ISSUES: List ALL issues with the agent's response

REASONING: Detailed explanation of your verdict

IMPORTANT: For Docker-related issues, if Docker validation shows "Success: False", the solution is automatically INCORRECT regardless of other factors."""
        
        return prompt
    
    def _parse_judgment(self, judgment: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Parse the judgment response from Amazon Q CLI"""
        # Extract technical correctness
        technical_correctness = "UNKNOWN"
        if "TECHNICAL CORRECTNESS:" in judgment:
            tech_section = judgment.split("TECHNICAL CORRECTNESS:", 1)[1].strip()
            tech_line = tech_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in tech_line.upper():
                technical_correctness = "INCORRECT"
            elif "PARTIALLY" in tech_line.upper():
                technical_correctness = "PARTIALLY CORRECT"
            elif "CORRECT" in tech_line.upper() and "PARTIALLY" not in tech_line.upper():
                technical_correctness = "CORRECT"
        
        # Extract alignment score
        alignment_score = {}
        if "ALIGNMENT SCORE:" in judgment:
            alignment_section = judgment.split("ALIGNMENT SCORE:", 1)[1]
            score_line = alignment_section.split("\n", 1)[0].strip()
            
            score_match = re.search(r'(\d+)/(\d+)', score_line)
            if score_match:
                satisfied = int(score_match.group(1))
                total = int(score_match.group(2))
                
                alignment_score = {
                    'satisfied': satisfied,
                    'total': total,
                    'percentage': (satisfied / total) * 100 if total > 0 else 0,
                    'technical_correctness': technical_correctness
                }
        
        # Extract verdict
        verdict = "UNKNOWN"
        if "VERDICT:" in judgment:
            verdict_section = judgment.split("VERDICT:", 1)[1].strip()
            verdict_line = verdict_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in verdict_line.upper():
                verdict = "INCORRECT"
            elif "PARTIALLY" in verdict_line.upper():
                verdict = "PARTIALLY CORRECT"
            elif "CORRECT" in verdict_line.upper() and "PARTIALLY" not in verdict_line.upper():
                verdict = "CORRECT"
        
        # Extract key issues
        key_issues = []
        if "KEY ISSUES:" in judgment:
            key_issues_section = judgment.split("KEY ISSUES:", 1)[1]
            
            if "REASONING:" in key_issues_section:
                key_issues_section = key_issues_section.split("REASONING:", 1)[0]
            
            for line in key_issues_section.strip().split("\n"):
                clean_line = line.strip()
                if clean_line and not clean_line.startswith("KEY ISSUES:"):
                    if clean_line.startswith("- "):
                        clean_line = clean_line[2:]
                    key_issues.append(clean_line)
        
        return verdict, key_issues, alignment_score

class CursorJudge(JudgeAgent):
    """Judge agent using Cursor CLI."""
    
    def __init__(self, cursor_path: str = "cursor", timeout: int = 120):
        super().__init__(name="CursorJudge", model_name="cursor-cli")
        self.cursor_path = cursor_path
        self.timeout = timeout
    
    def setup(self) -> bool:
        """Check if Cursor CLI is available"""
        try:
            result = subprocess.run(
                [self.cursor_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Cursor CLI found: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Cursor CLI not working: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error(f"Cursor CLI not found at: {self.cursor_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking Cursor CLI: {e}")
            return False
    
    def judge_response(
        self, 
        issue_data: Dict[str, Any], 
        agent_response: str, 
        docker_results: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, List[str], Dict[str, Any]]:
        """Judge response using Cursor CLI"""
        try:
            # Create a temporary file with the evaluation prompt
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                prompt = self._create_judge_prompt(issue_data, agent_response, docker_results)
                f.write(prompt)
                temp_file = f.name
            
            # Use Cursor CLI to open and analyze the file
            # Note: This is a simplified approach - actual Cursor CLI integration
            # would depend on the specific Cursor CLI commands available
            cmd = [self.cursor_path, temp_file]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                # For now, we'll create a mock judgment since Cursor CLI
                # doesn't have a direct chat API like Amazon Q
                judgment = self._create_mock_judgment(issue_data, agent_response, docker_results)
                verdict, key_issues, alignment_score = self._parse_judgment(judgment)
                return judgment, verdict, key_issues, alignment_score
            else:
                error_msg = f"Cursor CLI error: {result.stderr}"
                return error_msg, "UNKNOWN", [error_msg], {}
                
        except subprocess.TimeoutExpired:
            error_msg = f"Cursor CLI timeout after {self.timeout} seconds"
            return error_msg, "UNKNOWN", [error_msg], {}
        except Exception as e:
            error_msg = f"Cursor CLI error: {str(e)}"
            return error_msg, "UNKNOWN", [error_msg], {}
    
    def _create_judge_prompt(self, issue_data: Dict[str, Any], agent_response: str, docker_results: Optional[Dict[str, Any]]) -> str:
        """Create the judge prompt for Cursor CLI"""
        question_title = issue_data["first_question"]["title"]
        question_body = issue_data["first_question"]["body"]
        comments = issue_data.get("comments", [])
        user_satisfaction_conditions = issue_data.get("user_satisfaction_condition", [])
        
        # Format the original conversation
        conversation = f"Title: {question_title}\n\nQuestion: {question_body}\n\n"
        conversation += "--- Comments from maintainers and users ---\n"
        
        for comment in comments:
            conversation += f"[{comment['user']}]:\n{comment['body']}\n\n"
        
        # Include Docker results if available
        docker_info = ""
        if docker_results:
            success_status = docker_results.get('success', False)
            docker_info = f"""
DOCKER VALIDATION RESULTS:
Status: {success_status}
Logs: {docker_results.get('logs', 'No logs available')}
"""
        
        prompt = f"""# Judge Evaluation Request

## Original Issue and Conversation
{conversation}

## User Satisfaction Conditions
{json.dumps(user_satisfaction_conditions, indent=2)}

## Agent's Response to Evaluate
{agent_response}

{docker_info}

## Evaluation Instructions
Please evaluate the agent's response and provide your assessment in this EXACT format:

TECHNICAL CORRECTNESS: [CORRECT/PARTIALLY CORRECT/INCORRECT]
ALIGNMENT SCORE: X/Y CONDITIONS MET (Z%)
CONDITION 1: [TRUE/FALSE] <brief description of condition>
CONDITION 2: [TRUE/FALSE] <brief description of condition>
VERBOSITY ASSESSMENT: [CONCISE/APPROPRIATE/VERBOSE]
VERDICT: [CORRECT/PARTIALLY CORRECT/INCORRECT]
KEY ISSUES: List ALL issues with the agent's response
REASONING: Detailed explanation of your verdict

Please analyze this response and provide your judgment."""
        
        return prompt
    
    def _create_mock_judgment(self, issue_data: Dict[str, Any], agent_response: str, docker_results: Optional[Dict[str, Any]]) -> str:
        """Create a mock judgment for Cursor CLI (since it doesn't have direct chat API)"""
        # This is a placeholder - in a real implementation, you would use
        # Cursor's actual API or integration method
        
        # Simple heuristic-based judgment
        response_length = len(agent_response)
        has_code = "```" in agent_response
        has_explanation = any(word in agent_response.lower() for word in ["because", "reason", "why", "explanation"])
        
        if response_length > 200 and has_code and has_explanation:
            technical_correctness = "CORRECT"
            verdict = "CORRECT"
            satisfaction_rate = 100
        elif response_length > 100 and (has_code or has_explanation):
            technical_correctness = "PARTIALLY CORRECT"
            verdict = "PARTIALLY CORRECT"
            satisfaction_rate = 75
        else:
            technical_correctness = "INCORRECT"
            verdict = "INCORRECT"
            satisfaction_rate = 25
        
        conditions = issue_data.get("user_satisfaction_condition", [])
        satisfied_conditions = int(len(conditions) * satisfaction_rate / 100)
        
        judgment = f"""TECHNICAL CORRECTNESS: {technical_correctness}
- Based on response length, code presence, and explanation quality

ALIGNMENT SCORE: {satisfied_conditions}/{len(conditions)} CONDITIONS MET ({satisfaction_rate}%)

CONDITION 1: {'TRUE' if satisfaction_rate >= 80 else 'FALSE'} Response addresses the main issue
CONDITION 2: {'TRUE' if has_code else 'FALSE'} Provides code examples or solutions
CONDITION 3: {'TRUE' if has_explanation else 'FALSE'} Explains the reasoning

VERBOSITY ASSESSMENT: {'APPROPRIATE' if 100 <= response_length <= 500 else 'CONCISE' if response_length < 100 else 'VERBOSE'}

VERDICT: {verdict}

KEY ISSUES: {'None - comprehensive response' if verdict == 'CORRECT' else 'Response could be more detailed' if verdict == 'PARTIALLY CORRECT' else 'Response lacks sufficient detail and explanation'}

REASONING: {'The response provides a comprehensive solution with code examples and clear explanations.' if verdict == 'CORRECT' else 'The response addresses the issue but could be more complete.' if verdict == 'PARTIALLY CORRECT' else 'The response lacks sufficient detail to fully address the user\'s needs.'}"""
        
        return judgment
    
    def _parse_judgment(self, judgment: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Parse the judgment response (same as AmazonQJudge)"""
        # Extract technical correctness
        technical_correctness = "UNKNOWN"
        if "TECHNICAL CORRECTNESS:" in judgment:
            tech_section = judgment.split("TECHNICAL CORRECTNESS:", 1)[1].strip()
            tech_line = tech_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in tech_line.upper():
                technical_correctness = "INCORRECT"
            elif "PARTIALLY" in tech_line.upper():
                technical_correctness = "PARTIALLY CORRECT"
            elif "CORRECT" in tech_line.upper() and "PARTIALLY" not in tech_line.upper():
                technical_correctness = "CORRECT"
        
        # Extract alignment score
        alignment_score = {}
        if "ALIGNMENT SCORE:" in judgment:
            alignment_section = judgment.split("ALIGNMENT SCORE:", 1)[1]
            score_line = alignment_section.split("\n", 1)[0].strip()
            
            score_match = re.search(r'(\d+)/(\d+)', score_line)
            if score_match:
                satisfied = int(score_match.group(1))
                total = int(score_match.group(2))
                
                alignment_score = {
                    'satisfied': satisfied,
                    'total': total,
                    'percentage': (satisfied / total) * 100 if total > 0 else 0,
                    'technical_correctness': technical_correctness
                }
        
        # Extract verdict
        verdict = "UNKNOWN"
        if "VERDICT:" in judgment:
            verdict_section = judgment.split("VERDICT:", 1)[1].strip()
            verdict_line = verdict_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in verdict_line.upper():
                verdict = "INCORRECT"
            elif "PARTIALLY" in verdict_line.upper():
                verdict = "PARTIALLY CORRECT"
            elif "CORRECT" in verdict_line.upper() and "PARTIALLY" not in verdict_line.upper():
                verdict = "CORRECT"
        
        # Extract key issues
        key_issues = []
        if "KEY ISSUES:" in judgment:
            key_issues_section = judgment.split("KEY ISSUES:", 1)[1]
            
            if "REASONING:" in key_issues_section:
                key_issues_section = key_issues_section.split("REASONING:", 1)[0]
            
            for line in key_issues_section.strip().split("\n"):
                clean_line = line.strip()
                if clean_line and not clean_line.startswith("KEY ISSUES:"):
                    if clean_line.startswith("- "):
                        clean_line = clean_line[2:]
                    key_issues.append(clean_line)
        
        return verdict, key_issues, alignment_score

class LocalLLMJudge(JudgeAgent):
    """Judge agent using local LLM (Ollama)."""
    
    def __init__(self, model_name: str = "llama2", api_url: str = "http://localhost:11434"):
        super().__init__(name=f"LocalLLMJudge-{model_name}", model_name=model_name)
        self.model_name = model_name
        self.api_url = api_url
    
    def setup(self) -> bool:
        """Check if local LLM API is available"""
        try:
            import requests
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if any(self.model_name in name for name in model_names):
                    logger.info(f"Local LLM {self.model_name} found")
                    return True
                else:
                    logger.error(f"Model {self.model_name} not found. Available: {model_names}")
                    return False
            else:
                logger.error(f"Local LLM API not responding: {response.status_code}")
                return False
        except ImportError:
            logger.error("requests library not available for local LLM")
            return False
        except Exception as e:
            logger.error(f"Error checking local LLM: {e}")
            return False
    
    def judge_response(
        self, 
        issue_data: Dict[str, Any], 
        agent_response: str, 
        docker_results: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, List[str], Dict[str, Any]]:
        """Judge response using local LLM"""
        try:
            import requests
            
            # Create the judge prompt
            prompt = self._create_judge_prompt(issue_data, agent_response, docker_results)
            
            # Call local LLM API
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                judgment = result.get("response", "")
                verdict, key_issues, alignment_score = self._parse_judgment(judgment)
                return judgment, verdict, key_issues, alignment_score
            else:
                error_msg = f"Local LLM API error: {response.status_code}"
                return error_msg, "UNKNOWN", [error_msg], {}
                
        except Exception as e:
            error_msg = f"Local LLM error: {str(e)}"
            return error_msg, "UNKNOWN", [error_msg], {}
    
    def _create_judge_prompt(self, issue_data: Dict[str, Any], agent_response: str, docker_results: Optional[Dict[str, Any]]) -> str:
        """Create the judge prompt for local LLM"""
        question_title = issue_data["first_question"]["title"]
        question_body = issue_data["first_question"]["body"]
        comments = issue_data.get("comments", [])
        user_satisfaction_conditions = issue_data.get("user_satisfaction_condition", [])
        
        # Format the original conversation
        conversation = f"Title: {question_title}\n\nQuestion: {question_body}\n\n"
        conversation += "--- Comments from maintainers and users ---\n"
        
        for comment in comments:
            conversation += f"[{comment['user']}]:\n{comment['body']}\n\n"
        
        # Include Docker results if available
        docker_info = ""
        if docker_results:
            success_status = docker_results.get('success', False)
            docker_info = f"""
DOCKER VALIDATION RESULTS:
Status: {success_status}
Logs: {docker_results.get('logs', 'No logs available')}
"""
        
        prompt = f"""You are a judge evaluating an AI agent's response to a technical question.

ORIGINAL ISSUE AND CONVERSATION:
{conversation}

USER SATISFACTION CONDITIONS:
{json.dumps(user_satisfaction_conditions, indent=2)}

AGENT'S RESPONSE TO EVALUATE:
{agent_response}

{docker_info}

Please evaluate the agent's response and provide your assessment in this EXACT format:

TECHNICAL CORRECTNESS: [CORRECT/PARTIALLY CORRECT/INCORRECT]
ALIGNMENT SCORE: X/Y CONDITIONS MET (Z%)
CONDITION 1: [TRUE/FALSE] <brief description of condition>
CONDITION 2: [TRUE/FALSE] <brief description of condition>
VERBOSITY ASSESSMENT: [CONCISE/APPROPRIATE/VERBOSE]
VERDICT: [CORRECT/PARTIALLY CORRECT/INCORRECT]
KEY ISSUES: List ALL issues with the agent's response
REASONING: Detailed explanation of your verdict

IMPORTANT: For Docker-related issues, if Docker validation shows "Success: False", the solution is automatically INCORRECT."""
        
        return prompt
    
    def _parse_judgment(self, judgment: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """Parse the judgment response (same as other judges)"""
        # Extract technical correctness
        technical_correctness = "UNKNOWN"
        if "TECHNICAL CORRECTNESS:" in judgment:
            tech_section = judgment.split("TECHNICAL CORRECTNESS:", 1)[1].strip()
            tech_line = tech_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in tech_line.upper():
                technical_correctness = "INCORRECT"
            elif "PARTIALLY" in tech_line.upper():
                technical_correctness = "PARTIALLY CORRECT"
            elif "CORRECT" in tech_line.upper() and "PARTIALLY" not in tech_line.upper():
                technical_correctness = "CORRECT"
        
        # Extract alignment score
        alignment_score = {}
        if "ALIGNMENT SCORE:" in judgment:
            alignment_section = judgment.split("ALIGNMENT SCORE:", 1)[1]
            score_line = alignment_section.split("\n", 1)[0].strip()
            
            score_match = re.search(r'(\d+)/(\d+)', score_line)
            if score_match:
                satisfied = int(score_match.group(1))
                total = int(score_match.group(2))
                
                alignment_score = {
                    'satisfied': satisfied,
                    'total': total,
                    'percentage': (satisfied / total) * 100 if total > 0 else 0,
                    'technical_correctness': technical_correctness
                }
        
        # Extract verdict
        verdict = "UNKNOWN"
        if "VERDICT:" in judgment:
            verdict_section = judgment.split("VERDICT:", 1)[1].strip()
            verdict_line = verdict_section.split("\n", 1)[0].strip()
            
            if "INCORRECT" in verdict_line.upper():
                verdict = "INCORRECT"
            elif "PARTIALLY" in verdict_line.upper():
                verdict = "PARTIALLY CORRECT"
            elif "CORRECT" in verdict_line.upper() and "PARTIALLY" not in verdict_line.upper():
                verdict = "CORRECT"
        
        # Extract key issues
        key_issues = []
        if "KEY ISSUES:" in judgment:
            key_issues_section = judgment.split("KEY ISSUES:", 1)[1]
            
            if "REASONING:" in key_issues_section:
                key_issues_section = key_issues_section.split("REASONING:", 1)[0]
            
            for line in key_issues_section.strip().split("\n"):
                clean_line = line.strip()
                if clean_line and not clean_line.startswith("KEY ISSUES:"):
                    if clean_line.startswith("- "):
                        clean_line = clean_line[2:]
                    key_issues.append(clean_line)
        
        return verdict, key_issues, alignment_score

# Judge registry
JUDGE_REGISTRY = {
    "amazon-q": AmazonQJudge,
    "cursor-cli": CursorJudge,
    "local-llama2": lambda: LocalLLMJudge("llama2"),
    "local-codellama": lambda: LocalLLMJudge("codellama"),
    "local-mistral": lambda: LocalLLMJudge("mistral"),
}

def create_judge(judge_type: str, **kwargs) -> JudgeAgent:
    """
    Create a judge agent instance by type.
    
    Args:
        judge_type: Type of judge to create
        **kwargs: Additional arguments for judge initialization
        
    Returns:
        JudgeAgent instance
    """
    if judge_type not in JUDGE_REGISTRY:
        raise ValueError(f"Unknown judge type: {judge_type}. Available: {list(JUDGE_REGISTRY.keys())}")
    
    return JUDGE_REGISTRY[judge_type](**kwargs)

def list_available_judges():
    """List all available judges"""
    print("⚖️ Available Judges:")
    print("=" * 40)
    
    for name in JUDGE_REGISTRY.keys():
        print(f"  • {name}")
    
    print("\n💡 Usage:")
    print("  from judge_agents import create_judge")
    print("  judge = create_judge('amazon-q')")

if __name__ == "__main__":
    list_available_judges()
