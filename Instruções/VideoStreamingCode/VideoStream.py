class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except:
            raise IOError
        self.frameNum = 0
        
    def nextFrame(self):
        """Get next frame."""
        # Lê os 5 primeiros bytes que indicam o tamanho do próximo frame (string ASCII)
        data = self.file.read(5)
        
        # Verifica se leu algo (se não leu, é fim de arquivo)
        if data: 
            try:
                # Em Python 3, é mais seguro converter os bytes para string antes de virar int
                framelength = int(data)
                
                # Lê o frame atual com base no tamanho descoberto
                data = self.file.read(framelength)
                self.frameNum += 1
            except ValueError:
                # Se falhar a conversão, retorna bytes vazios
                data = bytes()
                
        return data
        
    def frameNbr(self):
        """Get frame number."""
        return self.frameNum