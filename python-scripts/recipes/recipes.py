import asyncio

from jsonsocketserver import JsonSocketServer
from appstatemachine import AppSM
from eventhandler import EventHandler

from masterrecipefinder import MasterRecipeFinder

PORT = 10000

async def main():

    sm = AppSM(makeGraph=True)
    server = JsonSocketServer(port=PORT)
    eventHandler = EventHandler(appSM=sm)

    await sm.start(eventHandler=eventHandler)
    await server.start(eventHandler=eventHandler)

    finder = MasterRecipeFinder()
    recipes = await(finder.updateAndGetMasterRecipes())
    print(recipes)

    mainLoop = asyncio.get_running_loop()
    await eventHandler.loop()
asyncio.run(main())