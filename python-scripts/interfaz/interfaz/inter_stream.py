import streamlit as st
import asyncio
import json
import threading
import queue
import time
from jsonsocketclient import JsonSocketClient, iniciar_cliente_socket
from opcua import Client
from variables import (
    NODES_ESTADO,
    SERVICIOS,
    POS,
    DETECT_BASES,
    DETECT_SPINNERS,
    DETECT_TRANSPORTE,
    ALARM_BASES,
    ALARM_SPINNERS,
    ALARM_TRANSPORTE,
)
from BBDD import obtener_datos, datos_disponibles


#Interfaz
st.set_page_config(layout="wide")
st.title("Interaz")
st.subheader("Conexión OPC UA")

###############3# Configuración del servidor OPC############################
OPC_SERVER_URL = "opc.tcp://spinners-node-red:54840"


#OPC Client 
class OpcClient:
    def __init__(self):
        self.client = None

    def connect(self, url):
        self.client = Client(url)
        self.client.connect()

    def disconnect(self):
        if self.client:
            self.client.disconnect()
            self.client = None

    def read_node(self, node_id):
        try:
            node = self.client.get_node(node_id)
            return node.get_value()
        except Exception as e:
            return f"Error: {e}"

#Inicializar el cliente OPC
if "opc_client" not in st.session_state:
    st.session_state.opc_client = OpcClient()
    st.session_state.connected = False


#Conexión OPC UA
if not st.session_state.connected:
    if st.button("Conectar al servidor OPC"):
        try:
            st.session_state.opc_client.connect(OPC_SERVER_URL)
            st.session_state.connected = True
            st.success("Conectado correctamente.")
        except Exception as e:
            st.error(f"Error al conectar: {e}")
else:
    if st.button("Desconectar"):
        st.session_state.opc_client.disconnect()
        st.session_state.connected = False
        st.success("Desconectado.")

#Método para traducir Estado Actual
def estado_to_text(valor):
    if valor == 0:
        return "None"
    elif valor == 1:
        return "Running"
    elif valor == 2:
        return "Complete"
    elif valor == 3:
        return "Aborted"
    else:
        return "Sin datos"

#Método para traducir Servicio Actual
def servicio_to_text(mod, valor):
    if not isinstance(valor, int):
        return "Sin datos"

    if mod == "BASES":
        return {
            0: "None",
            1: "Extender base",
            2: "Rearme"
        }.get(valor, "Sin datos")

    elif mod == "SPINNERS":
        return {
            0: "None",
            1: "Dispensar spinner",
            2: "Rearme"
        }.get(valor, "Sin datos")

    elif mod == "TRANSPORTE":
        return {
            0: "None",
            1: "Coger base",
            2: "Posar base",
            3: "Ir a posición",
            4: "Ir a estación",
            5: "Coger spinner",
            6: "Rearme posición neutra",
            7: "Rearme dejar pieza"
        }.get(valor, "Sin datos")

    return "Sin datos"

#Método Led
def led_html(valor):
    color = "green" if valor else "gray" if valor == 0 else "red"
    return f"<span style='display:inline-block; width:20px; height:20px; border-radius:50%; background:{color}; margin-right:10px'></span>"

#Método valor led
def valor_led(val):
    cols = st.columns(len(val))
    for col, (nombre, node_id) in zip(cols, val.items()):
        valor = st.session_state.opc_client.read_node(node_id)
        col.markdown(f"{led_html(valor)} **{nombre}**", unsafe_allow_html=True)
    
        

# Lectura de nodos
if st.session_state.connected:

        #Botones de control
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Estado actual")
        
        #Mostrar estados
        for nombre, node_id in NODES_ESTADO.items():
            valor = st.session_state.opc_client.read_node(node_id)
            texto = estado_to_text(valor) if isinstance(valor, int) else valor
            color = "green" if valor == 1 else "gray" if valor == 0 else "red"
            st.markdown(f"**{nombre}**: <span style='color:{color}; font-weight:bold'>{texto}</span>", unsafe_allow_html=True)

    with col2:
        st.subheader("Servicio actual")
        # Mostrar servicios
        for nombre, (modulo, node_id) in SERVICIOS.items():
            valor = st.session_state.opc_client.read_node(node_id)
            texto = servicio_to_text(modulo, valor)
            st.markdown(f"**{nombre}**: {texto}")

    with col3:
        st.subheader("Posición actual")
        # Mostrar posición
        for nombre, node_id in POS.items():
            valor = st.session_state.opc_client.read_node(node_id)
            st.markdown(f"**{nombre}**: {valor}")

    st.subheader("Detectores del Módulo de Bases")
    valor_led(DETECT_BASES)

    st.subheader("Detectores del Módulo de Spinners")
    valor_led(DETECT_SPINNERS)

    st.subheader("Detectores del Módulo de Transporte")
    valor_led(DETECT_TRANSPORTE)

    st.subheader("Alarmas del Módulo de Bases")
    valor_led(ALARM_BASES)

    st.subheader("Alarmas del Módulo de Spinners")
    valor_led(ALARM_SPINNERS)

    st.subheader("Alarmas del Módulo de Transporte")
    valor_led(ALARM_TRANSPORTE)
    


############################ Visualización de la BBDD#######################################
st.subheader("Base de Datos MySQL")


#Menú desplegable para seleccionar la tabla
tabla_seleccionada = st.selectbox("Selecciona la tabla que deseas visualizar:", datos_disponibles)

    
try:
    df = obtener_datos(tabla_seleccionada)
    if not df.empty:
        st.write("Registros encontrados:")
        st.dataframe(df)
    else:
        st.info("La base de datos no contiene registros.")
except Exception as e:
    st.error(f"Error al consultar la base de datos: {e}")



#################################Interfaz de Control#########################################3

st.subheader("Interfaz de Control")


# Estado inicial

#Mensajes visibles en la interfaz
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "mensaj" not in st.session_state:
    st.session_state.mensaj = []

#Inicialización de hilo cliente
if "cliente_thread_iniciado" not in st.session_state:
    st.session_state.cliente_thread_iniciado = False

#Confirmación de conexión a servidor
if "conectado" not in st.session_state:
    st.session_state.conectado = False
if "conectado2" not in st.session_state:
    st.session_state.conectado2 = False

#Captura de evento y mensaje por cada hilo
if "evento_queue" not in st.session_state:
    st.session_state.evento_queue = queue.Queue()
if "mensaje_queue" not in st.session_state:
    st.session_state.mensaje_queue = queue.Queue()

if "evento_queue2" not in st.session_state:
    st.session_state.evento_queue2 = queue.Queue()
if "mensaje_queue2" not in st.session_state:
    st.session_state.mensaje_queue2 = queue.Queue()

#Recetas, usuarios y parámetros
if "recetas" not in st.session_state:
    st.session_state.recetas = []
if "users" not in st.session_state:
    st.session_state.users = []
if "parametros" not in st.session_state:
    st.session_state.parametros = []

#Información de informes
if "recetas_informes" not in st.session_state:
    st.session_state.recetas_informes = []

#Interfaz
#Botón para conectar a los servidores
if not st.session_state.conectado and not st.session_state.conectado2:
    if st.button("Conectar a los servidores"):
        iniciar_cliente_socket(
            nombre_servidor="spinners-recipes",
            evento_queue=st.session_state.evento_queue,
            mensaje_queue=st.session_state.mensaje_queue,
            puerto= 10000
        )
        st.session_state.conectado = True
        st.success("Conectado al servidor Recetas")
        if not st.session_state.cliente_thread_iniciado:
            iniciar_cliente_socket(
                nombre_servidor="spinners-production-logs",
                evento_queue=st.session_state.evento_queue2,
                mensaje_queue=st.session_state.mensaje_queue2,
                puerto= 10001
            )
            st.session_state.conectado2 = True
            st.session_state.cliente_thread_iniciado = True
            st.success("Conectado al servidor Informes")

#Botones de control
col1, col2, col3, col4, col5, col6 = st.columns(6)


with col1:
    if st.button("Rearmar"):
        st.session_state.evento_queue.put({"hmiEvent":"resetPlant"})

with col2:
    if st.button("Recetas y usuarios"):
        st.session_state.evento_queue.put({"hmiEvent":"getRecipes"})
        st.session_state.evento_queue.put({"hmiEvent":"getUsers"})

with col3:
    if st.button("Pausa"):
        st.session_state.evento_queue.put({"hmiEvent":"pause"})

with col4:
    if st.button("Reanudar"):
        st.session_state.evento_queue.put({"hmiEvent":"unpause"})        

with col5:
     if st.button("Continuar última receta"):
        st.session_state.evento_queue.put({"hmiEvent":"continueLastRecipe"})

with col6:
    if st.button("Parada de Emergencia"):
        st.session_state.evento_queue.put({"hmiEvent":"emergencyStop"})


st.subheader("Modo manual")

#Estado para mostrar el modo manual
if "mostrar_control_manual" not in st.session_state:
    st.session_state.mostrar_control_manual = False

col9, = st.columns(1)
with col9:
    if st.button("Control manual"):
        st.session_state.evento_queue.put({"hmiEvent":"startManualControl"})
        st.session_state.mostrar_control_manual = True

if st.session_state.mostrar_control_manual:
    
    #Cargar datos desde las tablas necesarias
    try:
        df_modulos = obtener_datos("modulos_equipamiento")
        df_fases = obtener_datos("fases_equipamiento")
        
    except Exception as e:
        st.error(f"No se pudo cargar la información: {e}")
    else:
        #Desplegables
        modulos_dict = dict(zip(df_modulos["codigo_modulo_equipamiento"], df_modulos["id_modulo_equipamiento"])) 
        modulo = st.selectbox("Selecciona el módulo de equipamiento", list(modulos_dict.keys()))
        modulo_id = modulos_dict[modulo]

        fases_filtradas = df_fases[df_fases["id_modulo_equipamiento"] == modulo_id]
        
        if fases_filtradas.empty:
            st.warning("No hay fases asociadas a este módulo.")
        else:
            fases_dict = dict(zip(fases_filtradas["descripcion"], df_fases["num_srv"]))
            fase = st.selectbox("Selecciona la fase de equipamiento", list(fases_dict.keys()))
            fase_srv = fases_dict[fase] 
        
        setpoint: int
        if fase_srv == 3:
            setpoint = st.slider("Selecciona un valor", min_value=0, max_value=199500, value=0, step=1)
        elif fase_srv == 4:
            setpoint = st.slider("Selecciona un valor", min_value=0, max_value=10, value=0, step=1)
        else:
            setpoint = None
    

        #Botón para ejecutar
        if st.button("Ejecutar acción manual"):
            mensaje_manual = {
                "hmiEvent": "startManualPhases",
                "phases":[
                    {"me": modulo,"numSrv": fase_srv,"setpoint": setpoint}
                ]
            }
            st.session_state.evento_queue.put(mensaje_manual)
            st.success(f"Enviado: {mensaje_manual}")

#Mostrar estados en tiempo real
st.subheader("Mensajes y eventos del servidor de recetas")
output_area = st.empty()

#Mostrar el desplegable solo cuando ya hay recetas y usuarios cargados
if st.session_state.recetas and st.session_state.users:
    st.subheader("Panel para lanzar receta")
    receta_seleccionada = st.selectbox("Selecciona una receta:", st.session_state.recetas)
    usuario_seleccionado = st.selectbox("Selecciona un usuario:", st.session_state.users)
    
    
    #Mostrar los parámetros solo si la receta está en el dict
    receta_actual = st.session_state.parametros.get(receta_seleccionada, {})
    parametros = {}
    
    for param in receta_actual.get("parameters", []):
        nombre_param, tipo_param= param

        if tipo_param == "INT":
            valor = st.number_input(nombre_param, min_value=0, value=0, max_value=199500, step=1, format="%d")
        elif tipo_param == "FLOAT":
            valor = st.number_input(nombre_param, min_value=0.0, value=0.0, max_value=199500.0, step=0.1, format="%.2f")
        
        parametros[nombre_param]=valor
       
    #Lanzar receta
    if st.button("Lanzar receta"):
        mensaje = {
            "hmiEvent": "runRecipe",
            "recipe": receta_seleccionada,
            "user": usuario_seleccionado,
            "parameters": parametros
        }
        st.session_state.evento_queue.put(mensaje)
        st.success(f"Receta '{receta_seleccionada}' enviada al servidor.")

st.subheader("Panel de informes")
#Sistema de informes
if st.button("Sistema de informes"):
        st.session_state.mensaj.clear() 
        st.session_state.evento_queue2.put({"hmiEvent":"getControlRecipesList"})

mensajes2_box = st.empty()
receta_id: int
if st.session_state.recetas_informes:
        st.subheader("Generación de informe")
    #Mostrar selectbox con los IDs disponibles
        opciones = [f"ID {r['id']} - {r['date']}" for r in st.session_state.recetas_informes]
        seleccion = st.selectbox("Selecciona una receta por ID y fecha:", opciones)
        #Botón para enviar la selección
        if seleccion:
            receta_id = int(seleccion.split()[1])
            if st.button("Enviar"):
                
                mensaje_envio = {
                    "hmiEvent": "getControlRecipeDetails",
                    "controlRecipeID": receta_id
                }
                st.session_state.evento_queue2.put(mensaje_envio)
                st.rerun()
 

new_lines = []
recetas = []
users = []
parametros = []

#Método para el formateo de texto: texbox recetas
def formato(nuevo):
    texto = str(nuevo)
    caracter_elim = "{}'"
    texto = texto.translate(str.maketrans('','', caracter_elim))

    if "info" in texto:
        texto = texto.replace("],", "]],\n")
        texto = texto.replace("recipes:", "\nrecipes:")

        

    st.session_state.mensajes.append(texto)
    new_lines.append(nuevo)

#Método para el formateo de texto: texbox informes
def formato2(nuevo):
    texto = str(nuevo)

    if "}," in texto:
        texto = texto.replace("},", "},\n")

    caracter_elim = "{}'"
    texto = texto.translate(str.maketrans('','', caracter_elim))

    return texto

  
#Bucle para obtener características de recetas
while not st.session_state.mensaje_queue.empty():
    nuevo = st.session_state.mensaje_queue.get()
    formato(nuevo)

    if isinstance(nuevo, dict) and nuevo.get("info") == "recipes":
        recetas_dict = nuevo.get("recipes", {})
        st.session_state.recetas = list(recetas_dict.keys())
        st.session_state.parametros = nuevo.get("recipes", {})
        st.rerun()
    if isinstance(nuevo, dict) and nuevo.get("info") == "users":
        st.session_state.users = nuevo.get("users", {})
        st.rerun()
    



recet: str=""
#Función para parsear los datos
def parsear_mensaje(mensaje):
    recetas = []
    for item in mensaje:
        try:
            recetas.append({
                "id": int(item.get("id", 0)),
                "masterRecipe": item.get("masterRecipe", "Desconocido"),
                "date": item.get("date", "").strip()
            })
        except Exception as e:
            print(f"Error al parsear receta: {e}")
    return recetas


if "fase_informe" not in st.session_state:
    st.session_state.fase_informe = "esperando"

#Bucle para obtener características de informes
while not st.session_state.mensaje_queue2.empty():
    nuevo = st.session_state.mensaje_queue2.get()
    
    if isinstance(nuevo, dict) and "list" in nuevo:
        mensaje_crudo = nuevo["list"]
        recet = parsear_mensaje(mensaje_crudo)  
        st.session_state.recetas_informes = recet
        st.session_state.fase_informe = "mostrar_mensaje"

    nuevo = formato2(nuevo)
    st.session_state.mensaj.append(str(nuevo))
 

 
#Textbox sistema de informes
if st.session_state.mensaj:
    mensajes2_box.code("\n".join(st.session_state.mensaj[-10:]))

#Textbox gestor de recetas
if st.session_state.mensajes:
    output_area.code("\n".join(st.session_state.mensajes[-10:]))
    

#Temporizador de auto-actualización
time.sleep(0.5)
st.rerun()
