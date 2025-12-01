import sys, socket, threading
from ServerWorker import ServerWorker

class Server:
    def main(self):
        try:
            SERVER_PORT = int(sys.argv[1])
        except:
            print("[Usage: Server.py Server_port]")
            return

        rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rtspSocket.bind(('', SERVER_PORT))
        rtspSocket.listen(5)

        print("Servidor escutando na porta:", SERVER_PORT)

        while True:
            clientInfo = {}
            clientInfo['rtspSocket'] = rtspSocket.accept()
            print("Novo cliente conectado:", clientInfo['rtspSocket'][1])

            worker = ServerWorker(clientInfo)
            threading.Thread(target=worker.run).start()

if __name__ == "__main__":
    (Server()).main()
