"""
Simple HTTPS server for serving the Mini App
"""
import ssl
import http.server
import socketserver
import os

# Change to the mini_app directory
os.chdir('mini_app')

# Create SSL context (self-signed certificate for testing)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('cert.pem', 'key.pem')

# Create HTTP server
handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(("0.0.0.0", 8443), handler)

# Wrap with SSL
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print("Serving HTTPS on port 8443...")
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nShutting down...")
    httpd.server_close()