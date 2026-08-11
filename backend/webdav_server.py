# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import os
import sys
import time
import base64
import threading
import datetime
from xml.etree import ElementTree as ET
from wsgiref.simple_server import make_server, WSGIRequestHandler

from database import SessionLocal
import models
import auth

from sqlalchemy import func
import re
import hashlib
import secrets

WEBDAV_PORT = 8080
INBOX_BASE_DIR = os.path.abspath("documents/inbox")
os.makedirs(INBOX_BASE_DIR, exist_ok=True)
REALM = "Noxus Policy Posteingang Netzlaufwerk"

class QuietWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        # Suppress verbose WebDAV HTTP polling logs
        pass

def parse_digest_header(auth_header):
    content = auth_header[7:].strip()
    params = {}
    pattern = re.compile(r'(\w+)=(?:"([^"]*)"|([^,\s]*))')
    for match in pattern.finditer(content):
        key = match.group(1)
        val = match.group(2) if match.group(2) is not None else match.group(3)
        params[key] = val
    return params

def authenticate_request(environ):
    """Authenticate Digest Auth (Windows HTTP native) or Basic Auth against database netdrive credentials."""
    auth_header = environ.get("HTTP_AUTHORIZATION", "")
    method = environ.get("REQUEST_METHOD", "GET")
    path_info = environ.get("PATH_INFO", "/")

    if not auth_header:
        return None

    db = SessionLocal()
    try:
        # 1. Digest Auth (Native Windows Explorer over HTTP without registry changes)
        if auth_header.startswith("Digest "):
            params = parse_digest_header(auth_header)
            raw_username = params.get("username", "")
            clean_username = raw_username.split("\\")[-1].strip()

            user = db.query(models.User).filter(
                func.lower(models.User.netdrive_username) == clean_username.lower()
            ).first()

            if user and (user.netdrive_digest_ha1 or user.netdrive_password_hash):
                ha1 = user.netdrive_digest_ha1
                if ha1:
                    req_uri = params.get("uri", path_info)
                    nonce = params.get("nonce", "")
                    nc = params.get("nc", "")
                    cnonce = params.get("cnonce", "")
                    qop = params.get("qop", "")
                    response = params.get("response", "")

                    ha2_1 = hashlib.md5(f"{method}:{req_uri}".encode()).hexdigest()
                    ha2_2 = hashlib.md5(f"{method}:{path_info}".encode()).hexdigest()

                    if qop == "auth":
                        expected_1 = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2_1}".encode()).hexdigest()
                        expected_2 = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2_2}".encode()).hexdigest()
                    else:
                        expected_1 = hashlib.md5(f"{ha1}:{nonce}:{ha2_1}".encode()).hexdigest()
                        expected_2 = hashlib.md5(f"{ha1}:{nonce}:{ha2_2}".encode()).hexdigest()

                    if secrets.compare_digest(response, expected_1) or secrets.compare_digest(response, expected_2):
                        print(f"[WebDAV Digest Auth] Successful login for '{user.email}' (netdrive: '{clean_username}')")
                        return user
                    else:
                        print(f"[WebDAV Digest Auth Failed] Response mismatch for netdrive user '{clean_username}'")

        # 2. Basic Auth Fallback (macOS / Linux / iOS / Mobile)
        elif auth_header.startswith("Basic "):
            try:
                encoded = auth_header.split(" ", 1)[1]
                decoded = base64.b64decode(encoded).decode("utf-8")
                raw_username, password = decoded.split(":", 1)
                clean_username = raw_username.split("\\")[-1].strip()

                user = db.query(models.User).filter(
                    func.lower(models.User.netdrive_username) == clean_username.lower()
                ).first()

                if user and user.netdrive_password_hash:
                    if auth.verify_password(password, user.netdrive_password_hash):
                        # Auto-generate HA1 for Digest Auth if missing
                        if not user.netdrive_digest_ha1:
                            ha1_str = f"{user.netdrive_username}:{REALM}:{password}"
                            user.netdrive_digest_ha1 = hashlib.md5(ha1_str.encode("utf-8")).hexdigest()
                            db.commit()
                        print(f"[WebDAV Basic Auth] Successful login for '{user.email}' (netdrive: '{clean_username}')")
                        return user
                    else:
                        print(f"[WebDAV Basic Auth Failed] Password mismatch for netdrive user '{clean_username}'")
            except Exception as e:
                print(f"[WebDAV Basic Auth Error] Failed to decode header: {e}")
    finally:
        db.close()

    return None

def webdav_app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path_info = environ.get("PATH_INFO", "/")

    # Authenticate Digest or Basic Auth
    user = authenticate_request(environ)
    if not user:
        nonce_val = hashlib.md5(f"{time.time()}:{secrets.token_hex(8)}".encode()).hexdigest()
        opaque_val = hashlib.md5(f"NoxusOpaque:{nonce_val}".encode()).hexdigest()
        digest_header = f'Digest realm="{REALM}", qop="auth", nonce="{nonce_val}", opaque="{opaque_val}"'
        basic_header = f'Basic realm="{REALM}"'

        headers = [
            ("WWW-Authenticate", digest_header),
            ("WWW-Authenticate", basic_header),
            ("Content-Type", "text/plain"),
        ]
        start_response("401 Unauthorized", headers)
        return [b"401 Unauthorized - Bitte Netzlaufwerk-Zugangsdaten verwenden."]

    # User-specific inbox directory
    user_inbox_dir = os.path.join(INBOX_BASE_DIR, str(user.id))
    os.makedirs(user_inbox_dir, exist_ok=True)

    # Clean requested filename from path
    rel_path = path_info.lstrip("/").strip()
    if rel_path.startswith("inbox/"):
        rel_path = rel_path[6:]
    elif rel_path == "inbox":
        rel_path = ""

    target_file = os.path.join(user_inbox_dir, os.path.basename(rel_path)) if rel_path else user_inbox_dir

    # OPTIONS
    if method == "OPTIONS":
        headers = [
            ("DAV", "1, 2"),
            ("MS-Author-Via", "DAV"),
            ("Allow", "OPTIONS, GET, HEAD, POST, PUT, DELETE, PROPFIND, PROPPATCH, MKCOL, COPY, MOVE, LOCK, UNLOCK"),
            ("Content-Length", "0")
        ]
        start_response("200 OK", headers)
        return []

    # PROPFIND (Windows Directory Listing & Properties)
    if method == "PROPFIND":
        xml_resp = build_propfind_xml(user_inbox_dir, path_info)
        headers = [
            ("Content-Type", "application/xml; charset=utf-8"),
            ("Content-Length", str(len(xml_resp)))
        ]
        start_response("207 Multi-Status", headers)
        return [xml_resp]

    # PUT (File Upload via Netzlaufwerk)
    if method == "PUT":
        if not rel_path or os.path.isdir(target_file):
            start_response("400 Bad Request", [("Content-Type", "text/plain")])
            return [b"Ungueltiger Dateiname"]

        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
        except (ValueError, TypeError):
            content_length = 0

        try:
            with open(target_file, "wb") as f:
                if content_length > 0:
                    remaining = content_length
                    while remaining > 0:
                        chunk = environ["wsgi.input"].read(min(remaining, 65536))
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)
                else:
                    while True:
                        chunk = environ["wsgi.input"].read(65536)
                        if not chunk:
                            break
                        f.write(chunk)

            start_response("201 Created", [("Content-Length", "0")])
            return []
        except Exception as e:
            start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
            return [str(e).encode("utf-8")]

    # GET (Download File)
    if method in ["GET", "HEAD"]:
        if os.path.isfile(target_file):
            size = os.path.getsize(target_file)
            headers = [
                ("Content-Type", "application/octet-stream"),
                ("Content-Length", str(size))
            ]
            start_response("200 OK", headers)
            if method == "HEAD":
                return []
            def file_iter():
                with open(target_file, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        yield chunk
            return file_iter()
        else:
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"Datei nicht gefunden"]

    # DELETE
    if method == "DELETE":
        if os.path.isfile(target_file):
            try:
                os.remove(target_file)
                start_response("204 No Content", [])
                return []
            except Exception as e:
                start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
                return [str(e).encode("utf-8")]

    # Default fallback
    headers = [("Allow", "OPTIONS, GET, HEAD, PUT, DELETE, PROPFIND")]
    start_response("200 OK", headers)
    return []

def build_propfind_xml(user_inbox_dir, req_path):
    """Construct WebDAV 207 Multi-Status XML response for Windows Explorer."""
    multistatus = ET.Element("d:multistatus", {"xmlns:d": "DAV:"})

    items = [("", user_inbox_dir)]
    if os.path.exists(user_inbox_dir):
        for fname in os.listdir(user_inbox_dir):
            fpath = os.path.join(user_inbox_dir, fname)
            if os.path.isfile(fpath):
                items.append((fname, fpath))

    for fname, fpath in items:
        response = ET.SubElement(multistatus, "d:response")
        href_str = req_path.rstrip("/") + "/" + fname if fname else req_path
        ET.SubElement(response, "d:href").text = href_str

        propstat = ET.SubElement(response, "d:propstat")
        prop = ET.SubElement(propstat, "d:prop")

        if os.path.isdir(fpath):
            resourcetype = ET.SubElement(prop, "d:resourcetype")
            ET.SubElement(resourcetype, "d:collection")
        else:
            ET.SubElement(prop, "d:resourcetype")
            size = os.path.getsize(fpath)
            ET.SubElement(prop, "d:getcontentlength").text = str(size)
            mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(fpath)).strftime("%a, %d %b %Y %H:%M:%S GMT")
            ET.SubElement(prop, "d:getlastmodified").text = mtime

        ET.SubElement(propstat, "d:status").text = "HTTP/1.1 200 OK"

    return ET.tostring(multistatus, encoding="utf-8", xml_declaration=True)

def start_webdav_server_thread():
    """Start the WebDAV server thread on port 8080."""
    def run_server():
        try:
            httpd = make_server("0.0.0.0", WEBDAV_PORT, webdav_app, handler_class=QuietWSGIRequestHandler)
            print(f"[WebDAV Server] Listening on 0.0.0.0:{WEBDAV_PORT} for Netzlaufwerk connections...")
            httpd.serve_forever()
        except Exception as e:
            print(f"[WebDAV Server Error] {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread
