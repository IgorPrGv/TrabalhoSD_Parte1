import socket
import threading
import struct
import devices_pb2
import time

MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 10000
TCP_PORT = 10001

devices = {}  

def multicast_discovery():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MULTICAST_PORT))

    group = socket.inet_aton(MULTICAST_GROUP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print("Multicast discovery server running...")

    while True:
        data, address = sock.recvfrom(1024)
        print(f"Received discovery message from {address}")
        try:
            message = data.decode('utf-8')
            if message.startswith("DISCOVER_"):
                device_type = message.split("_", 1)[1]
                if device_type not in ["TEMPERATURE", "TV", "LAMP"]:
                    print(f"Unknown device type: {device_type}")
                    continue

                # Send response back to the device
                response = f"{socket.gethostbyname(socket.gethostname())}:{TCP_PORT}"
                sock.sendto(response.encode('utf-8'), address)

                # Add device to the discovered list
                device_id = f"{device_type}_{len(devices) + 1}"
                devices[device_id] = {"address": address, "type": device_type, "state": "discovered"}
                print(f"Discovered device: {device_id}")
                            
        except Exception as e:
            print(f"Error handling discovery message: {e}")

def handle_device_connection(device_socket, device_type):
    device_id = f"{device_type}_{len(devices) + 1}"
    devices[device_id] = {"socket": device_socket, "type": device_type, "state": "active"}

    print(f"Device {device_id} connected.")

    try:
        while True:
            data = device_socket.recv(1024)
            if not data:
                break
            
            devices[device_id]["last_message"] = data
    except Exception as e:
        print(f"Error with {device_id}: {e}")
    finally:
        device_socket.close()
        devices[device_id]["state"] = "disconnected"
        print(f"Device {device_id} disconnected.")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', TCP_PORT))
    server_socket.listen(5)
    print(f"TCP server running on port {TCP_PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        threading.Thread(target=handle_client, args=(client_socket,)).start()


def list_devices(client_socket):
    """Função para listar dispositivos conectados."""
    response = devices_pb2.DeviceList()

    if not devices:  
        response = "Nenhum dispositivo listado."
    else:
        for device_id, info in devices.items():
            device_info = response.devices.add()
            device_info.device_id = device_id
            device_info.type = info["type"]
            device_info.state = info["state"]

    client_socket.send(response.SerializeToString() if isinstance(response, devices_pb2.DeviceList) else response.encode('utf-8'))

def send_command_to_device(client_socket, data, device_id):
    """Função para enviar um comando para o dispositivo."""
    if device_id in devices and devices[device_id]["state"] == "active":
        devices[device_id]["socket"].send(data)
        response = f"Command sent to {device_id}"
    else:
        response = f"Device {device_id} not found or disconnected."
    
    client_socket.send(response.encode('utf-8'))

def shutdown_device(client_socket, device_id):
    """Função para desligar um dispositivo."""
    if device_id in devices:
        devices[device_id]["state"] = "disconnected"
        devices[device_id]["socket"].close()
        response = f"Device {device_id} shut down."
    else:
        response = f"Device {device_id} not found."
    
    client_socket.send(response.encode('utf-8'))

def shutdown_gateway(client_socket):
    """Função para desligar o gateway."""
    print("Shutting down gateway...")
    client_socket.send(b"Gateway shutting down.")
    client_socket.close()
    exit(0)

def handle_client(client_socket):
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            command = devices_pb2.ClientCommand()
            command.ParseFromString(data)

            if command.action == "list_devices":
                list_devices(client_socket)
            elif command.action == "send":
                device_id = command.target_device
                send_command_to_device(client_socket, data, device_id)
            elif command.action == "shutdown_device":
                device_id = command.target_device
                shutdown_device(client_socket, device_id)
            elif command.action == "shutdown_gateway":
                shutdown_gateway(client_socket)
    except Exception as e:
        print(f"Error with client: {e}")
    finally:
        client_socket.close()


if __name__ == "__main__":
    threading.Thread(target=multicast_discovery).start()
    start_server()
