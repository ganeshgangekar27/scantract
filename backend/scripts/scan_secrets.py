"""
Scan git history and working tree for potential secret patterns.
Never prints the actual secret values, only metadata.
"""
import subprocess
import re
import sys

def scan_blob(commit_sha, path, content_bytes):
    """Scan a blob for secret patterns, try both utf-8 and utf-16"""
    results = []
    
    # Try UTF-8
    try:
        content = content_bytes.decode('utf-8')
        matches = re.findall(r'sk-or-v1-[0-9a-f]{20,}', content)
        matches += re.findall(r'AIza[0-9A-Za-z_-]{20,}', content)
        if matches:
            for match in matches:
                results.append({
                    'commit': commit_sha,
                    'path': path,
                    'encoding': 'utf-8',
                    'len': len(match),
                    'last4': match[-4:]
                })
    except:
        pass
    
    # Try UTF-16
    try:
        content = content_bytes.decode('utf-16', errors='ignore')
        matches = re.findall(r'sk-or-v1-[0-9a-f]{20,}', content)
        matches += re.findall(r'AIza[0-9A-Za-z_-]{20,}', content)
        if matches:
            for match in matches:
                results.append({
                    'commit': commit_sha,
                    'path': path,
                    'encoding': 'utf-16',
                    'len': len(match),
                    'last4': match[-4:]
                })
    except:
        pass
    
    return results

def main():
    print("=== SCANNING GIT HISTORY (origin/main..HEAD) ===")
    
    # Get all blobs in commits between origin/main and HEAD
    try:
        rev_list = subprocess.check_output(
            ['git', 'rev-list', '--objects', 'origin/main..HEAD'],
            text=True
        ).strip().split('\n')
    except subprocess.CalledProcessError:
        print("No commits between origin/main and HEAD")
        rev_list = []
    
    all_results = []
    
    for line in rev_list:
        if not line:
            continue
        parts = line.split(' ', 1)
        obj_sha = parts[0]
        path = parts[1] if len(parts) > 1 else '(tree)'
        
        # Skip tree objects
        if path == '(tree)':
            continue
        
        # Get blob content
        try:
            content = subprocess.check_output(
                ['git', 'cat-file', 'blob', obj_sha],
                stderr=subprocess.DEVNULL
            )
            results = scan_blob(f"commit:{obj_sha[:7]}", path, content)
            all_results.extend(results)
        except:
            pass
    
    print(f"Scanned {len(rev_list)} objects from git history")
    print(f"Found {len(all_results)} potential secrets in git history")
    
    print("\n=== SCANNING WORKING TREE ===")
    
    # Get tracked files
    tracked = subprocess.check_output(['git', 'ls-files'], text=True).strip().split('\n')
    
    # Get untracked but not ignored
    try:
        untracked = subprocess.check_output(
            ['git', 'ls-files', '--others', '--exclude-standard'],
            text=True
        ).strip().split('\n')
    except:
        untracked = []
    
    worktree_files = [f for f in tracked + untracked if f]
    
    for filepath in worktree_files:
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            results = scan_blob('WORKTREE', filepath, content)
            all_results.extend(results)
        except:
            pass
    
    print(f"Scanned {len(worktree_files)} files from working tree")
    
    print(f"\n=== RESULTS ({len(all_results)} total) ===")
    
    if not all_results:
        print("No secrets found")
    else:
        for r in all_results:
            print(f"{r['commit']}: {r['path']} ({r['encoding']}) - len={r['len']} last4={r['last4']}")

if __name__ == "__main__":
    main()
