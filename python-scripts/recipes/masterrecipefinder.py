import asyncio
import copy
from mysqlclient import mysqlQuery


class MasterRecipeFinder:
    """Gets information about all master recipes in mysql database.

    Recipe data is stored as a dict:
    self.masterRecipes = {
        "RECIPE_1" : {
            "states" : ['E0', 'E1', 'E2', ...],
            "actions" : {
                "E0" : [{"me" : "ME_CODE_1", "numSrv" : numSrv1}],
                "E1" : [{"me" : "ME_CODE_2", "numSrv" : numSrv2},
                        {"me" : "ME_CODE_3", "numSrv" : numSrv3}, ...]
                ...
            },
            "transitions" : [{"name" : "tran_E0_E1", "initialState" : "E0", "finalState" : E1},
                             {"name" : "tran_E1_E2", "initialState" : "E1", "finalState" : E2}, ...],
            "initialState" : "E0",
            "finalState" : "E5"
        },
        "RECIPE_2" : {...},
        ...
    }
    """

    async def updateMasterRecipes(self):
        """Queries database and retrieves data about all master recipes.

        The sql client will raise error on timeout or conection error.
        """
        queriedRecipes = dict()

        # Getting names of all master recipes
        recipeNames = await self._queryMasterRecipes()

        for name in recipeNames:
            queriedRecipes[name] = dict()

            # Getting state names
            queriedRecipes[name]["states"] = await self._queryStates(masterRecipeName=name)

            # Getting actions (equipment module and service number) for each state in the recipe
            queriedRecipes[name]["actions"] = dict()
            for state in queriedRecipes[name]["states"]:
                queriedRecipes[name]["actions"][state] = await self._queryActions(
                    masterRecipeName=name,
                    stateName=state
                )

            # Getting transitions
            queriedRecipes[name]["transitions"] = await self._queryTransitions(masterRecipeName=name)

        await self._lock.acquire()
        self._masterRecipes = queriedRecipes
        self._lock.release()

    async def getMasterRecipes(self):
        """Get saved master recipes.

        Returns:
            Dict: Deep copy of recipes dict. Will be None if updateMasterRecipes() has never been called.
        """
        await self._lock.acquire()
        recipes = copy.deepcopy(self._masterRecipes)
        self._lock.release()
        return recipes

    async def updateAndGetMasterRecipes(self):
        """Queries database and retrieves data about all master recipes.

        The sql client will raise error on timeout or conection error.

        Returns:
            Dict: Deep copy of recipes dict.
        """
        await self.updateMasterRecipes()
        return await self.getMasterRecipes()

    def __init__(self):
        """Constructor. Sets up asyncio lock for reading/writing saved recipes.
        """
        self._lock = asyncio.Lock()
        self._masterRecipes = None

    async def _queryMasterRecipes(self):
        """Get all master recipe names. Sql client will raise error on timeout or conection error.

        Returns:
            List[str]: Recipe names.
        """
        recipeNames = await mysqlQuery("""
            SELECT codigo_receta_maestra FROM recetas_maestras;
        """)
        # Query returns names in separate tuples within the recipeNames list - [("RECIPE_1",), ("RECIPE_2"), ...]
        recipeNames = [x[0] for x in recipeNames]
        return recipeNames

    async def _queryStates(self, masterRecipeName: str):
        """Get states belonging to the specified master recipe. Sql client will raise error on timeout or conection error.

        Args:
            masterRecipeName (str): Name of the master recipe (MySQL column "codigo_receta_maestra")

        Returns:
            Tuple[List[str],bool]: States list ["E0", "E1", ...]
        """
        states = await mysqlQuery(
            """
                SELECT nombre
                FROM etapas
                    INNER JOIN recetas_maestras
                        ON etapas.id_receta_maestra = recetas_maestras.id_receta_maestra
                WHERE recetas_maestras.codigo_receta_maestra = %s;
            """,
            (masterRecipeName,)
        )

        # Query returns names in separate tuples within the states list - [("E0",), ("E1"), ...]
        states = [x[0] for x in states]
        return states

    async def _queryActions(self, masterRecipeName: str, stateName: str):
        """Get all actions belonging to the specified state. Sql client will raise error on timeout or conection error.

        Actions are identified by their equipment module code and service number.

        Args:
            masterRecipeName (str): Name of the master recipe (MySQL column "codigo_receta_maestra")
            stateName (str): Name of the state (MySQL column "nombre")

        Returns:
            List[Dict]: List of actions belonging to the specified state.
                The list will have one dict for each action:
                [{"me" : "ME_CODE_1", "numSrv" : "numSrv_1"},
                {"me" : "ME_CODE_2", "numSrv" : "numSrv_2"},
                ... ]
        """
        actions = await mysqlQuery(
            """
            SELECT modulos_equipamiento.codigo_modulo_equipamiento, fases_equipamiento.num_srv
            FROM recetas_maestras
                INNER JOIN etapas
                    ON  recetas_maestras.id_receta_maestra = etapas.id_receta_maestra
                INNER JOIN fases_etapas
                    ON etapas.id_etapa = fases_etapas.id_etapa
                INNER JOIN fases_equipamiento
                    ON fases_etapas.id_fase_equipamiento = fases_equipamiento.id_fase_equipamiento
                INNER JOIN modulos_equipamiento
                    ON fases_equipamiento.id_modulo_equipamiento = modulos_equipamiento.id_modulo_equipamiento
            WHERE recetas_maestras.codigo_receta_maestra = %s
                AND etapas.nombre = %s
            """,
            (masterRecipeName, stateName)
        )

        # Query returns actions as tuples inside of a list - [('ME_CODE_ACTION_1', numSRVaction1), ("ME_CODE", numSRVaction2)]
        actions = [dict(zip(("me", "numSrv"), x)) for x in actions]
        return actions

    async def _queryTransitions(self, masterRecipeName: str):
        """Get transitions of the specified recipe. Sql client will raise error on timeout or conection error.

        Transitions have an initial state, a final state, and an auto-generated name.

        Args:
            masterRecipeName (str): Name of the master recipe (MySQL column "codigo_receta_maestra")

        Returns:
            List[Dict]: List of transitions.
                The list will have one dict for each transition:
                [{'name': 'tran_E0_E1', 'initialState': 'E0', 'finalState': 'E1'},
                {'name': 'tran_E1_E2', 'initialState': 'E1', 'finalState': 'E2'},
                ... ]
        """

        # Initial states of transitions
        initialStates = await mysqlQuery(
            """
            SELECT etapas.nombre
            FROM transiciones
                INNER JOIN etapas
                    ON transiciones.id_etapa_inicial = etapas.id_etapa
                INNER JOIN recetas_maestras
                    ON recetas_maestras.id_receta_maestra = etapas.id_receta_maestra
            WHERE recetas_maestras.codigo_receta_maestra = %s
            """,
            (masterRecipeName,)
        )

        # Final states of transitions
        finalStates = await mysqlQuery(
            """
            SELECT etapas.nombre
            FROM transiciones
                INNER JOIN etapas
                    ON transiciones.id_etapa_final = etapas.id_etapa
                INNER JOIN recetas_maestras
                    ON recetas_maestras.id_receta_maestra = etapas.id_receta_maestra
            WHERE recetas_maestras.codigo_receta_maestra = %s
            """,
            (masterRecipeName,)
        )

        # Queries return names in separate tuples within the lists - [("E0",), ("E1"), ...]
        initialStates = [x[0] for x in initialStates]
        finalStates = [x[0] for x in finalStates]

        # Naming transitions
        transitions = []
        for i in range(len(initialStates)):
            transitions.append(
                {
                    "name": "tran_"+initialStates[i]+"_"+finalStates[i],
                    "initialState": initialStates[i],
                    "finalState": finalStates[i]
                }
            )

        return transitions
