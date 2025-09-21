"""
Demo Data Generator for CAB
Creates realistic sample data for demonstration purposes.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

def generate_demo_issues(language: str, count: int = 50) -> List[Dict[str, Any]]:
    """Generate realistic demo issues for a programming language"""
    
    # Sample issue templates based on common programming problems
    issue_templates = {
        "python": [
            {
                "title": "TypeError when using pandas DataFrame with mixed types",
                "body": "I'm getting a TypeError when trying to perform operations on a DataFrame with mixed data types. The error occurs when I try to use groupby on a column that contains both strings and numbers.",
                "tags": ["bug", "pandas", "dataframe"]
            },
            {
                "title": "FastAPI dependency injection not working with async functions",
                "body": "I'm having trouble with dependency injection in FastAPI when using async functions. The dependencies are not being resolved correctly and I'm getting None values.",
                "tags": ["question", "fastapi", "async"]
            },
            {
                "title": "Memory leak in long-running Django application",
                "body": "My Django application is experiencing memory leaks after running for several hours. The memory usage keeps increasing even when there's no user activity.",
                "tags": ["bug", "django", "memory"]
            }
        ],
        "javascript": [
            {
                "title": "React component not re-rendering after state update",
                "body": "I have a React component that's not re-rendering when I update the state. The state is being updated correctly but the UI doesn't reflect the changes.",
                "tags": ["bug", "react", "state"]
            },
            {
                "title": "Node.js async/await not working as expected",
                "body": "I'm trying to use async/await in Node.js but the code is not executing in the order I expect. Some operations are running in parallel when they should be sequential.",
                "tags": ["question", "nodejs", "async"]
            },
            {
                "title": "Webpack build failing with module resolution error",
                "body": "My Webpack build is failing with a module resolution error. It can't find a module that definitely exists in the node_modules directory.",
                "tags": ["bug", "webpack", "build"]
            }
        ],
        "typescript": [
            {
                "title": "TypeScript strict mode causing compilation errors",
                "body": "I enabled strict mode in TypeScript and now I'm getting compilation errors for code that was working before. How do I fix these type issues?",
                "tags": ["question", "typescript", "strict"]
            },
            {
                "title": "Generic type constraints not working as expected",
                "body": "I'm trying to use generic type constraints in TypeScript but the compiler is not enforcing them correctly. The types are not being narrowed as expected.",
                "tags": ["bug", "typescript", "generics"]
            }
        ]
    }
    
    # Sample solutions
    solutions = [
        "The issue is caused by incorrect type handling. You need to convert the mixed types to a consistent format before performing operations.",
        "This is a common problem with async dependencies. Make sure you're using the correct dependency injection syntax for async functions.",
        "The memory leak is likely caused by event listeners not being properly cleaned up. Make sure to remove listeners in componentWillUnmount.",
        "The component is not re-rendering because React is not detecting the state change. Make sure you're using setState correctly and not mutating the state directly.",
        "The async/await issue is because you're not awaiting the promises correctly. Make sure all async operations are properly awaited.",
        "The Webpack issue is likely a path resolution problem. Check your webpack configuration and make sure the module paths are correct.",
        "Strict mode in TypeScript enforces stricter type checking. You'll need to add proper type annotations and handle null/undefined cases.",
        "Generic type constraints need to be properly defined. Make sure your constraint types are correctly specified in the generic declaration."
    ]
    
    issues = []
    templates = issue_templates.get(language, issue_templates["python"])
    
    for i in range(count):
        template = random.choice(templates)
        
        # Generate realistic timestamps
        created_at = datetime.now() - timedelta(days=random.randint(1, 365))
        closed_at = created_at + timedelta(days=random.randint(1, 30))
        
        issue = {
            "number": random.randint(1000, 9999),
            "title": template["title"],
            "body": template["body"],
            "created_at": created_at.isoformat() + "Z",
            "closed_at": closed_at.isoformat() + "Z",
            "labels": template["tags"],
            "url": f"https://github.com/demo/{language}-repo/issues/{random.randint(1000, 9999)}",
            "author": f"user{random.randint(1, 100)}",
            "comments": [
                {
                    "user": f"maintainer{random.randint(1, 10)}",
                    "created_at": (created_at + timedelta(hours=random.randint(1, 24))).isoformat() + "Z",
                    "body": random.choice(solutions)
                },
                {
                    "user": f"user{random.randint(1, 100)}",
                    "created_at": (created_at + timedelta(hours=random.randint(25, 48))).isoformat() + "Z",
                    "body": "Thanks! This solution worked perfectly."
                }
            ],
            "satisfaction_conditions": [
                "The solution should resolve the TypeError",
                "The code should work with mixed data types",
                "Performance should not be significantly impacted"
            ],
            "docker_required": random.choice([True, False]),
            "difficulty": random.choice(["easy", "medium", "hard"]),
            "language": language
        }
        
        issues.append(issue)
    
    return issues

def generate_demo_repositories(languages: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Generate demo repository data"""
    
    repo_templates = {
        "python": [
            {"name": "django", "owner": "django", "stars": 75000, "description": "The Web framework for perfectionists with deadlines."},
            {"name": "fastapi", "owner": "tiangolo", "stars": 65000, "description": "Fast, modern web framework for building APIs with Python 3.8+"},
            {"name": "pandas", "owner": "pandas-dev", "stars": 42000, "description": "Flexible and powerful data analysis / manipulation library"},
            {"name": "requests", "owner": "psf", "stars": 52000, "description": "A simple, yet elegant HTTP library."},
            {"name": "numpy", "owner": "numpy", "stars": 25000, "description": "The fundamental package for scientific computing with Python"}
        ],
        "javascript": [
            {"name": "react", "owner": "facebook", "stars": 220000, "description": "A declarative, efficient, and flexible JavaScript library for building user interfaces."},
            {"name": "vue", "owner": "vuejs", "stars": 210000, "description": "Progressive JavaScript framework for building user interfaces."},
            {"name": "express", "owner": "expressjs", "stars": 65000, "description": "Fast, unopinionated, minimalist web framework for node."},
            {"name": "lodash", "owner": "lodash", "stars": 60000, "description": "A modern JavaScript utility library delivering modularity, performance, & extras."},
            {"name": "axios", "owner": "axios", "stars": 110000, "description": "Promise based HTTP client for the browser and node.js"}
        ],
        "typescript": [
            {"name": "typescript", "owner": "microsoft", "stars": 95000, "description": "TypeScript is a superset of JavaScript that compiles to clean JavaScript output."},
            {"name": "angular", "owner": "angular", "stars": 90000, "description": "One framework. Mobile & desktop."},
            {"name": "nestjs", "owner": "nestjs", "stars": 65000, "description": "A progressive Node.js framework for building efficient and scalable server-side applications."},
            {"name": "rxjs", "owner": "reactivex", "stars": 30000, "description": "A reactive programming library for JavaScript."},
            {"name": "vscode", "owner": "microsoft", "stars": 160000, "description": "Visual Studio Code"}
        ]
    }
    
    repositories = {}
    
    for language in languages:
        templates = repo_templates.get(language, repo_templates["python"])
        repos = []
        
        for i, template in enumerate(templates):
            repo = {
                "name": template["name"],
                "owner": template["owner"],
                "full_name": f"{template['owner']}/{template['name']}",
                "stars": template["stars"],
                "description": template["description"],
                "language": language,
                "created_at": (datetime.now() - timedelta(days=random.randint(365, 2000))).isoformat() + "Z",
                "updated_at": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat() + "Z",
                "issues_count": random.randint(50, 500),
                "help_wanted_issues": random.randint(5, 50),
                "question_issues": random.randint(10, 100)
            }
            repos.append(repo)
        
        repositories[language] = repos
    
    return repositories

def create_demo_dataset():
    """Create a complete demo dataset"""
    
    print("🎮 Creating demo dataset...")
    
    # Create demo directories
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)
    
    languages = ["python", "javascript", "typescript"]
    
    # Generate repositories
    repositories = generate_demo_repositories(languages)
    
    with open(demo_dir / "repositories.json", "w") as f:
        json.dump(repositories, f, indent=2)
    
    # Generate issues for each language
    all_issues = []
    
    for language in languages:
        issues = generate_demo_issues(language, 50)
        all_issues.extend(issues)
        
        # Save language-specific issues
        lang_dir = demo_dir / language
        lang_dir.mkdir(exist_ok=True)
        
        with open(lang_dir / f"{language}_issues.json", "w") as f:
            json.dump(issues, f, indent=2)
    
    # Create combined dataset
    with open(demo_dir / "dataset.jsonl", "w") as f:
        for issue in all_issues:
            f.write(json.dumps(issue) + "\n")
    
    # Generate summary statistics
    stats = {
        "total_issues": len(all_issues),
        "total_repositories": sum(len(repos) for repos in repositories.values()),
        "languages": languages,
        "issues_by_language": {lang: len([i for i in all_issues if i["language"] == lang]) for lang in languages},
        "docker_required": len([i for i in all_issues if i["docker_required"]]),
        "difficulty_distribution": {
            "easy": len([i for i in all_issues if i["difficulty"] == "easy"]),
            "medium": len([i for i in all_issues if i["difficulty"] == "medium"]),
            "hard": len([i for i in all_issues if i["difficulty"] == "hard"])
        },
        "created_at": datetime.now().isoformat()
    }
    
    with open(demo_dir / "statistics.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"✅ Demo dataset created with {len(all_issues)} issues across {len(languages)} languages")
    print(f"📁 Demo data saved to: {demo_dir}")
    
    return demo_dir

def main():
    """Main function to generate demo data"""
    demo_dir = create_demo_dataset()
    
    print("\n📊 Demo Dataset Statistics:")
    with open(demo_dir / "statistics.json", "r") as f:
        stats = json.load(f)
    
    for key, value in stats.items():
        if key != "created_at":
            print(f"  {key}: {value}")
    
    print(f"\n🎮 To use the demo data:")
    print(f"  python cab_pipeline.py --demo")
    print(f"  python web_app.py  # Then select demo mode in the web interface")

if __name__ == "__main__":
    main()
