# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import os
import sys
import time
import base64
import threading
import datetime
import shutil
import mimetypes
from urllib.parse import unquote, urlparse
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

def resolve_target_file(user_inbox_dir, path_info):
    """Resolve requested WebDAV path to local filesystem path within user's inbox folder."""
    raw_path = unquote(path_info).strip()
    clean_path = raw_path.lstrip("/")

    if clean_path.lower().startswith("davwwwroot/"):
        clean_path = clean_path[11:].lstrip("/")
    elif clean_path.lower() == "davwwwroot":
        clean_path = ""

    if clean_path.lower().startswith("inbox/"):
        clean_path = clean_path[6:].lstrip("/")
    elif clean_path.lower() == "inbox":
        clean_path = ""

    if not clean_path:
        return user_inbox_dir, ""

    safe_basename = os.path.basename(clean_path)
    target_path = os.path.join(user_inbox_dir, safe_basename)
    return target_path, safe_basename

def build_propfind_xml(user_inbox_dir, target_file, req_path, depth="1"):
    """Construct WebDAV 207 Multi-Status XML response fully compliant with Windows Explorer WebClient."""
    multistatus = ET.Element("d:multistatus", {"xmlns:d": "DAV:"})

    items = []

    clean_req_path = req_path.rstrip("/")
    if not clean_req_path:
        clean_req_path = "/"

    if os.path.isdir(target_file):
        base_href = clean_req_path if clean_req_path.endswith("/") else clean_req_path + "/"
        dir_name = os.path.basename(target_file) or "inbox"
        items.append((base_href, target_file, dir_name, True))

        if depth != "0" and os.path.exists(target_file):
            for fname in os.listdir(target_file):
                fpath = os.path.join(target_file, fname)
                if os.path.isfile(fpath):
                    child_href = base_href + fname
                    items.append((child_href, fpath, fname, False))
    elif os.path.isfile(target_file):
        fname = os.path.basename(target_file)
        items.append((clean_req_path, target_file, fname, False))

    for href_str, fpath, display_name, is_dir in items:
        response = ET.SubElement(multistatus, "d:response")
        ET.SubElement(response, "d:href").text = href_str

        propstat = ET.SubElement(response, "d:propstat")
        prop = ET.SubElement(propstat, "d:prop")

        ET.SubElement(prop, "d:displayname").text = display_name
        ET.SubElement(prop, "d:ishidden").text = "0"

        if is_dir:
            resourcetype = ET.SubElement(prop, "d:resourcetype")
            ET.SubElement(resourcetype, "d:collection")
            ET.SubElement(prop, "d:iscollection").text = "1"
        else:
            ET.SubElement(prop, "d:resourcetype")
            ET.SubElement(prop, "d:iscollection").text = "0"
            if os.path.exists(fpath):
                size = os.path.getsize(fpath)
                ET.SubElement(prop, "d:getcontentlength").text = str(size)
                
                mime_type, _ = mimetypes.guess_type(fpath)
                ET.SubElement(prop, "d:getcontenttype").text = mime_type or "application/octet-stream"

                mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(fpath)).strftime("%a, %d %b %Y %H:%M:%S GMT")
                ET.SubElement(prop, "d:getlastmodified").text = mtime
                
                ctime = datetime.datetime.utcfromtimestamp(os.path.getctime(fpath)).strftime("%Y-%m-%dT%H:%M:%SZ")
                ET.SubElement(prop, "d:creationdate").text = ctime

        supportedlock = ET.SubElement(prop, "d:supportedlock")
        lockentry = ET.SubElement(supportedlock, "d:lockentry")
        lockscope = ET.SubElement(lockentry, "d:lockscope")
        ET.SubElement(lockscope, "d:exclusive")
        locktype = ET.SubElement(lockentry, "d:locktype")
        ET.SubElement(locktype, "d:write")

        ET.SubElement(propstat, "d:status").text = "HTTP/1.1 200 OK"

    return ET.tostring(multistatus, encoding="utf-8", xml_declaration=True)

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

    target_file, rel_name = resolve_target_file(user_inbox_dir, path_info)

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

    # PROPFIND (Directory listing / File inspection)
    if method == "PROPFIND":
        if not os.path.exists(target_file):
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"404 Not Found"]

        depth = environ.get("HTTP_DEPTH", "1")
        xml_resp = build_propfind_xml(user_inbox_dir, target_file, path_info, depth)
        headers = [
            ("Content-Type", "application/xml; charset=utf-8"),
            ("Content-Length", str(len(xml_resp)))
        ]
        start_response("207 Multi-Status", headers)
        return [xml_resp]

    # LOCK (Windows Explorer Lock Request before Upload)
    if method == "LOCK":
        file_existed = os.path.exists(target_file)
        lock_token = "opaquelocktoken:noxus-" + secrets.token_hex(16)
        xml_resp = f"""<?xml version="1.0" encoding="utf-8"?>
<d:prop xmlns:d="DAV:">
  <d:lockdiscovery>
    <d:activelock>
      <d:locktype><d:write/></d:locktype>
      <d:lockscope><d:exclusive/></d:lockscope>
      <d:depth>0</d:depth>
      <d:owner><d:href>{path_info}</d:href></d:owner>
      <d:timeout>Second-3600</d:timeout>
      <d:locktoken><d:href>{lock_token}</d:href></d:locktoken>
      <d:lockroot><d:href>{path_info}</d:href></d:lockroot>
    </d:activelock>
  </d:lockdiscovery>
</d:prop>""".encode("utf-8")
        headers = [
            ("Content-Type", "application/xml; charset=utf-8"),
            ("Lock-Token", f"<{lock_token}>"),
            ("Content-Length", str(len(xml_resp)))
        ]
        status = "200 OK" if file_existed else "201 Created"
        start_response(status, headers)
        return [xml_resp]

    # UNLOCK
    if method == "UNLOCK":
        start_response("204 No Content", [("Content-Length", "0")])
        return []

    # PROPPATCH (Windows metadata modification)
    if method == "PROPPATCH":
        xml_resp = f"""<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>{path_info}</d:href>
    <d:propstat>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>""".encode("utf-8")
        headers = [
            ("Content-Type", "application/xml; charset=utf-8"),
            ("Content-Length", str(len(xml_resp)))
        ]
        start_response("207 Multi-Status", headers)
        return [xml_resp]

    # MKCOL (Folder Creation)
    if method == "MKCOL":
        os.makedirs(target_file, exist_ok=True)
        start_response("201 Created", [("Content-Length", "0")])
        return []

    # PUT (File Upload via Drag & Drop in Windows Explorer)
    if method == "PUT":
        if not rel_name or os.path.isdir(target_file):
            start_response("400 Bad Request", [("Content-Type", "text/plain")])
            return [b"Ungueltiger Dateiname"]

        file_existed = os.path.exists(target_file)
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

            print(f"[WebDAV Upload Success] Saved file '{rel_name}' to user {user.id} inbox.")
            status = "204 No Content" if file_existed else "201 Created"
            start_response(status, [("Content-Length", "0"), ("ETag", f'"{secrets.token_hex(8)}"')])
            return []
        except Exception as e:
            print(f"[WebDAV Upload Error] {e}")
            start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
            return [str(e).encode("utf-8")]

    # GET / HEAD (File Download / File Check)
    if method in ["GET", "HEAD"]:
        if os.path.isfile(target_file):
            size = os.path.getsize(target_file)
            mime_type, _ = mimetypes.guess_type(target_file)
            headers = [
                ("Content-Type", mime_type or "application/octet-stream"),
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
        if os.path.exists(target_file):
            try:
                if os.path.isdir(target_file):
                    shutil.rmtree(target_file)
                else:
                    os.remove(target_file)
                start_response("204 No Content", [])
                return []
            except Exception as e:
                start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
                return [str(e).encode("utf-8")]
        else:
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"Datei nicht gefunden"]

    # MOVE / COPY
    if method in ["MOVE", "COPY"]:
        dest_hdr = environ.get("HTTP_DESTINATION", "")
        if dest_hdr:
            parsed = urlparse(dest_hdr)
            dest_target, dest_rel = resolve_target_file(user_inbox_dir, parsed.path)
            if os.path.exists(target_file) and dest_target:
                try:
                    if method == "MOVE":
                        shutil.move(target_file, dest_target)
                    else:
                        if os.path.isdir(target_file):
                            shutil.copytree(target_file, dest_target, dirs_exist_ok=True)
                        else:
                            shutil.copy2(target_file, dest_target)
                    start_response("201 Created", [("Content-Length", "0")])
                    return []
                except Exception as e:
                    start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
                    return [str(e).encode("utf-8")]
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Ziel nicht gefunden"]

    # Default fallback
    headers = [("Allow", "OPTIONS, GET, HEAD, PUT, DELETE, PROPFIND, PROPPATCH, MKCOL, COPY, MOVE, LOCK, UNLOCK")]
    start_response("200 OK", headers)
    return []

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
