import networkx as nx
from pathlib import Path
from typing import Dict, List

class ImportanceScorer:
    """Calculate file importance scores using graph analysis"""
    
    def __init__(self, graph: nx.DiGraph, root_path: Path):
        self.graph = graph
        self.root_path = root_path
    
    def calculate_scores(self) -> List[Dict]:
        """Calculate importance scores for all files"""
        if len(self.graph.nodes()) == 0:
            return []
        
        scores = {}
        
        # Component 1: Incoming references (40% weight)
        in_degree_scores = self._calculate_in_degree_scores()
        
        # Component 2: PageRank centrality (40% weight)
        pagerank_scores = self._calculate_pagerank_scores()
        
        # Component 3: Entry point and special file bonuses (20% weight)
        bonus_scores = self._calculate_bonus_scores()
        
        # Combine scores
        for node in self.graph.nodes():
            total_score = (
                in_degree_scores.get(node, 0) * 0.4 +
                pagerank_scores.get(node, 0) * 0.4 +
                bonus_scores.get(node, 0) * 0.2
            )
            scores[node] = total_score
        
        # Normalize to 0-100
        normalized_scores = self._normalize_scores(scores)
        
        # Build result list
        result = []
        for node, score in normalized_scores.items():
            result.append({
                'file': node,
                'score': round(score, 2),
                'in_degree': self.graph.in_degree(node),
                'out_degree': self.graph.out_degree(node),
                'is_entry_point': self._is_entry_point(node),
                'file_type': Path(node).suffix
            })
        
        # Sort by score descending
        result.sort(key=lambda x: x['score'], reverse=True)
        
        return result
    
    def _calculate_in_degree_scores(self) -> Dict[str, float]:
        """Calculate scores based on incoming references"""
        scores = {}
        max_in_degree = max([self.graph.in_degree(n) for n in self.graph.nodes()] or [1])
        
        for node in self.graph.nodes():
            in_degree = self.graph.in_degree(node)
            scores[node] = (in_degree / max_in_degree) * 100 if max_in_degree > 0 else 0
        
        return scores
    
    def _calculate_pagerank_scores(self) -> Dict[str, float]:
        """Calculate PageRank-based importance scores"""
        try:
            pagerank = nx.pagerank(self.graph)
            max_pr = max(pagerank.values()) if pagerank else 1
            
            scores = {}
            for node, pr in pagerank.items():
                scores[node] = (pr / max_pr) * 100 if max_pr > 0 else 0
            
            return scores
        except:
            # If PageRank fails (e.g., empty graph), return zeros
            return {node: 0 for node in self.graph.nodes()}
    
    def _calculate_bonus_scores(self) -> Dict[str, float]:
        """Calculate bonus scores for special files"""
        scores = {}
        
        for node in self.graph.nodes():
            score = 0
            
            # Entry point files get high bonus
            if self._is_entry_point(node):
                score += 100
            
            # Configuration files
            elif self._is_config_file(node):
                score += 30
            
            # Test files get lower importance
            elif self._is_test_file(node):
                score -= 20
            
            # Files in root directory get slight bonus
            elif '/' not in node and '\\' not in node:
                score += 20
            
            scores[node] = max(0, score)
        
        return scores
    
    def _is_entry_point(self, file_path: str) -> bool:
        """Check if file is likely an entry point"""
        entry_point_names = [
            'main.py', 'app.py', '__main__.py', 'run.py', 'server.py',
            'index.js', 'main.js', 'app.js', 'server.js',
            'index.ts', 'main.ts', 'app.ts', 'server.ts',
            'index.jsx', 'App.jsx', 'main.jsx',
            'index.tsx', 'App.tsx', 'main.tsx',
            'Main.java', 'Application.java',
            'main.cpp', 'main.c',
            'index.html'
        ]
        
        filename = Path(file_path).name
        return filename in entry_point_names
    
    def _is_config_file(self, file_path: str) -> bool:
        """Check if file is a configuration file"""
        config_names = [
            'package.json', 'requirements.txt', 'setup.py', 'pyproject.toml',
            'tsconfig.json', 'webpack.config.js', 'vite.config.js',
            'Dockerfile', 'docker-compose.yml', '.env',
            'pom.xml', 'build.gradle', 'Makefile', 'CMakeLists.txt'
        ]
        
        filename = Path(file_path).name
        return filename in config_names or filename.endswith('.config.js')
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file"""
        path_lower = file_path.lower()
        return (
            'test' in path_lower or
            'spec' in path_lower or
            '__tests__' in path_lower or
            '.test.' in path_lower or
            '.spec.' in path_lower
        )
    
    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize scores to 0-100 range"""
        if not scores:
            return {}
        
        min_score = min(scores.values())
        max_score = max(scores.values())
        
        if max_score == min_score:
            return {k: 50.0 for k in scores.keys()}
        
        normalized = {}
        for node, score in scores.items():
            normalized[node] = ((score - min_score) / (max_score - min_score)) * 100
        
        return normalized
    
    def get_top_files(self, n: int = 10) -> List[Dict]:
        """Get top N most important files"""
        all_scores = self.calculate_scores()
        return all_scores[:n]
    
    def get_entry_points(self) -> List[str]:
        """Get all detected entry point files"""
        entry_points = []
        for node in self.graph.nodes():
            if self._is_entry_point(node):
                entry_points.append(node)
        return entry_points
