# 🚀 CAB Dataset Generation Pipeline Guide

## Overview

The CAB (CodeAssistBench) dataset generation pipeline is a robust, resumable, and well-monitored system for creating comprehensive datasets from GitHub issues. This guide explains how to use the new pipeline architecture.

## 🏗️ Architecture

### Core Components

1. **Pipeline Core** (`pipeline_core.py`)
   - Base framework for pipeline execution
   - Error handling and recovery
   - Progress tracking and logging
   - Resumability support

2. **Pipeline Steps** (`pipeline_steps.py`)
   - Individual, self-contained processing steps
   - Dependency management
   - Input validation
   - Output generation

3. **Pipeline Runner** (`pipeline_runner.py`)
   - Main execution orchestrator
   - Status monitoring
   - Summary generation

4. **CLI Interface** (`cab_cli.py`)
   - User-friendly command-line interface
   - Setup and validation
   - Demo mode

## 🔄 Pipeline Steps

### 1. Repository Collection
- **Purpose**: Collect top repositories for each programming language
- **Input**: Programming languages list
- **Output**: Repository metadata (name, owner, stars, description)
- **Dependencies**: None

### 2. Issue Extraction
- **Purpose**: Extract GitHub issues from collected repositories
- **Input**: Repository data from step 1
- **Output**: Raw issue data (title, body, comments, labels)
- **Dependencies**: Repository Collection

### 3. Conversation Filtering
- **Purpose**: Filter conversations using LLM for quality
- **Input**: Raw issue data from step 2
- **Output**: High-quality technical discussions
- **Dependencies**: Issue Extraction

### 4. Message Filtering
- **Purpose**: Remove irrelevant comments and messages
- **Input**: Filtered conversations from step 3
- **Output**: Clean, relevant technical content
- **Dependencies**: Conversation Filtering

### 5. Satisfaction Extraction
- **Purpose**: Extract user satisfaction conditions
- **Input**: Clean conversations from step 4
- **Output**: User requirements and success criteria
- **Dependencies**: Message Filtering

### 6. Docker Classification
- **Purpose**: Classify Docker environment requirements
- **Input**: Conversations with satisfaction conditions
- **Output**: Docker requirement classifications
- **Dependencies**: Satisfaction Extraction

### 7. Dataset Generation
- **Purpose**: Generate final structured dataset
- **Input**: All processed data from previous steps
- **Output**: JSONL dataset file
- **Dependencies**: Docker Classification

## 🚀 Quick Start

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup configuration
python cab_cli.py setup
```

### 2. Configure API Keys
Create a `.env` file with your API keys:
```bash
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_key
```

### 3. Generate Dataset
```bash
# Generate for specific languages
python cab_cli.py generate --languages python javascript typescript

# Run in demo mode (no API keys required)
python cab_cli.py demo
```

## 📊 Usage Examples

### Basic Usage
```bash
# Setup and validate configuration
python cab_cli.py setup

# Generate dataset for Python and JavaScript
python cab_cli.py generate --languages python javascript

# Check pipeline status
python cab_cli.py status

# Run tests
python cab_cli.py test
```

### Advanced Usage
```bash
# Generate without resuming from previous run
python cab_cli.py generate --languages python --no-resume

# Run demo with sample data
python cab_cli.py demo

# Get help
python cab_cli.py help
```

### Programmatic Usage
```python
from pipeline_runner import CABPipelineRunner

# Create runner
runner = CABPipelineRunner()

# Run pipeline
summary = await runner.run_pipeline(["python", "javascript"])

# Check status
status = runner.get_status()
```

## 🔧 Configuration

### Environment Variables
- `GITHUB_TOKEN`: GitHub API token (required)
- `OPENAI_API_KEY`: OpenAI API key (recommended)
- `AWS_ACCESS_KEY_ID`: AWS access key (optional)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (optional)

### Configuration File
The pipeline uses `config.yaml` for centralized configuration:

```yaml
# API Configuration
api:
  github:
    token: "${GITHUB_TOKEN}"
    base_url: "https://api.github.com"
  
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4o"

# Directory Configuration
directories:
  base: "./data"
  issue_data: "${directories.base}/issue"
  results: "${directories.base}/results"
  logs: "${directories.base}/logs"

# Pipeline Configuration
pipeline:
  max_repos_per_language: 100
  max_issues_per_repo: 50
  max_conversation_rounds: 10
  timeout_seconds: 300
```

## 📈 Monitoring and Logging

### Progress Tracking
The pipeline provides real-time progress tracking:
- Overall progress (0-100%)
- Individual step progress
- Current step identification
- Estimated time remaining

### Logging
Comprehensive logging is available:
- Console output for real-time monitoring
- File logging for detailed analysis
- Step-specific loggers
- Error tracking and debugging

### Status Monitoring
```bash
# Check current status
python cab_cli.py status

# View logs
tail -f data/logs/pipeline_*.log
```

## 🔄 Resumability

The pipeline supports resumability:
- Automatic checkpointing after each step
- Resume from last successful step
- Skip already completed steps
- Preserve intermediate results

### Resume Options
```bash
# Resume from previous run (default)
python cab_cli.py generate --languages python

# Start fresh (don't resume)
python cab_cli.py generate --languages python --no-resume
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python cab_cli.py test

# Run specific test file
python test_pipeline.py
```

### Test Coverage
The test suite covers:
- Individual step functionality
- Pipeline integration
- Error handling
- Configuration validation
- Resumability

## 🐛 Troubleshooting

### Common Issues

#### 1. API Key Errors
```
❌ GitHub token not configured
```
**Solution**: Set `GITHUB_TOKEN` in your `.env` file

#### 2. Permission Errors
```
❌ Permission denied: data/logs/
```
**Solution**: Ensure write permissions for data directories

#### 3. Network Errors
```
❌ Failed to fetch repositories
```
**Solution**: Check internet connection and API rate limits

#### 4. Memory Issues
```
❌ Out of memory during processing
```
**Solution**: Reduce batch sizes in configuration

### Debug Mode
```bash
# Enable debug logging
export CAB_LOG_LEVEL=DEBUG
python cab_cli.py generate --languages python
```

### Log Analysis
```bash
# View recent logs
tail -f data/logs/pipeline_*.log

# Search for errors
grep -i error data/logs/pipeline_*.log

# Check specific step
grep "conversation_filtering" data/logs/pipeline_*.log
```

## 📊 Output Format

### Dataset Structure
The final dataset is a JSONL file with entries like:

```json
{
  "language": "python",
  "issue_id": 1234,
  "title": "TypeError when using pandas DataFrame",
  "body": "I'm getting a TypeError when...",
  "created_at": "2024-01-01T00:00:00Z",
  "comments": [
    {
      "user": "maintainer",
      "created_at": "2024-01-01T12:00:00Z",
      "body": "This is caused by incorrect type handling..."
    }
  ],
  "satisfaction_conditions": [
    "The solution should resolve the TypeError",
    "The code should be maintainable"
  ],
  "docker_classification": "no_need_docker",
  "url": "https://github.com/owner/repo/issues/1234"
}
```

### Statistics
The pipeline generates comprehensive statistics:
- Total repositories collected
- Total issues extracted
- Filtering success rates
- Language distribution
- Processing times

## 🔮 Future Enhancements

### Planned Features
1. **Parallel Processing**: Multi-threaded step execution
2. **Cloud Integration**: AWS/GCP deployment options
3. **Advanced Filtering**: More sophisticated content filtering
4. **Quality Metrics**: Automated quality assessment
5. **Export Options**: Multiple output formats

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📞 Support

### Getting Help
- **Documentation**: This guide and README.md
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for questions
- **Email**: Contact the maintainers

### Community
- **Contributors**: See CONTRIBUTORS.md
- **Code of Conduct**: See CODE_OF_CONDUCT.md
- **License**: MIT License

---

**The CAB dataset generation pipeline provides a robust, scalable, and user-friendly way to create comprehensive datasets for evaluating AI coding assistants. With proper configuration and monitoring, it can process thousands of repositories and issues efficiently.**
