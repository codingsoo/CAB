# CAB (CodeAssistBench) Dataset Card

## Dataset Summary

**Name:** CAB (CodeAssistBench)  
**Version:** 1.0  
**Release Date:** 2025  
**License:** CC-BY-NC 4.0  
**Paper:** [arXiv:2507.10646](https://arxiv.org/abs/2507.10646)  
**Venue:** NeurIPS 2025 Datasets & Benchmarks Track  

CAB is a comprehensive benchmark dataset for evaluating AI coding assistants on real-world programming problems. It contains GitHub issues with verified solutions, user satisfaction criteria, and Docker environment requirements.

## Dataset Description

### Purpose
This dataset enables researchers to evaluate AI coding assistants on realistic programming problems with human-verified solutions and satisfaction criteria.

### Dataset Composition
- **Source:** GitHub issues from top-starred repositories
- **Languages:** C, C++, C#, Java, JavaScript, Python, TypeScript
- **Size:** < 1 million outputs, < 1 GB total
- **Format:** JSONL with structured issue data

### Data Collection
- **Repositories:** Top 100-1000 starred repositories per language
- **Issues:** Closed issues with "question" or "help wanted" labels
- **Filtering:** Multi-stage LLM-based quality filtering
- **Verification:** Human-verified solutions and satisfaction criteria

## Dataset Structure

### Fields
- `language`: Programming language
- `issue_id`: GitHub issue number
- `title`: Issue title
- `body`: Issue description
- `created_at`: Issue creation timestamp
- `comments`: Conversation thread
- `satisfaction_conditions`: User requirements
- `docker_classification`: Environment requirements
- `url`: GitHub issue URL

### Example Entry
```json
{
  "language": "python",
  "issue_id": 1234,
  "title": "TypeError when using pandas DataFrame",
  "body": "I'm getting a TypeError when...",
  "created_at": "2024-01-01T00:00:00Z",
  "comments": [...],
  "satisfaction_conditions": [
    "The solution should resolve the TypeError",
    "The code should be maintainable"
  ],
  "docker_classification": "no_need_docker",
  "url": "https://github.com/owner/repo/issues/1234"
}
```

## Usage

### Intended Use
- **Research:** Evaluating AI coding assistant performance
- **Benchmarking:** Comparing different AI models
- **Analysis:** Studying problem-solution patterns

### Prohibited Uses
- **Commercial use:** Prohibited under CC-BY-NC 4.0
- **Model training:** Requires explicit legal approval
- **Redistribution:** Must comply with original repository licenses

## Licensing

### Dataset License: CC-BY-NC 4.0
- **Attribution required:** Must cite the dataset and paper
- **Non-commercial:** Commercial use prohibited
- **Share-alike:** Derivative works must use same license

### Source Data Licenses
- **GitHub repositories:** Under their respective open source licenses
- **User compliance:** Must abide by original repository terms
- **Citation required:** All source repositories must be cited

## Dataset Creation

### Data Sources
- **GitHub API:** Public repository data
- **Issue filtering:** LLM-based quality assessment
- **Human verification:** Manual solution validation
- **Docker classification:** Environment requirement analysis

### Processing Pipeline
1. **Repository collection:** Top-starred repositories per language
2. **Issue extraction:** GitHub issues with relevant labels
3. **Quality filtering:** Multi-stage LLM filtering
4. **Satisfaction extraction:** User requirement identification
5. **Environment classification:** Docker requirement analysis
6. **Dataset assembly:** Structured JSONL format

### Quality Assurance
- **Multi-stage filtering:** LLM-based quality assessment
- **Human verification:** Manual solution validation
- **Docker testing:** Environment reproducibility
- **Citation tracking:** Source repository attribution

## Dataset Statistics

### Size
- **Total issues:** ~10,000
- **Languages:** 7 programming languages
- **Repositories:** ~500 total
- **File size:** < 1 GB

### Distribution
- **Python:** ~2,500 issues
- **JavaScript:** ~2,000 issues
- **TypeScript:** ~1,500 issues
- **Java:** ~1,500 issues
- **C++:** ~1,000 issues
- **C#:** ~1,000 issues
- **C:** ~500 issues

### Quality Metrics
- **Solution coverage:** 100% of issues have verified solutions
- **Satisfaction criteria:** 100% have user requirements
- **Docker classification:** 100% have environment requirements
- **Citation coverage:** 100% of source repositories cited

## Access and Download

### Repository Access
- **GitHub:** https://github.com/your-org/CodeAssistBench
- **Access control:** Public repository with proper licensing
- **Documentation:** Complete setup and usage guides

### Download Instructions
```bash
git clone https://github.com/your-org/CodeAssistBench.git
cd CodeAssistBench
python cab_cli.py demo  # Try demo mode
```

## Citation

### Dataset Citation
```bibtex
@inproceedings{kim2025codeassistbench,
  title={CodeAssistBench (CAB): Dataset & Benchmarking for Multi-turn Chat-Based Code Assistance}, 
  author={Myeongsoo Kim and Shweta Garg and Baishakhi Ray and Varun Kumar and Anoop Deoras},
  booktitle={Advances in Neural Information Processing Systems (NeurIPS)},
  year={2025},
  track={Datasets and Benchmarks}
}
```

### Source Repository Citations
All source repositories are properly cited in the dataset. Users must comply with their original licenses and citation requirements.

## Contact and Support

### Dataset Questions
- **Issues:** GitHub Issues for bug reports
- **Discussions:** GitHub Discussions for questions
- **Email:** your-email@university.edu

### Legal Questions
- **License compliance:** See LICENSE file
- **Commercial use:** Contact dataset maintainers
- **Model training:** Requires explicit legal approval

## Important Notices

### Usage Restrictions
- **Generated by Claude; do not use for model training without Legal approval**
- This dataset is intended for research and evaluation purposes only
- Commercial use is prohibited under CC-BY-NC 4.0
- Do not use for training AI models without explicit legal approval

### Dataset Scope
- This dataset is limited to the data needed to understand and reproduce the findings described in the NeurIPS 2025 Datasets & Benchmarks Track paper
- The dataset contains less than one million outputs and is under one gigabyte in size
- The dataset is maintained in an access-controlled repository

### Third-Party Data
- This dataset incorporates data from GitHub repositories
- Users must comply with the original licenses of the source repositories
- All source repositories are properly cited in the dataset documentation
