import asyncio
from mysql.connector.aio import connect
from typing import Sequence


async def mysqlQuery(query: str, params: Sequence[any] = None, user="admin", password="password", host="spinners-mysql", database: str = "spinners"):
    """Connect to mysql, execute query, commit and disconnect. Raises error on timeout or conection error.
    
    Args:
        query (str): SQL Query to execute.
        params (Sequence[any], optional): Params for query, if needed. Defaults to None.
        user (str, optional): Defaults to "admin".
        password (str, optional): Defaults to "password".
        host (str, optional): Defaults to "host".
        database (str, optional):  Defaults to "spinners".

    Returns:
        List[Any]: Results
    """
    # Connect to a MySQL server
    cnx = await asyncio.wait_for(
        connect(
            user=user,
            password=password,
            host=host,
            database=database),
        5
    )
    # Get a cursor
    cur = await cnx.cursor()

    # Execute a non-blocking query
    await cur.execute(query, params)

    # Retrieve the results of the query asynchronously
    results = await cur.fetchall()

    # Commit changes
    await cnx.commit()

    # Close cursor and connection
    await cur.close()
    await cnx.close()

    return results

async def mysqlMultipleQueries(query: str, params: Sequence[any] = None, user="admin", password="password", host="spinners-mysql", database: str = "spinners"):
    """Connect to mysql, execute query, commit and disconnect. Raises error on timeout or conection error.

    Args:
        query (str): SQL Query to execute.
        params (Sequence[any], optional): Params for query, if needed. Defaults to None.
        user (str, optional): Defaults to "admin".
        password (str, optional): Defaults to "password".
        host (str, optional): Defaults to "host".
        database (str, optional):  Defaults to "spinners".

    Returns:
        List[List[Any]]: List of results for each statement in order
    """
    # Connect to a MySQL server
    cnx = await asyncio.wait_for(
        connect(
            user=user,
            password=password,
            host=host,
            database=database),
        5
    )
    # Get a cursor
    cur = await cnx.cursor()

    # Execute a non-blocking query
    await cur.execute(query, params)

    # Retrieve the results of the query asynchronously
    results = []
    async for statement, result_set in cur.fetchsets():
        results.append(result_set)

    # Commit changes
    await cnx.commit()

    # Close cursor and connection
    await cur.close()
    await cnx.close()

    return results

async def mysqlTestConnection(user="admin", password="password", host="spinners-mysql", database: str = "spinners"):
    """Connect and disconnect from mysql server to check if it is active.
    Raises error on timeout or conection error

    Args:
        user (str, optional): Defaults to "admin".
        password (str, optional): Defaults to "password".
        host (str, optional): Defaults to "spinners-mysql".
        database (str, optional): Defaults to "spinners".

    Returns:
        bool: True if connection was established. False if timeout.
    """
    cnx = await asyncio.wait_for(
        connect(
            user=user,
            password=password,
            host=host,
            database=database),
        5
    )
    await cnx.close()
