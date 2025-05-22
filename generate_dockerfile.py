import os
import json
import boto3
import time
import datetime
import subprocess
import tempfile
import shutil
import concurrent.futures
import yaml  # For parsing YAML workflow files
import logging
from botocore.config import Config

LANG = "python"

# Define paths
input_dir = f"/mnt/efs/people/mysoo/CodeAssistBench/issue/all/docker_filter/{LANG}/need_docker"
output_dir = f"/mnt/efs/people/mysoo/CodeAssistBench/issue/all/docker_filter/{LANG}/build_env"
github_commits_dir = "/mnt/efs/people/mysoo/CodeAssistBench/github_commits"

# Define the directory where failure logs should be stored
failure_logs_dir = f"/mnt/efs/people/mysoo/CodeAssistBench/issue/all/docker_filter/{LANG}/build_env/issue_build_failure_logs"
# Create the directory if it doesn't exist
os.makedirs(failure_logs_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Counter for LLM API calls
LLM_CALL_COUNT = 0

def setup_logging():
    """Set up logging with rotation based on time and size"""
    # Create log directory if it doesn't exist
    log_dir = f"/mnt/efs/people/mysoo/CodeAssistBench/issue/all/docker_filter/{LANG}/build_env/llm_logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a new log file with timestamp
    log_filename = f"llm_interactions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    # Configure logging
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Log the start of the session
    logging.info(f"=== Starting new session with Claude 3.7 Sonnet model ===")
    print(f"Logging LLM interactions to {log_path}")
    
    return log_path

def log_llm_interaction(model_id, prompt, response_body, call_context=""):
    """
    Log the LLM interaction details including prompt and raw response
    
    Args:
        model_id: The ID of the model used
        prompt: The prompt sent to the model
        response_body: The raw response from the model
        call_context: Additional context about where this call was made from
    """
    logging.info(f"===== LLM INTERACTION {LLM_CALL_COUNT} =====")
    logging.info(f"Context: {call_context}")
    logging.info(f"Model: {model_id}")
    logging.info("--- PROMPT ---")
    logging.info(prompt)
    logging.info("--- RAW RESPONSE ---")
    logging.info(json.dumps(response_body, indent=2))
    logging.info("===========================================\n")

def call_llm_with_adaptive_context(bedrock_client, model_id, system_prompt, user_prompt, 
                                  readme_content, repo_structure_text, workflows_text, reference_dockerfile_text,
                                  max_retries=5):
    """
    Call LLM with adaptive context reduction when hitting context window errors
    """
    # Start with your original content sizes
    readme_length = 10000  # Start with your default size
    structure_length = 5000
    workflow_files_max = 2
    
    for attempt in range(max_retries):
        try:
            # Prepare the content with current sizes
            truncated_readme = truncate_text(readme_content, readme_length) if readme_content else ""
            readme_text = f"\nRepository README:\n{truncated_readme}\n\n" if truncated_readme else ""
            
            # Truncate structure text
            truncated_structure = truncate_text(repo_structure_text, structure_length) if repo_structure_text else ""
            structure_text = f"\nRepository Structure:\n```\n{truncated_structure}\n```\n" if truncated_structure else ""
            
            # Limit workflow files based on current setting
            limited_workflows_text = ""
            if workflows_text:
                # Extract workflow files (assuming workflows_text already contains the workflow files)
                # This is a simplified approach - you may need to adjust based on your actual data structure
                workflow_parts = workflows_text.split("Workflow file: ")
                if len(workflow_parts) > 1:
                    limited_workflows_text = "\nGitHub Workflow files found in repository:\n"
                    # Take first part plus up to workflow_files_max additional parts
                    for part in workflow_parts[:workflow_files_max+1]:
                        if "```yaml" in part:
                            # Truncate the yaml content
                            before_yaml = part.split("```yaml")[0]
                            yaml_content = part.split("```yaml")[1].split("```")[0]
                            after_yaml = part.split("```", 2)[2] if len(part.split("```")) > 2 else ""
                            
                            truncated_yaml = truncate_text(yaml_content, 2000)
                            limited_workflows_text += f"Workflow file: {before_yaml}```yaml{truncated_yaml}```{after_yaml}"
                        else:
                            limited_workflows_text += part
            
            # Combine all for the final prompt
            full_prompt = user_prompt + readme_text + structure_text + limited_workflows_text + reference_dockerfile_text
            
            # Log attempt details
            print(f"LLM call attempt {attempt+1}/{max_retries} - README size: {readme_length}, Structure size: {structure_length}, Workflows: {workflow_files_max}")
            
            # Call Claude 3.7 Sonnet
            response_text = call_sonnet_37(
                prompt=full_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=15000
            )
            
            # Create a response body similar to what we'd get from DeepSeek for logging compatibility
            response_body = {
                "content": [{"text": response_text}]
            }
            
            # Log the interaction
            log_llm_interaction(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                prompt=f"SYSTEM:\n{system_prompt}\n\nUSER:\n{full_prompt}",
                response_body=response_body,
                call_context=f"adaptive_context_call (attempt #{attempt+1})"
            )
            
            # Return the successful response in a format compatible with the rest of the code
            return {
                "choices": [{"message": {"content": response_text}}]
            }
            
        except Exception as e:
            error_str = str(e)
            print(f"Error in LLM call (attempt {attempt+1}): {error_str}")
            
            # Check if it's a context window error
            if "context" in error_str.lower() and "window" in error_str.lower() or "token" in error_str.lower():
                # Reduce context sizes for next attempt
                readme_length = int(readme_length * 0.7)  # Reduce by 30%
                structure_length = int(structure_length * 0.7)
                if workflow_files_max > 0:
                    workflow_files_max -= 1
                    
                print(f"Reducing context for next attempt - README: {readme_length}, Structure: {structure_length}, Workflows: {workflow_files_max}")
                
                # Ensure we don't go too low
                if readme_length < 1000:
                    readme_length = 1000
                if structure_length < 1000:
                    structure_length = 1000
            else:
                # If it's not a context window error, just raise it
                raise
    
    # If we get here, we've exhausted all retries
    raise Exception(f"Failed to call LLM after {max_retries} attempts with progressively reduced context")

def generate_failure_explanation(error_message):
    """Generate one sentence explanation for Docker build failure"""
    # Truncate error message if too long
    truncated_error = truncate_text(error_message, 3000)
    
    # System prompt
    system_prompt = 'Provide clear, concise explanations about Docker build failures.'
    
    # User prompt
    user_prompt = f"""
    The following is an error message from a failed Docker image build:
    
    ```
    {truncated_error}
    ```
    
    Please provide a clear, concise one-sentence explanation of why the Docker build failed.
    Your response should be ONLY the single sentence explanation with no additional text.
    """
    
    try:
        # Call Claude 3.7 Sonnet
        explanation = call_sonnet_37(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.0,
            max_tokens=1000
        )
        
        # Create a response body similar to what we'd get from DeepSeek for logging
        response_body = {
            "content": [{"text": explanation}]
        }
        
        # Log the interaction
        log_llm_interaction(
            model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            prompt=f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}",
            response_body=response_body,
            call_context="generate_failure_explanation"
        )
        
        # Ensure it's just one sentence (take the first sentence if multiple)
        if "." in explanation:
            explanation = explanation.split(".", 1)[0] + "."
            
        return explanation
    except Exception as e:
        print(f"Error generating explanation: {str(e)}")
        logging.error(f"Error in generate_failure_explanation: {str(e)}")
        return "Docker build failed due to an unspecified error."

def truncate_text(text, max_length=3000):
    """Truncate text to a maximum length, adding indicator if truncated"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length//2] + "\n...[truncated]...\n" + text[-max_length//2:]


def parse_github_workflow(workflow_content):
    """Extract useful information from GitHub workflow file"""
    try:
        # Parse YAML content
        workflow_data = yaml.safe_load(workflow_content)
        
        info = {
            "name": workflow_data.get("name", "Unnamed workflow"),
            "jobs": [],
            "build_steps": [],
            "dependencies": []
        }
        
        # Extract job information
        for job_name, job_config in workflow_data.get("jobs", {}).items():
            job_info = {
                "name": job_name,
                "runs-on": job_config.get("runs-on", ""),
                "steps": []
            }
            
            # Extract steps
            for step in job_config.get("steps", []):
                job_info["steps"].append({
                    "name": step.get("name", ""),
                    "uses": step.get("uses", ""),
                    "run": step.get("run", "")
                })
                
                # Collect build steps specifically (useful for Dockerfile generation)
                if step.get("run") and any(keyword in step.get("run", "").lower() 
                                         for keyword in ["build", "install", "compile", "dotnet", "msbuild", "npm", "mvn"]):
                    info["build_steps"].append(step.get("run"))
                    
                # Extract dependency information
                if step.get("uses") and any(keyword in step.get("uses", "").lower() 
                                         for keyword in ["setup-dotnet", "setup-node", "setup-java", "setup-python"]):
                    info["dependencies"].append(step.get("uses"))
                    
            info["jobs"].append(job_info)
            
        return info
    except Exception as e:
        print(f"Error parsing workflow: {str(e)}")
        return None

def generate_dockerfile_candidates(issue_data, num_candidates=5, error_message=None, reference_dockerfile=None):
    """Generate multiple Dockerfile candidates in parallel"""
    global LLM_CALL_COUNT
    
    # Get repository information
    repo_url = issue_data.get("url", "").split("/issues/")[0] if "/issues/" in issue_data.get("url", "") else ""
    issue_title = issue_data.get("title", "")
    issue_body = truncate_text(issue_data.get("body", ""), 3000)
    issue_number = issue_data.get("number", "unknown")
    commit_sha = issue_data.get("git_commit_info", {}).get("sha", "")
    
    # Add README if available (truncate if too long)
    readme_content = issue_data.get("repository_info", {}).get("readme", "")
    
    # Add repository structure if available
    repo_structure_text = ""
    if issue_data.get("repository_info", {}).get("structure_summary"):
        repo_structure_text = issue_data['repository_info']['structure_summary']
    
    # Add reference Dockerfile if available
    reference_dockerfile_text = ""
    if reference_dockerfile:
        reference_dockerfile_text = f"\nReference Dockerfile from another successful issue in this repository:\n{reference_dockerfile}\n\n"
    # If no reference but there's a repo Dockerfile, use that
    elif issue_data.get("repository_info", {}).get("dockerfile", ""):
        original_dockerfile = issue_data.get("repository_info", {}).get("dockerfile", "")
        reference_dockerfile_text = f"\nOriginal Dockerfile from repository:\n{original_dockerfile}\n\n"
    
    # Add GitHub workflow files if available (provide raw files)
    workflows_text = ""
    if issue_data.get("repository_info", {}).get("github_workflows"):
        workflows = issue_data.get("repository_info", {}).get("github_workflows", {})
        if workflows:
            # Include up to 2 workflow files to avoid overly large prompts
            workflow_files = list(workflows.items())[:2]
            
            workflows_text = "\nGitHub Workflow files found in repository:\n"
            for name, content in workflow_files:
                # Truncate each workflow file if too long
                truncated_content = truncate_text(content, 4000)
                workflows_text += f"\nWorkflow file: {name}\n```yaml\n{truncated_content}\n```\n"
    
    # Create a system prompt
    system_prompt = "You are an expert Docker engineer who creates Dockerfiles to build and validate GitHub projects."
    
    # Create a prompt based on whether we're generating a new Dockerfile or fixing an existing one
    if error_message:
        # Get existing Dockerfile
        existing_dockerfile = issue_data.get("dockerfile", "")
        
        prompt = f"""
        I need to fix a Dockerfile that failed to build for this GitHub issue. Please help me correct the errors.
        
        Repository URL: {repo_url}
        Issue Number: {issue_number}
        Issue Title: {issue_title}
        Reference Commit SHA: {commit_sha}
        
        Here's the current Dockerfile:
        ```
        {existing_dockerfile}
        ```
        
        The Docker build failed with the following error:
        ```
        {truncate_text(error_message, 3000)}
        ```
        
        Please provide an improved version of the Dockerfile that fixes these errors.
        Make sure it:
        1. Sets up the appropriate environment to build and validate the solution for this issue
        2. Installs all necessary dependencies
        3. Clones the repository and checks out commit {commit_sha} if the author did not specifically mention the version or commit hash
        4. Builds the project
        5. Do not need to run anything but have all dependencies and build the project the user need
        6. Do not have option flags when you build the project unless the user asked to do so or the project mentioned to have them
        
        IMPORTANT: Your response should ONLY contain the Dockerfile content itself, with no additional text, markdown formatting, or code blocks. Just the plain Dockerfile content that I can use directly.
        """
    else:
        prompt = f"""
        I need to create a Dockerfile to validate the solution to this GitHub issue.
        
        Repository URL: {repo_url}
        Issue Number: {issue_number}
        Issue Title: {issue_title}
        Commit SHA: {commit_sha}
        
        Issue Description:
        {issue_body}
        
        Please create a detailed Dockerfile that:
        1. Sets up the appropriate environment to build and validate the solution for this issue
        2. Installs all necessary dependencies
        3. Clones the repository and checks out the specific commit {commit_sha} if the author did not specifically mention the version or commit hash.
        4. Builds the project
        5. Do not need to run anything but have all dependencies and build the project the the user need.
        6. Do not have option flags when you build the project unless the user asked to do so or the project mentioned to have them
        
        The Dockerfile should be complete and ready to use. Please include comments to explain each step.
        
        IMPORTANT: Your response should ONLY contain the Dockerfile content itself, with no additional text, markdown formatting, or code blocks. Just the plain Dockerfile content that I can use directly.
        """
    
    # Function to generate a single candidate with adaptive context handling
    def generate_candidate(candidate_num):
        global LLM_CALL_COUNT  # Use global instead of nonlocal
        try:
            print(f"LLM API Call #{LLM_CALL_COUNT+1}: Generating candidate #{candidate_num}")
            
            # Use adaptive context handling
            response_body = call_llm_with_adaptive_context(
                None,  # No bedrock client needed for call_sonnet_37
                "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                system_prompt,
                prompt,
                readme_content,
                repo_structure_text,
                workflows_text,
                reference_dockerfile_text
            )
            
            dockerfile_content = response_body["choices"][0]["message"]["content"]
            
            # Clean up the response
            # First, try to extract content from code blocks if present
            if "```dockerfile" in dockerfile_content and "```" in dockerfile_content.split("```dockerfile", 1)[1]:
                dockerfile_content = dockerfile_content.split("```dockerfile", 1)[1].split("```", 1)[0].strip()
            elif "```Dockerfile" in dockerfile_content and "```" in dockerfile_content.split("```Dockerfile", 1)[1]:
                dockerfile_content = dockerfile_content.split("```Dockerfile", 1)[1].split("```", 1)[0].strip()
            elif "```" in dockerfile_content and "```" in dockerfile_content.split("```", 1)[1]:
                dockerfile_content = dockerfile_content.split("```", 1)[1].split("```", 1)[0].strip()
            
            # Remove any explanations before/after the actual Dockerfile content
            lines = dockerfile_content.split('\n')
            cleaned_lines = []
            in_dockerfile = False
            
            for line in lines:
                # Start capturing at the FROM instruction
                if line.strip().startswith("FROM "):
                    in_dockerfile = True
                    
                if in_dockerfile:
                    cleaned_lines.append(line)
                    
            # If we found a FROM directive, use the cleaned content
            if in_dockerfile:
                dockerfile_content = '\n'.join(cleaned_lines)
                
            return dockerfile_content
        except Exception as e:
            print(f"  Error generating Dockerfile candidate #{candidate_num}: {str(e)}")
            return None

    # Generate candidates concurrently
    candidates = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(num_candidates, 5)) as executor:
        future_to_candidate = {
            executor.submit(generate_candidate, i + 1): i + 1
            for i in range(num_candidates)
        }
        
        for future in concurrent.futures.as_completed(future_to_candidate):
            candidate_num = future_to_candidate[future]
            try:
                dockerfile_content = future.result()
                if dockerfile_content and dockerfile_content.strip():
                    candidates.append({
                        "dockerfile": dockerfile_content,
                        "candidate_number": candidate_num
                    })
                    print(f"  Successfully generated candidate #{candidate_num}")
                else:
                    print(f"  Failed to generate valid content for candidate #{candidate_num}")
            except Exception as e:
                print(f"  Error processing candidate #{candidate_num}: {str(e)}")
                
    return candidates

def improve_dockerfile_candidate(issue_data, candidate, error, attempt_number, improvement_attempt, reference_dockerfile=None):
    """Improve a specific Dockerfile candidate based on its error"""
    global LLM_CALL_COUNT
    
    # Get repository information
    repo_url = issue_data.get("url", "").split("/issues/")[0] if "/issues/" in issue_data.get("url", "") else ""
    issue_title = issue_data.get("title", "")
    issue_body = truncate_text(issue_data.get("body", ""), 3000)
    issue_number = issue_data.get("number", "unknown")
    commit_sha = issue_data.get("git_commit_info", {}).get("sha", "")
    
    # Add README if available (truncate if too long)
    readme_content = issue_data.get("repository_info", {}).get("readme", "")
    
    # Add repository structure if available
    repo_structure_text = ""
    if issue_data.get("repository_info", {}).get("structure_summary"):
        repo_structure_text = issue_data['repository_info']['structure_summary']
    
    # Add reference Dockerfile if available
    reference_dockerfile_text = ""
    if reference_dockerfile:
        reference_dockerfile_text = f"\nReference Dockerfile from another successful issue in this repository:\n{reference_dockerfile}\n\n"
    # If no reference but there's a repo Dockerfile, use that
    elif issue_data.get("repository_info", {}).get("dockerfile", ""):
        original_dockerfile = issue_data.get("repository_info", {}).get("dockerfile", "")
        reference_dockerfile_text = f"\nOriginal Dockerfile from repository:\n{original_dockerfile}\n\n"
    
    # Add GitHub workflow files if available (provide raw files)
    workflows_text = ""
    if issue_data.get("repository_info", {}).get("github_workflows"):
        workflows = issue_data.get("repository_info", {}).get("github_workflows", {})
        if workflows:
            # Include up to 2 workflow files to avoid overly large prompts
            workflow_files = list(workflows.items())[:2]
            
            workflows_text = "\nGitHub Workflow files found in repository:\n"
            for name, content in workflow_files:
                # Truncate each workflow file if too long
                truncated_content = truncate_text(content, 4000)
                workflows_text += f"\nWorkflow file: {name}\n```yaml\n{truncated_content}\n```\n"
    
    # Create a system prompt
    system_prompt = "You are an expert Docker engineer who specializes in fixing Dockerfiles that failed to build. Provide solutions that address build errors directly."
    
    # Create a prompt to fix this specific candidate
    fix_prompt = f"""
    I need to fix a Dockerfile that failed to build for this GitHub issue. Please help me correct the errors.
    
    Repository URL: {repo_url}
    Issue Number: {issue_number}
    Issue Title: {issue_title}
    Commit SHA: {commit_sha}
    
    Issue Description:
    {issue_body}
    
    Here's the current Dockerfile that's failing:
    ```
    {candidate["dockerfile"]}
    ```
    
    The Docker build failed with the following error:
    ```
    {truncate_text(error, 3000)}
    ```
    
    Please provide an improved version of the Dockerfile that fixes these specific errors.
    Make sure it:
    1. Sets up the appropriate environment to build and validate the solution for this issue
    2. Installs all necessary dependencies
    3. Clones the repository and checks out commit {commit_sha}
    4. Builds the project
    5. Do not need to run anything but have all dependencies and build the project the user need.
    6. Do not have option flags when you build the project unless the user asked to do so or the project mentioned to have them
    
    IMPORTANT: Your response should ONLY contain the Dockerfile content itself, with no additional text, markdown formatting, or code blocks. Just the plain Dockerfile content that I can use directly.
    """
    
    try:
        # Make LLM call to fix the error with adaptive context
        print(f"  LLM API Call #{LLM_CALL_COUNT+1}: Improving candidate #{candidate['candidate_number']} (attempt #{improvement_attempt})")
        
        # Use adaptive context handling
        fix_response_body = call_llm_with_adaptive_context(
            None,  # No bedrock client needed for call_sonnet_37
            "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            system_prompt,
            fix_prompt,
            readme_content,
            repo_structure_text,
            workflows_text,
            reference_dockerfile_text
        )
        
        fixed_dockerfile = fix_response_body["choices"][0]["message"]["content"]
        
        # Clean up the response
        if "```dockerfile" in fixed_dockerfile and "```" in fixed_dockerfile.split("```dockerfile", 1)[1]:
            fixed_dockerfile = fixed_dockerfile.split("```dockerfile", 1)[1].split("```", 1)[0].strip()
        elif "```Dockerfile" in fixed_dockerfile and "```" in fixed_dockerfile.split("```Dockerfile", 1)[1]:
            fixed_dockerfile = fixed_dockerfile.split("```Dockerfile", 1)[1].split("```", 1)[0].strip()
        elif "```" in fixed_dockerfile and "```" in fixed_dockerfile.split("```", 1)[1]:
            fixed_dockerfile = fixed_dockerfile.split("```", 1)[1].split("```", 1)[0].strip()
        
        # Remove any explanations before/after the actual Dockerfile content
        fixed_lines = fixed_dockerfile.split('\n')
        fixed_cleaned_lines = []
        in_fixed_dockerfile = False
        
        for line in fixed_lines:
            # Start capturing at the FROM instruction
            if line.strip().startswith("FROM "):
                in_fixed_dockerfile = True
                
            if in_fixed_dockerfile:
                fixed_cleaned_lines.append(line)
                
        # If we found a FROM directive, use the cleaned content
        if in_fixed_dockerfile:
            fixed_dockerfile = '\n'.join(fixed_cleaned_lines)
        
        return {
            "dockerfile": fixed_dockerfile,
            "candidate_number": candidate["candidate_number"],
            "improvement_attempt": improvement_attempt
        }
    except Exception as e:
        print(f"  Error improving Dockerfile candidate #{candidate['candidate_number']}: {str(e)}")
        return None

def test_build_dockerfile(dockerfile_content, repo_name, issue_number):
    """
    Test building the Docker image from the Dockerfile.
    Returns (success, error_message)
    """
    # Create a temporary directory to work in
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a unique tag for the image
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        image_tag = f"{repo_name.replace('/', '_')}_{issue_number}_{timestamp}".lower()
        
        # Write Dockerfile to temp directory
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
            
        # Build the Docker image
        print(f"Building Docker image {image_tag}...")
        process = subprocess.run(
            ["docker", "build", "-t", image_tag, "."],
            cwd=temp_dir,
            text=True,
            capture_output=True,
            timeout=600  # 10 minute timeout
        )
        
        # Check if build was successful
        if process.returncode == 0:
            print(f"Successfully built Docker image {image_tag}")
            return True, ""
        else:
            error_message = process.stderr or process.stdout
            print(f"Error building Docker image: {error_message[:500]}...")
            return False, error_message
    
    except subprocess.TimeoutExpired:
        error_message = "Docker build timed out after 10 minutes"
        return False, error_message
    except Exception as e:
        error_message = f"Error during Docker build: {str(e)}"
        return False, error_message
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

def test_candidates_in_parallel(candidates, repo_name, issue_number, max_workers=5):
    """Test multiple Dockerfile candidates in parallel"""
    results = []
    
    def test_single_candidate(candidate):
        try:
            dockerfile_content = candidate["dockerfile"]
            candidate_num = candidate["candidate_number"]
            improvement_attempt = candidate.get("improvement_attempt", 0)
            print(f"Testing candidate #{candidate_num}...")
            success, error = test_build_dockerfile(dockerfile_content, repo_name, issue_number)
            
            # Generate and save failure explanation if this is a failure
            if not success:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                repo_name_clean = repo_name.replace('/', '_')
                attempt_num = improvement_attempt + 1  # Default to 1 if not specified
                failure_file = f"{repo_name_clean}_{issue_number}_{timestamp}_attempt{attempt_num}_candidate{candidate_num}.json"
                failure_path = os.path.join(failure_logs_dir, failure_file)
                
                explanation = generate_failure_explanation(error)
                result = {
                    "build_status": "failed",
                    "failure_explanation": explanation,
                    "error_message": error,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                with open(failure_path, 'w') as f:
                    json.dump(result, f, indent=2)
                    
                print(f"Saved failure explanation to {failure_path}")
            
            # Return result dict
            return {
                "dockerfile": dockerfile_content,
                "success": success,
                "error": error if not success else None,
                "improvement_attempt": improvement_attempt,
                "candidate_number": candidate_num
            }
        except Exception as e:
            print(f"Error testing candidate #{candidate.get('candidate_number', 'unknown')}: {str(e)}")
            return {
                "dockerfile": candidate.get("dockerfile", ""),
                "success": False,
                "error": f"Testing error: {str(e)}",
                "improvement_attempt": candidate.get("improvement_attempt", 0),
                "candidate_number": candidate.get("candidate_number", 0)
            }
    
    # Process candidates in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_candidate = {
            executor.submit(test_single_candidate, candidate): candidate
            for candidate in candidates
        }
        
        for future in concurrent.futures.as_completed(future_to_candidate):
            candidate = future_to_candidate[future]
            try:
                result = future.result()
                results.append(result)
                
                # If we found a successful candidate, we can return early
                if result["success"]:
                    # Cancel any remaining futures
                    for f in future_to_candidate:
                        f.cancel()
                    break
                    
            except Exception as e:
                print(f"Error processing result for candidate #{candidate.get('candidate_number', 'unknown')}: {str(e)}")
    
    return results

def generate_and_test_dockerfile_candidates(issue_data, repo_name, issue_number, error_message=None, num_candidates=5, reference_dockerfile=None):
    """
    Generate and test Dockerfile candidates in parallel for improved efficiency:
    1. Generate all candidates in parallel
    2. Test all candidates in parallel, stopping if one succeeds
    3. If all candidates fail, improve them in parallel and test again
    """
    # STEP 1: Generate candidates in parallel
    print(f"Generating {num_candidates} Dockerfile candidates in parallel...")
    candidates = generate_dockerfile_candidates(issue_data, num_candidates, error_message, reference_dockerfile)
    
    # Save all generated candidates
    all_candidates = candidates.copy()
    
    # STEP 2: Test candidates in parallel
    print(f"Testing {len(candidates)} candidates in parallel...")
    results = test_candidates_in_parallel(candidates, repo_name, issue_number)
    
    # Save all results
    all_results = results.copy()
    
    # Check if any candidate was successful
    successful_result = next((r for r in results if r["success"]), None)
    if successful_result:
        print(f"Found successful candidate #{successful_result['candidate_number']}!")
        return successful_result["dockerfile"], all_candidates, all_results, True
    
    # STEP 3: If all candidates failed, try to improve each one
    print(f"\nAll {len(candidates)} candidates failed. Starting improvement attempts...")
    
    # Maximum number of improvement attempts per candidate
    max_improvement_attempts = 4
    
    # For each round of improvements
    for improvement_attempt in range(1, max_improvement_attempts + 1):
        print(f"\nImprovement round #{improvement_attempt}")
        
        # Collect candidates to improve
        candidates_to_improve = []
        for result in results:
            candidates_to_improve.append({
                "dockerfile": result["dockerfile"],
                "candidate_number": result["candidate_number"],
                "error": result["error"]
            })
        
        # Skip if no candidates to improve
        if not candidates_to_improve:
            break
            
        # Improve candidates in parallel
        improved_candidates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(candidates_to_improve), 5)) as executor:
            future_to_candidate = {
                executor.submit(
                    improve_dockerfile_candidate, 
                    issue_data,
                    candidate,
                    candidate["error"],
                    1,  # attempt_number (always 1 for this refactored version)
                    improvement_attempt,
                    reference_dockerfile  # Add reference dockerfile if available
                ): candidate
                for candidate in candidates_to_improve
            }
            
            for future in concurrent.futures.as_completed(future_to_candidate):
                candidate = future_to_candidate[future]
                try:
                    improved_candidate = future.result()
                    if improved_candidate and improved_candidate.get("dockerfile"):
                        improved_candidates.append(improved_candidate)
                        all_candidates.append(improved_candidate)  # Add to all candidates
                except Exception as e:
                    print(f"Error improving candidate #{candidate['candidate_number']}: {str(e)}")
        
        # Test the improved candidates in parallel
        if improved_candidates:
            print(f"Testing {len(improved_candidates)} improved candidates in parallel...")
            improved_results = test_candidates_in_parallel(improved_candidates, repo_name, issue_number)
            
            # Add to all results
            all_results.extend(improved_results)
            
            # Update current results for next round of improvements
            results = improved_results
            
            # Check if any improved candidate was successful
            successful_improved = next((r for r in improved_results if r["success"]), None)
            if successful_improved:
                print(f"Found successful improved candidate #{successful_improved['candidate_number']} (improvement attempt #{improvement_attempt})!")
                return successful_improved["dockerfile"], all_candidates, all_results, True
        else:
            print("No viable improved candidates to test")
            break
    
    # If we get here, no candidates were successful
    return None, all_candidates, all_results, False

def find_closest_commit_before_date(commits, target_date):
    """
    Find the closest commit before or on the target date
    Returns: (commit_sha, commit_date)
    """
    closest_commit = None
    closest_date = None
    
    # Convert target_date to datetime object if it's a string
    if isinstance(target_date, str):
        target_date = datetime.datetime.fromisoformat(target_date.replace("Z", "+00:00"))
    
    for commit in commits:
        commit_date_str = commit.get("date")
        if not commit_date_str:
            continue
        
        # Convert commit date to datetime object
        try:
            commit_date = datetime.datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        
        # Check if this commit is before or on the target date
        if commit_date <= target_date:
            # If we haven't found a commit yet, or this one is more recent
            if closest_date is None or commit_date > closest_date:
                closest_commit = commit
                closest_date = commit_date
    
    return closest_commit, closest_date

def extract_repo_name_from_url(url):
    """Extract repository name from GitHub URL"""
    if not url or "github.com" not in url:
        return None
    
    try:
        # URL format: https://github.com/owner/repo/issues/number
        parts = url.split("github.com/")[1].split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    except:
        pass
    
    return None

def find_commits_file_for_repo(repo_name):
    """Find the commit data file for a specific repository"""
    if not repo_name:
        return None
    
    # Format the repo name in the expected file pattern
    # Expected format: commits_github_issues_owner_repo_*.json
    repo_parts = repo_name.split("/")
    if len(repo_parts) != 2:
        return None
    
    owner, repo = repo_parts
    file_pattern = f"commits_github_issues_{owner}_{repo}_"
    
    # Try to find a matching file
    for filename in os.listdir(github_commits_dir):
        if filename.startswith(file_pattern) and filename.endswith(".json"):
            return os.path.join(github_commits_dir, filename)
            
    # Also try with other combinations of the name
    for filename in os.listdir(github_commits_dir):
        if owner.lower() in filename.lower() and repo.lower() in filename.lower() and filename.endswith(".json"):
            return os.path.join(github_commits_dir, filename)
    
    return None


def find_existing_successful_dockerfiles(repo_name):
    """
    Find successful Dockerfiles for the same repository in already processed files
    Returns a dictionary mapping issue numbers to successful Dockerfiles
    """
    successful_dockerfiles = {}
    
    # Check output directory for existing files
    output_files = [f for f in os.listdir(output_dir) if f.endswith('.json') and f.startswith(f"issue_{repo_name.replace('/', '_')}_")]
    
    for file_name in output_files:
        try:
            file_path = os.path.join(output_dir, file_name)
            with open(file_path, 'r') as f:
                issue_data = json.load(f)
                
                # Extract issue number from the filename
                parts = file_name.split('_')
                issue_number = parts[-1].split('.')[0] if len(parts) > 2 else "unknown"
                
                # Check if this file has a successful Dockerfile
                if issue_data.get("dockerfile_build_success") == True and "dockerfile" in issue_data:
                    successful_dockerfiles[issue_number] = issue_data["dockerfile"]
                    print(f"Found existing successful Dockerfile for {repo_name} issue #{issue_number}")
        except Exception as e:
            print(f"Error reading existing file {file_name}: {str(e)}")
    
    return successful_dockerfiles

def get_repository_info(repo_name, commit_sha):
    """Get README, Dockerfile, GitHub workflows, and repository structure by cloning the repo"""
    repo_info = {}
    
    # Create a temporary directory to clone the repository
    temp_dir = tempfile.mkdtemp()
    try:
        print(f"Cloning repository {repo_name} at commit {commit_sha[:7]} to {temp_dir}")
        
        # Clone the repository
        clone_url = f"https://github.com/{repo_name}.git"
        subprocess.run(
            ["git", "clone", "--quiet", clone_url, temp_dir],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Checkout the specific commit
        subprocess.run(
            ["git", "checkout", "--quiet", commit_sha],
            cwd=temp_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Generate a summary of the repository structure using find and du
        try:
            result = subprocess.run(
                ["find", ".", "-type", "f", "-not", "-path", "*/\\.*", "|", "sort"],
                cwd=temp_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True
            )
            repo_structure_summary = result.stdout
        except subprocess.SubprocessError:
            # Fallback using ls -R if find fails
            result = subprocess.run(
                ["ls", "-R"],
                cwd=temp_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            repo_structure_summary = result.stdout
        
        repo_info["structure_summary"] = repo_structure_summary
        
        # Find README files (limit to top 3)
        readme_files = []
        try:
            result = subprocess.run(
                ["find", ".", "-type", "f", "-iname", "readme*", "-o", "-iname", "*.md"],
                cwd=temp_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            readme_candidates = [path.strip() for path in result.stdout.split('\n') if path.strip()]
            # Prioritize certain README files
            prioritized = []
            for candidate in readme_candidates:
                basename = os.path.basename(candidate).lower()
                if basename in ["readme.md", "readme", "readme.txt"]:
                    prioritized.append(candidate)
            
            # Add any remaining candidates
            for candidate in readme_candidates:
                if candidate not in prioritized:
                    prioritized.append(candidate)
                    
            # Get the top 3
            readme_files = prioritized[:3]
        except subprocess.SubprocessError as e:
            print(f"Error finding README files: {str(e)}")
        
        # Read README content
        if readme_files:
            readme_content = ""
            for readme_path in readme_files:
                try:
                    with open(os.path.join(temp_dir, readme_path.lstrip("./").lstrip(".\\")), 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        readme_content += f"\n--- {readme_path} ---\n{content}\n\n"
                except Exception as e:
                    print(f"Error reading {readme_path}: {str(e)}")
            
            repo_info["readme"] = readme_content
            repo_info["readme_filenames"] = readme_files
        
        # Find Dockerfile files (limit to top 3)
        dockerfile_files = []
        try:
            result = subprocess.run(
                ["find", ".", "-type", "f", "-iname", "dockerfile*", "-o", "-iname", "*.dockerfile", "-o", "-path", "*/docker/*"],
                cwd=temp_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            dockerfile_candidates = [path.strip() for path in result.stdout.split('\n') if path.strip()]
            # Prioritize root Dockerfile
            prioritized = []
            for candidate in dockerfile_candidates:
                basename = os.path.basename(candidate).lower()
                dirname = os.path.dirname(candidate).lower()
                if basename == "dockerfile" and dirname in [".", "./"]:
                    prioritized.append(candidate)
            
            # Add any remaining candidates
            for candidate in dockerfile_candidates:
                if candidate not in prioritized:
                    prioritized.append(candidate)
                    
            # Get the top 3
            dockerfile_files = prioritized[:3]
        except subprocess.SubprocessError as e:
            print(f"Error finding Dockerfile files: {str(e)}")
        
        # Read Dockerfile content
        if dockerfile_files:
            dockerfile_content = ""
            for dockerfile_path in dockerfile_files:
                try:
                    with open(os.path.join(temp_dir, dockerfile_path.lstrip("./").lstrip(".\\")), 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        dockerfile_content += f"\n--- {dockerfile_path} ---\n{content}\n\n"
                except Exception as e:
                    print(f"Error reading {dockerfile_path}: {str(e)}")
            
            repo_info["dockerfile"] = dockerfile_content
            repo_info["dockerfile_paths"] = dockerfile_files
        
        # Find GitHub workflow files (limit to top 3)
        workflow_files = {}
        workflow_dir = os.path.join(temp_dir, '.github', 'workflows')
        if os.path.exists(workflow_dir):
            try:
                workflow_candidates = []
                for root, dirs, files in os.walk(workflow_dir):
                    for file in files:
                        if file.endswith(('.yml', '.yaml')):
                            rel_path = os.path.join(os.path.relpath(root, temp_dir), file)
                            workflow_candidates.append(rel_path)
                
                # Get the top 3
                for workflow_path in workflow_candidates[:3]:
                    try:
                        with open(os.path.join(temp_dir, workflow_path), 'r', encoding='utf-8', errors='replace') as f:
                            workflow_files[workflow_path] = f.read()
                    except Exception as e:
                        print(f"Error reading {workflow_path}: {str(e)}")
            except Exception as e:
                print(f"Error finding workflow files: {str(e)}")
        
        if workflow_files:
            repo_info["github_workflows"] = workflow_files
            
        return repo_info
    
    except subprocess.SubprocessError as e:
        print(f"Error with git operations: {str(e)}")
        return repo_info
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def generate_build_script(issue_data, repo_name, use_workflows=True):
    """Generate either a Dockerfile or extract information from GitHub workflows based on what's available"""
    
    # Check if GitHub workflows are available
    has_workflows = bool(issue_data.get("repository_info", {}).get("github_workflows"))
    
    # If workflows are available and we want to use them
    if has_workflows and use_workflows:
        workflows = issue_data.get("repository_info", {}).get("github_workflows", {})
        workflow_info = issue_data.get("repository_info", {}).get("github_workflow_info", {})
        
        # Keep track of the build strategy
        issue_data["build_strategy"] = "github_workflow"
        issue_data["github_workflow_files"] = list(workflows.keys())
        
        # Return the workflow information (you can handle this differently based on your needs)
        return {
            "type": "github_workflow",
            "workflows": workflows,
            "workflow_info": workflow_info
        }
    else:
        # Fall back to Dockerfile generation
        issue_data["build_strategy"] = "dockerfile"
        
        # Use your existing Dockerfile generation logic here
        # This is a placeholder - you'll need to integrate with your existing code
        dockerfile = "FROM ubuntu:latest\n# Dockerfile generation placeholder"
        
        return {
            "type": "dockerfile",
            "dockerfile": dockerfile
        }

def process_issues():
    # Process each JSON file in the input directory
    total_processed = 0
    successful_builds = 0
    
    # Keep track of successfully generated Dockerfiles by repo
    successful_dockerfiles = {}  # repo_name -> dockerfile
    
    # List all JSON files in the input directory
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    print(f"Found {len(json_files)} JSON files to process")
    
    for filename in json_files:
        file_path = os.path.join(input_dir, filename)
        print(f"Processing {filename}...")
        
        # Track LLM calls for this specific issue
        global LLM_CALL_COUNT
        issue_start_llm_count = LLM_CALL_COUNT
        
        # Read the JSON file
        with open(file_path, 'r') as f:
            try:
                # The input format is a list of issues
                issues_data = json.load(f)
                
                # Track repositories we've seen in this batch to avoid redundant lookups
                seen_repos = set()
                
                # Process each issue in the file
                for issue_data in issues_data:
                    # Get repository from URL
                    issue_url = issue_data.get("url", "")
                    repo_name = extract_repo_name_from_url(issue_url)
                    if not repo_name:
                        print(f"Couldn't extract repository name from {issue_url}, skipping")
                        continue
                    
                    # Load existing successful Dockerfiles for this repo if we haven't already
                    if repo_name not in seen_repos:
                        seen_repos.add(repo_name)
                        # Check for existing successful Dockerfiles for this repository
                        existing_dockerfiles = find_existing_successful_dockerfiles(repo_name)
                        if existing_dockerfiles:
                            # Use the most recent one as reference
                            most_recent_issue = max(existing_dockerfiles.keys())
                            successful_dockerfiles[repo_name] = existing_dockerfiles[most_recent_issue]
                            print(f"Using existing successful Dockerfile from issue #{most_recent_issue} for repository {repo_name}")
                            
                    # Get issue number
                    issue_number = issue_data.get("number", "unknown")
                    print(f"Processing issue #{issue_number} from {repo_name}")
                    
                    # Check if this specific issue already has a successful solution in the output dir
                    output_filename = f"issue_{repo_name.replace('/', '_')}_{issue_number}.json"
                    output_path = os.path.join(output_dir, output_filename)
                    if os.path.exists(output_path):
                        print(f"Issue #{issue_number} already has a solution at {output_path}, skipping")
                        successful_builds += 1
                        total_processed += 1
                        continue
                        
                    # Get issue creation date
                    issue_date_str = issue_data.get("created_at")
                    if not issue_date_str:
                        print(f"No creation date for issue #{issue_number}, skipping")
                        continue
                    
                    total_processed += 1
                    
                    # Skip if already has verified working dockerfile
                    if issue_data.get("dockerfile_build_success") == True:
                        print(f"Issue #{issue_number} already has working Dockerfile, skipping")
                        successful_builds += 1
                        
                        # Store the successful Dockerfile for this repo for future reference
                        if "dockerfile" in issue_data:
                            successful_dockerfiles[repo_name] = issue_data["dockerfile"]
                            
                        continue
                    
                    # Find commit if not already in the data
                    if "git_commit_info" not in issue_data:
                        # Find commits file for this repository
                        commits_file = find_commits_file_for_repo(repo_name)
                        if not commits_file:
                            print(f"No commits file found for repository {repo_name}, skipping")
                            continue
                        
                        # Load commits data
                        try:
                            with open(commits_file, 'r') as cf:
                                commits_data = json.load(cf)
                        except (json.JSONDecodeError, FileNotFoundError):
                            print(f"Error reading commits file {commits_file}, skipping")
                            continue
                        
                        # Get commits list
                        commits = commits_data.get("commits", [])
                        if not commits:
                            print(f"No commits found in {commits_file}, skipping")
                            continue
                            
                        # Find closest commit before issue date
                        closest_commit, closest_date = find_closest_commit_before_date(commits, issue_date_str)
                        
                        if not closest_commit:
                            print(f"No commit found before {issue_date_str} for {repo_name}, skipping")
                            continue
                            
                        # Add commit information to the issue data
                        commit_sha = closest_commit.get("sha")
                        issue_data["git_commit_info"] = {
                            "sha": commit_sha,
                            "date": closest_commit.get("date"),
                            "message": closest_commit.get("message"),
                            "author": closest_commit.get("author")
                        }
                    else:
                        commit_sha = issue_data["git_commit_info"]["sha"]
                    
                    # Get repository info if not already in the data
                    if "repository_info" not in issue_data:
                        print(f"Fetching repository info for {repo_name} at commit {commit_sha[:7]}")
                        repo_info = get_repository_info(repo_name, commit_sha)
                        issue_data["repository_info"] = repo_info
                        
                    # Store LLM call count prior to build attempts
                    issue_data["llm_calls_before_build"] = LLM_CALL_COUNT - issue_start_llm_count
                    
                    # Check if we should use an existing GitHub workflow
                    has_workflows = bool(issue_data.get("repository_info", {}).get("github_workflows"))
                    if has_workflows:
                        print(f"Found GitHub workflow files in repository")
                        # Store the workflow files info in the main issue data
                        issue_data["github_workflows_found"] = list(issue_data["repository_info"]["github_workflows"].keys())
                        
                    # Check if we should use an existing Dockerfile from the repository
                    use_repo_dockerfile = False
                    if "dockerfile" not in issue_data and "dockerfile" in issue_data.get("repository_info", {}):
                        print(f"Using Dockerfile from repository")
                        issue_data["dockerfile"] = issue_data["repository_info"]["dockerfile"]
                        issue_data["dockerfile_source"] = f"Repository at {issue_data['repository_info'].get('dockerfile_path', 'Dockerfile')}"
                        use_repo_dockerfile = True
                    
                    # Check if we already have a successful Dockerfile for this repo from another issue
                    reference_dockerfile = None
                    if repo_name in successful_dockerfiles:
                        print(f"Using previously successful Dockerfile for {repo_name} as reference")
                        # We'll use this as a reference for our LLM prompt, but won't automatically use it
                        reference_dockerfile = successful_dockerfiles[repo_name]
                    
                    # Test and improve the Dockerfile up to 5 times
                    max_attempts = 1
                    attempt = 1
                    build_success = False
                    
                    # If using repo Dockerfile, test it first
                    if use_repo_dockerfile:
                        print(f"Testing repository Dockerfile")
                        success, error_message = test_build_dockerfile(issue_data["dockerfile"], repo_name, issue_number)
                        
                        if success:
                            build_success = True
                            issue_data["dockerfile_build_success"] = True
                            issue_data["dockerfile_build_attempts"] = 1
                            print(f"Repository Dockerfile built successfully!")
                            successful_builds += 1
                            
                            # Store for future reference
                            successful_dockerfiles[repo_name] = issue_data["dockerfile"]
                        else:
                            # Store the error in a separate failure file
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                            repo_name_clean = repo_name.replace('/', '_')
                            error_file_path = os.path.join(failure_logs_dir, 
                                                         f"{repo_name_clean}_{issue_number}_{timestamp}_repo_dockerfile_failure.json")
                            
                            explanation = generate_failure_explanation(error_message)
                            with open(error_file_path, 'w') as err_f:
                                failure_data = {
                                    "dockerfile": issue_data["dockerfile"],
                                    "error_message": error_message,
                                    "failure_explanation": explanation,
                                    "timestamp": datetime.datetime.now().isoformat()
                                }
                                json.dump(failure_data, err_f, indent=2)
                            print(f"Saved repository Dockerfile failure explanation to {error_file_path}")
                    
                    # Only proceed with generation if not successful yet
                    while attempt <= max_attempts and not build_success:
                        print(f"Attempt {attempt}/{max_attempts} to generate and build Docker image")
                        
                        # Generate and test candidates
                        previous_error = None
                        if attempt > 1:
                            # Get most detailed error from previous attempt's failure file
                            timestamp_pattern = datetime.datetime.now().strftime("%Y%m%d")
                            repo_name_clean = repo_name.replace('/', '_')
                            
                            # Find failure files matching the pattern
                            failure_files = [f for f in os.listdir(failure_logs_dir) 
                                           if f.startswith(f"{repo_name_clean}_{issue_number}_{timestamp_pattern}") 
                                           and f"attempt{attempt-1}" in f 
                                           and f.endswith(".json")]
                            
                            if failure_files:
                                # Use the most recent failure file
                                failure_files.sort(reverse=True)
                                error_file_path = os.path.join(failure_logs_dir, failure_files[0])
                                
                                try:
                                    with open(error_file_path, 'r') as err_f:
                                        error_data = json.load(err_f)
                                        previous_error = error_data.get("error_message", "")
                                except:
                                    pass
                        
                        # Generate and immediately test candidates in parallel
                        successful_dockerfile, candidates, results, success = generate_and_test_dockerfile_candidates(
                            issue_data, 
                            repo_name, 
                            issue_number,
                            previous_error,
                            num_candidates=5,  # Explicitly set to 5
                            reference_dockerfile=reference_dockerfile  # Pass reference dockerfile if available
                        )
                        
                        # Store only attempt number in the main issue file
                        issue_data[f"dockerfile_attempt_{attempt}"] = attempt
                        
                        # Store detailed candidates and results in separate files
                        for i, result in enumerate(results[:5]):
                            # Build filename using timestamp
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                            repo_name_clean = repo_name.replace('/', '_')
                            
                            candidate_file_path = os.path.join(failure_logs_dir, 
                                               f"{repo_name_clean}_{issue_number}_{timestamp}_attempt{attempt}_candidate{i+1}.json")
                            
                            with open(candidate_file_path, 'w') as cand_f:
                                candidate_data = {
                                    "dockerfile": result["dockerfile"],
                                    "success": result["success"],
                                }
                                
                                if not result["success"]:
                                    candidate_data["error_message"] = result["error"]
                                    candidate_data["failure_explanation"] = generate_failure_explanation(result["error"])
                                    
                                json.dump(candidate_data, cand_f, indent=2)
                            
                            print(f"Saved candidate #{i+1} details to {candidate_file_path}")
                        
                        # If any candidate was successful
                        if success and successful_dockerfile:
                            build_success = True
                            issue_data["dockerfile"] = successful_dockerfile
                            issue_data["dockerfile_build_success"] = True
                            issue_data["dockerfile_build_attempts"] = attempt
                            
                            # Find which candidate was successful
                            for i, result in enumerate(results[:5]):
                                if result["success"]:
                                    issue_data["successful_candidate_index"] = i+1
                                    issue_data["successful_candidate_attempt"] = attempt
                                    issue_data["successful_candidate_improvement_attempt"] = result.get("improvement_attempt", 0)
                                    break
                                    
                            print(f"Docker build successful on attempt {attempt}!")
                            successful_builds += 1
                            
                            # Store the successful Dockerfile for future reference
                            successful_dockerfiles[repo_name] = successful_dockerfile
                            break
                        else:
                            # No successful candidates this attempt - save just the attempt number in main file
                            issue_data[f"dockerfile_attempt_{attempt}_failed"] = True
                            
                            # Store comprehensive failure info in a separate file
                            if results and results[0].get("error"):
                                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                                repo_name_clean = repo_name.replace('/', '_')
                                failure_file_path = os.path.join(failure_logs_dir, 
                                                              f"{repo_name_clean}_{issue_number}_{timestamp}_attempt{attempt}_failure.json")
                                
                                with open(failure_file_path, 'w') as fail_f:
                                    failure_data = {
                                        "error_message": results[0]["error"],
                                        "failure_explanation": generate_failure_explanation(results[0]["error"]),
                                        "dockerfile": results[0]["dockerfile"],
                                        "attempt": attempt,
                                        "timestamp": datetime.datetime.now().isoformat()
                                    }
                                    json.dump(failure_data, fail_f, indent=2)
                                
                                print(f"Saved attempt {attempt} failure details to {failure_file_path}")
                            
                            print(f"All candidates failed on attempt {attempt}")
                            
                        attempt += 1
                        
                    # Record final build status in main issue file
                    issue_data["dockerfile_build_success"] = build_success
                    issue_data["dockerfile_build_attempts"] = attempt - 1
                    
                    # Only keep the essential information in the main issue file
                    for key in list(issue_data.keys()):
                        if key.startswith("dockerfile_build_attempt") or key.startswith("dockerfile_candidates"):
                            del issue_data[key]
                            
                    # Store final LLM call count for this issue
                    issue_data["llm_calls_total"] = LLM_CALL_COUNT - issue_start_llm_count
                    
                    # If build was successful, save to output directory
                    if build_success:
                        output_filename = f"issue_{repo_name.replace('/', '_')}_{issue_number}.json"
                        output_path = os.path.join(output_dir, output_filename)
                        with open(output_path, 'w') as of:
                            json.dump(issue_data, of, indent=2)
                        print(f"Saved successful build to {output_path}")
                
            except json.JSONDecodeError:
                print(f"Error reading {filename}, skipping")
                continue
        
        # Add a short delay to avoid rate limits
        time.sleep(1)
    
    print("\n===== Processing Summary =====")
    print(f"Total issues processed: {total_processed}")
    print(f"Successfully built Docker images: {successful_builds}")
    print(f"Success rate: {(successful_builds/total_processed)*100 if total_processed > 0 else 0:.1f}%")
    print(f"Total LLM API calls made: {LLM_CALL_COUNT}")
    print("============================")

def call_sonnet_37(prompt, system_prompt=None, temperature=0.7, max_tokens=15000, max_retries=1000):
    """
    Make an API call to Claude 3.7 Sonnet using Bedrock with robust retry logic
    
    Args:
        prompt: The prompt to send to the model
        system_prompt: System prompt (optional)
        temperature: Sampling temperature (default 0.7)
        max_tokens: Maximum number of tokens to generate (default 15000)
        max_retries: Maximum number of retry attempts (default 1000)
        
    Returns:
        The generated text response
    """
    global LLM_CALL_COUNT
    LLM_CALL_COUNT += 1
    
    # Initialize the Bedrock client
    config = Config(retries={"max_attempts": 10000, "mode": "standard"})
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-2', config=config)
    
    # Model ID for Claude 3.7 Sonnet
    model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    
    # Format request for Claude 3.7 Sonnet
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    # Add system prompt if provided
    if system_prompt:
        request_body["system"] = system_prompt
    
    # Implement retry logic
    retry_count = 0
    backoff_time = 1  # Start with 1 second backoff
    max_backoff = 60  # Maximum backoff of 60 seconds
    
    while retry_count < max_retries:
        try:
            # Call the API
            response = bedrock_client.invoke_model(
                body=json.dumps(request_body),
                modelId=model_id,
                accept='application/json',
                contentType='application/json'
            )
            
            # Process the response
            response_body = json.loads(response.get('body').read())
            
            # Log the interaction
            log_llm_interaction(
                model_id=model_id,
                prompt=f"SYSTEM: {system_prompt}\nUSER: {prompt}" if system_prompt else prompt,
                response_body=response_body,
                call_context=f"call_sonnet_37 (LLM Call #{LLM_CALL_COUNT}, Attempt #{retry_count+1})"
            )
            
            # Extract the response text
            response_text = response_body["content"][0]["text"]
            
            # If we got here, the call was successful
            if retry_count > 0:
                print(f"  Succeeded after {retry_count+1} attempts")
            
            return response_text
            
        except Exception as e:
            retry_count += 1
            
            # Log the error
            error_message = str(e)
            print(f"  API call error (attempt {retry_count}/{max_retries}): {error_message}")
            logging.warning(f"API call error (attempt {retry_count}/{max_retries}): {error_message}")
            
            if retry_count >= max_retries:
                print(f"  Failed after {max_retries} attempts, raising exception")
                logging.error(f"Failed after {max_retries} attempts: {error_message}")
                raise
            
            sleep_time = 10
            
            print(f"  Retrying in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
            
            # Increase backoff time for next attempt (exponential backoff)
            backoff_time = min(backoff_time * 2, max_backoff)

if __name__ == "__main__":
    # Set up logging
    current_log_file = setup_logging()
    logging.info("Starting process_issues function")
    
    # Process all issues
    try:
        process_issues()
        logging.info("Completed process_issues function successfully")
    except Exception as e:
        error_msg = f"Error in main process: {str(e)}"
        print(error_msg)
        logging.error(error_msg)
        import traceback
        logging.error(traceback.format_exc())
    
    # Log summary
    logging.info(f"Total LLM API calls made: {LLM_CALL_COUNT}")