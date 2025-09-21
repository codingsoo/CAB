#!/usr/bin/env python3
"""
Repository Cleanup Script
Organizes the CAB repository into a professional structure.
"""

import os
import shutil
from pathlib import Path

def create_professional_structure():
    """Create a professional repository structure"""
    
    # Define the new structure
    structure = {
        "src/": {
            "pipeline/": [
                "pipeline_core.py",
                "pipeline_steps.py", 
                "pipeline_runner.py"
            ],
            "config/": [
                "cab_config.py",
                "config.yaml"
            ],
            "cli/": [
                "cab_cli.py"
            ],
            "web/": [
                "web_app.py"
            ],
            "data_processing/": [
                "get_github_repo.py",
                "get_github_issue.py",
                "conv_filter.py",
                "msg_filter.py",
                "scon_filter.py",
                "docker_filter.py",
                "generate_dataset.py",
                "get_github_commit.py",
                "generate_dockerfile.py"
            ],
            "evaluation/": [
                "run.py",
                "produce_results.py"
            ],
            "utils/": [
                "demo_data_generator.py"
            ]
        },
        "tests/": [
            "test_pipeline.py"
        ],
        "docs/": [
            "PIPELINE_GUIDE.md",
            "IMPROVEMENT_PLAN.md"
        ],
        "scripts/": [
            "setup.py"
        ],
        "examples/": [],
        "data/": {
            "repo/": [],
            "issue/": [],
            "results/": [],
            "logs/": [],
            "docker/": [],
            "commits/": []
        }
    }
    
    print("🏗️  Creating professional repository structure...")
    
    # Create directories
    for dir_path, contents in structure.items():
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")
        
        if isinstance(contents, dict):
            for subdir, files in contents.items():
                full_path = Path(dir_path) / subdir
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ Created directory: {full_path}")
    
    print("\n📁 Repository structure created successfully!")

def move_files_to_structure():
    """Move files to their proper locations"""
    
    file_moves = {
        # Pipeline files
        "pipeline_core.py": "src/pipeline/",
        "pipeline_steps.py": "src/pipeline/",
        "pipeline_runner.py": "src/pipeline/",
        
        # Config files
        "cab_config.py": "src/config/",
        "config.yaml": "src/config/",
        
        # CLI files
        "cab_cli.py": "src/cli/",
        
        # Web files
        "web_app.py": "src/web/",
        
        # Data processing files
        "get_github_repo.py": "src/data_processing/",
        "get_github_issue.py": "src/data_processing/",
        "conv_filter.py": "src/data_processing/",
        "msg_filter.py": "src/data_processing/",
        "scon_filter.py": "src/data_processing/",
        "docker_filter.py": "src/data_processing/",
        "generate_dataset.py": "src/data_processing/",
        "get_github_commit.py": "src/data_processing/",
        "generate_dockerfile.py": "src/data_processing/",
        
        # Evaluation files
        "run.py": "src/evaluation/",
        "produce_results.py": "src/evaluation/",
        
        # Utils files
        "demo_data_generator.py": "src/utils/",
        
        # Test files
        "test_pipeline.py": "tests/",
        
        # Documentation files
        "PIPELINE_GUIDE.md": "docs/",
        "IMPROVEMENT_PLAN.md": "docs/",
        
        # Script files
        "setup.py": "scripts/",
        
        # Data directories (move existing data)
        "repo/": "data/",
        "issue/": "data/",
    }
    
    print("\n📦 Moving files to proper locations...")
    
    for source, destination in file_moves.items():
        if Path(source).exists():
            dest_path = Path(destination)
            dest_path.mkdir(parents=True, exist_ok=True)
            
            if Path(source).is_file():
                shutil.move(source, dest_path / source)
                print(f"✅ Moved {source} → {destination}")
            elif Path(source).is_dir():
                # Move directory contents
                for item in Path(source).iterdir():
                    shutil.move(str(item), dest_path / item.name)
                # Remove empty source directory
                Path(source).rmdir()
                print(f"✅ Moved {source}/ → {destination}")
        else:
            print(f"⚠️  File not found: {source}")
    
    print("\n📁 Files moved successfully!")

def create_init_files():
    """Create __init__.py files for Python packages"""
    
    init_files = [
        "src/__init__.py",
        "src/pipeline/__init__.py",
        "src/config/__init__.py",
        "src/cli/__init__.py",
        "src/web/__init__.py",
        "src/data_processing/__init__.py",
        "src/evaluation/__init__.py",
        "src/utils/__init__.py",
        "tests/__init__.py"
    ]
    
    print("\n🐍 Creating Python package files...")
    
    for init_file in init_files:
        Path(init_file).touch()
        print(f"✅ Created {init_file}")
    
    print("🐍 Python packages created successfully!")

def remove_duplicate_files():
    """Remove duplicate and unnecessary files"""
    
    files_to_remove = [
        "generate_dataset copy.py",  # Duplicate file
        "README_v2.md",  # Old README version
    ]
    
    print("\n🗑️  Removing duplicate files...")
    
    for file_path in files_to_remove:
        if Path(file_path).exists():
            Path(file_path).unlink()
            print(f"✅ Removed {file_path}")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print("🗑️  Cleanup completed!")

def update_imports():
    """Update import statements in moved files"""
    
    print("\n🔧 Updating import statements...")
    
    # Files that need import updates
    import_updates = {
        "src/pipeline/pipeline_runner.py": {
            "from pipeline_core import": "from ..pipeline.pipeline_core import",
            "from pipeline_steps import": "from ..pipeline.pipeline_steps import",
            "from cab_config import": "from ..config.cab_config import"
        },
        "src/cli/cab_cli.py": {
            "from pipeline_runner import": "from ..pipeline.pipeline_runner import",
            "from cab_config import": "from ..config.cab_config import"
        },
        "src/web/web_app.py": {
            "from cab_config import": "from ..config.cab_config import",
            "from cab_pipeline import": "from ..pipeline.cab_pipeline import"
        }
    }
    
    for file_path, replacements in import_updates.items():
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                content = f.read()
            
            for old_import, new_import in replacements.items():
                content = content.replace(old_import, new_import)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Updated imports in {file_path}")
    
    print("🔧 Import statements updated!")

def create_example_files():
    """Create example files and configurations"""
    
    print("\n📝 Creating example files...")
    
    # Example configuration
    example_config = """# Example configuration for CAB
# Copy this to config.yaml and modify as needed

api:
  github:
    token: "${GITHUB_TOKEN}"
    base_url: "https://api.github.com"
  
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4o"

directories:
  base: "./data"
  issue_data: "${directories.base}/issue"
  results: "${directories.base}/results"
  logs: "${directories.base}/logs"

pipeline:
  max_repos_per_language: 50
  max_issues_per_repo: 25
  max_conversation_rounds: 5
  timeout_seconds: 300
"""
    
    with open("examples/config_example.yaml", "w") as f:
        f.write(example_config)
    
    # Example usage script
    example_usage = """#!/usr/bin/env python3
\"\"\"
Example usage of CAB pipeline
\"\"\"

import asyncio
from src.pipeline.pipeline_runner import CABPipelineRunner

async def main():
    # Create pipeline runner
    runner = CABPipelineRunner()
    
    # Run pipeline for specific languages
    languages = ["python", "javascript"]
    summary = await runner.run_pipeline(languages)
    
    print("Pipeline completed!")
    print(f"Summary: {summary}")

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    with open("examples/run_pipeline_example.py", "w") as f:
        f.write(example_usage)
    
    print("✅ Created example files")
    print("📝 Example files created successfully!")

def main():
    """Main cleanup function"""
    print("🧹 CAB Repository Cleanup")
    print("=" * 40)
    
    # Create professional structure
    create_professional_structure()
    
    # Move files to proper locations
    move_files_to_structure()
    
    # Create Python package files
    create_init_files()
    
    # Remove duplicate files
    remove_duplicate_files()
    
    # Update import statements
    update_imports()
    
    # Create example files
    create_example_files()
    
    print("\n" + "=" * 60)
    print("🎉 Repository cleanup completed successfully!")
    print("=" * 60)
    print("\n📋 What was done:")
    print("✅ Created professional directory structure")
    print("✅ Moved files to appropriate locations")
    print("✅ Created Python package files")
    print("✅ Removed duplicate files")
    print("✅ Updated import statements")
    print("✅ Created example files")
    print("\n🚀 Your repository is now professionally organized!")
    print("\n📁 New structure:")
    print("├── src/           # Source code")
    print("├── tests/         # Test files")
    print("├── docs/          # Documentation")
    print("├── scripts/       # Setup scripts")
    print("├── examples/      # Example usage")
    print("└── data/          # Data directories")

if __name__ == "__main__":
    main()
