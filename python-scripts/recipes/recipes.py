import asyncio

from jsonsocketserver import JsonSocketServer

PORT = 10000


async def messageHandler():
    global server
    global queue
    while True:
        message = await queue.get()
        print(message)
        await server.sendQueue.put({"Response": "Message received"})

async def addToQueue(message):
    global queue
    await queue.put(message)

async def main():
    global server
    global queue
    queue = asyncio.Queue()

    server = JsonSocketServer(fnHandleMessage = addToQueue,port=PORT)
    await server.start()
    mainLoop = asyncio.get_running_loop()
    mainLoop.create_task(messageHandler())
    
    while True:
        await asyncio.sleep(1)
asyncio.run(main())