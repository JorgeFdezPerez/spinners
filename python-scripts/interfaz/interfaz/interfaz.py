"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx
from opcua import Client
from rxconfig import config




# Encapsulamos la lógica OPC
class OpcClient:
    def __init__(self):
        self.client = None

    def connect(self):
        self.client = Client("opc.tcp://localhost:54840")
        self.client.connect()

    def get_value(self):
        node = self.client.get_node("ns=1;i=ME_BASES_NumSRV")  # Cambia por tu NodeId real
        return node.get_value()
    
    def disconnect(self):
        self.client.disconnect()

opc = OpcClient()

class State(rx.State):
    """The app state."""
    value: str = "Sin datos"

    def load_value(self):
        try:
            opc.connect()
            self.value = str(opc.get_value())
        except Exception as e:
            self.value = f"Error: {e}"

    def desconectar(self):
        try:
            opc.disconnect()  
        except Exception as e:
            print("Error en ", e)


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.vstack(
        rx.heading("Welcome to Reflex!", size="9"),
            # rx.text(
            #    "Get started by editing ",
            #    rx.code(f"{config.app_name}/{config.app_name}.py"),
            #    size="5",
            #),
            #rx.link(
            #    rx.button("Check out our docs!"),
            #    href="https://reflex.dev/docs/getting-started/introduction/",
            #    is_external=True,
            #), 
        rx.button("Leer dato OPC", on_click=State.load_value),
        rx.text(State.value),
        rx.button("Desconectar", on_click=State.desconectar),
        spacing="5",
        justify="center",
        min_height="85vh"
  
    )


app = rx.App()
app.add_page(index)
