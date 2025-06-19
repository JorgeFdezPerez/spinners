import asyncio
import json

#HOST = 'spinners-recipes-mock'
HOST = 'localhost'
PORT = 10000

class JsonSocketClient:
    def __init__(self, host=HOST, port=PORT, EOM="\r\n", encoding="utf-8"):
        self._host = host
        self._port = port
        self._EOM = EOM
        self._encoding = encoding
        self._reader = None
        self._writer = None
        self.sendQueue = asyncio.Queue()

    async def connect(self):
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        print("Conectado al servidor")
        asyncio.create_task(self._readLoop())
        asyncio.create_task(self._writeLoop())

    async def send(self, message: dict):
        await self.sendQueue.put(message)

    async def _readLoop(self):
        while True:
            try:
                data = await self._reader.readuntil(self._EOM.encode(self._encoding))
                message = json.loads(data.decode(self._encoding).removesuffix(self._EOM))
                print("Mensaje recibido del servidor:", message)
            except asyncio.IncompleteReadError:
                print("Desconectado del servidor")
                break
            except Exception as e:
                print("Error al recibir datos:", e)

    async def _writeLoop(self):
        while True:
            message = await self.sendQueue.get()
            try:
                messageEncoded = (json.dumps(message) + self._EOM).encode(self._encoding)
                self._writer.write(messageEncoded)
                await self._writer.drain()
            except Exception as e:
                print("Error al enviar mensaje:", e)

async def main():
    client = JsonSocketClient()
    await client.connect()

    await asyncio.sleep(1)
    await client.send({"hmiEvent":"resetPlant"})
    await asyncio.sleep(4)
    await client.send({"hmiEvent":"startManualControl"})
    await asyncio.sleep(1)
    await client.send({"hmiEvent":"startManualPhases",
                       "phases":[{"me": "ME_BASES", "numSrv": 1, "setPoint": None}]})
    await asyncio.sleep(5)
    await client.send({"hmiEvent":"resetPlant"})

    while(True):
        await asyncio.sleep(1)
asyncio.run(main())