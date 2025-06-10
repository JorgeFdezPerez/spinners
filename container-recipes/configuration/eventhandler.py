import asyncio
import logging
from appstatemachine import AppSM
from recipehandler import RecipeHandler
from mysqlclient import mysqlTestConnection, mysqlQuery
from opcuaclient import OpcuaClient
from jsonsocketserver import JsonSocketServer


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

    def __init__(self, appSM: AppSM, opcuaClient: OpcuaClient, recipeHandler: RecipeHandler, socketServer: JsonSocketServer):
        self._eventQueue = asyncio.Queue()
        self._appSM = appSM
        self._opcuaClient = opcuaClient
        self._recipeHandler = recipeHandler
        self._socketServer = socketServer
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
                    recipeInfo = await self._recipeHandler.getMasterRecipes()
                    self._logger.debug(
                        "Got master recipes info: %s" % recipeInfo)
                    asyncio.create_task(self._socketServer.sendQueue.put(
                        {"info": "recipes", "recipes": recipeInfo}))
                else:
                    asyncio.create_task(
                        self._socketServer.sendQueue.put({"error": "notInIdle"}))
            case "runRecipe":
                # Client has requested execution of a recipe
                # Do it only if currently in idle state
                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                if (currentState.name == "idle"):
                    await self._appSM.machine.recipeSelected()
                    masterRecipeName = event["recipe"]
                    username = event["user"]
                    paramValues = event["parameters"]
                    await self._recipeHandler.startControlRecipe(
                        masterRecipeName=masterRecipeName,
                        logInDatabase=True,
                        username=username,
                        paramValues=paramValues)
                else:
                    self._logger.debug("Did not select recipe - not in idle")
                    asyncio.create_task(
                        self._socketServer.sendQueue.put({"error": "notInIdle"}))
            case "emergencyStop":
                # Hmi has requested emergency stop
                # Abort all phases and go to state waitingToReset
                await self._opcuaClient.abortAllPhases()
                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                if (currentState.name != "waitingToReset"):
                    await self._appSM.machine.abortProduction()
                    # Log emergency stop in database (if recipe had logging enabled)
                    await self._recipeHandler.storeEmergencyStop("Parada de emergencia solicitada desde el HMI.")
                    # Tell socket client
                    asyncio.create_task(self._socketServer.sendQueue.put(
                        {"event": "recipeAborted"}))
            case "pause":
                await self._recipeHandler.pauseControlRecipe()
            case "unpause":
                await self._recipeHandler.unpauseControlRecipe()
            case "getUsers":
                users = await self._getUsers()
                self._logger.debug("Got list of users: %s" % users)
                asyncio.create_task(self._socketServer.sendQueue.put(
                    {"info": "users", "users": users}))
            case "continueLastRecipe":
                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                if (currentState.name == "idle"):
                    if(await self._recipeHandler.continueControlRecipe()):
                        await self._appSM.recipeSelected()
                    else:
                        asyncio.create_task(
                            self._socketServer.sendQueue.put({"error": "continuedRecipeWasCompleted"}))
                else:
                    asyncio.create_task(
                        self._socketServer.sendQueue.put({"error": "notInIdle"}))

    async def _processAppSMEvent(self, event: dict[str, str]):
        eventCode = event["appSMEvent"]
        # Tell socket client abour every change in state
        asyncio.create_task(
            self._socketServer.sendQueue.put({"state": eventCode}))
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
                            # If the system is not stopped, stop it
                            machine = self._appSM.machine
                            currentState = machine.get_model_state(
                                machine.model)
                            if (currentState.name != "waitingToReset"):
                                await self._appSM.machine.abortProduction()
                                # Store in database (if logging is enabled for the current recipe)
                                await self._recipeHandler.storeEmergencyStop(f"Alarma en {event["data"]["me"]}")
                                # Tell socket client about it
                                asyncio.create_task(
                                    self._socketServer.sendQueue.put({"state": eventCode}))

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
                # Tell socket client
                asyncio.create_task(self._socketServer.sendQueue.put(
                    {"event": "recipeComplete"}))

    async def _processError(self, error: dict[str, str]):
        errorCode = error["error"]
        match errorCode:
            case "socketServerEncoding":
                pass
            case "socketServerDecoding":
                pass
            case "socketClientDisconnected":
                pass

    async def _getUsers(self):
        """Get list of users from database

        Returns:
            List[str]: List of users
        """
        users = await mysqlQuery("SELECT nombre FROM usuarios")
        # Usernames are returned as tuples in a list [(username1,),(username2),...]
        users = [x[0] for x in users]
        return users
