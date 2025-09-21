import json
import os
import subprocess
import tempfile
import shutil
import boto3
import logging
import time
import numpy as np
import re
from botocore.config import Config
from datetime import datetime
from rank_bm25 import BM25Okapi
import docker
from docker.errors import DockerException, BuildError, APIError
# Add this to the imports at the top
import threading
from collections import defaultdict
import requests
import random
from openai import OpenAI
from dotenv import load_dotenv

# Add this after your logging configuration
# LLM call counter for tracking calls per agent per issue
llm_call_counter = defaultdict(lambda: defaultdict(int))
call_counter_lock = threading.Lock()
MAINTAINER = "llama"


# Configure main application logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('maintainer_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure boto3 client
config = Config(
    retries = {
        "max_attempts": 1000,
        "mode": "standard"
    },
    connect_timeout=120,  # 120 seconds for connection timeout
    read_timeout=1200     # 20 minutes for read timeout
)

bedrock = boto3.client('bedrock-runtime', config=config, region_name='us-west-2')

def is_input_too_long_error(response_text_or_error):
    """Check if the response or error message indicates an input too long error or payload size error."""
    error_patterns = [
        # Input too long errors
        "input is too long",
        "input is t\noo long", # Handle line break in error message
        "input exceeds maximum token length",
        "context window exceeded",
        "input sequence length exceeds the model's context window",
        "input too long for model",
        "input is too long for requested model",
        "ValidationException) when calling the InvokeModel operation: Input is t\noo long",
        "ValidationException) when calling the InvokeModel operation: Input is too long",
        "too many total text bytes",
        # Payload size errors
        "Member must have length less than or equal to",
        "body' failed to satisfy constraint",
        "failed to satisfy constraint: Member must have length"
    ]
    
    error_text = str(response_text_or_error).lower()
    for pattern in error_patterns:
        if pattern.lower() in error_text:
            return True
    return False

def call_llm(
    user_prompt,
    system_prompt,
    agent_type="unspecified",
    issue_id="unknown",
    max_retries=1000,
    model="sonnet",
):
    """Call LLM model with given prompts and retry logic, now supporting GPT-4o (4.1)."""
    # Choose model based on parameter
    is_thinking = False
    is_claude = False
    is_llama = False
    is_o4_mini = False
    is_gpt = False

    if model == "haiku":
        model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
        max_tokens_limit = 120_000
        model_name = "Haiku"
        is_claude = True
    elif model in ("deepseek", "deepseek-r1"):
        model_id = "us.deepseek.r1-v1:0"
        max_tokens_limit = 30_000
        model_name = "DeepSeek R1"
    elif model == "llama":
        model_id = "us.meta.llama3-3-70b-instruct-v1:0"
        max_tokens_limit = 8_192
        model_name = "Llama 3.3 70B"
        is_llama = True
    elif model == "o4-mini":
        model_id = "o4-mini"
        max_tokens_limit = 100_000
        model_name = "o4-mini"
        is_o4_mini = True
    elif model == "thinking":
        model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        max_tokens_limit = 120_000
        model_name = "Sonnet (Thinking Mode)"
        is_thinking = True
    elif model == "gpt-4.1-mini":
        model_id = "gpt-4.1-mini-2025-04-14"
        max_tokens_limit = 30000
        model_name = "gpt-4.1-mini-2025-04-14"
        is_gpt = True
    else:  # default to Sonnet
        model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        max_tokens_limit = 120_000
        model_name = "Sonnet"
        is_claude = True

    llm_logger.info(f"===== SYSTEM PROMPT =====\n{system_prompt}\n")
    llm_logger.info(f"===== USER PROMPT =====\n{user_prompt}\n")

    logger.info(
        f"Calling {model_name} model (prompt length: {len(user_prompt)}, agent: {agent_type}, issue: {issue_id})"
    )
    start_time = time.time()

    total_prompt_size = len(user_prompt) + len(system_prompt)
    if total_prompt_size > max_tokens_limit:
        logger.warning(f"Prompt size too large ({total_prompt_size} bytes). Skipping API call.")
        return "ERROR_INPUT_TOO_LONG"

    # Increment the call counter for this agent and issue
    with call_counter_lock:
        llm_call_counter[issue_id][agent_type] += 1
        total_calls = sum(llm_call_counter[issue_id].values())
        logger.info(
            f"LLM Call #{total_calls} for issue {issue_id}: Agent {agent_type} (agent total: {llm_call_counter[issue_id][agent_type]})"
        )

    retry_count = 0
    while retry_count <= max_retries:
        try:
            if is_o4_mini or is_gpt:
                # Load environment variables for OpenAI
                load_dotenv()
                api_token = os.getenv("GPT_TOKEN")
                if not api_token:
                    raise RuntimeError("GPT_TOKEN not set in .env")
                client = OpenAI(api_key=api_token)

                used_model = model_id
                openai_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                openai_response = client.chat.completions.create(
                    model=used_model,
                    messages=openai_messages,
                    max_tokens=max_tokens_limit,
                    temperature=0.0,
                )

                response_text = openai_response.choices[0].message.content

            else:
                # Different payload structure based on model type (Bedrock models)
                if is_claude:
                    body = json.dumps(
                        {
                            "anthropic_version": "bedrock-2023-05-31",
                            "system": system_prompt,
                            "messages": [{"role": "user", "content": user_prompt}],
                            "max_tokens": max_tokens_limit,
                            "temperature": 0.0,
                        }
                    )
                elif is_llama:
                    # Use the standard Meta chat format
                    formatted_prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{user_prompt}<|end|>\n<|assistant|>"
                    
                    body = json.dumps(
                        {
                            "prompt": formatted_prompt,
                            "max_gen_len": max_tokens_limit,
                            "temperature": 0.0,
                        }
                    )
                elif is_thinking:
                    body = json.dumps(
                        {
                            "anthropic_version": "bedrock-2023-05-31",
                            "system": system_prompt,
                            "messages": [{"role": "user", "content": user_prompt}],
                            "max_tokens": max_tokens_limit,
                            "thinking": {"type": "enabled", "budget_tokens": 30000},
                        }
                    )
                else:  # DeepSeek format
                    body = json.dumps(
                        {
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "max_tokens": max_tokens_limit,
                            "temperature": 0.0,
                        }
                    )

                response = bedrock.invoke_model(
                    body=body,
                    modelId=model_id,
                    accept="application/json",
                    contentType="application/json",
                )

                response_body = json.loads(response.get("body").read())

                # Different response format based on model type
                if is_claude:
                    response_text = response_body["content"][0]["text"]
                elif is_llama:
                    # Extract the generation and clean it by removing the <|end|> tag if present
                    raw_response = response_body.get("generation", response_body.get("completion", ""))
                    if "<|end|>" in raw_response:
                        response_text = raw_response.split("<|end|>")[0].strip()
                    else:
                        response_text = raw_response.strip()
                elif is_thinking:
                    response_text = response_body["content"][1]["text"]
                else:  # DeepSeek format
                    response_text = response_body["choices"][0]["message"]["content"]

                # Log conversation ID if available for tracking conversation threads
                if "conversation_id" in response_body:
                    llm_logger.info(f"Conversation ID: {response_body['conversation_id']}")

            elapsed_time = time.time() - start_time
            logger.info(f"{model_name} model responded in {elapsed_time:.2f} seconds")

            llm_logger.info(f"===== LLM RESPONSE =====\n{response_text}\n")
            return response_text

        except Exception as e:
            error_str = str(e)

            # Check for input too long or payload size errors
            if "ValidationException" in error_str and (
                "Input is too long" in error_str
                or "Member must have length less than or equal to" in error_str
                or "body' failed to satisfy constraint" in error_str
                or "decrease input length" in error_str
            ):
                logger.warning(
                    f"Input size error detected: {error_str}. Ending conversation and using existing results."
                )
                return "ERROR_INPUT_TOO_LONG"

            retry_count += 1
            if retry_count <= max_retries:
                wait_time = 10
                logger.warning(
                    f"LLM call failed (attempt {retry_count}/{max_retries}). "
                    f"Retrying in {wait_time:.2f} seconds. Error: {str(e)}"
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    f"LLM call failed after {max_retries} retries. Final error: {str(e)}"
                )
                raise Exception(
                    f"Failed to call LLM after {max_retries} retries: {str(e)}"
                )
def setup_docker_client():
    """Initialize Docker client with better error handling."""
    try:
        client = docker.from_env()
        # Test the connection
        client.ping()
        return client
    except (DockerException, requests.exceptions.ConnectionError) as e:
        logger.error(f"Failed to initialize Docker client: {e}")
        return None

def build_and_run_dockerfile(issue_data, test_commands, extra_files=None, build_timeout=900, run_timeout=600):
    """Build and run Dockerfile with test commands and additional files."""
    client = None
    temp_dir = None
    image_id = None
    container = None
    
    try:
        # Setup Docker client
        client = docker.from_env()
        
        # Check docker client connection
        try:
            client.ping()
        except Exception as e:
            logger.error(f"Docker client connection test failed: {e}")
            return False, f"Docker client connection error: {str(e)}"
        
        # Create temporary directory for Docker context
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created Docker build context at: {temp_dir}")
        
        # Write Dockerfile
        dockerfile_path = os.path.join(temp_dir, 'Dockerfile')
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(issue_data['dockerfile'])
            
        logger.info(f"Written Dockerfile ({len(issue_data['dockerfile'])} bytes)")
        
        # Write any additional files
        if extra_files:
            for file_path, content in extra_files.items():
                success = write_file_in_docker_context(temp_dir, file_path, content)
                if not success:
                    return False, f"Failed to create required file: {file_path}"
        
        # Create test script instead of adding commands to Dockerfile
        if test_commands:
            test_script_path = os.path.join(temp_dir, 'docker_test.sh')
            with open(test_script_path, 'w', encoding='utf-8') as f:
                f.write("#!/bin/bash\n")
                f.write("set -e\n")  # Exit on first error
                f.write("echo 'Starting Docker validation tests...'\n\n")
                
                for i, cmd in enumerate(test_commands):
                    # Skip docker commands as they won't work inside the container
                    if cmd.startswith("docker "):
                        f.write(f"echo 'Skipping docker command: {cmd}'\n")
                        continue
                        
                    f.write(f"echo 'Test {i+1}: {cmd}'\n")
                    f.write(f"{cmd}\n")
                    f.write(f"echo 'Test {i+1} completed successfully'\n\n")
                
                f.write("echo 'All tests passed successfully!'\n")
                
            # Make the script executable
            os.chmod(test_script_path, 0o755)
            logger.info(f"Created test script with {len(test_commands)} commands")
            
            # Modify Dockerfile to copy and run the test script
            with open(dockerfile_path, 'a', encoding='utf-8') as f:
                f.write("\n# Add test script\n")
                f.write("COPY docker_test.sh /docker_test.sh\n")
                f.write("RUN chmod +x /docker_test.sh\n\n")
                f.write("# Test commands will run when the container starts\n")
                f.write("CMD [\"/docker_test.sh\"]\n")
        
        # Log contents of build context for debugging
        try:
            file_list = subprocess.run(
                ["find", ".", "-type", "f", "-not", "-path", "*/\\.*"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Docker build context files:\n{file_list.stdout}")
        except Exception as e:
            logger.warning(f"Could not list build context files: {e}")
            
        # Build the Docker image with proper timeout handling
        logger.info(f"Building Docker image (timeout: {build_timeout}s)...")
        build_logs = []
        
        try:
            # Use the low-level API to get build progress
            build_result = client.api.build(
                path=temp_dir,
                rm=True,
                forcerm=True,
                decode=True,
                timeout=build_timeout
            )
            
            # Collect build logs
            for chunk in build_result:
                if 'stream' in chunk:
                    build_logs.append(chunk['stream'].strip())
                    logger.debug(f"Build log: {chunk['stream'].strip()}")
                elif 'error' in chunk:
                    error_msg = chunk['error'].strip()
                    build_logs.append(f"ERROR: {error_msg}")
                    logger.error(f"Build error: {error_msg}")
                    
                # Check if there's an image ID (indicating success)
                if 'aux' in chunk and 'ID' in chunk['aux']:
                    image_id = chunk['aux']['ID']
                    
            # If we didn't get an image ID, something went wrong
            if not image_id:
                for line in build_logs:
                    if line.startswith("Successfully built "):
                        image_id = line.split("Successfully built ")[1].strip()
                        break
                        
            if not image_id:
                return False, "Failed to get image ID after build"
                
            logger.info(f"Docker image built successfully: {image_id}")
            
        except docker.errors.BuildError as e:
            logger.error(f"Docker build failed: {str(e)}")
            build_logs.append(f"BUILD FAILED: {str(e)}")
            return False, '\n'.join(build_logs)
            
        except docker.errors.APIError as e:
            logger.error(f"Docker API error during build: {str(e)}")
            return False, f"Docker API error: {str(e)}"
            
        except Exception as e:
            logger.error(f"Unexpected error during Docker build: {str(e)}")
            return False, f"Unexpected build error: {str(e)}"
        
        # Run the Docker container with improved timeout handling
        logger.info(f"Running Docker container (timeout: {run_timeout}s)...")
        container_logs = []
        container_id = None
        
        try:
            # Create and start the container
            container = client.containers.create(image_id)
            container_id = container.id
            container.start()
            
            # Set a timeout for the entire container operation
            start_time = time.time()
            
            # Stream logs with timeout handling
            while time.time() - start_time < run_timeout:
                # Check if container is still running
                try:
                    container.reload()
                    if container.status != 'running':
                        # Container finished naturally
                        break
                except Exception as e:
                    logger.warning(f"Error checking container status: {e}")
                    break
                    
                # Brief sleep to avoid hammering the Docker API
                time.sleep(1)
            
            # Get final status - either it completed or timed out
            try:
                container.reload()
                logs = container.logs().decode('utf-8', errors='replace')
                
                # If we're here after timeout, container didn't finish - force stop
                if time.time() - start_time >= run_timeout:
                    logger.warning(f"Container timed out after {run_timeout}s, stopping")
                    container.stop(timeout=10)
                    success = False
                    logs += "\n\nERROR: Container execution timed out"
                else:
                    # Container finished, check exit code
                    exit_code = container.attrs['State']['ExitCode']
                    success = exit_code == 0
                    logger.info(f"Container exited with code {exit_code}")
                
                # Format the result
                result = f"Build logs:\n{''.join(build_logs)}\n\nContainer logs:\n{logs}"
                return success, result
                
            except Exception as e:
                logger.error(f"Error getting container results: {e}")
                return False, f"Error getting container results: {str(e)}\n\nBuild logs:\n{''.join(build_logs)}"
                
        except docker.errors.APIError as e:
            logger.error(f"Docker API error during container run: {str(e)}")
            return False, f"Docker run error: {str(e)}\n\nBuild logs:\n{''.join(build_logs)}"
            
        except Exception as e:
            logger.error(f"Unexpected error during container execution: {str(e)}")
            return False, f"Unexpected run error: {str(e)}\n\nBuild logs:\n{''.join(build_logs)}"
            
    except Exception as e:
        logger.error(f"Docker operation failed: {str(e)}")
        return False, f"Docker operation failed: {str(e)}"
        
    finally:
        # Clean up resources
        try:
            # Use try/except for each cleanup step to ensure we attempt all cleanup
            if container_id:
                try:
                    logger.info(f"Removing container: {container_id}")
                    client.containers.get(container_id).remove(force=True)
                except Exception as e:
                    # Just log the error but continue cleanup
                    logger.warning(f"Error removing container (may already be removed): {e}")
            
            if image_id and client:
                try:
                    logger.info(f"Removing image: {image_id}")
                    client.images.remove(image_id, force=True)
                except Exception as e:
                    logger.warning(f"Error removing image: {e}")
            
            if temp_dir and os.path.exists(temp_dir):
                try:
                    logger.info(f"Removing temporary directory: {temp_dir}")
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Error removing temporary directory: {e}")
                    
        except Exception as e:
            logger.warning(f"Error during Docker cleanup: {e}")

def maintainer_agent_response_docker(repo_dir, issue_data, conversation_history, system_prompt_template):
    """Generate a Docker-aware response from the maintainer agent."""
    # Extract the user's question
    latest_user_message = ""
    for message in reversed(conversation_history):
        if message['role'] == "user":
            latest_user_message = message['content']
            break
    
    # Create Docker-specific system prompt
    docker_system_prompt = system_prompt_template + """
    This is a Docker-related issue. You can:
    1. Explore the repository
    2. Suggest modifications to the Dockerfile
    3. Provide Docker commands to solve the issue
    4. Create or modify additional files needed for Docker builds
    
    Format file creation/modifications as:
    CREATE_FILE[filename]:
    file content
    END_FILE
    
    Format Dockerfile modifications as:
    MODIFY_DOCKERFILE:
    # modified content
    END_DOCKERFILE
    """
    
    # Create the user prompt
    user_prompt = f"""
    Original question: {issue_data['first_question']['title']}
    
    Conversation history:
    {formatted_conversation_history(conversation_history)}
    
    Dockerfile:
    {issue_data.get('dockerfile', 'No Dockerfile provided')}
    
    Latest user message: {latest_user_message}
    
    Please respond to the user's Docker-related issue with specific solutions.
    """
    
    # Extract the issue_id for consistent tracking
    issue_id = issue_data.get("id", "unknown")
    
    # Get the maintainer's response - use Haiku model
    response = call_llm(user_prompt, docker_system_prompt, "maintainer", issue_id, model=MAINTAINER)
    
    # Process file creation/modifications
    extra_files = {}
    modified_dockerfile = None
    
    # Extract CREATE_FILE blocks
    file_matches = re.finditer(r'CREATE_FILE\\$\\$(.+?)\\$\\$:(.*?)END_FILE', response, re.DOTALL)
    for match in file_matches:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        extra_files[filename] = content
    
    # Extract MODIFY_DOCKERFILE block
    dockerfile_match = re.search(r'MODIFY_DOCKERFILE:(.*?)END_DOCKERFILE', response, re.DOTALL)
    if dockerfile_match:
        modified_dockerfile = dockerfile_match.group(1).strip()
    
    # Clean up the response (remove the special formatting)
    cleaned_response = re.sub(r'CREATE_FILE\\$\\$(.+?)\\$\\$:(.*?)END_FILE', r'I have created a file named \1 with the necessary content.', response, flags=re.DOTALL)
    cleaned_response = re.sub(r'MODIFY_DOCKERFILE:(.*?)END_DOCKERFILE', r'I have modified the Dockerfile with the necessary changes.', cleaned_response, flags=re.DOTALL)
    
    return cleaned_response, extra_files, modified_dockerfile

def validate_docker_solution(issue_data, test_commands=None):
    """Validate a Docker solution by building and testing the Dockerfile."""
    client = None
    temp_dir = None
    image_id = None
    
    try:
        # Setup Docker client
        client = docker.from_env()
        
        # Test Docker client connection
        try:
            client.ping()
        except Exception as e:
            return False, f"Docker client connection error: {str(e)}"
        
        # Create temporary directory for Docker context
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created Docker build context at: {temp_dir}")
        
        # Write Dockerfile
        dockerfile_path = os.path.join(temp_dir, 'Dockerfile')
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(issue_data['dockerfile'])
        logger.info(f"Written Dockerfile ({len(issue_data['dockerfile'])} bytes)")
        
        # Add any extra files needed for the build
        if 'extra_files' in issue_data and issue_data['extra_files']:
            for file_path, content in issue_data['extra_files'].items():
                success = write_file_in_docker_context(temp_dir, file_path, content)
                if not success:
                    return False, f"Failed to create required file: {file_path}"
        
        # Step 1: Build the Docker image to validate Dockerfile syntax
        logger.info("Building Docker image to validate Dockerfile...")
        try:
            image, build_logs = client.images.build(
                path=temp_dir,
                rm=True,
                forcerm=True,
                timeout=900
            )
            image_id = image.id
            logger.info(f"Docker image built successfully: {image_id}")
        except Exception as e:
            logger.error(f"Docker build failed: {str(e)}")
            return False, f"Docker build failed: {str(e)}"
        
        # Step 2: Run a basic test to verify the container starts
        logger.info("Running basic test to verify container starts...")
        try:
            # Run with a simple command to verify container starts
            result = client.containers.run(
                image.id,
                command="echo 'Container starts successfully'",
                remove=True,
                timeout=60
            )
            logger.info("Basic container test succeeded")
        except Exception as e:
            logger.error(f"Container startup test failed: {str(e)}")
            return False, f"Container startup test failed: {str(e)}"
        
        # Step 3: Run additional test commands on the host using the built image
        test_results = []
        if test_commands:
            logger.info(f"Running {len(test_commands)} test commands...")
            
            for i, cmd in enumerate(test_commands):
                try:
                    # Skip docker build/run commands that would create new containers
                    if cmd.startswith(("docker build", "docker run")):
                        test_results.append(f"Skipping Docker command: {cmd}")
                        continue
                    
                    # Form the docker run command to execute test inside container
                    # Use bash to interpret the command
                    container_cmd = f"bash -c '{cmd}'"
                    logger.info(f"Running test {i+1}: {container_cmd}")
                    
                    output = client.containers.run(
                        image.id,
                        command=container_cmd,
                        remove=True,
                        timeout=600
                    )
                    output_text = output.decode('utf-8', errors='replace')
                    test_results.append(f"Test {i+1} passed: {cmd}\nOutput: {output_text}")
                    logger.info(f"Test {i+1} succeeded")
                except Exception as e:
                    error_msg = f"Test {i+1} failed: {cmd}\nError: {str(e)}"
                    test_results.append(error_msg)
                    logger.error(f"Test {i+1} failed: {str(e)}")
                    return False, "\n".join(test_results)
            
            logger.info("All tests passed successfully")
        
        # If we get here, everything succeeded
        return True, "\n".join(test_results) if test_results else "Docker validation succeeded"
        
    except Exception as e:
        logger.error(f"Docker validation failed: {str(e)}")
        return False, f"Docker validation failed: {str(e)}"
        
    finally:
        # Clean up resources
        try:
            if image_id and client:
                logger.info(f"Removing image: {image_id}")
                try:
                    client.images.remove(image_id, force=True)
                except Exception as e:
                    logger.warning(f"Error removing image: {e}")
            
            if temp_dir and os.path.exists(temp_dir):
                logger.info(f"Removing temporary directory: {temp_dir}")
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Error removing temporary directory: {e}")
        except Exception as e:
            logger.warning(f"Error during Docker cleanup: {e}")

def generate_test_commands(issue_data, maintainer_response, exploration_results=None):
    """Generate test commands based on maintainer's response and exploration results."""
    
    # Extract dockerfile content
    dockerfile = issue_data.get('dockerfile', '')
    
    # Create a prompt that includes exploration results
    docker_context = ""
    if exploration_results:
        docker_context = f"""
        EXPLORATION RESULTS:
        The following information was gathered during repository exploration in a temporary directory.
        IMPORTANT: These results show the repository structure, but paths will be DIFFERENT inside the Docker container.
        Use this information to understand the codebase, but adapt paths according to the Dockerfile context.
        
        {exploration_results}
        """
    
    system_prompt = f"""
    You are helping to generate test commands to verify the solution to a user's Docker issue.
    
    Based on the user's issue description, the maintainer's response, and the exploration results,
    generate a series of commands that will verify if the solution works as expected.
    
    IMPORTANT: Generate commands that will run INSIDE the Docker container.
    DO NOT include 'docker' commands as these will be executed inside the container.
    
    {docker_context}
    
    Carefully analyze the Dockerfile:
    ```
    {dockerfile}
    ```
    
    Based on the Dockerfile above:
    1. Only reference paths and directories that definitely exist in the container
    2. Only use commands that would be available in the container
    3. Check for critical files or services mentioned in the issue
    
    Good commands:
    - Command-line tests that verify the application works
    - File existence checks (e.g., `test -f /path/to/file` but ONLY for files you know exist)
    - Service checks (e.g., `curl localhost:8080` but only if the container exposes this port)
    - Configuration validation
    
    Format your response as a JSON array of commands.
    """
    
    user_prompt = f"""
    Maintainer's response:
    {maintainer_response}
    
    Dockerfile content:
    {dockerfile}
    
    Generate test commands that will verify the maintainer's response works correctly.
    These commands will run INSIDE the Docker container.
    
    REMEMBER: Only reference paths and resources that will definitely exist in the container. Also, only generate the minimal number of commands needed to verify the solution.
    
    Return ONLY a JSON array of commands.
    """
    
    # Extract issue_id for consistent tracking
    issue_id = issue_data.get("id", "unknown")
    
    # Call LLM to generate test commands
    response = call_llm(user_prompt, system_prompt, "maintainer", issue_id, model=MAINTAINER)
    
    # Parse the JSON response (keeping your existing parsing logic)
    try:
        start_idx = response.find('[')
        end_idx = response.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = response[start_idx:end_idx+1]
            commands = json.loads(json_str)
            return commands if isinstance(commands, list) else []
        else:
            logger.error("Could not find JSON array in response")
            return []
    except json.JSONDecodeError:
        logger.error("Failed to parse test commands from LLM response")
        return []

def parse_repo_name(repo_url):
    # For non-GitHub URLs, split by '/' and get the repository name
    parts = repo_url.split('/')
    if len(parts) >= 5:
        return '/'.join(parts[:5])
    else:
        return '/'.join(parts)

def clone_repo(repo_url, commit_hash, max_retries=5):
    """Clone repository with efficient fetching of a specific commit and retry logic."""
    temp_dir = tempfile.mkdtemp()
    logger.info(f"Created temporary directory: {temp_dir}")
    
    # Extract repo name from URL
    repo_name = parse_repo_name(repo_url)
    logger.info(f"Cloning repository: {repo_name}")
    
    for attempt in range(max_retries + 1):  # +1 because we're counting from 0
        try:
            # Clone with depth=1 first to make it faster
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries} for cloning {repo_name}")
                
            # Clean up previous failed attempt if needed
            if attempt > 0 and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    os.makedirs(temp_dir, exist_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to clean up directory between attempts: {e}")
                    temp_dir = tempfile.mkdtemp()  # Create a new temp dir if cleanup fails
            
            logger.info(f"Initial shallow clone of {repo_name} (attempt {attempt+1}/{max_retries+1})")
            clone_result = subprocess.run(
                ["git", "clone", "--quiet", "--depth=1", repo_name, temp_dir],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300  # 5 minute timeout for cloning
            )

            # Fetch the specific commit
            logger.info(f"Fetching specific commit: {commit_hash}")
            fetch_result = subprocess.run(
                ["git", "fetch", "--quiet", "--depth=1", "origin", commit_hash],
                cwd=temp_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300  # 5 minute timeout for fetching
            )

            # Checkout the commit
            logger.info(f"Checking out commit: {commit_hash}")
            checkout_result = subprocess.run(
                ["git", "checkout", "--quiet", commit_hash],
                cwd=temp_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60  # 1 minute timeout for checkout
            )
            
            logger.info(f"Successfully cloned repository at commit {commit_hash}")
            return temp_dir
            
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Timeout during git operation (attempt {attempt+1}/{max_retries+1}): {e}")
            if attempt == max_retries:
                logger.error(f"Failed to clone repository after {max_retries+1} attempts due to timeouts")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return None
                
        except subprocess.SubprocessError as e:
            # Get stderr if available for better error reporting
            stderr = e.stderr.decode('utf-8', errors='replace') if hasattr(e, 'stderr') and e.stderr else str(e)
            logger.warning(f"Git operation failed (attempt {attempt+1}/{max_retries+1}): {stderr}")
            
            # Check for specific errors that might be temporary
            if "could not resolve host" in stderr.lower() or "connection timed out" in stderr.lower() or "temporarily unavailable" in stderr.lower():
                if attempt == max_retries:
                    logger.error(f"Failed to clone repository after {max_retries+1} attempts: {stderr}")
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    return None
                    
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Waiting {wait_time:.2f}s before retry...")
                time.sleep(wait_time)
            else:
                # Permanent error, no need to retry
                logger.error(f"Failed to clone repository (permanent error): {stderr}")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error during repository cloning: {str(e)}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return None
    
    # Should never reach here due to the returns in the loop, but just in case
    logger.error("Failed to clone repository: retry loop exited unexpectedly")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    return None

def read_file(repo_dir, file_path):
    """Read the entire file."""
    try:
        full_path = os.path.join(repo_dir, file_path)
        logger.info(f"Reading file: {file_path}")
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        logger.info(f"Successfully read file ({len(content)} bytes)")
        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"Error reading file: {e}"

def read_file_lines(repo_dir, file_path, start_line, end_line):
    """Read specific lines from a file."""
    try:
        full_path = os.path.join(repo_dir, file_path)
        logger.info(f"Reading lines {start_line} to {end_line} from file: {file_path}")
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        # Convert to 0-based indexing and ensure within bounds
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        
        result = ''.join(lines[start_idx:end_idx])
        logger.info(f"Successfully read {end_idx - start_idx} lines from file")
        return result
    except Exception as e:
        logger.error(f"Error reading lines from file {file_path}: {e}")
        return f"Error reading file lines: {e}"

def list_directory(repo_dir, dir_path='.'):
    """List contents of a directory."""
    try:
        full_path = os.path.join(repo_dir, dir_path)
        logger.info(f"Listing directory: {dir_path}")
        contents = os.listdir(full_path)
        logger.info(f"Found {len(contents)} items in directory")
        return '\n'.join(contents)
    except Exception as e:
        logger.error(f"Error listing directory {dir_path}: {e}")
        return f"Error listing directory: {e}"

def find_files(repo_dir, pattern):
    """Find files matching a pattern."""
    try:
        logger.info(f"Finding files matching pattern: {pattern}")
        result = subprocess.run(
            ['find', '.', '-type', 'f', '-name', pattern],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        files_found = result.stdout.strip().split('\n') if result.stdout.strip() else []
        logger.info(f"Found {len(files_found)} files matching pattern")
        return result.stdout
    except subprocess.SubprocessError as e:
        logger.error(f"Error finding files with pattern {pattern}: {e}")
        return f"Error finding files: {e}"

def execute_command(repo_dir, command, timeout=60):
    """
    Execute a command in the repository directory with a timeout.
    Terminates after specified timeout (default: 60 seconds).
    """
    try:
        logger.info(f"Executing command: {command}")
        start_time = time.time()
        
        # Run process with timeout
        try:
            result = subprocess.run(
                command,
                cwd=repo_dir,
                capture_output=True,
                text=False,  # Changed to False to get bytes instead of text
                shell=True,
                timeout=timeout
            )
            
            elapsed_time = time.time() - start_time
            
            # Handle stdout and stderr as bytes and decode with error handling
            stdout_bytes = result.stdout if result.stdout else b''
            stderr_bytes = result.stderr if result.stderr else b''
            
            # Try to decode with UTF-8 first, then fall back to other encodings with error replacement
            try:
                stdout_text = stdout_bytes.decode('utf-8', errors='replace')
            except:
                # If still failing, use latin-1 which can decode any byte sequence
                stdout_text = stdout_bytes.decode('latin-1')
                
            try:
                stderr_text = stderr_bytes.decode('utf-8', errors='replace')
            except:
                stderr_text = stderr_bytes.decode('latin-1')
            
            # Count lines for logging
            stdout_lines = stdout_text.strip().split('\n') if stdout_text.strip() else []
            stderr_lines = stderr_text.strip().split('\n') if stderr_text.strip() else []
            
            logger.info(f"Command executed in {elapsed_time:.2f}s. "
                      f"STDOUT: {len(stdout_lines)} lines, STDERR: {len(stderr_lines)} lines")
            
            # Log stderr if it exists
            if stderr_lines:
                logger.warning(f"Command stderr: {stderr_text[:200]}{'...' if len(stderr_text) > 200 else ''}")
            
            return f"STDOUT:\n{stdout_text}\n\nSTDERR:\n{stderr_text}"
            
        except subprocess.TimeoutExpired:
            # Handle timeout
            elapsed_time = time.time() - start_time
            logger.warning(f"Command timed out after {elapsed_time:.2f}s: {command}")
            return f"ERROR: Command timed out after {timeout} seconds"
            
    except subprocess.SubprocessError as e:
        # Try to decode stderr with error handling
        stderr = ""
        if hasattr(e, 'stderr') and e.stderr:
            try:
                stderr = e.stderr.decode('utf-8', errors='replace')
            except:
                stderr = e.stderr.decode('latin-1')
        
        logger.error(f"Error executing command '{command}': {stderr or str(e)}")
        return f"Error executing command: {stderr or str(e)}"

def interactive_exploration(repo_dir, question, system_prompt_template, max_iterations=5, command_timeout=300, overall_timeout=600, issue_id="unknown"):
    """Interactively explore the repository to answer the question with timeouts, continuing after input too long errors."""
    conversation_history = []
    exploration_results_all = ""
    
    logger.info(f"Starting interactive exploration with max {max_iterations} iterations (overall timeout: {overall_timeout}s)")
    
    # Track overall exploration start time
    exploration_start_time = time.time()
    
    # Initial exploration
    initial_system_prompt = system_prompt_template + """
    First, assess the question and determine what files or code areas would be most relevant to explore.
    Respond with specific exploration commands that should be run to gather information.
    Format your response with exploration commands clearly labeled as:
    EXPLORE: <command to run>
    """
    
    initial_user_prompt = f"Question: {question}\n\nPlease help me understand this code issue."
    
    # Keep track of the current exploration context that we send to the LLM
    current_exploration_context = ""
    truncated_mode = False  # Flag to indicate we're operating in truncated mode
    
    # Estimate approx 4 chars per token, target ~150K tokens to leave room for system prompt
    max_token_estimate = 150000
    max_context_size = max_token_estimate * 4  # ~600K characters
    
    for iteration in range(max_iterations):
        # Check if overall timeout is approaching
        if time.time() - exploration_start_time > overall_timeout:
            logger.warning(f"Overall exploration timeout ({overall_timeout}s) reached after {iteration} iterations")
            exploration_results_all += f"\n--- TIMEOUT REACHED AFTER {iteration} ITERATIONS ---\n"
            break
            
        logger.info(f"Starting exploration iteration {iteration+1}/{max_iterations}")
        
        # Update the system prompt based on iteration
        if iteration == 0:
            system_prompt = initial_system_prompt
            user_prompt = initial_user_prompt
        else:
            system_prompt = system_prompt_template + """
            Based on the information gathered so far, continue exploring the repository to better understand the issue.
            You can request additional files, search for specific patterns, or examine other areas of the codebase.
            Format your exploration commands clearly as:
            EXPLORE: <command to run>
            
            If you believe you have enough information to answer the question fully, begin your response with:
            ANSWER: <comprehensive answer to the user's question>
            """
            
            # For subsequent iterations, include the exploration results
            user_prompt = f"Question: {question}\n\nExploration results so far:\n{current_exploration_context}\n\n"
            
            # Add info if we're in truncated mode
            if truncated_mode:
                user_prompt += "NOTE: Some earlier exploration results have been truncated due to context length limitations. Focus on the most recent results above.\n\n"
                
            user_prompt += "Please continue exploring or provide an answer."
        
        # Check if we're too close to overall timeout to start a new iteration
        remaining_time = overall_timeout - (time.time() - exploration_start_time)
        if remaining_time < 30:  # Allow 30s buffer for LLM call
            logger.warning("Too close to overall timeout to start new iteration with LLM. Generating response with current information.")
            break
            
        # Get model's exploration plan
        logger.info("Requesting exploration plan from LLM")
        try:
            # Use Haiku model for exploration
            exploration_plan = call_llm(user_prompt, system_prompt, "maintainer", issue_id, model=MAINTAINER)
            
            # Check for input too long error - this is a terminal error
            if exploration_plan == "ERROR_INPUT_TOO_LONG":
                logger.warning("Input too long error encountered. Stopping exploration and using existing results.")
                exploration_results_all += "\n--- EXPLORATION STOPPED: Input too long error ---\n"
                break  # Stop exploration and proceed to final answer generation
            
            # Successfully got an exploration plan
            conversation_history.append({"role": "assistant", "content": exploration_plan})
            logger.info(f"Received exploration plan ({len(exploration_plan)} chars)")
        except Exception as e:
            # LLM API errors are considered terminal
            logger.error(f"Error getting exploration plan from LLM: {e}")
            exploration_results_all += f"\n--- ERROR IN ITERATION {iteration+1} GETTING EXPLORATION PLAN ---\n{str(e)}\n"
            break  # Stop exploration and proceed to final answer generation
        
        # Extract exploration commands
        exploration_results = ""
        if "EXPLORE:" in exploration_plan:
            commands = [line.split("EXPLORE: ", 1)[1].strip() for line in exploration_plan.split('\n') 
                      if line.strip().startswith("EXPLORE:")]
            
            logger.info(f"Extracted {len(commands)} exploration commands")
            
            # Set a timeout for this iteration's exploration (not overall timeout)
            iteration_start_time = time.time()
            iteration_timeout = min(overall_timeout - (time.time() - exploration_start_time), 300)  # 5 min per iteration
            
            for i, cmd in enumerate(commands):
                # Check if we're close to iteration timeout before starting a new command
                remaining_iteration_time = iteration_timeout - (time.time() - iteration_start_time)
                if remaining_iteration_time < command_timeout:
                    logger.warning(f"Only {remaining_iteration_time:.1f}s left of iteration timeout. Skipping remaining commands.")
                    exploration_results += "NOTICE: Some commands were skipped due to approaching iteration timeout.\n\n"
                    break
                
                # Execute the command with error handling
                try:
                    logger.info(f"Executing command {i+1}/{len(commands)}: {cmd}")
                    result = execute_command(repo_dir, cmd, timeout=command_timeout)
                    exploration_results += f"Command: {cmd}\nResult:\n{result}\n\n"
                except Exception as e:
                    # Individual command execution errors are non-terminal
                    # Log the error and continue with next command
                    error_msg = f"Error executing command: {cmd}\nError: {str(e)}\n\n"
                    logger.error(f"Command execution error: {str(e)}")
                    exploration_results += error_msg
                    # Continue with next command - don't break the loop
                
                # Check if we've exceeded the iteration timeout
                if time.time() - iteration_start_time > iteration_timeout:
                    logger.warning(f"Iteration timeout ({iteration_timeout:.1f}s) reached after {i+1}/{len(commands)} commands")
                    exploration_results += f"NOTICE: Iteration timeout reached after {i+1}/{len(commands)} commands.\n\n"
                    break
        
        # Add this iteration's results to the full exploration history
        exploration_results_all += f"\n--- ITERATION {iteration+1} ---\n{exploration_results}"
        
        # Check if adding new results would exceed context size limit
        new_context = current_exploration_context + f"\n--- ITERATION {iteration+1} ---\n{exploration_results}"
        
        if len(new_context) > max_context_size:
            logger.warning(f"Exploration context would exceed size limit ({len(new_context)} chars / ~{len(new_context)//4} tokens). Stopping exploration.")
            
            # DO NOT add this iteration's results to context since it would exceed the limit
            # Instead, add a note explaining why we're stopping
            exploration_results_all += "\n--- EXPLORATION STOPPED: Context size limit would be exceeded ---\n"
            
            # Break out of the exploration loop without updating current_exploration_context
            logger.info("Breaking out of exploration loop due to context size limit")
            break
        else:
            # If within limits, update the current context
            current_exploration_context = new_context
            
        # Check if we have an answer
        if "ANSWER:" in exploration_plan:
            logger.info("Found ANSWER section in exploration plan. Extracting answer.")
            answer_part = exploration_plan.split("ANSWER:", 1)[1].strip()
            return answer_part, conversation_history, exploration_results_all
    
    # If we've gone through all iterations without an answer, generate a final answer using the gathered information
    logger.info("Maximum iterations reached or exploration stopped. Generating final answer.")
    final_system_prompt = system_prompt_template + """
    Based on all the exploration done so far, please provide a comprehensive answer to the user's question.
    Use all relevant information gathered during the exploration to formulate your response.
    """
    
    final_user_prompt = f"""
    Question: {question}
    
    Exploration results:
    {current_exploration_context}
    
    Please provide a comprehensive answer based on the exploration results above.
    """
    
    try:
        final_answer = call_llm(final_user_prompt, final_system_prompt, "maintainer", issue_id, model=MAINTAINER)
        if final_answer == "ERROR_INPUT_TOO_LONG":
            logger.warning("Input too long error in final answer generation. Creating abbreviated answer.")
            # Create a simpler prompt with just the question and a summary note
            simple_prompt = f"""
            Question: {question}
            
            Note: Extensive exploration was conducted, but the context became too large for a detailed response.
            Summarize what could be relevant to answering this question based on your knowledge:
            1. Key files or code patterns typically involved in this type of issue
            2. Common solutions to similar problems
            3. Important considerations the user should be aware of
            """
            final_answer = call_llm(simple_prompt, final_system_prompt, "maintainer", issue_id, model=MAINTAINER)
            if final_answer == "ERROR_INPUT_TOO_LONG":
                # If still failing, return a generic response
                final_answer = "After extensive repository exploration, I was unable to generate a complete answer due to context size limitations. I recommend breaking down this question into smaller, more specific queries."
        
        return final_answer, conversation_history, exploration_results_all
    except Exception as e:
        logger.error(f"Error generating final answer: {e}")
        # Return a useful answer based on what we learned so far
        fallback_answer = f"Based on the exploration conducted, I can provide the following information. Note that the full analysis was interrupted due to an error: {str(e)}. Here's what I found: {current_exploration_context[:2000]}..."
        return fallback_answer, conversation_history, exploration_results_all

def judge_maintainer_answer(issue_data, maintainer_answer, docker_results=None):
    """Judge the maintainer's answer correctness based on the original conversation."""
    logger.info("Activating judge agent to evaluate maintainer's answer")
    
    # Extract issue ID for logging
    issue_id = issue_data.get("id", "unknown")
    
    # Extract relevant information from the issue data
    question_title = issue_data["first_question"]["title"]
    question_body = issue_data["first_question"]["body"]
    comments = issue_data.get("comments", [])
    user_satisfaction_conditions = issue_data.get("user_satisfaction_condition", [])
    
    # Format the original conversation for better readability
    conversation = f"Title: {question_title}\n\nQuestion: {question_body}\n\n"
    conversation += "--- Comments from maintainers and users ---\n"
    
    for i, comment in enumerate(comments):
        conversation += f"[{comment['user']}]:\n{comment['body']}\n\n"
    
    # Include Docker results if available - Make this more prominent
    docker_info = ""
    if docker_results:
        success_status = docker_results.get('success', False)
        docker_info = f"""
        MAINTAINER ANSWER VALIDATION RESULTS via DOCKER:
        Status: {success_status}
        Logs:
        {docker_results.get('logs', 'No logs available')}
        """
    
    system_prompt = """
    You are a judge evaluating the maintainer's answer to a user's technical question.
    
    Your task is to determine if the maintainer's answer is:
    1. TECHNICALLY CORRECT - The solution must be highly accurate with minimal to no errors
    2. SATISFIES USER CONDITIONS - The answer addresses all the user's specific conditions
    3. APPROPRIATE VERBOSITY - Whether the answer contains only what's necessary or includes excessive information
    
    IMPORTANT: For Docker-related issues, a solution is ONLY considered correct if:
    1. The maintainer's explanation is technically sound AND
    2. The Docker build and test process actually succeeds (check the DOCKER VALIDATION RESULTS)
    
    If the Docker validation shows "Success: False", then the maintainer's answer CANNOT be considered correct,
    regardless of how good the explanation seems. Docker build success is mandatory for Docker issues.
    
    Provide your evaluation in the following format:
    
    TECHNICAL CORRECTNESS: [CORRECT/PARTIALLY CORRECT/INCORRECT]
    - CORRECT: The solution is completely accurate
    - PARTIALLY CORRECT: The core solution works but has minor technical issues that wouldn't prevent implementation
    - INCORRECT: The solution has significant errors, misconceptions, or would fail if implemented
    
    ALIGNMENT SCORE: X/Y CONDITIONS MET (Z%)
    
    CONDITION 1: [TRUE/FALSE] <brief description of condition>
    CONDITION 2: [TRUE/FALSE] <brief description of condition>
    ...and so on for each condition
    
    VERBOSITY ASSESSMENT: [CONCISE/APPROPRIATE/VERBOSE]
    - CONCISE: The answer lacks some potentially helpful context or details
    - APPROPRIATE: The answer contains just the right amount of information
    - VERBOSE: The answer contains unnecessary information beyond what the user requested
    
    VERDICT: [CORRECT/PARTIALLY CORRECT/INCORRECT] 
    You must provide exactly one of these three verdicts based ONLY on technical correctness AND alignment (NOT verbosity):
    - CORRECT: The answer is technically correct with no significant errors AND meets ALL user conditions
    - PARTIALLY CORRECT: The answer has only minor technical issues but meets SOME conditions, OR meets ALL conditions but has minor technical issues
    - INCORRECT: The answer has significant technical flaws OR fails to meet ANY conditions OR Docker validation failed
    
    KEY ISSUES: List ALL issues with the maintainer's answer, including even minor technical inaccuracies
    
    REASONING: Detailed explanation of your verdict, addressing both technical correctness and alignment with user conditions.
    
    Be thorough in your technical assessment. Any non-trivial error should be noted and count against the maintainer's answer.
    """
    
    # Create the judge user prompt with clear reference to the conversation containing reference code
    user_prompt = f"""
USER'S QUESTION AND REFERENCE CONVERSATION:
{conversation}

IMPORTANT: The reference conversation above contains the correct/accepted solution provided by the original maintainer(s). Use this as the authoritative baseline to judge the technical correctness of the maintainer's answer. The maintainer's answer should be consistent with the approaches, suggestions, and code provided in this reference conversation.

USER SATISFACTION CONDITIONS:
{json.dumps(user_satisfaction_conditions, indent=2)}

MAINTAINER'S ANSWER TO EVALUATE:
{maintainer_answer}

{docker_info}

Based on the above information:
1. Compare the maintainer's answer against the reference conversation to assess technical accuracy
2. Evaluate the TECHNICAL CORRECTNESS of the maintainer's answer
3. Determine how well the answer satisfies each user condition
4. Assess the verbosity of the answer (whether it contains unnecessary information)
5. Provide your final VERDICT considering technical correctness and alignment (but NOT verbosity)

For each condition, determine if it is TRUE (fully satisfied) or FALSE (not satisfied).

IMPORTANT GUIDELINES:
- Consider the original maintainer's solution in the reference conversation as a strong reference point
- Be rigorous but fair in your technical assessment
- For PARTIALLY CORRECT technical rating, the core solution must work but might have minor issues
- For CORRECT technical rating, the solution must match the intent and approach of the reference solution
- If this is a Docker-related issue and the Docker validation shows "Success: False", the solution is automatically incorrect
- The verbosity assessment should not affect your final verdict, but should be noted separately
"""
    
    # Get the judge's evaluation
    logger.info("Requesting evaluation from judge agent")
    evaluation = call_llm(user_prompt, system_prompt, "judge", issue_id)
    logger.info(f"Judge evaluation complete ({len(evaluation)} chars)")
    
    # Extract the alignment score
    alignment_score = {}
    if "ALIGNMENT SCORE:" in evaluation:
        try:
            # Extract the alignment score section
            alignment_section = evaluation.split("ALIGNMENT SCORE:", 1)[1]
            
            # Extract the summary score line (X/Y CONDITIONS MET (Z%))
            score_line = alignment_section.split("\n", 1)[0].strip()
            score_match = re.search(r'(\d+)/(\d+)', score_line)
            if score_match:
                satisfied = int(score_match.group(1))
                total = int(score_match.group(2))
                
                alignment_score = {
                    'satisfied': satisfied,
                    'total': total,
                    'percentage': (satisfied / total) * 100 if total > 0 else 0,
                    'conditions': []
                }
                
                # More robust parsing for conditions using string matching
                conditions_section = alignment_section
                lines = conditions_section.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith("CONDITION"):
                        condition_num_match = re.search(r'CONDITION (\d+):', line)
                        if condition_num_match:
                            condition_num = int(condition_num_match.group(1))
                            
                            # More flexible matching for TRUE/FALSE using string contains
                            is_satisfied = False
                            if "FALSE" in line.upper() or "NOT SATISFIED" in line.upper() or "NOT MET" in line.upper() or  "NOT_SATISFIED" in line.upper() or "NOT_MET" in line.upper():
                                is_satisfied = False
                            elif "TRUE" in line.upper() or "SATISFIED" in line.upper() or "MET" in line.upper():
                                is_satisfied = True
                            
                            # Extract description - everything after the status
                            description = line
                            # Remove the "CONDITION X:" part
                            if ":" in description:
                                description = description.split(":", 1)[1].strip()
                            # Remove any [TRUE]/[FALSE] or similar markers
                            description = re.sub(r'$$(TRUE|FALSE|SATISFIED|NOT SATISFIED|MET|NOT MET)$$', '', description, flags=re.IGNORECASE).strip()
                            
                            alignment_score['conditions'].append({
                                'number': condition_num,
                                'satisfied': is_satisfied,
                                'description': description
                            })
        except Exception as e:
            logger.error(f"Error parsing alignment score: {e}")
    
    # Extract technical correctness with more robust parsing
    technical_correctness = "UNKNOWN"
    if "TECHNICAL CORRECTNESS:" in evaluation:
        tech_section = evaluation.split("TECHNICAL CORRECTNESS:", 1)[1].strip()
        tech_line = tech_section.split("\n", 1)[0].strip()
        
        if "INCORRECT" in tech_line.upper():
            technical_correctness = "INCORRECT"
        elif "PARTIALLY" in tech_line.upper():
            technical_correctness = "PARTIALLY CORRECT"
        elif "CORRECT" in tech_line.upper() and "PARTIALLY" not in tech_line.upper():
            technical_correctness = "CORRECT"
    
    # Extract verbosity assessment with more robust parsing
    verbosity = "UNKNOWN"
    if "VERBOSITY ASSESSMENT:" in evaluation:
        verbosity_section = evaluation.split("VERBOSITY ASSESSMENT:", 1)[1].strip()
        verbosity_line = verbosity_section.split("\n", 1)[0].strip()
        
        if "CONCISE" in verbosity_line.upper():
            verbosity = "CONCISE"
        elif "APPROPRIATE" in verbosity_line.upper():
            verbosity = "APPROPRIATE"
        elif "VERBOSE" in verbosity_line.upper():
            verbosity = "VERBOSE"
    
    # Extract verdict with more robust parsing
    verdict = "UNKNOWN"
    if "VERDICT:" in evaluation:
        verdict_section = evaluation.split("VERDICT:", 1)[1].strip()
        verdict_line = verdict_section.split("\n", 1)[0].strip()
        
        if "INCORRECT" in verdict_line.upper():
            verdict = "INCORRECT"
        elif "PARTIALLY" in verdict_line.upper():
            verdict = "PARTIALLY CORRECT"
        elif "CORRECT" in verdict_line.upper() and "PARTIALLY" not in verdict_line.upper():
            verdict = "CORRECT"
    
    # Extract key issues
    key_issues = []
    if "KEY ISSUES:" in evaluation:
        key_issues_section = evaluation.split("KEY ISSUES:", 1)[1]
        
        # Get the text up to the next major section if there is one
        if "REASONING:" in key_issues_section:
            key_issues_section = key_issues_section.split("REASONING:", 1)[0]
            
        # Split by newlines and clean up
        for line in key_issues_section.strip().split("\n"):
            clean_line = line.strip()
            if clean_line and not clean_line.startswith("KEY ISSUES:"):
                # Remove bullet points if present
                if clean_line.startswith("- "):
                    clean_line = clean_line[2:]
                key_issues.append(clean_line)
    
    # If Docker build failed, ensure "INCORRECT" verdict regardless of other factors
    if docker_results is not None and not docker_results.get('success', False):
        verdict = "INCORRECT"
        technical_correctness = "INCORRECT"  # Also update technical correctness
        if "Docker validation failed" not in key_issues:
            key_issues.append("Docker validation failed - build or tests did not succeed")
    
    # Add technical correctness and verbosity to the alignment score
    if alignment_score:
        alignment_score['technical_correctness'] = technical_correctness
        alignment_score['verbosity'] = verbosity
    
    judgment = evaluation
    
    return judgment, verdict, key_issues, alignment_score

# --- User Style Extraction Functions --- #

def load_comment_pairs(file_path):
    """Load the comment pairs from the merged JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return {}

def load_jsonl_data(file_paths):
    """Load data from multiple JSONL files."""
    data = []
    for file_path in file_paths:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    line = line[line.find('{'):line.rfind('}')+1]

                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return data

def create_bm25_index(documents):
    """Create BM25 index from documents."""
    # Tokenize documents
    tokenized_docs = [doc.lower().split() for doc in documents]
    return BM25Okapi(tokenized_docs)

def preprocess_text(text):
    """Basic text preprocessing."""
    # Convert to lowercase and remove special characters
    text = re.sub(r'[^\w\s]', '', text.lower())
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_comment_pairs_file():
    """Generate the comment pairs file if it doesn't exist."""
    output_file = 'CHANGE_IT_TO_YOUR_PATH' # comments file to generate (json)
    
    if os.path.exists(output_file):
        logger.info(f"Comment pairs file already exists: {output_file}")
        return output_file
    
    logger.info("Generating comment pairs file...")
    # File paths
    file_paths = [
        'CHANGE_IT_TO_YOUR_PATH', #_no.jsonl issues that you don't want to have
        'CHANGE_IT_TO_YOUR_PATH' #_no.jsonl issues that you don't want to have
    ]
    
    # Process comment pairs
    comment_pairs = {}
    issue_data = load_jsonl_data(file_paths)
    
    for data in issue_data:
        comments = data.get('comments', [])
        for i in range(len(comments) - 1):
            current_comment = comments[i]['body']
            next_comment = comments[i + 1]['body']
            comment_pairs[current_comment] = next_comment
    
    logger.info(f"Processed {len(comment_pairs)} comment pairs")
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comment_pairs, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved comment pairs to {output_file}")
    return output_file

def find_similar_comments(query, comment_keys, bm25_index, top_n=3):
    """Find top similar comments using BM25."""
    # Tokenize query
    tokenized_query = query.lower().split()
    
    # Get scores
    scores = bm25_index.get_scores(tokenized_query)
    
    # Get top_n indices
    top_indices = np.argsort(scores)[::-1][:top_n]
    
    results = []
    for idx in top_indices:
        results.append({
            'score': scores[idx],
            'comment': comment_keys[idx]
        })
    
    return results

def get_user_style_from_similar_comments(similar_comments, comment_pairs):
    """Extract user style from similar comments and their responses."""
    user_responses = []
    
    for item in similar_comments:
        comment = item['comment']
        score = item['score']
        
        # Find the next comment (user response) if it exists
        if comment in comment_pairs:
            user_response = comment_pairs[comment]
            user_responses.append({
                'score': score,
                'response': user_response
            })
    
    return user_responses

def analyze_user_style(user_responses):
    """Analyze the style of user responses."""
    if not user_responses:
        return None
    
    all_text = " ".join([r['response'] for r in user_responses])
    sentences = re.split(r'[.!?]+', all_text)
    words = all_text.lower().split()
    
    # Basic metrics
    avg_response_length = sum(len(r['response']) for r in user_responses) / len(user_responses)
    avg_sentences = len(sentences) / len(user_responses)
    
    # Word usage patterns
    word_freq = {}
    for word in words:
        if len(word) > 3:  # Skip short words
            if word not in word_freq:
                word_freq[word] = 0
            word_freq[word] += 1
    
    # Get top words
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Look for question patterns
    questions = [s for s in sentences if '?' in s]
    question_ratio = len(questions) / len(sentences) if sentences else 0
    
    # Extract common phrases (3-5 words)
    phrases = []
    for sentence in sentences:
        words = sentence.split()
        for i in range(len(words) - 2):
            if i + 3 <= len(words):
                phrases.append(' '.join(words[i:i+3]))
    
    phrase_freq = {}
    for phrase in phrases:
        phrase = phrase.strip()
        if len(phrase) > 10:  # Minimum phrase length
            if phrase not in phrase_freq:
                phrase_freq[phrase] = 0
            phrase_freq[phrase] += 1
    
    top_phrases = sorted(phrase_freq.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'avg_response_length': avg_response_length,
        'avg_sentences': avg_sentences,
        'top_words': top_words,
        'question_ratio': question_ratio,
        'top_phrases': top_phrases,
        'sample_responses': [r['response'] for r in user_responses[:3]]  # Top 3 responses
    }

def get_user_style(maintainer_comment, comment_pairs_file=None):
    """Get user style based on similar maintainer comments."""
    if not comment_pairs_file:
        comment_pairs_file = generate_comment_pairs_file()
    
    # Load comment pairs
    comment_pairs = load_comment_pairs(comment_pairs_file)
    if not comment_pairs:
        logger.error("Failed to load comment pairs file")
        return None
    
    logger.info(f"Loaded {len(comment_pairs)} comment pairs")
    
    # Create BM25 index from all maintainer comments
    comment_keys = list(comment_pairs.keys())
    bm25_index = create_bm25_index(comment_keys)
    logger.info(f"Created BM25 index with {len(comment_keys)} comments")
    
    # Find similar comments
    similar_comments = find_similar_comments(maintainer_comment, comment_keys, bm25_index, top_n=3)
    logger.info(f"Found {len(similar_comments)} similar comments")
    
    # Get user responses to similar comments
    user_responses = get_user_style_from_similar_comments(similar_comments, comment_pairs)
    logger.info(f"Extracted {len(user_responses)} user responses")
    
    # Analyze user style
    user_style = analyze_user_style(user_responses)
    
    return {
        'user_style': user_style,
        'similar_comments': similar_comments,
        'user_responses': user_responses
    }

def user_agent_response(issue_data, conversation_history, docker_results=None):
    """Generate a response from the user agent based on the conversation history and Docker results."""
    logger.info("Activating user agent to respond to maintainer")
    
    # Extract issue ID for logging
    issue_id = issue_data.get("id", "unknown")
    
    # Extract relevant information from the issue data
    question_title = issue_data["first_question"]["title"]
    question_body = issue_data["first_question"]["body"]
    user_satisfaction_conditions = issue_data.get("user_satisfaction_condition", [])
    
    # Get the last maintainer response
    maintainer_response = None
    for message in reversed(conversation_history):
        if message['role'] == 'maintainer':
            maintainer_response = message['content']
            break
    
    # Get user style guidance if we have a maintainer response
    style_guidance = ""
    if maintainer_response:
        # Get user style based on similar comments
        style_data = get_user_style(maintainer_response)
        user_style = style_data['user_style'] if style_data else None
        top_responses = user_style.get('sample_responses', [])[:3]
        
        if user_style:
            logger.info("Adding user style guidance based on similar conversations")
            style_guidance = f"""
            When responding, mimic the communication style of the user based on these style reference:

            EXAMPLE 1: "{top_responses[0][:1000]}..." if top_responses else ""
            EXAMPLE 2: "{top_responses[1][:1000]}..." if len(top_responses) > 1 else ""
            EXAMPLE 3: "{top_responses[2][:1000]}..." if len(top_responses) > 2 else ""

            IMPORTANT: These examples are provided ONLY for style reference. Do NOT use any specific information or content from these examples in your response. Your response should be based solely on the current conversation and issue at hand, using only the communication style as a guide.

            Emulate the tone, sentence structure, and general communication approach, but generate your own content relevant to the current conversation.
            """
    
    # Create a formatted conversation history string
    formatted_conversation = ""
    for i, message in enumerate(conversation_history):
        role = "User" if message['role'] == "user" else "Maintainer"
        formatted_conversation += f"{role}: {message['content']}\n\n"
    
    # Prepare Docker results information if available
    docker_info = ""
    if docker_results:
        # Include full stdout and stderr
        stdout = docker_results.get('logs', '')
        
        docker_info = f"""
        You also have access to the results of running Docker commands to test the solution provided by the maintainer:
        
        Docker build and test {"succeeded" if docker_results.get('success', False) else "failed"}
        
        Test commands that were run:
        {json.dumps(docker_results.get('test_commands', []), indent=2)}
        
        Command output:
        {stdout}
        
        IMPORTANT: Use these Docker test results to determine if your satisfaction conditions have been met.
        If your question involves a Docker setup that needs to work correctly, a successful Docker build and test
        is a strong indicator that the solution works. Conversely, if Docker tests fail, analyze the logs to
        understand what's still not working correctly.
        """
    
    # Create the user agent system prompt
    system_prompt = f"""
    You are a user seeking help with a technical question about a software project.
    
    Your original question was: "{question_title}"
    
    You have certain expectations about what would make a satisfactory answer to your question.
    These satisfaction conditions are:
    {json.dumps(user_satisfaction_conditions, indent=2)}
    
    Your role is to engage with the maintainer to get a complete and correct answer. You should:
    1. Point out any unclear explanations or potential inaccuracies in the maintainer's response
    2. Ask follow-up questions to get clarification on points that seem unclear
    3. Express your satisfaction ONLY if all your satisfaction conditions are met
    
    DO NOT pretend to know the answers yourself, and DO NOT provide technical solutions.
    Your goal is to guide the maintainer toward providing a satisfactory answer.
    
    {style_guidance}
    
    {docker_info}
    
    IMPORTANT: Only express satisfaction when the maintainer has fully addressed all your satisfaction conditions.
    If you're not sure if all conditions are met, ask for further clarification rather than expressing satisfaction.
    
    After writing your response to the maintainer, add a separate section at the end that explicitly evaluates whether
    you are fully satisfied. Format this section as follows:
    
    SATISFACTION_STATUS: [FULLY_SATISFIED | PARTIALLY_SATISFIED | NOT_SATISFIED]
    REASON: <brief explanation of why you are or are not satisfied>
    
    This section will be removed before sending your response to the maintainer.
    """
    
    # Create the user agent user prompt
    user_prompt = f"""
    Here is your original question:
    {question_body}
    
    Here is your conversation with the maintainer so far:
    {formatted_conversation}
    
    Please provide your next response to the maintainer. Remember to focus on your satisfaction conditions 
    and ask for clarifications if needed. DO NOT express satisfaction unless all your conditions are fully met.
    
    After your response to the maintainer, add the SATISFACTION_STATUS section to evaluate whether your needs
    have been fully met.
    """
    
    # Get the user agent's response
    logger.info("Requesting response from user agent")
    full_response = call_llm(user_prompt, system_prompt, "user", issue_id)
    logger.info(f"User agent response complete ({len(full_response)} chars)")
    
    # Extract the satisfaction status and reason
    satisfaction_status = "NOT_SATISFIED"  # Default
    satisfaction_reason = "No explicit satisfaction status provided"
    
    # Look for the satisfaction status section
    if "SATISFACTION_STATUS:" in full_response:
        # Extract the actual response part (before satisfaction status)
        parts = full_response.split("SATISFACTION_STATUS:", 1)
        response_to_maintainer = parts[0].strip()
        
        # Extract satisfaction information
        status_section = parts[1].strip()
        if "FULLY_SATISFIED" in status_section:
            satisfaction_status = "FULLY_SATISFIED"
        elif "PARTIALLY_SATISFIED" in status_section:
            satisfaction_status = "PARTIALLY_SATISFIED"
        else:
            satisfaction_status = "NOT_SATISFIED"
            
        # Try to extract reason if present
        if "REASON:" in status_section:
            reason_part = status_section.split("REASON:", 1)[1].strip()
            satisfaction_reason = reason_part.split("\n")[0].strip()  # Take just the first line
    else:
        # If no satisfaction status is found, use the whole response
        response_to_maintainer = full_response
    
    # Log the satisfaction status
    logger.info(f"User satisfaction status: {satisfaction_status}")
    logger.info(f"Satisfaction reason: {satisfaction_reason}")
    
    # Return the response to show to maintainer and the satisfaction status
    return {
        "response": response_to_maintainer,
        "satisfaction_status": satisfaction_status,
        "satisfaction_reason": satisfaction_reason
    }

def maintainer_agent_response(repo_dir, issue_data, conversation_history, system_prompt_template):
    """Generate a response from the maintainer agent based on the conversation history and repository."""
    logger.info("Activating maintainer agent to respond to user")
    
    # Extract issue ID for logging
    issue_id = issue_data.get("id", "unknown")
    
    # Extract the user's question from conversation history
    latest_user_message = ""
    for message in reversed(conversation_history):
        if message['role'] == "user":
            latest_user_message = message['content']
            break
    
    # Create the maintainer system prompt with emphasis on comprehensive answers
    system_prompt = system_prompt_template + """
    You are in a conversation with a user who is asking questions about a code issue.
    Respond to their latest message, using your repository knowledge to provide accurate information.
    
    IMPORTANT GUIDELINES:
    1. Include ALL relevant information needed to fully answer the user's question.
    2. If you've provided partial information in previous responses, INCLUDE that information again.
    3. When referencing code or solutions you've mentioned before, ALWAYS include the full code or solution again.
    4. Make sure your answer is complete even if it means repeating information.
    
    If you need to explore the repository further to answer their question, you can do so using:
    EXPLORE: <command to run>
    
    Then provide your complete answer to the user in a clear, helpful manner.
    
    Make sure to address all points raised by the user and provide complete, accurate information.
    """
    
    # Create the maintainer user prompt - include full conversation history for context
    user_prompt = f"""
    Original question: {issue_data['first_question']['title']}
    
    Conversation history:
    {formatted_conversation_history(conversation_history)}
    
    Latest user message: {latest_user_message}
    
    Please respond to the user's latest message.
    """
    
    # Get the maintainer agent's response with exploration - using Haiku model
    logger.info("Preparing maintainer agent response")
    
    # Check if exploration commands are in the response
    exploration_results = ""
    # Use Haiku model for maintainer responses
    maintainer_response = call_llm(user_prompt, system_prompt, "maintainer", issue_id, model=MAINTAINER)
    
    # Process any exploration commands
    if "EXPLORE:" in maintainer_response:
        logger.info("Processing exploration commands in maintainer response")
        lines = maintainer_response.split('\n')
        processed_response = []
        exploration_results = ""
        
        for line in lines:
            if line.strip().startswith("EXPLORE:"):
                cmd = line.split("EXPLORE:", 1)[1].strip()
                logger.info(f"Executing exploration command: {cmd}")
                result = execute_command(repo_dir, cmd)
                exploration_results += f"Command: {cmd}\nResult:\n{result}\n\n"
            else:
                processed_response.append(line)
        
        # If exploration was performed, regenerate response with results
        if exploration_results:
            final_prompt = f"""
            Original question: {issue_data['first_question']['title']}
            
            Conversation history:
            {formatted_conversation_history(conversation_history)}
            
            Latest user message: {latest_user_message}
            
            Exploration results:
            {exploration_results}
            
            Please provide your final response to the user based on the exploration results.
            """
            
            # Use Haiku model for final response as well
            maintainer_response = call_llm(final_prompt, system_prompt, "maintainer", issue_id, model=MAINTAINER)
    
    logger.info(f"Maintainer agent response complete ({len(maintainer_response)} chars)")
    return maintainer_response, exploration_results

def formatted_conversation_history(history):
    """Format conversation history for better readability."""
    formatted = ""
    for i, message in enumerate(history):
        role = "User" if message['role'] == "user" else "Maintainer"
        formatted += f"{role}: {message['content']}\n\n"
    return formatted


def extract_alignment_section(judgment):
    """Extract the alignment section from the judge's evaluation."""
    if "ALIGNMENT SCORE:" in judgment:
        # Get the text after "ALIGNMENT SCORE:" label
        alignment_section = judgment.split("ALIGNMENT SCORE:", 1)[1].strip()
        
        # Get the text up to the next major section if there is one
        next_sections = ["KEY ISSUES:", "REASONING:", "VERDICT:"]
        for section in next_sections:
            if section in alignment_section:
                alignment_section = alignment_section.split(section, 1)[0].strip()
        
        return alignment_section
    elif "ALIGNMENT:" in judgment:
        # Get the text after "ALIGNMENT:" label
        alignment_section = judgment.split("ALIGNMENT:", 1)[1].strip()
        
        # Get the text up to the next major section if there is one
        next_sections = ["KEY ISSUES:", "REASONING:", "VERDICT:"]
        for section in next_sections:
            if section in alignment_section:
                alignment_section = alignment_section.split(section, 1)[0].strip()
        
        return alignment_section
    return None

def conduct_conversation(repo_dir, issue_data, initial_answer, verdict, key_issues, system_prompt_template, max_rounds=10, docker_results=None):
    """
    Conduct a conversation between the user and maintainer agents to resolve the issue.
    Only judges the maintainer's answer once at the end of the conversation.
    """
    logger.info(f"Starting conversation for issue: {issue_data['first_question']['title']}")
    
    # Extract issue ID for tracking
    issue_id = issue_data.get("id", f"issue_{hash(issue_data['first_question']['title'])}")
    
    conversation_history = [
        {"role": "user", "content": f"{issue_data['first_question']['title']}\n\n{issue_data['first_question']['body']}"},
        {"role": "maintainer", "content": initial_answer}
    ]
    
    exploration_log = ""
    
    # Add user satisfaction status tracking
    user_satisfied = False
    user_satisfaction_status = "NOT_SATISFIED"
    user_satisfaction_reason = ""
    
    # Track Docker results for the current round
    current_docker_results = docker_results
    
    # Setup Docker client
    docker_client = setup_docker_client()
    
    for round_num in range(max_rounds):
        # Check if conversation should end
        if user_satisfied:
            logger.info("User is satisfied. Ending conversation.")
            break
            
        logger.info(f"Starting conversation round {round_num + 1}/{max_rounds}")
        
        # User agent responds to maintainer (with Docker results but NO judge feedback)
        try:
            user_response_data = user_agent_response(
                issue_data, 
                conversation_history, 
                current_docker_results
            )
            
            # Extract components
            user_response = user_response_data["response"]
            user_satisfaction_status = user_response_data["satisfaction_status"]
            user_satisfaction_reason = user_response_data["satisfaction_reason"]
            
            # Check if we got an "input too long" error
            if user_response == "ERROR_INPUT_TOO_LONG":
                logger.warning("Input too long error in user agent response. Ending conversation and using existing results.")
                break
                
            # Update satisfaction status based on user's own assessment
            user_satisfied = (user_satisfaction_status == "FULLY_SATISFIED")
            
            # Log satisfaction status
            logger.info(f"User satisfaction status: {user_satisfaction_status}")
            logger.info(f"Reason: {user_satisfaction_reason}")
            
            conversation_history.append({"role": "user", "content": user_response})
            logger.info(f"User agent response in round {round_num + 1}: {len(user_response)} chars")
            
            # If user is fully satisfied, we can end the conversation
            if user_satisfied:
                logger.info("User is fully satisfied. Ending conversation.")
                break
                
        except Exception as e:
            if is_input_too_long_error(str(e)):
                logger.warning("Input too long error in user agent. Ending conversation and using existing results.")
                break
            else:
                logger.error(f"Error getting user agent response: {e}")
                conversation_history.append({"role": "user", "content": f"Error: Failed to get proper response. {str(e)}"})
        
        # Early termination check: if this was the last round, don't get maintainer response
        if round_num == max_rounds - 1:
            logger.info(f"Reached maximum conversation rounds ({max_rounds}). Ending conversation.")
            break
        
        # Maintainer agent responds to user
        local_docker_results = None  # To store Docker results from this round
        try:
            if 'dockerfile' in issue_data and docker_client:
                # Use Docker-aware maintainer response
                logger.info("Using Docker-aware maintainer response")
                maintainer_response, extra_files, modified_dockerfile = maintainer_agent_response_docker(
                    repo_dir, issue_data, conversation_history, system_prompt_template
                )
                
                # Check if we got an "input too long" error
                if maintainer_response == "ERROR_INPUT_TOO_LONG":
                    logger.warning("Input too long error in maintainer agent response. Ending conversation and using existing results.")
                    break
                    
                # Update Docker-related files if needed
                if modified_dockerfile:
                    issue_data['dockerfile'] = modified_dockerfile
                    logger.info("Updated Dockerfile with maintainer's modifications")
                
                # Run Docker tests if provided
                if extra_files or modified_dockerfile:
                    logger.info("Running Docker build with maintainer's changes")
                    test_commands = generate_test_commands(issue_data, maintainer_response, exploration_log)
                    success, logs = build_and_run_dockerfile(
                        issue_data, 
                        test_commands, 
                        extra_files=extra_files if extra_files else None
                    )
                    
                    # Store Docker results for this round
                    local_docker_results = {
                        'success': success,
                        'logs': logs,
                        'test_commands': test_commands,
                        'extra_files': extra_files,
                        'modified_dockerfile': modified_dockerfile is not None
                    }
                    
                    # Update current Docker results for next round
                    current_docker_results = local_docker_results
                    
                    # Add Docker results to the conversation
                    docker_result_summary = f"Docker build and test {'succeeded' if success else 'failed'}.\n\nLogs:\n{logs[:3000]}..."
                    conversation_history.append({"role": "maintainer", "content": maintainer_response + "\n\n" + docker_result_summary})
                else:
                    conversation_history.append({"role": "maintainer", "content": maintainer_response})
            else:
                # Use standard maintainer response
                maintainer_response, current_exploration = maintainer_agent_response(
                    repo_dir, issue_data, conversation_history, system_prompt_template
                )
                
                # Check if we got an "input too long" error
                if maintainer_response == "ERROR_INPUT_TOO_LONG":
                    logger.warning("Input too long error in maintainer agent response. Ending conversation and using existing results.")
                    break
                
                conversation_history.append({"role": "maintainer", "content": maintainer_response})
                exploration_log += f"\n--- CONVERSATION ROUND {round_num + 1} EXPLORATION ---\n{current_exploration}"
            
            logger.info(f"Maintainer agent response in round {round_num + 1}: {len(maintainer_response)} chars")
                
        except Exception as e:
            if is_input_too_long_error(str(e)):
                logger.warning("Input too long error in maintainer agent. Ending conversation and using existing results.")
                break
            else:
                logger.error(f"Error getting maintainer agent response: {e}")
                conversation_history.append({"role": "maintainer", "content": f"Error: Failed to get proper response. {str(e)}"})
                current_exploration = f"Error: {str(e)}"
                exploration_log += f"\n--- CONVERSATION ROUND {round_num + 1} ERROR ---\n{current_exploration}"
    
    
    # Log final results
    total_rounds = round_num + 1
    logger.info(f"Conversation completed after {total_rounds} rounds")
    
    logger.info(f"User satisfied: {user_satisfied}")
    logger.info(f"User satisfaction status: {user_satisfaction_status}")
    logger.info(f"User satisfaction reason: {user_satisfaction_reason}")
    
    # Log LLM call statistics for this conversation
    with call_counter_lock:
        llm_call_stats = dict(llm_call_counter[issue_id])
        logger.info(f"LLM calls during conversation: {llm_call_stats}")
    
    if user_satisfied:
        logger.info("Conversation result: SUCCESS - User is fully satisfied")
    
    # Include satisfaction status in the return value - we've moved the judging to process_issue
    return conversation_history, exploration_log, "PENDING", total_rounds, user_satisfied, {}, user_satisfaction_status, user_satisfaction_reason

def format_alignment_score(alignment_score):
    """Format the alignment score for human-readable display."""
    if not alignment_score or not isinstance(alignment_score, dict):
        return "No alignment score available"
    
    satisfied = alignment_score.get('satisfied', 0)
    total = alignment_score.get('total', 0)
    percentage = alignment_score.get('percentage', 0)
    
    result = f"ALIGNMENT SCORE: {satisfied}/{total} CONDITIONS MET ({percentage:.2f}%)\n\n"
    
    # Add individual condition results
    conditions = alignment_score.get('conditions', [])
    for condition in conditions:
        status = "TRUE" if condition.get('satisfied', False) else "FALSE"
        result += f"CONDITION {condition.get('number', '?')}: [{status}] {condition.get('description', '')}\n"
    
    return result

def process_issue(issue_data, max_iterations=5, max_conversation_rounds=10):
    """Process an issue with or without Docker validation."""
    # Initial setup
    repo_url = parse_repo_name(issue_data["commit_info"]["repository"])
    reference_commit_hash = issue_data["commit_info"]["latest_commit"]["sha"]
    question_title = issue_data["first_question"]["title"]
    question_body = issue_data["first_question"]["body"]
    question = f"{question_title}\n\n{question_body}"
    
    # Extract or generate issue ID for tracking
    issue_id = issue_data.get("id", f"issue_{hash(question_title)}")
    
    # Store the original conversation length (number of comments)
    original_comment_count = len(issue_data.get("comments", []))
    
    # Reset call counter for this issue
    with call_counter_lock:
        llm_call_counter[issue_id] = defaultdict(int)
    
    logger.info(f"Processing issue: {question_title} (ID: {issue_id})")
    logger.info(f"Repository: {repo_url}")
    logger.info(f"Reference commit hash: {reference_commit_hash}")
    logger.info(f"Original conversation length: {original_comment_count} comments")
    
    # Let maintainer agent determine if user specified a commit hash
    selected_commit_hash = maintainer_choose_commit(reference_commit_hash, question)
    logger.info(f"Selected commit hash for exploration: {selected_commit_hash}")
    
    # Create base system prompt template
    system_prompt_template = f"""
    You are a helpful maintainer of a software project. You can help answer questions about the code by exploring the repository.
    
    Repository: {repo_url}
    Selected commit hash for exploration: {selected_commit_hash}
    
    You have the following capabilities:
    1. Clone the repository and explore its contents
    2. Read files or specific lines of files
    3. List directories
    4. Find files matching patterns
    5. Execute commands within the repository
    
    When providing an answer, be clear, and directly address the user's question.
    """
    
    # Clone repo for exploration using the selected commit hash
    temp_repo_dir = clone_repo(repo_url, selected_commit_hash)
    if not temp_repo_dir:
        logger.error("Failed to clone repository")
        return {
            "question_title": question_title,
            "question_body": question_body,
            "issue_id": issue_id,
            "response": "Failed to clone the repository for exploration.",
            "judgment": "INCORRECT - Failed to clone repository",
            "initial_verdict": "INCORRECT",
            "final_verdict": "INCORRECT",
            "user_satisfied": False,
            "original_conversation_length": original_comment_count,
            "llm_calls": dict(llm_call_counter[issue_id])
        }
    
    try:
        # Start the interactive exploration process
        logger.info(f"Starting interactive exploration with max {max_iterations} iterations")
        initial_answer, exploration_history, exploration_log = interactive_exploration(
            temp_repo_dir, question, system_prompt_template, max_iterations, issue_id=issue_id
        )
        
        logger.info(f"Completed exploration. Initial answer length: {len(initial_answer)}")
        
        # Initialize variables to ensure they're always defined
        verdict = "UNKNOWN"
        key_issues = []
        user_satisfied = False
        docker_results = None
        initial_alignment_score = {}
        final_alignment_score = {}
        
        # For Docker-related issues, run Docker validation using the updated approach
        if 'dockerfile' in issue_data:
            logger.info("Docker issue detected. Running Docker validation...")
            try:
                # Generate test commands suitable for running inside the container
                test_commands = generate_test_commands(issue_data, initial_answer, exploration_log)
                
                # Extract any extra files from the maintainer's response if needed
                extra_files = {}
                if hasattr(issue_data, 'extra_files'):
                    extra_files = issue_data.extra_files
                
                # Store the extra files in the issue_data for Docker validation
                if extra_files:
                    issue_data['extra_files'] = extra_files
                
                # Validate the Docker solution
                if test_commands:
                    success, logs = validate_docker_solution(issue_data, test_commands)
                    docker_results = {
                        'success': success,
                        'logs': logs,
                        'test_commands': test_commands
                    }
                    logger.info(f"Docker validation result: {'SUCCESS' if success else 'FAILURE'}")
                else:
                    logger.warning("No test commands generated for Docker validation")
                    # Run a basic validation without specific test commands
                    success, logs = validate_docker_solution(issue_data)
                    docker_results = {
                        'success': success,
                        'logs': logs,
                        'test_commands': []
                    }
            except Exception as e:
                logger.error(f"Error during Docker validation: {str(e)}")
                docker_results = {'success': False, 'logs': f"Error: {str(e)}", 'error': str(e)}
        
        # Continue conversation without judging the initial answer
        logger.info("Starting conversation...")
        try:
            # We'll skip the initial judgment and only judge at the end of the conversation
            verdict = "PENDING"  # We'll use a placeholder verdict
            key_issues = []      # Empty list for now
            
            conversation_history, additional_exploration_log, final_verdict, total_rounds, user_satisfied, final_alignment_score, satisfaction_status, satisfaction_reason = conduct_conversation(
                temp_repo_dir,
                issue_data,
                initial_answer,
                verdict,
                key_issues,
                system_prompt_template,
                max_conversation_rounds,
                docker_results
            )
            
            # Get final answer from conversation
            final_answer = initial_answer
            for message in reversed(conversation_history):
                if message['role'] == 'maintainer':
                    final_answer = message['content']
                    break
            
            # Now judge the final answer only once
            try:
                # Get latest Docker results if available
                latest_docker_results = None
                if 'dockerfile' in issue_data:
                    test_commands = generate_test_commands(issue_data, final_answer, additional_exploration_log)
                    
                    # Extract any updated extra files from the final answer
                    maintainer_response, extra_files, modified_dockerfile = maintainer_agent_response_docker(
                        temp_repo_dir, issue_data, conversation_history, system_prompt_template
                    )
                    
                    # Update Dockerfile if modified during the conversation
                    if modified_dockerfile:
                        issue_data['dockerfile'] = modified_dockerfile
                    
                    # Store updated extra files in issue_data
                    if extra_files:
                        issue_data['extra_files'] = extra_files
                    
                    # Run final Docker validation
                    if test_commands:
                        success, logs = validate_docker_solution(issue_data, test_commands)
                        latest_docker_results = {
                            'success': success,
                            'logs': logs,
                            'test_commands': test_commands
                        }
                    else:
                        success, logs = validate_docker_solution(issue_data)
                        latest_docker_results = {
                            'success': success,
                            'logs': logs,
                            'test_commands': []
                        }
                
                # Judge the final answer
                logger.info("Judging final answer...")
                judgment, final_verdict, final_issues, final_alignment_score = judge_maintainer_answer(
                    issue_data, final_answer, latest_docker_results
                )
                
                logger.info(f"Final verdict: {final_verdict}")
                if final_alignment_score:
                    satisfied_count = final_alignment_score.get('satisfied', 0)
                    total_count = final_alignment_score.get('total', 0)
                    logger.info(f"Final alignment score: {satisfied_count}/{total_count} conditions met")
                
            except Exception as e:
                logger.error(f"Error during final judgment: {str(e)}")
                judgment = f"Judgment error: {str(e)}"
                final_verdict = "UNKNOWN"
        except Exception as e:
            logger.error(f"Error during conversation: {str(e)}")
            judgment = f"Conversation error: {str(e)}"
            final_verdict = "UNKNOWN"
            total_rounds = 0
        
        # Get final LLM call statistics
        with call_counter_lock:
            llm_call_stats = dict(llm_call_counter[issue_id])
            total_calls = sum(llm_call_stats.values())
            logger.info(f"Total LLM calls for issue {issue_id}: {total_calls}")
            logger.info(f"LLM calls by agent: {llm_call_stats}")
        
        result = {
            "question_title": question_title,
            "question_body": question_body,
            "issue_id": issue_id,
            "initial_response": initial_answer,
            "final_response": final_answer if 'final_answer' in locals() else initial_answer,
            "initial_verdict": "N/A",  # We don't judge the initial response anymore
            "final_verdict": final_verdict if 'final_verdict' in locals() else "UNKNOWN",
            "user_satisfied": user_satisfied,
            "original_conversation_length": original_comment_count,
            "total_conversation_rounds": total_rounds if 'total_rounds' in locals() else 0,
            "exploration_history": exploration_history,
            "exploration_log": exploration_log + (additional_exploration_log if 'additional_exploration_log' in locals() else ""),
            "conversation_history": conversation_history if 'conversation_history' in locals() else [],
            "judgment": judgment if 'judgment' in locals() else "No judgment performed",
            "initial_alignment_score": {},  # No initial judgment anymore
            "final_alignment_score": final_alignment_score if 'final_alignment_score' in locals() else {},
            "llm_calls": llm_call_stats
        }
        
        # Include Docker results if available
        if docker_results:
            result["docker_validation"] = docker_results
            
        return result
        
    except Exception as e:
        logger.error(f"Error in process_issue: {str(e)}")
        # Return error result with LLM call stats
        with call_counter_lock:
            llm_call_stats = dict(llm_call_counter[issue_id])
        
        return {
            "question_title": question_title,
            "question_body": question_body,
            "issue_id": issue_id,
            "error": str(e),
            "judgment": f"Error: {str(e)}",
            "initial_verdict": "ERROR",
            "final_verdict": "ERROR",
            "user_satisfied": False,
            "original_conversation_length": original_comment_count,
            "status": "failed",
            "llm_calls": llm_call_stats
        }
    finally:
        # Clean up temp directory
        logger.info(f"Cleaning up temporary directory: {temp_repo_dir}")
        if os.path.exists(temp_repo_dir):
            shutil.rmtree(temp_repo_dir)

def write_file_in_docker_context(temp_dir, file_path, content):
    """Write a file to the Docker build context with better path handling."""
    try:
        # Ensure path is relative to temp_dir and sanitized
        safe_path = os.path.normpath(file_path)
        if safe_path.startswith(os.sep):
            safe_path = safe_path[1:]  # Remove leading slash
            
        full_path = os.path.join(temp_dir, safe_path)
        
        # Create directories if they don't exist
        dir_path = os.path.dirname(full_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created file {safe_path} in Docker build context")
        return True
    except Exception as e:
        logger.error(f"Failed to create file {file_path}: {e}")
        return False

def system_prompt_template(issue_data):
    """
    Generate a custom system prompt template based on repository type and issue details.
    
    Args:
        issue_data: Dictionary containing information about the issue
        
    Returns:
        str: Customized system prompt template
    """
    # Extract relevant information from issue data
    repo_url = issue_data["commit_info"]["repository"]
    commit_hash = issue_data["commit_info"]["latest_commit"]["sha"]
    
    # Determine repository type and language
    repo_type = "Docker" if 'dockerfile' in issue_data else "Unknown"
    
    # Customize Docker-specific guidance if applicable
    docker_guidance = ""
    if repo_type == "Docker":
        docker_guidance = """
        Since this issue involves Docker, pay special attention to:
        - Dockerfile syntax and best practices
        - Container build and runtime issues
        - Environment variables and configuration
        - Networking and service dependencies
        - Volume mounting and file permissions
        - Image layers and caching
        
        When suggesting changes to a Dockerfile, explain the reasoning behind each modification.
        """
    
    # Build the base system prompt
    base_prompt = f"""
    You are a helpful maintainer of a software project. You can help answer questions about the code by exploring the repository.
     
    Repository: {repo_url}
    Commit hash: {commit_hash}
    Repository type: {repo_type}
    
    You have the following capabilities:
    1. Clone the repository and explore its contents
    2. Read files or specific lines of files
    3. List directories
    4. Find files matching patterns
    5. Execute commands within the repository
    
    When providing an answer:
    - Be clear and directly address the user's question
    - Provide complete, actionable solutions when possible
    - Include relevant code snippets to illustrate your points
    - Explain the reasoning behind your recommendations
    - Consider edge cases and potential issues with your suggestions
    {docker_guidance}
    
    Prioritize accuracy and completeness in your responses. If you're uncertain about something, acknowledge your uncertainty rather than providing potentially incorrect information.
    """
    
    return base_prompt

def maintainer_choose_commit(reference_commit, user_question):
    """
    Allow maintainer to decide whether to use reference commit or a user-specified commit,
    if the user explicitly mentioned one in their question.
    """
    # Create prompt for commit selection
    system_prompt = """
    You are a software maintainer helping with a code issue. You need to determine if the user has explicitly 
    mentioned a specific git commit hash they want you to examine.
    
    Your task:
    1. Carefully read the user's question
    2. Determine if they explicitly mentioned a specific commit hash they want you to look at
    3. If yes, extract and return ONLY that full commit hash as your response
    4. If no specific commit is mentioned, or if it's ambiguous, respond with ONLY "USE_REFERENCE_COMMIT"
    
    A git commit hash is typically a 40-character hexadecimal string (0-9, a-f), though users might mention 
    abbreviated versions (at least 7 characters).

    Only extract a hash if the user is clearly asking about a specific version/commit of the code.
    """
    
    user_prompt = f"""
    Reference commit: {reference_commit}
    
    User's question: {user_question}
    
    Has the user explicitly mentioned a specific commit hash they want me to examine? 
    If yes, what is that hash? If no, respond with USE_REFERENCE_COMMIT.
    """
    
    # Get maintainer's decision
    try:
        response = call_llm(user_prompt, system_prompt)
        response_text = response.strip()
        
        if "USE_REFERENCE_COMMIT" in response_text:
            logger.info(f"No specific commit mentioned. Using reference commit: {reference_commit}")
            return reference_commit
        else:
            # Try to extract a hash-like string from the response
            import re
            hash_pattern = re.compile(r'\b[0-9a-f]{7,40}\b', re.IGNORECASE)
            hash_match = hash_pattern.search(response_text)
            
            if hash_match:
                user_commit = hash_match.group(0)
                logger.info(f"User specified commit detected: {user_commit}")
                return user_commit
            else:
                logger.warning(f"Unexpected response format. Using reference commit: {reference_commit}")
                return reference_commit
            
    except Exception as e:
        logger.error(f"Error in commit selection: {e}")
        return reference_commit

def save_batch_results(results_batch, batch_num, results_dir, timestamp):
    """Save a batch of results to files."""
    try:
        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
        # Separate Docker and non-Docker results
        docker_results = []
        regular_results = []
        
        for result in results_batch:
            # Add metadata to result
            result['metadata'] = {
                'timestamp': timestamp,
                'batch_number': batch_num,
                'processing_date': datetime.now().isoformat(),
                'has_docker': 'docker_validation' in result,
                'total_conversation_rounds': result.get('total_conversation_rounds', 'N/A')
            }
            
            # Ensure conversation_history is properly formatted for JSON serialization
            if 'conversation_history' in result:
                # Ensure each message in conversation history is serializable
                # Convert any non-serializable objects to strings if needed
                for message in result['conversation_history']:
                    if 'content' in message and not isinstance(message['content'], (str, int, float, bool, type(None))):
                        message['content'] = str(message['content'])
            
            # Log individual result summary
            logger.info(f"Issue: {result['question_title']}")
            logger.info(f"Initial verdict: {result['initial_verdict']}")
            logger.info(f"Final verdict: {result['final_verdict']}")
            logger.info(f"Total conversation rounds: {result['total_conversation_rounds']}")
            logger.info(f"Conversation history length: {len(result.get('conversation_history', []))}")
            logger.info("------------------------")
            
            if 'docker_validation' in result:
                docker_results.append(result)
            else:
                regular_results.append(result)
        
        # Save Docker results
        if docker_results:
            docker_file = os.path.join(results_dir, f'docker_responses_{timestamp}_batch_{batch_num}.jsonl')
            with open(docker_file, 'w') as f:
                for result in docker_results:
                    f.write(json.dumps(result) + '\n')
            logger.info(f"Saved {len(docker_results)} Docker results to batch {batch_num}")
        
        # Save regular results
        if regular_results:
            regular_file = os.path.join(results_dir, f'responses_{timestamp}_batch_{batch_num}.jsonl')
            with open(regular_file, 'w') as f:
                for result in regular_results:
                    f.write(json.dumps(result) + '\n')
            logger.info(f"Saved {len(regular_results)} regular results to batch {batch_num}")
        
        # Update summary statistics
        save_batch_summary(results_dir, timestamp, batch_num, docker_results, regular_results)
        
    except Exception as e:
        logger.error(f"Error saving batch {batch_num}: {e}")
        # If there was an error in the main save, try to save just essential data
        try:
            emergency_file = os.path.join(results_dir, f'emergency_save_{timestamp}_batch_{batch_num}.jsonl')
            with open(emergency_file, 'w') as f:
                for result in results_batch:
                    # Create a simplified version with only essential fields
                    simplified = {
                        'issue_id': result.get('issue_id', 'unknown'),
                        'question_title': result.get('question_title', ''),
                        'initial_verdict': result.get('initial_verdict', 'UNKNOWN'),
                        'final_verdict': result.get('final_verdict', 'UNKNOWN'),
                        'user_satisfied': result.get('user_satisfied', False),
                        'initial_response': result.get('initial_response', ''),
                        'final_response': result.get('final_response', '')
                    }
                    # Include conversation history if possible
                    if 'conversation_history' in result:
                        try:
                            simplified['conversation_history'] = result['conversation_history']
                        except:
                            # If conversation history causes issues, save a simplified version
                            simplified['conversation_history_summary'] = f"Contains {len(result.get('conversation_history', []))} messages"
                    f.write(json.dumps(simplified) + '\n')
            logger.info(f"Saved emergency backup of results to {emergency_file}")
        except Exception as e2:
            logger.error(f"Emergency save also failed: {e2}")

def save_batch_summary(results_dir, timestamp, batch_num, docker_results, regular_results):
    """Save summary statistics for a batch."""
    try:
        summary_file = os.path.join(results_dir, f'summary_{timestamp}.json')
        
        # Initialize counters
        total_llm_calls = 0
        user_agent_calls = 0
        maintainer_agent_calls = 0
        judge_agent_calls = 0
        total_original_comments = 0
        
        # Add alignment score statistics
        total_initial_satisfaction_rate = 0
        total_final_satisfaction_rate = 0
        
        batch_stats = {
            'batch_number': batch_num,
            'timestamp': timestamp,
            'processing_date': datetime.now().isoformat(),
            'total_processed': len(docker_results) + len(regular_results),
            'docker_issues': len(docker_results),
            'regular_issues': len(regular_results),
            'success_rate': {
                'docker': {'success': 0, 'failure': 0},
                'regular': {'correct': 0, 'partially_correct': 0, 'incorrect': 0}
            },
            'user_satisfaction': {
                'satisfied': 0,
                'not_satisfied': 0,
                'satisfaction_rate': 0.0
            },
            'alignment_scores': {
                'initial': {'satisfied_conditions': 0, 'total_conditions': 0, 'avg_satisfaction_rate': 0},
                'final': {'satisfied_conditions': 0, 'total_conditions': 0, 'avg_satisfaction_rate': 0},
                'improvement_rate': 0.0
            },
            'conversation_stats': {
                'average_original_comments': 0,
                'average_conversation_rounds': {
                    'docker': 0,
                    'regular': 0,
                    'overall': 0
                },
                'rounds_to_original_ratio': 0.0
            },
            'llm_calls': {
                'total': 0,
                'average_per_issue': 0,
                'by_agent': {
                    'user': 0,
                    'maintainer': 0,
                    'judge': 0
                }
            }
        }
        
        # Track user satisfaction and rounds across all results
        satisfied_count = 0
        total_rounds = 0
        
        # Track alignment score statistics
        initial_satisfied_conditions = 0
        initial_total_conditions = 0
        final_satisfied_conditions = 0
        final_total_conditions = 0
        
        # Process all results
        total_issues = len(docker_results) + len(regular_results)
        all_results = docker_results + regular_results
        
        for result in all_results:
            # Add original conversation length to total
            total_original_comments += result.get('original_conversation_length', 0)
            
            # Track conversation rounds
            rounds = result.get('total_conversation_rounds', 0)
            total_rounds += rounds
            
            # Track Docker success/failure
            if 'docker_validation' in result:
                if result.get('docker_validation', {}).get('success', False):
                    batch_stats['success_rate']['docker']['success'] += 1
                else:
                    batch_stats['success_rate']['docker']['failure'] += 1
            else:
                # Track regular verdict
                verdict = result.get('final_verdict', 'INCORRECT').lower()
                if verdict == 'correct':
                    batch_stats['success_rate']['regular']['correct'] += 1
                elif verdict == 'partially correct':
                    batch_stats['success_rate']['regular']['partially_correct'] += 1
                else:
                    batch_stats['success_rate']['regular']['incorrect'] += 1
            
            # Track user satisfaction
            if result.get('user_satisfied', False):
                satisfied_count += 1
                
            # Track alignment scores
            if 'initial_alignment_score' in result and result['initial_alignment_score']:
                init_score = result['initial_alignment_score']
                satisfied = init_score.get('satisfied', 0)
                total = init_score.get('total', 0)
                initial_satisfied_conditions += satisfied
                initial_total_conditions += total
                
            if 'final_alignment_score' in result and result['final_alignment_score']:
                final_score = result['final_alignment_score']
                satisfied = final_score.get('satisfied', 0)
                total = final_score.get('total', 0)
                final_satisfied_conditions += satisfied
                final_total_conditions += total
                
            # Aggregate LLM calls
            if 'llm_calls' in result:
                for agent_type, calls in result['llm_calls'].items():
                    total_llm_calls += calls
                    if agent_type == 'user':
                        user_agent_calls += calls
                    elif agent_type == 'maintainer':
                        maintainer_agent_calls += calls
                    elif agent_type == 'judge':
                        judge_agent_calls += calls
        
        # Calculate statistics
        
        # Calculate conversation statistics
        if total_issues > 0:
            batch_stats['conversation_stats']['average_original_comments'] = total_original_comments / total_issues
            batch_stats['conversation_stats']['average_conversation_rounds']['overall'] = total_rounds / total_issues
            batch_stats['conversation_stats']['rounds_to_original_ratio'] = total_rounds / total_original_comments if total_original_comments > 0 else 0
            
        if docker_results:
            docker_rounds = sum(r.get('total_conversation_rounds', 0) for r in docker_results)
            batch_stats['conversation_stats']['average_conversation_rounds']['docker'] = docker_rounds / len(docker_results)
        if regular_results:
            regular_rounds = sum(r.get('total_conversation_rounds', 0) for r in regular_results)
            batch_stats['conversation_stats']['average_conversation_rounds']['regular'] = regular_rounds / len(regular_results)
        
        # Calculate user satisfaction statistics
        if total_issues > 0:
            batch_stats['user_satisfaction']['satisfied'] = satisfied_count
            batch_stats['user_satisfaction']['not_satisfied'] = total_issues - satisfied_count
            batch_stats['user_satisfaction']['satisfaction_rate'] = satisfied_count / total_issues
            
        # Calculate alignment score statistics
        if initial_total_conditions > 0:
            initial_satisfaction_rate = initial_satisfied_conditions / initial_total_conditions
            batch_stats['alignment_scores']['initial']['satisfied_conditions'] = initial_satisfied_conditions
            batch_stats['alignment_scores']['initial']['total_conditions'] = initial_total_conditions
            batch_stats['alignment_scores']['initial']['avg_satisfaction_rate'] = initial_satisfaction_rate
            
        if final_total_conditions > 0:
            final_satisfaction_rate = final_satisfied_conditions / final_total_conditions
            batch_stats['alignment_scores']['final']['satisfied_conditions'] = final_satisfied_conditions
            batch_stats['alignment_scores']['final']['total_conditions'] = final_total_conditions
            batch_stats['alignment_scores']['final']['avg_satisfaction_rate'] = final_satisfaction_rate
            
            # Calculate improvement rate
            if initial_total_conditions > 0 and initial_satisfaction_rate > 0:
                improvement = (final_satisfaction_rate - initial_satisfaction_rate) / initial_satisfaction_rate
                batch_stats['alignment_scores']['improvement_rate'] = improvement
        
        # Update LLM call statistics
        batch_stats['llm_calls']['total'] = total_llm_calls
        batch_stats['llm_calls']['average_per_issue'] = total_llm_calls / total_issues if total_issues > 0 else 0
        batch_stats['llm_calls']['by_agent']['user'] = user_agent_calls
        batch_stats['llm_calls']['by_agent']['maintainer'] = maintainer_agent_calls
        batch_stats['llm_calls']['by_agent']['judge'] = judge_agent_calls
        
        # Load existing summary if it exists
        all_stats = []
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                all_stats = json.load(f)
                if not isinstance(all_stats, list):
                    all_stats = [all_stats]
        
        # Add new batch stats
        all_stats.append(batch_stats)
        
        # Save updated summary
        with open(summary_file, 'w') as f:
            json.dump(all_stats, f, indent=2)
        
        logger.info(f"Updated summary statistics with batch {batch_num}")
        logger.info(f"User satisfaction rate: {batch_stats['user_satisfaction']['satisfaction_rate']:.2%}")
        logger.info(f"Initial alignment rate: {batch_stats['alignment_scores']['initial']['avg_satisfaction_rate']:.2%}")
        logger.info(f"Final alignment rate: {batch_stats['alignment_scores']['final']['avg_satisfaction_rate']:.2%}")
        logger.info(f"Alignment improvement rate: {batch_stats['alignment_scores']['improvement_rate']:.2%}")
        logger.info(f"Average original conversation length: {batch_stats['conversation_stats']['average_original_comments']:.1f} comments")
        logger.info(f"Average conversation rounds: {batch_stats['conversation_stats']['average_conversation_rounds']['overall']:.1f} rounds")
        logger.info(f"Total LLM calls: {total_llm_calls} (User: {user_agent_calls}, Maintainer: {maintainer_agent_calls}, Judge: {judge_agent_calls})")
        
    except Exception as e:
        logger.error(f"Error saving batch summary: {e}")

def get_processed_issues(output_dir):
    """Get already processed issues by reading the output directory."""
    processed_issues = set()
    
    try:
        # Look for all JSONL files in the output directory
        for filename in os.listdir(output_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(output_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        for line in f:
                            try:
                                result = json.loads(line)
                                # Get issue ID or use question title hash as fallback
                                issue_id = result.get('issue_id') or hash(result.get('question_title', ''))
                                processed_issues.add(issue_id)
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.error(f"Error reading file {filename}: {e}")
                    continue
                    
        logger.info(f"Found {len(processed_issues)} already processed issues")
        return processed_issues
        
    except Exception as e:
        logger.error(f"Error reading output directory: {e}")
        return set()

def process_language_specific_dataset(dataset_path, target_language, output_dir='language_results_gpt'):
    """Process only entries from a specific language in the dataset."""
    # Create language-specific output directory
    language_dir = os.path.join(output_dir, target_language)
    os.makedirs(language_dir, exist_ok=True)
    
    # Get already processed issues
    processed_issues = get_processed_issues(language_dir)
    logger.info(f"Found {len(processed_issues)} already processed issues")
    
    # Create timestamp for new results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Process dataset
    current_batch = []
    batch_size = 10
    batch_num = 1
    processed_count = 0
    skipped_count = 0
    already_processed = len(processed_issues)
    
    try:
        with open(dataset_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    json_content = line[line.find('{'):line.rfind('}')+1]
                    issue_data = json.loads(json_content)
                    
                    # Add debug logging
                    current_language = issue_data.get('language', '').lower()
                    if current_language == target_language.lower():
                        issue_id = issue_data.get('id') or hash(issue_data['first_question']['title'])
                        logger.debug(f"Processing issue {issue_id} for language {current_language}")
                        
                        if skipped_count < already_processed:
                            logger.info(f"Skipping already processed issue {issue_id}")
                            skipped_count += 1
                            continue
                        
                        # Process the issue
                        logger.info(f"Processing new issue: {issue_data['first_question']['title']}")
                        result = process_issue(issue_data)
                        current_batch.append(result)
                        processed_count += 1
                        
                        # Save batch when it reaches batch_size
                        if len(current_batch) >= batch_size:
                            batch_file = os.path.join(language_dir, f'batch_{batch_num}_{timestamp}.jsonl')
                            with open(batch_file, 'w') as f:
                                for res in current_batch:
                                    f.write(json.dumps(res) + '\n')
                            logger.info(f"Saved batch {batch_num} with {len(current_batch)} results")
                            current_batch = []
                            batch_num += 1
                            
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in dataset, skipping entry")
                except Exception as e:
                    logger.error(f"Error processing entry: {e}")
                    
        # Save any remaining results
        if current_batch:
            batch_file = os.path.join(language_dir, f'batch_{batch_num}_{timestamp}.jsonl')
            with open(batch_file, 'w') as f:
                for res in current_batch:
                    f.write(json.dumps(res) + '\n')
            logger.info(f"Saved final batch with {len(current_batch)} results")
        
        # Save processing summary
        summary_file = os.path.join(language_dir, f'summary_{timestamp}.json')
        summary = {
            'language': target_language,
            'timestamp': timestamp,
            'processed_count': processed_count,
            'skipped_count': skipped_count,
            'total_batches': batch_num,
            'completion_time': datetime.now().isoformat()
        }
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Processing complete. Processed: {processed_count}, Skipped: {skipped_count}")
        return language_dir
        
    except Exception as e:
        logger.error(f"Fatal error processing dataset: {e}")
        return None

def setup_language_specific_logging(target_language):
    """Setup logging with language-specific log files."""
    # Configure main application logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(f'maintainer_agent_{target_language}.log'),
            logging.StreamHandler()
        ]
    )
    global logger
    logger = logging.getLogger(__name__)

    # Configure separate LLM interaction logging per language
    global llm_logger
    llm_logger = logging.getLogger(f'llm_interactions_{target_language}_gpt')
    llm_logger.setLevel(logging.INFO)
    llm_handler = logging.FileHandler(f'llm_interactions_{target_language}_gpt.log')
    llm_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    llm_logger.addHandler(llm_handler)
    
    logger.info(f"Set up language-specific logging for {target_language}")

def main():
    """Main function to process specific languages from the dataset."""
    try:
        target_language = "c"  # Change this to the language you want to process
        dataset_path = 'CHANGE_IT_TO_YOUR_PATH' # Generated dataset path
        
        # Set up language-specific logging
        setup_language_specific_logging(target_language)
        
        output_dir = process_language_specific_dataset(dataset_path, target_language)
        
        if output_dir:
            logger.info(f"Successfully processed {target_language} entries. Results in: {output_dir}")
        else:
            logger.error(f"Failed to process {target_language} entries")
            
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")

if __name__ == "__main__":
    main()