import os, sys, socket, mimetypes
from urllib.parse import unquote, quote
import threading
import time
from typing import Dict, List

# config
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8001"))
ALLOWED_EXTENSIONS = {".html", ".png", ".pdf"}
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "16"))
COUNTS: Dict[str, int] = {}
COUNTS_LOCK = threading.Lock()
REQUESTS_PER_SECOND = 5
TIME_WINDOW = 1.0


client_requests: Dict[str, List[float]] = {}
requests_lock = threading.Lock()

# ensure common types exist
mimetypes.init()
mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("text/html; charset=utf-8", ".html")


def file_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def _bump_count(path_key: str):
    with COUNTS_LOCK:
        current = COUNTS.get(path_key, 0)
        time.sleep(100 / 1000.0)
        COUNTS[path_key] = current + 1


def respond(conn, status, headers, body):
    head = [f"HTTP/1.1 {status}".encode()]
    for k, v in headers.items():
        head.append(f"{k}: {v}".encode())
    head.append(b"")
    head.append(b"")
    conn.sendall(b"\r\n".join(head) + body)


def _is_subpath(child: str, parent: str) -> bool:
    child_real = os.path.realpath(child)
    parent_real = os.path.realpath(parent)
    try:
        return os.path.commonpath([child_real, parent_real]) == parent_real
    except ValueError:
        return False


def allow_request(ip: str) -> bool:
    #  Check if request from IP should be allowed based on rate limit
    now = time.time()

    with requests_lock:
        if ip not in client_requests:
            client_requests[ip] = []

        timestamps = client_requests[ip]

        # Clean old timestamps beyond window
        client_requests[ip] = [t for t in timestamps if now - t < TIME_WINDOW]

        # Check limit
        if len(client_requests[ip]) < REQUESTS_PER_SECOND:
            client_requests[ip].append(now)
            return True
        return False


def _respond_429(conn):
    body = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href='https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap' rel='stylesheet'>
    <title>429 Too Many Requests</title>
    <style>
    body{margin:0;padding:0;display:flex;justify-content:center;align-items:center;height:100vh;
    background:#0f0f10;color:#e5e5e5;font-family:'JetBrains Mono',monospace;text-align:center;}
    .container{max-width:600px;padding:20px;background:#18181b;border:1px solid #2a2a2a;
    border-radius:16px;box-shadow:0 0 24px rgba(125,249,255,0.08);}
    h1{font-size:80px;color:#7df9ff;margin:0;text-shadow:0 0 10px #00ffff;}
    p{color:#9ca3af;font-size:16px;margin-top:10px;}
    .hint{color:#777;margin-top:4px;font-size:14px;}
    </style></head>
    <body><div class="container">
    <h1>429</h1>
    <p>Too Many Requests</p>
    <p class="hint">Please slow down and try again in a moment.</p>
    </div></body></html>""".encode("utf-8")

    respond(conn, "429 Too Many Requests", {
        "Content-Type": "text/html; charset=utf-8",
        "Retry-After": "1",
        "Content-Length": str(len(body)),
        "Connection": "close"
    }, body)


def _minimal_listing_html(req_path: str, abs_dir: str) -> bytes:
    import datetime as _dt
    try:
        entries = sorted(os.listdir(abs_dir))
    except OSError:
        return b"<html><body><h1>Forbidden</h1></body></html>"

    lines = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<link href='https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap' rel='stylesheet'>",
        f"<title>Directory of {req_path}</title>",
        "<style>",
        "body{margin:0;padding:32px;background:#0f0f10;color:#e5e5e5;font-family:'JetBrains Mono',monospace;}",
        "h1{color:#7df9ff;text-align:center;font-weight:600;margin-bottom:24px;}",
        "main{max-width:900px;margin:0 auto;border:1px solid #2a2a2a;border-radius:16px;background:#18181b;padding:20px;box-shadow:0 0 20px rgba(125,249,255,0.1);}",
        "table{width:100%;border-collapse:collapse;}",
        "th,td{padding:10px 14px;text-align:left;border-bottom:1px solid #2a2a2a;}",
        "th{color:#9ca3af;font-weight:600;font-size:14px;}",
        "a{color:#7df9ff;text-decoration:none;transition:color 0.2s ease;}",
        "a:hover{color:#00ffff;text-shadow:0 0 6px #00ffff;}",
        "tr:hover{background:#202022;transition:background 0.2s ease;}",
        ".dir a::before{content:'📂 ';}",
        ".file a::before{content:'📄 ';}",
        ".up a::before{content:'⬆ ';}",
        ".footer{text-align:center;margin-top:20px;font-size:13px;color:#777;}",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>🌌 Maxim's PR2 Lab Explorer</h1>",
        "<main>",
        f"<h2 style='color:#9ca3af;margin-top:0;'>Path: {req_path}</h2>",
    ]

    if req_path != "/":
        parent = req_path.rstrip("/").rsplit("/", 1)[0]
        parent = "/" if not parent else parent + "/"
        lines.append(f'<p><a href="{quote(parent)}">⬆ Go Back</a></p>')

    lines.append("<table>")
    lines.append("<thead><tr><th>Name</th><th>Size</th><th>Last modified</th><th>Hits</th></tr></thead>")
    lines.append("<tbody>")

    for name in entries:
        full = os.path.join(abs_dir, name)
        is_directory = os.path.isdir(full)
        href = quote(name) + ("/" if is_directory else "")
        row_class = "dir" if is_directory else "file"
        size = "—" if is_directory else file_size(os.path.getsize(full))
        ts = os.path.getmtime(full)
        mtime = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        hits = COUNTS.get(req_path + name + ("/" if is_directory else ""), 0)
        lines.append(
            f'<tr class="{row_class}"><td><a href="{href}">{name}{"/" if is_directory else ""}</a></td>'
            f"<td>{size}</td><td>{mtime}</td><td>{hits}</td></tr>"
        )

    lines.append("</tbody></table>")
    lines.append("</main>")
    lines.append("<div class='footer'>© 2025 Maxim Roenco | Powered by Python Socket Server</div>")
    lines.append("</body></html>")

    return "\n".join(lines).encode("utf-8")



def _respond_301(conn, location: str):
    body = (f'<html><body>Moved: <a href="{location}">{location}</a></body></html>').encode("utf-8")
    respond(conn, "301 Moved Permanently",
            {"Location": location, "Content-Type": "text/html; charset=utf-8",

             "Content-Length": str(len(body)), "Connection": "close"}, body)


def _respond_404(conn):
    body = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href='https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap' rel='stylesheet'>
    <title>404 Not Found</title>
    <style>
    body{margin:0;padding:0;display:flex;justify-content:center;align-items:center;height:100vh;
    background:#0f0f10;color:#e5e5e5;font-family:'JetBrains Mono',monospace;text-align:center;}
    .container{max-width:600px;padding:20px;background:#18181b;border:1px solid #2a2a2a;
    border-radius:16px;box-shadow:0 0 24px rgba(125,249,255,0.08);}
    h1{font-size:80px;color:#7df9ff;margin:0;text-shadow:0 0 10px #00ffff;}
    p{color:#9ca3af;font-size:16px;margin-top:10px;}
    a{color:#7df9ff;text-decoration:none;font-weight:600;}
    a:hover{text-shadow:0 0 6px #00ffff;}
    </style></head>
    <body><div class="container">
    <h1>404</h1>
    <p>Oops! The page you’re looking for doesn’t exist.</p>
    <p><a href="/">Return to Home</a></p>
    </div></body></html>""".encode("utf-8")

    respond(conn, "404 Not Found", {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": str(len(body)),
        "Connection": "close"
    }, body)


# multithreaded handler
def _serve_connection(conn: socket.socket, addr, content_dir: str):
    # Multithreaded handler with rate limiting
    try:
        client_ip = addr[0]

        # Check rate limit
        if not allow_request(client_ip):
            _respond_429(conn)
            return

        time.sleep(0.5)  # simulate work
        data = conn.recv(4096)
        if not data:
            return

        line = data.split(b"\r\n", 1)[0].decode(errors="replace")
        parts = line.split()
        if len(parts) != 3:
            respond(conn, "400 Bad Request",
                    {"Content-Type": "text/plain", "Connection": "close"},
                    b"Bad Request")
            return

        method, target, version = parts
        if method != "GET":
            respond(conn, "405 Method Not Allowed",
                    {"Allow": "GET", "Content-Type": "text/plain", "Connection": "close"},
                    b"Only GET is allowed")
            return

        if not target.startswith("/"):
            target = "/"
        target = unquote(target)
        _bump_count(target)

        # map to filesystem under content_dir
        requested_rel = "" if target == "/" else target.lstrip("/")
        requested_abs = os.path.realpath(os.path.join(content_dir, requested_rel))

        # 1) traversal guard
        if not _is_subpath(requested_abs, content_dir):
            _respond_404(conn)
            return

        # 2) directory
        if os.path.isdir(requested_abs):
            if not target.endswith("/"):
                _respond_301(conn, target + "/")
                return
            body = _minimal_listing_html(target, requested_abs)
            respond(conn, "200 OK",
                    {"Content-Type": "text/html; charset=utf-8",
                    "Content-Length": str(len(body)), "Connection": "close"},
                    body)
            return

        # 3) file
        if not os.path.isfile(requested_abs):
            _respond_404(conn)
            return

        ext = os.path.splitext(requested_abs)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            _respond_404(conn)
            return

        mime_type, _ = mimetypes.guess_type(requested_abs)
        if mime_type is None:
            _respond_404(conn)
            return

        try:
            with open(requested_abs, "rb") as f:
                body = f.read()
            respond(conn, "200 OK",
                    {"Content-Type": mime_type,
                    "Content-Length": str(len(body)), "Connection": "close"},
                    body)
        except OSError:
            respond(conn, "500 Internal Server Error",
                    {"Content-Type": "text/plain", "Connection": "close"},
                    b"Internal Server Error")
    finally:
        try:
            conn.close()
        except Exception:
            pass

def main():
    if len(sys.argv) != 2:
        print("Usage: python server_mt.py <directory>")
        sys.exit(1)
    content_dir = os.path.abspath(sys.argv[1])
    if not os.path.isdir(content_dir):
        print(f"Error: Directory '{content_dir}' does not exist.")
        sys.exit(1)

    print(f"Serving directory (MT - Thread per request): {content_dir}")
    print(f"Server running on: http://0.0.0.0:{PORT}")
    print("Press Ctrl+C to stop")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        
        try:
            while True:
                conn, addr = s.accept()
                # Create a new thread for each request
                thread = threading.Thread(
                    target=_serve_connection, 
                    args=(conn, addr, content_dir),
                    daemon=True
                )
                thread.start()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            sys.exit(0)


if __name__ == "__main__":
    main()