import socket
import sys
import os

def parse_http_response(response_data):
    """Parse HTTP response into status, headers, and body"""
    # Split headers and body
    parts = response_data.split(b'\r\n\r\n', 1)
    
    if len(parts) != 2:
        return None, None, None
    
    header_section = parts[0].decode('utf-8', errors='ignore')
    body = parts[1]
    
    # Parse status line
    lines = header_section.split('\r\n')
    status_line = lines[0].split(' ', 2)
    
    if len(status_line) < 3:
        return None, None, None
    
    status_code = int(status_line[1])
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()
    
    return status_code, headers, body

def send_http_request(host, port, path):
    """Send HTTP GET request and return response"""
    try:
        # Create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)
        
        # Connect to server
        client_socket.connect((host, port))
        
        # Create HTTP GET request
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"
        
        # Send request
        client_socket.sendall(request.encode('utf-8'))
        
        # Receive response
        response_data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response_data += chunk
        
        client_socket.close()
        
        return response_data
    
    except socket.timeout:
        print("Error: Connection timed out")
        return None
    except ConnectionRefusedError:
        print("Error: Connection refused. Is the server running?")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_filename_from_path(path):
    """Extract filename from URL path"""
    filename = path.split('/')[-1]
    if not filename:
        filename = 'index.html'
    return filename

def get_content_type(headers, filename):
    """Determine content type from headers or filename"""
    # Check Content-Type header
    if 'content-type' in headers:
        content_type = headers['content-type'].lower()
        
        if 'text/html' in content_type:
            return 'html'
        elif 'application/pdf' in content_type:
            return 'pdf'
        elif 'image/png' in content_type:
            return 'png'
    
    # Fallback to file extension
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.html':
        return 'html'
    elif ext == '.pdf':
        return 'pdf'
    elif ext == '.png':
        return 'png'
    
    return 'unknown'

def main():
    if len(sys.argv) != 5:
        print("Usage: python client.py <server_host> <server_port> <url_path> <directory>")
        print("Example: python client.py localhost 8080 /document.pdf ./downloads")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    path = sys.argv[3]
    save_directory = sys.argv[4]
    
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    
    # Create save directory if it doesn't exist
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
        print(f"Created directory: {save_directory}")
    
    print(f"Requesting: http://{host}:{port}{path}")
    
    # Send request
    response_data = send_http_request(host, port, path)
    
    if response_data is None:
        sys.exit(1)
    
    # Parse response
    status_code, headers, body = parse_http_response(response_data)
    
    if status_code is None:
        print("Error: Failed to parse response")
        sys.exit(1)
    
    print(f"Status: {status_code}")
    
    if status_code != 200:
        print(f"Error: Server returned status {status_code}")
        print("Response body:")
        print(body.decode('utf-8', errors='ignore'))
        sys.exit(1)
    
    # Determine file type
    filename = get_filename_from_path(path)
    file_type = get_content_type(headers, filename)
    
    print(f"Content-Type: {headers.get('content-type', 'unknown')}")
    print(f"Detected type: {file_type}")
    
    # Handle based on file type
    if file_type == 'html':
        # Print HTML body
        print("\n" + "="*50)
        print("HTML CONTENT:")
        print("="*50)
        print(body.decode('utf-8', errors='ignore'))
        print("="*50)
    
    elif file_type in ['pdf', 'png']:
        # Save file
        save_path = os.path.join(save_directory, filename)
        
        with open(save_path, 'wb') as f:
            f.write(body)
        
        print(f"\nFile saved to: {save_path}")
        print(f"Size: {len(body)} bytes")
    
    else:
        print(f"\nUnknown file type. Saving as: {filename}")
        save_path = os.path.join(save_directory, filename)
        
        with open(save_path, 'wb') as f:
            f.write(body)
        
        print(f"File saved to: {save_path}")

if __name__ == "__main__":
    main()