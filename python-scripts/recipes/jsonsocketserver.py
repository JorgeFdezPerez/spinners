import json
import asyncio
from collections.abc import Callable


class JsonSocketServer:
    """Async socket server for TCP communication of dictionaries.

    Dictionaries are serialized as json and encoded.

    Attributes:
        sendQueue (asyncio.Queue): Put messages here to send them.
    """

    async def start(self):
        """Starts the server.
        """
        # Host must be 0.0.0.0 on Docker
        self._server = await asyncio.start_server(
            client_connected_cb=self._onConnection,
            host="0.0.0.0",
            port=self._port)

        loop = asyncio.get_running_loop()
        loop.create_task(self._server.serve_forever())

    def __init__(self, eventHandler: any, port: int, EOM="\r\n", encoding="utf-8"):
        """Constructor for socket server.

        Args:
            eventHandler (any): Object that will handle events received. Must have a method:
                eventHandler.handleEvent(event: dict[str,str])
            port (int): Port for TCP communication.
            EOM (str, optional): Marks the End Of Message.
                Is deleted from the message when decoding. Defaults to "\\r\\n".
            encoding (str, optional): Byte encoding. **Must be the same on client and server.** Defaults to "utf-8".
        """
        self._eventHandler = eventHandler
        self._port = port
        self._EOM = EOM
        self._encoding = encoding
        self._reader = None
        self._writer = None

        self.sendQueue = asyncio.Queue()

    async def _onConnection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Launches loops to read and write messages to connected client.

        Args:
            reader (asyncio.StreamReader): Stream reader created by asyncio.start_server().
            writer (asyncio.StreamWriter): Stream writer created by asyncio.start_server().
        """
        self._reader = reader
        self._writer = writer
        # Launch read and write loops
        asyncio.gather(self._readLoop(), self._writeLoop())

    async def _readLoop(self):
        """Reads messages from client, decodes them and sends them to the handler function.

        Sends {"error": "socketServerDecoding"} to message handler if there
        is an error when deserializing and decoding the dictionary.
        """
        while True:
            # Check if connection ended
            if (self._reader.at_eof()):
                loop.create_task(self._fnHandleMessage(
                    {"error": "socketClientDisconnected"}))
                await self._writer.write_eof()
            else:
                # Wait for message that ends with EOM
                received = await self._reader.readuntil(self._EOM.encode(self._encoding))
                loop = asyncio.get_running_loop()
                try:
                    message = json.loads(received.decode(
                        self._encoding).removesuffix(self._EOM))
                except:
                    message = {"error": "socketServerDecoding"}
                finally:
                    # Send message to external handler
                    loop.create_task(self._eventHandler.handleEvent(message))

    async def _writeLoop(self):
        """Encodes and sends messages stored in the queue.

        Sends {"error": "socketServerEncoding"} to message handler if there
        is an error when serializing and encoding the dictionary.
        """
        while True:
            message = await self.sendQueue.get()
            try:
                messageEncoded = (json.dumps(message) +
                                  self._EOM).encode(self._encoding)
            except:
                loop = asyncio.get_running_loop()
                loop.create_task(self._eventHandler.handleEvent(
                    {"error": "socketServerEncoding"}))
            else:
                self._writer.write(messageEncoded)
                await self._writer.drain()
