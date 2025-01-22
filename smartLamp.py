import socket
import time
from datetime import datetime
import devices_pb2
import struct
import uuid
import threading

MULTICAST_GROUP = '224.1.1.1'
PORT = 10000

DEVICE_ID = f"LAMP__{uuid.uuid4().hex[:8]}"

#inicial conditions
lower_limit_time = datetime.strptime("06:00:00", "%H:%M:%S").time()
upper_limit_time = datetime.strptime("18:00:00", "%H:%M:%S").time()
lamp_state = "off"


def discover_servers():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    
    message = "DISCOVER_LAMP"
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


def update_state(client_socket):
    "Thread to turn on/ioff automatically"
    try:
        while True:        
            current_time = datetime.now().time()
            time_data = devices_pb2.DeviceData()
            time_data.current_time = current_time.strftime("%H%M%S")
            time_data.upper_limit = upper_limit_time.strftime("%H%M%S")
            time_data.lower_limit = lower_limit_time.strftime("%H%M%S")
            client_socket.send(time_data.SerializeToString())
            print(f"Sent time: {current_time}")
            global lamp_state


            if time_data.lower_limit <= current_time.strftime("%H%M%S") < time_data.upper_limit:
                action = "on"
            else:
                action = "off"

            if action != lamp_state:
                lamp_state = action

                command_data = devices_pb2.DeviceCommand()
                command_data.action = action
                command_data.value = lamp_state

                client_socket.send(command_data.SerializeToString())
                print(f"Turned {action} by limit time at {current_time}")

            time.sleep(10)

    except Exception as e:
        print(f"Error updating state: {e}")
    finally:
        client_socket.close()

def receive_commands(client_socket):
    "Thread to receive server commands"
    try:
        while True:
            server_data = client_socket.recv(1024)
            server_command = devices_pb2.DeviceCommand()
            server_command.ParseFromString(server_data)

            if server_command.action == "on" and lamp_state == "off":
                lamp_state = "on"
                print("Lamp turned ON by server command.")
                
            elif server_command.action == "off" and lamp_state == "on":
                lamp_state = "off"
                print("Lamp turned OFF by server command.")

            elif server_command.action == "shutdown":
                print(f"Shutting down device as per server request.")
                break
                
            if is_valid_time_format(server_command.set_upper_limit):
                upper_limit_time = datetime.strptime(f"{server_command.set_upper_limit}", "%H:%M:%S").time()
                print(f"Time limit to turn off the lamp setted to {upper_limit_time}")
          
            if is_valid_time_format(server_command.set_lower_limit):
                lower_limit_time = datetime.strptime(f"{server_command.set_lower_limit}", "%H:%M:%S").time()
                print(f"Time limit to turn on the lamp setted to {lower_limit_time}")
    
    except Exception as e:
        print(f"Error receiving command: {e}")
    finally:
        client_socket.close()
        print(f"Device {DEVICE_ID} disconnected.")


def start_client(host, port):
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    client_socket.send(b"DEVICETYPE_SMARTLAMP")
    
    # Inicia threads para envio de temperatura e recepção de comandos
    threading.Thread(target=update_state, args=(client_socket,)).start()
    threading.Thread(target=receive_commands, args=(client_socket,)).start()

      
def is_valid_time_format(time_string):
    try:
        datetime.strptime(time_string, "%H%M%S")
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    while True:
        host, port = discover_servers()
        if host and port: 
            start_client(host, port)
            break  
        else:
            print("No server found. Retrying in 5 seconds...")
            time.sleep(5)  