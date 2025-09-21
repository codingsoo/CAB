"""
Setup script for CAB (CodeAssistBench)
Provides easy installation and configuration for the project.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import shutil

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_docker():
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is installed")
            
            # Check if Docker daemon is running
            result = subprocess.run(["docker", "info"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker daemon is running")
                return True
            else:
                print("⚠️  Docker is installed but daemon is not running")
                print("   Please start Docker Desktop or Docker daemon")
                return False
        else:
            print("❌ Docker is not installed")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed")
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Upgrade pip first
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing requirements"):
        return False
    
    # Install additional dependencies for web interface
    web_deps = [
        "fastapi",
        "uvicorn[standard]",
        "python-multipart",
        "jinja2",
        "pyyaml"
    ]
    
    for dep in web_deps:
        if not run_command(f"{sys.executable} -m pip install {dep}", f"Installing {dep}"):
            return False
    
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        "data",
        "data/repo",
        "data/issue", 
        "data/results",
        "data/logs",
        "data/docker",
        "data/commits"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True

def create_env_template():
    """Create .env template file"""
    print("🔧 Creating environment configuration template...")
    
    env_template = """# CAB Environment Configuration
# Copy this file to .env and fill in your API keys

# GitHub API Token (required)
# Get one at: https://github.com/settings/tokens
GITHUB_TOKEN=your_github_token_here

# OpenAI API Key (required for some features)
# Get one at: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# AWS Configuration (optional, for Bedrock)
# Configure with: aws configure
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-2

# Optional: Custom configuration
# CAB_LOG_LEVEL=INFO
# CAB_MAX_REPOS=100
"""
    
    env_file = Path(".env.template")
    with open(env_file, "w") as f:
        f.write(env_template)
    
    print("✅ Created .env.template file")
    print("📝 Please copy .env.template to .env and fill in your API keys")
    
    return True

def create_docker_compose():
    """Create Docker Compose file for easy deployment"""
    print("🐳 Creating Docker Compose configuration...")
    
    docker_compose = """version: '3.8'

services:
  cab-web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)
    
    print("✅ Created docker-compose.yml")
    
    return True

def create_dockerfile():
    """Create Dockerfile for containerized deployment"""
    print("🐳 Creating Dockerfile...")
    
    dockerfile = """FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional web dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart jinja2 pyyaml

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/repo data/issue data/results data/logs data/docker data/commits

# Expose port
EXPOSE 8000

# Run the web application
CMD ["python", "web_app.py"]
"""
    
    with open("Dockerfile", "w") as f:
        f.write(dockerfile)
    
    print("✅ Created Dockerfile")
    
    return True

def run_tests():
    """Run basic tests to verify installation"""
    print("🧪 Running basic tests...")
    
    try:
        # Test imports
        import cab_config
        import pipeline_core
        print("✅ Core modules import successfully")
        
        # Test configuration loading
        config = cab_config.get_config()
        print("✅ Configuration loads successfully")
        
        # Test pipeline initialization
        from pipeline_runner import CABPipelineRunner
        runner = CABPipelineRunner()
        print("✅ Pipeline initializes successfully")
        
        return True
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 CAB Setup Complete!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("1. Copy .env.template to .env and add your API keys:")
    print("   cp .env.template .env")
    print("   # Edit .env with your actual API keys")
    print("\n2. Start the web interface:")
    print("   python web_app.py")
    print("\n3. Open your browser to:")
    print("   http://localhost:8000")
    print("\n4. Or run the pipeline directly:")
    print("   python cab_cli.py --demo  # Demo mode")
    print("   python cab_cli.py --languages python javascript  # Full mode")
    print("\n🐳 Docker Option:")
    print("   docker-compose up  # Run with Docker")
    print("\n📚 Documentation:")
    print("   - Web Interface: http://localhost:8000/docs")
    print("   - README.md for detailed instructions")
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("🚀 CAB (CodeAssistBench) Setup")
    print("="*40)
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    # Check Docker (optional but recommended)
    docker_available = check_docker()
    if not docker_available:
        print("⚠️  Docker is recommended but not required for basic usage")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        print("❌ Failed to create directories")
        sys.exit(1)
    
    # Create configuration files
    create_env_template()
    create_docker_compose()
    create_dockerfile()
    
    # Run tests
    if not run_tests():
        print("❌ Setup tests failed")
        sys.exit(1)
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()