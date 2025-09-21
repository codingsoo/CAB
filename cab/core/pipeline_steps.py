"""
Individual Pipeline Steps for CAB Dataset Generation
Each step is a self-contained, resumable component with proper error handling.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline_core import (
    PipelineStep, PipelineContext, StepResult, StepStatus,
    create_step_result, log_step_progress, validate_file_exists, validate_directory_exists
)
from cab_config import get_config

logger = logging.getLogger(__name__)

class RepositoryCollectionStep(PipelineStep):
    """Step 1: Collect repository data from GitHub"""
    
    def __init__(self):
        super().__init__("repo_collection")
    
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that GitHub token is available"""
        config = context.config
        if not config.api.github_token:
            self.logger.error("GitHub token not configured")
            return False
        return True
    
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute repository collection"""
        try:
            self.logger.info("Starting repository collection")
            
            # Create output directory
            repo_dir = context.data_dir / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            
            collected_repos = {}
            total_repos = 0
            
            for i, language in enumerate(context.languages):
                log_step_progress(self.name, i / len(context.languages), f"Processing {language}")
                
                # Run the repository collection script
                result = await self._collect_language_repos(language, repo_dir, context)
                
                if result["success"]:
                    collected_repos[language] = result["repos"]
                    total_repos += len(result["repos"])
                    self.logger.info(f"Collected {len(result['repos'])} repositories for {language}")
                else:
                    self.logger.error(f"Failed to collect repositories for {language}: {result['error']}")
                    return create_step_result(
                        self.name, StepStatus.FAILED,
                        error_message=f"Repository collection failed for {language}: {result['error']}"
                    )
            
            # Save collected repositories
            repos_file = repo_dir / "collected_repositories.json"
            with open(repos_file, "w") as f:
                json.dump(collected_repos, f, indent=2)
            
            log_step_progress(self.name, 1.0, f"Collected {total_repos} repositories total")
            
            return create_step_result(
                self.name, StepStatus.COMPLETED,
                output_data={
                    "repositories": collected_repos,
                    "total_repos": total_repos,
                    "repos_file": str(repos_file)
                },
                progress=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Repository collection failed: {e}")
            return create_step_result(
                self.name, StepStatus.FAILED,
                error_message=str(e)
            )
    
    async def _collect_language_repos(self, language: str, output_dir: Path, context: PipelineContext) -> Dict[str, Any]:
        """Collect repositories for a specific language"""
        try:
            # This would call the actual get_github_repo.py script
            # For now, we'll simulate the process
            
            # In a real implementation, you would:
            # 1. Set up the environment variables
            # 2. Call the get_github_repo.py script with appropriate parameters
            # 3. Parse the output CSV file
            # 4. Return the repository data
            
            # Simulate repository collection
            await asyncio.sleep(1)  # Simulate API calls
            
            # Mock repository data
            mock_repos = [
                {
                    "name": f"{language}-repo-{i}",
                    "owner": f"{language}-owner-{i}",
                    "stars": 1000 + i * 100,
                    "description": f"Sample {language} repository {i}",
                    "language": language
                }
                for i in range(10)  # Collect 10 repos per language
            ]
            
            return {
                "success": True,
                "repos": mock_repos,
                "count": len(mock_repos)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class IssueExtractionStep(PipelineStep):
    """Step 2: Extract GitHub issues from collected repositories"""
    
    def __init__(self):
        super().__init__("issue_extraction", dependencies=["repo_collection"])
    
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that repository data is available"""
        repo_result = context.get_step_result("repo_collection")
        if not repo_result or repo_result.status != StepStatus.COMPLETED:
            self.logger.error("Repository collection step not completed")
            return False
        
        repos_file = repo_result.output_data.get("repos_file")
        if not validate_file_exists(repos_file, self.name):
            return False
        
        return True
    
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute issue extraction"""
        try:
            self.logger.info("Starting issue extraction")
            
            # Get repository data from previous step
            repo_result = context.get_step_result("repo_collection")
            repositories = repo_result.output_data["repositories"]
            
            # Create output directory
            issue_dir = context.data_dir / "issue" / "raw"
            issue_dir.mkdir(parents=True, exist_ok=True)
            
            extracted_issues = {}
            total_issues = 0
            
            for i, (language, repos) in enumerate(repositories.items()):
                log_step_progress(self.name, i / len(repositories), f"Extracting issues for {language}")
                
                # Extract issues for this language
                result = await self._extract_language_issues(language, repos, issue_dir, context)
                
                if result["success"]:
                    extracted_issues[language] = result["issues"]
                    total_issues += len(result["issues"])
                    self.logger.info(f"Extracted {len(result['issues'])} issues for {language}")
                else:
                    self.logger.error(f"Failed to extract issues for {language}: {result['error']}")
                    return create_step_result(
                        self.name, StepStatus.FAILED,
                        error_message=f"Issue extraction failed for {language}: {result['error']}"
                    )
            
            log_step_progress(self.name, 1.0, f"Extracted {total_issues} issues total")
            
            return create_step_result(
                self.name, StepStatus.COMPLETED,
                output_data={
                    "issues": extracted_issues,
                    "total_issues": total_issues,
                    "issue_dir": str(issue_dir)
                },
                progress=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Issue extraction failed: {e}")
            return create_step_result(
                self.name, StepStatus.FAILED,
                error_message=str(e)
            )
    
    async def _extract_language_issues(self, language: str, repos: List[Dict], output_dir: Path, context: PipelineContext) -> Dict[str, Any]:
        """Extract issues for a specific language"""
        try:
            # This would call the actual get_github_issue.py script
            # For now, we'll simulate the process
            
            # Simulate issue extraction
            await asyncio.sleep(2)  # Simulate API calls
            
            # Mock issue data
            mock_issues = [
                {
                    "number": 1000 + i,
                    "title": f"Sample {language} issue {i}",
                    "body": f"This is a sample issue for {language} repository",
                    "created_at": "2024-01-01T00:00:00Z",
                    "closed_at": "2024-01-02T00:00:00Z",
                    "labels": ["bug", "help wanted"],
                    "url": f"https://github.com/{language}-owner/{language}-repo/issues/{1000 + i}",
                    "author": f"user{i}",
                    "comments": [
                        {
                            "user": f"maintainer{i}",
                            "created_at": "2024-01-01T12:00:00Z",
                            "body": f"This is a solution for the {language} issue"
                        }
                    ]
                }
                for i in range(20)  # Extract 20 issues per language
            ]
            
            return {
                "success": True,
                "issues": mock_issues,
                "count": len(mock_issues)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class ConversationFilteringStep(PipelineStep):
    """Step 3: Filter conversations using LLM"""
    
    def __init__(self):
        super().__init__("conversation_filtering", dependencies=["issue_extraction"])
    
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that issue data is available"""
        issue_result = context.get_step_result("issue_extraction")
        if not issue_result or issue_result.status != StepStatus.COMPLETED:
            self.logger.error("Issue extraction step not completed")
            return False
        
        return True
    
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute conversation filtering"""
        try:
            self.logger.info("Starting conversation filtering")
            
            # Get issue data from previous step
            issue_result = context.get_step_result("issue_extraction")
            issues = issue_result.output_data["issues"]
            
            # Create output directory
            filtered_dir = context.data_dir / "issue" / "conv_filter"
            filtered_dir.mkdir(parents=True, exist_ok=True)
            
            filtered_issues = {}
            total_filtered = 0
            
            for i, (language, language_issues) in enumerate(issues.items()):
                log_step_progress(self.name, i / len(issues), f"Filtering conversations for {language}")
                
                # Filter issues for this language
                result = await self._filter_language_conversations(language, language_issues, filtered_dir, context)
                
                if result["success"]:
                    filtered_issues[language] = result["filtered_issues"]
                    total_filtered += len(result["filtered_issues"])
                    self.logger.info(f"Filtered {len(result['filtered_issues'])} conversations for {language}")
                else:
                    self.logger.error(f"Failed to filter conversations for {language}: {result['error']}")
                    return create_step_result(
                        self.name, StepStatus.FAILED,
                        error_message=f"Conversation filtering failed for {language}: {result['error']}"
                    )
            
            log_step_progress(self.name, 1.0, f"Filtered {total_filtered} conversations total")
            
            return create_step_result(
                self.name, StepStatus.COMPLETED,
                output_data={
                    "filtered_issues": filtered_issues,
                    "total_filtered": total_filtered,
                    "filtered_dir": str(filtered_dir)
                },
                progress=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Conversation filtering failed: {e}")
            return create_step_result(
                self.name, StepStatus.FAILED,
                error_message=str(e)
            )
    
    async def _filter_language_conversations(self, language: str, issues: List[Dict], output_dir: Path, context: PipelineContext) -> Dict[str, Any]:
        """Filter conversations for a specific language"""
        try:
            # This would call the actual conv_filter.py script
            # For now, we'll simulate the process
            
            # Simulate LLM filtering
            await asyncio.sleep(3)  # Simulate LLM calls
            
            # Mock filtering (keep 70% of issues)
            filtered_issues = issues[:int(len(issues) * 0.7)]
            
            return {
                "success": True,
                "filtered_issues": filtered_issues,
                "count": len(filtered_issues)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class MessageFilteringStep(PipelineStep):
    """Step 4: Filter irrelevant messages"""
    
    def __init__(self):
        super().__init__("message_filtering", dependencies=["conversation_filtering"])
    
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that filtered conversations are available"""
        conv_result = context.get_step_result("conversation_filtering")
        if not conv_result or conv_result.status != StepStatus.COMPLETED:
            self.logger.error("Conversation filtering step not completed")
            return False
        
        return True
    
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute message filtering"""
        try:
            self.logger.info("Starting message filtering")
            
            # Get filtered data from previous step
            conv_result = context.get_step_result("conversation_filtering")
            filtered_issues = conv_result.output_data["filtered_issues"]
            
            # Create output directory
            msg_filtered_dir = context.data_dir / "issue" / "msg_filter"
            msg_filtered_dir.mkdir(parents=True, exist_ok=True)
            
            msg_filtered_issues = {}
            total_msg_filtered = 0
            
            for i, (language, issues) in enumerate(filtered_issues.items()):
                log_step_progress(self.name, i / len(filtered_issues), f"Filtering messages for {language}")
                
                # Filter messages for this language
                result = await self._filter_language_messages(language, issues, msg_filtered_dir, context)
                
                if result["success"]:
                    msg_filtered_issues[language] = result["msg_filtered_issues"]
                    total_msg_filtered += len(result["msg_filtered_issues"])
                    self.logger.info(f"Message filtered {len(result['msg_filtered_issues'])} issues for {language}")
                else:
                    self.logger.error(f"Failed to filter messages for {language}: {result['error']}")
                    return create_step_result(
                        self.name, StepStatus.FAILED,
                        error_message=f"Message filtering failed for {language}: {result['error']}"
                    )
            
            log_step_progress(self.name, 1.0, f"Message filtered {total_msg_filtered} issues total")
            
            return create_step_result(
                self.name, StepStatus.COMPLETED,
                output_data={
                    "msg_filtered_issues": msg_filtered_issues,
                    "total_msg_filtered": total_msg_filtered,
                    "msg_filtered_dir": str(msg_filtered_dir)
                },
                progress=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Message filtering failed: {e}")
            return create_step_result(
                self.name, StepStatus.FAILED,
                error_message=str(e)
            )
    
    async def _filter_language_messages(self, language: str, issues: List[Dict], output_dir: Path, context: PipelineContext) -> Dict[str, Any]:
        """Filter messages for a specific language"""
        try:
            # This would call the actual msg_filter.py script
            # For now, we'll simulate the process
            
            # Simulate message filtering
            await asyncio.sleep(2)  # Simulate LLM calls
            
            # Mock filtering (keep 80% of issues)
            msg_filtered_issues = issues[:int(len(issues) * 0.8)]
            
            return {
                "success": True,
                "msg_filtered_issues": msg_filtered_issues,
                "count": len(msg_filtered_issues)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class SatisfactionExtractionStep(PipelineStep):
    """Step 5: Extract user satisfaction conditions"""
    
    def __init__(self):
        super().__init__("satisfaction_extraction", dependencies=["message_filtering"])
    
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that message filtered data is available"""
        msg_result = context.get_step_result("message_filtering")
        if not msg_result or msg_result.status != StepStatus.COMPLETED:
            self.logger.error("Message filtering step not completed")
            return False
        
        return True
    
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute satisfaction extraction"""
        try:
            self.logger.info("Starting satisfaction extraction")
            
            # Get message filtered data from previous step
            msg_result = context.get_step_result("message_filtering")
            msg_filtered_issues = msg_result.output_data["msg_filtered_issues"]
            
            # Create output directory
            scon_dir = context.data_dir / "issue" / "scon_filter"
            scon_dir.mkdir(parents=True, exist_ok=True)
            
            scon_issues = {}
            total_scon = 0
            
            for i, (language, issues) in enumerate(msg_filtered_issues.items()):
                log_step_progress(self.name, i / len(msg_filtered_issues), f"Extracting satisfaction for {language}")
                
                # Extract satisfaction for this language
                result = await self._extract_language_satisfaction(language, issues, scon_dir, context)
                
                if result["success"]:
                    scon_issues[language] = result["scon_issues"]
                    total_scon += len(result["scon_issues"])
                    self.logger.info(f"Extracted satisfaction for {len(result['scon_issues'])} issues in {language}")
                else:
                    self.logger.error(f"Failed to extract satisfaction for {language}: {result['error']}")
                    return create_step_result(
                        self.name, StepStatus.FAILED,
                        error_message=f"Satisfaction extraction failed for {language}: {result['error']}"
                    )
            
            log_step_progress(self.name, 1.0, f"Extracted satisfaction for {total_scon} issues total")
            
            return create_step_result(
                self.name, StepStatus.COMPLETED,
                output_data={
                    "scon_issues": scon_issues,
                    "total_scon": total_scon,
                    "scon_dir": str(scon_dir)
                },
                progress=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Satisfaction extraction failed: {e}")
            return create_step_result(
                self.name, StepStatus.FAILED,
                error_message=str(e)
            )
    
    async def _extract_language_satisfaction(self, language: str, issues: List[Dict], output_dir: Path, context: PipelineContext) -> Dict[str, Any]:
        """Extract satisfaction conditions for a specific language"""
        try:
            # This would call the actual scon_filter.py script
            # For now, we'll simulate the process
            
            # Simulate satisfaction extraction
            await asyncio.sleep(2)  # Simulate LLM calls
            
            # Mock satisfaction extraction (keep 90% of issues)
            scon_issues = issues[:int(len(issues) * 0.9)]
            
            # Add satisfaction conditions to each issue
            for issue in scon_issues:
                issue["satisfaction_conditions"] = [
                    "The solution should resolve the reported issue",
                    "The code should be maintainable and well-documented",
                    "Performance should not be significantly impacted"
                ]
            
            return {
                "success": True,
                "scon_issues": scon_issues,
                "count": len(scon_issues)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class DockerClassificationStep(PipelineStep):
    """Step 6: Classify Docker requirements"""
    
    def __init__(self):
        super().__init__("docker_classification", dependencies=["satisfaction_extraction"])
    
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that satisfaction data is available"""
        scon_result = context.get_step_result("satisfaction_extraction")
        if not scon_result or scon_result.status != StepStatus.COMPLETED:
            self.logger.error("Satisfaction extraction step not completed")
            return False
        
        return True
    
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute Docker classification"""
        try:
            self.logger.info("Starting Docker classification")
            
            # Get satisfaction data from previous step
            scon_result = context.get_step_result("satisfaction_extraction")
            scon_issues = scon_result.output_data["scon_issues"]
            
            # Create output directory
            docker_dir = context.data_dir / "issue" / "docker_filter"
            docker_dir.mkdir(parents=True, exist_ok=True)
            
            docker_classified = {}
            total_classified = 0
            
            for i, (language, issues) in enumerate(scon_issues.items()):
                log_step_progress(self.name, i / len(scon_issues), f"Classifying Docker for {language}")
                
                # Classify Docker for this language
                result = await self._classify_language_docker(language, issues, docker_dir, context)
                
                if result["success"]:
                    docker_classified[language] = result["classified_issues"]
                    total_classified += len(result["classified_issues"])
                    self.logger.info(f"Classified Docker for {len(result['classified_issues'])} issues in {language}")
                else:
                    self.logger.error(f"Failed to classify Docker for {language}: {result['error']}")
                    return create_step_result(
                        self.name, StepStatus.FAILED,
                        error_message=f"Docker classification failed for {language}: {result['error']}"
                    )
            
            log_step_progress(self.name, 1.0, f"Classified Docker for {total_classified} issues total")
            
            return create_step_result(
                self.name, StepStatus.COMPLETED,
                output_data={
                    "docker_classified": docker_classified,
                    "total_classified": total_classified,
                    "docker_dir": str(docker_dir)
                },
                progress=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Docker classification failed: {e}")
            return create_step_result(
                self.name, StepStatus.FAILED,
                error_message=str(e)
            )
    
    async def _classify_language_docker(self, language: str, issues: List[Dict], output_dir: Path, context: PipelineContext) -> Dict[str, Any]:
        """Classify Docker requirements for a specific language"""
        try:
            # This would call the actual docker_filter.py script
            # For now, we'll simulate the process
            
            # Simulate Docker classification
            await asyncio.sleep(2)  # Simulate LLM calls
            
            # Mock classification
            classified_issues = []
            for issue in issues:
                # Randomly classify issues
                import random
                docker_type = random.choice(["no_need_docker", "need_docker", "need_docker_but_cannot"])
                issue["docker_classification"] = docker_type
                classified_issues.append(issue)
            
            return {
                "success": True,
                "classified_issues": classified_issues,
                "count": len(classified_issues)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class DatasetGenerationStep(PipelineStep):
    """Step 7: Generate final dataset"""
    
    def __init__(self):
        super().__init__("dataset_generation", dependencies=["docker_classification"])
    
    def validate_inputs(self, context: PipelineContext) -> bool:
        """Validate that Docker classified data is available"""
        docker_result = context.get_step_result("docker_classification")
        if not docker_result or docker_result.status != StepStatus.COMPLETED:
            self.logger.error("Docker classification step not completed")
            return False
        
        return True
    
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute dataset generation"""
        try:
            self.logger.info("Starting dataset generation")
            
            # Get Docker classified data from previous step
            docker_result = context.get_step_result("docker_classification")
            docker_classified = docker_result.output_data["docker_classified"]
            
            # Create output directory
            dataset_dir = context.results_dir / "dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate dataset
            dataset_file = dataset_dir / "dataset.jsonl"
            total_entries = 0
            
            with open(dataset_file, "w") as f:
                for language, issues in docker_classified.items():
                    for issue in issues:
                        # Format issue for dataset
                        dataset_entry = {
                            "language": language,
                            "issue_id": issue.get("number"),
                            "title": issue.get("title"),
                            "body": issue.get("body"),
                            "created_at": issue.get("created_at"),
                            "comments": issue.get("comments", []),
                            "satisfaction_conditions": issue.get("satisfaction_conditions", []),
                            "docker_classification": issue.get("docker_classification"),
                            "url": issue.get("url")
                        }
                        
                        f.write(json.dumps(dataset_entry) + "\n")
                        total_entries += 1
            
            log_step_progress(self.name, 1.0, f"Generated dataset with {total_entries} entries")
            
            return create_step_result(
                self.name, StepStatus.COMPLETED,
                output_data={
                    "dataset_file": str(dataset_file),
                    "total_entries": total_entries,
                    "languages": list(docker_classified.keys())
                },
                progress=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Dataset generation failed: {e}")
            return create_step_result(
                self.name, StepStatus.FAILED,
                error_message=str(e)
            )

# Factory function to create all pipeline steps
def create_pipeline_steps() -> List[PipelineStep]:
    """Create all pipeline steps"""
    return [
        RepositoryCollectionStep(),
        IssueExtractionStep(),
        ConversationFilteringStep(),
        MessageFilteringStep(),
        SatisfactionExtractionStep(),
        DockerClassificationStep(),
        DatasetGenerationStep()
    ]
