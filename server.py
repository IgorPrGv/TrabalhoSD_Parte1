import socket
import threading
import struct
import devices_pb2
import time

MULTICAST_GROUP = '224.1.1.1'
MULTICAST_PORT = 10000
TCP_PORT = 10001

devices = {}  # Para armazenar os dispositivos conectados

def multicast_discovery():
    """Servidor multicast para descoberta de dispositivos."""
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

                # Envia a resposta de volta com o IP e a porta TCP
                response = f"{socket.gethostbyname(socket.gethostname())}:{TCP_PORT}"
                sock.sendto(response.encode('utf-8'), address)
                
        except Exception as e:
            print(f"Error handling discovery message: {e}")

def handle_device_connection(client_socket, device_type):
    """Função para adicionar o dispositivo ao dicionário após a conexão TCP."""
    device_id = f"{device_type}_{len(devices) + 1}"
    devices[device_id] = {"socket": client_socket, "type": device_type, "state": "active"}
    print(f"Device {device_id} connected.")

def handle_client_connection(client_socket,data):
    """Função para lidar com conexões de cliente (não dispositivos)."""
    try:
        try:
            command = devices_pb2.ClientCommand()
            command.ParseFromString(data)
            print(f"Received command: {command.action}")

            if command.action.startswith("send"):
                device_id = command.target_device
                print("mando u comandu")
                send_command_to_device(client_socket, command.action, device_id)

            elif command.action == "list":
                list_devices(client_socket)

            elif command.action == "shutdown_gateway":
                shutdown_gateway(client_socket)

        except Exception as e:
            print(f"Error parsing client command: {e}")
            client_socket.send(b"Invalid command format")

    except Exception as e:
        print(f"Error with client: {e}")
        
    finally:
        client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', TCP_PORT))
    server_socket.listen(5)
    print(f"TCP server running on port {TCP_PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        # Recebe o tipo do dispositivo ou cliente
        data = client_socket.recv(1024)
        print(f"{data}")
        if data:
            message = data.decode('utf-8')
            if message.startswith("DEVICETYPE_"):  # Se for um dispositivo
                device_type = message.split("_", 1)[1]
                print(f"Device type received: {device_type}")
                handle_device_connection(client_socket, device_type)
            else:
                print("Client connected.")
                threading.Thread(target=handle_client_connection, args=(client_socket,data)).start()
        else:
            client_socket.close()
            print("No device or client type received, closing connection.")

def list_devices(client_socket):
    """Função para listar dispositivos conectados."""
    if not devices:  
        # Mensagem clara para o cliente
        message = "Nenhum dispositivo listado.\n"
        client_socket.send(message.encode('utf-8'))
        print("No devices connected.")
    else:
        # Formata as informações dos dispositivos
        device_info_message = []
        for device_id, info in devices.items():
            device_info_message.append(
                f"Device ID: {device_id}\n"
                f"Type: {info['type']}\n"
                f"State: {info['state']}\n"
            )
        
        # Adiciona separadores entre dispositivos
        formatted_message = "\n".join(device_info_message)
        client_socket.send(formatted_message.encode('utf-8'))
        print(f"Sent device list to client:\n{formatted_message}")

def send_command_to_device(client_socket, command, device_id):
    """Envia o comando para o dispositivo correto (TV ou Sensor de Temperatura)."""
    if device_id in devices and devices[device_id]["state"] == "active":
        device_socket = devices[device_id]["socket"]
        device_type = devices[device_id]["type"]
        device_address = devices[device_id]["addresss"]

        if device_type == "TV":
            # Verifica se é um comando para a TV e serializa corretamente
            if isinstance(command, devices_pb2.TVCommand):
                serialized_command = command.SerializeToString()  # Serializa o comando TVCommand
                device_socket.sendto(serialized_command,device_address)
                response = f"TV Command sent to {device_id}"
            else:
                response = f"Invalid command for TV: {command.action}"

        elif device_type == "TEMPERATURE_SENSOR":
            # Verifica se é um comando para o sensor de temperatura e serializa corretamente
            if isinstance(command, devices_pb2.TemperatureCommand):
                serialized_command = command.SerializeToString()  # Serializa o comando TemperatureCommand
                device_socket.sendto(serialized_command,device_address)
                response = f"Temperature Command sent to {device_id}"
            else:
                response = f"Invalid command for Temperature Sensor: {command.action}"

        else:
            response = f"Unsupported device type: {device_type}."

    else:
        response = f"Device {device_id} not found or disconnected."
    
    # Envia a resposta de volta para o cliente
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

if __name__ == "__main__":
    threading.Thread(target=multicast_discovery).start()
    start_server()
