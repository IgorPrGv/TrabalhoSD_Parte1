import socket
import time
from datetime import datetime
import devices_pb2
import struct

MULTICAST_GROUP = '224.1.1.1'
PORT = 10000

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

def start_client(host, port):
    lower_limit_time = datetime.strptime("06:00:00", "%H:%M:%S").time()
    upper_limit_time = datetime.strptime("18:00:00", "%H:%M:%S").time()

    lamp_state = "off"

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    try:
        while True:
            current_time = datetime.now().time()
            time_data = devices_pb2.TimeData()
            time_data.current_time = current_time
            time_data.upper_limit_lamp = upper_limit_time 
            time_data.lower_limit_lamp = lower_limit_time 
            client_socket.send(command_data.SerializeToString())
            print(f"Sent time: {current_time}")


            if time_data.lower_limit_lamp <= current_time < time_data.upper_limit_lamp:
                action = "on"
            else:
                action = "off"

            if action != lamp_state:
                lamp_state = action

                command_data = devices_pb2.LampCommand()
                command_data.action = action
                command_data.lamp_state = lamp_state

                client_socket.send(command_data.SerializeToString())
                print(f"Sent command: turn {action} by limit time at {current_time}")

            server_data = client_socket.recv(1024)
            server_command = devices_pb2.LampCommand()
            server_command.ParseFromString(server_data)

            if server_command.action == "send: on" and lamp_state == "off":
                lamp_state = "on"
                print("Lamp turned ON by server command.")
                
            elif server_command.action == "send: off" and lamp_state == "on":
                lamp_state = "off"
                print("Lamp turned OFF by server command.")
                
                
            if is_valid_time_format(server_command.upper_limit_lamp):
                upper_limit_time = server_command.upper_limit_lamp
                print(f"Time limit to turn off the lamp setted to {upper_limit_time}")
          
            if is_valid_time_format(server_command.lower_limit_lamp):
                lower_limit_time = server_command.lower_limit_lamp
                print(f"Time limit to turn on the lamp setted to {lower_limit_time}")

            time.sleep(10)

    except KeyboardInterrupt:
        print("Stopping the client...")

    finally:
        client_socket.close()
        
      
def is_valid_time_format(time_string):
    try:

        datetime.strptime(time_string, "%H%M%S")
        return True
    except ValueError:
        return False


if __name__ == "_main_":
    while True:
        host, port = discover_servers()
        if host and port: 
            start_client(host, port)
            break  
        else:
            print("No server found. Retrying in 5 seconds...")
            time.sleep(5)  