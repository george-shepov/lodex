import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

import main

app = main.app


def _configured_cents(name: str, fallback: int) -> int:
    try:
        return int(os.getenv(name, str(fallback)) or fallback)
    except ValueError:
        return fallback


HOME_CONSULTATION_CENTS = _configured_cents(
    'LODEX_HOME_CONSULTATION_CENTS',
    main.STRIPE_DEPOSIT_AMOUNT_CENTS or 15000,
)
BUSINESS_CONSULTATION_CENTS = _configured_cents('LODEX_BUSINESS_CONSULTATION_CENTS', 30000)


def project_segment(project: dict) -> str:
    category = str(project.get('service_category') or '').strip().lower()
    if category.startswith('lodex enterprise'):
        return 'enterprise'
    if category.startswith('lodex business'):
        return 'business'
    return 'home'


def segment_amount_cents(segment: str) -> int | None:
    if segment == 'home':
        return HOME_CONSULTATION_CENTS
    if segment == 'business':
        return BUSINESS_CONSULTATION_CENTS
    return None


@app.middleware('http')
async def segment_checkout_pricing(request: Request, call_next):
    if request.method != 'POST' or request.url.path != '/api/payments/checkout':
        return await call_next(request)

    try:
        payload = await request.json()
    except Exception:
        return await call_next(request)

    project_code = str(payload.get('project_code') or '').strip()
    phone = str(payload.get('phone') or '').strip()
    if len(project_code) < 6 or len(phone) < 7:
        return JSONResponse({'detail': 'Project code and phone number are required.'}, status_code=422)

    project = main.find_project(project_code, phone)
    if project is None:
        return JSONResponse({'detail': 'We could not match that project code and phone number.'}, status_code=404)

    segment = project_segment(project)
    amount_cents = segment_amount_cents(segment)
    if amount_cents is None:
        return JSONResponse(
            {
                'detail': 'LODEX Enterprise projects use custom assessment pricing. Submit the intake and LODEX will confirm the assessment fee before payment.',
                'status': 'custom_assessment',
                'customer_type': 'enterprise',
            },
            status_code=409,
        )

    if not main.STRIPE_SECRET_KEY or amount_cents <= 0:
        return JSONResponse({'detail': 'Stripe consultation payments are not configured yet.'}, status_code=503)

    normalized_code = str(project['project_code']).upper()
    existing_payment = main.latest_payment(normalized_code)
    if existing_payment and existing_payment.get('status') == 'paid':
        return JSONResponse({'status': 'paid', 'project_code': normalized_code})

    origin = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173').rstrip('/')
    success_url = os.getenv(
        'STRIPE_CHECKOUT_SUCCESS_URL',
        f'{origin}/?payment=success&project_code={normalized_code}&session_id={{CHECKOUT_SESSION_ID}}',
    )
    cancel_url = os.getenv(
        'STRIPE_CHECKOUT_CANCEL_URL',
        f'{origin}/?payment=cancelled&project_code={normalized_code}',
    )
    service_category = str(project.get('service_category') or 'LODEX project')[:120]
    segment_label = 'LODEX Home' if segment == 'home' else 'LODEX Business'
    fields = [
        ('mode', 'payment'),
        ('success_url', success_url),
        ('cancel_url', cancel_url),
        ('line_items[0][price_data][currency]', main.STRIPE_CURRENCY),
        ('line_items[0][price_data][unit_amount]', str(amount_cents)),
        ('line_items[0][price_data][product_data][name]', f'{segment_label} on-site consultation — {service_category}'),
        ('line_items[0][quantity]', '1'),
        ('metadata[project_code]', normalized_code),
        ('metadata[project_id]', str(project.get('id', ''))),
        ('metadata[customer_type]', segment),
    ]
    email = str(project.get('email') or '').strip()
    if email:
        fields.append(('customer_email', email))

    session = await main.stripe_checkout_session(fields, f'lodex-{segment}-consultation-{normalized_code}-{uuid.uuid4().hex}')
    main.append_jsonl(main.PAYMENTS_FILE, {
        'project_code': normalized_code,
        'project_id': project.get('id'),
        'session_id': session['id'],
        'status': 'checkout_created',
        'customer_type': segment,
        'amount_cents': amount_cents,
        'currency': main.STRIPE_CURRENCY,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    return JSONResponse({
        'status': 'checkout_created',
        'project_code': normalized_code,
        'customer_type': segment,
        'checkout_url': session['url'],
        'amount_cents': amount_cents,
        'currency': main.STRIPE_CURRENCY,
    })


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
