import asyncio
import logging

from jsonsocketserver import JsonSocketServer
from appstatemachine import AppSM
from eventhandler import EventHandler
from recipehandler import RecipeHandler
from opcuaclient import OpcuaClient, MockOpcuaClient

PORT = 10000

# Mock recipes server for testing. Does not communicate with opcua

async def main():

    # Set up logging
    #logging.basicConfig(level=logging.WARNING)
    #logging.getLogger('transitions').setLevel(logging.INFO)
    #logging.getLogger('EventHandler').setLevel(logging.DEBUG)
    #logging.getLogger('RecipeHandler').setLevel(logging.DEBUG)
    #logging.getLogger('ControlRecipeSM').setLevel(logging.DEBUG)
    #logging.getLogger("OpcuaClient").setLevel(logging.DEBUG)
    #logging.getLogger("MasterRecipeFinder").setLevel(logging.DEBUG)

    await asyncio.sleep(5)

    sm = AppSM(makeGraph=False)
    server = JsonSocketServer(port=PORT)
    opcuaClient = MockOpcuaClient()
    recipeHandler = RecipeHandler()
    eventHandler = EventHandler(
        appSM=sm,
        opcuaClient=opcuaClient,
        recipeHandler=recipeHandler,
        socketServer=server
        )

    await server.start(eventHandler=eventHandler)
    await recipeHandler.setEventHandler(eventHandler=eventHandler)
    await opcuaClient.start(eventHandler=eventHandler)
    await sm.start(eventHandler=eventHandler)

    await eventHandler.loop()

    #asyncio.create_task(eventHandler.loop())

    #while True:
    #    await asyncio.sleep(5)
asyncio.run(main())
