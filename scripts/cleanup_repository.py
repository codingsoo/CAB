#!/usr/bin/env python3
"""
Repository Cleanup Script - Clean up unnecessary files and organize structure
"""

import os
import shutil
from pathlib import Path

def print_banner():
    """Print the cleanup banner"""
    print("🧹" + "="*60 + "🧹")
    print("   CAB Repository Cleanup Script")
    print("   Cleaning up unnecessary files and organizing structure")
    print("🧹" + "="*60 + "🧹")

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directory structure...")
    
    directories = [
        "examples",
        "examples/integration", 
        "examples/custom_agents",
        "examples/judges",
        "tests",
        "tests/unit",
        "tests/integration", 
        "tests/examples",
        "docs",
        "scripts",
        "data/raw",
        "data/processed",
        "data/examples"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ Created: {directory}")

def remove_unnecessary_files():
    """Remove unnecessary files"""
    print("\n🗑️ Removing unnecessary files...")
    
    # Temporary test files
    temp_files = [
        "test_step2.py",
        "test_step2_fixed.py", 
        "test_step2_honest.py",
        "run_step2_demo.py",
        "test_separation.py"
    ]
    
    # Log files
    log_files = [
        "maintainer_agent_c.log",
        "pipeline_runner.log",
        "maintainer_agent.log",
        "llm_interactions_c_gpt.log"
    ]
    
    # Duplicate files
    duplicate_files = [
        "generate_dataset copy.py",
        "README_v2.md"
    ]
    
    all_files = temp_files + log_files + duplicate_files
    
    for file_path in all_files:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"   ✅ Removed: {file_path}")
        else:
            print(f"   ⚠️ Not found: {file_path}")

def move_example_files():
    """Move example files to examples directory"""
    print("\n📦 Moving example files...")
    
    example_files = [
        ("example_amazon_q.py", "examples/integration/"),
        ("example_cursor_integration.py", "examples/integration/"),
        ("example_cursor_script.py", "examples/integration/"),
        ("example_custom_agent.py", "examples/custom_agents/"),
        ("example_judge_comparison.py", "examples/judges/"),
        ("amazon_q_integration_example.py", "examples/integration/"),
        ("cursor_integration_example.py", "examples/integration/")
    ]
    
    for source, destination in example_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_test_files():
    """Move test files to tests directory"""
    print("\n🧪 Moving test files...")
    
    test_files = [
        ("test_agent.py", "tests/integration/"),
        ("test_custom_agent.py", "tests/integration/"),
        ("test_external_agents.py", "tests/integration/"),
        ("test_full_pipeline.py", "tests/integration/"),
        ("test_judge_agents.py", "tests/integration/"),
        ("test_judge.py", "tests/integration/"),
        ("test_pipeline.py", "tests/unit/")
    ]
    
    for source, destination in test_files:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_documentation_files():
    """Move documentation files to docs directory"""
    print("\n📚 Moving documentation files...")
    
    doc_files = [
        "CUSTOM_AGENT_GUIDE.md",
        "CUSTOM_AGENT_SUMMARY.md", 
        "DATASET_CARD.md",
        "EASE_OF_USE_SUMMARY.md",
        "EXTERNAL_JUDGES_SUMMARY.md",
        "IMPROVEMENT_PLAN.md",
        "JUDGE_TESTING_SUMMARY.md",
        "PIPELINE_GUIDE.md",
        "SUPER_EASY_START.md",
        "REPOSITORY_CLEANUP_ANALYSIS.md"
    ]
    
    for source in doc_files:
        if os.path.exists(source):
            dest_path = Path("docs") / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_script_files():
    """Move utility scripts to scripts directory"""
    print("\n🔧 Moving utility scripts...")
    
    script_files = [
        "super_easy_setup.py",
        "try_cab.py",
        "cleanup_repo.py",
        "demo_data_generator.py"
    ]
    
    for source in script_files:
        if os.path.exists(source):
            dest_path = Path("scripts") / source
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def move_data_files():
    """Move data files to data directory"""
    print("\n📊 Moving data files...")
    
    data_dirs = [
        ("demo_data", "data/examples/"),
        ("issue", "data/raw/"),
        ("repo", "data/raw/")
    ]
    
    for source, destination in data_dirs:
        if os.path.exists(source):
            dest_path = Path(destination) / source
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.move(source, dest_path)
            print(f"   ✅ Moved: {source} → {dest_path}")
        else:
            print(f"   ⚠️ Not found: {source}")

def create_init_files():
    """Create __init__.py files for Python packages"""
    print("\n🐍 Creating __init__.py files...")
    
    init_dirs = [
        "examples",
        "examples/integration",
        "examples/custom_agents", 
        "examples/judges",
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/examples"
    ]
    
    for directory in init_dirs:
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Package initialization\n")
            print(f"   ✅ Created: {init_file}")
        else:
            print(f"   ⚠️ Already exists: {init_file}")

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

def show_cleanup_summary():
    """Show cleanup summary"""
    print("\n🎉 Cleanup Summary:")
    print("="*50)
    
    print("✅ Removed unnecessary files:")
    print("   • Temporary test files")
    print("   • Log files") 
    print("   • Duplicate files")
    
    print("\n✅ Organized files into directories:")
    print("   • examples/ - Example files")
    print("   • tests/ - Test files")
    print("   • docs/ - Documentation files")
    print("   • scripts/ - Utility scripts")
    print("   • data/ - Data files")
    
    print("\n✅ Created proper structure:")
    print("   • Clear separation of concerns")
    print("   • Professional organization")
    print("   • Easy to navigate")
    
    print("\n📚 Next Steps:")
    print("   1. Update import statements in moved files")
    print("   2. Update documentation references")
    print("   3. Test that everything still works")
    print("   4. Consider creating a proper Python package")

def main():
    """Main cleanup function"""
    print_banner()
    
    # Create directories
    create_directories()
    
    # Remove unnecessary files
    remove_unnecessary_files()
    
    # Move files to appropriate directories
    move_example_files()
    move_test_files()
    move_documentation_files()
    move_script_files()
    move_data_files()
    
    # Create __init__.py files
    create_init_files()
    
    # Show final structure
    show_final_structure()
    
    # Show summary
    show_cleanup_summary()

if __name__ == "__main__":
    main()
