import asyncio

from mysqlclient import mysqlQuery, mysqlMultipleQueries


class ControlRecipeStorer:
    """Logs control recipes in database
    """

    async def storeNewControlRecipe(self, masterRecipeName: str, username: str, paramValues: dict):
        """Creates a database entry for a new control recipe.

        Args:
            recipe (str): Master recipe it is based on
            username (str): Username of person who executed the control recipe
            paramValues (dict): Value of each parameter:
                {
                    "PARAM_1_NAME" : Value
                    "PARAM_2_NAME" : Value
                }
        """
        masterRecipeID = await mysqlQuery(
            """
                SELECT id_receta_maestra
                FROM recetas_maestras
                WHERE recetas_maestras.codigo_receta_maestra = %s
            """,
            (masterRecipeName,)
        )
        # Query returns ID as tuple inside a list - [(masterRecipeID,)]
        masterRecipeID = masterRecipeID[0][0]
        userID = await mysqlQuery(
            """
                SELECT id_usuario
                FROM usuarios
                WHERE usuarios.nombre = %s
            """,
            (username,)
        )
        # Query returns ID as tuple inside a list - [(userID,)]
        userID = userID[0][0]

        # Inserting new control recipe
        controlRecipeID = await mysqlMultipleQueries(
            """
                INSERT INTO recetas_control
                    (id_receta_maestra, id_usuario, cantidad_producida)
                VALUES
                    (%s, %s, 0);

                SELECT LAST_INSERT_ID();
            """,
            (masterRecipeID, userID)
        )
        # Query returns two results. ID of the newly stored recipe is a tuple inside a list in the second result - [[],[(controlRecipeID,)]]
        self._currentControlRecipe = controlRecipeID[1][0][0]

        # Store parameters values used in control recipe
        for param_name, param_value in paramValues.items():
            paramID = await mysqlQuery(
                """
                SELECT parametros.id_parametro
                FROM parametros
                INNER JOIN recetas_maestras
                    ON parametros.id_receta_maestra = recetas_maestras.id_receta_maestra
                WHERE parametros.nombre = %s
                """,
                (param_name,)
            )
            # Query returns ID as tuple inside a list - [(paramID,)]
            paramID = paramID[0][0]
            await mysqlQuery(
                """
                INSERT INTO valores_parametros
                    (id_parametro, id_receta_control, valor)
                VALUES
                    (%s,%s,%s)
                """,
                (paramID, masterRecipeID, str(param_value))
            )

    async def setCurrentRecipeProducedAmount(self, amount: int):
        """Update the produced amount of the current recipe (mysql column "cantidad_producida").

        Args:
            amount (int): New value for produced amount.
        """        
        await mysqlQuery(
            """
                UPDATE recetas_control
                SET cantidad_producida = %s
                WHERE recetas_control.id_receta_control = %s
            """,
            (amount, self._currentControlRecipe)
        )

    async def addCurrentRecipeAlarm(self, description: str):
        await mysqlQuery(
            """
                INSERT INTO alarmas
                    (id_receta_control, descripcion)
                VALUES
                    (%s,%s)
            """,
            (self._currentControlRecipe, description)
        )

    def __init__(self):
        self._currentControlRecipe = None
