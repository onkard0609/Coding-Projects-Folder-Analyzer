import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Try to import Google GenAI (new SDK), but make it optional
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Google GenAI SDK not available: {e}")
    GENAI_AVAILABLE = False
    genai = None

class AISummarizer:
    """Generate AI-powered intelligent project summaries using Google Gemini (New SDK)"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.client = None
        
        if self.api_key and GENAI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini Client: {e}")
                self.client = None
    
    def generate_summary(self, analysis_data: Dict, file_contents: Dict[str, str]) -> Dict:
        """Generate comprehensive AI summary of the project"""
        
        # If AI is not available, return rule-based summary
        if not self.client:
            return self._generate_fallback_summary(analysis_data)
        
        try:
            # Build context for AI
            context = self._build_context(analysis_data, file_contents)
            
            # Generate AI summary
            prompt = self._create_summary_prompt(context)
            
            # Call API using new SDK
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            
            # Parse response
            ai_summary = response.text
            print("DEBUG: AI Summary Length:", len(ai_summary))
            # print("DEBUG: AI Summary Content (First 500 chars):", ai_summary[:500])
            
            flow_chart = self._extract_flow_chart(ai_summary)
            print("DEBUG: Extracted Flow Chart:", flow_chart[:100] if flow_chart else "None")

            return {
                'ai_enabled': True,
                'summary': ai_summary,
                'insights': self._extract_insights(ai_summary),
                'recommendations': self._extract_recommendations(ai_summary),
                'flow_chart': flow_chart
            }
            
        except Exception as e:
            print(f"AI summarization failed: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_fallback_summary(analysis_data)
    
    def _build_context(self, analysis_data: Dict, file_contents: Dict[str, str]) -> str:
        """Build context string from analysis data"""
        context_parts = []
        
        # Project metadata
        summary = analysis_data.get('summary', {})
        stats = analysis_data.get('statistics', {})
        
        context_parts.append(f"PROJECT TYPE: {summary.get('project_type', 'Unknown')}")
        context_parts.append(f"FRAMEWORK: {summary.get('framework', 'None')}")
        context_parts.append(f"LANGUAGES: {', '.join(stats.get('languages', []))}")
        context_parts.append(f"TOTAL FILES: {stats.get('total_files', 0)}")
        context_parts.append(f"LINES OF CODE: {stats.get('total_lines', 0)}")
        
        # File structure
        context_parts.append("\nFILE STRUCTURE:")
        
        def format_tree(node, prefix=""):
            tree_str = ""
            if isinstance(node, dict):
                # Handle root or directory
                name = node.get('name', 'root')
                if node.get('type') == 'directory' or 'children' in node:
                    if name != 'root':
                        tree_str += f"{prefix}📂 {name}/\n"
                    children = node.get('children', [])
                    # Sort: directories first, then files
                    children.sort(key=lambda x: (x.get('type') != 'directory', x.get('name')))
                    
                    for i, child in enumerate(children):
                        is_last = i == len(children) - 1
                        new_prefix = prefix + ("    " if name != 'root' else "")
                        tree_str += format_tree(child, new_prefix)
                else:
                    # File
                    tree_str += f"{prefix}📄 {name}\n"
            return tree_str

        file_tree = analysis_data.get('file_tree', {})
        if file_tree:
            context_parts.append(format_tree(file_tree))
        else:
             # Fallback to list if tree not available
            for file_path in list(file_contents.keys())[:50]:
                context_parts.append(f"  - {file_path}")
        
        # Important files content (top 5)
        importance = analysis_data.get('importance', [])
        if importance:
            context_parts.append("\nKEY FILES CONTENT:")
            top_files = sorted(importance, key=lambda x: x.get('score', 0), reverse=True)[:5]
            
            for file_info in top_files:
                file_name = file_info.get('file', '')
                if file_name in file_contents:
                    content = file_contents[file_name]
                    # Limit content length
                    if len(content) > 500:
                        content = content[:500] + "..."
                    context_parts.append(f"\n--- {file_name} ---")
                    context_parts.append(content)
        
        # Dependencies
        deps = analysis_data.get('dependencies', {})
        edges = deps.get('edges', [])
        if edges:
            context_parts.append(f"\nDEPENDENCIES: {len(edges)} connections found")
            sample_deps = edges[:10]
            for edge in sample_deps:
                context_parts.append(f"  {edge.get('source')} -> {edge.get('target')}")
        
        return '\n'.join(context_parts)
    
    def _create_summary_prompt(self, context: str) -> str:
        """Create prompt for AI summarization"""
        prompt = f"""You are an expert software analyst. Analyze this project and provide a comprehensive summary.

{context}

Please provide a detailed analysis covering:

1. **Executive Summary** (2-3 sentences): What is this project and what does it do?

2. **Project Purpose**: Explain the main purpose and goals of this project.

3. **Key Features**: List the main features and capabilities you can identify from the code.

4. **Technology Stack**: Describe the technologies, frameworks, and libraries used.

5. **Architecture**: Explain how the project is structured and organized.

6. **Use Cases**: What are the likely use cases for this project?

7. **Code Quality Insights**: Any observations about code organization, best practices, or potential improvements.

8. **Recommendations**: 2-3 actionable recommendations for improving or extending the project.

9. **Execution Flow**: Create a Mermaid flowchart (graph TD) representing the logical execution flow of the application. Focus on how a user would interact with the system or how data flows. Use clear node names and labels. Wrap the mermaid code in a markdown code block (```mermaid ... ```).

Please be specific and reference actual files or code patterns you observe. Write in a professional but accessible tone.
"""
        return prompt
    
    def _extract_insights(self, ai_summary: str) -> List[str]:
        """Extract key insights from AI summary"""
        insights = []
        
        # Look for insight markers
        lines = ai_summary.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                insights.append(line[2:].strip())
            elif any(keyword in line.lower() for keyword in ['uses', 'implements', 'provides', 'features']):
                if len(line) > 20 and len(line) < 200:
                    insights.append(line)
        
        return insights[:10]  # Limit to 10 insights
    
    def _extract_recommendations(self, ai_summary: str) -> List[str]:
        """Extract recommendations from AI summary"""
        recommendations = []
        
        # Look for recommendations section
        if 'Recommendations' in ai_summary or 'recommendations' in ai_summary:
            lines = ai_summary.split('\n')
            in_recommendations = False
            
            for line in lines:
                if 'recommendation' in line.lower():
                    in_recommendations = True
                    continue
                
                if in_recommendations:
                    line = line.strip()
                    if line.startswith(('1.', '2.', '3.', '- ', '* ')):
                        # Remove numbering/bullets
                        rec = line.lstrip('0123456789.-* ').strip()
                        if rec:
                            recommendations.append(rec)
                    elif line and not line.startswith('#'):
                        # Stop if we hit a new section
                        if line.startswith('**') or line.isupper():
                            break
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _extract_flow_chart(self, ai_summary: str) -> str:
        """Extract Mermaid flow chart from AI summary"""
        try:
            # Look for mermaid code block
            if '```mermaid' in ai_summary:
                parts = ai_summary.split('```mermaid')
                if len(parts) > 1:
                    code_block = parts[1].split('```')[0].strip()
                    # Ensure it starts with graph or flowchart
                    if code_block.startswith('graph') or code_block.startswith('flowchart'):
                        return code_block
            
            # Alternative: Look for just the graph definition if no code block
            lines = ai_summary.split('\n')
            graph_lines = []
            in_graph = False
            
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('graph ') or stripped.startswith('flowchart '):
                    in_graph = True
                    graph_lines.append(stripped)
                    continue
                
                if in_graph:
                    # Heuristic to detect end of graph (empty line or new header)
                    if not stripped or stripped.startswith('#') or stripped.startswith('*'):
                        if len(graph_lines) > 2: # At least graph decl + 2 lines
                            break
                        # If just empty lines, maybe continue? But safe to break for now
                        if not stripped:
                             continue
                        break
                    graph_lines.append(line)
            
            if len(graph_lines) > 1:
                return '\n'.join(graph_lines)
                
            return ""
        except Exception:
            return ""
    
    def _generate_fallback_summary(self, analysis_data: Dict) -> Dict:
        """Generate rule-based summary when AI is not available"""
        summary = analysis_data.get('summary', {})
        stats = analysis_data.get('statistics', {})
        importance = analysis_data.get('importance', [])
        
        # Create basic summary
        project_type = summary.get('project_type', 'Unknown Project')
        framework = summary.get('framework', 'None detected')
        total_files = stats.get('total_files', 0)
        total_lines = stats.get('total_lines', 0)
        languages = ', '.join(stats.get('languages', []))
        
        fallback_text = f"""**Executive Summary**

This is a {project_type.lower()}"""
        
        if framework != 'None detected':
            fallback_text += f" built with {framework}"
        
        fallback_text += f". The project contains {total_files} files with approximately {total_lines:,} lines of code"
        
        if languages:
            fallback_text += f", written primarily in {languages}"
        
        fallback_text += ".\n\n**Project Analysis**\n\n"
        
        # Add description
        if summary.get('description'):
            fallback_text += summary['description'] + "\n\n"
        
        # Add key modules
        if summary.get('key_modules'):
            fallback_text += "**Key Components**\n\n"
            for module in summary['key_modules']:
                fallback_text += f"- **{module['name']}**: {module['role']} ({module['file_count']} files)\n"
            fallback_text += "\n"
        
        # Add important files
        if importance:
            top_files = sorted(importance, key=lambda x: x.get('score', 0), reverse=True)[:5]
            fallback_text += "**Most Critical Files**\n\n"
            for file_info in top_files:
                score = file_info.get('score', 0)
                file_name = file_info.get('file', '')
                fallback_text += f"- {file_name} (Importance: {score:.1f}/100)\n"
        
        return {
            'ai_enabled': False,
            'summary': fallback_text,
            'insights': [],
            'recommendations': [
                "Consider adding comprehensive documentation",
                "Implement automated testing for critical components",
                "Review code for optimization opportunities"
            ]
        }
