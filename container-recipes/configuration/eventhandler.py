import asyncio
import logging
from appstatemachine import AppSM
from recipehandler import RecipeHandler
from mysqlclient import mysqlTestConnection, mysqlQuery
from opcuaclient import OpcuaClient
from jsonsocketserver import JsonSocketServer
from manualcontroller import ManualController

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
        """Endless loop. Read events from event queue. Type can be "error", "appSMEvent",
        "socketServerEvent", "hmiEvent", "opcuaEvent", "recipeHandlerEvent", "manualControllerEvent".
        """        
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
                    case "manualControllerEvent":
                        await self._processManualControllerEvent(event)
                    case _:
                        self._logger.info("Event is of unknown type.")
            else:
                self._logger.info("Event gotten is an invalid object.")

    def __init__(self, appSM: AppSM, opcuaClient: OpcuaClient, recipeHandler: RecipeHandler, socketServer: JsonSocketServer, manualController: ManualController):
        """Constructor
        """        
        self._eventQueue = asyncio.Queue()
        self._appSM = appSM
        self._opcuaClient = opcuaClient
        self._recipeHandler = recipeHandler
        self._socketServer = socketServer
        self._manualController = manualController
        # set up logging
        self._logger = logging.getLogger("EventHandler")

    async def _processHmiEvent(self, event: dict[str, str]):
        """React to events coming from the user interface (via the json socket server).
        Event can be "resetPlant","startManualControl","startManualPhases","getRecipes","runRecipe",
        "emergencyStop","pause","unpause","getUsers","continueLastRecipe"

        Args:
            event (dict[str, str]): Event
        """        
        eventCode = event["hmiEvent"]
        match eventCode:
            case "resetPlant":
                # Enters resetting state if was in waitingToReset or controllingManually
                await self._appSM.machine.resetPlant()
            case "startManualControl":
                # Start manual control
                await self._appSM.machine.manualSelected()
            case "startManualPhases":
                # Launch a phase while controlling manually
                await self._manualController.startPhases(phases = event["phases"])
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
                await self._emergencyStop(event=event)
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
                    if (await self._recipeHandler.continueControlRecipe()):
                        await self._appSM.recipeSelected()
                    else:
                        asyncio.create_task(
                            self._socketServer.sendQueue.put({"error": "continuedRecipeWasCompleted"}))
                else:
                    asyncio.create_task(
                        self._socketServer.sendQueue.put({"error": "notInIdle"}))

    async def _processAppSMEvent(self, event: dict[str, str]):
        """React to events comming from the App state machine (when it changes state).
        Events can be "enterStarting","enterWaitingToReset","enterResetting","enterControllingManually",
        "exitControllingManually","enterProducingBatch"

        Args:
            event (dict[str, str]): Event.
        """        
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
                # Reset manual controller
                self._manualController.completePhase()
            case "exitControllingManually":
                pass
            case "enterProducingBatch":
                pass

    async def _processSocketServerEvent(self, event: dict[str, str]):
        """React to events coming from JsonSocketServer class.
        (connections, disconnects, etc)
        Events can be "connected"

        Args:
            event (dict[str, str]): Event received
        """
        eventCode = event["socketServerEvent"]
        match eventCode:
            case "connected":
                await self._emergencyStop(event=event)
                await self._appSM.start(eventHandler=self)

    async def _processOpcuaEvent(self, event: dict[str, str]):
        """React to events coming from the OPC UA client (changes in subscribed data, finishing phases).
        Events can be "receivedData","completedPhases".

        Args:
            event (dict[str, str]): Event.
        """        
        eventCode = event["opcuaEvent"]
        match eventCode:
            case "receivedData":
                match event["data"]["var"]:
                    case "EstadoActual":
                        # Change in the state of one of the equipment modules
                        if (event["data"]["value"] == 3):
                            # Equipment module was aborted - abort all other phases,
                            # then go to state waitingToReset
                            await self._emergencyStop(event=event)
                    case _:
                        pass
                pass
            case "completedPhases":
                machine = self._appSM.machine
                currentState = machine.get_model_state(machine.model)
                match(currentState.name):
                    case "resetting":
                        await self._recipeHandler.transitionControlRecipe()
                    case "producingBatch":
                        await self._recipeHandler.transitionControlRecipe()
                    case "controllingManually":
                        await self._manualController.completePhase()
                        asyncio.create_task(self._socketServer.sendQueue.put(
                            {"event": "manualPhasesDone"}))
                
    async def _processRecipeHandlerEvent(self, event: dict[str, str]):
        """React to events coming from recipe handler (finished recipe, have to start phases, etc.).
        Events can be "startPhases","finishedCycle","finishedAllCycles".

        Args:
            event (dict[str, str]): Event.
        """        
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

    async def _processManualControllerEvent(self, event: dict[str, str]):
        """React to events coming from manual controller (when it requests to start phases).
        Event can be "startPhases".

        Args:
            event (dict[str, str]): Event.
        """        
        eventCode = event["manualControllerEvent"]
        match eventCode:
            case "startPhases":
                # Manual control wants phases to be executed
                await self._opcuaClient.startEquipmentPhases(event["phases"])

    async def _processError(self, error: dict[str, str]):
        """React to error events.
        Event can be "socketServerEncoding","socketServerDecoding","socketClientDisconnected"

        Args:
            error (dict[str, str]): Error event.
        """        
        errorCode = error["error"]
        match errorCode:
            case "socketServerEncoding":
                pass
            case "socketServerDecoding":
                pass
            case "socketClientDisconnected":
                self._emergencyStop(error)

    async def _getUsers(self):
        """Get list of users from database

        Returns:
            List[str]: List of users
        """
        users = await mysqlQuery("SELECT nombre FROM usuarios")
        # Usernames are returned as tuples in a list [(username1,),(username2),...]
        users = [x[0] for x in users]
        return users

    async def _emergencyStop(self, event: dict[str, str]):
        """Stop all running equipment phases. Go to a safe state

        Args:
            event (dict[str, str]): Event that caused the emergency stop. For logging in database.
        """        
        # Stop all running phases
        await self._opcuaClient.abortAllPhases()

        machine = self._appSM.machine
        currentState = machine.get_model_state(
            machine.model)
        match (currentState.name):
            case "resetting":
                # Go to state waitingToReset
                await self._appSM.machine.abortProduction()
                # Tell socket client about it
                asyncio.create_task(
                    self._socketServer.sendQueue.put({"event":"recipeAborted"}))
            case "producingBatch":
                # Go to state waitingToReset
                await self._appSM.machine.abortProduction()
                # Store in database (if logging is enabled for the current recipe)
                if(event["data"] != None):
                    await self._recipeHandler.storeEmergencyStop(f"Alarma en {event["data"]["me"]}")
                elif(event["hmiEvent"] == "emergencyStop"):
                    await self._recipeHandler.storeEmergencyStop("Parada de emergencia")
                elif(event["error"] == "socketClientDisconnected"):
                    await self._recipeHandler.storeEmergencyStop("Cliente socket desconectado")
                elif(event["socketServerEvent"] == "connected"):
                    await self._recipeHandler.storeEmergencyStop("Nueva conexion de cliente socket")
                # Store control recipe in case it has to be continued later
                await self._recipeHandler.rememberAbortedControlRecipe()
                # Tell socket client about it
                asyncio.create_task(
                    self._socketServer.sendQueue.put({"event":"recipeAborted"}))
            case "controllingManually":
                await self._appSM.machine.abortProduction()
                await self._manualController.abort()
                asyncio.create_task(
                    self._socketServer.sendQueue.put({"event":"phasesAborted"}))