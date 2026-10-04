from pathlib import Path
from typing import Dict, List, Set
import re

class ProjectSummarizer:
    """Generate intelligent project summaries"""
    
    def __init__(self, root_path: Path, files: List[Path], file_stats: Dict):
        self.root_path = root_path
        self.files = files
        self.file_stats = file_stats
    
    def generate_summary(self) -> Dict:
        """Generate comprehensive project summary"""
        project_type = self._detect_project_type()
        framework = self._detect_framework()
        structure = self._analyze_structure()
        purpose = self._infer_purpose(project_type, framework)
        key_modules = self._identify_key_modules()
        
        return {
            'project_type': project_type,
            'framework': framework,
            'purpose': purpose,
            'structure': structure,
            'key_modules': key_modules,
            'statistics': self.file_stats,
            'description': self._generate_description(project_type, framework, structure)
        }
    
    def _detect_project_type(self) -> str:
        """Detect the type of project"""
        languages = set(self.file_stats.get('languages', []))
        file_types = self.file_stats.get('file_types', {})
        
        # Check for specific patterns
        has_python = 'Python' in languages
        has_js = 'JavaScript' in languages or 'TypeScript' in languages
        has_java = 'Java' in languages
        has_cpp = 'C++' in languages or 'C' in languages
        has_html = '.html' in file_types
        has_css = '.css' in file_types or '.scss' in file_types
        
        # Web frontend
        if has_js and has_html and has_css:
            return 'Web Frontend Application'
        
        # React app
        if '.jsx' in file_types or '.tsx' in file_types:
            return 'React Application'
        
        # Python web backend
        if has_python and self._has_web_framework():
            return 'Python Web Backend'
        
        # Machine Learning / Data Science
        if has_python and self._has_ml_libraries():
            return 'Machine Learning / Data Science Project'
        
        # Python CLI or Application
        if has_python:
            return 'Python Application'
        
        # Node.js backend
        if has_js and self._file_exists('package.json'):
            if has_html:
                return 'Full-Stack JavaScript Application'
            return 'Node.js Backend'
        
        # Java application
        if has_java:
            return 'Java Application'
        
        # C/C++ project
        if has_cpp:
            return 'C/C++ Application'
        
        # Documentation
        if '.md' in file_types and len(file_types) <= 2:
            return 'Documentation Project'
        
        # Generic
        return 'Mixed Language Project'
    
    def _detect_framework(self) -> str:
        """Detect framework being used"""
        # Check Python frameworks
        if self._check_imports(['fastapi']):
            return 'FastAPI'
        if self._check_imports(['flask']):
            return 'Flask'
        if self._check_imports(['django']):
            return 'Django'
        if self._check_imports(['streamlit']):
            return 'Streamlit'
        
        # Check JavaScript frameworks
        if self._file_exists('package.json'):
            package_json = self._read_package_json()
            if package_json:
                deps = {**package_json.get('dependencies', {}), **package_json.get('devDependencies', {})}
                
                if 'next' in deps:
                    return 'Next.js'
                if 'react' in deps:
                    return 'React'
                if 'vue' in deps:
                    return 'Vue.js'
                if 'angular' in deps or '@angular/core' in deps:
                    return 'Angular'
                if 'express' in deps:
                    return 'Express.js'
                if 'vite' in deps:
                    return 'Vite'
        
        # Check for other indicators
        if self._file_exists('requirements.txt'):
            return 'Python (pip)'
        if self._file_exists('pom.xml'):
            return 'Maven (Java)'
        if self._file_exists('build.gradle'):
            return 'Gradle (Java)'
        if self._file_exists('Cargo.toml'):
            return 'Rust (Cargo)'
        if self._file_exists('go.mod'):
            return 'Go Modules'
        
        return 'None detected'
    
    def _analyze_structure(self) -> Dict:
        """Analyze folder structure"""
        structure = {
            'has_tests': False,
            'has_docs': False,
            'has_config': False,
            'has_src': False,
            'directories': []
        }
        
        # Check for common directories
        for file_path in self.files:
            path_parts = Path(file_path).parts
            
            if 'test' in str(file_path).lower() or 'spec' in str(file_path).lower():
                structure['has_tests'] = True
            if 'doc' in str(file_path).lower() or '.md' in str(file_path):
                structure['has_docs'] = True
            if 'src' in path_parts:
                structure['has_src'] = True
            if 'config' in str(file_path).lower() or self._is_config_file(file_path):
                structure['has_config'] = True
        
        # Get top-level directories
        top_dirs = set()
        for file_path in self.files:
            rel_path = file_path.relative_to(self.root_path)
            if len(rel_path.parts) > 1:
                top_dirs.add(rel_path.parts[0])
        
        structure['directories'] = sorted(list(top_dirs))
        
        return structure
    
    def _infer_purpose(self, project_type: str, framework: str) -> str:
        """Infer the purpose of the project"""
        purposes = {
            'Web Frontend Application': 'Client-side web application for user interfaces',
            'React Application': 'Modern single-page application built with React',
            'Python Web Backend': f'Backend API service built with {framework}',
            'Machine Learning / Data Science Project': 'Data analysis, model training, or ML pipeline',
            'Python Application': 'Python-based application or script',
            'Node.js Backend': 'Server-side application built with Node.js',
            'Full-Stack JavaScript Application': 'Complete web application with frontend and backend',
            'Java Application': 'Enterprise or general-purpose Java application',
            'C/C++ Application': 'System-level or performance-critical application',
            'Documentation Project': 'Documentation or knowledge base',
            'Mixed Language Project': 'Multi-language application or library'
        }
        
        return purposes.get(project_type, 'General software project')
    
    def _identify_key_modules(self) -> List[Dict]:
        """Identify key modules and their roles"""
        modules = []
        
        # Group files by directory
        dir_files = {}
        for file_path in self.files:
            rel_path = file_path.relative_to(self.root_path)
            if len(rel_path.parts) > 1:
                dir_name = rel_path.parts[0]
                if dir_name not in dir_files:
                    dir_files[dir_name] = []
                dir_files[dir_name].append(file_path)
        
        # Analyze each directory
        for dir_name, files in dir_files.items():
            role = self._infer_module_role(dir_name, files)
            if role:
                modules.append({
                    'name': dir_name,
                    'role': role,
                    'file_count': len(files)
                })
        
        # Add root-level important files
        root_files = [f for f in self.files if len(f.relative_to(self.root_path).parts) == 1]
        if root_files:
            important_root = [f for f in root_files if self._is_important_file(f)]
            if important_root:
                modules.insert(0, {
                    'name': 'Root',
                    'role': 'Entry points and configuration files',
                    'file_count': len(important_root)
                })
        
        return modules
    
    def _infer_module_role(self, dir_name: str, files: List[Path]) -> str:
        """Infer the role of a module/directory"""
        dir_lower = dir_name.lower()
        
        roles = {
            'src': 'Source code',
            'lib': 'Library code',
            'utils': 'Utility functions',
            'helpers': 'Helper functions',
            'components': 'UI components',
            'models': 'Data models',
            'views': 'View templates',
            'controllers': 'Controllers',
            'routes': 'API routes',
            'api': 'API endpoints',
            'services': 'Business logic services',
            'db': 'Database layer',
            'database': 'Database layer',
            'tests': 'Unit and integration tests',
            'test': 'Test files',
            'docs': 'Documentation',
            'config': 'Configuration files',
            'public': 'Public static assets',
            'static': 'Static files',
            'assets': 'Media and asset files',
            'styles': 'Stylesheets',
            'css': 'Stylesheets',
            'scripts': 'Scripts and automation',
            'middleware': 'Middleware functions',
            'auth': 'Authentication logic'
        }
        
        return roles.get(dir_lower, f'{dir_name} module')
    
    def _has_web_framework(self) -> bool:
        """Check if project uses a web framework"""
        web_frameworks = ['fastapi', 'flask', 'django', 'tornado', 'aiohttp', 'express']
        return self._check_imports(web_frameworks)
    
    def _has_ml_libraries(self) -> bool:
        """Check if project uses ML libraries"""
        ml_libs = ['tensorflow', 'torch', 'sklearn', 'numpy', 'pandas', 'keras', 'scipy']
        return self._check_imports(ml_libs)
    
    def _check_imports(self, keywords: List[str]) -> bool:
        """Check if any file imports these keywords"""
        for file_path in self.files:
            if file_path.suffix in ['.py', '.js', '.ts']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for keyword in keywords:
                            if keyword in content.lower():
                                return True
                except:
                    continue
        return False
    
    def _file_exists(self, filename: str) -> bool:
        """Check if a file exists in the project"""
        for file_path in self.files:
            if file_path.name == filename:
                return True
        return False
    
    def _read_package_json(self) -> Dict:
        """Read and parse package.json"""
        import json
        for file_path in self.files:
            if file_path.name == 'package.json':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return {}
        return {}
    
    def _is_config_file(self, file_path: Path) -> bool:
        """Check if file is a configuration file"""
        config_files = [
            'package.json', 'requirements.txt', 'setup.py', 'pyproject.toml',
            'tsconfig.json', '.env', 'webpack.config.js', 'vite.config.js',
            'Dockerfile', 'docker-compose.yml', 'pom.xml', 'build.gradle'
        ]
        return file_path.name in config_files
    
    def _is_important_file(self, file_path: Path) -> bool:
        """Check if file is important"""
        important_names = [
            'main.py', 'app.py', 'server.py', 'index.js', 'main.js',
            'package.json', 'requirements.txt', 'README.md'
        ]
        return file_path.name in important_names or self._is_config_file(file_path)
    
    def _generate_description(self, project_type: str, framework: str, structure: Dict) -> str:
        """Generate a comprehensive human-readable description"""
        parts = []
        
        # Analyze the project to understand what it does
        features = self._detect_features()
        tech_stack = self._build_tech_stack(framework)
        
        # === OPENING STATEMENT ===
        parts.append(f"This is a {project_type.lower()}")
        
        if framework != 'None detected':
            parts.append(f"built with {framework}")
        
        # === FEATURE SUMMARY ===
        if features:
            feature_desc = self._describe_features(features, project_type)
            if feature_desc:
                parts.append(feature_desc)
        
        # === TECHNICAL DETAILS ===
        tech_desc = self._describe_tech_stack(tech_stack)
        if tech_desc:
            parts.append(tech_desc)
        
        # === ARCHITECTURE & STRUCTURE ===
        structure_desc = self._describe_structure(structure)
        if structure_desc:
            parts.append(structure_desc)
        
        # === STATISTICS ===
        stats_desc = self._describe_statistics()
        if stats_desc:
            parts.append(stats_desc)
        
        # === CAPABILITIES ===
        capabilities_desc = self._describe_capabilities(project_type, features)
        if capabilities_desc:
            parts.append(capabilities_desc)
        
        return '. '.join(parts) + '.'
    
    def _detect_features(self) -> Dict:
        """Detect features and capabilities from the codebase"""
        features = {
            'database': [],
            'api': [],
            'frontend': [],
            'authentication': False,
            'file_upload': False,
            'real_time': False,
            'testing': False,
            'deployment': [],
            'data_processing': [],
            'visualization': []
        }
        
        # Check all files for indicators
        for file_path in self.files:
            if file_path.suffix not in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    
                    # Database detection
                    if any(db in content for db in ['mongodb', 'mongoose']):
                        if 'MongoDB' not in features['database']:
                            features['database'].append('MongoDB')
                    if any(db in content for db in ['mysql', 'pymysql']):
                        if 'MySQL' not in features['database']:
                            features['database'].append('MySQL')
                    if any(db in content for db in ['postgresql', 'psycopg', 'asyncpg']):
                        if 'PostgreSQL' not in features['database']:
                            features['database'].append('PostgreSQL')
                    if any(db in content for db in ['sqlite', 'sqlite3']):
                        if 'SQLite' not in features['database']:
                            features['database'].append('SQLite')
                    if any(db in content for db in ['redis']):
                        if 'Redis' not in features['database']:
                            features['database'].append('Redis')
                    
                    # API features
                    if 'apigateway' in content or 'api_gateway' in content:
                        features['api'].append('API Gateway')
                    if 'graphql' in content:
                        features['api'].append('GraphQL')
                    if '@app.route' in content or 'router.' in content or 'app.get' in content:
                        features['api'].append('REST API')
                    if 'websocket' in content:
                        features['real_time'] = True
                    
                    # Authentication
                    if any(auth in content for auth in ['jwt', 'passport', 'oauth', 'auth0', 'bcrypt', 'hash']):
                        features['authentication'] = True
                    
                    # File upload
                    if any(upload in content for upload in ['multer', 'upload', 'formdata', 'multipart']):
                        features['file_upload'] = True
                    
                    # Frontend frameworks
                    if 'react' in content and 'React' not in features['frontend']:
                        features['frontend'].append('React')
                    if 'vue' in content and 'Vue.js' not in features['frontend']:
                        features['frontend'].append('Vue.js')
                    if 'angular' in content and 'Angular' not in features['frontend']:
                        features['frontend'].append('Angular')
                    
                    # Data visualization
                    if any(viz in content for viz in ['d3.js', 'd3', 'chart.js', 'plotly', 'matplotlib', 'seaborn']):
                        if 'd3.js' in content or 'd3' in content:
                            features['visualization'].append('D3.js')
                        if 'matplotlib' in content:
                            features['visualization'].append('Matplotlib')
                        if 'plotly' in content:
                            features['visualization'].append('Plotly')
                    
                    # Testing
                    if any(test in content for test in ['jest', 'pytest', 'unittest', 'mocha', 'chai', 'jasmine']):
                        features['testing'] = True
                    
                    # Data processing
                    if 'pandas' in content:
                        features['data_processing'].append('Pandas')
                    if 'numpy' in content:
                        features['data_processing'].append('NumPy')
                    
                    # Deployment
                    if 'docker' in str(file_path).lower():
                        features['deployment'].append('Docker')
                    if 'kubernetes' in content or 'k8s' in content:
                        features['deployment'].append('Kubernetes')
                        
            except:
                continue
        
        return features
    
    def _build_tech_stack(self, framework: str) -> List[str]:
        """Build a list of technologies used"""
        tech = []
        
        languages = self.file_stats.get('languages', [])
        if languages:
            tech.extend(languages)
        
        if framework != 'None detected' and framework not in tech:
            tech.append(framework)
        
        return tech
    
    def _describe_features(self, features: Dict, project_type: str) -> str:
        """Create a description of detected features"""
        descriptions = []
        
        # Database features
        if features['database']:
            db_list = ', '.join(features['database'])
            descriptions.append(f"with {db_list} for data persistence")
        
        # API features
        if features['api']:
            api_types = ', '.join(features['api'])
            descriptions.append(f"providing {api_types} endpoints")
        
        # Authentication
        if features['authentication']:
            descriptions.append("including user authentication and authorization")
        
        # File upload
        if features['file_upload']:
            descriptions.append("supporting file uploads and processing")
        
        # Real-time features
        if features['real_time']:
            descriptions.append("with real-time WebSocket communication")
        
        # Data visualization
        if features['visualization']:
            viz_tools = ', '.join(features['visualization'])
            descriptions.append(f"featuring data visualizations using {viz_tools}")
        
        # Data processing
        if features['data_processing']:
            tools = ', '.join(features['data_processing'])
            descriptions.append(f"leveraging {tools} for data analysis")
        
        if descriptions:
            return "The application includes " + ', '.join(descriptions)
        
        return ""
    
    def _describe_tech_stack(self, tech_stack: List[str]) -> str:
        """Describe the technology stack"""
        if len(tech_stack) > 1:
            return f"The technology stack includes {', '.join(tech_stack)}"
        return ""
    
    def _describe_structure(self, structure: Dict) -> str:
        """Describe the project structure"""
        components = []
        
        if structure['has_src']:
            components.append("well-organized source code")
        if structure['has_tests']:
            components.append("comprehensive test coverage")
        if structure['has_docs']:
            components.append("detailed documentation")
        if structure['has_config']:
            components.append("configuration management")
        
        if components:
            return f"The project is structured with {', '.join(components)}"
        
        return ""
    
    def _describe_statistics(self) -> str:
        """Describe project statistics"""
        total_files = self.file_stats.get('total_files', 0)
        total_lines = self.file_stats.get('total_lines', 0)
        
        if total_files and total_lines:
            size_desc = "small" if total_lines < 500 else "medium-sized" if total_lines < 5000 else "large-scale"
            return f"This is a {size_desc} project containing {total_files} files with approximately {total_lines:,} lines of code"
        
        return ""
    
    def _describe_capabilities(self, project_type: str, features: Dict) -> str:
        """Describe what the project can do"""
        # Build capability description based on project type
        capabilities = {
            'Python Web Backend': 'It serves as a backend service handling API requests, business logic, and data operations',
            'React Application': 'It provides a dynamic, interactive user interface with component-based architecture',
            'Machine Learning / Data Science Project': 'It performs data analysis, builds predictive models, and derives insights from data',
            'Full-Stack JavaScript Application': 'It delivers a complete web solution with both client and server functionality',
            'Node.js Backend': 'It handles server-side operations, routing, and data management',
            'Python Application': 'It executes application logic, processes data, and performs automated tasks'
        }
        
        return capabilities.get(project_type, "")

