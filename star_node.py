import socket
import socketserver
import sys
import threading

import time


class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # recv_data is the packet that I received
        # recv_from is the socket that I got data from
        recv_data = self.request[0].decode()
        recv_from = self.request[1]

        header = recv_data[0]

        if header == "0":
            update_from_poc_data(recv_data)


def update_from_poc_data(packet):
    global poc_list, my_poc_address, my_poc_port
    poc_string = packet[21:]
    individual_node = poc_string.split("<")
    for i_n in individual_node:
        individual_element = individual_node.split(",")
        if my_poc_address is not None and my_poc_port is not None and individual_element[1] == my_poc_address and str(individual_element[2]) == str(my_poc_port):
            my_poc_port = None
            my_poc_address = None
        if individual_element[0] not in poc_list.keys():
            poc_list[individual_element[0]] = (individual_element[1], int(individual_element[2]))


def peer_discover():
    global my_poc_address, my_poc_port, poc_list, N, my_name, server
    while len(poc_list) < N:
        # try sending to my PoC if I did not get response from my poc yet
        if my_poc_address is not None and my_poc_address is not None:
            packet = create_poc_packet(my_name, poc_list)
            server.socket.sendto(packet, (my_poc_address, int(my_poc_port)))

        # send my poc to all my poc until I find N items
        for node_name, node_value in poc_list:
            if node_name != my_name:
                packet = create_poc_packet(my_name, poc_list)
                server.socket.sendto(packet, (my_poc_address, int(my_poc_port)))

        time.sleep(5)

# Header : 0
# Name : 1 - 21
# data (poc_list) : 21 -
def create_poc_packet(name, data):
    # pad name with whitespace
    while len(name) != 20:
        name = " " + name

    poc_list_to_string = ""
    for node_name, node_value in data.items():
        poc_list_to_string = "<" + str(node_name) + "," + str(node_value[0]) + "," + str(node_value[1]) + ">"

    packet = "0" + name + poc_list_to_string
    return packet.encode()

# Packet Structure
# 0 Header = 1
# 1-10 PacketID
# 11-15 Source Port
def create_check_packet(packet_id, src_port):
    header = "1"
    packet_string = header + packet_id + src_port
    return packet_string.encode()

def rtt_check_send():
    global myname, poc_list, server, src_port, sent_packets
    #for every node in poc table, send rtt packet to receive rtt.
    id_count = 0
    sent_packets = {} #dict of sent rtt_check_packet_id --> sent time
    for node in poc_list.keys():
        if node != my_name: #except me
            dest_ip = poc_list[node][0]
            dest_port = poc_list[node][1]

            #create packet_id
            packet_id = str(src_port) + str(id_count)
            packet_id = packet_id.rjust(10)

            #create packet and send
            rtt_check_packet = create_check_packet(packet_id, str(src_port))
            server.socket.sendto(rtt_check_packet, (dest_ip, dest_port))

            #update current time to sent_packets dictionary
            sent_packets[packet_id]=time.time()

def rtt_check_receive(rtt_check_packet, src_ip):
    global my_name, my_port, src_port, sent_packets, poc_list, rtt_table
    packet_id = rtt_check_packet[1:11]
    src_port = rtt_check_packet[11:16]

    #packet returned! calculate rtt
    if packet_id in sent_packets.keys():
        rtt = time.time() - sent_packets[packet_id]

        #update rtt table
        node1 = my_name
        node2 = [k for k,v in poc_list.items() if v == (src_ip, int(src_port))]
        rtt_key = tuple(sorted([node1, node2]))
        rtt_table[rtt_key] = rtt

        #let everyone know that rtt table is updated!
        rtt_table_send(rtt_table)

    else: #someone sent rtt_check_packet! send it back right away.
        rtt_check_packet = create_check_packet(packet_id, my_port)
        server.socket.sendto(rtt_check_packet, (src_ip, int(src_port)))

# Packet Structure
# 0 Header = 2
# 1- RTT Table
def create_table_packet(rtt_table):
    header = "2"
    rtt_table_string = ""
    for k,v in rtt_table.items():
        rtt_table_string += "@" + k[0] + "," + k[1] + "," + str(v)
    packet_string = header + rtt_table_string
    return packet_string.encode()

# send my rtt_table to everyone in poc_list
def rtt_table_send(rtt_table):
    global poc_list
    rtt_table_packet = create_table_packet(rtt_table)
    for node in poc_list.keys():
        if node != my_name: #except me
            dest_ip = poc_list[node][0]
            dest_port = poc_list[node][1]
            server.socket.sendto(rtt_table_packet, (dest_ip, dest_port))

# some node sent rtt_table, so update my rtt table
def rtt_table_receive(rtt_table_packet):
    global rtt_table

    #create new rtt_table from received rtt_table
    rtt_table_string = rtt_table_packet[1:]
    received_rtt_table = {}
    rtt_table_string = rtt_table_string.split('@')
    for string in rtt_table_string:
        node1, node2, rtt = string.split(',')
        received_rtt_table[(node1, node2)] = rtt

    #combine rtt_tables
    new_rtt_table = {**rtt_table, **received_rtt_table}
    rtt_table = new_rtt_table

if __name__ == "__main__":
    # set variables to input so that it can be accessed throughout the file
    global poc_list, list_no_response, N, my_name, server, my_poc_port, my_poc_address
    my_name = sys.argv[1]
    my_port = int(sys.argv[2])

    # if no PoC (input 3 parameters), set N (number of nodes in system)
    # if node has PoC, append its PoC to list_no_response, which contains port number and ip address
    # of the nodes that PoC did not get response from
    N = 0
    list_no_response = []
    if len(sys.argv) == 4:
        N = sys.argv[3]
        my_poc_port = None
        my_poc_address = None
    else:
        N = sys.argv[5]
        my_poc_port = sys.argv[4]
        my_poc_address = sys.argv[3]

    # poc_list is a dictionary that has node's name as key and port number and ip address as value
    poc_list = dict()

    # add myself to poc_list
    my_address = socket.gethostbyname()
    poc_list[my_name] = (my_address, my_port)

    # create the server using socketserver module
    server = socketserver.UDPServer((my_address, my_port), MyUDPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()

    peer_discover()


