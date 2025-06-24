import streamlit as st
import random
import string

def boton(texto: str, color: str = "#e60000") -> bool:
    #Generar una clave única para evitar conflictos de CSS
    unique_key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

    #Crear estilo único para este botón
    custom_css = f"""
        <style>
            div[data-testid="stButton"] button[data-custom="{unique_key}"] {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 25px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: 0.3s;
            }}

            div[data-testid="stButton"] button[data-custom="{unique_key}"]:hover {{
                background-color: #00000033;
            }}
        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    #Renderizar botón con atributo personalizado (lo agregamos vía unsafe HTML)
    button_html = f"""
        <script>
        const buttons = parent.document.querySelectorAll('button');
        buttons.forEach(btn => {{
            if (btn.innerText === "{texto}") {{
                btn.setAttribute("data-custom", "{unique_key}");
            }}
        }});
        </script>
    """
    st.markdown(button_html, unsafe_allow_html=True)

    return st.button(texto)

    