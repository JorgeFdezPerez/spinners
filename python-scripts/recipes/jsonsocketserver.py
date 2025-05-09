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

    def __init__(self, fnHandleMessage: Callable[[dict[str, str]], None], port: int, EOM="\r\n", encoding="utf-8"):
        """Constructor for socket server.

        Args:
            fnHandleMessage (Callable[[dict[str,str]], None]): Function that will process messages received.
            port (int): Port for TCP communication.
            EOM (str, optional): Marks the End Of Message.
                Is deleted from the message when decoding. Defaults to "\\r\\n".
            encoding (str, optional): Byte encoding. **Must be the same on client and server.** Defaults to "utf-8".
        """
        self._fnHandleMessage = fnHandleMessage
        self._port = port
        self._EOM = EOM
        self._encoding = encoding
        self._reader = None
        self._writer = None

        self.sendQueue = asyncio.Queue()

    async def _onConnection(self, reader: asyncio.StreamReader, writer: asyncio.StreamReader):
        """Launches loops to read and write messages to connected client.

        Args:
            reader (asyncio.StreamReader): Stream reader created by asyncio.start_server().
            writer (asyncio.StreamReader): Stream writer created by asyncio.start_server().
        """
        self._reader = reader
        self._writer = writer
        # Launch read and write loops
        asyncio.gather(self._readLoop(), self._writeLoop())

    async def _readLoop(self):
        """Reads messages from client, decodes them and sends them to the handler function
        """
        while True:
            received = await self._reader.readuntil(self._EOM.encode(self._encoding))
            message = json.loads(received.decode(
                self._encoding).removesuffix(self._EOM))
            # Send message to external handler
            loop = asyncio.get_running_loop()
            loop.create_task(self._fnHandleMessage(message))

    async def _writeLoop(self):
        """Encodes and sends messages stored in the queue
        """
        while True:
            message = await self.sendQueue.get()
            self._writer.write(
                (json.dumps(message) + self._EOM).encode(self._encoding))
            await self._writer.drain()
