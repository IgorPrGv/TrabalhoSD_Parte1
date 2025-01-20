import socket
import time
import random
import struct
import devices_pb2
import uuid

MULTICAST_GROUP = '224.1.1.1'
PORT = 10000
DEVICE_ID = f"TEMP_SENSOR_{uuid.uuid4().hex[:8]}"

def discover_servers():
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


def start_device(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    temperature = 22.0

    try:
        while True:
            temperature_data = devices_pb2.TemperatureData()
            temperature_data.device_id = DEVICE_ID
            temperature_data.current_temperature = temperature

            client_socket.send(temperature_data.SerializeToString())
            print(f"Sent temperature: {temperature}°C from {DEVICE_ID}")


            command_data = client_socket.recv(1024)
            if not command_data: 
                print(f"Server disconnected.")
                break
            
            command = devices_pb2.TemperatureCommand()
            command.ParseFromString(command_data)
            print(f"Server command: {command.action} to {command.value}°C")

            if command.action == "send: increase":
                temperature += 1.0
            elif command.action == "send: decrease":
                temperature -= 1.0
            elif "shut" in command.action:
                print(f"Shutting down device as per server request.")
                break

            temperature += random.uniform(-0.5, 0.5)
            time.sleep(10)

    except KeyboardInterrupt:
        print("Stopping the device...")
    
    finally:
        client_socket.close()
        print(f"Device {DEVICE_ID} disconnected.")

if __name__ == "__main__":
    while True:
        host, port = discover_servers()
        if host and port: 
            start_device(host, port)
            break  
        else:
            print("No server found. Retrying in 5 seconds...")
            time.sleep(5)  