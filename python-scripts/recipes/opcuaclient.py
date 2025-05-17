import asyncio

class MockOpcuaClient:
    """Mock opcua client for trying out program without connection to
    opcua server / plant.
    """    
    async def start(self, eventHandler: any):
        self._eventHandler = eventHandler
        await asyncio.sleep(0.5)
        await self._eventHandler.handleEvent({"opcuaEvent": "started"})

    async def subscribeToData(self, equipmentModuleNames: list, variableNames: list):
        await asyncio.sleep(0.5)

    async def startEquipmentPhases(self, phases: list[dict]):
        await asyncio.sleep(0.5)
        await self.mockPhasesCompleted()

    async def abortAllPhases(self):
        await asyncio.sleep(0.5)

    async def resetAllModules(self):
        await asyncio.sleep(0.5)

    async def mockReceivedData(self, data: dict):
        """Generate a mock event of data being received.

        Args:
            data (dict): Data, such as:
                {"data": {"me" : "ME_BASES", "variable" : "numSrv", "value" : 4} }
        """
        event = {"opcuaEvent": "receivedData"}.update(data)
        await self._eventHandler.handleEvent(event)

    async def mockPhasesCompleted(self):
        """Generate a mock event of all running equipment phases being completed.
        """        
        event = {"opcuaEvent": "completedPhases"}
        asyncio.create_task(self._eventHandler.handleEvent(event))

    def __init__(self):
        self._eventHandler = None

class OpcuaClient:
    async def start(self, eventHandler: any):
        self._eventHandler = eventHandler
        # TODO: Connect to opcua
        await self._eventHandler.handleEvent({"opcuaEvent": "started"})

    async def subscribeToData(self, equipmentModuleNames: list, variableNames: list):
        # TODO: Get node ids from mysql or opcua, subscribe to them
        # TODO: Generate events (see mock class) when data changes
        pass

    async def startEquipmentPhases(self, phases: list[dict]):
        """Create task group to run specified phases.
        Task group will be cancelled when calling via abortAllPhases().
        On task group completion, event {"opcuaEvent": "completedPhases"} will be sent.

        Args:
            phases (list[Dict]): Phases to launch, for example:
                [
                {"me": "ME_BASES", "numSrv": 4, "setPoint": None},
                {"me": "ME_TRANSPORTE", "numSrv": 5, "setPoint": 2},
                ...]
        """        
        # TODO: Launch parallel task group that runs the equipment phases until completion
        # (opcua methods IniciarFase, CompletarFase).
        # Task group should send event on completion.
        # TODO: Task group should be cancellable when aborting all phases.
        pass

    async def abortAllPhases(self):
        # TODO: Abort all running phases, then reset them.
        # (opcua methods AbortarModulos, ResetModulo)
        # TODO: Cancel task from startEquipmentPhase.
        pass

    async def resetAllModules(self):
        # TODO: Reset running modules
        # (opcua method ResetModulo)
        pass

    def __init__(self):
        self._eventHandler = None
        self._runningTasks = []