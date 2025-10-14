import socket
import os
import sys
from urllib.parse import unquote

# MIME types for different file extensions
MIME_TYPES = {
    '.html': 'text/html',
    '.pdf': 'application/pdf',
    '.png': 'image/png'
}

def parse_http_request(request_data):
    """Parse HTTP request and return method, path, and headers"""
    lines = request_data.split('\r\n')
    request_line = lines[0].split()
    
    if len(request_line) < 3:
        return None, None, None
    
    method = request_line[0]
    path = request_line[1]
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    return method, path, headers

def generate_directory_listing(directory_path, url_path):
    """Generate HTML page showing directory contents"""
    try:
        items = os.listdir(directory_path)
    except (OSError, PermissionError):
        return None
    
    # Sort: directories first, then files
    dirs = sorted([i for i in items if os.path.isdir(os.path.join(directory_path, i))])
    files = sorted([i for i in items if os.path.isfile(os.path.join(directory_path, i))])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Directory listing for {url_path}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ padding: 8px; border-bottom: 1px solid #eee; }}
        a {{ text-decoration: none; color: #0066cc; }}
        a:hover {{ text-decoration: underline; }}
        .dir {{ font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Directory listing for {url_path}</h1>
    <hr>
    <ul>
"""
    
    # Add parent directory link if not at root
    if url_path != '/':
        parent_path = '/'.join(url_path.rstrip('/').split('/')[:-1])
        if not parent_path:
            parent_path = '/'
        html += f'        <li><a href="{parent_path}" class="dir"> Parent Directory</a></li>\n'
    
    # Add directories
    for d in dirs:
        href = url_path.rstrip('/') + '/' + d
        html += f'        <li><a href="{href}" class="dir"> {d}/</a></li>\n'
    
    # Add files
    for f in files:
        href = url_path.rstrip('/') + '/' + f
        html += f'        <li><a href="{href}"> {f}</a></li>\n'
    
    html += """    </ul>
    <hr>
</body>
</html>"""
    
    return html

def create_http_response(status_code, status_text, content_type, body):
    """Create HTTP response with headers and body"""
    if isinstance(body, str):
        body = body.encode('utf-8')
    
    response = f"HTTP/1.1 {status_code} {status_text}\r\n"
    response += f"Content-Type: {content_type}\r\n"
    response += f"Content-Length: {len(body)}\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    
    return response.encode('utf-8') + body

def handle_request(client_socket, base_directory):
    """Handle a single HTTP request"""
    try:
        # Receive request
        request_data = client_socket.recv(4096).decode('utf-8')
        
        if not request_data:
            return
        
        print(f"Received request:\n{request_data[:200]}...")
        
        # Parse request
        method, path, headers = parse_http_request(request_data)
        
        if method is None:
            response = create_http_response(400, "Bad Request", "text/html", 
                                           "<h1>400 Bad Request</h1>")
            client_socket.sendall(response)
            return
        
        # Only support GET method
        if method != 'GET':
            response = create_http_response(405, "Method Not Allowed", "text/html",
                                           "<h1>405 Method Not Allowed</h1>")
            client_socket.sendall(response)
            return
        
        # Decode URL path
        path = unquote(path)
        
        # Default path
        if path == '/':
            path = '/index.html'
        
        # Remove leading slash and construct file path
        file_path = os.path.normpath(os.path.join(base_directory, path.lstrip('/')))
        
        # Security check: ensure file is within base directory
        # if not file_path.startswith(os.path.abspath(base_directory)):
        #     response = create_http_response(403, "Forbidden", "text/html",
        #                                    "<h1>403 Forbidden</h1>")
        #     client_socket.sendall(response)
        #     return
        
        # Check if path is a directory
        if os.path.isdir(file_path):
            # Try to serve index.html if it exists
            index_path = os.path.join(file_path, 'index.html')
            if os.path.isfile(index_path):
                file_path = index_path
            else:
                # Generate directory listing
                html_content = generate_directory_listing(file_path, path.rstrip('/') + '/')
                if html_content is None:
                    response = create_http_response(404, "Not Found", "text/html",
                                                   "<h1>404 Not Found</h1>")
                else:
                    response = create_http_response(200, "OK", "text/html", html_content)
                client_socket.sendall(response)
                return
        
        # Check if file exists
        if not os.path.isfile(file_path):
            response = create_http_response(404, "Not Found", "text/html",
                                           "<h1>404 Not Found</h1><p>The requested file was not found.</p>")
            client_socket.sendall(response)
            print(f"404: File not found - {file_path}")
            return
        
        # Get file extension and MIME type
        _, ext = os.path.splitext(file_path)
        content_type = MIME_TYPES.get(ext.lower())
        
        if content_type is None:
            response = create_http_response(415, "Unsupported Media Type", "text/html",
                                           "<h1>415 Unsupported Media Type</h1>")
            client_socket.sendall(response)
            print(f"415: Unsupported file type - {ext}")
            return
        
        # Read and send file
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        response = create_http_response(200, "OK", content_type, file_content)
        client_socket.sendall(response)
        print(f"200: Served {file_path}")
        
    except Exception as e:
        print(f"Error handling request: {e}")
        try:
            response = create_http_response(500, "Internal Server Error", "text/html",
                                           "<h1>500 Internal Server Error</h1>")
            client_socket.sendall(response)
        except:
            pass

def start_server(host, port, directory):
    """Start the HTTP server"""
    # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to address
    server_socket.bind((host, port))
    
    # Listen for connections
    server_socket.listen(5)
    
    print(f"Server started on {host}:{port}")
    print(f"Serving directory: {os.path.abspath(directory)}")
    print("Press Ctrl+C to stop the server")
    
    try:
        while True:
            # Accept client connection
            client_socket, client_address = server_socket.accept()
            print(f"\nConnection from {client_address}")
            
            # Handle request
            handle_request(client_socket, directory)
            
            # Close connection
            client_socket.close()
    
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python server.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)
    
    HOST = '0.0.0.0'  # Listen on all interfaces
    PORT = 8080
    
    start_server(HOST, PORT, directory)