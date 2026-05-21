import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime
import io
import json

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Sistema de Asistencias - UGEL 06",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILOS CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>

    /* ===== Fondo general ===== */
    .stApp {
        background-color: #F3F4F6;
    }

    html, body, [class*="css"] {
        color: #111827;
        font-family: 'Segoe UI', Arial, sans-serif;
    }

    /* ===== Títulos ===== */
    h1, h2, h3 {
        color: #1D4ED8 !important;
        font-weight: 700;
    }

    /* ===== Texto ===== */
    p, span, label, div {
        color: #111827;
    }

    /* ===== Sidebar ===== */
    section[data-testid="stSidebar"] {
        background-color: #DBEAFE !important;
        border-right: 1px solid #BFDBFE;
    }

    section[data-testid="stSidebar"] * {
        color: #1E3A8A !important;
    }

    /* ===== Botones ===== */
    .stButton > button {
        background-color: #FCA5A5;
        color: #7F1D1D;
        border: none;
        border-radius: 10px;
        padding: 0.55rem 1.2rem;
        font-weight: 600;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    .stButton > button:hover {
        background-color: #F87171;
        color: white;
        transform: translateY(-1px);
    }

    /* ===== Cards ===== */
    .info-card {
        background-color: #FFFFFF;
        border-left: 5px solid #60A5FA;
        padding: 1rem 1.2rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        color: #111827;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }

    /* ===== Filas / tablas ===== */
    .profesor-row {
        background-color: #FEFCE8;
        border: 1px solid #FDE68A;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }

    /* ===== Headers de sección ===== */
    .section-header {
        color: #1D4ED8;
        font-size: 1.1rem;
        font-weight: 700;
        border-bottom: 3px solid #FCA5A5;
        padding-bottom: 0.35rem;
        margin-bottom: 1rem;
    }

    /* ===== Estados ===== */
    .status-presente {
        color: #15803D;
        font-weight: 600;
    }

    .status-ausente {
        color: #DC2626;
        font-weight: 600;
    }

    .status-retardo {
        color: #D97706;
        font-weight: 600;
    }

    /* ===== Inputs ===== */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] {

        background-color: #FFFFFF !important;
        color: #111827 !important;

        border: 1px solid #D1D5DB;
        border-radius: 10px;

        padding: 0.4rem;
    }

    /* ===== Dataframes ===== */
    .stDataFrame {
        background-color: #FFFFFF;
        border-radius: 12px;
        overflow: hidden;
    }

    /* ===== Alertas ===== */
    .stAlert {
        border-radius: 12px;
    }

    /* ===== Footer ===== */
    footer {
        visibility: hidden;
    }

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
ADMIN_USER = "admi"
ADMIN_PASS = "admi123"

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Asistencias_UGEL"

# ─────────────────────────────────────────────
# CONEXIÓN A GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource(ttl=300)
def get_gspread_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None


def get_sheet(tab_name: str):
    client = get_gspread_client()
    if client is None:
        return None
    try:
        spreadsheet = client.open(SHEET_NAME)
        return spreadsheet.worksheet(tab_name)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(
            f"No se encontró el archivo Google Sheets llamado '{SHEET_NAME}'. "
            "Verifique que el nombre sea exacto y que la cuenta de servicio tenga acceso."
        )
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(
            f"No se encontró la hoja '{tab_name}' dentro del archivo '{SHEET_NAME}'. "
            "Cree la hoja con ese nombre exacto."
        )
        return None
    except Exception as e:
        st.error(f"Error al acceder a la hoja '{tab_name}': {e}")
        return None


def sheet_to_df(tab_name: str) -> pd.DataFrame:
    ws = get_sheet(tab_name)
    if ws is None:
        return pd.DataFrame()
    try:
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al leer datos de '{tab_name}': {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────
def authenticate(usuario: str, password: str):
    """Retorna ('admin', None) o ('director', colegio_id) o (None, None)."""
    if usuario == ADMIN_USER and password == ADMIN_PASS:
        return "admin", None

    df = sheet_to_df("credenciales")
    if df.empty:
        return None, None

    df.columns = [c.strip().lower() for c in df.columns]
    if "colegio_id" not in df.columns or "password" not in df.columns:
        st.error("La hoja 'credenciales' debe tener columnas: colegio_id, password")
        return None, None

    df["colegio_id"] = df["colegio_id"].astype(str).str.strip()
    df["password"] = df["password"].astype(str).str.strip()

    match = df[(df["colegio_id"] == usuario.strip()) & (df["password"] == password.strip())]
    if not match.empty:
        return "director", usuario.strip()

    return None, None


# ─────────────────────────────────────────────
# PANTALLA DE LOGIN
# ─────────────────────────────────────────────
def pantalla_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align:center; color:#1E3A8A;'>UGEL06</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h3 style='text-align:center; color:#374151;'>Sistema de Registro de Asistencias :v</h3>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("**Usuario**")
            usuario = st.text_input("Usuario", label_visibility="collapsed")
            st.markdown("**Contrasena**")
            password = st.text_input("Contrasena", type="password", label_visibility="collapsed")
            submitted = st.form_submit_button("Ingresar", use_container_width=True)

        if submitted:
            if not usuario or not password:
                st.warning("Ingrese usuario y contrasena.")
            else:
                with st.spinner("Verificando credenciales..."):
                    rol, colegio_id = authenticate(usuario, password)
                if rol:
                    st.session_state["rol"] = rol
                    st.session_state["colegio_id"] = colegio_id
                    st.session_state["usuario"] = usuario
                    st.rerun()
                else:
                    st.error("Usuario o contrasena incorrectos.")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center; color:#9CA3AF; font-size:0.8rem;'>"
            "Made by Matías Zamudio</p>",
            unsafe_allow_html=True,
        )
# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<h2 style='color:white;'>UGEL 06</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='color:#CBD5E1;'>Usuario: <strong>{st.session_state.get('usuario','')}</strong></p>",
            unsafe_allow_html=True,
        )
        rol = st.session_state.get("rol", "")
        if rol == "admin":
            st.markdown("<p style='color:#FCD34D;'>Rol: Administrador</p>", unsafe_allow_html=True)
            opcion = st.radio(
                "Menu",
                ["Credenciales", "Profesores", "Reportes"],
                label_visibility="collapsed",
            )
        else:
            colegio = st.session_state.get("colegio_id", "")
            st.markdown(f"<p style='color:#CBD5E1;'>Colegio: <strong>{colegio}</strong></p>", unsafe_allow_html=True)
            st.markdown("<p style='color:#FCD34D;'>Rol: Director</p>", unsafe_allow_html=True)
            opcion = "Asistencia"

        st.markdown("---")
        if st.button("Cerrar sesion"):
            for k in ["rol", "colegio_id", "usuario"]:
                st.session_state.pop(k, None)
            st.rerun()

    return opcion


# ─────────────────────────────────────────────
# MODULO DIRECTOR: REGISTRO DE ASISTENCIA
# ─────────────────────────────────────────────
def modulo_director():
    colegio_id = st.session_state["colegio_id"]

    st.markdown(f"<h2>Registro de Asistencia</h2>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='info-card'>Colegio: <strong>{colegio_id}</strong></div>",
        unsafe_allow_html=True,
    )

    fecha_sel = st.date_input("Fecha de registro", value=date.today())
    fecha_str = fecha_sel.strftime("%Y-%m-%d")

    # Cargar profesores del colegio
    df_prof = sheet_to_df("profesores")
    if df_prof.empty:
        st.info("No hay profesores registrados. Contacte al administrador.")
        return

    df_prof.columns = [c.strip().lower() for c in df_prof.columns]
    if "colegio" not in df_prof.columns or "nombre" not in df_prof.columns:
        st.error("La hoja 'profesores' debe tener columnas: colegio, nombre, grado")
        return

    df_prof["colegio"] = df_prof["colegio"].astype(str).str.strip()
    mis_profesores = df_prof[df_prof["colegio"] == colegio_id].reset_index(drop=True)

    if mis_profesores.empty:
        st.info(f"No hay profesores registrados para el colegio '{colegio_id}'.")
        return

    # Cargar asistencias ya guardadas para esa fecha
    df_asist = sheet_to_df("asistencias")
    asist_hoy = {}
    if not df_asist.empty:
        df_asist.columns = [c.strip().lower() for c in df_asist.columns]
        if "fecha" in df_asist.columns:
            df_asist["fecha"] = df_asist["fecha"].astype(str)
            df_asist["colegio"] = df_asist["colegio"].astype(str).str.strip() if "colegio" in df_asist.columns else ""
            df_asist["profesor"] = df_asist["profesor"].astype(str).str.strip() if "profesor" in df_asist.columns else ""
            filtro = (df_asist["fecha"] == fecha_str) & (df_asist["colegio"] == colegio_id)
            for _, row in df_asist[filtro].iterrows():
                asist_hoy[row["profesor"]] = row

    st.markdown(f"<div class='section-header'>Profesores - {fecha_str}</div>", unsafe_allow_html=True)

    estados_opciones = ["Presente", "Ausente", "Tardanza", "Licencia", "Sanción"]
    registros = []

    with st.form("form_asistencia"):
        for idx, row in mis_profesores.iterrows():
            nombre = str(row["nombre"]).strip()
            grado = str(row.get("grado", "")).strip()

            # Valores por defecto desde registros previos
            prev = asist_hoy.get(nombre, None)
            def_estado = prev["estado"] if prev is not None and "estado" in prev else "Presente"
            def_horas = float(prev["horas"]) if prev is not None and "horas" in prev and str(prev["horas"]).strip() != "" else 6.0
            def_obs = str(prev["observacion"]) if prev is not None and "observacion" in prev else ""

            if def_estado not in estados_opciones:
                def_estado = "Presente"

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1.5, 3])
                with col1:
                    st.markdown(f"**{nombre}**")
                    if grado:
                        st.caption(f"Grado: {grado}")
                with col2:
                    estado = st.selectbox(
                        "Estado",
                        estados_opciones,
                        index=estados_opciones.index(def_estado),
                        key=f"estado_{idx}",
                        label_visibility="collapsed",
                    )
                with col3:
                    horas = st.number_input(
                        "Horas",
                        min_value=0.0,
                        max_value=12.0,
                        value=def_horas,
                        step=0.5,
                        key=f"horas_{idx}",
                        label_visibility="collapsed",
                    )
                with col4:
                    observacion = st.text_input(
                        "Observacion",
                        value=def_obs,
                        placeholder="Observacion (opcional)",
                        key=f"obs_{idx}",
                        label_visibility="collapsed",
                    )

            registros.append((nombre, estado, horas, observacion))
            st.divider()

        guardar = st.form_submit_button("Guardar Asistencia", use_container_width=True)

    if guardar:
        _guardar_asistencia(colegio_id, fecha_str, registros, asist_hoy, df_asist)


def _guardar_asistencia(colegio_id, fecha_str, registros, asist_hoy, df_asist_completo):
    ws = get_sheet("asistencias")
    if ws is None:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Si ya existen registros para esa fecha/colegio, eliminarlos primero
        all_data = ws.get_all_values()
        if len(all_data) > 1:
            headers = [h.strip().lower() for h in all_data[0]]
            rows_to_delete = []
            for i, row in enumerate(all_data[1:], start=2):
                row_dict = dict(zip(headers, row))
                if (
                    row_dict.get("fecha", "") == fecha_str
                    and row_dict.get("colegio", "").strip() == colegio_id
                ):
                    rows_to_delete.append(i)

            # Eliminar de abajo hacia arriba para no desplazar índices
            for row_idx in reversed(rows_to_delete):
                ws.delete_rows(row_idx)

        # Agregar nuevas filas
        nuevas_filas = []
        for nombre, estado, horas, observacion in registros:
            nuevas_filas.append([
                colegio_id, nombre, fecha_str, estado,
                str(horas), observacion, timestamp
            ])

        if nuevas_filas:
            ws.append_rows(nuevas_filas, value_input_option="RAW")

        st.success(f"Asistencia guardada correctamente para {len(nuevas_filas)} profesores.")
        st.cache_resource.clear()
    except Exception as e:
        st.error(f"Error al guardar asistencia: {e}")


# ─────────────────────────────────────────────
# MODULO ADMIN: CREDENCIALES
# ─────────────────────────────────────────────
def modulo_credenciales():
    st.markdown("<h2>Gestion de Credenciales</h2>", unsafe_allow_html=True)

    df = sheet_to_df("credenciales")
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]

    # Buscar colegio
    st.markdown("<div class='section-header'>Buscar Colegio</div>", unsafe_allow_html=True)
    buscar = st.text_input("Codigo de colegio", placeholder="Ingrese codigo para filtrar...")
    if not df.empty and "colegio_id" in df.columns:
        df_show = df[df["colegio_id"].astype(str).str.contains(buscar, case=False, na=False)] if buscar else df
        st.dataframe(df_show.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No hay colegios registrados aun.")

    st.markdown("---")

    # Agregar colegio
    st.markdown("<div class='section-header'>Agregar Nuevo Colegio</div>", unsafe_allow_html=True)
    with st.form("form_agregar_colegio"):
        col1, col2 = st.columns(2)
        with col1:
            nuevo_cod = st.text_input("Codigo del colegio")
        with col2:
            nuevo_pass = st.text_input("Contrasena inicial", type="password")
        if st.form_submit_button("Agregar Colegio"):
            if not nuevo_cod or not nuevo_pass:
                st.warning("Complete todos los campos.")
            else:
                ws = get_sheet("credenciales")
                if ws:
                    # Verificar duplicado
                    existing = df["colegio_id"].astype(str).tolist() if not df.empty and "colegio_id" in df.columns else []
                    if nuevo_cod.strip() in existing:
                        st.error(f"El colegio '{nuevo_cod}' ya existe.")
                    else:
                        try:
                            ws.append_row([nuevo_cod.strip(), nuevo_pass.strip()])
                            st.success(f"Colegio '{nuevo_cod}' agregado.")
                            st.cache_resource.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    st.markdown("---")

    # Actualizar contraseña
    st.markdown("<div class='section-header'>Actualizar Contrasena</div>", unsafe_allow_html=True)
    with st.form("form_actualizar_pass"):
        col1, col2 = st.columns(2)
        with col1:
            upd_cod = st.text_input("Codigo del colegio a modificar")
        with col2:
            upd_pass = st.text_input("Nueva contrasena", type="password")
        if st.form_submit_button("Actualizar Contrasena"):
            if not upd_cod or not upd_pass:
                st.warning("Complete todos los campos.")
            else:
                _actualizar_password(upd_cod.strip(), upd_pass.strip(), df)

    st.markdown("---")

    # Eliminar colegio
    st.markdown("<div class='section-header'>Eliminar Colegio</div>", unsafe_allow_html=True)
    with st.form("form_eliminar_colegio"):
        del_cod = st.text_input("Codigo del colegio a eliminar")
        confirm = st.checkbox("Confirmo que deseo eliminar este colegio")
        if st.form_submit_button("Eliminar Colegio"):
            if not del_cod:
                st.warning("Ingrese el codigo del colegio.")
            elif not confirm:
                st.warning("Debe confirmar la eliminacion.")
            else:
                _eliminar_colegio(del_cod.strip(), df)


def _actualizar_password(colegio_id, nueva_pass, df):
    ws = get_sheet("credenciales")
    if ws is None:
        return
    try:
        all_data = ws.get_all_values()
        headers = [h.strip().lower() for h in all_data[0]]
        col_idx = headers.index("colegio_id")
        pass_idx = headers.index("password")
        for i, row in enumerate(all_data[1:], start=2):
            if len(row) > col_idx and str(row[col_idx]).strip() == colegio_id:
                ws.update_cell(i, pass_idx + 1, nueva_pass)
                st.success(f"Contrasena actualizada para '{colegio_id}'.")
                st.cache_resource.clear()
                return
        st.error(f"No se encontro el colegio '{colegio_id}'.")
    except Exception as e:
        st.error(f"Error: {e}")


def _eliminar_colegio(colegio_id, df):
    ws = get_sheet("credenciales")
    if ws is None:
        return
    try:
        all_data = ws.get_all_values()
        headers = [h.strip().lower() for h in all_data[0]]
        col_idx = headers.index("colegio_id")
        for i, row in enumerate(all_data[1:], start=2):
            if len(row) > col_idx and str(row[col_idx]).strip() == colegio_id:
                ws.delete_rows(i)
                st.success(f"Colegio '{colegio_id}' eliminado.")
                st.cache_resource.clear()
                st.rerun()
                return
        st.error(f"No se encontro el colegio '{colegio_id}'.")
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────
# MODULO ADMIN: PROFESORES
# ─────────────────────────────────────────────
def modulo_profesores():
    st.markdown("<h2>Gestion de Profesores</h2>", unsafe_allow_html=True)

    df = sheet_to_df("profesores")
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]

    st.markdown("<div class='section-header'>Lista de Profesores</div>", unsafe_allow_html=True)
    if not df.empty:
        filtro_col = st.text_input("Filtrar por colegio", placeholder="Codigo de colegio...")
        df_show = df[df["colegio"].astype(str).str.contains(filtro_col, case=False, na=False)] if filtro_col else df
        st.dataframe(df_show.reset_index(drop=True), use_container_width=True)
        st.caption(f"Total: {len(df_show)} profesores")
    else:
        st.info("No hay profesores registrados.")

    st.markdown("---")

    # Agregar profesor
    st.markdown("<div class='section-header'>Agregar Profesor</div>", unsafe_allow_html=True)
    with st.form("form_agregar_prof"):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_colegio = st.text_input("Codigo del colegio")
        with col2:
            p_nombre = st.text_input("Nombre completo del profesor")
        with col3:
            p_grado = st.text_input("Grado / Nivel")
        if st.form_submit_button("Agregar Profesor"):
            if not p_colegio or not p_nombre:
                st.warning("Colegio y nombre son obligatorios.")
            else:
                ws = get_sheet("profesores")
                if ws:
                    try:
                        ws.append_row([p_colegio.strip(), p_nombre.strip(), p_grado.strip()])
                        st.success(f"Profesor '{p_nombre}' agregado al colegio '{p_colegio}'.")
                        st.cache_resource.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.markdown("---")

    # Eliminar profesor
    st.markdown("<div class='section-header'>Eliminar Profesor</div>", unsafe_allow_html=True)
    with st.form("form_eliminar_prof"):
        col1, col2 = st.columns(2)
        with col1:
            del_colegio = st.text_input("Codigo del colegio")
        with col2:
            del_nombre = st.text_input("Nombre exacto del profesor")
        confirm_del = st.checkbox("Confirmo que deseo eliminar este profesor")
        if st.form_submit_button("Eliminar Profesor"):
            if not del_colegio or not del_nombre:
                st.warning("Complete los campos.")
            elif not confirm_del:
                st.warning("Debe confirmar la eliminacion.")
            else:
                _eliminar_profesor(del_colegio.strip(), del_nombre.strip())


def _eliminar_profesor(colegio, nombre):
    ws = get_sheet("profesores")
    if ws is None:
        return
    try:
        all_data = ws.get_all_values()
        headers = [h.strip().lower() for h in all_data[0]]
        col_idx = headers.index("colegio")
        nom_idx = headers.index("nombre")
        for i, row in enumerate(all_data[1:], start=2):
            if (
                len(row) > max(col_idx, nom_idx)
                and str(row[col_idx]).strip() == colegio
                and str(row[nom_idx]).strip() == nombre
            ):
                ws.delete_rows(i)
                st.success(f"Profesor '{nombre}' eliminado.")
                st.cache_resource.clear()
                st.rerun()
                return
        st.error(f"No se encontro el profesor '{nombre}' en el colegio '{colegio}'.")
    except Exception as e:
        st.error(f"Error: {e}")


# ─────────────────────────────────────────────
# MODULO ADMIN: REPORTES
# ─────────────────────────────────────────────
def modulo_reportes():
    st.markdown("<h2>Reportes de Asistencia</h2>", unsafe_allow_html=True)

    df_asist = sheet_to_df("asistencias")
    if df_asist.empty:
        st.info("No hay asistencias registradas aun.")
        return

    df_asist.columns = [c.strip().lower() for c in df_asist.columns]

    # Filtros
    st.markdown("<div class='section-header'>Filtros</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    colegios = ["Todos"] + sorted(df_asist["colegio"].astype(str).unique().tolist()) if "colegio" in df_asist.columns else ["Todos"]
    with col1:
        filtro_colegio = st.selectbox("Colegio", colegios)
    with col2:
        fecha_ini = st.date_input("Desde", value=date.today().replace(day=1))
    with col3:
        fecha_fin = st.date_input("Hasta", value=date.today())

    # Aplicar filtros
    df_filtrado = df_asist.copy()
    if "colegio" in df_filtrado.columns and filtro_colegio != "Todos":
        df_filtrado = df_filtrado[df_filtrado["colegio"].astype(str) == filtro_colegio]
    if "fecha" in df_filtrado.columns:
        df_filtrado["fecha"] = df_filtrado["fecha"].astype(str)
        df_filtrado = df_filtrado[
            (df_filtrado["fecha"] >= fecha_ini.strftime("%Y-%m-%d")) &
            (df_filtrado["fecha"] <= fecha_fin.strftime("%Y-%m-%d"))
        ]

    st.markdown(f"<div class='info-card'>Registros encontrados: <strong>{len(df_filtrado)}</strong></div>", unsafe_allow_html=True)

    # Resumen en pantalla
    st.markdown("<div class='section-header'>Resumen por Profesor</div>", unsafe_allow_html=True)
    if not df_filtrado.empty and "profesor" in df_filtrado.columns and "estado" in df_filtrado.columns:
        df_res = _calcular_resumen(df_filtrado)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.info("No hay datos suficientes para el resumen.")
        df_res = pd.DataFrame()

    st.markdown("---")

    # Descarga Excel
    st.markdown("<div class='section-header'>Descargar Reporte Excel</div>", unsafe_allow_html=True)
    if st.button("Generar y Descargar Excel"):
        if df_filtrado.empty:
            st.warning("No hay datos para exportar con los filtros actuales.")
        else:
            excel_bytes = _generar_excel(df_filtrado, df_res)
            nombre_archivo = f"Reporte_Asistencias_{fecha_ini}_{fecha_fin}.xlsx"
            st.download_button(
                label="Descargar archivo Excel",
                data=excel_bytes,
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    st.markdown("---")

    # Actualizar estadísticas en hoja profesores
    st.markdown("<div class='section-header'>Actualizar Estadisticas en Hoja Profesores</div>", unsafe_allow_html=True)
    st.caption("Escribe dias_presentes, dias_ausentes y dias_retardo en la hoja 'profesores'.")
    if st.button("Actualizar Estadisticas"):
        _actualizar_estadisticas_profesores(df_asist)


def _calcular_resumen(df: pd.DataFrame) -> pd.DataFrame:
    df["horas"] = pd.to_numeric(df["horas"], errors="coerce").fillna(0)
    df_estado = df["estado"].astype(str).str.strip().str.capitalize()

    resumen = df.groupby(["colegio", "profesor"]).agg(
        total_dias=("fecha", "nunique"),
    ).reset_index()

    for est, col in [("Presente", "presentes"), ("Ausente", "ausencias"), ("Retardo", "retardos")]:
        temp = df[df["estado"].astype(str).str.strip().str.capitalize() == est].groupby(["colegio", "profesor"]).size().reset_index(name=col)
        resumen = resumen.merge(temp, on=["colegio", "profesor"], how="left")

    horas_tot = df.groupby(["colegio", "profesor"])["horas"].sum().reset_index(name="horas_totales")
    resumen = resumen.merge(horas_tot, on=["colegio", "profesor"], how="left")

    for col in ["presentes", "ausencias", "retardos"]:
        resumen[col] = resumen[col].fillna(0).astype(int)
    resumen["horas_totales"] = resumen["horas_totales"].fillna(0).round(1)
    resumen["pct_asistencia"] = (resumen["presentes"] / resumen["total_dias"] * 100).round(1)

    return resumen


def _generar_excel(df_detalle: pd.DataFrame, df_resumen: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_detalle.to_excel(writer, sheet_name="Detalle", index=False)
        if not df_resumen.empty:
            df_resumen.to_excel(writer, sheet_name="Resumen_Profesores", index=False)
    return output.getvalue()


def _actualizar_estadisticas_profesores(df_asist: pd.DataFrame):
    ws = get_sheet("profesores")
    if ws is None:
        return
    try:
        all_data = ws.get_all_values()
        if not all_data:
            st.error("La hoja 'profesores' esta vacia.")
            return

        headers = [h.strip().lower() for h in all_data[0]]
        col_colegio = headers.index("colegio") if "colegio" in headers else None
        col_nombre = headers.index("nombre") if "nombre" in headers else None

        if col_colegio is None or col_nombre is None:
            st.error("La hoja 'profesores' no tiene columnas 'colegio' y 'nombre'.")
            return

        # Asegurar columnas estadísticas
        nuevas_cols = ["dias_presente", "dias_ausentes", "dias_retardo"]
        for nc in nuevas_cols:
            if nc not in headers:
                ws.add_cols_to_sheet if False else None
                # Agregar encabezado
                col_pos = len(headers) + 1
                ws.update_cell(1, col_pos, nc)
                headers.append(nc)

        col_presente = headers.index("dias_presente")
        col_ausente = headers.index("dias_ausentes")
        col_retardo = headers.index("dias_retardo")

        # Calcular stats
        stats = {}
        for _, row in df_asist.iterrows():
            key = (str(row.get("colegio", "")).strip(), str(row.get("profesor", "")).strip())
            est = str(row.get("estado", "")).strip().capitalize()
            if key not in stats:
                stats[key] = {"Presente": 0, "Ausente": 0, "Retardo": 0}
            if est in stats[key]:
                stats[key][est] += 1

        # Actualizar filas
        updates = []
        for i, row in enumerate(all_data[1:], start=2):
            if len(row) > max(col_colegio, col_nombre):
                key = (str(row[col_colegio]).strip(), str(row[col_nombre]).strip())
                if key in stats:
                    s = stats[key]
                    updates.append({"range": f"R{i}C{col_presente+1}", "values": [[s["Presente"]]]})
                    updates.append({"range": f"R{i}C{col_ausente+1}", "values": [[s["Ausente"]]]})
                    updates.append({"range": f"R{i}C{col_retardo+1}", "values": [[s["Retardo"]]]})

        if updates:
            ws.spreadsheet.values_batch_update({"valueInputOption": "RAW", "data": updates})

        st.success("Estadisticas actualizadas correctamente.")
        st.cache_resource.clear()
    except Exception as e:
        st.error(f"Error al actualizar estadisticas: {e}")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────
def main():
    if "rol" not in st.session_state:
        pantalla_login()
        return

    opcion = render_sidebar()
    rol = st.session_state.get("rol", "")

    if rol == "director":
        modulo_director()
    elif rol == "admin":
        if opcion == "Credenciales":
            modulo_credenciales()
        elif opcion == "Profesores":
            modulo_profesores()
        elif opcion == "Reportes":
            modulo_reportes()


if __name__ == "__main__":
    main()
