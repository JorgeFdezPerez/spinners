import asyncio
import json




class JsonSocketClient:
    sms: str=""
    message_received_flag: bool = False
    #Incializacion
    def __init__(self,host, port, EOM="\r\n", encoding="utf-8"):
        self._host = host
        self._port = port
        self._EOM = EOM
        self._encoding = encoding
        self._reader = None
        self._writer = None
        self.sendQueue = asyncio.Queue()
        self.on_message = None  
        self.conectado = False
        

    #Conexión
    async def connect(self):
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        print("Conectado al servidor")
        self.conectado = True
        asyncio.create_task(self._readLoop())
        asyncio.create_task(self._writeLoop())

    #Envío mensaje a cola
    async def send(self, message: dict):
        await self.sendQueue.put(message)

    #Lectura
    async def _readLoop(self):
        while True:
            try:
                data = await self._reader.readuntil(self._EOM.encode(self._encoding))
                message = json.loads(data.decode(self._encoding).removesuffix(self._EOM))
                
                with open('datos.json', 'w') as f:
                    json.dump(message, f)

                self.message_received_flag = True

                print("Mensaje recibido del servidor:", message)

                if self.on_message:
                    self.on_message(message)
                
 
            except asyncio.IncompleteReadError:
                print("Desconectado del servidor")
                break
            except Exception as e:
                print("Error al recibir datos:", e)

    #Escritura
    async def _writeLoop(self):
        while True:
            message = await self.sendQueue.get()
            try:
                messageEncoded = (json.dumps(message) + self._EOM).encode(self._encoding)
                self._writer.write(messageEncoded)
                print("Enviando mensaje al servidor:", message)
                await self._writer.drain()
            except Exception as e:
                print("Error al enviar mensaje:", e)


    def set_on_message(self, callback):
        self.on_message = callback

#Inicio cliente socket
def iniciar_cliente_socket(nombre_servidor, evento_queue, mensaje_queue, puerto):
    import threading
    def _run():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_cliente(nombre_servidor, evento_queue, mensaje_queue, puerto))

    threading.Thread(target=_run).start()

#Ejecutar cliente socket
async def run_cliente(nombre_servidor, evento_queue, mensaje_queue, puerto):
    import queue
    cliente = JsonSocketClient(nombre_servidor, port=puerto)
    await cliente.connect()
    cliente.set_on_message(lambda msg: mensaje_queue.put(msg))

    while True:
        try:
            evento = evento_queue.get_nowait()
            await cliente.send(evento)
        except queue.Empty:
            await asyncio.sleep(0.1)

