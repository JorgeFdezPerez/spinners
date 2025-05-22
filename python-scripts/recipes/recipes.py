import asyncio
import logging

from jsonsocketserver import JsonSocketServer
from appstatemachine import AppSM
from eventhandler import EventHandler
from recipehandler import RecipeHandler
from opcuaclient import OpcuaClient

PORT = 10000


async def main():

    # Set up logging
    logging.basicConfig(level=logging.WARNING)
    #logging.getLogger('transitions').setLevel(logging.INFO)
    logging.getLogger('EventHandler').setLevel(logging.DEBUG)
    logging.getLogger('RecipeHandler').setLevel(logging.DEBUG)
    logging.getLogger('ControlRecipeSM').setLevel(logging.DEBUG)
    logging.getLogger("OpcuaClient").setLevel(logging.DEBUG)

    sm = AppSM(makeGraph=False)
    server = JsonSocketServer(port=PORT)
    opcuaClient = OpcuaClient()
    recipeHandler = RecipeHandler()
    eventHandler = EventHandler(
        appSM=sm, opcuaClient=opcuaClient, recipeHandler=recipeHandler)

    await server.start(eventHandler=eventHandler)
    await recipeHandler.setEventHandler(eventHandler=eventHandler)
    await opcuaClient.start(eventHandler=eventHandler)

    asyncio.create_task(eventHandler.loop())

    # MOCK EVENTS FOR TESTING
    # mock client connection
    await eventHandler.handleEvent({"socketServerEvent": "connected"})
    await asyncio.sleep(2)
    # mock hmi order to reset plant
    # (would come after client is notified that app is waiting to reset)
    await eventHandler.handleEvent({"hmiEvent": "resetPlant"})
    #await asyncio.sleep(2)
    # MockOpcuaClient launches fake events for phases being completed automatically
    
    #await opcuaClient.startEquipmentPhases([{"me": "ME_TRANSPORTE", "numSrv": 1, "setpoint": 0}])
    #await asyncio.sleep(6)
    #await opcuaClient.abortAllPhases()

    while True:
        await asyncio.sleep(5)
asyncio.run(main())
