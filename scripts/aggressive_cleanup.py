#!/usr/bin/env python3
"""
Aggressive Repository Cleanup Script - Create proper Python package structure
"""

import os
import shutil
from pathlib import Path

def print_banner():
    """Print the aggressive cleanup banner"""
    print("🚀" + "="*60 + "🚀")
    print("   CAB Aggressive Repository Cleanup")
    print("   Creating proper Python package structure")
    print("🚀" + "="*60 + "🚀")

def create_package_structure():
    """Create the cab package structure"""
    print("\n📁 Creating CAB package structure...")
    
    package_dirs = [
        "cab",
        "cab/core",
        "cab/agents", 
        "cab/judges",
        "cab/filters",
        "cab/data",
        "cab/utils"
    ]
    
    for directory in package_dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ Created: {directory}")

def move_core_files():
    """Move core functionality files"""
    print("\n🔧 Moving core functionality files...")
    
    core_files = [
        ("pipeline_runner.py", "cab/core/"),
        ("pipeline_core.py", "cab/core/"),
        ("pipeline_steps.py", "cab/core/"),
        ("cab_config.py", "cab/core/"),
        ("run.py", "cab/core/"),
        ("cab_pipeline.py", "cab/core/")
    ]
    
    for source, destination in core_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_agent_files():
    """Move agent-related files"""
    print("\n🤖 Moving agent files...")
    
    agent_files = [
        ("agent_interface.py", "cab/agents/"),
        ("external_agents.py", "cab/agents/")
    ]
    
    for source, destination in agent_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_judge_files():
    """Move judge-related files"""
    print("\n⚖️ Moving judge files...")
    
    judge_files = [
        ("judge_agents.py", "cab/judges/")
    ]
    
    for source, destination in judge_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_filter_files():
    """Move filter files"""
    print("\n🔍 Moving filter files...")
    
    filter_files = [
        ("conv_filter.py", "cab/filters/"),
        ("msg_filter.py", "cab/filters/"),
        ("scon_filter.py", "cab/filters/"),
        ("docker_filter.py", "cab/filters/")
    ]
    
    for source, destination in filter_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_data_files():
    """Move data processing files"""
    print("\n📊 Moving data processing files...")
    
    data_files = [
        ("generate_dataset.py", "cab/data/"),
        ("generate_dockerfile.py", "cab/data/"),
        ("get_github_commit.py", "cab/data/"),
        ("get_github_issue.py", "cab/data/"),
        ("get_github_repo.py", "cab/data/"),
        ("convert_dataset.py", "cab/data/"),
        ("produce_results.py", "cab/data/")
    ]
    
    for source, destination in data_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_utility_files():
    """Move utility files"""
    print("\n🛠️ Moving utility files...")
    
    utility_files = [
        ("register_custom_agent.py", "cab/utils/"),
        ("simulated_user.py", "cab/utils/")
    ]
    
    for source, destination in utility_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_remaining_files():
    """Move remaining files to appropriate locations"""
    print("\n📦 Moving remaining files...")
    
    remaining_files = [
        ("cleanup_repository.py", "scripts/"),
        ("REPOSITORY_CLEANUP_ANALYSIS.md", "docs/"),
        ("AGGRESSIVE_CLEANUP_PLAN.md", "docs/")
    ]
    
    for source, destination in remaining_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def create_init_files():
    """Create __init__.py files for all packages"""
    print("\n🐍 Creating __init__.py files...")
    
    init_dirs = [
        "cab",
        "cab/core",
        "cab/agents",
        "cab/judges", 
        "cab/filters",
        "cab/data",
        "cab/utils"
    ]
    
    for directory in init_dirs:
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# CAB Package\n")
            print(f"   ✅ Created: {init_file}")
        else:
            print(f"   ⚠️ Already exists: {init_file}")

def create_main_init():
    """Create main cab/__init__.py with key exports"""
    print("\n📦 Creating main package __init__.py...")
    
    main_init_content = '''"""
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
'''
    
    main_init_file = Path("cab/__init__.py")
    main_init_file.write_text(main_init_content)
    print(f"   ✅ Created: {main_init_file}")

def show_final_structure():
    """Show the final directory structure"""
    print("\n📁 Final Directory Structure:")
    print("="*50)
    
    def print_tree(directory, prefix="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return
            
        try:
            items = sorted(Path(directory).iterdir())
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                print(f"{prefix}{current_prefix}{item.name}")
                
                if item.is_dir() and current_depth < max_depth - 1:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    print_tree(item, next_prefix, max_depth, current_depth + 1)
        except PermissionError:
            pass
    
    print_tree(".", max_depth=3)

def show_root_files():
    """Show files remaining in root directory"""
    print("\n📄 Files in Root Directory:")
    print("="*30)
    
    root_files = []
    for item in Path(".").iterdir():
        if item.is_file() and not item.name.startswith("."):
            root_files.append(item.name)
    
    root_files.sort()
    for file in root_files:
        print(f"   📄 {file}")
    
    print(f"\n📊 Total files in root: {len(root_files)}")

def show_cleanup_summary():
    """Show cleanup summary"""
    print("\n🎉 Aggressive Cleanup Summary:")
    print("="*50)
    
    print("✅ Created proper Python package structure:")
    print("   • cab/ - Main package")
    print("   • cab/core/ - Core functionality")
    print("   • cab/agents/ - Agent implementations")
    print("   • cab/judges/ - Judge implementations")
    print("   • cab/filters/ - Data filtering")
    print("   • cab/data/ - Data processing")
    print("   • cab/utils/ - Utilities")
    
    print("\n✅ Moved all Python files into package:")
    print("   • Core functionality → cab/core/")
    print("   • Agents → cab/agents/")
    print("   • Judges → cab/judges/")
    print("   • Filters → cab/filters/")
    print("   • Data processing → cab/data/")
    print("   • Utilities → cab/utils/")
    
    print("\n✅ Created proper package initialization:")
    print("   • __init__.py files for all packages")
    print("   • Main package exports")
    print("   • Version and metadata")
    
    print("\n📚 Next Steps:")
    print("   1. Update import statements in all files")
    print("   2. Update documentation with new structure")
    print("   3. Test that everything still works")
    print("   4. Update setup.py for new package structure")
    print("   5. Create proper package distribution")

def main():
    """Main aggressive cleanup function"""
    print_banner()
    
    # Create package structure
    create_package_structure()
    
    # Move files to appropriate locations
    move_core_files()
    move_agent_files()
    move_judge_files()
    move_filter_files()
    move_data_files()
    move_utility_files()
    move_remaining_files()
    
    # Create __init__.py files
    create_init_files()
    create_main_init()
    
    # Show results
    show_final_structure()
    show_root_files()
    show_cleanup_summary()

if __name__ == "__main__":
    main()
