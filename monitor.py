import sys
import socket
from urllib.parse import urlparse
import re

def create_connection(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        return sock
    except Exception as e:
        return None

def status_code(response):
    lines = response.split("\r\n")
    status_line = lines[0]
    parts = status_line.split(" ")
    code = int(parts[1])
    status_text = " ".join(parts[2:])
    return code, status_text

def get_image_url(response, base_url):
    img_tags = re.findall(r'<img\s+[^>]*src="([^"]+)"', response, re.IGNORECASE)
    for tag in img_tags:
        if tag.startswith("/"):
            return base_url+tag
        else:
            return tag
    return None


def get_redirect(response):
    lines = response.split("\r\n")
    for line in lines:
        if line.startswith("Location:"):
            parts = line.split(" ")
            return parts[1]
    return None

def receive_full_response(sock):
    response = b''
    while True:
        data = sock.recv(4096)
        response += data
        if not data:
            break
    return response.decode()


def send_request(sock, host, path):
    request = f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n"
    try:
        sock.sendall(request.encode())
        response = receive_full_response(sock)
        return response
    except Exception as e:
        return None


def process_url(url):
    url = url.strip()
    parsed_url = urlparse(url)

    protocol = parsed_url.scheme
    host = parsed_url.netloc
    path = parsed_url.path if parsed_url.path else '/'

    port = 443 if protocol == 'https' else 80
    sock = create_connection(host, port)

    print(f"URL: {url}")
    if sock is None:
        print("Status: Network Error")
        print()
        return

    response = send_request(sock, host, path)
    if response:
        code, status = status_code(response)
        print(f"Status: {code} {status}")

        new_url = None
        if code in [301, 302]:
            redirect_url = get_redirect(response)
            print(f"Redirected URL: {redirect_url}")
            new_url = redirect_url

        else:
            # see if there is anything referenced in the response
            image_url = get_image_url(response, f'{protocol}://{host}')
            if image_url:
                print(f"Referenced URL: {image_url}")
                new_url = image_url

        if new_url:
            parsed_new = urlparse(new_url)

            protocol = parsed_new.scheme
            host = parsed_new.netloc
            path = parsed_new.path if parsed_new.path else '/'

            port = 443 if protocol == 'https' else 80
            sock = create_connection(host, port)
            if sock is None:
                print("Status: Network Error")
                print()
                return
            response = send_request(sock, host, path)
            if response:
                code, status = status_code(response)
                print(f"Status: {code} {status}")
            else:
                print("Status: Network Error")

    else:
        print("Status: Network Error")

    sock.close()
    # New Line
    print()

def main():
    # get urls_file name from command line
    if len(sys.argv) != 2:
        print('Usage: monitor urls_file')
        sys.exit()

    # text file to get list of urls
    urls_file = sys.argv[1]

    try:
        with open(urls_file) as f:
            urls = f.readlines()
    except Exception as e:
        print(f'Error reading file: {e}')
        sys.exit()

    for url in urls:
        process_url(url)


if __name__ == '__main__':
    main()
