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

        global send_time_dict, source_port, name, poc_list, server

        # check if i sent this packet to calculate rtt
        pid = received_data[7:16]

        # packet I sent is returned, so calculate rtt
        if pid in send_time_dict.keys():
            rtt = time.time() - send_time_dict[pid]
            #send updated rtt table to every poc
            send_rtt_vector(rtt)
        else:
            header = received_data[6]
            # received rtt vector, update my rtt table
            if header == "0":
                # received rtt vector, update my rtt table with information provided


            # got PoC packet, update PoC list
            elif header == "1":
                # get the 'data' portion of the packet
                received_data = str(received_data)
                data_to_process = received_data[27:]
                to_send = find_poc(data_to_process)
                send_poc(to_send)


def find_poc(data):
    global poc_list
    node = data.split("<")
    new_poc_list = set()
    for n in node:
        # get rid of unnecessary characters
        n = n.replace("<", "")
        n = n.replace(">", "")
        n = n.split(",")
        # new_node will be (name, ip, port)
        new_node = (n[0], n[1], n[2])
        new_poc_list.add(new_node)
    # get the difference between what I learned and what I knew
    to_send = new_poc_list - poc_list
    return to_send

def send_poc(to_send):
    global poc_list, src_port, name, packet_id_inc, send_time_dict, server
    # add all new information that I got
    poc_list.add(to_send)

    # while I know all N nodes
    while len(poc_list) < N:
        # send to all the nodes I know
        for (n_name, ip, port) in poc_list:
            # Don't sent to myself!
            if n_name != name:
                # Create packet id
                packet_id = source_port + str(packet_id_inc)
                packet_id_inc += 1
                send_time_dict[packet_id] = time.time()
                packet = create_packet("1", poc_list, src_port, port, name, packet_id)
                server.socket.sendto(packet, (ip, int(port)))


def send_rtt_vector(rtt):

# Packet Structure
# 0-5 Length
# 6 Header
# if header is 0, rtt vector / if header is 1, poc
# 7-16 Packet ID
# 17-21 Source Port
# 22-26 Destination Port
# 27-46 Name
# 27- Data
def create_packet(header, data, source_port, dest_port, n_name, id):
    # change data to string
    data_string = ""
    if header == "0":

    elif header == "1":
        for (n, i, p) in data:
            # format the data so that it would be easier when processing
            # sample : <name,ip,port>
            string_to_add = "<" + n + "," + i + "," + p + ">"
            data_string = data_string + string_to_add

    # pad source_port to be length 5
    while len(source_port) != 5:
        source_port = "0" + source_port

    # pad dest_port to be length 5
    while len(dest_port) != 5:
        dest_port = "0" + dest_port

    # pad id to be length 10
    while len(id) != 10:
        id = "0" + id

    # pad name to be length 20
    while len(n_name) != 20:
        n_name = " " + n_name

    length = len(data_string) + 1 + 10 + 5 + 5 + 5 + 20

    # pad length_str to be length 5
    length_str = str(length)
    while len(length_str) != 5:
        length_str = "0" + length_str

    data_string = length_str + header + id + source_port + dest_port  + n_name + data_string
    return data_string.encode()


if __name__ == "__main__":
    # user_input is the parameters user passed in
    user_input = sys.argv
    global send_time_dict, poc_list, rtt_table, server, name, source_port, packet_id_inc

    # N is number of total nodes
    # if the node does not have PoC, it has user_input length of 4 / else 6
    if len(user_input) == 4:
        N = int(user_input[3])
    else:
        N = int(user_input[5])

    # first user_input will be name and second will be source_port
    source_port = user_input[2]
    name = user_input[1]

    # initialize rtt table
    rtt_table = dict()
    rtt_table[name] = dict()

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
    send_poc(poc_list)

        # for node in recv_data:
        #     dest_port = node[2]
        #     dest_ip = node[1]
        #     packet = (1, poc_list, source_port, dest_port, source_port + str(packet_id))
        #     sock.sendto(packet, (dest_ip, int(dest_port)))






