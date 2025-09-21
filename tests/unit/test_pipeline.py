"""
Test Suite for CAB Dataset Generation Pipeline
Tests individual steps and the complete pipeline execution.
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from pipeline_core import PipelineExecutor, PipelineContext, StepStatus, StepResult
from pipeline_steps import (
    RepositoryCollectionStep, IssueExtractionStep, ConversationFilteringStep,
    MessageFilteringStep, SatisfactionExtractionStep, DockerClassificationStep,
    DatasetGenerationStep
)

class TestPipelineCore(unittest.TestCase):
    """Test the core pipeline framework"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Mock()
        self.config.directories.base = self.temp_dir
        self.config.directories.issue_data = f"{self.temp_dir}/issue"
        self.config.directories.results = f"{self.temp_dir}/results"
        self.config.directories.logs = f"{self.temp_dir}/logs"
        self.config.api.github_token = "test_token"
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_pipeline_context_creation(self):
        """Test pipeline context creation"""
        context = PipelineContext(
            config=self.config,
            languages=["python"],
            working_dir=Path(self.temp_dir),
            data_dir=Path(f"{self.temp_dir}/issue"),
            results_dir=Path(f"{self.temp_dir}/results"),
            logs_dir=Path(f"{self.temp_dir}/logs"),
            temp_dir=Path(f"{self.temp_dir}/temp")
        )
        
        self.assertEqual(context.languages, ["python"])
        self.assertFalse(context.cancelled)
        self.assertEqual(len(context.step_results), 0)
    
    def test_step_result_creation(self):
        """Test step result creation"""
        result = StepResult(
            step_name="test_step",
            status=StepStatus.COMPLETED,
            start_time=1000.0,
            end_time=1002.0
        )
        
        self.assertEqual(result.step_name, "test_step")
        self.assertEqual(result.status, StepStatus.COMPLETED)
        self.assertEqual(result.duration, 2.0)
    
    def test_pipeline_executor_creation(self):
        """Test pipeline executor creation"""
        executor = PipelineExecutor()
        self.assertIsNotNone(executor)
        self.assertEqual(len(executor.steps), 0)

class TestPipelineSteps(unittest.TestCase):
    """Test individual pipeline steps"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Mock()
        self.config.directories.base = self.temp_dir
        self.config.directories.issue_data = f"{self.temp_dir}/issue"
        self.config.directories.results = f"{self.temp_dir}/results"
        self.config.directories.logs = f"{self.temp_dir}/logs"
        self.config.api.github_token = "test_token"
        
        self.context = PipelineContext(
            config=self.config,
            languages=["python"],
            working_dir=Path(self.temp_dir),
            data_dir=Path(f"{self.temp_dir}/issue"),
            results_dir=Path(f"{self.temp_dir}/results"),
            logs_dir=Path(f"{self.temp_dir}/logs"),
            temp_dir=Path(f"{self.temp_dir}/temp")
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_repository_collection_step_validation(self):
        """Test repository collection step validation"""
        step = RepositoryCollectionStep()
        
        # Test with valid config
        self.assertTrue(step.validate_inputs(self.context))
        
        # Test with missing token
        self.context.config.api.github_token = None
        self.assertFalse(step.validate_inputs(self.context))
    
    @patch('pipeline_steps.asyncio.sleep')
    async def test_repository_collection_step_execution(self, mock_sleep):
        """Test repository collection step execution"""
        step = RepositoryCollectionStep()
        
        # Mock the sleep to avoid actual delays
        mock_sleep.return_value = None
        
        result = await step.execute(self.context)
        
        self.assertEqual(result.status, StepStatus.COMPLETED)
        self.assertIn("repositories", result.output_data)
        self.assertIn("total_repos", result.output_data)
        self.assertEqual(result.progress, 1.0)
    
    def test_issue_extraction_step_validation(self):
        """Test issue extraction step validation"""
        step = IssueExtractionStep()
        
        # Test without repository collection
        self.assertFalse(step.validate_inputs(self.context))
        
        # Test with completed repository collection
        repo_result = StepResult(
            step_name="repo_collection",
            status=StepStatus.COMPLETED,
            output_data={"repos_file": "test_file.json"}
        )
        self.context.set_step_result("repo_collection", repo_result)
        
        # Mock file existence
        with patch('pipeline_core.validate_file_exists', return_value=True):
            self.assertTrue(step.validate_inputs(self.context))
    
    @patch('pipeline_steps.asyncio.sleep')
    async def test_issue_extraction_step_execution(self, mock_sleep):
        """Test issue extraction step execution"""
        step = IssueExtractionStep()
        
        # Set up prerequisite
        repo_result = StepResult(
            step_name="repo_collection",
            status=StepStatus.COMPLETED,
            output_data={
                "repositories": {
                    "python": [
                        {"name": "test-repo", "owner": "test-owner", "stars": 1000}
                    ]
                }
            }
        )
        self.context.set_step_result("repo_collection", repo_result)
        
        # Mock the sleep to avoid actual delays
        mock_sleep.return_value = None
        
        result = await step.execute(self.context)
        
        self.assertEqual(result.status, StepStatus.COMPLETED)
        self.assertIn("issues", result.output_data)
        self.assertIn("total_issues", result.output_data)
        self.assertEqual(result.progress, 1.0)
    
    def test_conversation_filtering_step_validation(self):
        """Test conversation filtering step validation"""
        step = ConversationFilteringStep()
        
        # Test without issue extraction
        self.assertFalse(step.validate_inputs(self.context))
        
        # Test with completed issue extraction
        issue_result = StepResult(
            step_name="issue_extraction",
            status=StepStatus.COMPLETED,
            output_data={"issues": {"python": []}}
        )
        self.context.set_step_result("issue_extraction", issue_result)
        
        self.assertTrue(step.validate_inputs(self.context))
    
    @patch('pipeline_steps.asyncio.sleep')
    async def test_conversation_filtering_step_execution(self, mock_sleep):
        """Test conversation filtering step execution"""
        step = ConversationFilteringStep()
        
        # Set up prerequisite
        issue_result = StepResult(
            step_name="issue_extraction",
            status=StepStatus.COMPLETED,
            output_data={
                "issues": {
                    "python": [
                        {"number": 1, "title": "Test issue", "body": "Test body"}
                    ]
                }
            }
        )
        self.context.set_step_result("issue_extraction", issue_result)
        
        # Mock the sleep to avoid actual delays
        mock_sleep.return_value = None
        
        result = await step.execute(self.context)
        
        self.assertEqual(result.status, StepStatus.COMPLETED)
        self.assertIn("filtered_issues", result.output_data)
        self.assertIn("total_filtered", result.output_data)
        self.assertEqual(result.progress, 1.0)
    
    def test_dataset_generation_step_validation(self):
        """Test dataset generation step validation"""
        step = DatasetGenerationStep()
        
        # Test without Docker classification
        self.assertFalse(step.validate_inputs(self.context))
        
        # Test with completed Docker classification
        docker_result = StepResult(
            step_name="docker_classification",
            status=StepStatus.COMPLETED,
            output_data={"docker_classified": {"python": []}}
        )
        self.context.set_step_result("docker_classification", docker_result)
        
        self.assertTrue(step.validate_inputs(self.context))
    
    @patch('pipeline_steps.asyncio.sleep')
    async def test_dataset_generation_step_execution(self, mock_sleep):
        """Test dataset generation step execution"""
        step = DatasetGenerationStep()
        
        # Set up prerequisite
        docker_result = StepResult(
            step_name="docker_classification",
            status=StepStatus.COMPLETED,
            output_data={
                "docker_classified": {
                    "python": [
                        {
                            "number": 1,
                            "title": "Test issue",
                            "body": "Test body",
                            "created_at": "2024-01-01T00:00:00Z",
                            "comments": [],
                            "satisfaction_conditions": ["Test condition"],
                            "docker_classification": "no_need_docker",
                            "url": "https://github.com/test/repo/issues/1"
                        }
                    ]
                }
            }
        )
        self.context.set_step_result("docker_classification", docker_result)
        
        # Mock the sleep to avoid actual delays
        mock_sleep.return_value = None
        
        result = await step.execute(self.context)
        
        self.assertEqual(result.status, StepStatus.COMPLETED)
        self.assertIn("dataset_file", result.output_data)
        self.assertIn("total_entries", result.output_data)
        self.assertEqual(result.progress, 1.0)
        
        # Verify dataset file was created
        dataset_file = Path(result.output_data["dataset_file"])
        self.assertTrue(dataset_file.exists())
        
        # Verify dataset content
        with open(dataset_file, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            
            entry = json.loads(lines[0])
            self.assertEqual(entry["language"], "python")
            self.assertEqual(entry["title"], "Test issue")

class TestPipelineIntegration(unittest.TestCase):
    """Test complete pipeline integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('pipeline_core.get_config')
    @patch('pipeline_steps.asyncio.sleep')
    async def test_complete_pipeline_execution(self, mock_sleep, mock_get_config):
        """Test complete pipeline execution"""
        # Mock configuration
        mock_config = Mock()
        mock_config.directories.base = self.temp_dir
        mock_config.directories.issue_data = f"{self.temp_dir}/issue"
        mock_config.directories.results = f"{self.temp_dir}/results"
        mock_config.directories.logs = f"{self.temp_dir}/logs"
        mock_config.api.github_token = "test_token"
        mock_get_config.return_value = mock_config
        
        # Mock the sleep to avoid actual delays
        mock_sleep.return_value = None
        
        # Create pipeline executor
        executor = PipelineExecutor()
        
        # Register all steps
        from pipeline_steps import create_pipeline_steps
        steps = create_pipeline_steps()
        for step in steps:
            executor.register_step(step)
        
        # Execute pipeline
        summary = await executor.execute_pipeline(["python"], resume=False)
        
        # Verify results
        self.assertIn("total_steps", summary)
        self.assertIn("completed_steps", summary)
        self.assertIn("step_results", summary)
        
        # Verify all steps completed
        self.assertEqual(summary["completed_steps"], len(steps))
        self.assertEqual(summary["failed_steps"], 0)
        
        # Verify dataset was generated
        self.assertIn("dataset_generation", summary["step_results"])
        dataset_result = summary["step_results"]["dataset_generation"]
        self.assertEqual(dataset_result["status"], "completed")

class TestPipelineErrorHandling(unittest.TestCase):
    """Test pipeline error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Mock()
        self.config.directories.base = self.temp_dir
        self.config.directories.issue_data = f"{self.temp_dir}/issue"
        self.config.directories.results = f"{self.temp_dir}/results"
        self.config.directories.logs = f"{self.temp_dir}/logs"
        self.config.api.github_token = "test_token"
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_step_failure_handling(self):
        """Test handling of step failures"""
        step = RepositoryCollectionStep()
        
        # Mock a failure in the step execution
        with patch.object(step, '_collect_language_repos', return_value={"success": False, "error": "Test error"}):
            result = await step.execute(self.context)
            
            self.assertEqual(result.status, StepStatus.FAILED)
            self.assertIn("Test error", result.error_message)
    
    async def test_dependency_validation(self):
        """Test dependency validation"""
        step = IssueExtractionStep()
        
        # Test without dependencies
        self.assertFalse(step.can_run(self.context))
        
        # Test with completed dependencies
        repo_result = StepResult(
            step_name="repo_collection",
            status=StepStatus.COMPLETED
        )
        self.context.set_step_result("repo_collection", repo_result)
        
        self.assertTrue(step.can_run(self.context))

def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestPipelineCore,
        TestPipelineSteps,
        TestPipelineIntegration,
        TestPipelineErrorHandling
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
