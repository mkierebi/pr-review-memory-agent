"""
Post generated review comments to GitHub PR
"""

import os
import json
from github import Github
from typing import List, Dict, Optional

def get_position_in_diff(patch: str, target_line: int) -> Optional[int]:
    """
    Find the position in diff patch for a given line number
    Returns the position (1-based) or None if not found
    """
    if not patch:
        return None
        
    lines = patch.split('\n')
    position = 0
    current_new_line = 0
    
    for line in lines:
        if line.startswith('@@'):
            # Parse hunk header like "@@ -10,7 +10,7 @@"
            try:
                parts = line.split()
                new_range = parts[1]  # +10,7 part  
                current_new_line = int(new_range.split(',')[0].replace('+', ''))
                position += 1
                continue
            except:
                continue
                
        position += 1
        
        if line.startswith('+'):
            # This is a new line
            if current_new_line == target_line:
                return position
            current_new_line += 1
        elif line.startswith('-'):
            # This is a deleted line, don't increment new line counter
            pass
        elif line.startswith(' '):
            # This is a context line
            current_new_line += 1
            
    return None

def load_review_context(context_path: str = "scripts/review_rules.txt") -> str:
    """Load rules or additional context for the review from an external file."""
    if os.path.exists(context_path):
        with open(context_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def calculate_diff_position(pr, file_path: str, target_line: int) -> int:
    """Calculate the position in the diff for a given line number"""
    try:
        # Get the diff for the file
        files = pr.get_files()
        target_file = None
        
        for file in files:
            if file.filename == file_path:
                target_file = file
                break
        
        if not target_file or not target_file.patch:
            return None
            
        # Parse the patch to find the position
        patch_lines = target_file.patch.split('\n')
        position = 0
        current_line = 0
        
        print(f"🔍 Calculating diff position for {file_path}, target line: {target_line}")
        print(f"📝 Patch preview (first 10 lines):")
        
        for i, line in enumerate(patch_lines[:10]):
            print(f"  {i}: '{line}'")
        
        for line in patch_lines:
            if line.startswith('@@'):
                # Parse hunk header to get starting line
                import re
                match = re.search(r'\+(\d+)', line)
                if match:
                    current_line = int(match.group(1)) - 1
                    print(f"🎯 Hunk start: line {current_line + 1}")
                continue
                
            position += 1
            
            if line.startswith('+'):
                current_line += 1
                print(f"📍 Position {position}: +line {current_line}")
                if current_line == target_line:
                    print(f"✅ Found target line {target_line} at position {position}")
                    return position
            elif line.startswith(' '):
                current_line += 1
                print(f"📍 Position {position}: context line {current_line}")
            # Lines starting with '-' don't increment current_line
        
        print(f"❌ Target line {target_line} not found in diff")
        return None
    except Exception as e:
        print(f"Error calculating diff position: {e}")
        return None


def post_review_comments():
    """Post generated review comments to PR"""
    
    github_token = os.getenv('GITHUB_TOKEN')
    pr_number = int(os.getenv('PR_NUMBER'))
    repo_name = os.getenv('REPO_NAME')
    
    if not all([github_token, pr_number, repo_name]):
        print("Missing required environment variables")
        return False
    
    # Load generated review
    if not os.path.exists('generated_review.json'):
        print("No generated review file found")
        return False
    
    with open('generated_review.json', 'r') as f:
        review_data = json.load(f)
    
    # Initialize GitHub client
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    comments_posted = 0
    errors = 0
    
    # Get PR head commit for review comments
    head_commit = pr.get_commits().reversed[0]

    review_context = load_review_context()
    
    try:
        # Post each comment
        for comment_data in review_data['comments']:
            try:
                # Format comment with context about similar reviews
                formatted_comment = format_review_comment(comment_data)
                if review_context:
                    formatted_comment = f"{formatted_comment}\n\n---\n*📜 Review context:*\n{review_context}"
                
                # Try inline comment first, fallback to general comment
                try:
                    # Calculate diff position for inline comments
                    diff_position = calculate_diff_position(pr, comment_data['file'], comment_data['line'])
                    
                    if diff_position is not None:
                        # Try different PyGithub syntax variations
                        try:
                            # Method 1: Using commit_id as string
                            pr.create_review_comment(
                                body=formatted_comment,
                                commit_id=head_commit.sha,
                                path=comment_data['file'],
                                position=diff_position
                            )
                            print(f"✅ Posted inline comment (method 1) for {comment_data['file']} at position {diff_position}")
                            comments_posted += 1
                        except Exception as e1:
                            try:
                                # Method 2: Using commit object
                                pr.create_review_comment(
                                    formatted_comment,
                                    head_commit,
                                    comment_data['file'],
                                    diff_position
                                )
                                print(f"✅ Posted inline comment (method 2) for {comment_data['file']} at position {diff_position}")
                                comments_posted += 1
                            except Exception as e2:
                                print(f"❌ Method 1 failed: {e1}")
                                print(f"❌ Method 2 failed: {e2}")
                                raise Exception(f"Both inline methods failed: {e1}, {e2}")
                    else:
                        # No valid position found, use general comment
                        raise Exception("Could not calculate diff position")
                        
                except Exception as inline_error:
                    # Try alternative: create a review with inline comments
                    try:
                        print(f"🔄 Trying review API for {comment_data['file']}:{comment_data['line']}")
                        
                        # Create review with inline comment
                        review_comments = [{
                            'path': comment_data['file'],
                            'position': diff_position if diff_position else 1,
                            'body': formatted_comment
                        }]
                        
                        review = pr.create_review(
                            body="Auto-review based on similar past reviews",
                            event="COMMENT",
                            comments=review_comments
                        )
                        print(f"✅ Posted review comment for {comment_data['file']} at position {diff_position}")
                        comments_posted += 1
                        
                    except Exception as review_error:
                        # Final fallback to general comment with file reference
                        general_comment = f"**File: `{comment_data['file']}`** (line ~{comment_data['line']})\n\n{formatted_comment}"
                        pr.create_issue_comment(general_comment)
                        print(f"✅ Posted general comment for {comment_data['file']}:{comment_data['line']} (inline failed: {str(inline_error)[:50]}..., review failed: {str(review_error)[:50]}...)")
                        comments_posted += 1
                    
            except Exception as e:
                print(f"❌ Error posting comment for {comment_data['file']}: {e}")
                errors += 1
                continue
        
        # Post summary comment if multiple comments were generated
        if comments_posted > 1:
            post_summary_comment(pr, review_data, comments_posted)
        
        print(f"📊 Review posting complete: {comments_posted} comments posted, {errors} errors")
        return comments_posted > 0
        
    except Exception as e:
        print(f"❌ Error posting review: {e}")
        return False


def format_review_comment(comment_data: Dict) -> str:
    """Format review comment with context about similar past reviews"""
    
    comment = comment_data['comment']
    
    # Add context about similar reviews found
    if comment_data.get('similarity_info'):
        similar_count = len(comment_data['similarity_info'])
        top_similarity = max(info['similarity'] for info in comment_data['similarity_info'])
        
        # Get unique reviewers
        reviewers = set(info['reviewer'] for info in comment_data['similarity_info'])
        reviewer_text = f"{len(reviewers)} reviewer(s)" if len(reviewers) > 1 else f"@{list(reviewers)[0]}"
        
        # Get common tags
        all_tags = []
        for info in comment_data['similarity_info']:
            all_tags.extend(info['tags'])
        
        common_tags = list(set(all_tags))
        tags_text = ", ".join(common_tags[:3])  # Show max 3 tags
        
        footer = f"\n\n---\n*🤖 This suggestion is based on {similar_count} similar past review(s) by {reviewer_text} (similarity: {top_similarity:.0%})*"
        if tags_text:
            footer += f"\n*📋 Related areas: {tags_text}*"
            
        return comment + footer
    
    return comment + "\n\n---\n*🤖 Generated based on similar past reviews*"


def post_summary_comment(pr, review_data: Dict, comments_posted: int):
    """Post summary comment about the auto-review"""
    
    metadata = review_data.get('metadata', {})
    
    summary = f"""## 🤖 Auto-Review Summary

I've analyzed this PR using **{metadata.get('memory_size', 0)} past reviews** from our team's memory and posted **{comments_posted} suggestions** based on similar code patterns.

### Analysis Results:
- **Code chunks analyzed:** {metadata.get('total_chunks_analyzed', 0)}
- **Chunks with similar past reviews:** {metadata.get('chunks_with_similar_reviews', 0)}
- **Review comments generated:** {metadata.get('comments_generated', 0)}
- **Comments successfully posted:** {comments_posted}

The suggestions above are based on patterns from previous code reviews. Please review them critically and feel free to ignore if not applicable to your specific case.

---
*This auto-review system learns from our team's review history to provide consistent feedback. It's meant to supplement, not replace, human review.*"""

    try:
        pr.create_issue_comment(summary)
        print("✅ Posted summary comment")
    except Exception as e:
        print(f"⚠️ Could not post summary comment: {e}")


def main():
    """Main execution function"""
    
    print("📤 Posting auto-review comments...")
    
    success = post_review_comments()
    
    if success:
        print("✅ Review comments posted successfully")
    else:
        print("❌ Failed to post review comments")


if __name__ == "__main__":
    main()