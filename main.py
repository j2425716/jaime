import streamlit as st
import json
import os
from fpdf import FPDF
import datetime
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple, Dict
import math
from PIL import Image
import base64

# Constantes y configuración inicial
FACTURAS_FILE = "facturas.json"
FACTURAS_DIR = "facturas"
ASSETS_DIR = "/assets"
IGV_RATE = Decimal('0.18')

# Asegurar que los directorios existen
os.makedirs(FACTURAS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Función para convertir la imagen en base64
def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


class FacturaError(Exception):
    """Clase personalizada para errores relacionados con facturas"""
    pass

def decimal_to_str(value: Decimal) -> str:
    """Convierte un Decimal a string con formato de moneda"""
    return f"S/ {value:.2f}"

def calcular_base_imponible(total: Decimal) -> Decimal:
    """Calcula la base imponible a partir del total que incluye IGV"""
    return (total / (Decimal('1') + IGV_RATE)).quantize(Decimal('0.01'), ROUND_HALF_UP)

def calcular_igv(base_imponible: Decimal) -> Decimal:
    """Calcula el IGV a partir de la base imponible"""
    return (base_imponible * IGV_RATE).quantize(Decimal('0.01'), ROUND_HALF_UP)

def cargar_facturas() -> List[Dict]:
    try:
        if os.path.exists(FACTURAS_FILE):
            with open(FACTURAS_FILE, "r", encoding='utf-8') as file:
                content = file.read()
                if not content.strip():
                    return []
                return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        st.error(f"Error al cargar facturas: {str(e)}")
        return []
    return []

def guardar_facturas(facturas: List[Dict]) -> None:
    """Guarda las facturas en el archivo JSON con manejo de errores"""
    try:
        with open(FACTURAS_FILE, "w", encoding='utf-8') as file:
            json.dump(facturas, file, indent=4, ensure_ascii=False)
    except (IOError, TypeError, ValueError) as e:
        st.error(f"Error al guardar facturas: {str(e)}")
        raise FacturaError("No se pudo guardar la factura")
    except Exception as e:
        st.error(f"Error inesperado al guardar facturas: {str(e)}")
        raise FacturaError("No se pudo guardar la factura debido a un error inesperado")

def generar_factura(cliente: str, productos: List[Tuple[str, int, float]], descuento: float, factura_id: int, notas: str = "") -> str:
    """Genera el PDF de la factura con mejor formato y manejo de errores"""
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Encabezado
        if os.path.exists(os.path.join(ASSETS_DIR, "logo.png")):
            pdf.image(os.path.join(ASSETS_DIR, "logo.png"), x=10, y=10, w=30)
            pdf.ln(35)  # Espacio después del logo
        
        pdf.set_font("Arial", style='B', size=16)
        pdf.cell(200, 10, "FACTURA", ln=True, align='C')
        pdf.ln(10)

        # Información del cliente
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}", ln=True)
        pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)
        pdf.cell(200, 10, f"Factura N°: {factura_id:04d}", ln=True)
        pdf.ln(10)

        # Tabla de productos
        pdf.set_font("Arial", style='B', size=12)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(80, 10, "Producto", border=1, fill=True)
        pdf.cell(30, 10, "Cantidad", border=1, fill=True)
        pdf.cell(40, 10, "Precio Unit.", border=1, fill=True)
        pdf.cell(40, 10, "Total", border=1, fill=True)
        pdf.ln()

        # Contenido de la tabla
        subtotal = Decimal('0')
        pdf.set_font("Arial", size=12)
        
        for nombre, cantidad, precio in productos:
            precio_decimal = Decimal(str(precio))
            total_linea = precio_decimal * Decimal(str(cantidad))
            base_imponible = calcular_base_imponible(total_linea)
            subtotal += base_imponible
            
            pdf.cell(80, 10, nombre[:30], border=1)
            pdf.cell(30, 10, str(cantidad), border=1, align='R')
            pdf.cell(40, 10, decimal_to_str(precio_decimal), border=1, align='R')
            pdf.cell(40, 10, decimal_to_str(total_linea), border=1, align='R')
            pdf.ln()

        # Cálculos finales
        igv = calcular_igv(subtotal)
        descuento_decimal = Decimal(str(descuento))
        total = subtotal + igv - descuento_decimal

        # Totales
        pdf.ln(5)
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(150, 10, "Subtotal:", border=1, align='R')
        pdf.cell(40, 10, decimal_to_str(subtotal), border=1, align='R')
        pdf.ln()
        pdf.cell(150, 10, "IGV (18%):", border=1, align='R')
        pdf.cell(40, 10, decimal_to_str(igv), border=1, align='R')
        pdf.ln()
        pdf.cell(150, 10, "Descuento:", border=1, align='R')
        pdf.cell(40, 10, f"-{decimal_to_str(descuento_decimal)}", border=1, align='R')
        pdf.ln()
        pdf.cell(150, 10, "Total a Pagar:", border=1, align='R')
        pdf.cell(40, 10, decimal_to_str(total), border=1, align='R')

        # Agregar notas si existen
        if notas.strip():
            pdf.ln(10)
            pdf.set_font("Arial", style='B', size=12)
            pdf.cell(190, 10, "Notas:", ln=True)
            pdf.set_font("Arial", size=10)
            for linea in notas.split('\n'):
                pdf.multi_cell(190, 7, linea)

        # Agregar términos y condiciones
        pdf.ln(10)
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(190, 10, "Términos y Condiciones:", ln=True)
        pdf.set_font("Arial", size=10)
        terminos = [
            "1. El pago debe realizarse en la fecha de vencimiento indicada.",
            "2. Los precios incluyen IGV (18%).",
            "3. La factura es un documento oficial y debe conservarse para fines tributarios.",
            "4. Los productos entregados no tienen devolución salvo defectos de fábrica.",
            "5. Para cualquier reclamo, presentar esta factura dentro de las 24 horas siguientes.",
            "6. La empresa se reserva el derecho de modificar estos términos previo aviso."
        ]
        for termino in terminos:
            pdf.multi_cell(190, 7, termino)

        # Guardar PDF
        filename = os.path.join(FACTURAS_DIR, f"factura_{factura_id:04d}_{int(time.time())}.pdf")
        pdf.output(filename)
        return filename

    except (IOError, RuntimeError) as e:
        st.error(f"Error al generar el PDF: {str(e)}")
        raise FacturaError("No se pudo generar la factura PDF")

def validar_producto(nombre: str, cantidad: int, precio: float) -> bool:
    if not nombre.strip():
        st.error("El nombre del producto no puede estar vacío")
        return False
    if cantidad < 1:
        st.error("La cantidad debe ser mayor a 0")
        return False
    if precio <= 0 or not math.isfinite(precio):
        st.error("El precio debe ser un número válido y mayor a 0")
        return False
    return True

def editar_producto(index: int, nuevo_nombre: str, nueva_cantidad: int, nuevo_precio: float):
    """Edita un producto en la lista de productos"""
    if validar_producto(nuevo_nombre, nueva_cantidad, nuevo_precio):
        st.session_state['productos'][index] = (nuevo_nombre, nueva_cantidad, nuevo_precio)
        st.session_state['producto_editando'] = None
        st.success("✅ Producto actualizado")
        st.rerun()

def eliminar_producto(index: int):
    """Elimina un producto de la lista de productos"""
    if 'productos' in st.session_state and index < len(st.session_state['productos']):
        st.session_state['productos'].pop(index)
        st.success("✅ Producto eliminado correctamente")
        st.rerun()
    else:
        st.error("Error al eliminar el producto")

def obtener_siguiente_id(facturas: List[Dict]) -> int:
    """Obtiene el siguiente ID disponible para una nueva factura"""
    if not facturas:
        return 1
    return max(factura['id'] for factura in facturas) + 1

def nueva_factura():
    """Limpia el estado para crear una nueva factura"""
    st.session_state.clear()
    st.session_state['productos'] = []
    st.session_state['cliente_actual'] = ''
    st.session_state['remitente'] = ''
    st.session_state['factura_editando'] = None
    st.session_state['producto_editando'] = None
    st.rerun()

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Facturación",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    /* Estilos generales */
    .stApp {
        background-color: #1a1a2e;
        color: #e0e0e0;
    }
    
    /* Estilo para el título principal */
    .main-title {
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #2a2a4a 0%, #1a1a2e 100%);
    }
    
    /* Estilo para las cajas de entrada */
    .stTextInput input, .stNumberInput input, .stDateInput input {
        background-color: #2a2a4a !important;
        color: white !important;
        border: 1px solid #3a3a5a !important;
        border-radius: 8px !important;
    }
    
    /* Estilo para los botones */
    .stButton button {
        background-color: #4a4a8a !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
    }
    
    /* Estilo para las tarjetas */
    .card {
        background-color: #2a2a4a;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #3a3a5a;
        margin-bottom: 1rem;
    }
    
    /* Estilo para las tablas */
    .stDataFrame {
        background-color: #2a2a4a !important;
        border-radius: 10px !important;
    }
    
    /* Estilo para los selectores */
    .stSelectbox select {
        background-color: #2a2a4a !important;
        color: white !important;
        border: 1px solid #3a3a5a !important;
        border-radius: 8px !important;
    }
    
    /* Estilo para los expansores */
    .streamlit-expanderHeader {
        background-color: #2a2a4a !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Logo personalizado */
    .logo-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 2rem;
        padding: 1rem;
        background-color: #2a2a4a;
        border-radius: 10px;
    }
    
    .logo-text {
        color: white;
        font-size: 2rem;
        font-weight: bold;
    }

    /* Estilo para los campos de texto */
    .stTextArea textarea {
        background-color: #2a2a4a !important;
        color: white !important;
        border: 1px solid #3a3a5a !important;
        border-radius: 8px !important;
    }

    /* Estilo para los mensajes de éxito y error */
    .stSuccess, .stError {
        background-color: #2a2a4a !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }

    /* Estilo para la imagen del logo */
    .logo-img {
        width: 100px;
        height: auto;
        object-fit: contain;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Logo y título
    logo_path = os.path.join(ASSETS_DIR, "logo.png")

    if os.path.exists(logo_path):
        logo_base64 = image_to_base64(logo_path)
        st.markdown(f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}" class="logo-img" />
            <div class="logo-text">FACTURA</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="logo-container">
            <div style="background-color: #6b46c1; width: 50px; height: 50px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 24px;">V</div>
            <div class="logo-text">FACTURA</div>
        </div>
        """, unsafe_allow_html=True)

    # Inicialización del estado
    if 'facturas' not in st.session_state:
        st.session_state['facturas'] = cargar_facturas()
    if 'productos' not in st.session_state:
        st.session_state['productos'] = []
    if 'factura_editando' not in st.session_state:
        st.session_state['factura_editando'] = None
    if 'producto_editando' not in st.session_state:
        st.session_state['producto_editando'] = None
    if 'remitente' not in st.session_state:
        st.session_state['remitente'] = ""


    # Subir logo
    with st.sidebar:
        st.header("Configuración")
        logo_file = st.file_uploader("Subir logo", type=['png', 'jpg', 'jpeg'])
        if logo_file is not None:
            try:
                # Guardar el logo
                with open(os.path.join(ASSETS_DIR, "logo.png"), "wb") as f:
                    f.write(logo_file.getbuffer())
                st.success("✅ Logo actualizado correctamente")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar el logo: {str(e)}")

    # Botón de Nueva Factura
    col_nueva_factura = st.columns([6, 1])[1]
    with col_nueva_factura:
        if st.button("📄 Nueva Factura", key="nueva_factura", type="primary"):
            nueva_factura()

    # Contenedor principal
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        # Información de la factura
        col1, col2, col3 = st.columns([2,2,1])
        
        with col1:
            remitente_temp = st.session_state['remitente']
            remitente_input = st.text_input("De:", value=remitente_temp, key="remitente_input")
            
        with col2:
            cliente = st.text_input("Cobrar a:", 
                                  placeholder="Para quién es la factura",
                                  value=st.session_state.get('cliente_actual', ''))
            
        with col3:
            st.text_input("Número de factura",
                         placeholder="#0001",
                         key="numero_factura")

        # Fechas
        col1, col2 = st.columns(2)
        with col1:
            fecha_emision = st.date_input("Fecha", datetime.date.today())
        with col2:
            fecha_vencimiento = st.date_input("Fecha de vencimiento", 
                                            fecha_emision + datetime.timedelta(days=30))

        st.markdown('</div>', unsafe_allow_html=True)


        # Sección de productos
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Artículos")
        
        # Formulario para agregar productos
        with st.form("producto_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([3,1,1])
            
            with col1:
                nombre = st.text_input("Descripción del servicio o producto",
                                     placeholder="Ej: Consultoría")
            with col2:
                cantidad = st.number_input("Cantidad", min_value=1, value=1)
            with col3:
                precio = st.number_input("Precio", min_value=0.0, value=0.0, format="%.2f")
                
            submitted = st.form_submit_button("Añadir artículo")
            
            if submitted and validar_producto(nombre, cantidad, precio):
                st.session_state['productos'].append((nombre, cantidad, precio))
                st.success("✅ Producto añadido")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Lista de productos
        if st.session_state['productos']:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("### Lista de Productos")
            
            for i, (nombre, cantidad, precio) in enumerate(st.session_state['productos']):
                cols = st.columns([3, 2, 2, 1, 1])
                
                if st.session_state.get('producto_editando') == i:
                    with cols[0]:
                        nuevo_nombre = st.text_input("Nombre", nombre, key=f"edit_nombre_{i}")
                    with cols[1]:
                        nueva_cantidad = st.number_input("Cantidad", min_value=1, value=cantidad, key=f"edit_cantidad_{i}")
                    with cols[2]:
                        nuevo_precio = st.number_input("Precio", min_value=0.01, value=precio, key=f"edit_precio_{i}", format="%.2f")
                    with cols[3]:
                        if st.button("💾", key=f"guardar_{i}"):
                            editar_producto(i, nuevo_nombre, nueva_cantidad, nuevo_precio)
                    with cols[4]:
                        if st.button("❌", key=f"cancelar_{i}"):
                            st.session_state['producto_editando'] = None
                            st.rerun()
                else:
                    cols[0].write(nombre)
                    cols[1].write(str(cantidad))
                    cols[2].write(f"S/ {precio:.2f}")
                    with cols[3]:
                        if st.button("✏️", key=f"edit_{i}"):
                            st.session_state['producto_editando'] = i
                            st.rerun()
                    with cols[4]:
                        if st.button("🗑️", key=f"delete_{i}"):
                            eliminar_producto(i)

            # Sección de totales y descuento
            st.write("---")
            subtotal = Decimal('0')
            precio_decimal = Decimal(str(precio))
            total_linea = precio_decimal * Decimal(str(cantidad))
            base_imponible = calcular_base_imponible(total_linea)
            subtotal += base_imponible
            
            st.write(f"**Subtotal:** {decimal_to_str(subtotal)}")

            descuento = st.number_input("Descuento", 
                                      min_value=0.00,
                                      max_value=float(subtotal),
                                      step=0.01,
                                      format="%.2f")

            
            igv = calcular_igv(subtotal)
            descuento_decimal = Decimal(str(descuento))
            total = subtotal + igv - descuento_decimal

            st.write(f"**Subtotal con Descuento:** {decimal_to_str(subtotal)}")
            st.write(f"**IGV (18%):** {decimal_to_str(igv)}")
            st.write(f"**Total a Pagar:** {decimal_to_str(total)}")

            st.markdown('</div>', unsafe_allow_html=True)

        # Sección de notas y términos
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            notas = st.text_area("Notas", 
                               placeholder="Notas adicionales para el cliente...")
        
        with col2:
            with st.expander("📋 Ver Términos y Condiciones"):
                st.markdown("""
                1. El pago debe realizarse en la fecha de vencimiento indicada.
                2. Los precios incluyen IGV (18%).
                3. La factura es un documento oficial y debe conservarse.
                4. Los productos no tienen devolución salvo defectos.
                5. Reclamos dentro de las 24 horas siguientes.
                """)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # Botón de generar factura
        if st.button("💾 Generar Factura", type="primary", use_container_width=True, 
                    disabled=not cliente.strip() or not st.session_state['productos']):
            try:
                factura_id = (st.session_state['factura_editando'] or 
                            obtener_siguiente_id(st.session_state['facturas']))
                
                pdf_path = generar_factura(
                    cliente,
                    st.session_state['productos'],
                    descuento,
                    factura_id,
                    notas
                )
                
                nueva_factura_data = {
                    "id": factura_id,
                    "cliente": cliente,
                    "archivo": pdf_path,
                    "productos": st.session_state['productos'],
                    "descuento": descuento,
                    "fecha_emision": fecha_emision.isoformat(),
                    "fecha_vencimiento": fecha_vencimiento.isoformat(),
                    "notas": notas
                }

                if st.session_state['factura_editando']:
                    st.session_state['facturas'] = [
                        f for f in st.session_state['facturas'] 
                        if f['id'] != factura_id
                    ]
                
                st.session_state['facturas'].append(nueva_factura_data)
                guardar_facturas(st.session_state['facturas'])
                
                st.success("✅ Factura generada correctamente")
                nueva_factura()
            
            except FacturaError as e:
                st.error(f"Error: {str(e)}")

    # Mostrar facturas existentes
    if st.session_state['facturas']:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📂 Facturas Generadas")
        
        for factura in sorted(st.session_state['facturas'], 
                            key=lambda x: x['id'], reverse=True):
            with st.expander(f"📄 Factura {factura['id']:04d} - {factura['cliente']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if os.path.exists(factura['archivo']):
                        with open(factura['archivo'], "rb") as file:
                            st.download_button(
                                "📥 Descargar PDF",
                                data=file,
                                file_name=os.path.basename(factura['archivo']),
                                mime="application/pdf",
                                key=f"download_{factura['id']}"
                            )
                
                with col2:
                    if st.button("✏️ Editar", key=f"editar_{factura['id']}"):
                        st.session_state['productos'] = factura['productos']
                        st.session_state['cliente_actual'] = factura['cliente']
                        st.session_state['remitente'] = factura.get('remitente', "")  # 🔹 Cargar remitente
                        st.session_state['factura_editando'] = factura['id']
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Eliminar", key=f"eliminar_{factura['id']}"):
                        if os.path.exists(factura['archivo']):
                            os.remove(factura['archivo'])
                        st.session_state['facturas'] = [
                            f for f in st.session_state['facturas'] 
                            if f['id'] != factura['id']
                        ]
                        guardar_facturas(st.session_state['facturas'])
                        st.success("✅ Factura eliminada correctamente")
                        st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()