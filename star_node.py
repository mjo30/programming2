import socket
import sys
import time

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
    my_name = sys.argv[1]
    my_port = sys.argv[2]

    # if no PoC (input 3 parameters), set N (number of nodes in system)
    # if node has PoC, append its PoC to list_no_response, which contains port number and ip address
    # of the nodes that PoC did not get response from
    N = 0
    list_no_response = []
    if len(sys.argv) == 4:
        N = sys.argv[3]
    else:
        N = sys.argv[5]
        list_no_response.append((sys.argv[3], sys.argv[4]))

    poc_list = dict()

    my_address = socket.gethostbyname()
    poc_list[my_name] = ()
