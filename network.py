import sys
import socket

if __name__ == "__main__":
    user_input = sys.argv

    # star_node will have <name> and <local_port>
    star_node = (user_input[0], user_input[1])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if len(user_input) == 5:
        