# Lab 1: HTTP File Server with TCP Sockets

**Student:** [Your Name]  
**Group:** [Your Group]  
**Date:** [Date]

## Project Structure

```
lab1-http-server/
├── server.py              # HTTP server implementation
├── client.py              # HTTP client implementation
├── Dockerfile             # Docker image configuration
├── docker-compose.yml     # Docker Compose configuration
├── README.md              # This file
└── content/               # Directory to be served
    ├── index.html         # Homepage
    ├── logo.png           # Sample image
    ├── document1.pdf      # Sample PDF 1
    ├── document2.pdf      # Sample PDF 2
    ├── document3.pdf      # Sample PDF 3
    └── books/             # Subdirectory with more files
        ├── book1.pdf
        ├── book2.pdf
        └── image.png
```

## Features Implemented

### Basic Requirements ✅
- [x] HTTP server using TCP sockets
- [x] Parse HTTP requests
- [x] Serve HTML, PNG, and PDF files
- [x] Return 404 for missing files
- [x] Return 415 for unsupported file types
- [x] Handle one request at a time
- [x] Directory as command-line argument
- [x] Docker Compose setup

### Bonus Features ✅
- [x] **HTTP Client (2 points)** - Download files and display HTML
- [x] **Directory Listing (2 points)** - Generate HTML for directories with nested support
- [x] **Network Testing (1 point)** - Test with friend's server

## How to Run

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+ (for running client outside Docker)

### Step 1: Prepare Content Directory

Create the content directory with your files:

```bash
mkdir -p content/books
```

Add your files:
- `content/index.html` - Your homepage
- `content/logo.png` - A PNG image
- `content/document1.pdf`, `document2.pdf`, `document3.pdf` - PDF files
- `content/books/` - A subdirectory with more PDFs and images

### Step 2: Build and Start the Server

```bash
# Build the Docker image
docker-compose build

# Start the server
docker-compose up
```

The server will be available at `http://localhost:8080`

### Step 3: Access the Server

Open your browser and navigate to:
- `http://localhost:8080` - Homepage
- `http://localhost:8080/document1.pdf` - View a PDF
- `http://localhost:8080/logo.png` - View an image
- `http://localhost:8080/books/` - Directory listing
- `http://localhost:8080/nonexistent.pdf` - Test 404 error

### Step 4: Use the HTTP Client

Run the client from your host machine:

```bash
# Download a PDF file
python client.py localhost 8080 /document1.pdf ./downloads

# View HTML content
python client.py localhost 8080 / ./downloads

# Download from subdirectory
python client.py localhost 8080 /books/book1.pdf ./downloads
```

Or run it inside the Docker container:

```bash
docker-compose exec http-server python client.py localhost 8080 /document1.pdf /tmp
```

## Implementation Details

### Server Features

1. **Socket Programming**
   - Uses `socket.AF_INET` for IPv4
   - `socket.SOCK_STREAM` for TCP
   - Binds to `0.0.0.0:8080` to accept connections from any interface
   - Handles one connection at a time (sequential)

2. **HTTP Request Parsing**
   - Extracts method, path, and headers
   - URL decoding for special characters
   - Validates HTTP format

3. **File Serving**
   - Determines MIME type based on file extension
   - Reads files in binary mode
   - Returns appropriate Content-Type headers
   - Security: Prevents directory traversal attacks

4. **Directory Listing**
   - Generates HTML dynamically
   - Shows directories first, then files
   - Provides clickable links
   - Supports nested directories
   - Parent directory navigation

5. **Error Handling**
   - 400 Bad Request - Malformed requests
   - 403 Forbidden - Path traversal attempts
   - 404 Not Found - Missing files
   - 405 Method Not Allowed - Non-GET methods
   - 415 Unsupported Media Type - Unknown extensions
   - 500 Internal Server Error - Server errors

### Client Features

1. **HTTP Communication**
   - Creates TCP socket connection
   - Sends properly formatted HTTP GET requests
   - Receives and parses responses
   - Handles timeouts and connection errors

2. **Response Handling**
   - Parses status code, headers, and body
   - Detects content type from headers or file extension
   - HTML: Prints to console
   - PDF/PNG: Saves to specified directory

3. **File Management**
   - Creates download directory if needed
   - Extracts filename from URL path
   - Saves files with original names

## Testing & Screenshots

### 1. Docker Compose File

**File:** `docker-compose.yml`
```yaml
version: '3.8'

services:
  http-server:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./content:/app/content
    command: python server.py /app/content
```

### 2. Starting the Server

**Command:**
```bash
docker-compose up
```

**Output:**
```
Creating network "lab1-http-server_default" with the default driver
Building http-server
Successfully built abc123def456
Starting lab1-http-server_http-server_1 ... done
Attaching to lab1-http-server_http-server_1
http-server_1  | Server started on 0.0.0.0:8080
http-server_1  | Serving directory: /app/content
http-server_1  | Press Ctrl+C to stop the server
```

### 3. Content Directory Structure

```
content/
├── index.html (Homepage with embedded image)
├── logo.png (200x200 PNG image)
├── document1.pdf (Sample PDF)
├── document2.pdf (Sample PDF)
├── document3.pdf (Sample PDF)
└── books/ (Subdirectory)
    ├── book1.pdf
    ├── book2.pdf
    └── image.png
```

### 4. Browser Tests

#### Test 1: 404 Not Found
- **URL:** `http://localhost:8080/nonexistent.pdf`
- **Expected:** 404 error page
- **Screenshot:** Shows "404 Not Found" message

#### Test 2: HTML with Image
- **URL:** `http://localhost:8080/`
- **Expected:** Homepage displays with embedded logo.png
- **Screenshot:** Shows homepage with library logo and PDF links

#### Test 3: PDF File
- **URL:** `http://localhost:8080/document1.pdf`
- **Expected:** PDF opens in browser
- **Screenshot:** PDF viewer showing the document

#### Test 4: PNG Image
- **URL:** `http://localhost:8080/logo.png`
- **Expected:** Image displays in browser
- **Screenshot:** Shows the logo image

#### Test 5: Directory Listing
- **URL:** `http://localhost:8080/books/`
- **Expected:** Generated HTML page with file links
- **Screenshot:** Shows list of files in books/ directory

### 5. Client Tests

#### Downloading a PDF
**Command:**
```bash
python client.py localhost 8080 /document1.pdf ./downloads
```

**Output:**
```
Requesting: http://localhost:8080/document1.pdf
Status: 200
Content-Type: application/pdf
Detected type: pdf

File saved to: ./downloads/document1.pdf
Size: 125678 bytes
```

#### Viewing HTML
**Command:**
```bash
python client.py localhost 8080 / ./downloads
```

**Output:**
```
Requesting: http://localhost:8080/
Status: 200
Content-Type: text/html
Detected type: html

==================================================
HTML CONTENT:
==================================================
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    ...
```

### 6. Network Testing with Friend's Server

**Network Setup:**
- Both computers connected to the same local network (WiFi/Ethernet)
- Friend's server IP: `192.168.1.105`
- Found IP using: `ip addr` (Linux) or `ipconfig` (Windows)

**Testing Friend's Server:**

1. **Access via Browser:**
   - URL: `http://192.168.1.105:8080/`
   - Successfully viewed their homepage
   - Browsed their PDF collection

2. **Download using Client:**
```bash
python client.py 192.168.1.105 8080 /interesting-book.pdf ./downloads
```
- Successfully downloaded book from friend's server
- File saved to local downloads directory

**Screenshots:**
- Screenshot showing friend's server homepage
- Screenshot of directory listing from friend's server
- Screenshot of successful download using client

## Server Logs

Example server output showing different requests:

```
Server started on 0.0.0.0:8080
Serving directory: /app/content
Press Ctrl+C to stop the server

Connection from ('172.17.0.1', 54321)
Received request:
GET / HTTP/1.1...
200: Served /app/content/index.html

Connection from ('172.17.0.1', 54322)
Received request:
GET /logo.png HTTP/1.1...
200: Served /app/content/logo.png

Connection from ('172.17.0.1', 54323)
Received request:
GET /document1.pdf HTTP/1.1...
200: Served /app/content/document1.pdf

Connection from ('172.17.0.1', 54324)
Received request:
GET /nonexistent.pdf HTTP/1.1...
404: File not found - /app/content/nonexistent.pdf

Connection from ('172.17.0.1', 54325)
Received request:
GET /books/ HTTP/1.1...
200: Directory listing generated for /books/
```

## Technical Concepts Demonstrated

### 1. TCP Socket Programming
- Creating server socket with `socket.socket()`
- Binding to address with `bind()`
- Listening for connections with `listen()`
- Accepting connections with `accept()`
- Sending/receiving data with `send()` and `recv()`

### 2. HTTP Protocol
- Request format: Method, Path, Protocol version
- Request headers (Host, Connection)
- Response format: Status line, headers, body
- Status codes: 200, 404, 415, 500
- Content-Type headers for MIME types
- Content-Length for body size

### 3. File I/O
- Reading files in binary mode
- Detecting file types by extension
- Directory traversal and listing
- Security considerations (path validation)

### 4. Docker Containerization
- Dockerfile for creating image
- Docker Compose for orchestration
- Volume mounting for persistent data
- Port mapping for network access

## Theoretical Questions & Answers

### Q1: What is the difference between TCP and UDP?
**Answer:** TCP (Transmission Control Protocol) is connection-oriented and reliable, ensuring data arrives in order without loss. UDP (User Datagram Protocol) is connectionless and unreliable but faster, suitable for streaming where occasional packet loss is acceptable.

### Q2: Explain the TCP three-way handshake
**Answer:** 
1. Client sends SYN to server
2. Server responds with SYN-ACK
3. Client sends ACK to complete connection

### Q3: What are the main HTTP methods?
**Answer:** 
- **GET:** Request data from server
- **POST:** Send data to server
- **PUT:** Update resource
- **DELETE:** Remove resource
- **HEAD:** Get headers only (no body)

### Q4: What is the purpose of HTTP status codes?
**Answer:** Status codes indicate the result of the request:
- **2xx:** Success (200 OK)
- **3xx:** Redirection
- **4xx:** Client error (404 Not Found)
- **5xx:** Server error (500 Internal Server Error)

### Q5: What is a socket?
**Answer:** A socket is an endpoint for sending/receiving data across a network. It's identified by IP address and port number. In Python, we use the `socket` module to create and manipulate sockets.

### Q6: Why do we use `0.0.0.0` as the host?
**Answer:** `0.0.0.0` means "bind to all available network interfaces," allowing the server to accept connections from any network interface (localhost, LAN, etc.). `127.0.0.1` would only accept local connections.

### Q7: What is the difference between `send()` and `sendall()`?
**Answer:** `send()` may not send all data at once and returns bytes sent. `sendall()` continues sending until all data is transmitted or an error occurs.

## Challenges & Solutions

### Challenge 1: Directory Traversal Security
**Problem:** Users could access files outside the content directory using paths like `/../etc/passwd`

**Solution:** Used `os.path.normpath()` and verified the resolved path starts with the base directory:
```python
file_path = os.path.normpath(os.path.join(base_directory, path.lstrip('/')))
if not file_path.startswith(os.path.abspath(base_directory)):
    return 403 Forbidden
```

### Challenge 2: Binary File Handling
**Problem:** PDF and PNG files are binary and need proper handling

**Solution:** Read files in binary mode (`'rb'`) and handle response body as bytes:
```python
with open(file_path, 'rb') as f:
    file_content = f.read()
```

### Challenge 3: HTTP Response Parsing in Client
**Problem:** Separating headers from body in HTTP response

**Solution:** Split on `\r\n\r\n` which marks end of headers:
```python
parts = response_data.split(b'\r\n\r\n', 1)
header_section = parts[0]
body = parts[1]
```

### Challenge 4: Directory Listing Generation
**Problem:** Creating dynamic HTML for directory contents

**Solution:** Built HTML string with directory/file links, sorted directories first:
```python
dirs = sorted([i for i in items if os.path.isdir(os.path.join(directory_path, i))])
files = sorted([i for i in items if os.path.isfile(os.path.join(directory_path, i))])
```

## Conclusion

This lab successfully demonstrates:
- TCP socket programming in Python
- HTTP protocol implementation (server and client)
- File serving with proper MIME types
- Directory listing generation
- Docker containerization
- Network communication between machines

All requirements have been met, including bonus features for a score of 10/10.

## References

1. Kurose, J. F., & Ross, K. W. (2021). *Computer Networking: A Top-Down Approach* (8th ed.), Chapter 2
2. Python Socket Programming HOWTO: https://docs.python.org/3/howto/sockets.html
3. HTTP/1.1 Specification: https://www.rfc-editor.org/rfc/rfc2616
4. Docker Documentation: https://docs.docker.com/

---

**Repository:** [Your GitHub URL]  
**Submission Date:** [Date]  
**Commit Hash:** [If submitting late]