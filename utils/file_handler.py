import os
import zipfile
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Optional
import chardet

class FileHandler:
    """Handle file uploads, zip extraction, and folder operations"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    def create_session(self) -> str:
        """Create a unique session ID for an upload"""
        session_id = str(uuid.uuid4())
        session_path = self.upload_dir / session_id
        session_path.mkdir(exist_ok=True)
        return session_id
    
    def extract_zip(self, zip_path: Path, session_id: str) -> Path:
        """Extract zip file to session directory"""
        extract_path = self.upload_dir / session_id / "extracted"
        extract_path.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        return extract_path
    
    def save_folder_files(self, files: List, session_id: str) -> Path:
        """Save uploaded folder files preserving structure"""
        folder_path = self.upload_dir / session_id / "folder"
        folder_path.mkdir(exist_ok=True)
        
        for file_data in files:
            file_path = folder_path / file_data['path']
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_data['content'])
        
        return folder_path
    
    def get_file_tree(self, root_path: Path) -> Dict:
        """Generate file tree structure"""
        def build_tree(path: Path, relative_to: Path) -> Dict:
            rel_path = path.relative_to(relative_to)
            
            if path.is_file():
                return {
                    'name': path.name,
                    'path': str(rel_path),
                    'type': 'file',
                    'size': path.stat().st_size,
                    'extension': path.suffix
                }
            else:
                children = []
                try:
                    for child in sorted(path.iterdir()):
                        # Skip hidden files and common ignore patterns
                        if child.name.startswith('.') or child.name in ['node_modules', '__pycache__', 'venv', '.git']:
                            continue
                        children.append(build_tree(child, relative_to))
                except PermissionError:
                    pass
                
                return {
                    'name': path.name,
                    'path': str(rel_path),
                    'type': 'directory',
                    'children': children
                }
        
        return build_tree(root_path, root_path)
    
    def get_all_files(self, root_path: Path) -> List[Path]:
        """Get all files recursively, filtering out non-code files"""
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala',
            '.html', '.css', '.scss', '.sass', '.less',
            '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.conf',
            '.md', '.txt', '.sh', '.bat', '.sql'
        }
        
        files = []
        for path in root_path.rglob('*'):
            if path.is_file():
                # Skip hidden files and common ignore patterns
                if any(part.startswith('.') for part in path.parts):
                    continue
                if any(ignore in path.parts for ignore in ['node_modules', '__pycache__', 'venv', '.git', 'dist', 'build']):
                    continue
                
                # Only include code/text files
                if path.suffix in code_extensions or path.suffix == '' and path.name in ['Dockerfile', 'Makefile']:
                    files.append(path)
        
        return files
    
    def read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content with encoding detection"""
        try:
            # Try UTF-8 first
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding']
            
            if encoding:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except:
                    return None
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def cleanup_session(self, session_id: str):
        """Clean up session directory"""
        session_path = self.upload_dir / session_id
        if session_path.exists():
            shutil.rmtree(session_path)
    
    def get_file_stats(self, root_path: Path) -> Dict:
        """Get statistics about the uploaded folder"""
        files = self.get_all_files(root_path)
        
        stats = {
            'total_files': len(files),
            'total_lines': 0,
            'file_types': {},
            'languages': set()
        }
        
        for file_path in files:
            ext = file_path.suffix or 'no_extension'
            stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
            
            # Count lines
            content = self.read_file_content(file_path)
            if content:
                stats['total_lines'] += len(content.splitlines())
            
            # Detect language
            lang = self._detect_language(file_path)
            if lang:
                stats['languages'].add(lang)
        
        stats['languages'] = list(stats['languages'])
        return stats
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C/C++',
            '.hpp': 'C++',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.md': 'Markdown'
        }
        return ext_map.get(file_path.suffix)
