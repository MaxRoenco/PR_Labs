#!/usr/bin/env python3
"""
Automated test script for HTTP server
Run this after starting your server to verify all features work
"""

import socket
import time
import os

def test_request(host, port, path, expected_status):
    """Send HTTP request and check status code"""
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Connect
        sock.connect((host, port))
        
        # Send request
        request = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        sock.sendall(request.encode())
        
        # Receive response
        response = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        
        sock.close()
        
        # Parse status code
        status_line = response.split(b'\r\n')[0].decode('utf-8')
        status_code = int(status_line.split()[1])
        
        # Check result
        if status_code == expected_status:
            return True, status_code, len(response)
        else:
            return False, status_code, len(response)
    
    except Exception as e:
        return False, 0, str(e)

def print_test_result(test_name, passed, details=""):
    """Print test result with formatting"""
    if passed:
        print(f"✓ {test_name:<40} PASSED {details}")
    else:
        print(f"✗ {test_name:<40} FAILED {details}")

def main():
    HOST = 'localhost'
    PORT = 8080
    
    print("="*70)
    print("HTTP Server Test Suite")
    print("="*70)
    print(f"Testing server at {HOST}:{PORT}")
    print()
    
    # Wait a moment for server to be ready
    time.sleep(1)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Homepage (HTML)
    tests_total += 1
    passed, status, size = test_request(HOST, PORT, '/', 200)
    print_test_result("Test 1: Homepage (HTML)", passed, f"[Status: {status}, Size: {size} bytes]")
    if passed:
        tests_passed += 1
    
    # Test 2: 404 Not Found
    tests_total += 1
    passed, status, size = test_request(HOST, PORT, '/nonexistent.pdf', 404)
    print_test_result("Test 2: 404 Not Found", passed, f"[Status: {status}]")
    if passed:
        tests_passed += 1
    
    # Test 3: PDF file
    tests_total += 1
    passed, status, size = test_request(HOST, PORT, '/document1.pdf', 200)
    print_test_result("Test 3: PDF file", passed, f"[Status: {status}, Size: {size} bytes]")
    if passed:
        tests_passed += 1
    
    # Test 4: PNG image
    tests_total += 1
    passed, status, size = test_request(HOST, PORT, '/logo.png', 200)
    print_test_result("Test 4: PNG image", passed, f"[Status: {status}, Size: {size} bytes]")
    if passed:
        tests_passed += 1
    
    # Test 5: Directory listing
    tests_total += 1
    passed, status, size = test_request(HOST, PORT, '/books/', 200)
    print_test_result("Test 5: Directory listing", passed, f"[Status: {status}, Size: {size} bytes]")
    if passed:
        tests_passed += 1
    
    # Test 6: Nested directory file
    tests_total += 1
    passed, status, size = test_request(HOST, PORT, '/books/book1.pdf', 200)
    print_test_result("Test 6: Nested directory file", passed, f"[Status: {status}, Size: {size} bytes]")
    if passed:
        tests_passed += 1
    
    # Summary
    print()
    print("="*70)
    print(f"Test Results: {tests_passed}/{tests_total} passed")
    
    if tests_passed == tests_total:
        print("🎉 All tests passed! Your server is working correctly.")
    else:
        print("⚠️  Some tests failed. Check your server implementation.")
    
    print("="*70)
    print()
    
    # Additional checks
    print("Additional Checks:")
    print()
    
    # Check if content directory has required files
    required_files = [
        'content/index.html',
        'content/logo.png',
        'content/document1.pdf',
        'content/books/'
    ]
    
    print("File Structure Check:")
    all_files_exist = True
    for file_path in required_files:
        exists = os.path.exists(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
        if not exists:
            all_files_exist = False
    
    print()
    
    if not all_files_exist:
        print("⚠️  Some required files are missing. Add them to pass all tests.")
    
    # Check Docker setup
    print("Docker Setup Check:")
    docker_files = ['Dockerfile', 'docker-compose.yml']
    for file_path in docker_files:
        exists = os.path.exists(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
    
    print()
    print("="*70)
    
    # Client test suggestion
    print()
    print("Next Steps:")
    print("1. Test the client:")
    print("   python client.py localhost 8080 /document1.pdf ./downloads")
    print()
    print("2. Take screenshots for your report")
    print()
    print("3. Test with a friend's server on the same network")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nError running tests: {e}")
        print("Make sure the server is running: docker-compose up")