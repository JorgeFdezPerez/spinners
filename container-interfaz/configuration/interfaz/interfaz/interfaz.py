"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import asyncio
import logging
import reflex as rx
from opcua import Client
from rxconfig import config
from opcua.common.subscription import Subscription
from threading import Lock
import threading
import time
import socket

from interfaz.jsonsocketclient import JsonSocketClient
import json
import time




opc_lock = Lock()
opc_data = {}
opc_callback = None
main_loop = asyncio.get_event_loop()
current_state = None





cliente = JsonSocketClient()

def start_client():

    async def main():
        
        await cliente.connect()
        
        State.cargar_contenido()
        # Esperar indefinidamente
        while True:

            await asyncio.sleep(1)
            if cliente.message_received_flag:
                State.cargar_contenido()
                cliente.message_received_flag = False
                print("hola")
            #data = await cliente._reader.readuntil(cliente._EOM.encode(cliente._encoding))
            #message = json.loads(data.decode(cliente._encoding).removesuffix(cliente._EOM))
            # Actualiza el estado de Reflex (usa un evento)
            #rx.run_on_ui(State.agregar_mensaje)(json.dumps(message))

    asyncio.run(main())





class SubHandler():
    def __init__(self, callback, loop):
        self.callback = callback
        #self.loop = loop
        #self.callback = opc_callback


    def datachange_notification(self, node, val, data):
        #if opc_callback:
        #    self.callback(node,val)
        #with opc_lock:
        #    opc_data[node.nodeid.Identifier]=val

        # Si el estado está montado y el event loop está corriendo
        print(val)
        print(node)
        #self.callback(node, val)
        
        if current_state is not None:
            print(val)
            coro = current_state.actualizar_estado(node, val)
            asyncio.run_coroutine_threadsafe(coro, main_loop)
        
     
            


# Encapsulamos la lógica OPC
class OpcClient:
    def __init__(self):
        self.client = None
        self.sub = None
        self.handles = []

    def connect(self):
        self.client = Client("opc.tcp://spinners-node-red:54840")
        self.client.connect()

    def subscribe(self, callback, direcciones: list[str], alarmas: list[str]):
        #Se comprueba que el cliente esté conectado
        if self.client:
            global opc_callback
            opc_callback = callback
            node_detect_bases = []
            node_alarmas = []

           
            node_bases = self.client.get_node("ns=1;s=ME_BASES_EstadoActual")  
            node_spinners = self.client.get_node("ns=1;s=ME_SPINNERS_EstadoActual") 
            node_transporte = self.client.get_node("ns=1;s=ME_TRANSPORTE_EstadoActual")
            node_bases_ServAct =  self.client.get_node("ns=1;s=ME_BASES_ServicioActual") 
            node_spinners_ServAct =  self.client.get_node("ns=1;s=ME_SPINNERS_ServicioActual") 
            node_transporte_ServAct =  self.client.get_node("ns=1;s=ME_TRANSPORTE_ServicioActual")
            node_transporte_posAct = self.client.get_node("ns=1;s=ME_TRANSPORTE_PosActual")
            node_transporte_posObj = self.client.get_node("ns=1;s=ME_TRANSPORTE_PosObj")
            
            
            for direccion in direcciones:
                nodo = self.client.get_node(f"ns=1;s={direccion}")
                node_detect_bases.append(nodo)
            
            for alarma in alarmas:
                nodo_alarm = self.client.get_node(f"ns=1;s={alarma}")
                node_alarmas.append(nodo_alarm)

            
            #Crear suscripción
            handler = SubHandler(callback, main_loop)
            self.sub = self.client.create_subscription(100, handler)
            
            #Leer datos
            self.handles=[
                self.sub.subscribe_data_change(node_bases),
                self.sub.subscribe_data_change(node_spinners),
                self.sub.subscribe_data_change(node_transporte),
                self.sub.subscribe_data_change(node_bases_ServAct),
                self.sub.subscribe_data_change(node_spinners_ServAct),
                self.sub.subscribe_data_change(node_transporte_ServAct),
                self.sub.subscribe_data_change(node_transporte_posAct),
                self.sub.subscribe_data_change(node_transporte_posObj),
            ]
             # Añadir los nodos detectores a las suscripciones
            for nodo in node_detect_bases:
                self.handles.append(self.sub.subscribe_data_change(nodo))
            
             # Añadir los nodos alarmas a las suscripciones
            for nodo in node_alarmas:
                self.handles.append(self.sub.subscribe_data_change(nodo))
       
        
    
    def disconnect(self):
        try:
            if self.sub:
                self.sub.delete()
                self.sub = None
            if self.client:
                self.client.disconnect()
                self.client = None
        except Exception as e:
            print(f"Error cerrando cliente OPC UA: {e}")
            

opc = OpcClient()

# Componente visual LED
def led_component(encendido: bool) -> rx.Component:
    return rx.box(
        border_radius="50%",               # un círculo
        width="40px",                      # Tamaño del LED
        height="40px",
        background_color = rx.cond(encendido, "green", "gray"),
        border="2px solid #000",           # Borde negro
        margin="1em",
        transition="background-color 0.3s ease",  # Animación suave al cambiar color
    )


def led_con_etiqueta(nombre: str, encendido: bool) -> rx.Component:
    return rx.vstack(
        led_component(encendido),
        rx.text(nombre, font_size="0.8em"),
        align="center"
    )

#def start_sync_loop():
#    def loop():
#        while True:
#            try:
#                State.sync_from_opc()  # Llamamos el evento Reflex desde backend
#                time.sleep(1)  # cada 1 segundo
#            except Exception as e:
#                print(f"[Sync Error]: {e}")
#                break

#   hilo = threading.Thread(target=loop, daemon=True)
#   hilo.start()



class State(rx.State):

    # Método para actualizar el mensaje desde socket (añadido)
    @rx.event
    async def recibir_mensaje_async(self, texto: str):
        self.mensajes = texto

    """The app state."""

    valores: list[int] = [4, 4, 4]
    pos_trans: list[int] = [0, 0]
    val_ServAct: list[int] = [4, 4, 4]
    errores: list[str] = ["", "", ""]
    leyendo: bool = False
    direccion_detect_bases: list[str] = ["ME_BASES_A0","ME_BASES_A1","ME_BASES_Empty","ME_BASES_Base","ME_BASES_Aminus",
                                        "ME_SPINNERS_A0","ME_SPINNERS_A1","ME_SPINNERS_Base","ME_SPINNERS_TransportePreparadoParaRecogerSpinner", "ME_SPINNERS_Aminus", "ME_SPINNERS_Aplus",
                                        "ME_SPINNERS_SpinnersPreparadoParaDispensar", "ME_SPINNERS_SpinnersAcabadoDeExpulsarBase",
                                        "ME_TRANSPORTE_B0","ME_TRANSPORTE_B1","ME_TRANSPORTE_C0","ME_TRANSPORTE_C1","ME_TRANSPORTE_BPlus", "ME_TRANSPORTE_BMinus",
                                        "ME_TRANSPORTE_CPlus","ME_TRANSPORTE_CMinus","ME_TRANSPORTE_Busy", "ME_TRANSPORTE_INP","ME_TRANSPORTE_Hold","ME_TRANSPORTE_PreparadoParaRecogerSpinner"
                                        ]
    direccion_alarma: list[str] = ["ME_BASES_Alarmas_dos_detect","ME_BASES_Alarma_base","ME_BASES_Alarma_retroceso","ME_BASES_Alarma_avance",
                                    "ME_SPINNERS_ErrorSensoresASimultaneos","ME_SPINNERS_ErrorA0NoActivo","ME_SPINNERS_ErrorA1NoActivo",
                                    "ME_TRANSPORTE_ErrorSensoresBSimultaneos","ME_TRANSPORTE_ErrorSensoresCSimultaneos","ME_TRANSPORTE_ErrorB0NoActivoTransporte",
                                    "ME_TRANSPORTE_ErrorB1NoActivoTransporte","ME_TRANSPORTE_ErrorC0NoActivoTransporte","ME_TRANSPORTE_ErrorC1NoActivoTransporte",
                                    "ME_TRANSPORTE_ErrorMoverConPinzaExtendida","ME_TRANSPORTE_ErrorCogerBaseConPinzaOcupada",
                                    "ME_TRANSPORTE_ErrorDriverNoResponde","ME_TRANSPORTE_ErrorCogerSpinnerSinBase"]

    
    
    detect_bases: list[bool] = [False]*len(direccion_detect_bases) #Incializamos LED
    alarmas: list[bool] = [False]*len(direccion_alarma)
    #posicion: list[bool] = [False]*len(transporte_pos)

    def on_mount(self):
        global current_state
        current_state = self
        print("ok")

  

    #def cambiar_mensaje(self, valor: str):
    #    self.mensaje_a_enviar = valor

    #async def enviar_mensaje(self):
    #    if self.mensaje_a_enviar:
    #        try:
    #            await cliente.send({"mensaje": self.mensaje_a_enviar})
    #            self.mensajes.append(f"Tú: {self.mensaje_a_enviar}")
    #            self.mensaje_a_enviar = ""
    #        except Exception as e:
    #            self.mensajes.append(f"Error al enviar: {e}")


        
    
    mensajes: str = " " 

    def cargar_contenido(self):
        try:
            with open("datos.json", "r") as f:
                data = json.load(f)
                self.mensajes = json.dumps(data, indent=2)
                print("conseguido")
                print(self.mensajes)
        except Exception as e:
            self.mensajes = f"Error al leer el archivo: {str(e)}"

        #self.mensajes.append(nuevo_mensaje)

            
    def result(self):
        return self.mensajes


    @property
    def texto_concatenado(self) -> str:
        return "\n\n---\n\n".join(self.mensajes)

    def comienzo(self):
        # Iniciar el cliente socket en un hilo separado
        client_thread = threading.Thread(target=start_client, daemon=True)
        client_thread.start()


    async def rearmar(self):
        await cliente.send({"hmiEvent":"resetPlant"})
    
    async def list_recipes(self):
        await cliente.send({"hmiEvent":"getRecipes"})

    async def list_users(self):
        await cliente.send({"hmiEvent":"getUsers"})

    async def pause(self):
        await cliente.send({"hmiEvent":"pause"})

    async def unpause(self):
        await cliente.send({"hmiEvent":"unpause"})
        
        
    #@rx.event
    #def sync_from_opc(self):
        #from copy import deepcopy
    #    with opc_lock:
    #        datos = opc_data.copy()
        
    #    nuevos_estados = self.detect_bases[:]
    #    nuevas_alarmas = self.alarmas[:]

    #    for node_id, value in datos.items():
    #        if node_id in self.direccion_detect_bases:
    #            idx = self.direccion_detect_bases.index(node_id)
    #            nuevos_estados[idx] = bool(value)

    #        if node_id in self.direccion_alarma:
    #            idx = self.direccion_alarma.index(node_id)
    #            nuevas_alarmas[idx] = bool(value)

        #if nuevos_estados != self.detect_bases:
    #    self.detect_bases = nuevos_estados
        
        #if nuevas_alarmas != self.alarmas:
    #    self.alarmas = nuevas_alarmas

  


    #@rx.var
    def agrupar_por_modulo(self, direcciones: list[str], estados: list[bool]) -> dict[str, list[tuple[str, bool]]]:
        modulos = {
            "ME_BASES_": [],
            "ME_SPINNERS_": [],
            "ME_TRANSPORTE_": []
        }
        for nombre, estado in zip(direcciones, estados):
            for prefijo in modulos:
                if nombre.startswith(prefijo):
                    limpio = nombre[len(prefijo):]
                    modulos[prefijo].append((limpio, estado))
                    break
        return modulos

    @rx.var
    def lectura_por_modulo(self) -> dict[str, list[tuple[str, bool]]]:
        return self.agrupar_por_modulo(self.direccion_detect_bases, self.detect_bases)

    @rx.var
    def lectura_por_modulo_alarma(self) -> dict[str, list[tuple[str, bool]]]:
        return self.agrupar_por_modulo(self.direccion_alarma, self.alarmas)


    #Método para alterar el estado
    def toggle_led(self, index: int):
        self.detect_bases[index] = not self.detect_bases[index]
    
    @rx.event
    async def actualizar_estado(self, node, value):
        node_id = node.nodeid.Identifier

        valores = self.valores[:]
        val_ServAct = self.val_ServAct[:]
        pos_trans = self.pos_trans[:]
        detect_bases = self.detect_bases[:]
        alarmas = self.alarmas[:]

        if node_id == "ME_BASES_EstadoActual":
            valores[0] = int(value)
        elif node_id == "ME_SPINNERS_EstadoActual":
            valores[1] = int(value)
        elif node_id == "ME_TRANSPORTE_EstadoActual":
            valores[2] = int(value)
        elif node_id == "ME_BASES_ServicioActual":
            val_ServAct[0] = int(value)
        elif node_id == "ME_SPINNERS_ServicioActual":
            val_ServAct[1] = int(value)
        elif node_id == "ME_TRANSPORTE_ServicioActual":
            val_ServAct[2] = int(value) 
        elif node_id == "ME_TRANSPORTE_PosActual":
            pos_trans[0] = int(value) 
        elif node_id == "ME_TRANSPORTE_PosObj":
            pos_trans[1] = int(value) 

        
        for i in range(len(self.direccion_detect_bases)):
            if node_id == self.direccion_detect_bases[i]:
                detect_bases[i] = bool(value)
                
        for i in range(len(self.direccion_alarma)):
            if node_id == self.direccion_alarma[i]:
                alarmas[i] = bool(value)

        self.valores = valores
        self.val_ServAct = val_ServAct
        self.pos_trans = pos_trans
        self.detect_bases = detect_bases
        self.alarmas = alarmas
    
     
         
    
    def iniciar_lectura(self):
        try:
            if opc.client:
                opc.disconnect() #Desconectamos previamente
            opc.connect()
            opc.subscribe(self.actualizar_estado, self.direccion_detect_bases, self.direccion_alarma)
            self.leyendo = True
            self.errores = ["","",""]

            #start_sync_loop()
            
        except Exception as e:
            self.valores = [-1, -1, -1]
            self.val_ServAct = [-1, -1, -1]
            self.pos_trans = [-1, -1]
            self.detect_bases = [False]*len(self.direccion_detect_bases)
            self.alarmas = [False]*len(self.direccion_alarma)
            self.errores = [f"Error:{e}",f"Error:{e}",f"Error:{e}"]
            opc.disconnect()
            self.leyendo = False

    
    def desconectar(self):
        try:
            opc.disconnect()  
            self.leyendo = False
            self.valores = ["Desconectado", "", ""]
            self.val_ServAct = ["Desconectado", "", ""]
        except Exception as e:
            self.valores = [f"Error al desconectar: {e}", "", ""]
            self.val_ServAct = [f"Error al desconectar: {e}", "", ""]
    @rx.var
    def leds(self) -> list[tuple[str, bool]]:
        return list(zip(self.direccion_detect_bases, self.detect_bases))

    tipo_dato: str = "int"
    val_2: int = 0

    def set_tipo_dato(self, tipo):
        self.tipo_dato = tipo
        self.val_2 = 0 if tipo !="bool" else 1
    
    def set_valor_bool(self, val: str):
        self.val_2 = 1 if val == "True" else 0

    def incrementar(self):
        max_val = {
            "int": 2**31 - 1,
            "word": 65535,
            "dword": 4294967295
        }.get(self.tipo_dato, 1)
        if self.val_2 < max_val:
            self.val_2 += 1

    def decrementar(self):
        min_val = {
            "int": -2**31,
            "word": 0,
            "dword": 0
        }.get(self.tipo_dato, 0)
        if self.val_2 > min_val:
            self.val_2 -= 1

    def set_valor(self, val):
        try:
            self.val_2 = int(val)
        except ValueError:
            self.val_2 = 0
    


def render_input():
    return rx.cond(
        State.tipo_dato == "bool",
        rx.select(
            ["True", "False"],
            value=rx.cond(State.val_2 == 1, "True", "False"),
            on_change=State.set_valor_bool,
        ),
        rx.hstack(
            rx.input(
                type_="number",
                value=State.val_2,
                on_change=State.set_valor,
                width="125px"
            ),
            rx.button("+", on_click=State.incrementar, width="35px", color_scheme="green"),
            rx.button("-", on_click=State.decrementar, width="35px", color_scheme="green"),
            spacing="0",
        )
    )
def mostrar_estado(valor, error):
    return rx.cond(
        valor == -1,
        rx.text(error),
        convert_EstadoActual(valor)
      
    )

def mostrar_servicio(Mod,valor, error):
    return rx.cond(
        valor == -1,
        rx.text(error),
        convert_ServicioActual(Mod, valor)  
    )

def convert_EstadoActual(rx_var):
        #None = 0, Running = 1, Complete = 2, Aborted = 3"
    return rx.cond(
        rx_var == 0, "None",
        rx.cond(rx_var == 1, "Running",
        rx.cond(rx_var == 2, "Complete",
        rx.cond(rx_var == 3, "Aborted", "Sin datos")))
    )

def convert_ServicioActual(Mod, rx_var):
        
    if (Mod == "BASES"):
        #Numero de servicio. servicioBases_none=0, servicioBases_extenderBase = 1, servicioBases_rearme = 2
        return rx.cond(
            rx_var == 0, "None",
            rx.cond(rx_var == 1, "Extender base",
            rx.cond(rx_var == 2, "Rearme", "Sin datos"))
    )
    if (Mod == "SPINNERS"):
        #Numero de Servicio. servicioSpinners_none=0, servicioSpinners_dispensarSpinner=1, servicioSpinners_rearme=2
        return rx.cond(
            rx_var == 0, "None",
            rx.cond(rx_var == 1, "Dispensar spinner",
            rx.cond(rx_var == 2, "Rearme", "Sin datos"))
        )
    if(Mod == "TRANSPORTE"):
        #Numero de servicio actual del transporte. None = 0, CogerBase = 1, PosarBase = 2, IrAPosicion = 3, IrAEstacion = 4, CogerSpinner = 5, RearmePosicionNeutra = 6, RearmeDejarPieza = 7
         return rx.cond(
            rx_var == 0, "None",
            rx.cond(rx_var == 1, "Coger base",
            rx.cond(rx_var == 2, "Posar base", 
            rx.cond(rx_var == 3, "Ir a posición",
            rx.cond(rx_var == 4, "Ir a estación",
            rx.cond(rx_var == 5, "Coger spinner",
            rx.cond(rx_var == 6, "Rearme posición neutra",
            rx.cond(rx_var == 7, "Rearme dejar pieza","Sin datos")))))))
        )

import json
def enviarMensaje(mensaje):
    mensaje = mensaje.json.dumps()
    mensaje = mensaje + "\r\n"
    mensaje.encode(encoding = 'utf-8')




def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.vstack(
        rx.heading("Interfaz", size="8", width="200px",height="10"),
      
      rx.box(
    
        rx.button("Leer dato OPC", on_click=State.iniciar_lectura, id_disabled=State.leyendo, color_scheme="green"),
        #rx.button("Desconectar", on_click=State.desconectar, is_disabled=~State.leyendo, color_scheme="red"),
      ),
        rx.grid(
            
                rx.vstack(
                    rx.box(
                        rx.text("Estado Actual", weight="bold"),
                        
                        rx.hstack(
                            rx.text("Módulo de Bases: "), 
                            mostrar_estado(State.valores[0], State.errores[0])
                        ),
                        rx.hstack(
                            rx.text("Módulo de Spinners: "), 
                            mostrar_estado(State.valores[1], State.errores[1])
                        ),
                        rx.hstack(
                            rx.text("Módulo de Transporte: "), 
                            mostrar_estado(State.valores[2], State.errores[2])
                        ),

                        spacing="5"

                    ),
                    rx.box(
                        rx.text("Servicio Actual", weight="bold"),
                        rx.hstack(
                                rx.text("Módulo de Bases: "), 
                                mostrar_servicio("BASES",State.val_ServAct[0], State.errores[0])
                            ),
                        rx.hstack(
                                rx.text("Módulo de Spinners: "), 
                                mostrar_servicio("SPINNERS",State.val_ServAct[1], State.errores[1])
                            ),
                        rx.hstack(
                                rx.text("Módulo de transporte: "), 
                                mostrar_servicio("TRANSPORTE",State.val_ServAct[2], State.errores[2])
                            ),
                        spacing="5"
                    ),
                    rx.box(
                        rx.text("Posición del transportador", weight="bold"),
                        rx.hstack(
                                rx.text("Posición actual: ", State.pos_trans[0])
                            
                            ),
                        rx.hstack(
                                rx.text("Posición objetivo: ", State.pos_trans[1])
                            
                            ),
                            spacing="5"

                        ),
                            #columns="repeat(3, 1fr)",         
                            #spacing="3",       
                            #width="100%",  
                            #max_width="1000px",
                            #margin="auto",
                            #justify_items="start",    # Alineación horizontal
                            #align_items="start"
                            
                
                    
                    rx.box(
                        rx.text("Detectores", weight="bold"),
                        rx.text("Modulo de Base", weight="bold"),
                        rx.hstack(
                            rx.foreach(
                                State.lectura_por_modulo["ME_BASES_"],
                                lambda led: led_con_etiqueta(led[0], led[1]),
                   
                
                                #State.leds,
                                #lambda led: led_con_etiqueta(limpiar_nombres(led[0]), led[1])
                                ),
                        

                        ),
                        rx.text("Modulo de Spinners", weight="bold"),
                        rx.grid(
                            rx.foreach(
                                State.lectura_por_modulo["ME_SPINNERS_"],
                                lambda led: led_con_etiqueta(led[0], led[1])
                            ),
                            columns="repeat(4, 2fr)",         
                            spacing="6",       
                            width="60%",  
                            justify_items="start",    
                            align_items="start"
                        ),
                        rx.text("Modulo de Transporte", weight="bold"),
                        rx.grid(
                            rx.foreach(
                                State.lectura_por_modulo["ME_TRANSPORTE_"],
                                lambda led: led_con_etiqueta(led[0], led[1])),
                
                            columns="repeat(4, 2fr)",         
                            spacing="6",       
                            width="60%",  
                            #max_width="1000px",
                            justify_items="start",    # Alineación horizontal
                            align_items="center"
                            
                            
                        )
                
                    )
            ),
            
        
            
            rx.vstack(
                rx.text("Alarmas", weight="bold"),
                rx.text("Modulo de Base", weight="bold"),
                rx.hstack(
                    rx.foreach(
                        State.lectura_por_modulo_alarma["ME_BASES_"],
                        lambda led: led_con_etiqueta(led[0], led[1])
        
                        #State.leds,
                        #lambda led: led_con_etiqueta(limpiar_nombres(led[0]), led[1])
                        )
                ),
                rx.text("Modulo de Spinners", weight="bold"),
                rx.hstack(
                    rx.foreach(
                        State.lectura_por_modulo_alarma["ME_SPINNERS_"],
                        lambda led: led_con_etiqueta(led[0], led[1]))
                ),
                rx.text("Modulo de Transporte", weight="bold"),
                rx.grid(
                    rx.foreach(
                        State.lectura_por_modulo_alarma["ME_TRANSPORTE_"],
                        lambda led: led_con_etiqueta(led[0], led[1])),
                    columns="repeat(3, 1fr)",         
                    spacing="1",       
                    width="100%",      
                    align_items="center",  
                    justify_items="center" 

                )
            ),

            rx.vstack(
                rx.text("Recetas", weight="bold"),
                rx.grid(
                    rx.button("Start", on_click=State.comienzo, width=150, height=50),
                    # Script JavaScript que hace clic al botón oculto cada 5 segundos
                    
                    #rx.button("Stop", on_click=JsonSocketClient.send("{'appSMEvent':'enterStopped'}"), width=150, height=50),
                    rx.button("Rearmar", on_click=State.rearmar, width=150, height=50),
                    rx.button("Obtener recetas", on_click=State.list_recipes, width=150, height=50),
                    rx.button("Lista de usuarios", on_click=State.list_users, width=150, height=50),
                    rx.button("Pausa",on_click=State.pause, width=150, height=50),
                    rx.button("Pausa",on_click=State.unpause, width=150, height=50),
                    columns="repeat(4, 1fr)",         
                    spacing="1",       
                    width="100%",      
                    align_items="center",  
                    justify_items="center" 

                ),
                rx.grid(
                    rx.box(
                        rx.text("Recetas"),
                        rx.select(
                            items=[" "],
                            width="200px",
                            height="50px"    
                        ),
                        rx.text("Usuarios"),
                        rx.select(
                            items=[" "],
                            width="200px",
                            height="50px"    
                        ),
                        rx.text("Parámetro 1"),
                        rx.select(
                            ["bool", "int", "word", "dword"],
                            value=State.tipo_dato,
                            on_change=State.set_tipo_dato,
                        ),
                        render_input(),
                        rx.text("Valor seleccionado: "),
                        rx.text(State.val_2),
                        rx.text("Parámetro 2"),
                        rx.select(
                            ["bool", "int", "word", "dword"],
                            value=State.tipo_dato,
                            on_change=State.set_tipo_dato,
                        ),
                        render_input(),
                        rx.text("Valor seleccionado: "),
                        rx.text(State.val_2),
                        rx.button("RUN", color_scheme="green"),
                    ),
                    rx.vstack(
                        rx.text("Estado"),
                        #rx.text_area(value= str(State.contenido_archivo), is_read_only=True, width = "400px",height = "100px"),
                        
                        rx.text(
                            #State.result
                            read_only= True,
                            width = "400px",
                            height = "100px",
                        ),
                         
                        
                        rx.text("Gestor de recetas"),
                         rx.input(
                            read_only = True,
                            width = "400px",
                            height = "300px",
                         
                        ),
                    ),
                    rx.box(
                        rx.text("Usuarios"),
                        rx.input(
                            read_only = True,
                            width = "200px",
                            height = "420px",
                         
                        ),
                    ),
                    columns="repeat(3, 1fr)",         
                    spacing="1",       
                    width="100%",      
                    align_items="center",  
                    justify_items="center",


                ),
                spacing="2"
              

            ),

                columns="repeat(3, 1fr)",         
                spacing="3",       
                width="60%",      
                align_items="start",  
                justify_items="start"
                
        ),
    )
    

  


app = rx.App()
app.add_page(index)
