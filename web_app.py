"""
FastAPI Web Application for CAB (CodeAssistBench)
Provides a web interface for running the benchmark pipeline and viewing results.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
import logging
from pathlib import Path
import uvicorn

from cab_config import get_config
from cab_pipeline import CABPipeline, PipelineStep

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CAB - CodeAssistBench",
    description="Web interface for the CodeAssistBench research project",
    version="2.0.0"
)

# Add CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.web.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline_instance: Optional[CABPipeline] = None

# Pydantic models for API
class PipelineRequest(BaseModel):
    languages: List[str] = ["python", "javascript", "typescript"]
    skip_steps: Optional[List[str]] = None
    demo_mode: bool = False

class PipelineResponse(BaseModel):
    status: str
    message: str
    pipeline_id: Optional[str] = None

class StatusResponse(BaseModel):
    status: Dict[str, Any]
    is_running: bool
    current_step: Optional[str] = None

# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CAB - CodeAssistBench</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2c3e50; margin-bottom: 10px; }
            .header p { color: #7f8c8d; font-size: 18px; }
            .section { margin-bottom: 30px; }
            .section h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #2c3e50; }
            .form-group select, .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
            .checkbox-group { display: flex; flex-wrap: wrap; gap: 10px; }
            .checkbox-item { display: flex; align-items: center; gap: 5px; }
            .btn { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-right: 10px; }
            .btn:hover { background: #2980b9; }
            .btn:disabled { background: #bdc3c7; cursor: not-allowed; }
            .btn-danger { background: #e74c3c; }
            .btn-danger:hover { background: #c0392b; }
            .status { padding: 15px; border-radius: 5px; margin: 20px 0; }
            .status.running { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .status.completed { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
            .status.error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .progress-bar { width: 100%; height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; margin: 10px 0; }
            .progress-fill { height: 100%; background: #3498db; transition: width 0.3s ease; }
            .step-list { list-style: none; padding: 0; }
            .step-item { padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 4px solid #ddd; }
            .step-item.pending { background: #f8f9fa; }
            .step-item.running { background: #e3f2fd; border-left-color: #2196f3; }
            .step-item.completed { background: #e8f5e8; border-left-color: #4caf50; }
            .step-item.failed { background: #ffebee; border-left-color: #f44336; }
            .results { margin-top: 30px; }
            .metric { display: inline-block; background: #ecf0f1; padding: 15px; margin: 10px; border-radius: 5px; text-align: center; min-width: 150px; }
            .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
            .metric-label { color: #7f8c8d; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 CAB - CodeAssistBench</h1>
                <p>NeurIPS 2024 - Comprehensive Benchmark for AI Coding Assistants</p>
            </div>

            <div class="section">
                <h2>🔧 Configuration</h2>
                <div class="form-group">
                    <label for="languages">Programming Languages:</label>
                    <div class="checkbox-group">
                        <div class="checkbox-item">
                            <input type="checkbox" id="python" value="python" checked>
                            <label for="python">Python</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="javascript" value="javascript" checked>
                            <label for="javascript">JavaScript</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="typescript" value="typescript" checked>
                            <label for="typescript">TypeScript</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="java" value="java">
                            <label for="java">Java</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="c" value="c">
                            <label for="c">C</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="cpp" value="c++">
                            <label for="cpp">C++</label>
                        </div>
                        <div class="checkbox-item">
                            <input type="checkbox" id="csharp" value="c#">
                            <label for="csharp">C#</label>
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="demo-mode"> Run in Demo Mode (uses pre-computed data)
                    </label>
                </div>
            </div>

            <div class="section">
                <h2>▶️ Pipeline Control</h2>
                <button id="start-btn" class="btn" onclick="startPipeline()">Start Pipeline</button>
                <button id="stop-btn" class="btn btn-danger" onclick="stopPipeline()" disabled>Stop Pipeline</button>
                <button id="status-btn" class="btn" onclick="refreshStatus()">Refresh Status</button>
            </div>

            <div id="status-section" class="section" style="display: none;">
                <h2>📊 Pipeline Status</h2>
                <div id="status-display"></div>
                <div id="progress-display"></div>
                <ul id="steps-list" class="step-list"></ul>
            </div>

            <div id="results-section" class="section" style="display: none;">
                <h2>📈 Results</h2>
                <div id="results-display"></div>
            </div>
        </div>

        <script>
            let statusInterval;
            let isRunning = false;

            async function startPipeline() {
                const languages = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
                    .map(cb => cb.value);
                const demoMode = document.getElementById('demo-mode').checked;

                try {
                    const response = await fetch('/api/pipeline/start', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ languages, demo_mode: demoMode })
                    });

                    const result = await response.json();
                    
                    if (response.ok) {
                        isRunning = true;
                        document.getElementById('start-btn').disabled = true;
                        document.getElementById('stop-btn').disabled = false;
                        document.getElementById('status-section').style.display = 'block';
                        
                        // Start polling for status
                        statusInterval = setInterval(refreshStatus, 2000);
                        refreshStatus();
                    } else {
                        alert('Error: ' + result.message);
                    }
                } catch (error) {
                    alert('Error starting pipeline: ' + error.message);
                }
            }

            async function stopPipeline() {
                try {
                    await fetch('/api/pipeline/stop', { method: 'POST' });
                    isRunning = false;
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
                    clearInterval(statusInterval);
                } catch (error) {
                    alert('Error stopping pipeline: ' + error.message);
                }
            }

            async function refreshStatus() {
                try {
                    const response = await fetch('/api/pipeline/status');
                    const status = await response.json();
                    
                    updateStatusDisplay(status);
                    
                    if (!status.is_running) {
                        isRunning = false;
                        document.getElementById('start-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = true;
                        clearInterval(statusInterval);
                    }
                } catch (error) {
                    console.error('Error fetching status:', error);
                }
            }

            function updateStatusDisplay(status) {
                const statusDisplay = document.getElementById('status-display');
                const progressDisplay = document.getElementById('progress-display');
                const stepsList = document.getElementById('steps-list');

                // Update status
                statusDisplay.innerHTML = `
                    <div class="status ${status.is_running ? 'running' : 'completed'}">
                        <strong>Status:</strong> ${status.is_running ? 'Running' : 'Completed'}
                        ${status.current_step ? `<br><strong>Current Step:</strong> ${status.current_step}` : ''}
                    </div>
                `;

                // Update progress
                const totalSteps = Object.keys(status.status).length;
                const completedSteps = Object.values(status.status).filter(s => s.status === 'completed').length;
                const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

                progressDisplay.innerHTML = `
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <p>Progress: ${completedSteps}/${totalSteps} steps completed (${progress.toFixed(1)}%)</p>
                `;

                // Update steps list
                stepsList.innerHTML = Object.entries(status.status)
                    .map(([step, stepStatus]) => `
                        <li class="step-item ${stepStatus.status}">
                            <strong>${step.replace(/_/g, ' ').toUpperCase()}</strong>
                            <br>Status: ${stepStatus.status}
                            ${stepStatus.progress > 0 ? `<br>Progress: ${(stepStatus.progress * 100).toFixed(1)}%` : ''}
                            ${stepStatus.error_message ? `<br>Error: ${stepStatus.error_message}` : ''}
                        </li>
                    `).join('');
            }

            // Initialize
            refreshStatus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/pipeline/start", response_model=PipelineResponse)
async def start_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """Start the CAB pipeline"""
    global pipeline_instance
    
    try:
        if pipeline_instance and any(status.status == "running" for status in pipeline_instance.status.values()):
            raise HTTPException(status_code=400, detail="Pipeline is already running")
        
        pipeline_instance = CABPipeline()
        
        if request.demo_mode:
            background_tasks.add_task(run_demo_pipeline, pipeline_instance)
        else:
            skip_steps = [PipelineStep(step) for step in (request.skip_steps or [])]
            background_tasks.add_task(run_pipeline_task, pipeline_instance, request.languages, skip_steps)
        
        return PipelineResponse(
            status="started",
            message="Pipeline started successfully",
            pipeline_id="main"
        )
    except Exception as e:
        logger.error(f"Error starting pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipeline/stop", response_model=PipelineResponse)
async def stop_pipeline():
    """Stop the running pipeline"""
    global pipeline_instance
    
    try:
        if not pipeline_instance:
            raise HTTPException(status_code=400, detail="No pipeline is running")
        
        # In a real implementation, you'd need to implement proper cancellation
        # For now, we'll just mark it as stopped
        for step in pipeline_instance.status:
            if pipeline_instance.status[step].status == "running":
                pipeline_instance._update_status(step, "stopped")
        
        return PipelineResponse(
            status="stopped",
            message="Pipeline stopped successfully"
        )
    except Exception as e:
        logger.error(f"Error stopping pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pipeline/status", response_model=StatusResponse)
async def get_pipeline_status():
    """Get current pipeline status"""
    global pipeline_instance
    
    if not pipeline_instance:
        return StatusResponse(
            status={},
            is_running=False
        )
    
    status = pipeline_instance.get_status()
    is_running = any(step_status["status"] == "running" for step_status in status.values())
    current_step = next(
        (step for step, step_status in status.items() if step_status["status"] == "running"),
        None
    )
    
    return StatusResponse(
        status=status,
        is_running=is_running,
        current_step=current_step
    )

@app.get("/api/results")
async def get_results():
    """Get pipeline results"""
    global pipeline_instance
    
    if not pipeline_instance:
        raise HTTPException(status_code=404, detail="No results available")
    
    return pipeline_instance.results

@app.get("/api/config")
async def get_configuration():
    """Get current configuration"""
    config = get_config()
    return {
        "api_keys_configured": config.validate_api_keys(),
        "directories": {
            "base": config.directories.base,
            "results": config.directories.results,
            "logs": config.directories.logs
        },
        "pipeline": {
            "max_repos_per_language": config.pipeline.max_repos_per_language,
            "max_issues_per_repo": config.pipeline.max_issues_per_repo
        }
    }

# Background task functions
async def run_pipeline_task(pipeline: CABPipeline, languages: List[str], skip_steps: List[PipelineStep]):
    """Background task to run the pipeline"""
    try:
        results = pipeline.run_full_pipeline(languages, skip_steps)
        pipeline.results = results
        logger.info("Pipeline completed successfully")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

async def run_demo_pipeline(pipeline: CABPipeline):
    """Background task to run demo pipeline"""
    try:
        results = pipeline.run_demo_mode()
        pipeline.results = results
        logger.info("Demo pipeline completed successfully")
    except Exception as e:
        logger.error(f"Demo pipeline failed: {e}")
        raise

def main():
    """Run the web application"""
    config = get_config()
    
    print("🚀 Starting CAB Web Interface...")
    print(f"📊 Dashboard: http://{config.web.host}:{config.web.port}")
    print(f"📚 API Docs: http://{config.web.host}:{config.web.port}/docs")
    
    uvicorn.run(
        "web_app:app",
        host=config.web.host,
        port=config.web.port,
        reload=config.web.debug
    )

if __name__ == "__main__":
    main()
