import sys
from time import time
HEADER_SIZE = 12

class RtpPacket:    
    header = bytearray(HEADER_SIZE)
    
    def __init__(self):
        pass
        
    def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload):
        """Encode the RTP packet with header fields and payload."""
        timestamp = int(time())
        self.header = bytearray(HEADER_SIZE)
        #--------------
        # TO COMPLETE
        #--------------
        # Fill the header bytearray with RTP header fields
        
        # Byte 0: Version (2 bits), Padding (1 bit), Extension (1 bit), CSRC Count (4 bits)
        # Operação: Desloca a versão 6 bits para a esquerda, padding 5 bits, etc.
        self.header[0] = (version << 6) | (padding << 5) | (extension << 4) | cc
        
        # Byte 1: Marker (1 bit), Payload Type (7 bits)
        # Operação: Desloca o marcador 7 bits para a esquerda e combina com o Payload Type
        self.header[1] = (marker << 7) | pt
        
        # Byte 2 e 3: Sequence Number (16 bits)
        # Operação: Separa o inteiro em 2 bytes (High byte e Low byte)
        self.header[2] = (seqnum >> 8) & 0xFF
        self.header[3] = seqnum & 0xFF
        
        # Byte 4 a 7: Timestamp (32 bits)
        # Operação: Separa o timestamp em 4 bytes
        self.header[4] = (timestamp >> 24) & 0xFF
        self.header[5] = (timestamp >> 16) & 0xFF
        self.header[6] = (timestamp >> 8) & 0xFF
        self.header[7] = timestamp & 0xFF
        
        # Byte 8 a 11: SSRC (32 bits)
        # Operação: Separa o SSRC em 4 bytes
        self.header[8] = (ssrc >> 24) & 0xFF
        self.header[9] = (ssrc >> 16) & 0xFF
        self.header[10] = (ssrc >> 8) & 0xFF
        self.header[11] = ssrc & 0xFF
        
        # Get the payload from the argument
        self.payload = payload
        
    def decode(self, byteStream):
        """Decode the RTP packet."""
        self.header = bytearray(byteStream[:HEADER_SIZE])
        self.payload = byteStream[HEADER_SIZE:]
    
    def version(self):
        """Return RTP version."""
        return int(self.header[0] >> 6)
    
    def seqNum(self):
        """Return sequence (frame) number."""
        seqNum = self.header[2] << 8 | self.header[3]
        return int(seqNum)
    
    def timestamp(self):
        """Return timestamp."""
        timestamp = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
        return int(timestamp)
    
    def payloadType(self):
        """Return payload type."""
        pt = self.header[1] & 127
        return int(pt)
    
    def getPayload(self):
        """Return payload."""
        return self.payload
        
    def getPacket(self):
        """Return RTP packet."""
        return self.header + self.payload