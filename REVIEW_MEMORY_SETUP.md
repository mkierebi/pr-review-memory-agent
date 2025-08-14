# 🧠 PR Review Memory System

Automated - Extracts comments from reviews
- Creates embeddings via Cohere API
- Saves in FAISS index on `memory` branch

### `auto-review.yml`  
**Trigger**: `pull_request` (opened/synchronize)
- Analyzes PR changes
- Searches similar cases from memory
- Generates contextual suggestions via Cohere
- Posts comments on PR learning from GitHub PR review history that uses Cohere embeddings and FAISS to provide contextual review suggestions.

## 🎯 How It Works

1. **Knowledge Collection**: Each PR review → embeddings → stored in `memory` branch
2. **Auto Review**: New PR → search similar cases → generate suggestions via Cohere

## 🚀 Setup

### 1. GitHub Secrets

Add in Settings → Secrets and variables → Actions:

```bash
COHERE_API_KEY=your_cohere_api_key_here
```

### 2. Create Memory Branch

```bash
# Automatically created by first workflow, but can be created manually:
git checkout --orphan memory
git rm -rf .
mkdir memory_data
echo '{"embeddings": [], "metadata": {"version": "1.0"}}' > memory_data/metadata.json
git add memory_data/metadata.json
git commit -m "Initialize memory branch"
git push origin memory
```

### 3. Permissions

In Settings → Actions → General → Workflow permissions:
- ✅ **Read and write permissions**
- ✅ **Allow GitHub Actions to create and approve pull requests**

## 📋 Workflows

### `collect-reviews.yml`
**Trigger**: `pull_request_review` + `pull_request_review_comment`
- Extracts comments from reviews
- Creates embeddings via Cohere API
- Saves in FAISS index on `memory` branch

### `auto-review.yml`  
**Trigger**: `pull_request` (opened/synchronize)
- Analyzes PR changes
- Searches similar cases from memory
- Generates contextual suggestions via Cohere model
- Posts comments on PR

## 🛠 Components

### Core Files
- `scripts/claude_embeddings.py` - Cohere API integration + embedding management (filename kept for compatibility)
- `scripts/faiss_memory_manager.py` - FAISS vector storage + similarity search
- `scripts/extract_review.py` - Extract reviews from GitHub events
- `scripts/generate_review.py` - Generate automatic reviews
- `scripts/post_review.py` - Post comments to GitHub

### Memory Structure
```
memory/ branch:
├── memory_data/
│   ├── faiss.index          # FAISS vector index
│   └── metadata.json        # Review metadata + mappings
```

## 🔧 Configuration

### Environment Variables
```bash
GITHUB_TOKEN=automatic        # Provided by GitHub Actions
COHERE_API_KEY=required       # Your Cohere API key for embeddings and review generation
PR_NUMBER=automatic          # From GitHub event
REPO_NAME=automatic          # From GitHub context
```

### Customization

In `claude_embeddings.py` (filename kept for compatibility):
- **Similarity threshold**: `min_similarity=0.3` (30%)
- **Embedding dimension**: `dimension=384`
- **Top results**: `top_k=5`

In `generate_review.py`:
- **Chunk size**: `max_lines=20`
- **Cohere model**: `command-r-plus`
- **Max tokens**: `300`

## 📊 Example Usage

### 1. Review submission
```
PR #123: "Fix null pointer exception"
Review: "Should validate input parameters before processing"
→ Embedding created → Stored in memory
```

### 2. New PR analysis  
```
PR #456: Similar null handling code
→ Finds similar pattern (85% similarity)
→ Suggests: "Consider validating input parameters (based on past review by @senior-dev)"
```

### 3. Comment format
```markdown
This method should validate the payment object for null values before processing

---
🤖 This suggestion is based on 2 similar past review(s) by @senior-dev (similarity: 85%)
📋 Related areas: security, validation
```

## 🎯 Features

- **Smart chunking**: Splits large diffs into smaller reviewable chunks
- **Context awareness**: Considers filename, PR title, code context
- **Tag extraction**: Automatic tagging (security, performance, style, etc.)
- **Similarity filtering**: Only relevant suggestions (>30% similarity)
- **Fallback handling**: General comments if inline fails
- **Batch processing**: Efficient embedding storage
- **Memory persistence**: Incrementally updated knowledge base

## 🚨 Troubleshooting

### Workflow not working?
1. Check if `COHERE_API_KEY` is set
2. Verify repo permissions (write access)
3. Check if memory branch exists

### No suggestions?
1. Memory might be empty (first PRs)
2. **Context mismatch** - Ensure embedding context format is consistent between storage and search
3. Check Cohere API quota/limits
4. Low similarity threshold - try lowering min_similarity in generate_review.py

### Error in comments?
1. PR might be too large (rate limiting)
2. File paths changed between review and post
3. GitHub API rate limits

### Context Format Issue (Fixed)
**Problem**: Embeddings were stored with context format `"PR #X in repo"` but searched with `"File: X Changes: +Y -Z"`, causing 0% similarity matches.

**Solution**: Updated `generate_review.py` to use consistent context format for both storage and search operations.

## 📈 Monitoring

### Memory stats
```bash
git checkout memory
python -c "
from scripts.faiss_memory_manager import FAISSMemoryManager
m = FAISSMemoryManager()
m.load_from_files('memory_data/faiss.index', 'memory_data/metadata.json')
print(m.get_stats())
"
```

### Workflow logs
- GitHub Actions → Repository → Actions tab
- Check individual workflow runs for detailed logs

## 🔒 Security Notes

- Cohere API key stored as GitHub Secret
- Memory branch contains only embeddings, not raw code
- No sensitive data in embeddings (hashed IDs)
- GitHub token auto-scoped to repository

## 🚀 Extensions

### Possible improvements:
1. **Custom tagging** - Team-specific categories
2. **Reviewer weighting** - Trust scores based on experience  
3. **File type awareness** - Different models per language
4. **Integration with IDE** - VSCode extension
5. **Analytics dashboard** - Review patterns visualization
6. **A/B testing** - Compare human vs AI review effectiveness