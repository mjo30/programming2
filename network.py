import sys
import socket

from packet import Packet

if __name__ == "__main__":
    user_input = sys.argv

    # star_node will have <name> and <local_port>
    N = int(user_input[4])
    source_port = user_input[1]
    name = user_input[0]

    while len(source_port) != 5:
        source_port = "0" + source_port

    star_node = (name, source_port)

    src_ip = socket.gethostbyname()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((src_ip, int(source_port)))

    poc_list = set()
    poc_list.add((name, src_ip, source_port))

    packet_id = 0

    while len(poc_list) < N:
        if len(user_input) == 5:
            dest_port = user_input[3]
            dest_ip = user_input[2]
            packet = Packet(1, poc_list, source_port, dest_port, source_port + str(packet_id))
            sock.sendto(packet, (dest_ip, int(dest_port)))

        recv_packet, address = sock.recvfrom(512000)
        recv_data = recv_packet.data
        print(recv_data)

        recv_data = recv_data.difference(poc_list)

        for node in recv_data:
            dest_port = node[2]
            dest_ip = node[1]
            packet = Packet(1, poc_list, source_port, dest_port, source_port + str(packet_id))
            sock.sendto(packet, (dest_ip, int(dest_port)))






