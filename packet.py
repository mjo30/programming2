class Packet:
    def __init__(self, header, data, source_port, dest_port, id):
        self.header = header
        self.data = data
        self.source_port = source_port
        self.dest_port = dest_port
        self.id = id
        # self.checksum = checksum
        # -----------------------------