from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import json
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from utils.file_handler import FileHandler
from analyzer.dependency_analyzer import DependencyAnalyzer
from analyzer.importance_scorer import ImportanceScorer
from analyzer.project_summarizer import ProjectSummarizer
from analyzer.flow_analyzer import FlowAnalyzer
from analyzer.ai_summarizer import AISummarizer

app = FastAPI(title="Folder Analyzer API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize file handler
file_handler = FileHandler(upload_dir="uploads")

# In-memory storage for analysis results (use Redis in production)
analysis_cache = {}


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Folder Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "upload_zip": "/upload/zip",
            "analyze": "/analyze/{session_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/upload/zip")
async def upload_zip(file: UploadFile = File(...)):
    """
    Upload and analyze a zip file
    
    Args:
        file: Zip file containing the project folder
    
    Returns:
        Analysis results including dependencies, importance scores, and summary
    """
    try:
        # Validate file type
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Only .zip files are supported")
        
        # Create session
        session_id = file_handler.create_session()
        
        # Save uploaded file
        zip_path = file_handler.upload_dir / session_id / "upload.zip"
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract zip
        extract_path = file_handler.extract_zip(zip_path, session_id)
        
        # Find the actual project root (handle single-folder zips)
        project_root = extract_path
        subdirs = list(extract_path.iterdir())
        if len(subdirs) == 1 and subdirs[0].is_dir():
            project_root = subdirs[0]
        
        # Analyze the project
        result = await analyze_project(project_root, session_id)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/upload/folder")
async def upload_folder(files: List[UploadFile] = File(...)):
    """
    Upload and analyze a folder (multiple files with paths)
    
    This endpoint handles folder uploads where files are sent with their relative paths
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        # Create session
        session_id = file_handler.create_session()
        folder_path = file_handler.upload_dir / session_id / "folder"
        folder_path.mkdir(exist_ok=True)
        
        # Save files preserving structure
        for upload_file in files:
            # Get relative path from filename (browsers may include path)
            file_path = folder_path / upload_file.filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
        
        # Analyze the project
        result = await analyze_project(folder_path, session_id)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def analyze_project(root_path: Path, session_id: str) -> dict:
    """
    Perform comprehensive project analysis
    
    Args:
        root_path: Path to the project root directory
        session_id: Session identifier
    
    Returns:
        Complete analysis results
    """
    try:
        # Get all files
        files = file_handler.get_all_files(root_path)
        
        if not files:
            raise HTTPException(status_code=400, detail="No analyzable files found in the upload")
        
        # Get file statistics
        file_stats = file_handler.get_file_stats(root_path)
        
        # Get file tree
        file_tree = file_handler.get_file_tree(root_path)
        
        # Analyze dependencies
        dep_analyzer = DependencyAnalyzer(root_path)
        dependency_result = dep_analyzer.analyze(files)
        
        # Calculate importance scores
        importance_scorer = ImportanceScorer(dependency_result['graph'], root_path)
        importance_scores = importance_scorer.calculate_scores()
        entry_points = importance_scorer.get_entry_points()
        
        # Generate project summary
        summarizer = ProjectSummarizer(root_path, files, file_stats)
        project_summary = summarizer.generate_summary()
        
        # Analyze execution flow
        flow_analyzer = FlowAnalyzer(dependency_result['graph'], root_path, files)
        flow_analysis = flow_analyzer.analyze_flow(entry_points)
        
        # === AI-POWERED INTELLIGENT SUMMARY ===
        # Read file contents for AI analysis (limit to important files)
        file_contents = {}
        for file_path in files[:30]:  # Limit to 30 files for AI analysis
            try:
                # Only read text files
                if file_path.suffix in ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.md', '.txt', '.json', '.yaml', '.yml']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Limit content size
                        if len(content) > 2000:
                            content = content[:2000] + "\n... (truncated)"
                        rel_path = file_path.relative_to(root_path)
                        file_contents[str(rel_path)] = content
            except:
                continue
        
        # Generate AI summary
        ai_summarizer = AISummarizer()  # Will use GEMINI_API_KEY env variable if available
        ai_summary = ai_summarizer.generate_summary({
            'summary': project_summary,
            'statistics': file_stats,
            'importance': importance_scores,
            'dependencies': {
                'nodes': dependency_result['nodes'],
                'edges': dependency_result['edges']
            },
            'file_tree': file_tree
        }, file_contents)
        
        # Build complete result
        result = {
            "session_id": session_id,
            "status": "success",
            "file_tree": file_tree,
            "statistics": file_stats,
            "dependencies": {
                "nodes": dependency_result['nodes'],
                "edges": dependency_result['edges']
            },
            "importance": importance_scores,
            "summary": project_summary,
            "flow": flow_analysis,
            "ai_summary": ai_summary,  # Added AI summary
            "metadata": {
                "total_files_analyzed": len(files),
                "languages_detected": file_stats.get('languages', []),
                "entry_points": entry_points,
                "ai_enabled": ai_summary.get('ai_enabled', False)
            }
        }
        
        # Override flow with AI flow if available and valid
        if ai_summary.get('flow_chart'):
            print("DEBUG: Overriding flow with AI generated flow")
            result['flow']['mermaid_diagram'] = ai_summary['flow_chart']
            result['flow']['flow_description'] = "AI-generated execution flow based on project analysis."
            result['flow']['has_flow'] = True
        else:
             print("DEBUG: No AI flow chart found in summary")
        
        # Cache result
        analysis_cache[session_id] = result
        
        return result
    
    except Exception as e:
        # Clean up on error
        file_handler.cleanup_session(session_id)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@app.get("/analyze/{session_id}")
async def get_analysis(session_id: str):
    """
    Retrieve cached analysis results
    
    Args:
        session_id: Session identifier from upload
    
    Returns:
        Cached analysis results
    """
    if session_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis_cache[session_id]


@app.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """
    Clean up session data
    
    Args:
        session_id: Session identifier to clean up
    """
    try:
        file_handler.cleanup_session(session_id)
        if session_id in analysis_cache:
            del analysis_cache[session_id]
        
        return {"status": "success", "message": "Session cleaned up"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

