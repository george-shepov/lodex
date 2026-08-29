import importlib
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse

import main
from virtual_alerts import VirtualRoomAlertMiddleware

app = main.app

# Register the persistent admin lead/CRM routes on the same FastAPI app.
importlib.import_module('leads')
importlib.import_module('catalog')

# Customer virtual-room joins must alert the operator even when the customer
# did not enter through the explicit live-support form.
app.add_middleware(VirtualRoomAlertMiddleware)


def find_upload_record(upload_id: str):
    for record in reversed(main.load_jsonl(main.UPLOAD_DIR.parent / 'uploads.jsonl')):
        if str(record.get('upload_id', '')) == upload_id:
            return record
    return None


def resolve_upload(upload_id: str):
    record = find_upload_record(upload_id)
    if not record:
        raise HTTPException(404, 'Upload not found.')

    stored_path = str(record.get('stored_path') or '').strip()
    if not stored_path:
        raise HTTPException(404, 'Upload file is unavailable.')

    candidate = Path(stored_path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate

    root = main.UPLOAD_DIR.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise HTTPException(404, 'Upload file is unavailable.') from exc

    if not resolved.is_file():
        raise HTTPException(404, 'Upload file is unavailable.')
    return record, resolved


@app.get('/api/admin/uploads/{upload_id}', dependencies=[Depends(main.require_admin)])
async def admin_upload(upload_id: str):
    record, path = resolve_upload(upload_id)
    return FileResponse(
        path,
        media_type=str(record.get('media_type') or 'application/octet-stream'),
        headers={
            'Cache-Control': 'private, max-age=300',
            'X-Content-Type-Options': 'nosniff',
        },
    )
