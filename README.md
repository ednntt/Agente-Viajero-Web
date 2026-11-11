# Problema del Agente Viajero — versión web

Esta carpeta contiene una adaptación web de la aplicación de escritorio Tkinter.

## Funcionalidades incluidas

- Generación aleatoria de grafos con anillo base y pesos positivos.
- Creación y edición manual de flechas y costos.
- Selección del nodo inicial y renombrado de nodos.
- Cálculo por fuerza bruta de ciclos hamiltonianos dirigidos.
- Deduplicación de ciclos inversos cuando existen ambas direcciones, siguiendo la lógica del programa original.
- Navegación por ciclos: anterior, siguiente y reinicio.
- Identificación y visualización del ciclo óptimo.
- Grafo interactivo, tabla de ciclos y matriz de costos.
- Sugerencia de flechas faltantes cuando no existe un ciclo hamiltoniano.
- Historial de la sesión con importar y exportar JSON.

## Ejecutar localmente

Se recomienda Python 3.10 o superior.

1. Instala Python.
2. Abre una terminal en esta carpeta.
3. Ejecuta:

   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

4. Se abrirá el programa en el navegador, normalmente en `http://localhost:8501`.

## Publicar con un enlace gratuito usando Streamlit Community Cloud

1. Crea una cuenta en GitHub.
2. Crea un repositorio nuevo, por ejemplo `agente-viajero-web`.
3. Sube `app.py` y `requirements.txt` a la raíz del repositorio.
4. Entra a https://share.streamlit.io/ e inicia sesión con GitHub.
5. Selecciona **Create app**.
6. Elige tu repositorio, la rama `main` y el archivo `app.py`.
7. Pulsa **Deploy**. Streamlit generará un enlace público para compartir.

## Consideraciones importantes

- El enlace permite abrir la aplicación desde un navegador sin instalar Python.
- La aplicación está adaptada para navegador; no es una conversión automática de Tkinter. La distribución visual y algunas interacciones propias de escritorio (por ejemplo, arrastrar nodos libremente y la animación de la bandera) se sustituyen por controles web.
- El historial se mantiene durante la sesión del navegador. Para conservarlo entre sesiones, descarga el JSON desde Historial y vuelve a importarlo cuando lo necesites.
- El cálculo es de fuerza bruta. Con 10 nodos puede tardar más porque examina hasta 9! permutaciones antes de filtrar rutas inválidas.
- Esta versión no incluye las imágenes de fondo opcionales `fondo_grafo` y `fondo_pagina` del programa de escritorio.
