import socket
import time
import random
import struct
import devices_pb2
import threading

MULTICAST_GROUP = '224.1.1.1'
PORT = 10000
DEVICE_ID = "TEMPERATURE_SENSOR"

# Temperatura inicial
temperature = {"value": 22.0}

def discover_servers():
    """Função para descobrir servidores via multicast."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    message = "DISCOVER_TEMPERATURE"
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

def send_temperature(client_socket):
    """Thread para enviar temperatura ao servidor periodicamente."""
    try:
        while True:
            # Cria e envia os dados de temperatura
            temperature_data = devices_pb2.DeviceData()
            temperature_data.device_id = DEVICE_ID
            temperature_data.current_measurement = temperature["value"]

            client_socket.send(temperature_data.SerializeToString())
            print(f"Sent temperature: {temperature['value']:.2f}°C from {DEVICE_ID}")

            # Atualiza a temperatura local com uma flutuação aleatória
            temperature["value"] += random.uniform(-0.5, 0.5)
            time.sleep(5)  # Envia a cada 5 segundos
    except Exception as e:
        print(f"Error sending temperature: {e}")
    finally:
        client_socket.close()

def receive_commands(client_socket):
    """Thread para receber comandos do servidor."""
    try:
        while True:
            print("uaiou tru")
            command_data = client_socket.recv(1024)
            print(f"{command_data}")
            if command_data:
                # Processa o comando recebido
                command = devices_pb2.DeviceCommand()
                command.ParseFromString(command_data)
                print(f"Server command: {command.action}")

                if command.action == "increase":
                    temperature["value"] += 1.0
                    print("Increasing temperature by 1°C.")
                elif command.action == "decrease":
                    temperature["value"] -= 1.0
                    print("Decreasing temperature by 1°C.")
                elif command.action == "shutdown":
                    print(f"Shutting down device as per server request.")
                    break
    except Exception as e:
        print(f"Error receiving command: {e}")
    finally:
        client_socket.close()
        print(f"Device {DEVICE_ID} disconnected.")

def start_device(host, port):
    """Inicia o dispositivo de temperatura."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    client_socket.send(b"DEVICETYPE_TEMPERATURE_SENSOR")

    # Inicia threads para envio de temperatura e recepção de comandos
    threading.Thread(target=send_temperature, args=(client_socket,)).start()
    threading.Thread(target=receive_commands, args=(client_socket,)).start()

if __name__ == "__main__":
    while True:
        host, port = discover_servers()
        if host and port: 
            start_device(host, port)
            break  
        else:
            print("No server found. Retrying in 5 seconds...")
            time.sleep(5)
