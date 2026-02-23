import os
import uuid
import tempfile
import threading
import time
import json

from flask import Flask, request, jsonify, Response, send_file, render_template

from core.ocr import extract_text_from_file
from core.parser import parse_receipt
from core.exporter import write_to_excel_headless

app = Flask(__name__)

# session_id -> {"dir": str, "excel_path": str|None, "created_at": float}
_sessions: dict[str, dict] = {}
_sessions_lock = threading.Lock()

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".pdf"}
MAX_FILES = 50
CLEANUP_OLDER_THAN_SECONDS = 3600  # 1 hour


def _is_allowed(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS


def _cleanup_old_sessions():
    now = time.time()
    with _sessions_lock:
        stale = [sid for sid, info in _sessions.items()
                 if now - info["created_at"] > CLEANUP_OLDER_THAN_SECONDS]
        for sid in stale:
            import shutil
            try:
                shutil.rmtree(_sessions[sid]["dir"], ignore_errors=True)
            except Exception:
                pass
            del _sessions[sid]


def _schedule_cleanup():
    threading.Timer(CLEANUP_OLDER_THAN_SECONDS, _periodic_cleanup).start()


def _periodic_cleanup():
    _cleanup_old_sessions()
    _schedule_cleanup()


_schedule_cleanup()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    allowed = [f for f in files if f and _is_allowed(f.filename)]
    if not allowed:
        return jsonify({"error": "No valid receipt files (png/jpg/pdf/…)"}), 400
    if len(allowed) > MAX_FILES:
        return jsonify({"error": f"Too many files (max {MAX_FILES})"}), 400

    session_id = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp(prefix=f"receiptpro_{session_id}_")

    saved_paths = []
    for f in allowed:
        dest = os.path.join(tmp_dir, f.filename)
        f.save(dest)
        saved_paths.append(dest)

    with _sessions_lock:
        _sessions[session_id] = {
            "dir": tmp_dir,
            "files": saved_paths,
            "excel_path": None,
            "created_at": time.time(),
        }

    return jsonify({"session_id": session_id, "file_count": len(saved_paths)})


@app.route("/stream/<session_id>")
def stream(session_id: str):
    with _sessions_lock:
        session = _sessions.get(session_id)
    if not session:
        return Response("data: {\"error\": \"session not found\"}\n\n",
                        mimetype="text/event-stream", status=404)

    def generate():
        filepaths = session["files"]
        total = len(filepaths)
        receipts_data = []

        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

        for i, fp in enumerate(filepaths):
            filename = os.path.basename(fp)
            yield f"data: {json.dumps({'type': 'progress', 'index': i, 'filename': filename})}\n\n"

            try:
                extracted = extract_text_from_file(fp)
                parsed = parse_receipt(extracted)
                receipts_data.append((filename, extracted, parsed))
                yield f"data: {json.dumps({'type': 'done', 'index': i, 'filename': filename, 'parsed': parsed})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'index': i, 'filename': filename, 'message': str(e)})}\n\n"

        # Write Excel
        excel_path = os.path.join(session["dir"], "receipts.xlsx")
        try:
            write_to_excel_headless(excel_path, receipts_data)
            with _sessions_lock:
                _sessions[session_id]["excel_path"] = excel_path
            yield f"data: {json.dumps({'type': 'complete', 'download_url': f'/download/{session_id}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Excel export failed: {e}'})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/download/<session_id>")
def download(session_id: str):
    with _sessions_lock:
        session = _sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404

    excel_path = session.get("excel_path")
    if not excel_path or not os.path.exists(excel_path):
        return jsonify({"error": "Excel not ready yet"}), 404

    return send_file(excel_path, as_attachment=True, download_name="receipts.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    app.run(debug=True)
