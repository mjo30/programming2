import socketserver
import sys
import socket
import threading

import time


class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # data is the packet to deliver
        received_data = self.request[0].decode()
        src_address = self.request[1]

        global send_time_dict, rtt_table, src_port, name, poc_list, server

        p_name = received_data[27:46]
        p_id = received_data[7:16]

        # packet I sent is returned, so calculate rtt
        if p_id in send_time_dict.keys():
            rtt = time.time() - send_time_dict[p_id]

            #update rtt table
            rtt_table[name][p_name] = rtt
            rtt_table[p_name][name] = rtt

            #create rtt vector (Format: <Node1 Name, Node2 Name, Node1-Node2 rtt><Node1 Name, Node3 Name, Node1-Node3 rtt>...)
            rtt_vector = ""
            for firstNode in rtt_table:
                for secondNode in rtt_table[firstNode]:
                    rtt = rtt_table[firstNode][secondNode]
                    rtt_vector += "<" + firstNode + ", " + secondNode + ", " + str(rtt) + ">"

            #send rtt vector to every node in poc list
            for poc in poc_list:
                if poc[0] != name:
                    rtt_packet = create_packet("0", rtt_vector, src_port, poc[2], name, p_id)
                    server.socket.sendto(rtt_packet, (poc[1], int(poc[2])))
        else:
            header = received_data[6]
            # received rtt vector, update my rtt table
            if header == "0":
                rtt_vector = received_data[47:]
                rtt_list = rtt_vector.split("<")
                for rtt_set in rtt_list:
                    rtt_set = rtt_set.replace("<", "")
                    rtt_set = rtt_set.replace(">", "")
                    rtt_set = rtt_set.split(",")
                    node1 = rtt_set[0].replace(" ", "")
                    node2 = rtt_set[1].replace(" ", "")
                    rtt = rtt_set[2]
                    rtt_table[node1][node2] = rtt

            # got PoC packet, update PoC list
            elif header == "1":
                dest_port = received_data[17:21]
                dest_port.replace(" ", "")
                packet = create_packet("1", poc_list, src_port, dest_port, name, packet_id)
                server.socket.sendto(packet, (dest_address, int(dest_port)))

# Packet Structure
# 0-5 Length
# 6 Header
# if header is 0, rtt vector / if header is 1, poc
# 7-16 Packet ID
# 17-21 Source Port
# 22-26 Destination Port
# 27-46 Name
# 47- Data
def create_packet(header, data, src_port, dest_port, name, id):
    # change data to string
    data_string = ""
    for (n, i, p) in data:
        data_string = data_string + n + " " + i + " " + p + " "

    # pad source_port to be length 5
    while len(src_port) != 5:
        src_port = "0" + src_port

    # pad dest_port to be length 5
    while len(dest_port) != 5:
        dest_port = "0" + dest_port

    # pad id to be length 10
    while len(id) != 10:
        id = "0" + id

    # pad name to be length 20
    while len(name) != 20:
        name = " " + name

    length = len(data_string) + 1 + 10 + 5 + 5 + 5 + 20

    # pad length_str to be length 5
    length_str = str(length)
    while len(length_str) != 5:
        length_str = "0" + length_str

    data_string = length_str + header + id + src_port + dest_port  + data_string
    return data_string.encode()



if __name__ == "__main__":
    # user_input is the parameters user passed in
    user_input = sys.argv
    global send_time_dict, poc_list, rtt_table, server, name, src_port

    # N is number of total nodes
    # if the node does not have PoC, it has user_input length of 4 / else 6
    if len(user_input) == 4:
        N = int(user_input[3])
    else:
        N = int(user_input[5])

    # first user_input will be name and second will be source_port
    src_port = user_input[2]
    name = user_input[1]

    # initialize rtt table
    rtt_table = dict()
    rtt_table[name] = dict()

    # get source ip
    src_ip = socket.gethostbyname(socket.gethostname())
    # create socketserver
    # https://docs.python.org/3/library/socketserver.html
    server = socketserver.UDPServer((src_ip, int(src_port)), MyUDPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()

    # create a poc list that puts in all the nodes that it discovered
    poc_list = set()
    # add itself to the poc_list
    poc_list.add((name, src_ip, src_port))

    # Create dictionary (packet_id --> send_time)
    packet_id_inc = 0
    packet_id = ""
    send_time_dict = {}

    # add what you have for poc with name as 0 because you do not know the name yet
    if len(user_input) == 6:
        dest_port = user_input[4]
        dest_ip = user_input[3]
        poc_list.add((0, dest_ip, dest_port))

    # PoC discovery phase
    while len(poc_list) < N:
        # iterate through every node in poc list
        for node in poc_list:
            node_name = node[0]
            # if
            if node_name != name or node_name not in rtt_table[name]:
                packet_id = src_port + str(packet_id_inc)
                packet_id_inc += 1
                send_time_dict[packet_id] = time.time()
                packet = create_packet("1", poc_list, src_port, dest_port, name, packet_id)
                server.socket.sendto(packet, (dest_ip, int(dest_port)))

        # for node in recv_data:
        #     dest_port = node[2]
        #     dest_ip = node[1]
        #     packet = (1, poc_list, source_port, dest_port, source_port + str(packet_id))
        #     sock.sendto(packet, (dest_ip, int(dest_port)))






