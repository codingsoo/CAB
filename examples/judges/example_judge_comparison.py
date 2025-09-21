#!/usr/bin/env python3
"""
Example: Compare different judges (Amazon Q CLI vs Cursor CLI) for agent evaluation.
This demonstrates how to use external AI tools as judges.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_test_scenario() -> Dict[str, Any]:
    """Create a test scenario for judge comparison."""
    return {
        "issue_data": {
            "issue_id": "judge_comparison_001",
            "first_question": {
                "title": "Docker build failing with permission error",
                "body": "I'm trying to build a Docker image but getting a permission error. The error says 'permission denied' when trying to copy files. How can I fix this?"
            },
            "comments": [
                {
                    "user": "maintainer",
                    "body": "This is usually a file permission issue. Can you share your Dockerfile?"
                },
                {
                    "user": "user",
                    "body": "Here's my Dockerfile:\n```dockerfile\nFROM ubuntu:20.04\nCOPY . /app\nWORKDIR /app\nRUN chmod +x script.sh\nCMD [\"./script.sh\"]\n```"
                },
                {
                    "user": "maintainer",
                    "body": "The issue is that you're copying files before setting proper permissions. Try this:\n```dockerfile\nFROM ubuntu:20.04\nWORKDIR /app\nCOPY --chown=root:root . /app\nRUN chmod +x script.sh\nCMD [\"./script.sh\"]\n```"
                },
                {
                    "user": "user",
                    "body": "That worked! Thanks for the help."
                }
            ],
            "user_satisfaction_condition": [
                "The user should understand what caused the permission error",
                "The solution should fix the Docker build issue",
                "The explanation should be clear and include code examples",
                "The user should be able to implement the fix successfully"
            ]
        },
        "agent_response": """
I can help you fix the Docker permission error! This is a common issue when copying files into Docker containers.

**The Problem:**
The permission error occurs because Docker copies files with the same permissions as the host system, and the container might not have the right permissions to execute them.

**The Solution:**
You need to set proper ownership and permissions when copying files. Here's the corrected Dockerfile:

```dockerfile
FROM ubuntu:20.04
WORKDIR /app
COPY --chown=root:root . /app
RUN chmod +x script.sh
CMD ["./script.sh"]
```

**Key Changes:**
1. **`--chown=root:root`**: Sets the owner and group of copied files to root
2. **`WORKDIR /app`**: Sets the working directory before copying
3. **`chmod +x script.sh`**: Makes the script executable

**Alternative Solutions:**
If you still have issues, you can also try:

```dockerfile
FROM ubuntu:20.04
WORKDIR /app
COPY . /app
USER root
RUN chown -R root:root /app && chmod +x script.sh
CMD ["./script.sh"]
```

**Why This Works:**
- The `--chown` flag ensures files are owned by the correct user
- Setting `WORKDIR` first ensures the copy operation works correctly
- The `chmod` command makes the script executable

This should resolve your permission error and allow the Docker build to complete successfully!
""",
        "docker_results": {
            "success": True,
            "logs": "Docker build completed successfully. All tests passed.",
            "test_commands": ["docker build -t test-image .", "docker run test-image"]
        }
    }

def compare_judges():
    """Compare different judges on the same agent response."""
    print("⚖️ Judge Comparison: Amazon Q CLI vs Cursor CLI")
    print("=" * 60)
    
    # Create test scenario
    scenario = create_test_scenario()
    issue_data = scenario["issue_data"]
    agent_response = scenario["agent_response"]
    docker_results = scenario["docker_results"]
    
    print("📝 Test Scenario:")
    print(f"   Issue: {issue_data['first_question']['title']}")
    print(f"   Agent Response Length: {len(agent_response)} characters")
    print(f"   Docker Results: {'Success' if docker_results['success'] else 'Failed'}")
    print(f"   Satisfaction Conditions: {len(issue_data['user_satisfaction_condition'])}")
    
    # Test judges
    judges_to_test = ["amazon-q", "cursor-cli"]
    results = {}
    
    for judge_type in judges_to_test:
        print(f"\n⚖️ Testing {judge_type} Judge")
        print("-" * 40)
        
        try:
            from judge_agents import create_judge
            
            # Create judge
            judge = create_judge(judge_type)
            
            if not judge.setup():
                print(f"❌ {judge_type} setup failed")
                continue
            
            # Get judgment
            judgment, verdict, key_issues, alignment_score = judge.judge_response(
                issue_data, agent_response, docker_results
            )
            
            # Store results
            results[judge_type] = {
                "verdict": verdict,
                "technical_correctness": alignment_score.get("technical_correctness", "UNKNOWN"),
                "satisfaction_rate": alignment_score.get("percentage", 0),
                "key_issues": key_issues,
                "judgment_length": len(judgment)
            }
            
            print(f"✅ {judge_type} evaluation completed")
            print(f"   Verdict: {verdict}")
            print(f"   Technical Correctness: {alignment_score.get('technical_correctness', 'UNKNOWN')}")
            print(f"   Satisfaction Rate: {alignment_score.get('percentage', 0):.1f}%")
            print(f"   Key Issues: {len(key_issues)}")
            
        except Exception as e:
            print(f"❌ Error testing {judge_type}: {e}")
            continue
    
    # Compare results
    print(f"\n📊 Judge Comparison Results")
    print("=" * 50)
    
    if not results:
        print("❌ No judges were able to evaluate the response")
        return
    
    # Create comparison table
    print(f"{'Judge':<15} {'Verdict':<15} {'Tech Correct':<15} {'Satisfaction':<12} {'Issues':<8}")
    print("-" * 80)
    
    for judge_type, result in results.items():
        print(f"{judge_type:<15} {result['verdict']:<15} {result['technical_correctness']:<15} "
              f"{result['satisfaction_rate']:>8.1f}% {len(result['key_issues']):>6}")
    
    # Analysis
    print(f"\n🔍 Analysis:")
    
    # Find consensus
    verdicts = [result["verdict"] for result in results.values()]
    if len(set(verdicts)) == 1:
        print(f"   ✅ Consensus: All judges agree on verdict '{verdicts[0]}'")
    else:
        print(f"   ⚠️ Disagreement: Judges have different verdicts: {set(verdicts)}")
    
    # Find best satisfaction rate
    best_judge = max(results.items(), key=lambda x: x[1]["satisfaction_rate"])
    print(f"   🏆 Highest Satisfaction: {best_judge[0]} ({best_judge[1]['satisfaction_rate']:.1f}%)")
    
    # Find most detailed evaluation
    most_detailed = max(results.items(), key=lambda x: x[1]["judgment_length"])
    print(f"   📝 Most Detailed: {most_detailed[0]} ({most_detailed[1]['judgment_length']} chars)")
    
    # Show key issues from each judge
    print(f"\n🔍 Key Issues by Judge:")
    for judge_type, result in results.items():
        print(f"\n   {judge_type.upper()}:")
        if result["key_issues"]:
            for i, issue in enumerate(result["key_issues"][:3], 1):  # Show first 3
                print(f"     {i}. {issue}")
        else:
            print(f"     No issues identified")

def show_judge_integration_examples():
    """Show examples of integrating judges with the CAB framework."""
    print(f"\n📚 Judge Integration Examples")
    print("=" * 50)
    
    print(f"\n1. 🔄 Using Judges in Agent Evaluation:")
    print(f"   from judge_agents import create_judge")
    print(f"   from simulated_user import CABEvaluator")
    print(f"   ")
    print(f"   # Create custom judge")
    print(f"   judge = create_judge('amazon-q')")
    print(f"   ")
    print(f"   # Evaluate agent with custom judge")
    print(f"   evaluator = CABEvaluator()")
    print(f"   result = evaluator.evaluate_agent_with_judge(")
    print(f"       agent, 'dataset.jsonl', judge")
    print(f"   )")
    
    print(f"\n2. 📊 Multi-Judge Evaluation:")
    print(f"   judges = ['amazon-q', 'cursor-cli']")
    print(f"   all_results = {{}}")
    print(f"   ")
    print(f"   for judge_type in judges:")
    print(f"       judge = create_judge(judge_type)")
    print(f"       if judge.setup():")
    print(f"           result = evaluator.evaluate_agent_with_judge(")
    print(f"               agent, 'dataset.jsonl', judge")
    print(f"           )")
    print(f"           all_results[judge_type] = result")
    
    print(f"\n3. 🎯 Judge Selection Based on Issue Type:")
    print(f"   def select_judge(issue_data):")
    print(f"       if 'docker' in issue_data['first_question']['title'].lower():")
    print(f"           return create_judge('amazon-q')  # Better for Docker issues")
    print(f"       else:")
    print(f"           return create_judge('cursor-cli')  # General purpose")
    
    print(f"\n4. 📈 Judge Performance Comparison:")
    print(f"   # Compare judges across multiple issues")
    print(f"   judge_scores = {{}}")
    print(f"   for issue in issues:")
    print(f"       for judge_type in ['amazon-q', 'cursor-cli']:")
    print(f"           judge = create_judge(judge_type)")
    print(f"           judgment, verdict, issues, score = judge.judge_response(")
    print(f"               issue, agent_response")
    print(f"           )")
    print(f"           if judge_type not in judge_scores:")
    print(f"               judge_scores[judge_type] = []")
    print(f"           judge_scores[judge_type].append(score.get('percentage', 0))")

def main():
    """Main function for judge comparison example."""
    print("⚖️ Judge Comparison Example")
    print("=" * 60)
    print("Comparing Amazon Q CLI vs Cursor CLI as judges")
    
    # Run comparison
    compare_judges()
    
    # Show integration examples
    show_judge_integration_examples()
    
    print(f"\n🎯 Judge Comparison Summary:")
    print(f"   ✅ Multiple judges can evaluate the same response")
    print(f"   ✅ Judges provide different perspectives and insights")
    print(f"   ✅ Comparison helps identify the best judge for specific use cases")
    print(f"   ✅ External AI tools work well as judges")
    print(f"\n🎉 Judge comparison demonstrates the flexibility of CAB!")

if __name__ == "__main__":
    main()
