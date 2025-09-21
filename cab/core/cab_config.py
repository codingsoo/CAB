"""
Configuration management for CAB (CodeAssistBench)
Handles loading and validation of configuration from YAML and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API configuration settings"""
    github_token: str
    github_base_url: str
    aws_region: str
    bedrock_model: str
    openai_api_key: Optional[str]
    openai_model: str

@dataclass
class DirectoryConfig:
    """Directory configuration settings"""
    base: str
    repo_data: str
    issue_data: str
    results: str
    logs: str
    docker_data: str
    commits: str

@dataclass
class PipelineConfig:
    """Pipeline configuration settings"""
    max_repos_per_language: int
    max_issues_per_repo: int
    max_conversation_rounds: int
    timeout_seconds: int

@dataclass
class DockerConfig:
    """Docker configuration settings"""
    enabled: bool
    build_timeout: int
    run_timeout: int
    memory_limit: str
    cpu_limit: str

@dataclass
class WebConfig:
    """Web interface configuration settings"""
    host: str
    port: int
    debug: bool
    cors_origins: list

class CABConfig:
    """Main configuration class for CAB"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._raw_config = {}
        self._load_config()
        self._validate_config()
        self._create_directories()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self._raw_config = yaml.safe_load(f)
        
        # Resolve environment variables
        self._resolve_env_vars()
    
    def _resolve_env_vars(self):
        """Resolve environment variables in configuration"""
        def resolve_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.getenv(env_var, value)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            return value
        
        self._raw_config = resolve_value(self._raw_config)
    
    def _validate_config(self):
        """Validate configuration and set up dataclasses"""
        try:
            # API Configuration
            api_config = self._raw_config.get('api', {})
            github_config = api_config.get('github', {})
            aws_config = api_config.get('aws', {})
            openai_config = api_config.get('openai', {})
            
            self.api = APIConfig(
                github_token=github_config.get('token', ''),
                github_base_url=github_config.get('base_url', 'https://api.github.com'),
                aws_region=aws_config.get('region', 'us-east-2'),
                bedrock_model=aws_config.get('bedrock_model', ''),
                openai_api_key=openai_config.get('api_key'),
                openai_model=openai_config.get('model', 'gpt-4o')
            )
            
            # Directory Configuration
            dir_config = self._raw_config.get('directories', {})
            self.directories = DirectoryConfig(
                base=dir_config.get('base', './data'),
                repo_data=dir_config.get('repo_data', './data/repo'),
                issue_data=dir_config.get('issue_data', './data/issue'),
                results=dir_config.get('results', './data/results'),
                logs=dir_config.get('logs', './data/logs'),
                docker_data=dir_config.get('docker_data', './data/docker'),
                commits=dir_config.get('commits', './data/commits')
            )
            
            # Pipeline Configuration
            pipeline_config = self._raw_config.get('pipeline', {})
            self.pipeline = PipelineConfig(
                max_repos_per_language=pipeline_config.get('max_repos_per_language', 100),
                max_issues_per_repo=pipeline_config.get('max_issues_per_repo', 50),
                max_conversation_rounds=pipeline_config.get('max_conversation_rounds', 10),
                timeout_seconds=pipeline_config.get('timeout_seconds', 300)
            )
            
            # Docker Configuration
            docker_config = self._raw_config.get('docker', {})
            self.docker = DockerConfig(
                enabled=docker_config.get('enabled', True),
                build_timeout=docker_config.get('build_timeout', 600),
                run_timeout=docker_config.get('run_timeout', 300),
                memory_limit=docker_config.get('memory_limit', '4g'),
                cpu_limit=docker_config.get('cpu_limit', '2')
            )
            
            # Web Configuration
            web_config = self._raw_config.get('web', {})
            self.web = WebConfig(
                host=web_config.get('host', '0.0.0.0'),
                port=web_config.get('port', 8000),
                debug=web_config.get('debug', False),
                cors_origins=web_config.get('cors_origins', [])
            )
            
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        dirs_to_create = [
            self.directories.base,
            self.directories.repo_data,
            self.directories.issue_data,
            self.directories.results,
            self.directories.logs,
            self.directories.docker_data,
            self.directories.commits
        ]
        
        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are present"""
        validation_results = {
            'github_token': bool(self.api.github_token),
            'openai_api_key': bool(self.api.openai_api_key),
            'aws_configured': bool(self.api.aws_region and self.api.bedrock_model)
        }
        
        return validation_results
    
    def get_required_env_vars(self) -> list:
        """Get list of required environment variables"""
        return ['GITHUB_TOKEN', 'OPENAI_API_KEY']
    
    def print_setup_instructions(self):
        """Print setup instructions for missing configuration"""
        print("\n🔧 CAB Setup Instructions")
        print("=" * 50)
        
        required_vars = self.get_required_env_vars()
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
            print("\nPlease set these environment variables:")
            for var in missing_vars:
                print(f"  export {var}=your_{var.lower()}")
            print("\nOr create a .env file with:")
            for var in missing_vars:
                print(f"  {var}=your_{var.lower()}")
        else:
            print("\n✅ All required environment variables are set!")
        
        validation = self.validate_api_keys()
        if not validation['github_token']:
            print("\n❌ GitHub token not configured")
            print("   Get one at: https://github.com/settings/tokens")
        
        if not validation['openai_api_key']:
            print("\n❌ OpenAI API key not configured")
            print("   Get one at: https://platform.openai.com/api-keys")
        
        if not validation['aws_configured']:
            print("\n⚠️  AWS Bedrock not configured (optional for some features)")
            print("   Configure AWS credentials: aws configure")

# Global configuration instance
config = None

def get_config() -> CABConfig:
    """Get the global configuration instance"""
    global config
    if config is None:
        config = CABConfig()
    return config

def reload_config():
    """Reload configuration from file"""
    global config
    config = CABConfig()
    return config
