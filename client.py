import socket

HOST = '127.0.0.1'  # Or change to remote host if not local
PORT = 5050         # Must match server's port

def main():
    with socket.create_connection((HOST, PORT)) as sock:
        print(f"[CLIENT] Connected to {HOST}:{PORT}")
        buffer = b""
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                print("[CLIENT] Disconnected")
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                print("[DATA]", line.decode().strip())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[CLIENT] Farewell, quitting now.")
