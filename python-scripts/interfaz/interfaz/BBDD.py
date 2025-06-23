import mysql.connector
from sqlalchemy import create_engine

# Conexión usando SQLAlchemy
def obtener_engine():
    # Formato: dialect+driver://usuario:contraseña@host:puerto/base_datos
    #pymysql
    return create_engine("mysql+pymysql://admin:password@spinners-mysql:3306/spinners")

#Conectar con la base de datos MySQL
def conectar_bd():
    return mysql.connector.connect(
        host="spinners-mysql",     
        user="admin",
        password="password",
        database="spinners"
    )

#Consultar y cargar datos con Pandas
import pandas as pd

def obtener_datos(tabla):
    engine = obtener_engine()
    # conexion = conectar_bd()
    consulta = f"SELECT * FROM `{tabla}`"
    df = pd.read_sql(consulta, engine)
    #conexion.close()
    return df

datos_disponibles = [
    "etapas", "fases_equipamiento", "fases_etapas",
    "modulos_equipamiento", "parametros", "recetas_maestras",
    "transiciones", "usuarios", "variables_me"
]