from random import randint
import sys, traceback, threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket

class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2
    
    clientInfo = {}
    
    def __init__(self, clientInfo):
        self.clientInfo = clientInfo
        
    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()
    
    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:            
            try:
                data = connSocket.recv(256)
                if data:
                    # Decodifica bytes para string (Python 3)
                    decoded_data = data.decode('utf-8')
                    print("-" * 20)
                    print("RTSP Request recebido:\n" + decoded_data.strip())
                    self.processRtspRequest(decoded_data)
                else:
                    # Se data for vazio, o cliente desconectou. Encerra o loop.
                    print("Cliente desconectou o socket RTSP.")
                    break
            except Exception as e:
                print("Erro no recvRtspRequest:", e)
                break
    
    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        # splitlines() é mais seguro para quebras de linha
        request = data.splitlines()
        line1 = request[0].split(' ')
        requestType = line1[0]
        
        # Get the media file name
        filename = line1[1]
        
        # Get the RTSP sequence number 
        seq = request[1].split(' ')
        
        # Process SETUP request
        if requestType == self.SETUP:
            if self.state == self.INIT:
                print("Processando SETUP...")
                
                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                    print("Arquivo de video aberto com sucesso:", filename)
                except IOError:
                    print("Erro: Arquivo não encontrado ->", filename)
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
                
                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)
                
                # Send RTSP reply
                self.replyRtsp(self.OK_200, seq[1])
                
                # Get the RTP/UDP port from the last line
                # Procura a linha que começa com Transport
                for line in request:
                    if "Transport:" in line:
                         self.clientInfo['rtpPort'] = line.split('client_port=')[1].strip()
                         break
        
        # Process PLAY request      
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("Processando PLAY...")
                self.state = self.PLAYING
                
                # Create a new socket for RTP/UDP
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                self.replyRtsp(self.OK_200, seq[1])
                
                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp) 
                self.clientInfo['worker'].start()
        
        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("Processando PAUSE...")
                self.state = self.READY
                
                self.clientInfo['event'].set()
            
                self.replyRtsp(self.OK_200, seq[1])
        
        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("Processando TEARDOWN...")

            self.clientInfo['event'].set()
            
            self.replyRtsp(self.OK_200, seq[1])
            
            # Close the RTP socket
            if 'rtpSocket' in self.clientInfo:
                self.clientInfo['rtpSocket'].close()
            
    def sendRtp(self):
        """Send RTP packets over UDP."""
        print("Iniciando envio RTP...")
        while True:
            self.clientInfo['event'].wait(0.05) 
            
            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet(): 
                break 
                
            data = self.clientInfo['videoStream'].nextFrame()
            
            if data: 
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    packet = self.makeRtp(data, frameNumber)
                    self.clientInfo['rtpSocket'].sendto(packet,(address,port))
                    # Descomente a linha abaixo se quiser ver MUITOS logs
                    # print(f"Enviado frame {frameNumber} para {address}:{port} ({len(packet)} bytes)")
                except Exception as e:
                    print("Erro de Conexão no envio RTP:", e)
            else:
                # Se não há dados, o video acabou ou falhou
                # print("Sem dados do VideoStream (Fim do arquivo ou erro)")
                pass

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26 # MJPEG type
        seqnum = frameNbr
        ssrc = 0 
        
        rtpPacket = RtpPacket()
        
        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
        
        return rtpPacket.getPacket()
        
    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) + '\n'
            connSocket = self.clientInfo['rtspSocket'][0]
            # Envia resposta codificada em bytes
            connSocket.send(reply.encode('utf-8'))
        
        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("Erro 404: Arquivo não encontrado.")
        elif code == self.CON_ERR_500:
            print("Erro 500: Erro de conexão.")