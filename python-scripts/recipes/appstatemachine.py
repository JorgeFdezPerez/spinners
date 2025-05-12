import enum
import asyncio
from transitions.extensions import HierarchicalAsyncGraphMachine


class States(enum.Enum):
    starting = 0
    active = 1
    stopped = 2
    waitingToReset = 3
    resetting = 4
    idle = 5
    controllingManually = 6
    producingBatch = 7


APP_SM_GRAPH_FILENAME = "App state machine.png"


class AppSM:
    """Highest level state machine, for controlling start, stop, modes, etc. of the recipe management application.

    See diagram in "App state machine.png".

    Attributes:
        machine (HierarchicalAsyncGraphMachine): State machine. Call these functions to transition:
            startedApp()
            fatalError()
            retryStartingApp()
            resetPlant()
            resetComplete()
            recipeSelected()
            manualSelected()
            recipeDone()
    """

    async def start(self, eventHandler: any):
        """Start machine by reentering the initial state (starting). This activates the on_enter action.
        Also sets event handler to be used.

        Args:
            eventHandler (any): Object that will handle events received. Must have a method:
                eventHandler.handleEvent(event: dict[str,str])
        """
        self._eventHandler = eventHandler
        if(self._eventHandler == None):
            raise TypeError("Event handler was not set")
        await self.machine.to_starting()


    def __init__(self, makeGraph: bool = False):
        self._eventHandler = None

        # States
        # Executing a recipe (TEMP - replace with lower level HSM for recipe execution)
        producingBatchState = States.producingBatch

        activeState = {
            "name": States.active,
            "children": [
                States.waitingToReset,  # Entry point of active.
                States.resetting,  # Resetting plant to initial state
                States.idle,  # Awaiting orders from HMI
                States.controllingManually,  # Manual control of plant by calling services
                producingBatchState  # Running a recipe
            ]
        }
        self._states = [
            States.starting,  # Initial steps, ie start socket server, connect to OPC, connect to SQL
            activeState,  # Ready to be used
            States.stopped  # Due to some fatal error, such as lost connection to plant
        ]

        if (makeGraph):
            graphEngine = "graphviz"
        else:
            graphEngine = "mermaid"

        self.machine = HierarchicalAsyncGraphMachine(
            states=self._states,
            initial=States.starting,
            # When an event ocurrs that shouldn't trigger a transition, don't launch an exception
            ignore_invalid_triggers=True,
            graph_engine=graphEngine)

        # Transitions
        # Once initial steps are done, go to active - enter at waiting to reset
        self.machine.add_transition(
            "startedApp", States.starting, States.waitingToReset
        )
        # On fatal error, stop
        self.machine.add_transition(
            "fatalError", [States.starting, States.active], States.stopped
        )
        # Retry from stop
        self.machine.add_transition(
            "retryStartingApp", States.stopped, States.starting
        )
        # Start resetting plant
        self.machine.add_transition(
            "resetPlant", [States.waitingToReset,
                           States.controllingManually], States.resetting
        )
        # Plant has reached initial conditions
        self.machine.add_transition(
            "resetComplete", States.resetting, States.idle
        )
        # Recipe has been selected and parametrised
        self.machine.add_transition(
            "recipeSelected", States.idle, States.producingBatch
        )
        # Manual control has been selected
        self.machine.add_transition(
            "manualSelected", States.idle, States.controllingManually
        )
        # TEMP - CHANGE LATER
        self.machine.add_transition(
            "recipeDone", States.producingBatch, States.idle
        )

        # Actions
        self.machine.on_enter_starting(self._onEnterStarting)
        self.machine.on_enter_stopped(self._onEnterStopped)
        self.machine.on_enter_active_waitingToReset(self._onEnterWaitingToReset)
        self.machine.on_enter_active_resetting(self._onEnterResetting)
        self.machine.on_enter_active_idle(self._onEnterIdle)
        self.machine.on_enter_active_controllingManually(self._onEnterControllingManually)
        self.machine.on_exit_active_controllingManually(self._onExitControllingManually)
        self.machine.on_enter_active_producingBatch(self._onEnterProducingBatch)

        if (makeGraph):
            graph = self.machine.get_combined_graph(title="App state machine")
            graph.draw(filename=APP_SM_GRAPH_FILENAME, format="png")

    async def _onEnterStarting(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "enterStarting"})

    async def _onEnterStopped(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "enterStopped"})

    async def _onEnterWaitingToReset(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "enterWaitingToReset"})
        
    async def _onEnterResetting(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "enterResetting"})

    async def _onEnterIdle(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "enterIdle"})

    async def _onEnterControllingManually(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "enterControllingManually"})

    async def _onExitControllingManually(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "exitControllingManually"})

    async def _onEnterProducingBatch(self):
        await self._eventHandler.handleEvent({"appSMEvent" : "enterProducingBatch"})
