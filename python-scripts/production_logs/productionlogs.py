import asyncio

from jsonsocketserver import JsonSocketServer
from mysqlclient import mysqlQuery

PORT = 10001


class EventHandler:
    """Event handler. Recieves events in a queue and performs sql queries to react to them.

    Events are dicts, with first key { "EVENT_TYPE" : "EVENT_CODE" }
    """
    async def handleEvent(self, event: dict[str, str]):
        """Add event to queue

        Args:
            event (dict[str,str]): Event to add.
                Dict with first key { "EVENT_TYPE" : "EVENT_CODE" }. Events can optionally have more keys (params, etc).
        """
        await self._eventQueue.put(event)

    async def loop(self):
        """Endless loop. Read events from event queue. Type can be "hmiEvent".
        """    
        while True:
            event = await self._eventQueue.get()
            if (isinstance(event, dict)):
                type = next(iter(event))

                if (type == "hmiEvent"):
                    if (event[type] == "getControlRecipesList"):
                        list = await self._getControlRecipesList()
                        asyncio.create_task(
                            self._server.sendQueue.put({"list": list}))
                    elif (event[type] == "getControlRecipeDetails"):
                        id = event["controlRecipeID"]
                        details = await self._getControlRecipeDetails(id)
                        asyncio.create_task(
                            self._server.sendQueue.put({"details": details}))

    def __init__(self, socketServer: JsonSocketServer):
        """Constructor.

        Args:
            socketServer (JsonSocketServer): Socket server to communicate with client.
        """        
        self._eventQueue = asyncio.Queue()
        self._server = socketServer

    async def _getControlRecipesList(self):
        """Gets list of control recipes

        Returns:
            List[dict]: Control recipes:
                [
                    {"id": ID_1, "masterRecipe": MASTER_RECIPE_NAME_1, "date": DATE_1},
                    {"id": ID_2, "masterRecipe": MASTER_RECIPE_NAME_2, "date": DATE_2},
                    ...
                ]
        """
        controlRecipes = await mysqlQuery(
            """
            SELECT recetas_control.id_receta_control, recetas_maestras.codigo_receta_maestra,
                recetas_control.fecha_creada
            FROM recetas_control
            INNER JOIN recetas_maestras
                ON recetas_control.id_receta_maestra = recetas_maestras.id_receta_maestra
            """
        )
        # Values are a list of tuples [(ID_1,RECIPE_NAME_1,DATE_1),(ID_2,RECIPE_NAME_2,DATE_2),...]
        controlRecipes = [dict(zip(("id", "masterRecipe", "date"), x))
                          for x in controlRecipes]
        # Date to string so that it can be encoded by socket server
        for i in controlRecipes:
            i["date"] = str(i["date"])
        return controlRecipes

    async def _getControlRecipeDetails(self, id: int):
        details = await mysqlQuery(
            """
            SELECT recetas_maestras.codigo_receta_maestra, usuarios.nombre,
                recetas_control.fecha_creada, recetas_control.cantidad_producida
            FROM recetas_control
            INNER JOIN recetas_maestras
                ON recetas_control.id_receta_maestra = recetas_maestras.id_receta_maestra
            INNER JOIN usuarios
                ON recetas_control.id_usuario = usuarios.id_usuario
            WHERE recetas_control.id_receta_control = %s
            """,
            (id,)
        )
        details = dict(
            zip(("masterRecipe", "user", "date", "produced"), details[0]))
        # Date to string so that it can be encoded by socket server
        details["date"] = str(details["date"])
        paramValues = await mysqlQuery(
            """
            SELECT parametros.nombre, valores_parametros.valor
            FROM valores_parametros
            INNER JOIN parametros
                ON parametros.id_parametro = valores_parametros.id_parametro
            WHERE valores_parametros.id_receta_control = %s
            """,
            (id,)
        )
        paramValuesDict = {}
        # param values are returned as [("P_1_NAME","P_1_VALUE"),(...),...]
        for i in paramValues:
            paramValuesDict[i[0]] = i[1]
        details["parameterValues"] = paramValuesDict

        alarms = await mysqlQuery(
            """
            SELECT id_alarma,descripcion,fecha
            FROM alarmas
            WHERE id_receta_control = %s
            """,
            (id,)
        )
        alarmsDict = {}
        for i in alarms:
            alarmsDict[str(i[0])] = {"description":i[1],"date":str(i[2])}
        details["alarms"] = alarmsDict

        return details

async def main():
    await asyncio.sleep(5)
    
    server = JsonSocketServer(PORT)
    eventHandler = EventHandler(server)
    server._eventHandler = eventHandler
    await server.start(eventHandler=eventHandler)
    await eventHandler.loop()

asyncio.run(main())
