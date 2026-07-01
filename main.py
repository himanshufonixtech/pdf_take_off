import sys
# Main FastAPI application for FenX PDF Takeoff Tool (reloaded to pick up API key change)
import os

# Disable .pyc bytecode caching — prevents stale cache causing old-code bugs on reload
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import json
import uuid
import datetime
import traceback
from typing import List
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

import config
from services.classifier import classify_pdf
import concurrent.futures
from services.extractor import extract_plans_data, extract_nathers_data, extract_basix_data
from services.reconciler import reconcile_takeoff
from services.excel_generator import generate_takeoff_excel

app = FastAPI(title="FenX Window & Door Takeoff Prototype")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No-cache middleware — prevents browser from serving stale JS/CSS/HTML after updates
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/") or path == "/":
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# In-memory + persistent simple JSON database for jobs
JOBS_DB_PATH = os.path.join(config.OUTPUTS_DIR, "jobs.json")
jobs_cache = {}

db_loaded = False

def load_jobs_db():
    global jobs_cache, db_loaded
    if db_loaded:
        return
    if os.path.exists(JOBS_DB_PATH):
        try:
            with open(JOBS_DB_PATH, "r", encoding="utf-8") as f:
                jobs_cache = json.load(f)
                db_loaded = True
        except Exception as e:
            print("Error loading jobs db:", e)
            jobs_cache = {}
    else:
        jobs_cache = {}

def startup_cleanup_jobs():
    global jobs_cache
    # Clean up jobs stuck in "Processing" or "Uploaded" on server restart
    dirty = False
    for j_id, job in jobs_cache.items():
        if job.get("status") in ["Processing", "Uploaded"]:
            job["status"] = "Failed"
            job["stage"] = "Interrupted"
            job["error"] = "Server was restarted or interrupted while this job was processing. Please upload files again."
            dirty = True
    if dirty:
        save_jobs_db()

def save_jobs_db():
    try:
        with open(JOBS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(jobs_cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Error saving jobs db:", e)

# Load jobs on startup
load_jobs_db()
startup_cleanup_jobs()

def process_takeoff_background(job_id: str):
    """
    Background worker that runs the intake, classification,
    extraction, reconciliation, and excel generation steps.
    """
    job = jobs_cache.get(job_id)
    if not job:
        return
        
    try:
        # Step 1: Classification
        job["status"] = "Processing"
        job["stage"] = "Classifying Documents"
        job["progress"] = 15
        save_jobs_db()
        
        plans_paths = []
        nathers_paths = []
        basix_paths = []
        
        # Classify files (optionally in parallel for speed)
        if getattr(config, "PARALLEL_CLASSIFY", True) and len(job.get("files", [])) > 1:
            max_workers = min(getattr(config, "MAX_CLASSIFY_WORKERS", 4), max(1, len(job.get("files", []))))
            futures = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                for file_info in job["files"]:
                    file_path = file_info["path"]
                    fut = ex.submit(classify_pdf, file_path)
                    futures[fut] = file_info

                for fut in concurrent.futures.as_completed(futures):
                    try:
                        classification = fut.result()
                    except Exception as e:
                        classification = {"file_type": "Unknown", "pages": 0, "error": str(e)}
                    file_info = futures[fut]
                    file_info["type"] = classification.get("file_type", "Unknown")
                    file_info["pages"] = classification.get("pages", 0)

                    ftype = file_info["type"]
                    path = file_info["path"]
                    if ftype == "Plans":
                        plans_paths.append(path)
                    elif ftype == "NatHERS":
                        nathers_paths.append(path)
                    elif ftype == "BASIX":
                        basix_paths.append(path)
                    elif ftype == "Hybrid":
                        plans_paths.append(path)
                        nathers_paths.append(path)
                        basix_paths.append(path)
        else:
            for file_info in job["files"]:
                file_path = file_info["path"]
                classification = classify_pdf(file_path)
                file_info["type"] = classification["file_type"]
                file_info["pages"] = classification["pages"]

                if classification["file_type"] == "Plans":
                    plans_paths.append(file_path)
                elif classification["file_type"] == "NatHERS":
                    nathers_paths.append(file_path)
                elif classification["file_type"] == "BASIX":
                    basix_paths.append(file_path)
                elif classification["file_type"] == "Hybrid":
                    plans_paths.append(file_path)
                    nathers_paths.append(file_path)
                    basix_paths.append(file_path)
                
        # Step 2: Extraction (parallel, bounded)
        job["stage"] = "Extracting Data (Plans & Certificates)"
        job["progress"] = 40
        save_jobs_db()

        plans_windows = []
        nathers_windows = []
        basix_data = {"commitments": [], "cert_number": None, "total_glazing_area": None}

        # Build list of file entries to extract from (use updated types on job['files'])
        file_entries = list(job.get("files", []))

        # FIX #3b: Extract NatHERS first (sequentially) to get known tags,
        # then pass them to plans extractor to suppress phantom openings.
        nathers_tags_set = set()
        for fe in file_entries:
            if fe.get("type") in ("NatHERS", "Hybrid"):
                try:
                    nathers_rows = extract_nathers_data(fe["path"])
                    for row in nathers_rows:
                        t = str(row.get("tag", "")).strip().upper()
                        if t:
                            nathers_tags_set.add(t)
                    nathers_windows.extend(nathers_rows)
                    fe["_nathers_done"] = True
                except Exception as e:
                    print(f"NatHERS pre-extract error for {fe['path']}: {e}")

        def extract_for_file(file_info):
            path = file_info.get("path")
            ftype = file_info.get("type", "Unknown")
            result = {"path": path, "type": ftype, "extracted": None}
            try:
                if ftype == "Plans":
                    # Pass NatHERS tags so plans extractor can suppress phantoms
                    result["extracted"] = extract_plans_data(path, nathers_tags=nathers_tags_set)
                elif ftype == "NatHERS":
                    if file_info.get("_nathers_done"):
                        result["extracted"] = []  # already extracted above
                    else:
                        result["extracted"] = extract_nathers_data(path)
                elif ftype == "BASIX":
                    result["extracted"] = extract_basix_data(path)
                elif ftype == "Hybrid":
                    res = {}
                    res["plans"] = extract_plans_data(path, nathers_tags=nathers_tags_set)
                    if file_info.get("_nathers_done"):
                        res["nathers"] = []  # already done
                    else:
                        res["nathers"] = extract_nathers_data(path)
                    res["basix"] = extract_basix_data(path)
                    result["extracted"] = res
                else:
                    result["extracted"] = None
            except Exception as e:
                print(f"Error extracting from {path}: {e}")
                traceback.print_exc()
                result["error"] = str(e)
            return result

        # Decide worker count
        if getattr(config, "PARALLEL_EXTRACTION", True):
            max_workers = min(getattr(config, "MAX_EXTRACTION_WORKERS", 4), max(1, len(file_entries)))
        else:
            max_workers = 1

        # Run extractions in parallel (bounded) and merge results
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(extract_for_file, fe): fe for fe in file_entries}
            completed = 0
            total = len(futures)
            for fut in concurrent.futures.as_completed(futures):
                completed += 1
                fe = futures[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    print(f"Extraction task raised: {e}")
                    res = {"path": fe.get("path"), "type": fe.get("type"), "extracted": None, "error": str(e)}

                if res.get("error"):
                    raise RuntimeError(f"Extraction failed for {os.path.basename(res['path'])}: {res['error']}")

                # Merge
                rtype = res.get("type")
                extracted = res.get("extracted")
                if rtype == "Plans" and extracted:
                    plans_windows.extend(extracted if isinstance(extracted, list) else [])
                elif rtype == "NatHERS" and extracted:
                    nathers_windows.extend(extracted if isinstance(extracted, list) else [])
                elif rtype == "BASIX" and extracted:
                    if isinstance(extracted, dict):
                        if extracted.get("cert_number"):
                            basix_data["cert_number"] = extracted["cert_number"]
                        if extracted.get("total_glazing_area"):
                            basix_data["total_glazing_area"] = extracted["total_glazing_area"]
                        if extracted.get("commitments"):
                            basix_data["commitments"].extend(extracted.get("commitments", []))
                elif rtype == "Hybrid" and extracted:
                    plans_windows.extend(extracted.get("plans", []) if extracted.get("plans") else [])
                    nathers_windows.extend(extracted.get("nathers", []) if extracted.get("nathers") else [])
                    if extracted.get("basix"):
                        b = extracted.get("basix")
                        if b.get("cert_number"):
                            basix_data["cert_number"] = b["cert_number"]
                        if b.get("total_glazing_area"):
                            basix_data["total_glazing_area"] = b["total_glazing_area"]
                        if b.get("commitments"):
                            basix_data["commitments"].extend(b.get("commitments", []))

                # Update progress in the job so UI sees movement
                try:
                    job_progress_base = 40
                    # progress moves from 40 -> 70 during extraction
                    job["progress"] = int(job_progress_base + (completed / total) * 30)
                    save_jobs_db()
                except Exception:
                    pass

        # Handle plan-only scenario
        if plans_windows and not nathers_windows:
             # Just map plans into a temporary format that looks like it reconciled
             pass
             
        # Step 3: Reconciliation
        job["stage"] = "Reconciling & Cross-checking"
        job["progress"] = 75
        save_jobs_db()
        
        recon_results = reconcile_takeoff(plans_windows, nathers_windows, basix_data)
        
        job["takeoff_rows"]      = recon_results["rows"]
        job["flags"]             = recon_results["flags"]
        job["overall_confidence"]= recon_results["overall_confidence"]
        job["is_rejected"]       = recon_results["is_rejected"]
        job["rejection_reason"]  = recon_results["rejection_reason"]
        job["review_required"]   = recon_results.get("review_required", False)
        job["review_reason"]     = recon_results.get("review_reason", "")
        job["plan_glazing_area"] = recon_results.get("plan_glazing_area", 0.0)
        job["cert_glazing_area"] = recon_results.get("cert_glazing_area")
        
        # Step 4: Excel Generation
        if recon_results["is_rejected"]:
            job["status"] = "Rejected"
            job["stage"] = "Rejected"
            job["progress"] = 100
        else:
            job["stage"] = "Generating Excel Output"
            job["progress"] = 90
            save_jobs_db()
            
            safe_project = job['project_name'].replace(' ', '_').replace('/', '-')
            excel_filename = f"{job_id}_{safe_project}.xlsx"
            excel_path = os.path.join(config.OUTPUTS_DIR, excel_filename)
            
            generate_takeoff_excel(recon_results, excel_path, job["project_name"], job["project_type"])
            
            job["excel_url"] = f"/api/download/{excel_filename}"
            # FIX #8: Show REVIEW REQUIRED as a distinct status
            if recon_results.get("review_required"):
                job["status"] = "Review Required"
            else:
                job["status"] = "Completed"
            job["stage"] = job["status"]
            job["progress"] = 100
            
    except Exception as e:
        print(f"Background process error for job {job_id}: {e}")
        traceback.print_exc()
        job["status"] = "Failed"
        job["stage"] = "Failed"
        job["progress"] = 100
        job["error"] = str(e)
        
    save_jobs_db()

@app.post("/api/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    project_name: str = Form(None),
    project_type: str = Form("Single Dwelling"),
    files: List[UploadFile] = File(...)
):
    # Auto-generate Project Name if not provided
    today_str = datetime.date.today().strftime("%Y%m%d")
    load_jobs_db()
    job_index = len(jobs_cache) + 1
    job_id = f"FNX-{today_str}-{job_index:03d}"
    
    if not project_name:
        project_name = f"Takeoff Project {job_index:02d}"
        
    saved_files = []
    for f in files:
        # Save file to uploads folder
        safe_filename = f"{job_id}_{secure_filename(f.filename)}"
        file_path = os.path.join(config.UPLOADS_DIR, safe_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await f.read())
            
        saved_files.append({
            "filename": f.filename,
            "path": file_path,
            "type": "Unknown",
            "pages": 0
        })
        
    job_state = {
        "job_id": job_id,
        "project_name": project_name,
        "project_type": project_type,
        "status": "Uploaded",
        "progress": 0,
        "stage": "Queueing",
        "files": saved_files,
        "takeoff_rows": [],
        "flags": [],
        "overall_confidence": 0.0,
        "is_rejected": False,
        "rejection_reason": "",
        "excel_url": None,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    jobs_cache[job_id] = job_state
    save_jobs_db()
    
    # Start task in background
    background_tasks.add_task(process_takeoff_background, job_id)
    
    return job_state
@app.get("/api/jobs")
async def get_all_jobs():
    load_jobs_db()
    # Return sorted by timestamp descending
    sorted_jobs = sorted(jobs_cache.values(), key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Strip paths to keep payloads clean
    clean_jobs = []
    for job in sorted_jobs:
        clean_job = dict(job)
        clean_job["files"] = [{"filename": f["filename"], "type": f.get("type", "Unknown"), "pages": f.get("pages", 0)} for f in job["files"]]
        clean_jobs.append(clean_job)
        
    return clean_jobs

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    load_jobs_db()
    job = jobs_cache.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    clean_job = dict(job)
    clean_job["files"] = [{"filename": f["filename"], "type": f.get("type", "Unknown"), "pages": f.get("pages", 0)} for f in job["files"]]
    return clean_job

@app.post("/api/job/{job_id}/reprocess")
async def reprocess_job(job_id: str, background_tasks: BackgroundTasks):
    """Reset a failed/rejected job and reprocess it with the current API key and model."""
    load_jobs_db()
    job = jobs_cache.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") == "Processing":
        raise HTTPException(status_code=400, detail="Job is already processing")

    # Verify all files still exist
    missing = [f["path"] for f in job.get("files", []) if not os.path.exists(f["path"])]
    if missing:
        raise HTTPException(status_code=400, detail=f"Upload files missing, please re-upload: {missing}")

    # Reset state
    job["status"] = "Uploaded"
    job["stage"] = "Queueing"
    job["progress"] = 0
    job["takeoff_rows"] = []
    job["flags"] = []
    job["overall_confidence"] = 0.0
    job["is_rejected"] = False
    job["rejection_reason"] = ""
    job["excel_url"] = None
    job.pop("error", None)
    
    # Reset file-specific processing state
    for f in job.get("files", []):
        f.pop("_nathers_done", None)
        
    save_jobs_db()

    background_tasks.add_task(process_takeoff_background, job_id)
    return {"message": f"Job {job_id} queued for reprocessing", "job_id": job_id}


@app.get("/api/download/{filename}")
async def download_excel_file(filename: str):
    file_path = os.path.join(config.OUTPUTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Excel file not found")
    return FileResponse(file_path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def secure_filename(filename: str) -> str:
    """Basic secure filename sanitizer."""
    return "".join(c for c in filename if c.isalnum() or c in "._- ")

# Serve HTML index at root
@app.get("/")
async def serve_index():
    index_path = os.path.join(config.STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"message": "Frontend not found"})

# Mount Static Files
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
