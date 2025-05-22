import os
import json
import glob
import datetime
import re
from collections import defaultdict

def extract_repo_info(repo_url):
    """Extract repository owner and name from URL."""
    if not repo_url or "github.com" not in repo_url:
        return None, None
    
    # Clean up the URL
    # Remove trailing issue numbers sometimes present in URLs
    repo_url = re.sub(r'//\d+\$', '', repo_url)
    repo_url = re.sub(r'/issues.*\$', '', repo_url)
    repo_url = repo_url.rstrip('/')
    
    # Extract owner and repo
    match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def find_latest_commit_before_date(repo_url, issue_date):
    """Find the latest commit hash before the issue creation date."""
    # Extract repo owner and name from URL
    owner, repo_name = extract_repo_info(repo_url)
    if not owner or not repo_name:
        return ""
    
    # Convert issue_date to datetime if it's a string
    if isinstance(issue_date, str):
        try:
            issue_date = datetime.datetime.fromisoformat(issue_date.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return ""
    
    # Look for commit file in the directory
    commit_files_dir = "/mnt/efs/people/mysoo/CodeAssistBench/github_commits"
    
    # Try different possible filename patterns
    patterns = [
        f"{commit_files_dir}/commits_github_issues_{owner}{repo_name}_*.json",
        f"{commit_files_dir}/commits_github_issues_{owner}_{repo_name}_*.json",
        f"{commit_files_dir}/commits_{owner}_{repo_name}_*.json"
    ]
    
    matching_files = []
    for pattern in patterns:
        matching_files.extend(glob.glob(pattern))
    
    if not matching_files:
        # Try case-insensitive matching as a fallback
        all_files = glob.glob(f"{commit_files_dir}/*.json")
        owner_lower = owner.lower()
        repo_lower = repo_name.lower()
        for file_path in all_files:
            if owner_lower in file_path.lower() and repo_lower in file_path.lower():
                matching_files.append(file_path)
                break
    
    if not matching_files:
        return ""
    
    # Use the first matching file
    commit_file = matching_files[0]
    
    try:
        with open(commit_file, 'r', encoding='utf-8', errors='replace') as f:
            commit_data = json.load(f)
        
        # Check if commits exist
        if not commit_data or "commits" not in commit_data or not commit_data["commits"]:
            return ""
        
        # Find the latest commit before the issue date
        latest_commit = None
        for commit in commit_data["commits"]:
            if "date" not in commit or not commit["date"]:
                continue
                
            try:
                commit_date = datetime.datetime.fromisoformat(commit["date"].replace('Z', '+00:00'))
                if commit_date <= issue_date:
                    if latest_commit is None or commit_date > datetime.datetime.fromisoformat(latest_commit["date"].replace('Z', '+00:00')):
                        latest_commit = commit
            except (ValueError, TypeError, KeyError):
                continue
        
        return latest_commit["sha"] if latest_commit else ""
    except Exception as e:
        print(f"Error reading commit file {commit_file}: {str(e)}")
        return ""

def process_dockerfile_issue(file_path, language):
    """Process a build_env issue file with Dockerfile."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
        
        repo = data.get("url", "")
        repo = re.sub(r'/issues.*\$', '', repo).rstrip('/')
        created_at = data.get("created_at", "")
        
        # Get commit info
        commit_sha = data.get("git_commit_info", {}).get("sha", "")
        if not commit_sha:
            commit_sha = find_latest_commit_before_date(repo, created_at)
        
        # Extract required fields
        result = {
            "language": language,  # Add language field
            "commit_info": {
                "repository": repo,
                "latest_commit": {
                    "sha": commit_sha
                }
            },
            "first_question": {
                "title": data.get("title", ""),
                "body": data.get("body", "")
            },
            "comments": data.get("comments", []),
            "user_satisfaction_condition": data.get("satisfaction_conditions", []),
            "created_at": created_at,
            "dockerfile": data.get("dockerfile", "")
        }
        return [result]  # Return as a list to be consistent with no_need_docker
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return []

def process_no_docker_issue(file_path, language):
    """Process a no_need_docker issue file which contains an array of issues."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            data_list = json.load(f)
        
        results = []
        # Ensure data_list is always a list
        if not isinstance(data_list, list):
            data_list = [data_list]
            
        # Process each issue in the list
        for data in data_list:
            repo_url = data.get("url", "")
            repo_url = re.sub(r'/issues.*\$', '', repo_url).rstrip('/')
            # Clean up the URL
            repo_url = re.sub(r'//\d+\$', '', repo_url)
            
            created_at = data.get("created_at", "")
            
            # Find latest commit before issue creation date
            commit_sha = find_latest_commit_before_date(repo_url, created_at)
            
            # Extract required fields
            result = {
                "language": language,  # Add language field
                "commit_info": {
                    "repository": repo_url,
                    "latest_commit": {
                        "sha": commit_sha
                    }
                },
                "first_question": {
                    "title": data.get("title", ""),
                    "body": data.get("body", "")
                },
                "comments": data.get("comments", []),
                "user_satisfaction_condition": data.get("satisfaction_conditions", []),
                "created_at": created_at
            }
            results.append(result)
            
        return results
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return []

def generate_dataset():
    """Generate the jsonl file from build_env and no_need_docker directories."""
    base_dir = "/mnt/efs/people/mysoo/CodeAssistBench/issue/all/docker_filter"
    output_file = "/mnt/efs/people/mysoo/CodeAssistBench/dataset_all.jsonl"
    
    # Get all language directories
    lang_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    # For statistics
    total_count = 0
    stats = defaultdict(lambda: {"build_env": 0, "no_need_docker": 0, "total": 0})
    commit_stats = {"with_commit": 0, "without_commit": 0}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Process each language directory
        for lang in lang_dirs:
            print(f"Processing language: {lang}")
            
            # Process build_env files
            build_env_dir = os.path.join(base_dir, lang, "build_env")
            if os.path.exists(build_env_dir):
                build_env_files = glob.glob(os.path.join(build_env_dir, "issue_*.json"))
                for file_path in build_env_files:
                    results = process_dockerfile_issue(file_path, lang)
                    for result in results:
                        f.write(json.dumps(result) + '\n')
                        stats[lang]["build_env"] += 1
                        stats[lang]["total"] += 1
                        total_count += 1
                        
                        # Track commit stats
                        if result["commit_info"]["latest_commit"]["sha"]:
                            commit_stats["with_commit"] += 1
                        else:
                            commit_stats["without_commit"] += 1
            
            # Process no_need_docker files
            no_docker_dir = os.path.join(base_dir, lang, "no_need_docker")
            if os.path.exists(no_docker_dir):
                no_docker_files = glob.glob(os.path.join(no_docker_dir, "github_issues*.json"))
                for file_path in no_docker_files:
                    results = process_no_docker_issue(file_path, lang)
                    for result in results:
                        f.write(json.dumps(result) + '\n')
                        stats[lang]["no_need_docker"] += 1
                        stats[lang]["total"] += 1
                        total_count += 1
                        
                        # Track commit stats
                        if result["commit_info"]["latest_commit"]["sha"]:
                            commit_stats["with_commit"] += 1
                        else:
                            commit_stats["without_commit"] += 1
    
    # Print detailed statistics
    print("\n=== Dataset Generation Statistics ===")
    print(f"Total entries: {total_count}")
    print("\nBreakdown by language:")
    
    # Sort by total count descending for better readability
    sorted_langs = sorted(stats.keys(), key=lambda x: stats[x]["total"], reverse=True)
    
    for lang in sorted_langs:
        print(f"\n{lang}:")
        print(f"  - build_env: {stats[lang]['build_env']} entries")
        print(f"  - no_need_docker: {stats[lang]['no_need_docker']} entries")
        print(f"  - Total: {stats[lang]['total']} entries")
    
    # Calculate category totals
    build_env_total = sum(stats[lang]["build_env"] for lang in stats)
    no_docker_total = sum(stats[lang]["no_need_docker"] for lang in stats)
    
    print("\nCategory totals:")
    print(f"  - build_env: {build_env_total} entries")
    print(f"  - no_need_docker: {no_docker_total} entries")
    print(f"  - Grand total: {total_count} entries")
    
    print("\nCommit information stats:")
    print(f"  - Entries with commit hash: {commit_stats['with_commit']} ({commit_stats['with_commit']/total_count*100:.1f}%)")
    print(f"  - Entries without commit hash: {commit_stats['without_commit']} ({commit_stats['without_commit']/total_count*100:.1f}%)")
    
    print(f"\nGenerated dataset saved to: {output_file}")

if __name__ == "__main__":
    generate_dataset()