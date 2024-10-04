import sys
import socket
from urllib.parse import urlparse, urljoin
import re

# Get urls_file name from command line
if len(sys.argv) != 2:
    print('Usage: monitor urls_file')
    sys.exit()

urls_file = sys.argv[1]


# Function to create and return a TCP connection
def create_tcp_connection(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        return sock
    except Exception as e:
        print(f"Network Error:\n {e}")
        return None


# Function to send HTTP request and receive response
def send_http_request(sock, host, path):
    request = f"GET {path} HTTP/1.0\r\n"
    request += f"Host: {host}\r\n"
    request += "\r\n"

    try:
        sock.send(bytes(request, 'utf-8'))
        response = b""
        while True:
            data = sock.recv(4096)
            if not data:
                break
            response += data
        return response.decode('utf-8')
    except Exception as e:
        print(f"Error while receiving data: {e}")
        return None


# Function to extract the status code from the response
def extract_status(response):
    lines = response.split("\r\n")
    status_line = lines[0]  # The first line contains the status
    parts = status_line.split(" ")
    status_code = int(parts[1])
    status_text = " ".join(parts[2:])
    return status_code, status_text


# Function to extract the "Location" header for redirection
def get_redirect_location(response):
    lines = response.split("\r\n")
    for line in lines:
        if line.lower().startswith("location:"):
            return line.split(": ")[1]
    return None


# Function to extract image URLs from HTML content
def extract_image_urls(html_content, base_url):
    image_urls = []
    img_tags = re.findall(r'<img\s+[^>]*src="([^"]+)"', html_content, re.IGNORECASE)
    for img_url in img_tags:
        # Handle relative URLs
        full_img_url = urljoin(base_url, img_url)
        image_urls.append(full_img_url)
    return image_urls


# Function to process each URL and handle redirection if necessary
def process_url(url):
    url = url.strip()
    parsed_url = urlparse(url)

    protocol = parsed_url.scheme
    host = parsed_url.netloc
    path = parsed_url.path if parsed_url.path else '/'

    if protocol == 'http':
        port = 80
    elif protocol == 'https':
        port = 443
        # For HTTPS, we need to wrap the socket with SSL
        import ssl
        context = ssl.create_default_context()
    else:
        print(f"Unknown protocol for URL: {url}")
        return

    # Create TCP connection
    sock = create_tcp_connection(host, port)
    if sock:
        if protocol == 'https':
            # Wrap the socket with SSL for HTTPS
            sock = context.wrap_socket(sock, server_hostname=host)

        # Send HTTP request and receive response
        response = send_http_request(sock, host, path)
        sock.close()

        if response:
            # Extract the status code and text
            status_code, status_text = extract_status(response)
            print(f"URL: {url}")
            print(f"Status: {status_code} {status_text}")

            # Handle redirection if status code is 301 or 302
            if status_code in [301, 302]:
                redirect_url = get_redirect_location(response)
                if redirect_url:
                    print(f"Redirected URL: {redirect_url}")
                    process_url(redirect_url)
                else:
                    print(f"Error: No 'Location' header for redirection")
            else:
                # Extract and process referenced images from the HTML content (for 2XX status codes)
                if status_code in range(200, 300):
                    base_url = f"{protocol}://{host}"
                    image_urls = extract_image_urls(response, base_url)
                    for img_url in image_urls:
                        print(f"Referenced URL: {img_url}")
                        process_url(img_url)  # Fetch the referenced image URL

        else:
            print(f"Error: No response received for URL: {url}")
    else:
        print(f"Could not connect to {url}")


# Read URLs from the file
with open(urls_file, 'r') as file:
    urls = file.readlines()

# Process each URL
for url in urls:
    process_url(url)
