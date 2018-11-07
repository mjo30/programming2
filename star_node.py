import socket
import sys

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
