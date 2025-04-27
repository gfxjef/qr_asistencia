import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_migrate import Migrate
from models import db, Asistente, Charla, asistente_charla
from utils import generate_qr_code, export_registros_excel, export_asistentes_excel, export_reporte_general
from datetime import datetime
from sqlalchemy import text, func
import tempfile
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-development')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qr_asistencia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# Crear tablas de base de datos y charlas predefinidas
with app.app_context():
    db.create_all()
    
    # Crear charlas predefinidas si no existen
    if Charla.query.count() == 0:
        charlas_predefinidas = [
            {"nombre": "Charla de Olympus", "descripcion": "Información sobre equipos Olympus"},
            {"nombre": "Charla de Sartorius", "descripcion": "Presentación de tecnologías Sartorius"},
            {"nombre": "Charla de Velp", "descripcion": "Novedades de productos Velp"}
        ]
        
        for charla_info in charlas_predefinidas:
            charla = Charla(
                nombre=charla_info["nombre"],
                descripcion=charla_info["descripcion"],
                fecha=datetime.now() # Puedes ajustar esto según necesites
            )
            db.session.add(charla)
        
        db.session.commit()
        print("Charlas predefinidas creadas correctamente")

# Proporcionar la variable 'now' a todas las plantillas
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route("/")
def home():
    # Pasar las charlas a la página principal
    charlas = Charla.query.all()
    return render_template("home.html", charlas=charlas)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/dashboard")
def dashboard():
    asistentes = Asistente.query.all()
    return render_template("dashboard.html", asistentes=asistentes)

@app.route("/register", methods=["GET", "POST"])
def register():
    # Obtener todas las charlas para mostrarlas en el formulario
    charlas_disponibles = Charla.query.all()
    
    if request.method == "POST":
        # Get form data
        nombres = request.form.get('nombres')
        empresa = request.form.get('empresa')
        cargo = request.form.get('cargo')
        correo = request.form.get('correo')
        numero = request.form.get('numero')
        dni = request.form.get('dni')
        charlas_seleccionadas = request.form.getlist('charlas')  # Obtener múltiples valores
        
        # Validate required fields
        if not all([nombres, empresa, correo, dni]):
            flash('Por favor complete todos los campos obligatorios', 'error')
            return redirect(url_for('register'))
        
        # Check if asistente already exists
        existing_user = Asistente.query.filter_by(dni=dni).first()
        if existing_user:
            flash('Ya existe un asistente registrado con este DNI', 'error')
            return redirect(url_for('register'))
        
        # Create new asistente
        asistente = Asistente(
            nombres=nombres,
            empresa=empresa,
            cargo=cargo,
            correo=correo,
            numero=numero,
            dni=dni,
            charlas=",".join(charlas_seleccionadas) if charlas_seleccionadas else ""
        )
        
        # Save to database
        db.session.add(asistente)
        db.session.commit()
        
        # Asociar asistente con las charlas seleccionadas en la tabla de asociación
        if charlas_seleccionadas:
            for charla_id in charlas_seleccionadas:
                charla = Charla.query.get(charla_id)
                if charla:
                    charla.asistentes.append(asistente)
        
        db.session.commit()
        
        # Generar un código QR más pequeño con las 3 primeras letras de cada campo
        # y agregando "01" al final
        nombre_corto = nombres[:3] if nombres else "NNN"
        empresa_corta = empresa[:3] if empresa else "EEE"
        dni_corto = dni[:3] if dni else "DDD"
        cargo_corto = cargo[:3] if cargo else "CCC"
        numero_corto = numero[:3] if numero else "000"
        
        # Crear un string compacto para el QR en lugar de JSON
        qr_data = f"{nombre_corto}{empresa_corta}{dni_corto}{cargo_corto}{numero_corto}01"
        qr_path = generate_qr_code(qr_data, asistente.id)
        
        # Update asistente with QR code path
        asistente.codigoQR = qr_path
        db.session.commit()
        
        flash('Asistente registrado correctamente', 'success')
        return redirect(url_for('view_qr', id=asistente.id))
    
    return render_template("register.html", charlas=charlas_disponibles)

@app.route("/qr/<int:id>")
def view_qr(id):
    asistente = Asistente.query.get_or_404(id)
    return render_template("view_qr.html", asistente=asistente)

@app.route("/confirmar-asistencia")
def confirmar_asistencia():
    # Obtenemos todas las charlas disponibles para mostrarlas en la interfaz del escáner QR
    charlas = Charla.query.all()
    return render_template("confirmar_asistencia.html", charlas=charlas)

@app.route("/asistente-info")
def asistente_info():
    """
    Página que muestra la información completa del asistente
    después de escanear su código QR. Además, registra automáticamente
    la asistencia general al evento.
    
    Si la solicitud es AJAX, devuelve solo el fragmento HTML con la información
    del asistente para insertarlo en la página principal.
    """
    codigo_qr = request.args.get('codigo')
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not codigo_qr:
        if es_ajax:
            return "<div class='alert alert-danger'>No se proporcionó un código QR</div>"
        return render_template("asistente_info.html", 
                              asistente=None, 
                              error_message="No se proporcionó un código QR")
    
    try:
        # Verificar si el formato del código es válido
        if len(codigo_qr) < 17:  # Debería tener al menos 17 caracteres
            if es_ajax:
                return "<div class='alert alert-danger'>Formato de código QR inválido</div>"
            return render_template("asistente_info.html", 
                                  asistente=None, 
                                  error_message="Formato de código QR inválido")
        
        # Extraer los fragmentos de los campos
        nombre_frag = codigo_qr[:3]
        empresa_frag = codigo_qr[3:6]
        dni_frag = codigo_qr[6:9]
        cargo_frag = codigo_qr[9:12]
        numero_frag = codigo_qr[12:15]
        
        # Buscar el asistente usando los fragmentos del código
        asistentes_posibles = Asistente.query.filter(
            Asistente.nombres.like(f"{nombre_frag}%"),
            Asistente.empresa.like(f"{empresa_frag}%"),
            Asistente.dni.like(f"{dni_frag}%")
        ).all()
        
        # Si encontramos múltiples coincidencias, intentamos refinar con el cargo y número
        if len(asistentes_posibles) > 1:
            asistentes_posibles = [a for a in asistentes_posibles if 
                                 (not a.cargo or a.cargo.startswith(cargo_frag)) and
                                 (not a.numero or a.numero.startswith(numero_frag))]
        
        # Si no encontramos asistente con esos criterios
        if not asistentes_posibles:
            error_msg = "No se encontró ningún asistente con este código QR"
            if es_ajax:
                return f"<div class='alert alert-danger'>{error_msg}</div>"
            return render_template("asistente_info.html", 
                                  asistente=None, 
                                  error_message=error_msg)
        
        # Tomar el primer asistente que coincide
        asistente = asistentes_posibles[0]
        
        # Obtener las charlas a las que está registrado
        charlas_asistente = get_charlas_asistente(asistente)
        
        # Verificar si el asistente ya ha registrado su asistencia general
        ya_registrado = asistente.asistencia_confirmada
        mensaje_registro = "Este QR ya fue registrado anteriormente"
        
        # Si no está ya registrado, registrar la asistencia
        if not ya_registrado:
            asistente.asistencia_confirmada = True
            asistente.fecha_asistencia = datetime.now()
            db.session.commit()
        
        if es_ajax:
            # Si es AJAX, devuelve un fragmento HTML
            html_fragment = f"""
            <div class="text-center mb-3">
                {"<div class='alert alert-warning'><strong>¡Atención!</strong> " + mensaje_registro + "</div>" 
                 if ya_registrado else 
                 "<div class='alert alert-success'><strong>¡Asistencia confirmada!</strong> Registro exitoso.</div>"}
                
                {"<p class='text-muted small'>Hora de registro: " + asistente.fecha_asistencia.strftime('%d/%m/%Y %H:%M:%S') + "</p>"
                 if asistente.fecha_asistencia else ""}
            </div>
            
            <h4>{asistente.nombres}</h4>
            <hr>
            
            <div class="mb-2"><strong>Empresa:</strong> {asistente.empresa}</div>
            <div class="mb-2"><strong>DNI:</strong> {asistente.dni}</div>
            <div class="mb-2"><strong>Cargo:</strong> {asistente.cargo or 'No especificado'}</div>
            <div class="mb-2"><strong>Correo:</strong> {asistente.correo}</div>
            <div class="mb-2"><strong>Teléfono:</strong> {asistente.numero or 'No especificado'}</div>
            
            <div class="mt-3">
                <h5>Charlas registradas:</h5>
                {"".join([
                    f"<div class='list-group-item mb-1'><strong>{charla['nombre']}</strong></div>"
                    for charla in charlas_asistente
                ]) if charlas_asistente else "<p class='text-muted'>No hay charlas registradas para este asistente.</p>"}
            </div>
            """
            return html_fragment
        else:
            # Si no es AJAX, renderizar la plantilla completa
            return render_template("asistente_info.html", 
                                asistente=asistente,
                                charlas=charlas_asistente,
                                ya_registrado=ya_registrado,
                                mensaje_registro=mensaje_registro)
    
    except Exception as e:
        print(f"Error al procesar código QR: {str(e)}")
        error_msg = f"Error al procesar código QR: {str(e)}"
        if es_ajax:
            return f"<div class='alert alert-danger'>{error_msg}</div>"
        return render_template("asistente_info.html", 
                              asistente=None, 
                              error_message=error_msg)

# Función auxiliar para obtener las charlas de un asistente
def get_charlas_asistente(asistente):
    charlas_asistente = []
    for charla in asistente.charlas_rel.all():
        charlas_asistente.append({
            'id': charla.id,
            'nombre': charla.nombre,
            'descripcion': charla.descripcion,
            'fecha': charla.fecha
        })
    return charlas_asistente

@app.route("/procesar-qr", methods=["POST"])
def procesar_qr():
    """
    Procesa un código QR escaneado y devuelve la información del asistente
    junto con las charlas a las que está registrado.
    
    El formato del código QR es: [3 letras nombre][3 letras empresa][3 letras DNI][3 letras cargo][3 letras número]01
    """
    data = request.get_json()
    
    if not data or 'codigo' not in data:
        return jsonify({'success': False, 'message': 'Código QR no proporcionado'})
    
    codigo_qr = data['codigo']
    
    # Verificar si el formato del código es válido
    if len(codigo_qr) < 17:  # Debería tener al menos 17 caracteres (5 campos * 3 caracteres + "01")
        return jsonify({'success': False, 'message': 'Formato de código QR inválido'})
    
    try:
        # Extraer los fragmentos de los campos
        nombre_frag = codigo_qr[:3]
        empresa_frag = codigo_qr[3:6]
        dni_frag = codigo_qr[6:9]
        cargo_frag = codigo_qr[9:12]
        numero_frag = codigo_qr[12:15]
        
        # Intentar buscar el asistente usando los fragmentos del código
        # Usamos LIKE para hacer una búsqueda aproximada, ya que solo tenemos los primeros 3 caracteres
        asistentes_posibles = Asistente.query.filter(
            Asistente.nombres.like(f"{nombre_frag}%"),
            Asistente.empresa.like(f"{empresa_frag}%"),
            Asistente.dni.like(f"{dni_frag}%")
        ).all()
        
        # Si encontramos múltiples coincidencias, intentamos refinar con el cargo y número
        if len(asistentes_posibles) > 1:
            asistentes_posibles = [a for a in asistentes_posibles if 
                                   (not a.cargo or a.cargo.startswith(cargo_frag)) and
                                   (not a.numero or a.numero.startswith(numero_frag))]
        
        # Si no encontramos asistente con esos criterios
        if not asistentes_posibles:
            return jsonify({
                'success': False, 
                'message': 'No se encontró ningún asistente con este código QR'
            })
        
        # Tomar el primer asistente que coincide
        asistente = asistentes_posibles[0]
        
        # Obtener las charlas a las que está registrado
        charlas_asistente = []
        for charla in asistente.charlas_rel.all():
            charlas_asistente.append({
                'id': charla.id,
                'nombre': charla.nombre,
                'descripcion': charla.descripcion,
                'fecha': charla.fecha.strftime('%d/%m/%Y %H:%M') if charla.fecha else None
            })
        
        # Devolver la información del asistente y sus charlas
        return jsonify({
            'success': True,
            'asistente': asistente.to_dict(),
            'charlas': charlas_asistente
        })
    
    except Exception as e:
        print(f"Error al procesar código QR: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error al procesar código QR: {str(e)}'
        })

@app.route("/charla/<int:id>")
def ver_charla(id):
    # Obtenemos la charla específica
    charla = Charla.query.get_or_404(id)
    
    # Verificar si se solicita la vista de registros
    if request.args.get('view') == 'registros':
        # Obtener información de asistencias para mostrar el estado de cada asistente
        asistencias = db.session.execute(
            text(f"SELECT asistente_id, charla_id, asistio, fecha_confirmacion FROM asistente_charla "
                f"WHERE charla_id = {id}")
        ).fetchall()
        
        # Mostrar la plantilla de registros
        return render_template("registros_charla.html", charla=charla, asistencias=asistencias)
    
    # Por defecto, mostrar la página principal con el escáner QR
    return render_template("ver_charla.html", charla=charla)

@app.route("/confirmar/<int:charla_id>/<int:asistente_id>", methods=["POST"])
def confirmar_asistente(charla_id, asistente_id):
    # Confirmar la asistencia de un participante a una charla
    charla = Charla.query.get_or_404(charla_id)
    asistente = Asistente.query.get_or_404(asistente_id)
    
    # Verificamos si el asistente ya está asociado con la charla
    # Si no lo está, lo asociamos ahora
    if asistente not in charla.asistentes:
        charla.asistentes.append(asistente)
    
    # Actualizamos la relación para marcar la asistencia como confirmada
    # Esto lo haremos directamente en la base de datos ya que SQLAlchemy no maneja
    # fácilmente los atributos de tablas asociativas
    db.session.execute(
        text(f"UPDATE asistente_charla SET asistio = 1, fecha_confirmacion = '{datetime.now()}' "
             f"WHERE asistente_id = {asistente_id} AND charla_id = {charla_id}")
    )
    db.session.commit()
    
    flash(f'Asistencia de {asistente.nombres} confirmada para {charla.nombre}', 'success')
    return redirect(url_for('ver_charla', id=charla_id))

@app.route("/charla-asistencia/<int:id>")
def charla_asistencia(id):
    """
    Página para confirmar la asistencia a una charla específica.
    Muestra un lector QR para escanear los códigos de los asistentes.
    """
    # Obtener la charla
    charla = Charla.query.get_or_404(id)
    return render_template("charla_asistencia.html", charla=charla)

@app.route("/confirmar-charla/<int:charla_id>", methods=["POST"])
def confirmar_charla(charla_id):
    """
    Confirma la asistencia de un asistente a una charla específica.
    Recibe el código QR del asistente y lo procesa.
    """
    data = request.get_json()
    if not data or 'codigo' not in data:
        return jsonify({'success': False, 'message': 'Código QR no proporcionado'})
    
    codigo_qr = data['codigo']
    
    # Verificar si el formato del código es válido
    if len(codigo_qr) < 17:  # Debería tener al menos 17 caracteres
        return jsonify({'success': False, 'message': 'Formato de código QR inválido'})
    
    try:
        # Extraer los fragmentos de los campos
        nombre_frag = codigo_qr[:3]
        empresa_frag = codigo_qr[3:6]
        dni_frag = codigo_qr[6:9]
        cargo_frag = codigo_qr[9:12]
        numero_frag = codigo_qr[12:15]
        
        # Buscar el asistente usando los fragmentos del código
        asistentes_posibles = Asistente.query.filter(
            Asistente.nombres.like(f"{nombre_frag}%"),
            Asistente.empresa.like(f"{empresa_frag}%"),
            Asistente.dni.like(f"{dni_frag}%")
        ).all()
        
        # Refinar búsqueda si hay múltiples coincidencias
        if len(asistentes_posibles) > 1:
            asistentes_posibles = [a for a in asistentes_posibles if 
                                 (not a.cargo or a.cargo.startswith(cargo_frag)) and
                                 (not a.numero or a.numero.startswith(numero_frag))]
        
        # Si no encontramos asistente con esos criterios
        if not asistentes_posibles:
            return jsonify({
                'success': False, 
                'message': 'No se encontró ningún asistente con este código QR'
            })
        
        # Tomar el primer asistente que coincide
        asistente = asistentes_posibles[0]
        charla = Charla.query.get_or_404(charla_id)
        
        # Verificar si el asistente está registrado para esta charla
        if charla not in [c for c in asistente.charlas_rel]:
            return jsonify({
                'success': False,
                'message': f"El asistente {asistente.nombres} no está registrado para la charla {charla.nombre}"
            })
        
        # Verificar si el asistente ya ha registrado asistencia a esta charla
        asistencia = db.session.execute(
            text(f"SELECT asistio FROM asistente_charla "
                f"WHERE asistente_id = {asistente.id} AND charla_id = {charla.id}")
        ).fetchone()
        
        if asistencia and asistencia.asistio:
            return jsonify({
                'success': False,
                'message': f"El asistente {asistente.nombres} ya registró su asistencia a esta charla"
            })
        
        # Confirmar la asistencia del asistente a la charla
        db.session.execute(
            text(f"UPDATE asistente_charla SET asistio = 1, fecha_confirmacion = '{datetime.now()}' "
                f"WHERE asistente_id = {asistente.id} AND charla_id = {charla.id}")
        )
        db.session.commit()
        
        return jsonify({
            'success': True,
            'asistente': asistente.to_dict(),
            'charla': {
                'id': charla.id,
                'nombre': charla.nombre,
                'descripcion': charla.descripcion
            }
        })
        
    except Exception as e:
        print(f"Error al procesar código QR para charla: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error al procesar código QR: {str(e)}'
        })

@app.route("/admin")
def admin():
    """Página de administración del sistema"""
    # Calcular estadísticas para el dashboard
    charlas_total = Charla.query.count()
    asistentes_total = Asistente.query.count()
    
    # Contar asistencias confirmadas (asistentes que han marcado asistencia general)
    asistentes_confirmados = Asistente.query.filter(Asistente.asistencia_confirmada == True).count()
    
    # Contar el total de asistencias a charlas confirmadas
    asistencias_charlas = db.session.execute(
        text("SELECT COUNT(*) as total FROM asistente_charla WHERE asistio = 1")
    ).fetchone()[0]
    
    return render_template("admin/index.html", 
                          charlas_total=charlas_total,
                          asistentes_total=asistentes_total,
                          asistentes_confirmados=asistentes_confirmados,
                          asistencias_total=asistencias_charlas)

@app.route("/admin/charlas")
def admin_charlas():
    """Administración de charlas"""
    charlas = Charla.query.all()
    return render_template("admin/charlas.html", charlas=charlas)

@app.route("/admin/charlas/nueva", methods=["GET", "POST"])
def nueva_charla():
    """Crear una nueva charla"""
    if request.method == "POST":
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        fecha_str = request.form.get('fecha')
        
        if not nombre:
            flash('El nombre de la charla es obligatorio', 'danger')
            return redirect(url_for('nueva_charla'))
        
        # Crear objeto de fecha si se proporciona
        fecha = None
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Formato de fecha inválido', 'danger')
                return redirect(url_for('nueva_charla'))
        
        # Crear la charla
        charla = Charla(
            nombre=nombre,
            descripcion=descripcion,
            fecha=fecha
        )
        
        db.session.add(charla)
        db.session.commit()
        
        flash(f'Charla "{nombre}" creada exitosamente', 'success')
        return redirect(url_for('admin_charlas'))
    
    return render_template("admin/nueva_charla.html")

@app.route("/admin/charlas/editar/<int:id>", methods=["GET", "POST"])
def editar_charla(id):
    """Editar una charla existente"""
    charla = Charla.query.get_or_404(id)
    
    if request.method == "POST":
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        fecha_str = request.form.get('fecha')
        
        if not nombre:
            flash('El nombre de la charla es obligatorio', 'danger')
            return redirect(url_for('editar_charla', id=id))
        
        # Actualizar campos
        charla.nombre = nombre
        charla.descripcion = descripcion
        
        # Actualizar fecha si se proporciona
        if fecha_str:
            try:
                charla.fecha = datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Formato de fecha inválido', 'danger')
                return redirect(url_for('editar_charla', id=id))
        
        db.session.commit()
        flash(f'Charla "{nombre}" actualizada exitosamente', 'success')
        return redirect(url_for('admin_charlas'))
    
    # Formato de fecha para formulario HTML
    fecha_form = charla.fecha.strftime('%Y-%m-%dT%H:%M') if charla.fecha else ""
    
    return render_template("admin/editar_charla.html", charla=charla, fecha_form=fecha_form)

@app.route("/admin/charlas/eliminar/<int:id>", methods=["POST"])
def eliminar_charla(id):
    """Eliminar una charla"""
    charla = Charla.query.get_or_404(id)
    nombre = charla.nombre
    
    # Eliminar las asociaciones con asistentes
    db.session.execute(text(f"DELETE FROM asistente_charla WHERE charla_id = {id}"))
    
    # Eliminar la charla
    db.session.delete(charla)
    db.session.commit()
    
    flash(f'Charla "{nombre}" eliminada exitosamente', 'success')
    return redirect(url_for('admin_charlas'))

@app.route("/admin/export_registros")
def export_registros():
    """Exportar todos los registros de asistentes a Excel"""
    try:
        # Obtener todos los asistentes
        asistentes = Asistente.query.all()
        
        # Generar el archivo Excel
        temp_path = export_registros_excel(asistentes)
        
        # Generar nombre de archivo con fecha actual
        filename = f"registros_asistentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Enviar el archivo al usuario
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        flash(f'Error al exportar registros: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route("/admin/export_asistentes")
def export_asistentes():
    """Exportar asistentes confirmados a Excel con hojas separadas por charla"""
    try:
        # Obtener asistentes que confirmaron su asistencia general
        asistentes = Asistente.query.filter(Asistente.asistencia_confirmada == True).all()
        
        # Obtener todas las charlas
        charlas = Charla.query.all()
        
        # Para cada charla, obtener los asistentes que confirmaron asistencia específica
        asistencia_por_charla = {}
        for charla in charlas:
            # Consultar directamente la tabla asistente_charla para esta charla
            # y obtener los IDs de asistentes con asistio=1
            asistencia_records = db.session.execute(
                text(f"""
                    SELECT asistente_id 
                    FROM asistente_charla 
                    WHERE charla_id = {charla.id} AND asistio = 1
                """)
            ).fetchall()
            
            # Guardar la lista de IDs de asistentes que confirmaron asistencia a esta charla
            asistencia_por_charla[charla.id] = [record[0] for record in asistencia_records]
        
        # Generar el archivo Excel con la información correcta
        temp_path = export_asistentes_excel(asistentes, charlas, asistencia_por_charla)
        
        # Generar nombre de archivo con fecha actual
        filename = f"asistentes_confirmados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Enviar el archivo al usuario
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        flash(f'Error al exportar asistentes: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route("/admin/export_reporte")
def export_reporte():
    """Exportar reporte general con estadísticas"""
    try:
        # Obtener datos para el reporte
        asistentes_total = Asistente.query.count()
        asistentes_confirmados = Asistente.query.filter(Asistente.asistencia_confirmada == True).count()
        charlas = Charla.query.all()
        
        # Estadísticas adicionales
        asistencia_charlas = {}
        for charla in charlas:
            asistentes_charla = db.session.execute(
                text(f"SELECT COUNT(*) as total FROM asistente_charla "
                    f"WHERE charla_id = {charla.id} AND asistio = 1")
            ).fetchone()[0]
            asistencia_charlas[charla.id] = {
                'nombre': charla.nombre,
                'total_registrados': len(charla.asistentes),
                'total_asistieron': asistentes_charla,
            }
        
        # Generar el archivo Excel
        temp_path = export_reporte_general(asistentes_total, asistentes_confirmados, asistencia_charlas, charlas)
        
        # Generar nombre de archivo con fecha actual
        filename = f"reporte_general_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Enviar el archivo al usuario
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    except Exception as e:
        flash(f'Error al exportar reporte: {str(e)}', 'danger')
        return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(debug=True)