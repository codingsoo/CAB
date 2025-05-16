# Repository Structure

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

## Note
The date cutoff (November 1, 2024) for recent repositories is specifically chosen to avoid data leakage in model training and evaluation.