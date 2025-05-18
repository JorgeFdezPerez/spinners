import asyncio
import logging

from jsonsocketserver import JsonSocketServer
from appstatemachine import AppSM
from eventhandler import EventHandler
from recipehandler import RecipeHandler
from opcuaclient import MockOpcuaClient

PORT = 10000


async def main():

    # Set up logging
    logging.basicConfig(level=logging.WARNING)
    #logging.getLogger('transitions').setLevel(logging.INFO)
    logging.getLogger('EventHandler').setLevel(logging.DEBUG)
    logging.getLogger('RecipeHandler').setLevel(logging.DEBUG)
    logging.getLogger('ControlRecipeSM').setLevel(logging.DEBUG)

    sm = AppSM(makeGraph=False)
    server = JsonSocketServer(port=PORT)
    opcuaClient = MockOpcuaClient()
    recipeHandler = RecipeHandler()
    eventHandler = EventHandler(
        appSM=sm, opcuaClient=opcuaClient, recipeHandler=recipeHandler)

    await server.start(eventHandler=eventHandler)
    await recipeHandler.setEventHandler(eventHandler=eventHandler)

    asyncio.create_task(eventHandler.loop())

    # MOCK EVENTS FOR TESTING
    # mock client connection
    await eventHandler.handleEvent({"socketServerEvent": "connected"})
    await asyncio.sleep(2)
    # mock hmi order to reset plant
    # (would come after client is notified that app is waiting to reset)
    await eventHandler.handleEvent({"hmiEvent": "resetPlant"})
    await asyncio.sleep(2)
    # MockOpcuaClient launches fake events for phases being completed automatically

    while True:
        await asyncio.sleep(5)
asyncio.run(main())
