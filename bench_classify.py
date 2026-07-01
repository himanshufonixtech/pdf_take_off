import time
import sys
from services.classifier import classify_pdf
import concurrent.futures

# Files to test - use provided POC and repeat to simulate multiple uploads
base = r"D:\fonix\pdftakeoff\docs\req_docs\POC_Brief_PDF_Takeoff_Tool.pdf"
files = [base]
# If user has multiple files in uploads, use those too
import glob, os
uploads = glob.glob(os.path.join('uploads', '*.pdf'))
for u in uploads:
    if u not in files:
        files.append(u)
# Ensure we have at least 5 entries by repeating the POC
while len(files) < 5:
    files.append(base)

print('Testing files:')
for f in files:
    print(' -', f)

# Sequential timing
seq_times = []
start = time.time()
for f in files:
    t0 = time.time()
    r = classify_pdf(f)
    seq_times.append(time.time()-t0)
    print(f'Classified {os.path.basename(f)} -> {r.get("file_type")} in {seq_times[-1]:.3f}s')
seq_total = time.time() - start

# Parallel timing using thread pool
par_times = []
start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    futs = {ex.submit(classify_pdf, f): f for f in files}
    for fut in concurrent.futures.as_completed(futs):
        f = futs[fut]
        t0 = time.time()
        try:
            r = fut.result()
        except Exception as e:
            r = {'file_type':'Unknown','error':str(e)}
        elapsed = time.time()-t0
        par_times.append(elapsed)
        print(f'Parallel result for {os.path.basename(f)} -> {r.get("file_type")} (worker callback took {elapsed:.3f}s)')
par_total = time.time() - start

print('\nSummary:')
print('Sequential avg per-file: {:.3f}s total {:.3f}s'.format(sum(seq_times)/len(seq_times), seq_total))
print('Parallel wall time: {:.3f}s ({} files)'.format(par_total, len(files)))
print('Per-file durations (seq):', ['{:.3f}s'.format(t) for t in seq_times])
print('Per-file callback durations (par):', ['{:.3f}s'.format(t) for t in par_times])
