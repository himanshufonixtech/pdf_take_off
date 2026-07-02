// FenX Application Logic - Takeoff Automation

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const browseBtn = document.getElementById("browse-btn");
    const selectedFilesList = document.getElementById("selected-files-list");
    const uploadForm = document.getElementById("upload-form");
    const processBtn = document.getElementById("process-btn");
    const refreshJobsBtn = document.getElementById("refresh-jobs-btn");
    const searchJobsInput = document.getElementById("search-jobs");
    const recentJobsList = document.getElementById("recent-jobs-list");
    
    // Modal Elements
    const uploadModal = document.getElementById("upload-modal");
    const openUploadModalBtn = document.getElementById("open-upload-modal-btn");
    const closeModalBtn = document.getElementById("close-modal-btn");
    
    if (openUploadModalBtn) {
        openUploadModalBtn.addEventListener("click", () => {
            uploadModal.style.display = "flex";
        });
    }
    
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => {
            uploadModal.style.display = "none";
        });
    }
    
    // Progress UI Elements
    const progressCard = document.getElementById("progress-card");
    const activeJobIdLabel = document.getElementById("active-job-id");
    const progressFill = document.getElementById("progress-fill");
    const progressStage = document.getElementById("progress-stage");
    const progressPercent = document.getElementById("progress-percent");
    const stepUpload = document.getElementById("step-upload");
    const stepClassify = document.getElementById("step-classify");
    const stepExtract = document.getElementById("step-extract");
    const stepReconcile = document.getElementById("step-reconcile");
    
    // Main Panel Progress UI Elements
    const processingJobState = document.getElementById("processing-job-state");
    const processingProjectName = document.getElementById("processing-project-name");
    const processingJobId = document.getElementById("processing-job-id");
    const mainProgressFill = document.getElementById("main-progress-fill");
    const mainProgressStage = document.getElementById("main-progress-stage");
    const mainProgressPercent = document.getElementById("main-progress-percent");
    const mainStepUpload = document.getElementById("main-step-upload");
    const mainStepClassify = document.getElementById("main-step-classify");
    const mainStepExtract = document.getElementById("main-step-extract");
    const mainStepReconcile = document.getElementById("main-step-reconcile");
    
    // Results Preview UI Elements
    const noActiveJobState = document.getElementById("no-active-job");
    const activeJobResults = document.getElementById("active-job-results");
    const resultProjectName = document.getElementById("result-project-name");
    const resultJobId = document.getElementById("result-job-id");
    const resultProjectType = document.getElementById("result-project-type");
    const resultTimestamp = document.getElementById("result-timestamp");
    const downloadExcelBtn = document.getElementById("download-excel-btn");
    const metricWindowsFound = document.getElementById("metric-windows-found");
    const metricDoorsFound = document.getElementById("metric-doors-found");
    const metricPagesProcessed = document.getElementById("metric-pages-processed");
    const takeoffFilter = document.getElementById("takeoff-filter");
    const takeoffRecordsCount = document.getElementById("takeoff-records-count");
    const metricTotalFlags = document.getElementById("metric-total-flags");
    
    const rejectionBanner = document.getElementById("rejection-banner");
    const rejectionMsg = document.getElementById("rejection-msg");
    const takeoffTableBody = document.getElementById("takeoff-table-body");
    const consistencyFlagsTableBody = document.getElementById("consistency-flags-table-body");
    const flagsTabBadge = document.getElementById("flags-tab-badge");
    const tabBtnFlags = document.getElementById("tab-btn-flags");
    const tabBtnJson = document.getElementById("tab-btn-json");
    
    // Detected Docs Elements
    const docPlans = document.getElementById("doc-plans");
    const docNathers = document.getElementById("doc-nathers");
    const docBasix = document.getElementById("doc-basix");
    const docColour = document.getElementById("doc-colour");
    const rawJsonContent = document.getElementById("raw-json-content");
    
    // App State Variables
    let selectedFiles = [];
    let pollingInterval = null;
    let currentActiveJobId = null;

    // --- Core Startup Functions ---
    fetchRecentJobs(true);
    
    // --- Event Listeners: File Picker Setup ---
    browseBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", handleFileSelection);
    
    // Drag & Drop events
    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        }, false);
    });
    
    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
        }, false);
    });
    
    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = Array.from(dt.files).filter(f => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
        if (files.length > 0) {
            addSelectedFiles(files);
        }
    });

    function handleFileSelection(e) {
        const files = Array.from(e.target.files);
        addSelectedFiles(files);
        fileInput.value = ""; // Clear file input value to allow re-selecting the same files if needed
    }

    function addSelectedFiles(files) {
        files.forEach(file => {
            // Check for duplicates
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        });
        updateSelectedFilesUI();
    }

    function removeSelectedFile(index) {
        selectedFiles.splice(index, 1);
        updateSelectedFilesUI();
    }

    function updateSelectedFilesUI() {
        const ul = selectedFilesList.querySelector(".file-list");
        ul.innerHTML = "";
        
        if (selectedFiles.length === 0) {
            selectedFilesList.style.display = "none";
            processBtn.disabled = true;
            return;
        }
        
        selectedFilesList.style.display = "block";
        processBtn.disabled = false;
        
        selectedFiles.forEach((file, idx) => {
            const li = document.createElement("li");
            
            const nameSpan = document.createElement("span");
            nameSpan.className = "filename";
            nameSpan.innerHTML = `<i class="fa-regular fa-file-pdf"></i> ${file.name}`;
            
            const sizeSpan = document.createElement("span");
            sizeSpan.style.color = "var(--text-muted)";
            sizeSpan.innerText = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
            
            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.innerHTML = '<i class="fa-solid fa-trash-can"></i>';
            removeBtn.addEventListener("click", () => removeSelectedFile(idx));
            
            const rightDiv = document.createElement("div");
            rightDiv.style.display = "flex";
            rightDiv.style.alignItems = "center";
            rightDiv.style.gap = "8px";
            rightDiv.appendChild(sizeSpan);
            rightDiv.appendChild(removeBtn);
            
            li.appendChild(nameSpan);
            li.appendChild(rightDiv);
            ul.appendChild(li);
        });
    }

    // --- Form Submission: Upload & Intake ---
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (selectedFiles.length === 0) return;
        
        const formData = new FormData();
        const projNameVal = document.getElementById("project-name").value;
        const projTypeVal = document.getElementById("project-type").value;
        
        if (projNameVal) {
            formData.append("project_name", projNameVal);
        }
        formData.append("project_type", projTypeVal);
        
        selectedFiles.forEach(file => {
            formData.append("files", file);
        });
        
        // Lock controls
        processBtn.disabled = true;
        processBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading...';
        
        try {
            const response = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed with status ${response.status}`);
            }
            
            const job = await response.json();
            
            // Clear form and selections
            selectedFiles = [];
            updateSelectedFilesUI();
            document.getElementById("project-name").value = "";
            processBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Automated Takeoff';
            
            // Start progress tracking
            if (uploadModal) uploadModal.style.display = "none";
            startJobTracking(job.job_id);
            fetchRecentJobs();
            
        } catch (error) {
            console.error("Upload Error:", error);
            alert(`Error launching takeoff: ${error.message}`);
            processBtn.disabled = false;
            processBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Automated Takeoff';
        }
    });

    // --- Polling & Background Processing Progress UI ---
    function startJobTracking(jobId) {
        if (pollingInterval) clearInterval(pollingInterval);
        
        currentActiveJobId = jobId;
        activeJobIdLabel.innerText = jobId;
        progressCard.style.display = "block";
        
        // Hide previous preview during processing, show processing panel
        noActiveJobState.style.display = "none";
        if (processingJobState) processingJobState.style.display = "flex";
        activeJobResults.style.display = "none";
        
        // Find project name from the sidebar if available
        let projectName = "Takeoff Project";
        const sidebarCard = recentJobsList.querySelector(`.job-card[data-job-id="${jobId}"]`);
        if (sidebarCard) {
            const titleEl = sidebarCard.querySelector(".job-title");
            if (titleEl) projectName = titleEl.innerText;
        }
        if (processingProjectName) processingProjectName.innerText = projectName;
        if (processingJobId) processingJobId.innerText = jobId;
        
        // Initialize bullets status
        resetProgressSteps();
        stepUpload.classList.add("done");
        stepClassify.classList.add("active");
        
        if (mainStepUpload) mainStepUpload.classList.add("done");
        if (mainStepClassify) mainStepClassify.classList.add("active");
        
        updateProgressUI(jobId, 10, "Uploading files...");
        
        pollingInterval = setInterval(() => pollJobStatus(jobId), 2000);
    }

    async function pollJobStatus(jobId) {
        try {
            const response = await fetch(`/api/job/${jobId}`);
            if (!response.ok) return;
            
            const job = await response.json();
            
            const status = job.status;
            const progress = job.progress || 0;
            const stage = job.stage || "Processing";
            
            updateProgressUI(jobId, progress, stage);
            
            // Sync bullets
            if (progress >= 15) {
                stepClassify.classList.remove("active");
                stepClassify.classList.add("done");
                stepExtract.classList.add("active");
                
                if (mainStepClassify) {
                    mainStepClassify.classList.remove("active");
                    mainStepClassify.classList.add("done");
                }
                if (mainStepExtract) mainStepExtract.classList.add("active");
            }
            if (progress >= 40) {
                stepExtract.classList.remove("active");
                stepExtract.classList.add("done");
                stepReconcile.classList.add("active");
                
                if (mainStepExtract) {
                    mainStepExtract.classList.remove("active");
                    mainStepExtract.classList.add("done");
                }
                if (mainStepReconcile) mainStepReconcile.classList.add("active");
            }
            if (progress >= 75) {
                stepReconcile.classList.remove("active");
                stepReconcile.classList.add("done");
                
                if (mainStepReconcile) {
                    mainStepReconcile.classList.remove("active");
                    mainStepReconcile.classList.add("done");
                }
            }
            
            if (status === "Completed" || status === "Review Required" || status === "Rejected" || status === "Failed") {
                clearInterval(pollingInterval);
                pollingInterval = null;
                progressCard.style.display = "none";
                if (processingJobState) processingJobState.style.display = "none";
                
                // Fetch recent jobs to sync sidebar status
                fetchRecentJobs();
                
                // Show results card
                displayJobResults(job);
            }
            
        } catch (error) {
            console.error("Polling Error:", error);
        }
    }

    function resetProgressSteps() {
        [stepUpload, stepClassify, stepExtract, stepReconcile,
         mainStepUpload, mainStepClassify, mainStepExtract, mainStepReconcile].forEach(el => {
            if (el) el.className = "step-item";
        });
    }

    function updateProgressUI(jobId, percent, stageText) {
        progressFill.style.width = `${percent}%`;
        progressPercent.innerText = `${percent}%`;
        progressStage.innerText = stageText;
        
        if (mainProgressFill) mainProgressFill.style.width = `${percent}%`;
        if (mainProgressPercent) mainProgressPercent.innerText = `${percent}%`;
        if (mainProgressStage) mainProgressStage.innerText = stageText;
        
        // Also update the sidebar card for this job if it exists!
        const activeCard = recentJobsList.querySelector(`.job-card[data-job-id="${jobId}"]`);
        if (activeCard) {
            const barFill = activeCard.querySelector(".sidebar-progress-bar-fill");
            const stageSpan = activeCard.querySelector(".sidebar-progress-stage");
            const pctSpan = activeCard.querySelector(".sidebar-progress-percent");
            if (barFill) barFill.style.width = `${percent}%`;
            if (stageSpan) stageSpan.innerText = stageText;
            if (pctSpan) pctSpan.innerText = `${percent}%`;
        }
    }

    // --- Fetching & Rendering Recent Jobs Sidebar ---
    async function fetchRecentJobs(autoTrack = false) {
        try {
            const response = await fetch("/api/jobs");
            if (!response.ok) throw new Error("Could not fetch jobs list");
            
            const jobs = await response.json();
            // Sidebar mein Completed aur Review Required dono dikhao (dono finished states hain)
            const completedJobs = jobs.filter(j => j.status === "Completed" || j.status === "Review Required");
            renderRecentJobs(completedJobs);
            
            if (autoTrack) {
                const activeJob = jobs.find(j => j.status === "Processing" || j.status === "Uploaded");
                if (activeJob && !pollingInterval) {
                    startJobTracking(activeJob.job_id);
                }
            }
        } catch (error) {
            console.error("Sidebar Refresh Error:", error);
            recentJobsList.innerHTML = '<div class="jobs-empty-state"><i class="fa-solid fa-circle-exclamation"></i> Error loading jobs</div>';
        }
    }

    function renderRecentJobs(jobs) {
        recentJobsList.innerHTML = "";
        
        if (jobs.length === 0) {
            recentJobsList.innerHTML = '<div class="jobs-empty-state">No takeoffs processed yet.</div>';
            return;
        }
        
        const filterVal = searchJobsInput.value.toLowerCase().trim();
        
        jobs.forEach(job => {
            // Apply sidebar search filter
            if (filterVal && !job.project_name.toLowerCase().includes(filterVal) && !job.job_id.toLowerCase().includes(filterVal)) {
                return;
            }
            
            const card = document.createElement("div");
            card.className = "job-card";
            card.setAttribute("data-job-id", job.job_id);
            if (currentActiveJobId === job.job_id) {
                card.classList.add("active");
            }
            
            // Add status-specific class for left border color
            // Sanitize status to a valid CSS class (replace spaces with dashes, lowercase)
            const statusClass = job.status.toLowerCase().replace(/\s+/g, '-');
            card.classList.add(`status-${statusClass}`);
            
            // Format timestamp
            const date = new Date(job.timestamp);
            const formattedDate = date.toLocaleDateString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
            
            // Status icon mapping
            const statusIcons = {
                'completed': '<i class="fa-solid fa-circle-check"></i>',
                'review-required': '<i class="fa-solid fa-circle-exclamation"></i>',
                'processing': '<i class="fa-solid fa-spinner fa-spin"></i>',
                'uploaded': '<i class="fa-solid fa-cloud-arrow-up"></i>',
                'failed': '<i class="fa-solid fa-circle-xmark"></i>',
                'rejected': '<i class="fa-solid fa-triangle-exclamation"></i>'
            };
            const statusIcon = statusIcons[statusClass] || '';
            
            // File count info
            const fileCount = job.files ? job.files.length : 0;
            const totalPages = job.files ? job.files.reduce((sum, f) => sum + (f.pages || 0), 0) : 0;
            
            let progressHtml = "";
            if (job.status === "Processing" || job.status === "Uploaded") {
                const pct = job.progress || 0;
                progressHtml = `
                    <div class="sidebar-job-progress">
                        <div class="progress-bar-bg" style="height: 5px; margin-bottom: 0; border-radius: 4px;">
                            <div class="sidebar-progress-bar-fill progress-bar-fill" style="width: ${pct}%; border-radius: 4px;"></div>
                        </div>
                        <div class="sidebar-progress-meta">
                            <span class="sidebar-progress-stage">${job.stage || 'Queueing...'}</span>
                            <span class="sidebar-progress-percent">${pct}%</span>
                        </div>
                    </div>
                `;
            }
            
            // Info row: file count + pages (for completed jobs)
            let infoHtml = "";
            if (job.status === "Completed" || job.status === "Review Required" || job.status === "Rejected" || job.status === "Failed") {
                const pagesText = totalPages > 0 ? ` · ${totalPages} pg` : "";
                infoHtml = `<div style="font-size: 10px; color: var(--text-muted); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                    <i class="fa-regular fa-file-pdf" style="font-size: 9px;"></i> ${fileCount} file${fileCount !== 1 ? 's' : ''}${pagesText}
                </div>`;
            }
            
            card.innerHTML = `
                <div class="job-card-header">
                    <span class="job-title" title="${job.project_name}">${job.project_name}</span>
                    <span class="job-id">${job.job_id}</span>
                </div>
                <div class="job-card-meta">
                    <span class="job-date"><i class="fa-regular fa-clock"></i> ${formattedDate}</span>
                    <span class="job-status-badge ${statusClass}">${statusIcon} ${job.status}</span>
                </div>
                ${progressHtml}
                ${infoHtml}
            `;
            
            card.addEventListener("click", () => {
                // If clicked job is processing, show progress card, else load preview results
                if (job.status === "Processing" || job.status === "Uploaded") {
                    startJobTracking(job.job_id);
                } else {
                    if (pollingInterval) {
                        clearInterval(pollingInterval);
                        pollingInterval = null;
                        progressCard.style.display = "none";
                    }
                    if (processingJobState) processingJobState.style.display = "none";
                    currentActiveJobId = job.job_id;
                    highlightActiveSidebarCard(job.job_id);
                    displayJobResults(job);
                }
            });
            
            recentJobsList.appendChild(card);
        });
    }

    function highlightActiveSidebarCard(jobId) {
        const cards = recentJobsList.querySelectorAll(".job-card");
        cards.forEach(card => {
            const idText = card.querySelector(".job-id").innerText;
            if (idText === jobId) {
                card.classList.add("active");
            } else {
                card.classList.remove("active");
            }
        });
    }

    // --- Rendering Job Results & Preview Panels ---
    function displayJobResults(job) {
        noActiveJobState.style.display = "none";
        activeJobResults.style.display = "flex";
        
        resultProjectName.innerText = job.project_name;
        resultJobId.innerHTML = `<i class="fa-solid fa-hashtag"></i> ${job.job_id}`;
        resultProjectType.innerHTML = `<i class="fa-solid fa-building"></i> ${job.project_type}`;
        
        const date = new Date(job.timestamp);
        resultTimestamp.innerHTML = `<i class="fa-solid fa-clock"></i> ${date.toLocaleDateString()}`;
        
        // Excel download configuration
        if (job.excel_url && (job.status === "Completed" || job.status === "Review Required" || job.status === "Rejected")) {
            downloadExcelBtn.href = job.excel_url;
            downloadExcelBtn.download = job.excel_url.split('/').pop() || "Takeoff_Results.xlsx";
            downloadExcelBtn.classList.remove("disabled");
            downloadExcelBtn.style.pointerEvents = "auto";
            downloadExcelBtn.style.opacity = "1";
        } else {
            downloadExcelBtn.removeAttribute("href");
            downloadExcelBtn.style.pointerEvents = "none";
            downloadExcelBtn.style.opacity = "0.5";
        }
        
        // Populate Detected Documents
        const hasType = (typeStr) => job.files && job.files.some(f => f.type && f.type.includes(typeStr));
        const setDocStatus = (el, exists, label) => {
            if (exists) {
                el.style.color = "var(--color-success)";
                el.innerHTML = '<i class="fa-solid fa-circle-check"></i> ' + label;
            } else {
                el.style.color = "var(--text-muted)";
                el.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> ' + label;
            }
        };
        
        if (docPlans) setDocStatus(docPlans, hasType("Plans") || hasType("Hybrid"), "Plans");
        if (docNathers) setDocStatus(docNathers, hasType("NatHERS") || hasType("Hybrid"), "NatHERS");
        if (docBasix) setDocStatus(docBasix, hasType("BASIX") || hasType("Hybrid"), "BASIX");
        if (docColour) setDocStatus(docColour, hasType("Colour Schedule"), "Colour Schedule");
        
        // Populate Raw JSON
        if (rawJsonContent) {
            rawJsonContent.innerText = JSON.stringify(job, null, 2);
        }
        
        // Metrics Summary
        let windows = 0;
        let doors = 0;
        if (job.takeoff_rows) {
            job.takeoff_rows.forEach(r => {
                const typ = (r.opening_type || r.type || "").toLowerCase();
                if (typ.includes("door") || typ.includes("louvre") || typ.includes("bifold") || typ.includes("stacker")) {
                     doors += parseInt(r.quantity || 1);
                } else {
                     windows += parseInt(r.quantity || 1);
                }
            });
        }
        
        let pages = 0;
        if (job.files) {
            pages = job.files.reduce((acc, f) => acc + (f.pages || 0), 0);
        }
        
        if (metricWindowsFound) metricWindowsFound.innerText = windows;
        if (metricDoorsFound) metricDoorsFound.innerText = doors;
        if (metricPagesProcessed) metricPagesProcessed.innerText = pages;
        if (metricTotalFlags) metricTotalFlags.innerText = job.flags ? job.flags.length : 0;
        
        // Rejection and Failure display
        if (job.status === "Rejected") {
            rejectionBanner.style.display = "flex";
            rejectionBanner.querySelector("h4").innerText = "Takeoff Rejected by Quality Controls";
            rejectionMsg.innerText = job.rejection_reason || "Low data confidence score detected.";
        } else if (job.status === "Failed") {
            rejectionBanner.style.display = "flex";
            rejectionBanner.querySelector("h4").innerText = "Takeoff Processing Failed / Interrupted";
            rejectionMsg.innerText = job.error || "An unexpected error occurred during processing.";
        } else {
            rejectionBanner.style.display = "none";
        }
        
        // Render Tables & Tabs Content
        renderTakeoffTable(job.takeoff_rows || []);
        renderConsistencyReport(job.flags || []);
    }

    function renderTakeoffTable(rows) {
        takeoffTableBody.innerHTML = "";
        
        if (rows.length === 0) {
            takeoffTableBody.innerHTML = '<tr><td colspan="12" class="text-center" style="padding: 30px; text-align: center; color: var(--text-muted);">No windows/doors detected in this takeoff.</td></tr>';
            return;
        }
        
        rows.forEach(r => {
            const tr = document.createElement("tr");
            
            // Compute confidence - support both field names from backend
            const confidence = r.confidence_score ?? r.confidence ?? null;
            
            // Set row color class based on opening type and confidence
            if (confidence !== null && confidence < 70) {
                tr.className = "row-low-confidence";
            } else {
                const optType = r.opening_type;
                if (optType === "Door") {
                    tr.className = "row-door";
                } else if (optType === "Bi-fold/Stacker Door") {
                    tr.className = "row-bifold";
                } else if (optType === "Louvre") {
                    tr.className = "row-louvre";
                } else {
                    tr.className = "row-window";
                }
            }
            
            // Support both backend field naming conventions
            const tag = r.window_or_door_number || r.tag || "N/A";
            const width = r.width_mm || r.width || "—";
            const height = r.height_mm || r.height || "—";
            const glazing = r.glazing_type || r.glazing || "—";
            const frame = r.frame_material || r.frame || "—";
            const confDisplay = confidence !== null ? confidence.toFixed(0) + '%' : "—";
            
            tr.innerHTML = `
                <td>${r.location || "Unknown"}</td>
                <td><strong>${tag}</strong></td>
                <td>${r.opening_type || r.type || "—"}</td>
                <td class="text-right">${width}</td>
                <td class="text-right">${height}</td>
                <td>${r.orientation || "—"}</td>
                <td title="${glazing}">${glazing}</td>
                <td>${r.u_value || "—"}</td>
                <td>${r.shgc || "—"}</td>
                <td>${frame}</td>
                <td class="text-right"><strong>${r.quantity || 1}</strong></td>
                <td>${confDisplay}</td>
            `;
            takeoffTableBody.appendChild(tr);
        });
        
        if (takeoffRecordsCount) {
            takeoffRecordsCount.innerText = rows.length;
        }
    }

    function renderConsistencyReport(flags) {
        if (!consistencyFlagsTableBody) return;
        consistencyFlagsTableBody.innerHTML = "";
        if (flagsTabBadge) flagsTabBadge.innerText = flags.length;
        
        if (flags.length === 0) {
            consistencyFlagsTableBody.innerHTML = `<tr><td colspan="5" class="text-center" style="padding: 30px; text-align: center; color: var(--text-muted);"><i class="fa-solid fa-circle-check" style="color: var(--color-success);"></i> Perfect Consistency! No mismatches found.</td></tr>`;
            return;
        }
        
        flags.forEach(flag => {
            const tr = document.createElement("tr");
            const typeStr = (flag.flag_type || flag.category || "").toLowerCase();
            const isDanger = typeStr.includes("missing") || typeStr.includes("low_confidence") || typeStr.includes("aggregate");
            
            if (isDanger) {
                tr.classList.add("row-low-confidence");
            }
            
            const severityColor = (flag.severity === "High") ? "var(--color-danger)" : (flag.severity === "Medium" ? "var(--color-warning)" : "#1e88e5");
            
            tr.innerHTML = `
                <td><strong>${flag.flag_type || flag.category || "Unknown"}</strong></td>
                <td>${flag.opening_id || flag.item_ref || "N/A"}</td>
                <td>${flag.description || "—"}</td>
                <td><span class="badge" style="background-color: ${severityColor}; color: white;">${flag.severity || "Medium"}</span></td>
                <td>System Analysis</td>
            `;
            consistencyFlagsTableBody.appendChild(tr);
        });
    }

    // --- Tab-Switching Logic ---
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            // Remove active class from all buttons and panels
            tabButtons.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
            
            // Add active class
            btn.classList.add("active");
            const targetTab = btn.getAttribute("data-tab");
            document.getElementById(targetTab).classList.add("active");
        });
    });

    // --- Sidebar Search & Control Handlers ---
    searchJobsInput.addEventListener("input", () => {
        fetchRecentJobs();
    });
    
    refreshJobsBtn.addEventListener("click", () => {
        fetchRecentJobs();
    });

    // --- Takeoff Table Filtering Logic ---
    if (takeoffFilter) {
        takeoffFilter.addEventListener("input", (e) => {
            const term = e.target.value.toLowerCase();
            const rows = takeoffTableBody.querySelectorAll("tr");
            let visibleCount = 0;
            
            rows.forEach(row => {
                if (row.innerText.toLowerCase().includes(term)) {
                    row.style.display = "";
                    visibleCount++;
                } else {
                    row.style.display = "none";
                }
            });
            
            if (takeoffRecordsCount) {
                takeoffRecordsCount.innerText = visibleCount;
            }
        });
    }
});
