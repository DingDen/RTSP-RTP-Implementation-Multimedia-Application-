import sys, socket
from ServerWorker import ServerWorker

class Server:
    def main(self):
        try:
            SERVER_PORT = int(sys.argv[1])
        except:
            print("[Usage: Server.py Server_port]") # Corrigido para Python 3
            return

        rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rtspSocket.bind(('', SERVER_PORT))
        rtspSocket.listen(5)
        
        print("Servidor escutando na porta:", SERVER_PORT)

        # Recebe conexões de clientes (Loop infinito)
        while True:
            clientInfo = {}
            # accept() retorna (socket, address)
            clientInfo['rtspSocket'] = rtspSocket.accept()
            print("Novo cliente conectado:", clientInfo['rtspSocket'][1])
            
            # Inicia o worker para este cliente
            ServerWorker(clientInfo).run()

if __name__ == "__main__":
    (Server()).main()