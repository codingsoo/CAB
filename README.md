# CAB: CodeAssistBench

## Overview
This repository contains two main directories: `issue` and `repo`, organizing GitHub data based on time periods and filtering stages.

## Directory Structure

### 📁 repo/
Contains repository information categorized by time periods.

#### 📂 all/
- Top 100 starred repositories
- Includes `top_20/` subdirectory with repositories selected based on:
  - Active "help wanted" and "question" issue tags
  - Priority given to repositories with higher issue counts when scores are tied

#### 📂 recent/
- Top 1000 starred repositories created after November 1, 2024
- Includes `top_20/` subdirectory with similar selection criteria as `all/`

### 📁 issue/
Contains processed GitHub issues with various filtering stages.

#### Common Structure for both `all/` and `recent/`:
```text
issue/
├── conv_filter/       # Issues after conversation filtering
├── virtual_user/      # Extracted satisfactory conditions
├── msg_filter/        # Issues after message filtering
├── regex_filter/      # Issues after regex filtering
└── docker_filter/     # Issues after docker filtering
    ├── c/
        ├── build_env               # Issues with docker environment
        ├── need_docker             # Issues require docker environment
        ├── need_docker_but_cannot  # Issues require docker environment, but we cannot dockerize them due to constraints such as hardware dependency, network dependency, ...
        └── no_need_docker          # Issues do not require docker environment
    ├── c#/
    ├── cpp/
    ├── java/
    ├── javascript/
    ├── python/
    └── typescript/
```
Each programming language directory contains individual repository files with their respective processed issues.

## Quick‑Start Guide

### 1 ― Prerequisites
- **Python >= 3.12** (tested on 3.12.6)
- A GitHub **Personal Access Token (classic)** with at least `public_repo` scope.
- `pip` (comes with Python) and optionally `virtualenv`/`venv` for isolated environments.

### 2 ― Installation
```bash
# 1. Clone the repo
$ git clone https://github.com/<your‑org>/CodeAssistBench.git
$ cd CodeAssistBench

# 2. (Recommended) create an isolated environment
$ python -m venv .venv
$ source .venv/bin/activate     # PowerShell: .venv\Scripts\Activate.ps1

# 3. Install Python dependencies
$ pip install --upgrade pip
$ pip install -r requirements.txt
```

### 3 ― Configure Secrets
Create a **.env** file in the project root and paste your token:
```dotenv
GITHUB_TOKEN=ghp_yourpersonalaccesstoken
```
> **Tip 📌** Create the token at <https://github.com/settings/tokens> → **Classic tokens**.  
> The script prints your remaining request quota before and after each run.

### 4 ― Collect Repository Data (`get_github_repo.py`)
Run the helper script to build an initial CSV of repositories matching your criteria:
```bash
$ python get_github_repo.py   # formerly get_github_issue.py in v1.0
```
The script is interactive by default:  
1. Choose a language from the menu (e.g. `Python`).  
2. Enter how many repositories you want to analyse (e.g. `500`).  
3. Optionally override the cutoff date (`YYYY‑MM‑DD`).

A CSV named like `python_repos_analysis_YYYYMMDD_HHMMSS.csv` is written to the project root with community‑score metrics.

### 5. Extract & Validate Issue-Level Q&A (`get_github_issue.py`)

Once you’ve generated your repo CSV in Step 4, run:

```bash
python get_github_issue.py
```

#### Interactive prompts
1. **CSV path**  
   Path to the file you created in Step 4 (e.g. `python_repos_analysis_20250522_113015.csv`).

2. **Label-based filtering**  
   - Enter `y` to restrict crawling to issues labeled `question` or `help wanted`.  
   - Enter `n` to scan *all* closed issues.

#### What the script does

| Phase               | Description                                                                                                     |
| ------------------- | --------------------------------------------------------------------------------------------------------------- |
| 🔄 **Fetch issues**   | Calls the GitHub REST API (page-by-page), respecting rate limits.                                                |
| ⚙️ **Deduplicate**    | Merges duplicates when an issue carries multiple labels.                                                       |
| 🚫 **Apply filters**  | Keeps only issues with contributions from **multiple authors** and **no external media** (URLs/images/videos). |
| 💬 **Fetch comments** | Pulls the full discussion thread for each retained issue.                                                     |
| 💾 **Persist**        | Writes one timestamped JSON file per repo:  
  `github_issues_<owner>_<repo>_YYYYMMDD_HHMMSS.json`.                                                            |

#### Output
- **Console summary:** counts of processed, skipped (single-author or media-heavy), and retained issues.  
- **JSON files:** one per repository, each containing clean Q&A pairs ready for downstream analysis.

### 6. Filter & Qualify Conversations (`conv_filter.py`)
Once Step 5 is complete, run:

```bash
python conv_filter.py
```

#### What the script does

| Phase                     | Description                                                                                                                                       |
|---------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| 🤖 Init Bedrock client     | Configures AWS Bedrock runtime with your region & model.                                                                                           |
| 🔍 Load issues             | Reads each `*.json` from `input_dir`.                                                                                                             |
| 📝 Evaluate issue          | Sends title, body, and comments to the LLM; answers 7 Yes/No questions (`resolved`, `clear solution`, `PII-free`, `reproducible`).                 |
| ✅ Filter qualified issues | Retains only issues meeting all criteria: non-self-answered, technically specific, solution-contained, PII-free, reproducible.                       |
| 💾 Persist results         | Writes filtered issues to `output_dir/<owner>_<repo>.json` and logs every LLM interaction to:  
  - `llm_responses.jsonl`  
  - `evaluation_results.jsonl`  |


#### Output

Filtered JSON files in `output_dir`, each containing only the qualified Q&A.  
LLM logs under your chosen `output_log_dir` (raw inputs, outputs, timings, metadata).

### 7. Filter Irrelevant Comments (`msg_filter.py`)

Once Step 6 is complete, run:

```bash
python msg_filter.py
```

#### What the script does

| Phase                         | Description                                                                           |
|-------------------------------|---------------------------------------------------------------------------------------|
| 🤖 Init Bedrock client         | Configures AWS Bedrock runtime with your region & model.                               |
| 🔄 Merge comments              | Combines consecutive comments from the same author into a single entry.                |
| 🗑️ Identify irrelevant comments | Uses an LLM to detect and list comments with no support-related value.                 |
| 🔍 Filter conversation         | Removes purely social or off-topic comments while preserving technical discussion.     |
| 💾 Persist results             | Writes filtered issues to `output_dir` and logs raw LLM responses under `logs/`.       |

#### Output

Filtered JSON files in `output_dir`, each containing only issues with relevant comments. Raw LLM logs written to `output_dir/logs/raw_responses_<timestamp>.jsonl`.

### 8. Extract User Satisfaction Conditions (`scon_filter.py`)
Once Step 7 is complete, run:

```bash
python scon_filter.py
```

#### What the script does

| Phase                              | Description                                                                                                            |
|------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| 🤖 Init Bedrock client              | Configures AWS Bedrock runtime with your region & model.                                                                |
| 📂 Load conversations               | Reads each `*.json` from the specified `input_dir`.                                                                    |
| 📋 Extract satisfaction conditions   | Uses an LLM to identify general user satisfaction criteria (what the user needed, not the specific solution).           |
| ✅ Verify conditions                | Validates which extracted conditions are actually satisfied by the original conversation context.                     |
| 💾 Persist results                  | Saves conversations augmented with `satisfaction_conditions` to `output_dir` and writes prompts/responses logs.       |

#### Output

Processed JSON files in `output_dir`, each containing conversations with `satisfaction_conditions`.  
Prompts and responses saved to `output_dir/<filename>_prompts_responses.json`.

### 9. Classify Docker Needs (`docker_filter.py`)
Once Step 8 is complete, run:

```bash
python docker_filter.py
```

#### What the script does

| Phase                             | Description                                                                                                                             |
|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| 🤖 Init Bedrock client             | Configures AWS Bedrock runtime with your region & model.                                                                                 |
| 📂 Load filtered conversations      | Reads each `*.json` from the `scon_filter` output directory.                                                                              |
| 📑 Classify Docker requirement      | Uses an LLM to determine if each issue:  
1. Does not need build environment  
2. Can be dockerized without any issue  
3. Requires build environment but hard to be dockerized                                                        |
| 💾 Save classifications             | Writes issues into `need_docker`, `no_need_docker`, or `need_docker_but_cannot` subdirectories.                                         |
| 📂 Persist LLM logs                 | Stores raw prompts and responses in `llm_responses/`.                                                                                   |
| 📊 Generate summary                 | Aggregates counts and percentages into `classification_summary.json` and `processed_issues.json`.                                        |

#### Output

- Issues sorted into:
  - `no_need_docker`: issues that can be verified without a build environment
  - `need_docker`: issues that require Docker for verification
  - `need_docker_but_cannot`: issues requiring build environment but difficult to containerize
- Raw LLM logs under `llm_responses/`.
- Summary statistics in `classification_summary.json` and processed IDs in `processed_issues.json`.


### 10. Fetch GitHub Commits & Generate Dockerfiles  
Once Step 9 is complete, run both scripts in sequence:

```bash
python get_github_commit.py
python generate_dockerfile.py
```

#### What the scripts do

| Phase                                 | Description                                                                                                                      |
|---------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| 🤖 Init GitHub & Bedrock clients       | Configures the GitHub API client (using your `GITHUB_TOKEN`) and the Bedrock LLM client.                                         |
| 📥 Load filter output                  | Reads each `*.json` from the `scon_filter` and `docker_filter/need_docker` directories.                                         |
| ⏳ Fetch commits                        | For each repo, calls GitHub’s API to retrieve all commits up to the latest issue date.                                          |
| 📝 Save commit data                    | Persists a `commits_<source>.json` file containing SHA, author, date, and message for each commit.                              |
| 🐳 Generate Dockerfile candidates      | Uses an LLM to produce Dockerfile candidates for each issue, based on repo state, commit SHA, README, workflows, and errors.     |
| 🔄 Improve & retest Dockerfiles        | Iteratively fixes failed builds by feeding error logs back to the LLM, generating improved Dockerfile versions.                 |
| 📂 Persist Dockerfiles & logs          | Writes final Dockerfile(s) under `build_env/`, stores detailed failure logs in `issue_build_failure_logs/` and LLM logs in `llm_logs/`. |
| 📊 Generate summary                    | Outputs a build summary with success rates, LLM call counts, and timing into the console and a JSON summary file.               |

#### Output

- **Commit data**: `github_commits/commits_<repo>.json`  
- **Dockerfiles**: Written to `build_env/issue_<repo>_<number>.json` on success  
- **Failure logs**: JSON files in `issue_build_failure_logs/` with error & explanation  
- **LLM logs**: Timestamped `.log` files in `llm_logs/`  
- **Build summary**: Printed to console and saved in `classification_summary.json` and per-issue output files  

### 11. Generate Dataset

Run the `generate_dataset.py` script to produce a newline-delimited JSON file:

```bash
python generate_dataset.py
```

#### What the script does

| Phase               | Description                                                                                          |
|---------------------|------------------------------------------------------------------------------------------------------|
| 📂 Load source      | Scans each language subdirectory under `.../docker_filter/{language}/build_env` and `.../no_need_docker` |
| 📝 Parse issue data | Extracts repository URL, issue metadata, comments, satisfaction conditions, and Dockerfile content    |
| 🔗 Resolve commits  | Finds the latest commit SHA on or before each issue’s `created_at` using your `github_commits` files |
| 📑 Format entries   | Builds one JSON object per issue with the following fields:                                          |
|                     | • `language`                                                                                         |
|                     | • `commit_info.repository` and `commit_info.latest_commit.sha`                                       |
|                     | • `first_question.title` and `first_question.body`                                                   |
|                     | • `comments` (array)                                                                                 |
|                     | • `user_satisfaction_condition` (array)                                                              |
|                     | • `created_at`                                                                                       |
|                     | • `dockerfile` (only for `build_env` issues)                                                         |
| 💾 Write JSONL      | Appends each JSON object as a new line in `dataset_all.jsonl`                                        |
| 📊 Print statistics | Logs total entries, per-language counts, build_env vs. no_need_docker breakdown, and commit coverage |

#### Format of each dataset entry

```json
{
  "language": "python",
  "commit_info": {
    "repository": "https://github.com/owner/repo",
    "latest_commit": { "sha": "abc123..." }
  },
  "first_question": {
    "title": "Issue title here",
    "body": "Full issue body text here"
  },
  "comments": [ /* array of comment objects */ ],
  "user_satisfaction_condition": [ /* array of strings */ ],
  "created_at": "2024-05-01T12:34:56Z",
  "dockerfile": "FROM ubuntu:20.04\n..."  // only present for build_env issues
}
```

#### Output
- **Dataset file**: dataset_all.jsonl — one JSON object per line, ready for downstream analysis or model training.

## Logs & Reproducibility

Both logs capture raw LLM interactions end‑to‑end, including prompts and tool calls, to enable full reproducibility of our pipeline.

- 📄 A full trace of the benchmark build process can be found in the raw LLM log:  
[LLM Log (Benchmark Generation)](https://drive.google.com/file/d/1riLanOSGZfmYsPAvTCUx9eeh4iK_ex0d/view?usp=sharing)
- 📄 A full trace of the empricial study process can be found in the raw LLM log: 
[LLM Log (Experiment Run)](https://drive.google.com/file/d/1UCj5v-o3olwjYM5lyIbWjts4LyrMDZLT/view?usp=sharing)

## Note
The date cutoff (November 1, 2024) for recent repositories is specifically chosen to avoid data leakage in model training and evaluation.