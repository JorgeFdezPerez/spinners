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
    executingRecipe = 7


class AppStateMachine:
    """Highest level state machine, for controlling start, stop, modes, etc. of the recipe management application.
    """

    def __init__(self):
        # Executing a recipe (TEMP - replace with lower level HSM for recipe execution)
        executingRecipeState = States.executingRecipe

        activeState = {
            "name": States.active,
            "children": [
                States.waitingToReset,  # Entry point of active.
                States.resetting,  # Resetting plant to initial state
                States.idle,  # Awaiting orders from HMI
                States.controllingManually,  # Manual control of plant by calling services
                executingRecipeState  # Running a recipe
            ]
        }
        self._states = [
            States.starting,  # Initial steps, ie start socket server, connect to OPC, connect to SQL
            activeState,  # Ready to be used
            States.stopped  # Due to some fatal error, such as lost connection to plant
        ]

        self.machine = HierarchicalAsyncGraphMachine(
            states=self._states, initial=States.starting, graph_engine="graphviz")

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
            "recipeSelected", States.idle, States.executingRecipe
        )
        # Manual control has been selected
        self.machine.add_transition(
            "manualSelected", States.idle, States.controllingManually
        )
        # TEMP - CHANGE LATER
        self.machine.add_transition(
            "recipeDone", States.executingRecipe, States.idle
        )


async def main():
    sm = AppStateMachine()
    print(sm.machine.state)
    await sm.machine.startedApp()
    print(sm.machine.state)

    graph = sm.machine.get_combined_graph(title = "App state machine")
    graph.draw(filename = "App state machine.png", format="png")


asyncio.run(main())
