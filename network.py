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
        print("received data: ", received_data)

        global send_time_dict, rtt_table, src_port, name, poc_list, server

        # check if i sent this packet to calculate rtt
        p_name = received_data[26:46]
        p_name = p_name.replace(" ", "")
        p_id = received_data[6:16]
        print("The packet that I got :", p_id)

        print("Send_time_dict: ", send_time_dict)
        # packet I sent is returned, so calculate rtt
        if p_id in send_time_dict.keys():
            print("################ Received the packet I sent ! #######################")
            rtt = time.time() - send_time_dict[p_id]

            #update rtt table
            rtt_table[name][p_name] = rtt
            if p_name not in rtt_table.keys():
                rtt_table[p_name] = dict()
            rtt_table[p_name][name] = rtt
            print("rtt_table: ", rtt_table)

            #create rtt vector (Format: <Node1 Name, Node2 Name, Node1-Node2 rtt><Node1 Name, Node3 Name, Node1-Node3 rtt>...)
            rtt_vector = ""
            for firstNode in rtt_table:
                for secondNode in rtt_table[firstNode]:
                    rtt = rtt_table[firstNode][secondNode]
                    rtt_vector += "<" + firstNode + ", " + secondNode + ", " + str(rtt) + ">"
            print("rtt_vector: ", rtt_vector)

            #update poc list
            to_send = find_poc(str(received_data))
            poc_list = poc_list.union(to_send)
            #send rtt vector to every node in poc list
            i = 0
            print("hi poc_list: ", poc_list)
            for poc in poc_list:
                if i != 0:
                    rtt_packet = create_packet("0", rtt_vector, src_port, poc[2], name, p_id)
                    print("rtt_packet: ", rtt_packet)
                    server.socket.sendto(rtt_packet, (poc[1], int(poc[2])))
                i += 1
        else:
            header = received_data[5]
            # received rtt vector, update my rtt table
            if header == "0":

                rtt_vector = received_data[46:]
                # decode rtt vector
                rtt_list = rtt_vector.split("<")
                for rtt_set in rtt_list:
                    rtt_set = rtt_set.replace(">", "")
                    rtt_set = rtt_set.split(",")
                    node1 = rtt_set[0].replace(" ", "")
                    node2 = rtt_set[1].replace(" ", "")
                    rtt = rtt_set[2]
                    #update
                    rtt_table[node1][node2] = rtt
                    print("rtt_table: ", rtt_table)

            # got PoC packet, update PoC list
            elif header == "1":
                # get the 'data' portion of the packet
                received_data = str(received_data)
                # send the packet that has same packet_id if that packet has me as PoC
                if len(poc_list) < N:
                    packet = create_packet("1", poc_list, received_data[21:26], received_data[16:21],
                                           name, received_data[6:16])
                    src_address.sendto(packet, self.client_address)
                to_send = find_poc(received_data)
                send_poc(to_send)

def find_poc(data):
    global poc_list, src_port, name
    data = data[46:]
    print("data: ", data)
    node = data.split("<")
    node = node[1:]
    new_poc_list = set()
    for n in node:
        # get rid of unnecessary characters
        print("n: ", n)
        n = n.replace(">", "")
        node_n = n.split(",")
        print("node_n: ", node_n)
        n_name = node_n[0]
        # new_node will be (name, ip, port)
        new_node = (n_name, node_n[1], node_n[2])
        new_poc_list.add(new_node)
    # get the difference between what I learned and what I knew
    to_send = new_poc_list - poc_list
    print("to_send: ", to_send)
    return to_send

def send_poc(to_send):
    global poc_list, src_port, name, packet_id_inc, send_time_dict, server, rtt_table, poc_dest_port, poc_dest_ip
    # add all new information that I got
    poc_list = poc_list.union(to_send)
    # while I know all N nodes
    while len(poc_list) <= N:
        # send to all the nodes I know
        in_poc_list = False
        for (n_name, ip, port) in poc_list:
            # Don't send to myself!
            if n_name != name:
                # Create packet id
                packet_id = str(src_port) + str(packet_id_inc)
                packet_id_inc = int(packet_id_inc) + 1
                while (len(packet_id) != 10):
                    packet_id = "0" + packet_id
                send_time_dict[packet_id] = time.time()
                packet = create_packet("1", poc_list, src_port, port, name, packet_id)
                server.socket.sendto(packet, (ip, int(port)))
                print("send packet: ", packet)
            if ip == poc_dest_ip and port == poc_dest_port:
                in_poc_list = True
        # If my PoC is not in my list, send to my PoC
        if not in_poc_list and poc_dest_ip is not None and poc_dest_port is not None:
            packet_id = src_port + str(packet_id_inc)
            packet_id_inc += 1
            while (len(packet_id) != 10):
                packet_id = "0" + packet_id
            send_time_dict[packet_id] = time.time()
            packet = create_packet("1", poc_list, src_port, poc_dest_port, name, packet_id)
            server.socket.sendto(packet, (poc_dest_ip, int(poc_dest_port)))
            print("send packet: ", packet)
        if len(poc_list) == N:
            break
        time.sleep(5)
    print("poc List: ", poc_list)
    print("rtt_table: ", rtt_table)
    print("done!")

# Packet Structure
# 0-4 Length
# 5 Header  if header is 0, rtt vector / if header is 1, poc
# 6-15 Packet ID
# 16-20 Source Port
# 21-25 Destination Port
# 26-45 Name
# 46- Data
def create_packet(header, data, src_port, dest_port, n_name, id):
    # change data to string
    data_string = ""
    if header == "0":
        data_string = data
    elif header == "1":
        for (n, i, p) in data:
            # format the data so that it would be easier when processing
            # sample : <name,ip,port>
            string_to_add = "<" + str(n) + "," + str(i) + "," + str(p) + ">"
            data_string = data_string + string_to_add

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
    while len(n_name) != 20:
        n_name = " " + n_name

    length = len(data_string) + 1 + 10 + 5 + 5 + 5 + 20

    # pad length_str to be length 5
    length_str = str(length)
    while len(length_str) != 5:
        length_str = "0" + length_str

    data_string = length_str + header + id + src_port + dest_port + n_name + data_string
    return data_string.encode()


if __name__ == "__main__":
    # user_input is the parameters user passed in
    user_input = sys.argv
    global send_time_dict, poc_list, rtt_table, server, name, src_port, poc_dest_port, poc_dest_ip

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
    # create socketserver (https://docs.python.org/3/library/socketserver.html)
    server = socketserver.UDPServer((src_ip, int(src_port)), MyUDPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()

    # create a poc list that puts in all the nodes that it discovered
    poc_list = set()
    # add itself to the poc_list
    poc_list.add((name, src_ip, src_port))
    print("original poc_list: ", poc_list)

    # Create dictionary (packet_id --> send_time)
    packet_id_inc = 0
    packet_id = ""
    send_time_dict = {}

    poc_dest_port = None
    poc_dest_ip = None

    # add what you have for poc with name as 0 because you do not know the name yet
    if len(user_input) == 6:
        poc_dest_port = user_input[4]
        poc_dest_ip = user_input[3]
        # PoC discovery phase
        send_poc(poc_list)





