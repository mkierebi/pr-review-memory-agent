"""
Generate automated PR review using stored memory embeddings
"""

import os
import json
import sys
from github import Github
from claude_embeddings import CohereEmbeddingClient, ReviewEmbeddingManager
from faiss_memory_manager import FAISSMemoryManager
import requests
from typing import List, Dict, Tuple

from call_claude_api import call_claude_api
from post_review import load_review_context


def get_pr_changes():
    """Get PR changes and file diffs"""
    
    github_token = os.getenv('GITHUB_TOKEN')
    pr_number = int(os.getenv('PR_NUMBER'))
    repo_name = os.getenv('REPO_NAME')
    base_sha = os.getenv('BASE_SHA')
    head_sha = os.getenv('HEAD_SHA')
    
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    # Get changed files
    files = pr.get_files()
    
    changes = []
    for file in files:
        if file.patch and file.status in ['modified', 'added']:
            # Split patch into chunks for better processing
            chunks = split_patch_into_chunks(file.patch, file.filename)
            changes.extend(chunks)
    
    return changes, pr, repo


def split_patch_into_chunks(patch: str, filename: str, max_lines: int = 20) -> List[Dict]:
    """Split large patches into smaller reviewable chunks"""
    
    chunks = []
    lines = patch.split('\n')
    current_chunk = []
    hunk_header = None
    
    for line in lines:
        if line.startswith('@@'):
            # Save previous chunk if exists
            if current_chunk and hunk_header:
                chunks.append({
                    'filename': filename,
                    'hunk_header': hunk_header,
                    'code_chunk': '\n'.join(current_chunk),
                    'added_lines': [l for l in current_chunk if l.startswith('+')],
                    'removed_lines': [l for l in current_chunk if l.startswith('-')]
                })
            
            # Start new chunk
            hunk_header = line
            current_chunk = []
        else:
            current_chunk.append(line)
            
            # Split large chunks
            if len(current_chunk) >= max_lines and any(l.startswith(('+', '-')) for l in current_chunk[-5:]):
                if hunk_header:
                    chunks.append({
                        'filename': filename,
                        'hunk_header': hunk_header,
                        'code_chunk': '\n'.join(current_chunk),
                        'added_lines': [l for l in current_chunk if l.startswith('+')],
                        'removed_lines': [l for l in current_chunk if l.startswith('-')]
                    })
                current_chunk = []
    
    # Add final chunk
    if current_chunk and hunk_header:
        chunks.append({
            'filename': filename,
            'hunk_header': hunk_header,
            'code_chunk': '\n'.join(current_chunk),
            'added_lines': [l for l in current_chunk if l.startswith('+')],
            'removed_lines': [l for l in current_chunk if l.startswith('-')]
        })
    
    return chunks


def find_similar_past_reviews(code_chunks: List[Dict], memory_manager: FAISSMemoryManager, cohere_client: CohereEmbeddingClient, pr_info: Dict) -> List[Dict]:
    """Find similar past reviews for code chunks"""
    
    review_suggestions = []
    
    # Adjust similarity threshold based on memory size
    # If we have very few past reviews, be more lenient to provide some feedback
    memory_size = memory_manager.index.ntotal
    if memory_size <= 5:
        min_similarity = 0.2  # Lower threshold for small memory
    elif memory_size <= 10:
        min_similarity = 0.3  # Medium threshold
    else:
        min_similarity = 0.4  # Standard threshold
    
    print(f"🎯 Using similarity threshold: {min_similarity} (memory size: {memory_size})")
    
    for chunk in code_chunks:
        # Generate embedding for current code chunk using same context format as storage
        context = f"PR #{pr_info.get('pr_number', 'unknown')} in {pr_info.get('repo', 'unknown')}"
        query_embedding = cohere_client.generate_review_embedding(chunk['code_chunk'], context)
        
        # Search for similar reviews
        similar_reviews = memory_manager.search_similar(
            query_embedding, 
            top_k=3, 
            min_similarity=min_similarity
        )
        
        if similar_reviews:
            suggestion = {
                'file': chunk['filename'],
                'hunk_header': chunk['hunk_header'],
                'code_chunk': chunk['code_chunk'],
                'similar_reviews': []
            }
            
            for review_embedding, similarity in similar_reviews:
                suggestion['similar_reviews'].append({
                    'similarity': similarity,
                    'comment': review_embedding.review_comment,
                    'reviewer': review_embedding.reviewer,
                    'tags': review_embedding.tags,
                    'original_code': review_embedding.code_chunk[:200] + "..." if len(review_embedding.code_chunk) > 200 else review_embedding.code_chunk
                })
            
            review_suggestions.append(suggestion)
    
    return review_suggestions


def build_review_prompt(code_chunk, review_context):
    return f"""You are a code reviewer.
Review the following code according to these guidelines:

{review_context}

Code to review:
{code_chunk}

List any issues found, referencing the guidelines. If everything is OK, say so.
"""


def generate_review_comments_with_cohere(review_suggestions: List[Dict], pr_info: Dict) -> List[Dict]:
    """Use Cohere to generate contextual review comments based on similar past reviews"""
    
    cohere_api_key = os.getenv('COHERE_API_KEY')
    if not cohere_api_key:
        print("❌ COHERE_API_KEY not found in environment variables")
        return []

    review_comments = []
    review_context = load_review_context()
    
    for suggestion in review_suggestions:
        # Build prompt for review generation
        similar_reviews_text = "\n".join([
            f"- Reviewer {sr['reviewer']}: {sr['comment']} (similarity: {sr['similarity']:.2f})"
            for sr in suggestion['similar_reviews']
        ])
        
        prompt = f"""You are a code reviewer analyzing this code change.

Code to review:
```
{suggestion['code_chunk']}
```

File: {suggestion['file']}

Similar past reviews for reference:
{similar_reviews_text}

Additional context:
{review_context}

Based on the similar past reviews and the code change, provide a constructive review comment. Focus on:
1. Issues that were caught in similar past reviews
2. Best practices from past reviews
3. Consistency with previous feedback patterns

If the similar reviews don't apply well to the current code, respond with "NO_REVIEW_NEEDED".

Review comment:"""

        try:
            # Call Cohere API
            headers = {
                "Authorization": f"Bearer {cohere_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "command-r-plus",
                "message": prompt,
                "max_tokens": 300,
                "temperature": 0.3
            }
            
            response = requests.post(
                "https://api.cohere.com/v1/chat",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                comment_text = result['text'].strip()
                
                if comment_text and comment_text != "NO_REVIEW_NEEDED":
                    # Extract line information for inline comments - use better line detection
                    line_number = extract_line_number_from_chunk(suggestion)

                    if review_context:
                        comment_text = f"{comment_text}\n\n---\n*📜 Review context:*\n{review_context}"
                    
                    review_comments.append({
                        'file': suggestion['file'],
                        'line': line_number,
                        'comment': comment_text,
                        'similarity_info': [
                            {
                                'similarity': sr['similarity'],
                                'reviewer': sr['reviewer'],
                                'tags': sr['tags']
                            } for sr in suggestion['similar_reviews']
                        ]
                    })
                    
                    print(f"Generated review for {suggestion['file']}:{line_number}")
            else:
                print(f"Error calling Cohere API: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error generating review comment: {e}")
            continue
    
    return review_comments


def extract_line_number_from_hunk(hunk_header: str) -> int:
    """Extract line number from git hunk header"""
    try:
        # Parse hunk header like "@@ -10,7 +10,7 @@" or "@@ -10,7 +10,7 @@ some context"
        import re
        
        # Look for pattern like "+10,7" or "+10"
        match = re.search(r'\+(\d+)', hunk_header)
        if match:
            return int(match.group(1))
        
        # Fallback: try to find any number after +
        parts = hunk_header.split()
        for part in parts:
            if '+' in part:
                nums = re.findall(r'\+(\d+)', part)
                if nums:
                    return int(nums[0])
        
        return 1
    except Exception as e:
        return 1


def extract_line_number_from_chunk(chunk: Dict) -> int:
    """Extract line number from code chunk by finding first added line"""
    try:
        # First try to get line from hunk header
        hunk_line = extract_line_number_from_hunk(chunk['hunk_header'])
        
        # Then look for the first added line in the chunk
        lines = chunk['code_chunk'].split('\n')
        line_offset = 0
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                # Found first added line
                return hunk_line + line_offset
            elif line.startswith(' ') or line.startswith('+'):
                # Count context and added lines
                line_offset += 1
        
        # No added lines found, return hunk start
        return hunk_line
        
    except Exception as e:
        return 1


def main():
    """Main execution function"""
    
    print("🔍 Analyzing PR for auto-review...")
    
    # Load memory
    memory_manager = FAISSMemoryManager()
    index_path = "memory_data/faiss.index"
    metadata_path = "memory_data/metadata.json"
    
    # Switch to memory branch to load data
    os.system("git checkout memory")
    
    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        print("📭 No memory data found, skipping auto-review")
        return
    
    memory_manager.load_from_files(index_path, metadata_path)
    print(f"📚 Loaded memory with {memory_manager.index.ntotal} past reviews")
    
    if memory_manager.index.ntotal == 0:
        print("📭 Empty memory, skipping auto-review")
        return
    
    # Switch back to PR branch
    os.system("git checkout -")
    
    # Get PR changes
    try:
        code_chunks, pr, repo = get_pr_changes()
        print(f"📝 Found {len(code_chunks)} code chunks to review")
        
        if not code_chunks:
            print("📭 No reviewable changes found")
            return
        
    except Exception as e:
        print(f"❌ Error getting PR changes: {e}")
        return
    
    # Initialize Cohere client
    cohere_api_key = os.getenv('COHERE_API_KEY')
    cohere_client = CohereEmbeddingClient(cohere_api_key)
    
    # Find similar past reviews
    pr_search_info = {
        'pr_number': pr.number,
        'repo': repo.full_name
    }
    review_suggestions = find_similar_past_reviews(code_chunks, memory_manager, cohere_client, pr_search_info)
    print(f"🔎 Found {len(review_suggestions)} chunks with similar past reviews")
    
    if not review_suggestions:
        print("📭 No similar past reviews found")
        # NEW: Fallback to context rules if available
        review_context_path = "scripts/review_rules.txt"
        if os.path.exists(review_context_path):
            with open(review_context_path, "r", encoding="utf-8") as f:
                review_context = f.read()

            review_context = load_review_context()
            # Generate a generic comment for each code chunk
            review_comments = []
            for chunk in code_chunks:
                prompt = build_review_prompt(chunk['code_chunk'], review_context)
                # Call to your LLM API to generate the comment
                comment_text = call_claude_api(prompt)
                review_comments.append({
                    'file': chunk['filename'],
                    'line': extract_line_number_from_hunk(chunk['hunk_header']),
                    'comment': comment_text,
                    'similarity_info': []
                })

            # Save generated review
            if review_comments:
                review_data = {
                    'pr_number': pr.number,
                    'comments': review_comments,
                    'metadata': {
                        'total_chunks_analyzed': len(code_chunks),
                        'chunks_with_similar_reviews': 0,
                        'comments_generated': len(review_comments),
                        'memory_size': memory_manager.index.ntotal
                    }
                }
                with open('generated_review.json', 'w') as f:
                    json.dump(review_data, f, indent=2)
                print("✅ Review generated with context rules only")
        return
    
    # Generate review comments using Cohere
    pr_info = {
        'title': pr.title,
        'number': pr.number,
        'author': pr.user.login
    }
    
    review_comments = generate_review_comments_with_cohere(review_suggestions, pr_info)
    print(f"💬 Generated {len(review_comments)} review comments")
    
    # Save generated review
    if review_comments:
        review_data = {
            'pr_number': pr.number,
            'comments': review_comments,
            'metadata': {
                'total_chunks_analyzed': len(code_chunks),
                'chunks_with_similar_reviews': len(review_suggestions),
                'comments_generated': len(review_comments),
                'memory_size': memory_manager.index.ntotal
            }
        }
        
        with open('generated_review.json', 'w') as f:
            json.dump(review_data, f, indent=2)
        
        print("✅ Review generated successfully")
    else:
        print("📭 No review comments generated")


if __name__ == "__main__":
    main()
