"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import asyncio
import logging
from opcua import Client

from opcua.common.subscription import Subscription
from threading import Lock
import threading
import time

opc_lock = Lock()
opc_data = {}
opc_callback = None
main_loop = asyncio.get_event_loop()
current_state = None


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
        # if current_state is not None:
        #     print(val)
            #coro = current_state.actualizar_estado(node, val)
            #asyncio.run_coroutine_threadsafe(coro, main_loop)
        #self.callback(node, val)
     
            


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

opc.connect()
direccion_detect_bases: list[str] = ["ME_BASES_Base"]
direccion_alarma: list[str] = ["ME_BASES_Alarmas_dos_detect"]
opc.subscribe(None, direccion_detect_bases, direccion_alarma)

while(True):
    pass
