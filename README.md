# 🚀 CAB: CodeAssistBench

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: CC--BY--NC--4.0](https://img.shields.io/badge/License-CC--BY--NC--4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![NeurIPS 2025](https://img.shields.io/badge/NeurIPS-2025-orange.svg)](https://neurips.cc/)
[![arXiv](https://img.shields.io/badge/arXiv-2507.10646-b31b1b.svg)](https://arxiv.org/abs/2507.10646)

> **NeurIPS 2025 Datasets & Benchmarks Track** - Comprehensive Benchmark for AI Coding Assistants

**CAB (CodeAssistBench)** evaluates AI coding assistants on real-world programming problems from GitHub issues. It provides a standardized way to measure how well AI models can help with actual development challenges.

## 🎯 What CAB Does

CAB is designed to provide a robust and reproducible benchmark for evaluating the capabilities of AI coding assistants in multi-turn, chat-based interactions within realistic project environments.

### 📊 **Step 1: Dataset Collection**
**Option A: Use Pre-Collected Dataset**
- **Ready-to-use**: Complete dataset from our NeurIPS 2025 paper
- **7 programming languages**: C, C++, C#, Java, JavaScript, Python, and TypeScript
- **Real GitHub issues**: Curated from top-starred repositories with verified solutions
- **Multi-turn conversations**: Full discussion threads between users and maintainers
- **Docker environments**: Automatically generated build environments for reproducible testing

**Option B: Generate Custom Dataset**
- **Automated pipeline**: Collect fresh datasets from GitHub with your own criteria
- **Customizable filtering**: Choose specific languages, repository types, or issue categories
- **Scalable processing**: Handle thousands of repositories and issues
- **Quality control**: LLM-powered filtering for high-quality, technically relevant conversations
- **Fresh data**: Get the latest issues and repositories for up-to-date evaluation

### 🤖 **Step 2: Simulated User Environment**
- **Modular Architecture**: Clean separation between agents and testing framework
- **Agent Interface**: Any AI model can be tested by implementing the `CABAgent` interface
- **Realistic interactions**: Simulate real developer scenarios with AI coding assistants
- **Multi-turn conversations**: Support for back-and-forth dialogue between user and assistant
- **Context awareness**: Maintain conversation history and project context
- **Environment setup**: Automatic Docker containerization for isolated testing
- **Easy Integration**: Support for OpenAI, Claude, local models, and custom agents

### ⚖️ **Step 3: Automated Judging**
- **Solution evaluation**: Compare AI-generated solutions against human-verified answers
- **Satisfaction criteria**: Evaluate based on user satisfaction conditions from original issues
- **Multi-metric assessment**: Comprehensive evaluation across multiple dimensions
- **Technical correctness**: Assess accuracy and completeness of solutions
- **Docker validation**: Verify solutions work in containerized environments
- **Verbosity assessment**: Evaluate response clarity and appropriateness
- **Reproducible scoring**: Consistent and objective evaluation methodology
- **Performance analytics**: Detailed analysis and comparison of different AI models

## 🚀 Quick Start

### 🎯 Super Easy Start (Recommended)
```bash
# See what CAB can do (no setup required)
python scripts/try_cab.py

# One-command setup
python scripts/super_easy_setup.py

# Quick test (no API keys needed)
python tests/integration/test_agent.py --agent mock --dataset data/converted_dataset.jsonl --max-issues 1
```

📚 **For complete beginners**: See [docs/SUPER_EASY_START.md](docs/SUPER_EASY_START.md)

### 🔧 Manual Setup
```bash
# Prerequisites: Python 3.8+
git clone https://github.com/your-org/CodeAssistBench.git
cd CodeAssistBench
pip install -r requirements.txt

# Configuration (optional for basic testing)
cp .env.template .env
# Edit .env with your API keys if needed
```

## 📊 Usage

### 1. Data Setup
Generate the benchmark dataset from GitHub issues:

```bash
# Generate dataset for specific languages
python scripts/cab_cli.py generate --languages python javascript typescript

# Or try demo mode (no API keys needed)
python scripts/cab_cli.py demo
```

This creates a dataset of real GitHub issues with:
- Problem descriptions
- Human-provided solutions
- User satisfaction criteria
- Docker environment requirements

### 2. Agent Running
Test AI agents using the modular framework:

```bash
# Test with mock agent (no API calls required)
python tests/integration/test_agent.py --agent mock --dataset data/converted_dataset.jsonl

# Test with OpenAI GPT-4
python tests/integration/test_agent.py --agent openai-gpt4 --dataset data/converted_dataset.jsonl --max-issues 5

# Test with Claude
python tests/integration/test_agent.py --agent claude-sonnet --dataset data/converted_dataset.jsonl --verbose

# Test with Cursor CLI (if installed)
python tests/integration/test_agent.py --agent cursor-cli --dataset data/converted_dataset.jsonl

# Test with Amazon Q CLI (if installed)
python tests/integration/test_agent.py --agent amazon-q --dataset data/converted_dataset.jsonl

# Test with Local LLM (Ollama)
python tests/integration/test_agent.py --agent local-llama2 --dataset data/converted_dataset.jsonl

# Test Judge functionality (Step 3)
python tests/integration/test_judge.py

# Test Full Pipeline (Agent + Judge)
python tests/integration/test_full_pipeline.py

# Test External AI Tools as Judges
python tests/integration/test_judge_agents.py

# Compare Different Judges
python examples/judges/example_judge_comparison.py
```

The benchmark tests AI agents by:
- **Modular Testing**: Any agent implementing `CABAgent` interface can be tested
- **Realistic Scenarios**: Presenting real GitHub issues with multi-turn conversations
- **Flexible Integration**: Support for OpenAI, Claude, local models, and custom agents
- Allowing agents to explore codebases
- Recording agent responses and solutions
- Measuring solution quality

### 3. Judge Running
Evaluate agent performance:

```bash
# Analyze results
python cab/data/produce_results.py

# Generate performance report
python cab/data/produce_results.py --output results_report.json
```

The judge evaluates:
- **Accuracy**: How often agents provide correct solutions
- **Satisfaction**: How well solutions meet user requirements
- **Efficiency**: Time and resource usage
- **Reproducibility**: Success rate in Docker environments

## 📈 Results

CAB generates comprehensive evaluation metrics:

- **Overall Performance**: Accuracy across all issues
- **Language-specific Results**: Performance by programming language
- **Difficulty Analysis**: Performance on easy/medium/hard problems
- **Solution Quality**: Detailed analysis of agent responses

### Example Results
```
Overall Accuracy: 73.2%
├── Python: 78.5%
├── JavaScript: 71.8%
└── TypeScript: 69.3%

Solution Quality:
├── Correct: 73.2%
├── Partially Correct: 18.4%
└── Incorrect: 8.4%
```

## 🏗️ Architecture

CAB uses a **modular architecture** with clear separation of concerns:

### **Agent Interface** (`cab/agents/agent_interface.py`)
- **`CABAgent`**: Abstract base class that any AI agent must implement
- **Built-in Agents**: OpenAI, Claude, and Mock agents ready to use
- **External Agents**: Cursor CLI, GitHub Copilot, Local LLMs (Ollama)
- **Easy Extension**: Add new agents by implementing the interface
- **No Dependencies**: Agents are independent of the testing framework

### **Simulated User Environment** (`cab/utils/simulated_user.py`)
- **`SimulatedUser`**: Simulates realistic user interactions
- **`CABEvaluator`**: Orchestrates agent evaluation on datasets
- **Multi-turn Conversations**: Supports back-and-forth dialogue
- **Satisfaction Tracking**: Evaluates user satisfaction criteria

### **Benefits of This Architecture**
- ✅ **Modular**: Test any agent without modifying the framework
- ✅ **Extensible**: Easy to add new AI models or testing strategies
- ✅ **Independent**: Agents and testing framework are decoupled
- ✅ **Testable**: Mock agent allows testing without API calls
- ✅ **Flexible**: Support for different conversation patterns and evaluation metrics

## 🔧 External Agent Integration

CAB supports testing external AI tools and agents:

### **Available External Agents**
- **Cursor CLI**: Test Cursor's AI coding assistant
- **GitHub Copilot**: Test GitHub Copilot CLI
- **Amazon Q CLI**: Test Amazon Q's AI coding assistant
- **Local LLMs**: Test Ollama models (Llama2, CodeLlama, Mistral)
- **Custom Scripts**: Test any custom AI agent script

### **Setup External Agents**
```bash
# Check available external agents
python tests/integration/test_external_agents.py

# Test Cursor CLI (requires Cursor CLI installation)
python tests/integration/test_agent.py --agent cursor-cli --dataset data/converted_dataset.jsonl

# Test Local LLM (requires Ollama installation)
python tests/integration/test_agent.py --agent local-llama2 --dataset data/converted_dataset.jsonl
```

### **Adding Custom Agents**

#### Quick Start
```bash
# Test your custom agent directly
python tests/integration/test_custom_agent.py my_agent.py MyAgent --max-issues 3
```

#### Custom Agent Template
```python
# my_custom_agent.py
from cab.agents.agent_interface import CABAgent, ConversationContext, AgentResponse

class MyAgent(CABAgent):
    def __init__(self):
        super().__init__(name="MyAgent", model_name="my-model")
    
    def setup(self) -> bool:
        """Initialize your agent"""
        return True
    
    def respond(self, context: ConversationContext) -> AgentResponse:
        """Generate response to the issue"""
        issue = context.issue_data["first_question"]
        response = f"I can help with: {issue['title']}"
        return AgentResponse(content=response)
```

#### Advanced Integration
```python
from cab.agents.external_agents import CustomScriptAgent
from cab.utils.simulated_user import CABEvaluator

# Create custom agent
agent = CustomScriptAgent('my_ai_script.py', 'MyCustomAgent')

# Test with CAB
evaluator = CABEvaluator()
result = evaluator.evaluate_agent(agent, 'dataset.jsonl')
```

📚 **See [docs/CUSTOM_AGENT_GUIDE.md](docs/CUSTOM_AGENT_GUIDE.md) for detailed examples and best practices.**

## ⚖️ Judge Testing (Step 3)

CAB includes an automated judge that evaluates agent responses:

### **Judge Capabilities**
- **Technical Correctness**: Assesses accuracy and completeness of solutions
- **User Satisfaction**: Evaluates against original user satisfaction conditions
- **Docker Validation**: Verifies solutions work in containerized environments
- **Verbosity Assessment**: Evaluates response clarity and appropriateness

### **Testing the Judge**
```bash
# Test judge functionality
python test_judge.py

# Test full pipeline (Agent + Judge)
python test_full_pipeline.py
```

### **Using the Judge in Your Code**
```python
from cab.core.run import judge_maintainer_answer

# Judge an agent response
judgment, verdict, key_issues, alignment_score = judge_maintainer_answer(
    issue_data, agent_response, docker_results
)

print(f"Verdict: {verdict}")
print(f"Satisfaction Rate: {alignment_score.get('percentage', 0):.1f}%")
```

### **External AI Tools as Judges**
CAB supports using external AI tools as judges:

```python
from cab.judges.judge_agents import create_judge

# Create judge using Amazon Q CLI
judge = create_judge('amazon-q')

# Judge an agent response
judgment, verdict, key_issues, alignment_score = judge.judge_response(
    issue_data, agent_response, docker_results
)

print(f"Amazon Q Verdict: {verdict}")
```

**Available Judge Types:**
- **`amazon-q`**: Amazon Q CLI judge
- **`cursor-cli`**: Cursor CLI judge  
- **`local-llama2`**: Local LLM (Llama2) judge
- **`local-codellama`**: Local LLM (CodeLlama) judge
- **`local-mistral`**: Local LLM (Mistral) judge

#### Custom Agent Tools
```bash
# Test custom agent directly (recommended)
python tests/integration/test_custom_agent.py my_agent.py MyAgent

# Register and test with CLI (advanced)
python cab/utils/register_custom_agent.py register-test my_agent.py MyAgent my-custom

# List all available agents
python cab/utils/register_custom_agent.py list
```

## 🔧 Advanced Usage

### Custom Configuration
Edit `config.yaml` to customize:
- Number of repositories per language
- Issue filtering criteria
- Docker environment settings
- Evaluation parameters

### Web Interface
```bash
# Start web dashboard
python web_app.py

# Open browser to http://localhost:8000
```

### Docker Deployment
```bash
# Run with Docker
docker-compose up

# Or build custom image
docker build -t cab-benchmark .
```

## 📚 Documentation

- **[Pipeline Guide](docs/PIPELINE_GUIDE.md)**: Detailed pipeline documentation
- **[Contributing](CONTRIBUTING.md)**: How to contribute to CAB
- **[API Reference](docs/api.md)**: Programmatic usage

## 🔬 Research Applications

CAB enables researchers to:
- **Compare AI models** objectively on real problems
- **Measure progress** in AI coding capabilities
- **Identify weaknesses** in current approaches
- **Develop better evaluation metrics**

## 📄 Citation

```bibtex
@inproceedings{kim2025codeassistbench,
  title={CodeAssistBench (CAB): Dataset & Benchmarking for Multi-turn Chat-Based Code Assistance}, 
  author={Myeongsoo Kim and Shweta Garg and Baishakhi Ray and Varun Kumar and Anoop Deoras},
  booktitle={Advances in Neural Information Processing Systems (NeurIPS)},
  year={2025},
  track={Datasets and Benchmarks}
}
```

**Paper:** [arXiv:2507.10646](https://arxiv.org/abs/2507.10646) | **Venue:** NeurIPS 2025 Datasets & Benchmarks Track

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📜 License

### Dataset License: CC-BY-NC 4.0
The CAB dataset is released under the Creative Commons Attribution-NonCommercial 4.0 International License (CC-BY-NC 4.0). This applies to the GitHub issues, processed conversations, and benchmark data.

**Important:** This dataset is for research and evaluation purposes only. Commercial use is prohibited. Do not use for training AI models without explicit legal approval.

### Software License: MIT
The open source code in this repository is released under the MIT License.

See [LICENSE](LICENSE) for full details.

## 📚 Dataset Citations

This dataset incorporates data from the following sources:

- **GitHub Issues**: Collected from public repositories under their respective open source licenses
- **Repository Data**: Top-starred repositories across 7 programming languages
- **Conversation Data**: Multi-turn discussions between users and maintainers
- **Solution Data**: Human-verified solutions and satisfaction criteria

All source repositories are properly cited and users must comply with their original licenses.

---

**Made with ❤️ for the AI research community**