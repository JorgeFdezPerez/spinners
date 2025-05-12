import asyncio

from jsonsocketserver import JsonSocketServer
from appstatemachine import AppSM
from eventhandler import EventHandler

PORT = 10000

async def main():

    sm = AppSM(makeGraph=True)
    eventHandler = EventHandler(appSM=sm)

    server = JsonSocketServer(eventHandler=eventHandler, port=PORT)
    await server.start()
    mainLoop = asyncio.get_running_loop()
    
    await eventHandler.loop()
asyncio.run(main())