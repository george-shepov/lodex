import asyncio
import json
from pathlib import Path

import httpx
import pytest

import admin_media
import main


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def media_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / 'data'
    uploads_dir = data_dir / 'uploads'
    uploads_dir.mkdir(parents=True)
    image = uploads_dir / 'customer-photo.jpg'
    image.write_bytes(b'customer-photo-bytes')
    (data_dir / 'uploads.jsonl').write_text(json.dumps({
        'upload_id': 'photo-123',
        'filename': 'kitchen.jpg',
        'media_type': 'image/jpeg',
        'description': 'Kitchen damage',
        'stored_path': str(image),
    }) + '\n', encoding='utf-8')

    monkeypatch.setattr(main, 'UPLOAD_DIR', uploads_dir)
    monkeypatch.setattr(main, 'LODEX_ADMIN_TOKEN', 'owner-token-for-tests')
    main.admin_sessions.clear()
    return image


def test_admin_upload_requires_session_and_serves_media(media_app):
    async def scenario():
        transport = httpx.ASGITransport(app=admin_media.app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            blocked = await client.get('/api/admin/uploads/photo-123')
            assert blocked.status_code == 401

            login = await client.post('/api/admin/login', json={'token': 'owner-token-for-tests'})
            assert login.status_code == 200

            response = await client.get('/api/admin/uploads/photo-123')
            assert response.status_code == 200
            assert response.content == b'customer-photo-bytes'
            assert response.headers['content-type'].startswith('image/jpeg')
            assert response.headers['cache-control'].startswith('private')
            assert response.headers['x-content-type-options'] == 'nosniff'

            missing = await client.get('/api/admin/uploads/missing')
            assert missing.status_code == 404

    run(scenario())
