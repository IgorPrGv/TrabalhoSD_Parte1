import socket
import devices_pb2


def connect_to_gateway():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", 10001))
    # sock.send("client".encode('utf-8'))
    return sock

def list_devices(sock):
    send_command(sock, "list_devices")


def send_device_command(sock):
    device_id = input("Enter device ID: ").strip()
    action = input("Enter command action: ").strip()
    send_command(sock, action, target_device=device_id)


def shutdown_device(sock):
    device_id = input("Enter device ID: ").strip()
    send_command(sock, "shutdown_device", target_device=device_id)

def shutdown_gateway(sock):
    send_command(sock, "shutdown_gateway")
    print("Gateway shutting down...")


def send_command(sock, action, target_device=None):
    command = devices_pb2.ClientCommand()
    command.action = action
    if target_device:
        command.target_device = target_device

    try:
        sock.send(command.SerializeToString())
        response = sock.recv(1024)
        print(f"Response: {response.decode('utf-8')}")
    except Exception as e:
        print(f"Error sending command: {e}")


def print_menu_options(sock):
    print("\nOpções:\n")
    print("list: Listar quais dispositivos estão conectados")
    print("send: Enviar um comando para o dispositivo")
    print("shutdown_device: Desligar um dos dispositivos")
    print("shutdown_gateway: Desligar o gateway")
    print("exit: Fechar o programa")


if __name__ == "__main__":
    gateway_socket = connect_to_gateway()

    menu_options = {
        "man": print_menu_options,
        "list": list_devices,
        "send": send_device_command,
        "shutdown_device": shutdown_device,
        "shutdown_gateway": shutdown_gateway,
        "exit": lambda sock: print("Exiting...")
    }

    while True:
        choice = input("$ ").strip()

        if choice in menu_options:
            if choice == "exit":
                menu_options[choice](gateway_socket)
                break
            else:
                menu_options[choice](gateway_socket)
        else:
            print("Invalid option. Please try again.")
