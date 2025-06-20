import asyncio
import logging

from asyncua import Client, Node
from asyncua.ua import Variant, VariantType
from functools import partial


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
    """Opcua client for launching and aborting equipment phases.
    Subscribes to equipment module state variables on start.
    """

    async def start(self, eventHandler: any):
        """Start opcua client, subscribing to variables.

        Args:
            eventHandler (any): Event handler that will react to changes in subscribed variables.
            Must have method:
                async eventHandler.handleEvent(event: dict)
        """
        self._eventHandler = eventHandler

        asyncio.create_task(self._receiveLoop())

        asyncio.create_task(self._eventHandler.handleEvent({"opcuaEvent": "started"}))

    async def startEquipmentPhases(self, phases: list[dict]):
        """Create task to run specified phases.
        Task will be cancelled when calling abortAllPhases().
        On task completion, event {"opcuaEvent": "completedPhases"} will be sent.

        Args:
            phases (list[Dict]): Phases to launch, for example:
                [
                {"me": "ME_BASES", "numSrv": 4, "setPoint": None},
                {"me": "ME_TRANSPORTE", "numSrv": 5, "setPoint": 2},
                ...]
        """
        self._runningTask = asyncio.create_task(
            self._executeSeveralPhases(phases=phases))

    async def abortAllPhases(self):
        """Cancel the startEquipmentPhases task and abort
        all equipment modules, then reset them to idle state.
        """
        # Cancel OpcuaClient task that is running equipment phases
        if (self._runningTask != None):
            self._runningTask.cancel()

        modules = ["ME_TRANSPORTE", "ME_BASES", "ME_SPINNERS"]
        async with Client(url="opc.tcp://spinners-node-red:54840") as client:
            # Send abort event to all modules
            gatewayNode = client.get_node("ns=1;i=1000")
            await gatewayNode.call_method("1:AbortarModulos")
            self._logger.debug("Aborted all modules.")

            await asyncio.sleep(0.5)

            # Reset aborted modules to idle state
            for module in modules:
                stateNode = await gatewayNode.get_child(f"1:{module}/1:EstadoActual")
                state = await stateNode.read_value()
                if (state == 3):  # 3 is the aborted state
                    param_ME = Variant(
                        Value=module, VariantType=VariantType.String)
                    await gatewayNode.call_method("1:ResetModulo", param_ME)
                    self._logger.debug("Reset %s." % module)

    async def resetAllModules(self):
        """Reset modules from aborted or completed state to idle state.
        """
        modules = ["ME_TRANSPORTE", "ME_BASES", "ME_SPINNERS"]
        async with Client(url="opc.tcp://spinners-node-red:54840") as client:
            gatewayNode = client.get_node("ns=1;i=1000")
            for module in modules:
                stateNode = await gatewayNode.get_child(f"1:{module}/1:EstadoActual")
                state = await stateNode.read_value()
                if (state != 0):  # 0 is the idle state
                    param_ME = Variant(
                        Value=module, VariantType=VariantType.String)
                    await gatewayNode.call_method("1:ResetModulo", param_ME)
                    self._logger.debug("Reset %s." % module)

    def __init__(self):
        """Constructor.
        """
        self._eventHandler = None
        self._runningTask = None
        self._logger = logging.getLogger("OpcuaClient")

    async def _receiveLoop(self):
        """Subscribes to equipment module state variables and loops forever.
        Changes in the variables will be sent to event handler by subscription handler.
        """
        async with Client(url="opc.tcp://spinners-node-red:54840") as client:
            gatewayNode = client.get_node("ns=1;i=1000")
            # Subscribe to data
            subscriptionHandler = OpcuaSubscriptionHandler(self._eventHandler)
            subscription = await client.create_subscription(100, subscriptionHandler)
            for module in ["ME_TRANSPORTE", "ME_BASES", "ME_SPINNERS"]:
                stateNode = await gatewayNode.get_child("1:%s/1:EstadoActual" % module)
                await subscription.subscribe_data_change(stateNode)
            self._logger.debug("Subscribed to variables.")
            # Loop forever to keep subscriptions active
            while True:
                await asyncio.sleep(10)

    async def _executeSeveralPhases(self, phases: list[dict]):
        """Launch several phases in parallel.
        Sends event when done:
            {"opcuaEvent": "completedPhases"}

        Args:
            phases (list[dict]): Phases to start, for example:
                [
                {"me": "ME_BASES", "numSrv": 4, "setPoint": None},
                {"me": "ME_TRANSPORTE", "numSrv": 5, "setPoint": 2},
                ...]
        """
        self._logger.debug("Launching phases %s." % phases)
        coroutines = []
        for phase in phases:
            coroutines.append(partial(self._executeOnePhase, phase=phase))

        # Launch phases in parallel.
        # They may be cancelled when aborting phases, raising a CancelledError
        try:
            await asyncio.gather(*[coroutine() for coroutine in coroutines])
            self._logger.debug("Phase execution completed.")
            await self._eventHandler.handleEvent({"opcuaEvent": "completedPhases"})
        except asyncio.CancelledError:
            self._logger.debug("Phase execution cancelled.")

    async def _executeOnePhase(self, phase: dict):
        """Send start event for an equipment phase. Once it is done,
        send reset event to send module back to idle state.

        Args:
            phase (dict): Phase to launch, for example:
                {
                    "me": "EQUIPMENT_MODULE_NAME",
                    "numSrv": 5,
                    "setpoint": 11
                }
        """

        param_ME = Variant(Value=phase["me"], VariantType=VariantType.String)
        param_numSrv = Variant(
            Value=phase["numSrv"], VariantType=VariantType.UInt16)
        
        # Opcua does not let you send a none value
        setpoint = phase["setpoint"]
        if(setpoint == None):
            setpoint = 0
        param_setpoint = Variant(
            Value=setpoint, VariantType=VariantType.UInt32)

        async with Client(url="opc.tcp://spinners-node-red:54840") as client:
            gatewayNode = client.get_node("ns=1;i=1000")
            stateNode = await gatewayNode.get_child(f"1:{phase["me"]}/1:EstadoActual")

            # Check if in state completed or aborted, in that case reset the module before using it
            state = await stateNode.read_value()
            if((state == 2) or (state == 3)):
                self._logger.debug(f"Trying to launch {phase["me"]} but it is in state {state}, resetting.")
                await gatewayNode.call_method("1:CompletarFase", param_ME)
            while((state == 2) or (state == 3)):
                await asyncio.sleep(0.5)
                state = await stateNode.read_value()


            # Start phase
            await gatewayNode.call_method("1:IniciarFase", param_ME, param_numSrv, param_setpoint)
            self._logger.debug("Started %s." % phase["me"])

            # Wait for completion
            state = await stateNode.read_value()
            while (state != 2):  # 2 is state "complete"
                await asyncio.sleep(1)
                state = await stateNode.read_value()

            # Send reset event on completion
            self._logger.debug("%s phase completed, resetting"% phase["me"])
            await gatewayNode.call_method("1:CompletarFase", param_ME)
            while (state == 2):
                await asyncio.sleep(0.5)
                state = await stateNode.read_value()


class OpcuaSubscriptionHandler:
    """Handler for subscribing to opcua data.
    Notifies changes in the data to event handler.
    """

    def __init__(self, eventHandler: any):
        """Constructor.

        Args:
            eventHandler (any): Event handler that will react to the data. Must have method:
                async eventHandler.handleEvent(event: dict)
        """
        self._eventHandler = eventHandler

    async def datachange_notification(self, node: Node, val, data):
        """Callback when subscribed data in the opcua server changes.
        Sends data to event handler as dict:
            {'opcuaEvent': 'receivedData', 'data': {'me': 'ME_TRANSPORTE', 'var': 'EstadoActual', 'value': 0}}

        Args:
            node (Node): Node of the variable that changed.
            val (_type_): Value of the variable that changed.
            data (_type_): 
        """
        equipmentModule = await node.get_parent()
        equipmentModuleName = (await equipmentModule.read_browse_name()).Name
        variableName = (await node.read_browse_name()).Name

        event = {"opcuaEvent": "receivedData"}
        event["data"] = {"me": equipmentModuleName,
                         "var": variableName, "value": val}

        asyncio.create_task(self._eventHandler.handleEvent(event))
