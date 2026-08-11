# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import dash
from dash import html, Input, Output, clientside_callback
from flask import send_file, render_template, send_from_directory
import mimetypes
import os

# 1. CONFIGURACIÓN DE SEGURIDAD PARA WINDOWS/BROWSERS
# Esto es vital para que el motor web-ifc.wasm y los módulos .mjs funcionen
mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/javascript', '.mjs')

# 2. INICIALIZACIÓN DE DASH
# No cargamos assets automáticamente para evitar conflictos con el bundle de Vite
app = dash.Dash(__name__, assets_folder='assets')
server = app.server

# 3. RUTAS DE DIRECTORIOS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
# Carpeta donde guardas tus archivos IFC reales
IFC_FOLDER = r"C:\Users\RafaelNúñezdeArenas\Desktop\250804_Test"

# 4. RUTAS DE FLASK (BACKEND)

@server.route('/static/<path:path>')
def serve_static(path):
    """Sirve el bundle de Vite, el worker y el web-ifc.wasm"""
    return send_from_directory(STATIC_DIR, path)

@server.route("/viewer_page")
def render_viewer():
    """Sirve la página que contiene el canvas del visor BIM"""
    return render_template("viewer.html")

@server.route("/models/<filename>")
def serve_models(filename):
    """Sirve los archivos IFC físicos desde tu carpeta de trabajo"""
    file_path = os.path.join(IFC_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return f"Error: El archivo {filename} no existe en {IFC_FOLDER}", 404

# 5. DISEÑO DE LA INTERFAZ (DASH LAYOUT)
app.layout = html.Div([
    # Cabecera / Controles
    html.Div([
        html.H3("Control de Visibilidad BIM", style={"color": "white", "margin-bottom": "10px"}),
        html.Button("Cargar Estructura (ZoneA_Est)", id="btn-est", n_clicks=0, 
                    style={"margin-right": "10px", "padding": "10px", "cursor": "pointer"}),
        html.Button("Cargar Arquitectura (ZoneA_Arc)", id="btn-arc", n_clicks=0, 
                    style={"padding": "10px", "cursor": "pointer"}),
    ], style={"backgroundColor": "#1a1a1a", "padding": "20px"}),

    # El Iframe es la ventana al mundo Three.js
    html.Iframe(
        id="bim-iframe",
        src="/viewer_page",
        style={"width": "100%", "height": "85vh", "border": "none"}
    ),
    
    # Div oculto para recibir los resultados de los callbacks de Dash
    html.Div(id="callback-output-status", style={"display": "none"})
], style={"margin": "0", "padding": "0", "overflow": "hidden"})

# 6. COMUNICACIÓN DASH -> IFRAME (CLIENTSIDE CALLBACK)
# Esta lógica corre en el navegador, permitiendo enviar la URL del modelo al visor
clientside_callback(
    """
    function(n_est, n_arc) {
        // Obtenemos el contexto de la ventana del Iframe
        const iframe = document.getElementById('bim-iframe');
        if (!iframe) return "";
        
        const viewer = iframe.contentWindow;

        // Verificamos si la función loadModel ya fue expuesta por main.js
        if (viewer && viewer.loadModel) {
            const triggered = dash_clientside.callback_context.triggered;
            
            if (triggered.length > 0) {
                const propId = triggered[0].prop_id;
                
                if (propId === 'btn-est.n_clicks' && n_est > 0) {
                    viewer.loadModel('/models/PyNet_CM_ZoneA_Est.ifc');
                }
                if (propId === 'btn-arc.n_clicks' && n_arc > 0) {
                    viewer.loadModel('/models/PyNet_CM_ZoneA_Arc.ifc');
                }
            }
        }
        return "";
    }
    """,
    Output('callback-output-status', 'children'),
    Input('btn-est', 'n_clicks'),
    Input('btn-arc', 'n_clicks'),
    prevent_initial_call=True
)

if __name__ == "__main__":
    # use_reloader=False es importante para no duplicar procesos de memoria al usar WASM
    app.run(debug=True, port=8050, use_reloader=False)