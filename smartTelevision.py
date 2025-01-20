import socket
import devices_pb2
import time
import struct

MULTICAST_GROUP = '224.1.1.1'
PORT = 10000


def discover_servers():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    

    message = "DISCOVER_TV"
    print(f"Sending discovery message...")
    sock.sendto(message.encode('utf-8'), (MULTICAST_GROUP, PORT))
    sock.settimeout(5)
    try:
        data, address = sock.recvfrom(1024)
        print(f"Received response: {data.decode('utf-8')} from {address}")
        host, port = data.decode('utf-8').split(":")
        return host, int(port)
    except socket.timeout:
        print(f"Discovery timed out.")
        return None, None
    finally:
        sock.close()

def start_device(host, port):
    tv_state = {
        "power": False,
        "mode": None,  
        "now": None
    }

    device_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    device_socket.connect((host, port))

    try:
        while True:
            
            command_data = device_socket.recv(1024)
            print("teve resebeuson")
            if not command_data:
                break

            command = devices_pb2.TVCommand()
            command.ParseFromString(command_data)
            
            if command.action == "send: on":
                tv_state["power"] = True
                print("TV Ligada.")

            elif command.action == "send: off":
                tv_state["power"] = False
                tv_state["mode"] = None
                tv_state["now"] = None
                print("TV Desligada.")

            elif command.action == "send: cable" and tv_state["power"]:
                tv_state["mode"] = "cable"
                tv_state["now"] = command.value
                print(f"Assistindo canal a cabo: {command.value}")

            elif command.action == "send: streaming" and tv_state["power"]:
                tv_state["mode"] = "streaming"
                tv_state["now"] = command.value
                print(f"Assistindo streaming: {command.value}")

            else:
                print("Comando inválido ou TV está desligada.")

    except KeyboardInterrupt:
        print("Encerrando dispositivo...")
    finally:
        device_socket.close()

if __name__ == "__main__":
    while True:
        host, port = discover_servers()
        if host and port: 
            start_device(host, port)
            break  
        else:
            print("No server found. Retrying in 5 seconds...")
            time.sleep(5)  
