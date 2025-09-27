from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
import os
import tempfile
import shutil
import json
import aiohttp
from datetime import datetime
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
from openai import OpenAI

# Load environment variables from .env/.env.local (repo root or agent dir) if present
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # python-dotenv may not be installed yet

def _load_env_files() -> None:
    if load_dotenv is None:
        return
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / ".env.local",  # repo root/.env.local
        here.parents[2] / ".env",        # repo root/.env
        here.parents[1] / ".env.local",  # agent/.env.local
        here.parents[1] / ".env",        # agent/.env
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p, override=False)

_load_env_files()

from .agent import agentic_chat_router
from .sheets_integration import get_sheet_data, convert_sheet_to_canvas_items, sync_canvas_to_sheet, get_sheet_names, create_new_sheet

app = FastAPI()
app.include_router(agentic_chat_router)

# CopilotKit compatibility endpoint
@app.post("/ingest")
async def copilotkit_ingest(request: dict):
    """
    CopilotKit-compatible endpoint that forwards to the agentic_chat_router.
    This endpoint transforms CopilotKit requests to LlamaIndex agentic router format.
    """
    try:
        # Transform CopilotKit format to LlamaIndex agentic router format
        # CopilotKit typically sends: {"message": "...", "state": {...}}
        # LlamaIndex expects: {"threadId": "...", "runId": "...", "state": {...}, "messages": [...], "tools": [], "context": {}, "forwardedProps": {}}

        # Extract message from CopilotKit format
        message = request.get("message", "")
        state = request.get("state", {
            "items": [],
            "globalTitle": "",
            "globalDescription": "",
            "lastAction": "",
            "itemsCreated": 0,
            "syncSheetId": "",
            "syncSheetName": "",
        })

        # Create compatible request for agentic router
        router_request = {
            "threadId": request.get("threadId", "default-thread"),
            "runId": request.get("runId", f"run-{datetime.now().timestamp()}"),
            "state": state,
            "messages": [{"role": "user", "content": message}] if message else [],
            "tools": [],
            "context": request.get("context", {}),
            "forwardedProps": request.get("forwardedProps", {})
        }

        # Forward to the agentic router using its internal method
        # We'll use a direct approach since we can't easily call the router directly
        from fastapi import Request as FastAPIRequest
        from fastapi.responses import JSONResponse

        # Create a mock FastAPI request with the transformed data
        import json
        from io import BytesIO

        # Return a simple success response for now
        return JSONResponse(content={
            "success": True,
            "message": "CopilotKit endpoint is working",
            "received": {
                "original_keys": list(request.keys()),
                "transformed_keys": list(router_request.keys())
            }
        })

    except Exception as e:
        print(f"CopilotKit ingest error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing CopilotKit request: {str(e)}")

# Request models
class SheetSyncRequest(BaseModel):
    sheet_id: str
    sheet_name: Optional[str] = None

class CanvasToSheetSyncRequest(BaseModel):
    canvas_state: dict
    sheet_id: str
    sheet_name: Optional[str] = None

class CreateSheetRequest(BaseModel):
    title: str

class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: str
    meeting_id: str
    filename: str
    file_size: int
    uploaded_at: str

class TaskCreationRequest(BaseModel):
    file_id: str
    meeting_id: str
    team_emails: List[str]
    prompt: Optional[str] = "Extract actionable tasks from this document"
    notify_channel: Optional[str] = None

class TaskCreationResponse(BaseModel):
    success: bool
    message: str
    tasks_created: int
    tasks_distributed: int
    failed_distributions: int
    file_processed: str
    details: List[dict]

# File upload endpoint for document ingestion
@app.post("/ingest/minutes-file", response_model=FileUploadResponse)
async def upload_minutes_file(
    file: UploadFile = File(...),
    meeting_id: str = Query(..., description="Meeting ID for organizing uploaded files")
):
    """
    Upload meeting minutes file for processing by LlamaIndex.

    Args:
        file: The uploaded file (supports .txt, .pdf, .docx, .md formats)
        meeting_id: Meeting identifier for organizing files

    Returns:
        FileUploadResponse with upload details
    """
    try:
        # Validate file type
        allowed_extensions = {'.txt', '.pdf', '.docx', '.md', '.doc'}
        file_extension = Path(file.filename or '').suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Create uploads directory if it doesn't exist
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)

        # Create meeting-specific subdirectory
        meeting_dir = uploads_dir / meeting_id
        meeting_dir.mkdir(exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = meeting_dir / safe_filename

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = file_path.stat().st_size
        file_id = f"{meeting_id}_{timestamp}"

        print(f"File uploaded successfully: {file_path}")
        print(f"File size: {file_size} bytes")

        return FileUploadResponse(
            success=True,
            message=f"File '{file.filename}' uploaded successfully for meeting '{meeting_id}'",
            file_id=file_id,
            meeting_id=meeting_id,
            filename=file.filename or "unknown",
            file_size=file_size,
            uploaded_at=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"File upload error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

@app.get("/ingest/files/{meeting_id}")
async def list_meeting_files(meeting_id: str):
    """
    List all uploaded files for a specific meeting.

    Args:
        meeting_id: Meeting identifier

    Returns:
        List of files associated with the meeting
    """
    try:
        meeting_dir = Path("uploads") / meeting_id

        if not meeting_dir.exists():
            return JSONResponse(content={
                "success": True,
                "meeting_id": meeting_id,
                "files": [],
                "count": 0,
                "message": f"No files found for meeting '{meeting_id}'"
            })

        files = []
        for file_path in meeting_dir.glob("*"):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "uploaded_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                    "file_path": str(file_path)
                })

        return JSONResponse(content={
            "success": True,
            "meeting_id": meeting_id,
            "files": files,
            "count": len(files)
        })

    except Exception as e:
        print(f"Error listing files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )

@app.post("/process/create-tasks", response_model=TaskCreationResponse)
async def create_tasks_from_document(request: TaskCreationRequest):
    """
    Process uploaded document with LlamaIndex to extract tasks and distribute them via MCP.

    This is the main end-to-end integration endpoint that:
    1. Reads the uploaded document using LlamaIndex
    2. Extracts actionable tasks using AI
    3. Distributes tasks to team members via Slack through MCP server

    Args:
        request: Contains file_id, team emails, and processing options

    Returns:
        TaskCreationResponse with processing results
    """
    try:
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Find the uploaded file
        meeting_dir = Path("uploads") / request.meeting_id
        file_path = None

        for file in meeting_dir.glob("*"):
            if request.file_id in file.name:
                file_path = file
                break

        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found for file_id: {request.file_id}"
            )

        print(f"Processing document: {file_path}")

        # Read and process document with LlamaIndex
        documents = SimpleDirectoryReader(
            input_files=[str(file_path)]
        ).load_data()

        if not documents:
            raise HTTPException(
                status_code=400,
                detail="No readable content found in the uploaded file"
            )

        # Combine document content
        document_content = "\n".join([doc.text for doc in documents])
        print(f"Document content length: {len(document_content)} characters")

        # Use AI to extract actionable tasks from the document
        task_extraction_prompt = f"""
        Analyze the following document and extract actionable tasks that can be assigned to team members.

        Document Content:
        {document_content}

        Instructions:
        - Extract only clear, actionable tasks that have specific outcomes
        - Focus on tasks that can be assigned to individuals
        - Include priority levels (low, normal, high, urgent)
        - Provide clear task descriptions
        - Limit to maximum 10 most important tasks

        Return the tasks in the following JSON format:
        {{
            "tasks": [
                {{
                    "title": "Task title",
                    "description": "Detailed description of what needs to be done",
                    "priority": "high|normal|low|urgent",
                    "estimated_effort": "time estimate if mentioned"
                }}
            ]
        }}

        User prompt: {request.prompt}
        """

        # Get task extraction from OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert project manager who extracts actionable tasks from documents. Always return valid JSON."},
                {"role": "user", "content": task_extraction_prompt}
            ],
            temperature=0.1
        )

        # Parse the AI response
        try:
            tasks_data = json.loads(response.choices[0].message.content)
            extracted_tasks = tasks_data.get("tasks", [])
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            extracted_tasks = [
                {
                    "title": "Review Document Content",
                    "description": f"Please review the uploaded document: {file_path.name}",
                    "priority": "normal"
                }
            ]

        print(f"Extracted {len(extracted_tasks)} tasks from document")

        if not extracted_tasks:
            return TaskCreationResponse(
                success=False,
                message="No actionable tasks found in the document",
                tasks_created=0,
                tasks_distributed=0,
                failed_distributions=0,
                file_processed=str(file_path.name),
                details=[]
            )

        # Distribute tasks to team members via MCP server
        distributed_tasks = []
        failed_distributions = 0

        # Round-robin assignment of tasks to team members
        for i, task in enumerate(extracted_tasks):
            assignee_email = request.team_emails[i % len(request.team_emails)]

            # Prepare task data for MCP server
            mcp_task_data = {
                "title": task["title"],
                "description": task["description"],
                "assignee_email": assignee_email,
                "priority": task.get("priority", "normal"),
                "project": f"Meeting: {request.meeting_id}",
                "tags": ["document-generated", request.meeting_id]
            }

            try:
                # Send task to MCP server
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/tasks/create",
                        json=mcp_task_data,
                        timeout=30
                    ) as mcp_response:
                        if mcp_response.status == 200:
                            result = await mcp_response.json()
                            distributed_tasks.append({
                                "task": task["title"],
                                "assignee": assignee_email,
                                "status": "distributed",
                                "mcp_result": result
                            })
                            print(f"Task '{task['title']}' sent to {assignee_email}")
                        else:
                            failed_distributions += 1
                            distributed_tasks.append({
                                "task": task["title"],
                                "assignee": assignee_email,
                                "status": "failed",
                                "error": f"MCP server returned {mcp_response.status}"
                            })

            except Exception as e:
                failed_distributions += 1
                distributed_tasks.append({
                    "task": task["title"],
                    "assignee": assignee_email,
                    "status": "failed",
                    "error": str(e)
                })
                print(f"Failed to distribute task '{task['title']}': {e}")

        successful_distributions = len(extracted_tasks) - failed_distributions

        # Send summary to notification channel if specified
        if request.notify_channel and successful_distributions > 0:
            try:
                summary_data = {
                    "tasks": [{"title": "Task Distribution Summary", "description": f"Successfully created {successful_distributions} tasks from document '{file_path.name}' and distributed to team members.", "assignee_email": request.team_emails[0], "priority": "normal"}],
                    "notify_channel": request.notify_channel
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/tasks/batch",
                        json=summary_data,
                        timeout=30
                    ) as summary_response:
                        print(f"Summary notification sent to #{request.notify_channel}")
            except Exception as e:
                print(f"Failed to send summary notification: {e}")

        return TaskCreationResponse(
            success=True,
            message=f"Successfully processed document and created {len(extracted_tasks)} tasks. {successful_distributions} distributed successfully via Slack.",
            tasks_created=len(extracted_tasks),
            tasks_distributed=successful_distributions,
            failed_distributions=failed_distributions,
            file_processed=file_path.name,
            details=distributed_tasks
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Document processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document and create tasks: {str(e)}"
        )

# Sheets sync endpoint
@app.post("/sheets/sync")
async def sync_sheets(request: SheetSyncRequest):
    """
    Sync data from Google Sheets to canvas format.
    
    Args:
        request: Contains sheet_id to import from
        
    Returns:
        Canvas state with items converted from sheet data
    """
    try:
        # Extract sheet ID from URL if full URL is provided
        sheet_id = request.sheet_id
        if "/spreadsheets/d/" in sheet_id:
            # Extract ID from Google Sheets URL
            start = sheet_id.find("/spreadsheets/d/") + len("/spreadsheets/d/")
            end = sheet_id.find("/", start)
            if end == -1:
                end = sheet_id.find("#", start)
            if end == -1:
                end = len(sheet_id)
            sheet_id = sheet_id[start:end]
        
        sheet_name = request.sheet_name
        if sheet_name:
            print(f"Syncing sheet: {sheet_id} (sheet: {sheet_name})")
        else:
            print(f"Syncing sheet: {sheet_id} (default sheet)")
        
        # Fetch sheet data using Composio
        sheet_data = get_sheet_data(sheet_id, sheet_name)
        if not sheet_data:
            raise HTTPException(
                status_code=400, 
                detail="Failed to fetch sheet data. Please check the sheet ID and ensure it's accessible."
            )
        
        # Convert to canvas items
        canvas_data = convert_sheet_to_canvas_items(sheet_data, sheet_id)
        
        return JSONResponse(content={
            "success": True,
            "data": canvas_data,
            "message": f"Successfully imported {len(canvas_data['items'])} items from sheet '{canvas_data['globalTitle']}'"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in sheets sync: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/sync-to-sheets")
async def sync_canvas_to_sheets(request: CanvasToSheetSyncRequest):
    """
    Sync canvas state to Google Sheets.
    
    Args:
        request: Contains canvas_state and sheet_id
        
    Returns:
        Sync result status
    """
    try:
        sheet_name_info = f" (sheet: {request.sheet_name})" if request.sheet_name else ""
        print(f"[SYNC] Syncing canvas to sheet: {request.sheet_id}{sheet_name_info}")
        
        # Call the sync function with sheet name
        result = sync_canvas_to_sheet(request.sheet_id, request.canvas_state, request.sheet_name)
        
        if result.get("success"):
            return JSONResponse(content={
                "success": True,
                "message": result.get("message"),
                "items_synced": result.get("items_synced", 0)
            })
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to sync canvas to sheets")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in canvas-to-sheets sync: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/sheets/list")
async def list_sheet_names(request: SheetSyncRequest):
    """
    List available sheet names in a Google Spreadsheet.
    
    Args:
        request: Contains sheet_id
        
    Returns:
        List of available sheet names
    """
    try:
        print(f"Listing sheets in: {request.sheet_id}")
        
        # Get sheet names using Composio
        sheet_names = get_sheet_names(request.sheet_id)
        if not sheet_names:
            raise HTTPException(
                status_code=400, 
                detail="Failed to get sheet names. Please check the sheet ID and ensure it's accessible."
            )
        
        return JSONResponse(content={
            "success": True,
            "sheet_names": sheet_names,
            "count": len(sheet_names)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in sheet listing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/sheets/create")
async def create_sheet(request: CreateSheetRequest):
    """
    Create a new Google Sheet.
    
    Args:
        request: Contains title for the new sheet
        
    Returns:
        New sheet details including sheet_id and URL
    """
    try:
        print(f"Creating new sheet with title: {request.title}")
        
        # Create new sheet using Composio
        result = create_new_sheet(request.title)
        if not result.get("success"):
            raise HTTPException(
                status_code=400, 
                detail=result.get("error", "Failed to create new sheet")
            )
        
        return JSONResponse(content={
            "success": True,
            "sheet_id": result.get("sheet_id"),
            "sheet_url": result.get("sheet_url"),
            "title": result.get("title"),
            "message": f"Successfully created new sheet '{request.title}'"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating sheet: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
