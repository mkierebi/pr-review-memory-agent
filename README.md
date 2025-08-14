# PR Review Memory Agent

Automated PR review system that learns from past code reviews using AI embeddings and provides intelligent feedback based on historical patterns.

## Quick Start

### Setup in Target Repository

Copy these folders from this repository to your target repository:

```
.github/          # GitHub Actions workflows
scripts/          # Core Python scripts
memory_data/      # FAISS index storage (auto-created)
```

### Required Files

1. **`.github/workflows/`**
   - `collect-reviews.yml` - Collects and stores past reviews
   - `auto-review.yml` - Generates automated reviews

2. **`scripts/`**
   - `extract_review.py` - Extracts reviews and creates embeddings
   - `generate_review.py` - Generates new reviews based on similarity
   - `post_review.py` - Posts review comments to GitHub
   - `claude_embeddings.py` - Cohere API integration
   - `faiss_memory_manager.py` - Vector similarity search
   - `call_cohere_api.py` - Cohere text generation
   - `review_rules.txt` - Additional review guidelines

3. **`requirements.txt`** - Python dependencies

### Environment Setup

Set these GitHub repository secrets:

```
COHERE_API_KEY=your_cohere_api_key
GITHUB_TOKEN=automatic_github_token
```

### Usage

1. **Collect Reviews**:
   - Create new PR containing sample code with issues
   - Add inline reviews
   - Reviews will be analyzed and embeddings created in memory branch

2. **Auto-Review New PRs**:
   - System automatically triggers on new PRs
   - Finds similar past reviews using vector similarity
   - Generates contextual feedback using Cohere AI
   - Posts inline or general comments

## Testing Branches

- **`create_embeddings`** - Contains sample PR for manual review collection
- **`test_auto_review`** - Test branch for automated review generation
- **`memory`** - Stores collected review embeddings and metadata

## Requirements

- Python 3.9+
- Cohere API access
- GitHub repository with Actions enabled

```
pip install -r requirements.txt
```

## How It Works

1. **Collection Phase**: Extracts reviews from PR comments, generates embeddings
2. **Storage Phase**: Stores embeddings in FAISS vector database on memory branch  
3. **Review Phase**: For new PRs, finds similar past reviews and generates feedback
4. **Posting Phase**: Posts intelligent comments based on historical patterns
