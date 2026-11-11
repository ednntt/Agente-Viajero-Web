import itertools
import json
import random
from datetime import datetime

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Problema del Agente Viajero",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta inspirada en la aplicación de escritorio original
BG = "#dfe7f3"
BLUE = "#1565c0"
BLUE_DARK = "#0d47a1"
GREEN = "#2e7d32"
RED = "#e53935"
GRAY = "#9aa5b8"
PALETTE = ["#1e88e5", "#43a047", "#fb8c00", "#8e24aa", "#00acc1",
           "#f9a825", "#6d4c41", "#3949ab", "#00897b", "#54767a"]
MAX_NODES = 10
MAX_DEGREE = 3
MAX_ROWS = 300

st.markdown("""
<style>
    .stApp { background: #dfe7f3; }
    [data-testid="stHeader"] { background: rgba(223,231,243,0.92); }
    [data-testid="stSidebar"] { background: #eef3fa; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #c5d0e0;
        padding: 12px 16px; border-radius: 10px;
    }
    .block-container { padding-top: 1.4rem; }
    h1, h2, h3 { color: #0d47a1; }
    div.stButton > button[kind="primary"] {
        background: #1565c0; border-color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)


def default_state():
    defaults = {
        "graph_data": None,
        "nodes": [],
        "edges": [],
        "names": {},
        "start": 0,
        "mode": "aleatorio",
        "cycles": [],
        "matrix": [],
        "cycle_index": -1,
        "history": [],
        "log": [],
        "edge_text": "",
        "name_text": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


default_state()


def node_name(v):
    return st.session_state.names.get(str(v), chr(65 + v))


def fmt_num(value):
    x = round(float(value), 4)
    return str(int(x)) if x.is_integer() else str(x)


def log(message):
    st.session_state.log.append(f"{datetime.now().strftime('%H:%M:%S')}  {message}")
    st.session_state.log = st.session_state.log[-500:]


def build_matrix(n, edges):
    matrix = [[None for _ in range(n)] for _ in range(n)]
    for u, v, w in edges:
        matrix[u][v] = w
    return matrix


def calculate_cycles(n, edges, start):
    """Replica el conteo de ciclos dirigidos y la deduplicación del código original."""
    matrix = build_matrix(n, edges)
    found = []
    others = [v for v in range(n) if v != start]
    for perm in itertools.permutations(others):
        route = (start,) + perm
        total = 0
        valid = True
        for k in range(n):
            cost = matrix[route[k]][route[(k + 1) % n]]
            if cost is None:
                valid = False
                break
            total += cost
        if not valid:
            continue
        if perm[0] > perm[-1]:
            reverse_exists = all(
                matrix[route[(k + 1) % n]][route[k]] is not None
                for k in range(n)
            )
            if reverse_exists:
                continue
        found.append({"route": list(route), "cost": total})
    return found, matrix


def suggest_missing_edges(n, matrix, start):
    best = None
    for perm in itertools.permutations(v for v in range(n) if v != start):
        route = (start,) + perm
        missing = [
            (route[k], route[(k + 1) % n])
            for k in range(n)
            if matrix[route[k]][route[(k + 1) % n]] is None
        ]
        if best is None or len(missing) < len(best):
            best = missing
            if len(best) <= 1:
                break
    return best or []


def random_graph(n):
    edges = {}
    nodes = list(range(n))
    random.shuffle(nodes)
    # Anillo base en un sentido: asegura al menos un ciclo hamiltoniano.
    for k in range(n):
        a, b = nodes[k], nodes[(k + 1) % n]
        weight = random.randint(10, 30)
        edges[(a, b)] = weight
        if random.random() < 0.8:
            edges[(b, a)] = weight

    # Aristas extra con máximo de tres conexiones por nodo.
    pairs = list(itertools.combinations(range(n), 2))
    random.shuffle(pairs)
    for i, j in pairs:
        degree_i = len({v for u, v in edges if u == i or v == i})
        degree_j = len({v for u, v in edges if u == j or v == j})
        if ((i, j) not in edges and (j, i) not in edges
                and degree_i < MAX_DEGREE and degree_j < MAX_DEGREE
                and random.random() < 0.5):
            weight = random.randint(10, 30)
            a, b = (i, j) if random.random() < 0.5 else (j, i)
            edges[(a, b)] = weight
            if random.random() < 0.8:
                edges[(b, a)] = weight
    return [(u, v, w) for (u, v), w in edges.items()]


def parse_manual_edges(raw, n):
    """Formato por línea: A,B,12. También acepta 0,1,12."""
    names = [chr(65 + i) for i in range(n)]
    lookup = {name.lower(): i for i, name in enumerate(names)}
    parsed = {}
    for line_no, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.replace(";", ",").split(",")]
        if len(parts) != 3:
            raise ValueError(f"Línea {line_no}: usa el formato A,B,12.")
        a, b, weight_text = parts
        try:
            u = int(a) if a.isdigit() else lookup[a.lower()]
            v = int(b) if b.isdigit() else lookup[b.lower()]
        except (KeyError, ValueError):
            raise ValueError(f"Línea {line_no}: nodo no válido. Usa A hasta {names[-1]} o índices 0 a {n-1}.")
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"Línea {line_no}: nodo fuera del rango.")
        if u == v:
            raise ValueError(f"Línea {line_no}: no se permiten bucles de un nodo a sí mismo.")
        try:
            weight = float(weight_text.replace(",", "."))
        except ValueError:
            raise ValueError(f"Línea {line_no}: el peso debe ser numérico.")
        if not (weight > 0 and weight < float("inf")):
            raise ValueError(f"Línea {line_no}: el peso debe ser positivo.")
        if weight.is_integer():
            weight = int(weight)
        parsed[(u, v)] = weight
    if not parsed:
        raise ValueError("Agrega al menos una flecha.")
    return [(u, v, w) for (u, v), w in parsed.items()]


def set_graph(n, edges, mode="manual", names=None, start=0):
    st.session_state.nodes = list(range(n))
    st.session_state.edges = edges
    st.session_state.names = names or {}
    st.session_state.start = start
    st.session_state.mode = mode
    cycles, matrix = calculate_cycles(n, edges, start)
    st.session_state.cycles = cycles
    st.session_state.matrix = matrix
    st.session_state.cycle_index = -1
    st.session_state.edge_text = "\n".join(
        f"{chr(65+u)},{chr(65+v)},{fmt_num(w)}" for u, v, w in edges
    )
    st.session_state.name_text = "\n".join(
        f"{chr(65+i)}={st.session_state.names.get(str(i), chr(65+i))}"
        for i in range(n)
    )
    log(f"Grafo {mode} creado: {n} nodos, {len({frozenset((u,v)) for u,v,_ in edges})} aristas.")
    log(f"Ciclos hamiltonianos encontrados: {len(cycles)}.")


def route_text(route):
    labels = [node_name(v) for v in route]
    return " → ".join(labels + [labels[0]])


def draw_graph(selected_route=None, suggested=None):
    n = len(st.session_state.nodes)
    if n == 0:
        return None
    graph = nx.DiGraph()
    graph.add_nodes_from(range(n))
    for u, v, w in st.session_state.edges:
        graph.add_edge(u, v, weight=w)
    pos = nx.spring_layout(graph.to_undirected(), seed=17, k=1.0, iterations=100)

    fig = go.Figure()
    selected_pairs = set()
    if selected_route:
        selected_pairs = {
            (selected_route[k], selected_route[(k + 1) % n])
            for k in range(n)
        }

    # Aristas: se usan trazos separados para distinguir las del ciclo.
    for u, v, data in graph.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        is_selected = (u, v) in selected_pairs
        color = RED if is_selected else GRAY
        width = 4 if is_selected else 1.7
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line=dict(color=color, width=width),
            hoverinfo="text",
            text=f"{node_name(u)} → {node_name(v)} | costo: {fmt_num(data['weight'])}",
            showlegend=False,
        ))
        # Flecha al final de cada arco
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y",
            axref="x", ayref="y", showarrow=True, arrowhead=3,
            arrowsize=1.1, arrowwidth=width, arrowcolor=color,
            standoff=17, startstandoff=14,
        )
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        fig.add_trace(go.Scatter(
            x=[mx], y=[my], mode="text",
            text=[fmt_num(data["weight"])],
            textfont=dict(size=11, color="#263238"),
            hoverinfo="skip", showlegend=False,
        ))

    if suggested:
        for u, v in suggested:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode="lines",
                line=dict(color=GREEN, width=2, dash="dash"),
                hoverinfo="text", text=f"Falta agregar: {node_name(u)} → {node_name(v)}",
                showlegend=False,
            ))
            fig.add_annotation(
                x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y",
                axref="x", ayref="y", showarrow=True, arrowhead=3,
                arrowcolor=GREEN, arrowwidth=2, standoff=17, startstandoff=14,
            )

    node_colors = [BLUE_DARK if v == st.session_state.start else PALETTE[v % len(PALETTE)]
                   for v in range(n)]
    fig.add_trace(go.Scatter(
        x=[pos[v][0] for v in range(n)],
        y=[pos[v][1] for v in range(n)],
        mode="markers+text",
        text=[node_name(v) for v in range(n)],
        textposition="middle center",
        textfont=dict(color="white", size=13, family="Arial"),
        marker=dict(size=38, color=node_colors, line=dict(color="white", width=2)),
        hovertext=[
            f"Nodo {node_name(v)}" + (" | INICIO" if v == st.session_state.start else "")
            for v in range(n)
        ],
        hoverinfo="text", showlegend=False,
    ))
    fig.update_layout(
        height=560, margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def make_record():
    return {
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "n": len(st.session_state.nodes),
        "modo": st.session_state.mode,
        "inicio": st.session_state.start,
        "nombres": st.session_state.names,
        "aristas": st.session_state.edges,
        "ciclos": len(st.session_state.cycles),
        "optimo": min((c["cost"] for c in st.session_state.cycles), default=None),
    }


# ------------------------- Encabezado y menú -------------------------
st.title("Problema del Agente Viajero")
st.caption("Algoritmo de fuerza bruta · Ciclos hamiltonianos · Matriz de costos")
with st.sidebar:
    st.header("Panel de control")
    page = st.radio(
        "Secciones",
        ["Simulación", "Crear / editar grafo", "Historial"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Parámetros del algoritmo**")
    st.write(f"Nodos permitidos: 5 a {MAX_NODES}")
    st.write(f"Máximo de conexiones por nodo en modo aleatorio: {MAX_DEGREE}")
    st.caption("Los pesos deben ser números positivos.")

if page == "Crear / editar grafo":
    st.subheader("Crear o editar un grafo")
    st.write("Elige la cantidad de nodos y registra cada flecha con su costo.")
    col1, col2 = st.columns([1, 2])
    with col1:
        n = st.number_input("Número de nodos", min_value=5, max_value=10, value=5, step=1)
        st.caption("Los nodos se identifican inicialmente como A, B, C…")
        start_label = st.selectbox("Nodo de inicio", [chr(65+i) for i in range(int(n))])
    with col2:
        st.markdown("**Flechas y pesos**")
        st.caption("Una por línea. Ejemplo: A,B,12 significa A → B con costo 12. Para doble sentido, registra también B,A,12.")
        raw_edges = st.text_area(
            "Aristas",
            value=st.session_state.edge_text,
            height=190,
            placeholder="A,B,12\nB,C,15\nC,D,10\nD,E,20\nE,A,18",
            label_visibility="collapsed",
        )
    if st.button("Aplicar grafo manual", type="primary", use_container_width=True):
        try:
            parsed = parse_manual_edges(raw_edges, int(n))
            set_graph(int(n), parsed, mode="manual", start=ord(start_label)-65)
            st.success(f"Grafo aplicado. Se encontraron {len(st.session_state.cycles)} ciclos hamiltonianos.")
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("**Cambiar nombres de nodos (opcional)**")
    st.caption("Escribe una asignación por línea, por ejemplo A=Lima. Deja vacío para usar letras.")
    names_raw = st.text_area("Nombres", value=st.session_state.name_text, height=110)
    if st.button("Actualizar nombres", use_container_width=True):
        try:
            updated = {}
            for line in names_raw.splitlines():
                if not line.strip():
                    continue
                if "=" not in line:
                    raise ValueError("Formato inválido. Usa A=Nombre.")
                key, value = [part.strip() for part in line.split("=", 1)]
                idx = ord(key.upper()) - 65
                if idx < 0 or idx >= len(st.session_state.nodes) or not value:
                    raise ValueError(f"Asignación no válida: {line}")
                updated[str(idx)] = value[:20]
            st.session_state.names = updated
            st.success("Nombres actualizados.")
        except Exception as exc:
            st.error(str(exc))

elif page == "Historial":
    st.subheader("Historial de grafos")
    st.caption("El historial se conserva durante la sesión del navegador. Puedes descargarlo para guardarlo y volver a importarlo después.")
    upload = st.file_uploader("Importar historial JSON", type=["json"])
    if upload is not None:
        try:
            records = json.loads(upload.getvalue().decode("utf-8"))
            if not isinstance(records, list):
                raise ValueError("El archivo debe contener una lista de registros.")
            st.session_state.history.extend(records)
            st.success(f"Se importaron {len(records)} registros.")
        except Exception as exc:
            st.error(f"No se pudo importar: {exc}")

    if st.session_state.history:
        rows = []
        for i, rec in enumerate(st.session_state.history):
            rows.append({
                "N°": i + 1, "Fecha": rec.get("fecha", "-"),
                "Nodos": rec.get("n", "-"), "Ciclos": rec.get("ciclos", "-"),
                "Costo mínimo": rec.get("optimo") if rec.get("optimo") is not None else "—",
                "Modo": rec.get("modo", "-"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        choices = list(range(len(st.session_state.history)))
        selected = st.selectbox(
            "Selecciona un grafo para cargar",
            choices,
            format_func=lambda i: f"Grafo {i+1} · {st.session_state.history[i].get('fecha','sin fecha')} · {st.session_state.history[i].get('n','?')} nodos",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Cargar seleccionado", type="primary", use_container_width=True):
                rec = st.session_state.history[selected]
                try:
                    n = int(rec["n"])
                    edges = [(int(u), int(v), float(w) if not float(w).is_integer() else int(w))
                             for u, v, w in rec["aristas"]]
                    set_graph(n, edges, rec.get("modo", "manual"),
                              rec.get("nombres", {}), int(rec.get("inicio", 0)))
                    st.success("Grafo cargado.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Registro inválido: {exc}")
        with c2:
            payload = json.dumps(st.session_state.history, ensure_ascii=False, indent=2)
            st.download_button("Descargar historial", payload, "historial_grafos.json",
                               "application/json", use_container_width=True)
        with c3:
            if st.button("Eliminar seleccionado", use_container_width=True):
                del st.session_state.history[selected]
                st.rerun()
        if st.button("Vaciar todo el historial"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("Aún no hay grafos guardados. Guarda un grafo desde la sección Simulación.")

else:
    st.subheader("Simulación")
    st.write("Genera un grafo aleatorio o trabaja con uno creado manualmente.")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        n_random = st.number_input("Nodos para grafo aleatorio", 5, 10, 5, 1)
        if st.button("Generar grafo aleatorio", type="primary", use_container_width=True):
            edges = random_graph(int(n_random))
            set_graph(int(n_random), edges, mode="aleatorio", start=0)
            st.rerun()
    with c2:
        if st.button("Nueva simulación", use_container_width=True):
            st.session_state.nodes = []
            st.session_state.edges = []
            st.session_state.cycles = []
            st.session_state.matrix = []
            st.session_state.cycle_index = -1
            st.session_state.log = []
            st.rerun()
    with c3:
        if st.session_state.nodes:
            labels = [node_name(v) for v in st.session_state.nodes]
            chosen = st.selectbox(
                "Punto de inicio",
                list(range(len(labels))),
                index=st.session_state.start,
                format_func=lambda i: labels[i],
            )
            if chosen != st.session_state.start:
                set_graph(len(st.session_state.nodes), st.session_state.edges,
                          st.session_state.mode, st.session_state.names, chosen)
                st.rerun()

    if not st.session_state.nodes:
        st.info("Para comenzar, genera un grafo aleatorio o crea uno en «Crear / editar grafo».")
    else:
        n = len(st.session_state.nodes)
        cycles = st.session_state.cycles
        matrix = st.session_state.matrix
        best_cost = min((c["cost"] for c in cycles), default=None)
        unique_edges = len({frozenset((u, v)) for u, v, _ in st.session_state.edges})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Nodos", n)
        m2.metric("Aristas", unique_edges)
        m3.metric("Ciclos hamiltonianos", len(cycles))
        m4.metric("Costo mínimo", fmt_num(best_cost) if best_cost is not None else "—")

        if cycles:
            ordered = sorted(range(len(cycles)), key=lambda i: cycles[i]["cost"])
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("⏮ Reiniciar recorrido", use_container_width=True):
                    st.session_state.cycle_index = -1
                    st.rerun()
            with c2:
                if st.button("Anterior", disabled=st.session_state.cycle_index <= 0,
                             use_container_width=True):
                    st.session_state.cycle_index -= 1
                    st.rerun()
            with c3:
                if st.button("Siguiente ciclo",
                             disabled=st.session_state.cycle_index >= len(cycles)-1,
                             use_container_width=True):
                    st.session_state.cycle_index += 1
                    st.rerun()
            with c4:
                if st.button("Mostrar óptimo", type="primary", use_container_width=True):
                    st.session_state.cycle_index = min(range(len(cycles)), key=lambda i: cycles[i]["cost"])
                    st.rerun()

            current = None
            if 0 <= st.session_state.cycle_index < len(cycles):
                current = cycles[st.session_state.cycle_index]
            if current:
                st.success(f"Ciclo N° {st.session_state.cycle_index + 1}: {route_text(current['route'])} · Costo: {fmt_num(current['cost'])}")
            else:
                st.info("Pulsa «Siguiente ciclo» para iniciar el recorrido, o «Mostrar óptimo» para ver la mejor ruta.")

            tab_graph, tab_cycles, tab_matrix, tab_log = st.tabs(
                ["Grafo", "Ciclos y costos", "Matriz de costos", "Registro"]
            )
            with tab_graph:
                st.plotly_chart(draw_graph(current["route"] if current else None),
                                use_container_width=True, config={"displayModeBar": True})
                st.caption("El ciclo seleccionado se resalta en rojo. El nodo de inicio aparece en azul oscuro.")
            with tab_cycles:
                rows = []
                for idx in ordered[:MAX_ROWS]:
                    item = cycles[idx]
                    rows.append({
                        "N°": idx + 1,
                        "Ciclo": route_text(item["route"]),
                        "Costo": fmt_num(item["cost"]),
                        "Óptimo": "Sí" if item["cost"] == best_cost else "",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if len(cycles) > MAX_ROWS:
                    st.caption(f"Se muestran los {MAX_ROWS} ciclos de menor costo, de {len(cycles)} encontrados.")
            with tab_matrix:
                matrix_rows = []
                for i in range(n):
                    row = {"Nodo": node_name(i)}
                    for j in range(n):
                        row[node_name(j)] = "—" if i == j else ("∞" if matrix[i][j] is None else fmt_num(matrix[i][j]))
                    matrix_rows.append(row)
                st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)
            with tab_log:
                st.code("\n".join(st.session_state.log) or "Sin registros todavía.", language="text")

            if st.button("Guardar grafo en historial", use_container_width=True):
                st.session_state.history.append(make_record())
                log(f"Grafo guardado en historial. Total: {len(st.session_state.history)}.")
                st.success("Grafo guardado en el historial de esta sesión.")
        else:
            missing = suggest_missing_edges(n, matrix, st.session_state.start)
            st.warning("El grafo no permite construir ningún ciclo hamiltoniano.")
            st.write("Flechas que faltan para completar un ciclo con la menor cantidad de adiciones:")
            st.write(", ".join(f"{node_name(u)} → {node_name(v)}" for u, v in missing) or "No se pudo determinar.")
            st.plotly_chart(draw_graph(suggested=missing), use_container_width=True)
            st.caption("Las flechas punteadas verdes son las sugeridas.")
        with st.expander("Ver lista de flechas y pesos"):
            st.dataframe(pd.DataFrame(
                [{"Desde": node_name(u), "Hacia": node_name(v), "Costo": fmt_num(w)}
                 for u, v, w in st.session_state.edges]
            ), use_container_width=True, hide_index=True)

st.divider()
st.caption("Versión web adaptada del programa original. El cálculo de ciclos sigue el método de fuerza bruta y admite hasta 10 nodos.")
