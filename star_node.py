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
        print(recv_data)

        #poc packet is received
        if header == "0":
            if not peer_discovery_done:
                update_from_poc_data(recv_data)

        #rtt_check_packet is received
        elif header == "1":
            rtt_check_receive(self, recv_data, recv_from)

        #rtt_table_packet is received
        elif header == "2":
            print("RTT Received ", recv_data)
            rtt_table_receive(recv_data)

# 0 Header("0")
# 1- PoC List
def create_poc_packet(data):
    # pad name with whitespace
    poc_list_to_string = ""
    for node_name, node_value in data.items():
        poc_list_to_string += "@" + str(node_name) + "," + str(node_value[0]) + "," + str(node_value[1])

    packet = "0" + poc_list_to_string
    return packet.encode()

# 0 Header("1")
# 1-10 PacketID
# 11-35 Source ip
# 36-40 Source Port
def create_check_packet(packet_id, src_ip, src_port):
    header = "1"
    packet_string = header + packet_id + src_ip + src_port
    return packet_string.encode()

# 0 Header("2")
# 1- RTT Table
def create_table_packet(rtt_table):
    header = "2"
    rtt_table_string = ""
    for k,v in rtt_table.items():
        rtt_table_string += "@" + k[0] + "," + k[1] + "," + str(v)
    packet_string = header + rtt_table_string
    return packet_string.encode()

def peer_discover():
    global my_poc_address, my_poc_port, poc_list, N, my_name, server
    while len(poc_list) < N:
        # try sending to my PoC if I did not get response from my poc yet
        if my_poc_address is not None and my_poc_address is not None:
            packet = create_poc_packet(poc_list)
            server.socket.sendto(packet, (my_poc_address, int(my_poc_port)))
        time.sleep(5)
    print("Peer discovery done!")

def compute_rtt():
    global my_name, poc_list, server, sent_packets, my_address, my_port
    # for every node in poc table, send rtt packet to receive rtt.
    id_count = 0

    print("poc_list: ", poc_list)
    for name, value in poc_list.items():
        if name == my_name: # don't calculate rtt for myself
            continue
        is_rtt_calculated = False
        for rtt_name in rtt_table.keys(): #check if rtt is already calculated
            if tuple(sorted([name, my_name])) == rtt_name:
                is_rtt_calculated = True
                break
        if not is_rtt_calculated:
            dest_ip, dest_port = value

            # create packet_id
            packet_id = str(my_name) + str(id_count)
            packet_id = packet_id.rjust(10)

            # create packet and send
            src_address = my_address.rjust(25)
            rtt_check_packet = create_check_packet(packet_id, src_address, str(my_port))
            server.socket.sendto(rtt_check_packet, (dest_ip, int(dest_port)))

            # update current time to sent_packets dictionary
            sent_packets[packet_id] = time.time()

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


def rtt_check_receive(self, rtt_check_packet, rtt_socket):
    global my_name, my_port, sent_packets, poc_list, rtt_table, my_address
    packet_id = rtt_check_packet[1:11]
    src_address = rtt_check_packet[11:36].replace(" ", "")
    src_port = rtt_check_packet[36:41]
    print("packet: ", rtt_check_packet)
    print("packetid: ", packet_id)
    print("src_address: ", src_address)
    print("src_port: ", src_port)

    #packet returned! calculate rtt
    print("Sent packets: ", sent_packets)
    if packet_id in sent_packets.keys():
        print("Received the packet I sent! '0'")
        rtt = time.time() - sent_packets[packet_id]

        #update rtt table
        node1 = my_name
        node2 = [k for k,v in poc_list.items() if v == (src_address, int(src_port))]
        print(node2)
        rtt_key = tuple(sorted([node1, node2[0]]))
        rtt_table[rtt_key] = rtt

        #let everyone know that rtt table is updated!
        rtt_table_send(rtt_table)

    else: #someone sent rtt_check_packet! send it back right away.
        src_address = my_address.rjust(25)
        rtt_check_packet = create_check_packet(packet_id, src_address, str(my_port))
        rtt_socket.sendto(rtt_check_packet, self.client_address)
        time.sleep(10)

# send my rtt_table to everyone in poc_list
def rtt_table_send(rtt_table):
    global poc_list, server
    rtt_table_packet = create_table_packet(rtt_table)
    for name, value in poc_list.items():
        if name != my_name: #except me
            dest_ip, dest_port = value
            print("Send this packet: ", rtt_table_packet)
            server.socket.sendto(rtt_table_packet, (dest_ip, int(dest_port)))

# some node sent rtt_table, so update my rtt table
def rtt_table_receive(rtt_table_packet):
    global rtt_table

    #create new rtt_table from received rtt_table
    rtt_table_string = rtt_table_packet[1:]
    received_rtt_table = {}
    rtt_table_string = rtt_table_string.split('@')
    rtt_table_string = list(filter(None, rtt_table_string))
    for string in rtt_table_string:
        node1, node2, rtt = string.split(',')
        received_rtt_table[(node1, node2)] = rtt

    #combine rtt_tables
    new_rtt_table = {**rtt_table, **received_rtt_table}
    rtt_table = new_rtt_table
    print("RRRRRRRR ", rtt_table)

if __name__ == "__main__":
    # set variables to input so that it can be accessed throughout the file
    global poc_list, list_no_response, N, my_name, my_port, server, my_poc_port, my_poc_address, rtt_table, peer_discovery_done, my_address, sent_packets
    my_name = sys.argv[1]
    my_port = int(sys.argv[2])

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
    rtt_table = dict()

    # add myself to poc_list
    my_address = socket.gethostbyname(socket.gethostname())
    poc_list[my_name] = (my_address, my_port)

    # create the server using socketserver module
    server = socketserver.UDPServer((my_address, my_port), MyUDPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()

    peer_discover()

    compute_rtt()

    time.sleep(3)
    print("rtt_table: ", rtt_table)
    print("done!")

    server.server_close()
    server.shutdown()
    sys.exit(0)




