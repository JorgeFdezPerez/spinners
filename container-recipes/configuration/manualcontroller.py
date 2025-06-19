import asyncio


class ManualController:
    async def setEventHandler(self, eventHandler):
        """Set event handler to notify when launching equipment phases
        and when a cycle of the recipe is done.

        Args:
            eventHandler (any): Object that will handle events received. Must have a method:
                eventHandler.handleEvent(event: dict[str,str])
        """
        self._eventHandler = eventHandler

    async def startPhases(self, phases: list[dict]):
        """Start the phases, if there are not already phases running

        Args:
            phases (list[Dict]): Phases to launch, for example:
                [
                {"me": "ME_BASES", "numSrv": 4, "setPoint": None},
                {"me": "ME_TRANSPORTE", "numSrv": 5, "setPoint": 2},
                ...]
        """
        if (not (self._phasesRunning)):
            event = {"manualControllerEvent": "startPhases"}
            event["phases"] = phases
            asyncio.create_task(self._eventHandler.handleEvent(event))
            self._phasesRunning = True

    async def completePhase(self):
        self._phasesRunning = False

    async def abort(self):
        self._phasesRunning = False

    def __init__(self):
        self._phasesRunning = False
