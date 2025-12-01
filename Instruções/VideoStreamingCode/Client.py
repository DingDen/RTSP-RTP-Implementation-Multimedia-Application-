from tkinter import *
import tkinter.messagebox as tkMessageBox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    DESCRIBE = 4

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.frameNbr = 0
        self.rtpSocket = None
        self.playEvent = threading.Event()  # sempre crie o atributo (evita race)
        self.connectToServer()

    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button        
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)

        # Create Pause button           
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)

        # Create Describe button
        self.describe = Button(self.master, width=20, padx=3, pady=3)
        self.describe["text"] = "Describe"
        self.describe["command"] = self.describeMovie
        self.describe.grid(row=1, column=3, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=1, column=4, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        # Tenta enviar TEARDOWN apenas se tivermos socket
        if self.rtspSocket:
            self.sendRtspRequest(self.TEARDOWN)
        # Fecha GUI
        try:
            # fecha janela primeiro para evitar race com threads que atualizam GUI
            self.master.destroy()
        except:
            pass

        # Apaga cache de imagem
        try:
            os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
        except OSError:
            pass

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            # Garantir que playEvent existe e está limpo
            self.playEvent.clear()
            # Create a new thread to listen for RTP packets (cria AFTER playEvent)
            threading.Thread(target=self.listenRtp, daemon=True).start()
            self.sendRtspRequest(self.PLAY)

    def listenRtp(self):        
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()
                    # print("Current Seq Num: " + str(currFrameNbr))

                    if currFrameNbr > self.frameNbr: # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except socket.timeout:
                # timeout é esperado; verifica eventos e continua
                if self.playEvent.is_set():
                    break
                if self.teardownAcked == 1:
                    break
                continue
            except Exception as e:
                # Stop listening upon requesting PAUSE or TEARDOWN
                # protegendo atributos que podem não existir
                if hasattr(self, 'playEvent') and self.playEvent.is_set():
                    break

                if self.teardownAcked == 1:
                    # close safely
                    try:
                        if self.rtpSocket:
                            self.rtpSocket.close()
                    except:
                        pass
                    break

                # Log e continua (não fecha abruptamente)
                print("Erro em listenRtp:", e)
                break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        # 'wb' é crucial para escrever bytes de imagem no Python 3
        with open(cachename, "wb") as file:
            file.write(data)
        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        try:
            photo = ImageTk.PhotoImage(Image.open(imageFile))
            self.label.configure(image = photo, height=288) 
            self.label.image = photo
        except Exception as e:
            # Em caso de imagem corrompida, apenas ignora o frame
            print(f"Erro ao atualizar frame: {e}")

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print(f"Conectado ao servidor RTSP {self.serverAddr}:{self.serverPort}")
        except Exception as e:
            self.rtspSocket = None
            tkMessageBox.showwarning('Connection Failed', f"Connection to '{self.serverAddr}:{self.serverPort}' failed.\n{e}")

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""  
        if not self.rtspSocket:
            print("Não há conexão RTSP ativa.")
            return

        # Update RTSP sequence number.
        self.rtspSeq += 1

        request = ""
        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            # Start thread to receive RTSP replies (once)
            threading.Thread(target=self.recvRtspReply, daemon=True).start()
            request = f"SETUP {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nTransport: RTP/UDP; client_port={self.rtpPort}\n\n"
            self.requestSent = self.SETUP

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            request = f"PLAY {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}\n\n"
            self.requestSent = self.PLAY

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            request = f"PAUSE {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}\n\n"
            self.requestSent = self.PAUSE

        # Describe request
        elif requestCode == self.DESCRIBE:
            request = f"DESCRIBE {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}"
            self.requestSent = self.DESCRIBE

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            request = f"TEARDOWN {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}\n\n"
            self.requestSent = self.TEARDOWN

        else:
            return

        try:
            self.rtspSocket.send(request.encode('utf-8'))
            print('\nData sent:\n' + request)
        except Exception as e:
            print("Erro ao enviar RTSP request:", e)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            try:
                reply = self.rtspSocket.recv(1024)
                if reply:
                    self.parseRtspReply(reply)
                else:
                    # conexão fechada pelo servidor
                    print("Servidor fechou a conexão RTSP.")
                    break

                # Close the RTSP socket upon requesting Teardown
                if self.requestSent == self.TEARDOWN:
                    try:
                        self.rtspSocket.shutdown(socket.SHUT_RDWR)
                        self.rtspSocket.close()
                    except:
                        pass
                    break
            except Exception as e:
                print("Erro em recvRtspReply:", e)
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        try:
            decoded_data = data.decode('utf-8')
            lines = decoded_data.splitlines()
            if len(lines) < 2:
                return
            seqNum = int(lines[1].split(' ')[1])
        except Exception:
            # Se falhar o decode ou o split, ignora
            return

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            try:
                session = int(lines[2].split(' ')[1])
            except Exception:
                return

            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200: 
                    if self.requestSent == self.SETUP:
                        self.state = self.READY
                        self.openRtpPort() 
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        self.playEvent.set()
                    elif self.requestSent == self.DESCRIBE:
                        sdpInfo = '\n'.join(lines[3:])  # pega o corpo do RTSP, onde está o SDP
                        print("SDP recebido do servidor:\n" + sdpInfo)
                        tkMessageBox.showinfo("SDP Info", sdpInfo)
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        self.teardownAcked = 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.settimeout(0.5)

        try:
            self.rtpSocket.bind(("", self.rtpPort))
            print(f"RTP socket aberto em 0.0.0.0:{self.rtpPort}")
        except Exception as e:
            tkMessageBox.showwarning('Unable to Bind', f'Unable to bind PORT={self.rtpPort}\n{e}')

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        # tenta pausar para não deixar thread RTP ativa
        try:
            self.pauseMovie()
        except:
            pass

        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            try:
                self.playMovie()
            except:
                pass
    
    def describeMovie(self):
        """Handler do botão DESCRIBE"""
        if self.state != self.INIT:
            self.sendRtspRequest(self.DESCRIBE)