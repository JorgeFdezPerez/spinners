import logging
import copy

from transitions.extensions import AsyncGraphMachine
from functools import partial

RECIPE_SM_GRAPH_FILENAME = "Recipe.png"


class ControlRecipeSM:
    """State machine for executing individual cycles of a control recipe
    """

    def buildControlRecipe(self, masterRecipe: dict, makeGraph: bool = False, paramValues: dict = {}):
        """Sets up a state machine for a control recipe based off a master recipe.

        Args:
            masterRecipe (dict): Master recipe dict:
                {
                    "description" : "aeiou",
                    "states" : ['E0', 'E1', 'E2', ...],
                    "initialState" : "E0",
                    "finalState" : "E5"
                    "actions" : {
                                "E0" : [{"me" : "ME_CODE_1", "numSrv" : numSrv1, "setpoint_param": None, "default_setpoint": None}],
                                "E1" : [{"me" : "ME_CODE_2", "numSrv" : numSrv2, "setpoint_param": None, "default_setpoint": 30},
                                        {"me" : "ME_CODE_3", "numSrv" : numSrv3, "setpoint_param": "PARAM_6_NAME", "default_setpoint": -9.5}, ...]
                                ...
                                },
                    "transitions" : [{"name" : "tran_E0_E1", "initialState" : "E0", "finalState" : E1},
                                     {"name" : "tran_E1_E2", "initialState" : "E1", "finalState" : E2}, ...],
                    "parameters" : {"PARAM_1_NAME" : "PARAM_1_TYPE",
                                    "PARAM_2_NAME" : "PARAM_2_TYPE", ...}
                }

            makeGraph (bool, optional): Save a graph of the state machine. Defaults to False.
            paramValues (dict, optional): Parameter values dict. Defaults to {}. Format is:
                {
                    "PARAM_1_NAME" : Value
                    "PARAM_2_NAME" : Value
                }
        """

        # Turn transitions dicts into lists to use in the state machine
        transitions = []
        for i in masterRecipe["transitions"]:
            transitions.append([i["name"], i["initialState"], i["finalState"]])

        # Initial and final states
        self._initialState = masterRecipe["initialState"]
        self._finalState = masterRecipe["finalState"]

        if (makeGraph):
            graphEngine = "graphviz"
        else:
            graphEngine = "mermaid"

        self._machine = AsyncGraphMachine(
            states=masterRecipe["states"],
            initial=self._initialState,
            transitions=transitions,
            ignore_invalid_triggers=True,
            graph_engine=graphEngine
        )

        # Associate actions to states
        for stateName in masterRecipe["actions"]:
            state = self._machine.get_state(stateName)

            # Get actions (equipment phases to call) from master recipe
            phases = self._getPhasesWithSetpointValues(masterRecipe["actions"][stateName], paramValues)

            debugCallback = partial(
                self._logger.debug, msg="Triggered on_enter callback of %s" % stateName)
            state.add_callback("enter", debugCallback)
            callback = partial(self._fnStartPhases, phases=phases)
            state.add_callback("enter", callback)

        if (makeGraph):
            graph = self._machine.get_combined_graph(title="Recipe")
            graph.draw(filename=RECIPE_SM_GRAPH_FILENAME, format="png")

        # Add an extra transition to reset the state machine internally
        # (will not show up on the graph)
        self._machine.add_transition('init_recipe', '*', self._initialState)

        self._logger.debug("Finished building control recipe state machine")
        self._logger.debug("Has states %s" % self._machine.states.keys())

    async def initControlRecipe(self):
        """Sets initial state (also triggering that state's actions).
        """
        self._logger.debug("Setting initial state %s" % self._machine.initial)

        await self._machine.init_recipe()

    async def advanceState(self):
        """Call this function to advance a state in a recipe (so when equipment phases have been executed).
        Triggers all transitions from the current state, going to the next state
        if there are no additional conditions associated to the transitions.


        Sends event that recipe is done if this function is called from the final state.
        """
        self._logger.debug("Advancing to next state")

        currentState = self._machine.get_model_state(self._machine.model)
        if (currentState.name == self._finalState):
            self._logger.debug("Already in final state")
            await self._fnNotifyFinished()
        else:
            # Getting all valid transitions from current state
            validTransitions = self._machine.get_triggers(currentState)
            # The state machine generates with a lot of transitions.
            # Need to select only the ones that are actually specified in the recipe
            # (they are named tran_E0_E1, tran_E1_E2, ...)
            validTransitions = [
                x for x in validTransitions if x.startswith("tran_")]
            self._logger.debug(
                "Valid transitions after filtering are %s" % validTransitions)
            # Do transition (if there are multiple transitions, they should have been defined
            # with a condition associated so that only one actually executes)
            for transition in validTransitions:
                await self._machine.trigger(transition)

    async def retryState(self):
        """Call this function to start current state's phases again.
        """
        currentState = self._machine.get_model_state()
        self._machine.set_state(currentState)

    def __init__(self, fnStartPhases: callable, fnNotifyFinished: callable):
        """Constructor.

        Args:
            fnStartPhases (callable): Function to call in order to start phases, sent as a list of dicts. should be:
                async fnStartPhases(phases: list[dict]);
                phases = [
                {"me": "ME_BASES", "numSrv": 4, "setPoint": None},
                {"me": "ME_TRANSPORTE", "numSrv": 5, "setPoint": 2},
                ...]
            fnNotifyFinished (callable): Function to call when the current cycle of the control recipe is done. Should be:
                async fnNotifyFinished();
        """
        self._machine = None
        self._fnStartPhases = fnStartPhases
        self._fnNotifyFinished = fnNotifyFinished
        self._logger = logging.getLogger("ControlRecipeSM")

    def _getPhasesWithSetpointValues(self, phasesNoSetpoint: list[dict], paramValues: dict = {}):
        """From a list of equipment phases with optional fields "setpoint_param", "default_setpoint"
        return a list specifying the setpoint value.

        If a param has been specified, prioritises its value.
        If it isn't specified or its value is None, uses the default setpoint.
        If a default setpoint isn't specified, the value is set to None
        (this should be the case for phases that don't use setpoints).

        Args:
            phasesNoSetpoint (list[dict]): List of phases:
                [{"me" : "ME_CODE_2", "numSrv" : numSrv2, "setpoint_param": None, "default_setpoint": 30},
                 {"me" : "ME_CODE_3", "numSrv" : numSrv3, "setpoint_param": "PARAM_2_NAME", "default_setpoint": -9.5}, ...]
            paramValues (dict, optional): Parameter values. Defaults to {}.
                Structured as:
                    {
                    "PARAM_1_NAME" : 40
                    "PARAM_2_NAME" : 50
                    }

        """        
        phases = copy.deepcopy(phasesNoSetpoint)
        # Setpoints for equipment phases, based off master recipe defaults and control recipe parameters:
        for equipmentPhase in phases:
            setpoint = None
            # Check if setpoint can be set from a control recipe parameter
            paramName = equipmentPhase["setpoint_param"]
            if (paramName != None):
                setpoint = paramValues[paramName]

            # If setpoint does not have a value yet,
            # set the default value if it exists
            if (setpoint == None):
                setpoint = equipmentPhase["default_setpoint"]

            # (Setpoint may still have None value if the phase doesn't use a setpoint at all)

            # Store setpoint in phases
            equipmentPhase["setpoint"] = setpoint

            # Remove data that isn't needed to launch the phase
            del equipmentPhase["setpoint_param"]
            del equipmentPhase["default_setpoint"]

        return phases