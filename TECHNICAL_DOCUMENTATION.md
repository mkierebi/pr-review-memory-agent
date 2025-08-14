# Technical Documentation

## Data Sources

- **GitHub API**: Pull request data, review comments, diff patches
- **Code Changes**: File modifications, line additions/deletions  
- **Review History**: Past reviewer feedback and approval patterns
- **Licensing**: Uses public GitHub API data from repository owner's consent

## Model Architecture

### Embedding Model
- **Provider**: Cohere AI
- **Model**: `embed-english-light-v3.0`
- **Dimensions**: 384
- **Input**: Code chunks + context metadata
- **Output**: Vector embeddings for similarity search

### Text Generation Model  
- **Provider**: Cohere AI
- **Model**: `command-r-plus`
- **Purpose**: Generate review comments based on similar past reviews
- **Temperature**: 0.3 (balanced creativity/consistency)

### Vector Storage
- **Engine**: FAISS (Facebook AI Similarity Search)
- **Index Type**: Flat L2 distance
- **Storage**: Local files on memory branch
- **Similarity Threshold**: Dynamic (0.2-0.4 based on memory size)

## System Architecture

```
GitHub PR → extract_review.py → Cohere Embeddings → FAISS Index
                ↓
New PR → generate_review.py → Similarity Search → Cohere Generation → post_review.py
```

## Evaluation Methodology

### Test Setup
```bash
# Test review generation
python scripts/generate_review.py

# Expected output format:
🔍 Analyzing PR for auto-review...
📚 Loaded memory with X past reviews  
📝 Found N code chunks to review
🔎 Found M chunks with similar past reviews
💬 Generated K review comments
✅ Review generated successfully
```

### Success Criteria
- **Similarity Detection**: Finds relevant past reviews (similarity > 0.2)
- **Comment Generation**: Produces contextual feedback
- **Line Positioning**: Maps comments to correct code lines
- **API Integration**: Successfully posts to GitHub

### Test Results (Latest)
```
📚 Loaded memory with 3 past reviews
📝 Found 1 code chunks to review  
🔎 Found 1 chunks with similar past reviews
Generated review for PaymentController.java:0
💬 Generated 1 review comments
✅ Review generated successfully
```

**Status**: ✅ Core functionality working
**Issue**: Line positioning showing `:0` instead of actual line numbers

## Known Limitations

1. **Repository Scope**: Limited to single repository with local memory branch
2. **Line Positioning**: Currently maps to line 0, needs diff position calculation fix
3. **Memory Persistence**: Requires manual memory branch maintenance
4. **API Dependencies**: Relies on Cohere API availability
5. **Context Window**: Limited by model token limits for large files

## Improvement Areas

1. **Multi-Repository Support**: Centralized embedding storage across repositories
2. **Rule-Based Enhancement**: Integrate with static analysis tools and coding guidelines  
3. **Learning Feedback Loop**: Incorporate reviewer feedback on generated comments
4. **Advanced Positioning**: Better diff-to-line mapping for inline comments
5. **Performance Optimization**: Caching and incremental embedding updates
