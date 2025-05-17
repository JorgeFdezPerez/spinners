import asyncio
import logging

from transitions.extensions import AsyncGraphMachine

from masterrecipefinder import MasterRecipeFinder
from controlrecipesm import ControlRecipeSM


class RecipeHandler:
    async def setEventHandler(self, eventHandler):
        """Set event handler to notify when launching equipment phases
        and when a cycle of the recipe is done.

        Args:
            eventHandler (any): Object that will handle events received. Must have a method:
                eventHandler.handleEvent(event: dict[str,str])
        """
        self._eventHandler = eventHandler

    async def getMasterRecipes(self):
        """Update master recipes from mysql database and return dict with information about them.

        Returns:
            Dict: Dictionary containing high level information about the recipes. Structured like:
                {
                    "RECIPE_NAME_1" : {
                        "description" : "abcd",
                        "parameters" : {"PARAM_1_NAME" : "PARAM_1_TYPE",
                                        "PARAM_2_NAME" : "PARAM_2_TYPE", ...}},
                    "RECIPE_NAME_2 : {...},
                    ...
                }
        """

        # TODO: Handle timeout error

        self._logger.debug("Getting master recipes")
        self._masterRecipes = await self._finder.updateAndGetMasterRecipes()

        recipeInfo = {}
        for recipeName in self._masterRecipes:
            recipeInfo[recipeName] = {}
            recipeInfo[recipeName]["description"] = self._masterRecipes[recipeName]["description"]
            recipeInfo[recipeName]["parameters"] = self._masterRecipes[recipeName]["parameters"]
        return recipeInfo

    async def startControlRecipe(self, masterRecipeName: str, logInDatabase: bool = True, params: dict = {}):
        """Start execution of a control recipe based off a master recipe.

        Send special parameter "REPETICIONES" to specify number of loops (defaults to 1).

        Args:
            masterRecipeName (str): Recipe to execute
            logInDatabase (bool, optional): Store control recipe in database. Defaults to True.
                Set to false for things like resets.
            params (dict, optional): Parameters to use. Defaults to {}. Format:
                {
                    "PARAM_1_NAME" : Value
                    "PARAM_2_NAME" : Value
                }

        Raises:
            TypeError: "Master recipes are not loaded." if getMasterRecipes wasn't called.
            TypeError: "Event handler not set." if setEventHandler wasn't called.
        """
        if (self._masterRecipes == None):
            raise TypeError("Master recipes are not loaded.")
        if (self._eventHandler == None):
            raise TypeError("Event handler not set.")

        self._logger.debug("Starting control recipe based on %s"% masterRecipeName)

        self._logInDatabase = logInDatabase
        self._paused = False
        self._transitionOnUnpause = False
        self._completedCycles = 0

        # Number of cycles to do, based off param named "REPETICIONES"
        if ("REPETICIONES" in params):
            self._maxCycles = params["REPETICIONES"]
        else:
            self._maxCycles = 1
        
        self._logger.debug("Number of cycles will be %s"% self._maxCycles)

        masterRecipe = self._masterRecipes[masterRecipeName]
        self._controlRecipeSM.buildControlRecipe(
            masterRecipe=masterRecipe,
            makeGraph=False,
            params=params
        )

        if (self._logInDatabase):
            # TODO: Create initial entry for recipe
            pass
        else:
            pass
        
        await self._controlRecipeSM.initControlRecipe()

    async def transitionControlRecipe(self):
        """Call function when current state's phases are done to transition to the next state
        """
        if (self._paused):
            self._logger.debug("Control recipe state finished while paused. Remembering for later.")
            # Remember that phases are already done when unpausing
            self._transitionOnUnpause = True
        else:
            self._logger.debug("Going to next state in control recipe.")
            await self._controlRecipeSM.advanceState()

    async def pauseControlRecipe(self):
        """Pause control recipe execution.

        Currently launched phases will finish running, then it will stop.
        """
        self._paused = True

    async def unpauseControlRecipe(self):
        """Resume control recipe execution.
        """
        self._paused = False
        if (self._transitionOnUnpause):
            self._transitionOnUnpause = False
            await self._controlRecipeSM.advanceState()

    def __init__(self):
        """Constructor.
        """
        self._finder = MasterRecipeFinder()
        self._controlRecipeSM = ControlRecipeSM(
            fnStartPhases=self._startPhases,
            fnNotifyFinished=self._onCycleFinished
        )
        self._logger = logging.getLogger("RecipeHandler")
        self._eventHandler = None

        self._masterRecipes = None

        self._paused = False
        self._transitionOnUnpause = False
        self._completedCycles = 0
        self._maxCycles = 0
        self._logInDatabase = True

    async def _onCycleFinished(self):
        """Send message to event handler to notify that a cycle of the recipe has been
        finished.

        Starts a new cycle if all cycles aren't done yet.

        If all cycles are done, also sends a finished all event.

        Stores information in mysql database if logInDatabase was set to true when starting the recipe.

        Events sent:
            {"recipeHandlerEvent": "finishedCycle"}
            {"recipeHandlerEvent": "finishedAllCycles"}
        """

        # TODO: log in database

        await self._eventHandler.handleEvent({"recipeHandlerEvent": "finishedCycle"})

        self._completedCycles = self._completedCycles + 1
        if (self._completedCycles == self._maxCycles):
            self._logger.debug("Completed final cycle.")
            await self._eventHandler.handleEvent({"recipeHandlerEvent": "finishedAllCycles"})
        else:
            self._logger.debug("Completed one cycle.")
            self._controlRecipeSM.initControlRecipe()

    async def _startPhases(self, phases: dict):
        """Send phases dict to event handler in order to start them.
        Function is sent as a callback to _controlRecipeSM to trigger
        phases according to the state machine.

        Will send the dict:
            {"recipeHandlerEvent": "startPhases", "phases": [...]}

        Args:
            phases (list[Dict]): Phases to launch, for example:
                [
                {"me": "ME_BASES", "numSrv": 4, "setPoint": None},
                {"me": "ME_TRANSPORTE", "numSrv": 5, "setPoint": 2},
                ...]
        """
        self._logger.debug("Starting phases %s"% phases)
        event = {"recipeHandlerEvent": "startPhases"}
        event["phases"] = phases
        asyncio.create_task(self._eventHandler.handleEvent(event))
