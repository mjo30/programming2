import socket
import socketserver
import sys
import threading

import time


class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        recv_data = self.request[0].decode() #recv_data is the packet that I received
        recv_from = self.request[1]  # recv_from is the socket that I got data from

        header = recv_data[0]
        global rtt_matrix, sent_packets, rtt_vector
        #poc packet is received
        if header == "0":
            if not peer_discovery_done:
                update_from_poc_data(recv_data)

        elif header == "1":
            # print("Received rtt vector, ", recv_data)
            # if packet id is in sent_packets
            if recv_data[11:] in sent_packets.keys():
                # name is the name that I got this packet from
                name = recv_data[1:11].replace(" ", "")
                # if I do not have rtt information about this node
                if name not in rtt_vector.keys():
                    # calculate the rtt and put it in
                    past_time = sent_packets[recv_data[11:]]
                    rtt_vector[name] = time.time() - past_time
            else:
                # if i did not send this packet, send it back without doing anything
                # print("Send to ", recv_data)
                recv_from.sendto(recv_data.encode(), self.client_address)

        # if i received rtt matrix, update
        elif header == "2":
            # print("Received rtt matrix ", recv_data)
            if len(rtt_matrix.keys()) < N:
                update_rtt_matrix(recv_data)


# update rtt matrix from data that I received
def update_rtt_matrix(data):
    global rtt_matrix, poc_list, my_name, rtt_vector
    # get initial length of rtt matrix
    init_len = len(rtt_matrix.keys())
    # get everything without header
    matrix_string = data[1:]
    # split rtt_vector
    individual_node = matrix_string.split("&")
    # get rid of [""]
    individual_node = individual_node[1:]
    for i_n in individual_node:
        name_index = i_n.find("@")
        name = i_n[0:name_index]
        if name not in rtt_matrix.keys():
            rtt_matrix[name] = i_n[name_index:]

    len_after_update = len(rtt_matrix.keys())

    # if length before update and length after update is different, it means that matrix
    # has been updated! send new information to all poc
    # if len(rtt_vector) != N - 1:
    #     compute_my_rtt()

    if len_after_update != init_len and len(rtt_vector) == N - 1:
        for key, value in poc_list.items():
            if key != my_name:
                packet = create_rtt_vector_packet()
                server.socket.sendto(packet, (value[0], int(value[1])))

    # print("This is rtt matrix ", rtt_matrix)


# 0 Header("0")
# 1- PoC List
def create_poc_packet(data):
    # pad name with whitespace
    poc_list_to_string = ""
    for node_name, node_value in data.items():
        poc_list_to_string += "@" + str(node_name) + "," + str(node_value[0]) + "," + str(node_value[1])

    packet = "0" + poc_list_to_string
    return packet.encode()


def peer_discover():
    global my_poc_address, my_poc_port, poc_list, N, my_name, server
    while len(poc_list) < N:
        # try sending to my PoC if I did not get response from my poc yet
        if my_poc_address is not None and my_poc_address is not None:
            packet = create_poc_packet(poc_list)
            server.socket.sendto(packet, (my_poc_address, int(my_poc_port)))
        time.sleep(5)


def compute_my_rtt():
    global poc_list, server, my_name, rtt_matrix, rtt_vector
    while len(rtt_vector) < N - 1:
        for key, value in poc_list.items():
            if key != my_name and key not in rtt_vector.keys():
                packet = create_rtt_packet(key)
                server.socket.sendto(packet, (value[0], int(value[1])))
        time.sleep(3)
    # add my information to rtt matrix
    # when you have all the information that you need, put it into rtt_matrix
    # rtt matrix will look like this :
    # {my_name : @B:0.23@C:0.25@D:0.30}
    if len(rtt_vector) == N - 1:
        rtt_vector_string = ""
        for key, value in rtt_vector.items():
            rtt_vector_string = rtt_vector_string + "@" + str(key) + ":" + str(value)
        rtt_matrix[my_name] = rtt_vector_string

        for key, value in poc_list.items():
            if key != my_name:
                packet = create_rtt_vector_packet()
                server.socket.sendto(packet, (value[0], int(value[1])))


# packet has
# header : packet[0]
# name : packet[1:11]
# data : packet[11:]
def create_rtt_packet(name):
    global packet_inc_factor, my_name, packet_inc_factor, sent_packets
    name = name.rjust(10)
    packet_id = my_name + "@" + str(packet_inc_factor)
    packet = "1" + name + packet_id
    sent_packets[packet_id] = time.time()
    packet_inc_factor += 1
    return packet.encode()


def update_from_poc_data(packet):
    global poc_list, my_poc_address, my_poc_port, my_name, peer_discovery_done, server
    poc_string = packet[1:]
    individual_node = poc_string.split("@")
    individual_node = list(filter(None, individual_node))
    for i_n in individual_node:
        name, address, port = i_n.split(",")
        if name not in poc_list.keys():
            poc_list[name] = (address, int(port))

    # my poc is updated, so tell everyone!
    for node_name, node_value in poc_list.items():
        if node_name != my_name:
            dest_address, dest_port = node_value
            packet = create_poc_packet(poc_list)
            server.socket.sendto(packet, (dest_address, int(dest_port)))
    if len(poc_list) == N:
        peer_discovery_done = True


# send my rtt matrix to my PoC if rtt_matrix is not complete
def compute_global_rtt():
    global rtt_matrix, poc_list, my_name, server, rtt_vector
    if len(rtt_vector.keys()) == N - 1:
        while len(rtt_matrix) < N:
            for key, value in poc_list.items():
                if key != my_name and key not in rtt_matrix.keys():
                    packet = create_rtt_vector_packet()
                    server.socket.sendto(packet, (value[0], int(value[1])))
            time.sleep(3)


def create_rtt_vector_packet():
    global rtt_matrix
    rtt_matrix_string = ""
    # rtt_matrix_string will look like
    # &A@B:25 &B@A:25
    for key, value in rtt_matrix.items():
        rtt_matrix_string = rtt_matrix_string + "&" + str(key) + value

    rtt_matrix_string = "2" + rtt_matrix_string
    return rtt_matrix_string.encode()


def find_hub():
    global rtt_matrix, hub_name
    # this dictionary will have name as key and sum of rtt as value
    min_rtt_dict = dict()
    sum_value = float(0)
    for name, string in rtt_matrix.items():
        # String will be in this form '@A:0.00@B:0.01'
        # after splitting will be something like ['', 'A:0.00', 'B:0.01']
        split_string = string.split("@")
        for s_s in split_string:
            index_of_colon = s_s.find(":")
            if index_of_colon != -1:
                sum_value += float(s_s[index_of_colon + 1:])
        min_rtt_dict[name] = sum_value

    hub_name = min(min_rtt_dict, key=min_rtt_dict.get)


if __name__ == "__main__":
    # set variables to input so that it can be accessed throughout the file
    global poc_list, list_no_response, N, my_name, my_port, server, my_poc_port, my_poc_address, rtt_matrix, peer_discovery_done, my_address, sent_packets, rtt_vector, packet_inc_factor, hub_name
    my_name = sys.argv[1]
    my_port = int(sys.argv[2])

    rtt_vector = dict()
    packet_inc_factor = 0
    # if no PoC (input 3 parameters), set N (number of nodes in system)
    # if node has PoC, append its PoC to list_no_response, which contains port number and ip address
    # of the nodes that PoC did not get response from
    N = 0
    peer_discovery_done = False
    list_no_response = []
    if len(sys.argv) == 4:
        N = int(sys.argv[3])
        my_poc_port = None
        my_poc_address = None
    else:
        N = int(sys.argv[5])
        my_poc_port = sys.argv[4]
        my_poc_address = sys.argv[3]

    # poc_list is a dictionary that has node's name as key and port number and ip address as value
    poc_list = dict()

    # dict of sent rtt_check_packet_id --> sent time
    sent_packets = dict()

    #rtt_table is a dictionary that has tuple of (node1 name, node2 name) as key and rtt as value
    rtt_matrix = dict()

    # add myself to poc_list
    my_address = socket.gethostbyname(socket.gethostname())
    poc_list[my_name] = (my_address, my_port)

    # create the server using socketserver module
    server = socketserver.UDPServer((my_address, my_port), MyUDPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()

    peer_discover()
    print("POC LIST ", poc_list)
    time.sleep(1)

    compute_my_rtt()
    print("This is my rtt vector ", rtt_vector)
    time.sleep(1)

    compute_global_rtt()
    time.sleep(1)
    print("rtt_matrix: ", rtt_matrix)

    find_hub()
    time.sleep(1)

    print("Found a hub: ", hub_name)

    server.server_close()
    server.shutdown()
    sys.exit(0)
