import asyncio
import logging
from appstatemachine import AppSM
from recipehandler import RecipeHandler
from mysqlclient import mysqlTestConnection
from opcuaclient import OpcuaClient


class EventHandler:
    """Event handler. Recieves events in a queue and calls class methods to react to them.

    Events are dicts, with first key { "EVENT_TYPE" : "EVENT_CODE" }
    """

    async def handleEvent(self, event: dict[str, str]):
        """Add event to queue

        Args:
            event (dict[str,str]): Event to add.
                Dict with first key { "EVENT_TYPE" : "EVENT_CODE" }. Events can optionally have more keys (params, etc).
        """
        # self._logger.debug("Got %s", event)
        await self._eventQueue.put(event)

    async def loop(self):
        while True:
            event = await self._eventQueue.get()
            self._logger.debug("Handling %s", event)

            # Check event is a dict and isn't empty
            if (isinstance(event, dict) and dict):
                type = next(iter(event))
                match type:
                    case "error":
                        await self._processError(event)
                    case "appSMEvent":
                        await self._processAppSMEvent(event)
                    case "socketServerEvent":
                        await self._processSocketServerEvent(event)
                    case "hmiEvent":
                        await self._processHmiEvent(event)
                    case "opcuaEvent":
                        await self._processOpcuaEvent(event)
                    case "recipeHandlerEvent":
                        await self._processRecipeHandlerEvent(event)
                    case _:
                        self._logger.info("Event is of unknown type.")
            else:
                self._logger.info("Event gotten is an invalid object.")

    def __init__(self, appSM: AppSM, opcuaClient: OpcuaClient, recipeHandler: RecipeHandler):
        self._eventQueue = asyncio.Queue()
        self._appSM = appSM
        self._opcuaClient = opcuaClient
        self._recipeHandler = recipeHandler
        # set up logging
        self._logger = logging.getLogger("EventHandler")

    async def _processHmiEvent(self, event: dict[str, str]):
        eventCode = event["hmiEvent"]
        match eventCode:
            case "resetPlant":
                # Enters resetting state if was in waitingToReset or controllingManually
                await self._appSM.machine.resetPlant()
            case "manualSelected":
                # NOT IMPLEMENTED
                pass
                # await self._appSM.machine.manualSelected()
            case "getRecipes":
                # Client is requesting recipe list.
                # Recipe list will be fetched only if in idle state.

                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                if (currentState.name == "idle"):
                    recipeInfo = self._recipeHandler.getMasterRecipes()
                    # TODO: Tell socket client recipe info
                    pass
                else:
                    # TODO: Tell socket client about error
                    pass
            case "recipeSelected":
                # Client has requested execution of a recipe
                # Do it only if currently in idle state
                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                if (currentState.name == "idle"):
                    await self._appSM.machine.recipeSelected()
                    masterRecipeName = event["name"]
                    paramValues = event["params"]
                    await self._recipeHandler.startControlRecipe(
                        masterRecipeName=masterRecipeName,
                        logInDatabase=True,
                        paramValues=paramValues)
                else:
                    self._logger.debug("Did not select recipe - not in idle")
                    # TODO: Tell socket client about error
                    pass
            case "emergencyStop":
                # Hmi has requested emergency stop
                # Abort all phases and go to state waitingToReset
                await self._opcuaClient.abortAllPhases()
                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                if (currentState.name != "waitingToReset"):
                    await self._appSM.machine.abortProduction()
                pass

    async def _processAppSMEvent(self, event: dict[str, str]):
        eventCode = event["appSMEvent"]
        # TODO: Tell socket client about every app state change
        match eventCode:
            case "enterStarting":
                # In order to start the app, connect to opcua and database servers,
                # then transition to active

                # TODO: Handle opcua connection errors
                # TODO: Handle mysql connection errors

                await self._opcuaClient.start(eventHandler=self)
                await mysqlTestConnection()

                await self._appSM.machine.startedApp()
            case "enterWaitingToReset":
                # TODO: Tell socket client
                pass
            case "enterResetting":
                # In order to reset the plant: Execute reset recipe "RECETA_REARME"

                # First, reset all equipment modules just in case
                await self._opcuaClient.resetAllModules()
                # Load resetting recipe and execute it
                await self._recipeHandler.getMasterRecipes()
                await self._recipeHandler.startControlRecipe("RECETA_REARME", logInDatabase=False)
                # Recipe handler will send its own event once done
            case "enterControllingManually":
                # TODO: Enable manual control
                pass
            case "exitControllingManually":
                # TODO: Disable manual control
                pass
            case "enterProducingBatch":
                pass

    async def _processSocketServerEvent(self, event: dict[str, str]):
        """React to events coming from JsonSocketServer class.
        (connections, disconnects, etc)

        Args:
            event (dict[str, str]): Event received
        """
        eventCode = event["socketServerEvent"]
        match eventCode:
            case "connected":
                await self._appSM.start(eventHandler=self)

    async def _processOpcuaEvent(self, event: dict[str, str]):
        eventCode = event["opcuaEvent"]
        match eventCode:
            case "receivedData":
                # TODO : Handle receiving abort/alarm data
                match event["data"]["var"]:
                    case "EstadoActual":
                        # Change in the state of one of the equipment modules
                        if (event["data"]["value"] == 3):
                            # Equipment module was aborted - abort all other phases,
                            # then go to state waitingToReset
                            await self._opcuaClient.abortAllPhases()
                            machine = self._appSM.machine
                            currentState = machine.get_model_state(
                                machine.model)
                            if (currentState.name != "waitingToReset"):
                                await self._appSM.machine.abortProduction()

                    case _:
                        pass
                pass
            case "completedPhases":
                # Phases for this state in the recipe are done, so go to next state
                await self._recipeHandler.transitionControlRecipe()

    async def _processRecipeHandlerEvent(self, event: dict[str, str]):
        eventCode = event["recipeHandlerEvent"]
        match eventCode:
            case "startPhases":
                # Recipe handler wants phases to be executed
                await self._opcuaClient.startEquipmentPhases(event["phases"])
            case "finishedCycle":
                # TODO: Send info to socket client
                pass
            case "finishedAllCycles":
                # Once a recipe (reset recipe or a normal one) is done, go back to idle

                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                if (currentState.name == "resetting"):
                    await self._appSM.machine.resetComplete()
                elif (currentState.name == "producingBatch"):
                    await self._appSM.machine.recipeDone()

    async def _processError(self, error: dict[str, str]):
        errorCode = error["error"]
        match errorCode:
            case "socketServerEncoding":
                pass
            case "socketServerDecoding":
                pass
            case "socketClientDisconnected":
                pass
