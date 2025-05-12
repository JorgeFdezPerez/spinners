import asyncio
from appstatemachine import AppSM


class EventHandler:
    async def putEvent(self, event: dict[str, str]):
        """Add event to queue

        Args:
            event (dict[str,str]): Event to add.
                Dict with first key { type : eventCode }. Some events can optionally have more keys.
        """
        await self._eventQueue.put(event)

    async def loop(self):
        while True:
            event = await self._eventQueue.get()

            # Check event is a dict and isn't empty
            if (isinstance(event, dict) and dict):
                type = next(iter(event))
                match type:
                    case "error":
                        self._processError(event)
                    case "hmiEvent":
                        self._processHmiEvent(event)
                    case _:
                        print(
                            "Event handler got event of unknown type : " + str(type))
            else:
                print("Event handler got invalid object")

    def __init__(self, appSM: AppSM):
        self._eventQueue = asyncio.Queue()
        self._appSM = AppSM

    async def _processHmiEvent(self, event: dict[str, str]):
        eventCode = event["hmiEvent"]
        match eventCode:
            case "resetPlant":
                await self._appSM.machine.resetPlant()
            case "manualSelected":
                await self._appSM.machine.manualSelected()
            case "recipeSelected":
                # TODO: Load recipe
                await self._appSM.machine.recipeSelected()

    async def _processError(self, error: dict[str, str]):
        errorCode = error["error"]
        match errorCode:
            case "socketServerEncoding":
                print("Socket server encoding error")
            case "socketServerDecoding":
                print("Socket server decoding error")
            case "socketClientDisconnected":
                print("Socket client has disconnected")
