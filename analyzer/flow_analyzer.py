import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Set
import re

class FlowAnalyzer:
    """Analyze execution flow and generate flow diagrams"""
    
    def __init__(self, graph: nx.DiGraph, root_path: Path, files: List[Path]):
        self.graph = graph
        self.root_path = root_path
        self.files = files
    
    def analyze_flow(self, entry_points: List[str]) -> Dict:
        """Analyze execution flow from entry points"""
        if not entry_points:
            # Try to detect entry points
            entry_points = self._detect_entry_points()
        
        if not entry_points:
            return {
                'has_flow': False,
                'entry_points': [],
                'mermaid_diagram': '',
                'flow_description': 'No entry point detected'
            }
        
        # Analyze flow from each entry point
        flows = []
        for entry_point in entry_points:
            flow = self._trace_flow(entry_point)
            if flow:
                flows.append({
                    'entry_point': entry_point,
                    'dependencies': flow
                })
        
        # Generate Mermaid diagram
        mermaid_diagram = self._generate_mermaid_diagram(entry_points)
        
        # Generate flow description
        flow_description = self._generate_flow_description(entry_points, flows)
        
        return {
            'has_flow': True,
            'entry_points': entry_points,
            'flows': flows,
            'mermaid_diagram': mermaid_diagram,
            'flow_description': flow_description
        }
    
    def _detect_entry_points(self) -> List[str]:
        """Detect likely entry point files"""
        entry_point_patterns = [
            'main.py', 'app.py', '__main__.py', 'run.py', 'server.py', 'manage.py',
            'index.js', 'main.js', 'app.js', 'server.js',
            'index.ts', 'main.ts', 'app.ts', 'server.ts',
            'index.jsx', 'App.jsx', 'main.jsx',
            'index.tsx', 'App.tsx', 'main.tsx',
            'Main.java', 'Application.java',
            'main.cpp', 'main.c',
            'index.html'
        ]
        
        entry_points = []
        for node in self.graph.nodes():
            filename = Path(node).name
            if filename in entry_point_patterns:
                entry_points.append(node)
        
        # Also check for files with __main__ check (Python)
        for file_path in self.files:
            if file_path.suffix == '.py':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '__name__' in content and '__main__' in content:
                            rel_path = str(file_path.relative_to(self.root_path))
                            if rel_path not in entry_points:
                                entry_points.append(rel_path)
                except:
                    pass
        
        return entry_points
    
    def _trace_flow(self, entry_point: str, max_depth: int = 5) -> List[str]:
        """Trace execution flow from an entry point using BFS"""
        if entry_point not in self.graph:
            return []
        
        visited = set()
        flow = []
        queue = [(entry_point, 0)]
        
        while queue:
            node, depth = queue.pop(0)
            
            if node in visited or depth > max_depth:
                continue
            
            visited.add(node)
            flow.append(node)
            
            # Add dependencies (files this node imports)
            for neighbor in self.graph.successors(node):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        
        return flow
    
    def _generate_mermaid_diagram(self, entry_points: List[str]) -> str:
        """Generate Mermaid flowchart diagram"""
        if not entry_points:
            return ''
        
        lines = ['graph TD']
        
        # Add nodes and edges based on entry point flows
        added_edges = set()
        processed_nodes = set()
        
        for entry_point in entry_points:
            if entry_point not in self.graph:
                continue
            
            # Use BFS to create flow
            queue = [(entry_point, 0)]
            visited = set()
            
            while queue:
                node, depth = queue.pop(0)
                
                if node in visited or depth > 3:  # Limit depth for clarity
                    continue
                
                visited.add(node)
                
                # Add node
                node_id = self._sanitize_id(node)
                node_label = Path(node).name
                
                if node not in processed_nodes:
                    # Style entry points differently
                    if node == entry_point:
                        lines.append(f'    {node_id}["{node_label}"]')
                        lines.append(f'    style {node_id} fill:#4CAF50,stroke:#2E7D32,color:#fff')
                    else:
                        lines.append(f'    {node_id}["{node_label}"]')
                    processed_nodes.add(node)
                
                # Add edges to dependencies
                for neighbor in self.graph.successors(node):
                    edge = (node, neighbor)
                    if edge not in added_edges:
                        neighbor_id = self._sanitize_id(neighbor)
                        neighbor_label = Path(neighbor).name
                        
                        # Add neighbor node if not added
                        if neighbor not in processed_nodes:
                            lines.append(f'    {neighbor_id}["{neighbor_label}"]')
                            processed_nodes.add(neighbor)
                        
                        lines.append(f'    {node_id} --> {neighbor_id}')
                        added_edges.add(edge)
                    
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))
        
        return '\n'.join(lines)
    
    def _sanitize_id(self, path: str) -> str:
        """Sanitize path for use as Mermaid node ID"""
        # Replace special characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', path)
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'f_' + sanitized
        return sanitized or 'node'
    
    def _generate_flow_description(self, entry_points: List[str], flows: List[Dict]) -> str:
        """Generate human-readable flow description"""
        if not entry_points:
            return "No entry point detected."
        
        descriptions = []
        
        for entry_point in entry_points:
            entry_name = Path(entry_point).name
            descriptions.append(f"**Entry Point: {entry_name}**")
            
            # Find flow for this entry point
            flow = None
            for f in flows:
                if f['entry_point'] == entry_point:
                    flow = f['dependencies']
                    break
            
            if flow and len(flow) > 1:
                descriptions.append(f"Execution starts from `{entry_name}` and flows through {len(flow) - 1} dependent files:")
                
                # List first few dependencies
                for i, dep in enumerate(flow[1:6]):  # Show up to 5 dependencies
                    dep_name = Path(dep).name
                    descriptions.append(f"{i + 1}. `{dep_name}`")
                
                if len(flow) > 6:
                    descriptions.append(f"... and {len(flow) - 6} more files")
            else:
                descriptions.append(f"`{entry_name}` has no detected dependencies")
            
            descriptions.append("")  # Empty line between entry points
        
        return '\n'.join(descriptions)
    
    def get_critical_path(self, entry_point: str) -> List[str]:
        """Get the critical path from entry point (longest dependency chain)"""
        if entry_point not in self.graph:
            return []
        
        # Find longest path using DFS
        def dfs(node: str, visited: Set[str]) -> List[str]:
            if node in visited:
                return []
            
            visited.add(node)
            longest = [node]
            
            for neighbor in self.graph.successors(node):
                path = dfs(neighbor, visited.copy())
                if len(path) + 1 > len(longest):
                    longest = [node] + path
            
            return longest
        
        return dfs(entry_point, set())
    
    def get_flow_summary(self) -> Dict:
        """Get a summary of the execution flow"""
        entry_points = self._detect_entry_points()
        
        summary = {
            'total_files': len(self.graph.nodes()),
            'entry_points_count': len(entry_points),
            'entry_points': [Path(ep).name for ep in entry_points],
            'has_clear_entry': len(entry_points) > 0
        }
        
        if entry_points:
            # Calculate average dependency depth
            depths = []
            for ep in entry_points:
                flow = self._trace_flow(ep)
                depths.append(len(flow))
            
            summary['avg_dependency_depth'] = sum(depths) / len(depths) if depths else 0
            summary['max_dependency_depth'] = max(depths) if depths else 0
        
        return summary
