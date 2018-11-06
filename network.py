import socketserver
import sys
import socket
import threading


class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # data is the packet to deliver
        data = self.request[0].strip()
        socket = self.request[1]
        socket.sendto(data.upper(), self.client_address)


# def find_poc():

# Packet Structure
# 0-5 Length
# 6 Header
# 7-16 Packet ID
# 17-21 Source Port
# 22-26 Destination Port
# 27-31 RTT
# 32-
def create_packet(header, data, source_port, dest_port, id, rtt):
    # change data to string
    data_string = ""
    for (n, i, p) in data:
        data_string = data_string + n + " " + i + " " + p + " "

    # pad source_port to be length 5
    while len(source_port) != 5:
        source_port = "0" + source_port

    # pad dest_port to be length 5
    while len(dest_port) != 5:
        dest_port = "0" + dest_port

    # pad id to be length 10
    while len(id) != 10:
        id = "0" + id

    # pad rtt to be length 5
    rtt = str(rtt)
    while len(rtt) != 5:
        rtt = "0" + rtt

    length = len(data_string) + 1 + 10 + 5 + 5 + 5 + 5

    # pad length_str to be length 5
    length_str = str(length)
    while len(length_str) != 5:
        length_str = "0" + length_str

    data_string = length_str + header + id + source_port + dest_port + rtt + data_string
    arr = bytearray(length)
    for i in range(length):
        arr[i] = ord(data_string[i])
    return arr


if __name__ == "__main__":
    # user_input is the parameters user passed in
    user_input = sys.argv

    # N is number of total nodes
    # if the node does not have PoC, it has user_input length of 4 / else 6
    if len(user_input) == 4:
        N = int(user_input[3])
    else:
        N = int(user_input[5])

    # first user_input will be name and second will be source_port
    source_port = user_input[2]
    name = user_input[1]

    # get source ip
    src_ip = socket.gethostbyname(socket.gethostname())
    # create socketserver
    # https://docs.python.org/3/library/socketserver.html
    server = socketserver.UDPServer((src_ip, int(source_port)), MyUDPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()

    # create a poc list that puts in all the nodes that it discovered
    poc_list = set()
    # add itself to the poc_list
    poc_list.add((name, src_ip, source_port))

    packet_id = 0

    while len(poc_list) < N:
        if len(user_input) == 6:
            dest_port = user_input[4]
            dest_ip = user_input[3]
            packet = create_packet("1", poc_list, source_port, dest_port, source_port + str(packet_id), 0)
            sock.sendto(packet, (dest_ip, int(dest_port)))

        recv_packet, address = sock.recvfrom(512000)
        recv_data = recv_packet.data
        print(recv_data)

        recv_data = recv_data.difference(poc_list)

        for node in recv_data:
            dest_port = node[2]
            dest_ip = node[1]
            packet = (1, poc_list, source_port, dest_port, source_port + str(packet_id))
            sock.sendto(packet, (dest_ip, int(dest_port)))






