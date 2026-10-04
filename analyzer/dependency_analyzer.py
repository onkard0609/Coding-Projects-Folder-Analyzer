import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import networkx as nx

class DependencyAnalyzer:
    """Multi-language dependency analyzer"""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.graph = nx.DiGraph()
        self.file_map = {}  # Map relative paths to absolute paths
        
    def analyze(self, files: List[Path]) -> Dict:
        """Analyze dependencies for all files"""
        # Build file map
        for file_path in files:
            rel_path = file_path.relative_to(self.root_path)
            self.file_map[str(rel_path)] = file_path
            self.graph.add_node(str(rel_path), path=file_path)
        
        # Analyze each file
        for file_path in files:
            self._analyze_file(file_path)
        
        return self._build_result()
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single file for dependencies"""
        ext = file_path.suffix
        rel_path = str(file_path.relative_to(self.root_path))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return
        
        dependencies = []
        
        if ext == '.py':
            dependencies = self._analyze_python(content, file_path)
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            dependencies = self._analyze_javascript(content, file_path)
        elif ext == '.java':
            dependencies = self._analyze_java(content, file_path)
        elif ext in ['.cpp', '.c', '.h', '.hpp']:
            dependencies = self._analyze_cpp(content, file_path)
        elif ext == '.css':
            dependencies = self._analyze_css(content, file_path)
        elif ext == '.html':
            dependencies = self._analyze_html(content, file_path)
        
        # Add edges to graph
        for dep in dependencies:
            if dep in self.file_map:
                self.graph.add_edge(rel_path, dep)
    
    def _analyze_python(self, content: str, file_path: Path) -> List[str]:
        """Analyze Python imports"""
        dependencies = []
        
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep = self._resolve_python_import(alias.name, file_path)
                        if dep:
                            dependencies.append(dep)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dep = self._resolve_python_import(node.module, file_path)
                        if dep:
                            dependencies.append(dep)
        except SyntaxError:
            # Fallback to regex for syntax errors
            dependencies.extend(self._analyze_python_regex(content, file_path))
        
        return dependencies
    
    def _analyze_python_regex(self, content: str, file_path: Path) -> List[str]:
        """Fallback regex-based Python import analysis"""
        dependencies = []
        
        # Match: import module or from module import
        import_pattern = r'^\s*(?:from\s+([\w.]+)\s+)?import\s+([\w.,\s]+)'
        
        for line in content.splitlines():
            match = re.match(import_pattern, line)
            if match:
                module = match.group(1) or match.group(2).split(',')[0].strip()
                dep = self._resolve_python_import(module, file_path)
                if dep:
                    dependencies.append(dep)
        
        return dependencies
    
    def _resolve_python_import(self, module: str, file_path: Path) -> Optional[str]:
        """Resolve Python import to file path"""
        # Convert module to path
        parts = module.split('.')
        
        # Try relative import from current directory
        current_dir = file_path.parent
        
        # Try as .py file
        potential_path = current_dir / f"{parts[0]}.py"
        if potential_path.exists() and potential_path != file_path:
            return str(potential_path.relative_to(self.root_path))
        
        # Try as package (__init__.py)
        potential_path = current_dir / parts[0] / "__init__.py"
        if potential_path.exists():
            return str(potential_path.relative_to(self.root_path))
        
        # Try from root
        potential_path = self.root_path / f"{'/'.join(parts)}.py"
        if potential_path.exists():
            return str(potential_path.relative_to(self.root_path))
        
        potential_path = self.root_path / '/'.join(parts) / "__init__.py"
        if potential_path.exists():
            return str(potential_path.relative_to(self.root_path))
        
        return None
    
    def _analyze_javascript(self, content: str, file_path: Path) -> List[str]:
        """Analyze JavaScript/TypeScript imports"""
        dependencies = []
        
        # Match: import ... from '...'
        import_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
        
        # Match: require('...')
        require_pattern = r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        
        # Match: import('...')
        dynamic_import_pattern = r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        
        for pattern in [import_pattern, require_pattern, dynamic_import_pattern]:
            for match in re.finditer(pattern, content):
                import_path = match.group(1)
                dep = self._resolve_js_import(import_path, file_path)
                if dep:
                    dependencies.append(dep)
        
        return dependencies
    
    def _resolve_js_import(self, import_path: str, file_path: Path) -> Optional[str]:
        """Resolve JavaScript import to file path"""
        # Skip node_modules and external packages
        if not import_path.startswith('.'):
            return None
        
        current_dir = file_path.parent
        
        # Resolve relative path
        resolved = (current_dir / import_path).resolve()
        
        # Try with common extensions
        for ext in ['', '.js', '.jsx', '.ts', '.tsx', '.json']:
            potential_path = Path(str(resolved) + ext)
            if potential_path.exists() and potential_path.is_relative_to(self.root_path):
                return str(potential_path.relative_to(self.root_path))
        
        # Try as directory with index file
        for ext in ['.js', '.jsx', '.ts', '.tsx']:
            potential_path = resolved / f"index{ext}"
            if potential_path.exists() and potential_path.is_relative_to(self.root_path):
                return str(potential_path.relative_to(self.root_path))
        
        return None
    
    def _analyze_java(self, content: str, file_path: Path) -> List[str]:
        """Analyze Java imports"""
        dependencies = []
        
        # Match: import package.Class;
        import_pattern = r'import\s+([\w.]+);'
        
        for match in re.finditer(import_pattern, content):
            import_stmt = match.group(1)
            dep = self._resolve_java_import(import_stmt, file_path)
            if dep:
                dependencies.append(dep)
        
        return dependencies
    
    def _resolve_java_import(self, import_stmt: str, file_path: Path) -> Optional[str]:
        """Resolve Java import to file path"""
        # Convert package.Class to path/Class.java
        parts = import_stmt.split('.')
        class_name = parts[-1]
        
        # Try to find .java file
        for java_file in self.root_path.rglob(f"{class_name}.java"):
            if java_file.is_relative_to(self.root_path):
                return str(java_file.relative_to(self.root_path))
        
        return None
    
    def _analyze_cpp(self, content: str, file_path: Path) -> List[str]:
        """Analyze C/C++ includes"""
        dependencies = []
        
        # Match: #include "file.h" (local includes only)
        include_pattern = r'#include\s+"([^"]+)"'
        
        for match in re.finditer(include_pattern, content):
            include_file = match.group(1)
            dep = self._resolve_cpp_include(include_file, file_path)
            if dep:
                dependencies.append(dep)
        
        return dependencies
    
    def _resolve_cpp_include(self, include_file: str, file_path: Path) -> Optional[str]:
        """Resolve C++ include to file path"""
        current_dir = file_path.parent
        
        # Try relative to current file
        potential_path = current_dir / include_file
        if potential_path.exists():
            return str(potential_path.relative_to(self.root_path))
        
        # Try from root
        potential_path = self.root_path / include_file
        if potential_path.exists():
            return str(potential_path.relative_to(self.root_path))
        
        return None
    
    def _analyze_css(self, content: str, file_path: Path) -> List[str]:
        """Analyze CSS imports"""
        dependencies = []
        
        # Match: @import 'file.css' or @import url('file.css')
        import_pattern = r'@import\s+(?:url\()?[\'"]([^\'"]+)[\'"]'
        
        for match in re.finditer(import_pattern, content):
            import_file = match.group(1)
            dep = self._resolve_css_import(import_file, file_path)
            if dep:
                dependencies.append(dep)
        
        return dependencies
    
    def _resolve_css_import(self, import_file: str, file_path: Path) -> Optional[str]:
        """Resolve CSS import to file path"""
        current_dir = file_path.parent
        
        potential_path = current_dir / import_file
        if potential_path.exists():
            return str(potential_path.relative_to(self.root_path))
        
        return None
    
    def _analyze_html(self, content: str, file_path: Path) -> List[str]:
        """Analyze HTML script and link tags"""
        dependencies = []
        
        # Match: <script src="...">
        script_pattern = r'<script[^>]+src=[\'"]([^\'"]+)[\'"]'
        
        # Match: <link href="...">
        link_pattern = r'<link[^>]+href=[\'"]([^\'"]+)[\'"]'
        
        for pattern in [script_pattern, link_pattern]:
            for match in re.finditer(pattern, content):
                src = match.group(1)
                # Skip external URLs
                if src.startswith('http'):
                    continue
                
                dep = self._resolve_html_resource(src, file_path)
                if dep:
                    dependencies.append(dep)
        
        return dependencies
    
    def _resolve_html_resource(self, src: str, file_path: Path) -> Optional[str]:
        """Resolve HTML resource to file path"""
        current_dir = file_path.parent
        
        # Handle absolute paths from root
        if src.startswith('/'):
            potential_path = self.root_path / src.lstrip('/')
        else:
            potential_path = current_dir / src
        
        if potential_path.exists() and potential_path.is_relative_to(self.root_path):
            return str(potential_path.relative_to(self.root_path))
        
        return None
    
    def _build_result(self) -> Dict:
        """Build result dictionary with nodes and edges"""
        nodes = []
        for node in self.graph.nodes():
            in_degree = self.graph.in_degree(node)
            out_degree = self.graph.out_degree(node)
            
            nodes.append({
                'id': node,
                'path': node,
                'in_degree': in_degree,
                'out_degree': out_degree,
                'file_type': Path(node).suffix
            })
        
        edges = []
        for source, target in self.graph.edges():
            edges.append({
                'source': source,
                'target': target
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'graph': self.graph  # Keep for further analysis
        }
