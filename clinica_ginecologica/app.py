"""
Sistema de Gestión de Pacientes Ginecológicos
Aplicación principal Flask
"""
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func
from models import db, Paciente, Medico, Cita, HistorialMedico, Recordatorio, TipoConsulta, init_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-cambiar-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinica_ginecologica.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return Paciente.query.get(int(user_id))


# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.route('/')
def index():
    """Página de inicio"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        paciente = Paciente.query.filter_by(email=email).first()
        
        if paciente and paciente.check_password(password):
            login_user(paciente, remember=True)
            flash('¡Bienvenida! Has iniciado sesión correctamente.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')
    
    return render_template('login.html')


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """Registro de nuevo paciente"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Verificar si el email ya existe
        if Paciente.query.filter_by(email=request.form.get('email')).first():
            flash('Este email ya está registrado.', 'danger')
            return redirect(url_for('registro'))
        
        # Verificar si la cédula ya existe
        if Paciente.query.filter_by(cedula=request.form.get('cedula')).first():
            flash('Esta cédula ya está registrada.', 'danger')
            return redirect(url_for('registro'))
        
        # Crear nuevo paciente
        paciente = Paciente(
            email=request.form.get('email'),
            nombres=request.form.get('nombres'),
            apellidos=request.form.get('apellidos'),
            cedula=request.form.get('cedula'),
            fecha_nacimiento=datetime.strptime(request.form.get('fecha_nacimiento'), '%Y-%m-%d'),
            telefono=request.form.get('telefono'),
            direccion=request.form.get('direccion')
        )
        paciente.set_password(request.form.get('password'))
        
        db.session.add(paciente)
        db.session.commit()
        
        flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    
    return render_template('registro.html')


@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('index'))


# ==================== DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """Panel principal del paciente"""
    # Próximas citas
    proximas_citas = Cita.query.filter(
        Cita.paciente_id == current_user.id,
        Cita.fecha_hora >= datetime.now(),
        Cita.estado.in_(['pendiente', 'confirmada'])
    ).order_by(Cita.fecha_hora).limit(5).all()
    
    # Recordatorios activos
    recordatorios = Recordatorio.query.filter(
        Recordatorio.paciente_id == current_user.id,
        Recordatorio.estado == 'activo',
        Recordatorio.fecha_recordatorio >= datetime.now()
    ).order_by(Recordatorio.fecha_recordatorio).limit(5).all()
    
    # Últimas consultas
    ultimas_consultas = HistorialMedico.query.filter(
        HistorialMedico.paciente_id == current_user.id
    ).order_by(HistorialMedico.fecha_consulta.desc()).limit(3).all()
    
    return render_template('dashboard.html',
                         proximas_citas=proximas_citas,
                         recordatorios=recordatorios,
                         ultimas_consultas=ultimas_consultas)


# ==================== PERFIL Y FICHA ====================

@app.route('/mi-perfil')
@login_required
def mi_perfil():
    """Ver perfil del paciente"""
    return render_template('perfil.html', paciente=current_user)


@app.route('/mi-perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    """Editar perfil del paciente"""
    if request.method == 'POST':
        current_user.telefono = request.form.get('telefono')
        current_user.direccion = request.form.get('direccion')
        current_user.tipo_sangre = request.form.get('tipo_sangre')
        current_user.alergias = request.form.get('alergias')
        current_user.antecedentes_familiares = request.form.get('antecedentes_familiares')
        
        # Datos ginecológicos
        fum = request.form.get('fecha_ultima_menstruacion')
        if fum:
            current_user.fecha_ultima_menstruacion = datetime.strptime(fum, '%Y-%m-%d')
        
        current_user.embarazos_previos = request.form.get('embarazos_previos', 0, type=int)
        current_user.partos = request.form.get('partos', 0, type=int)
        current_user.cesareas = request.form.get('cesareas', 0, type=int)
        current_user.abortos = request.form.get('abortos', 0, type=int)
        current_user.metodo_anticonceptivo = request.form.get('metodo_anticonceptivo')
        
        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('mi_perfil'))
    
    return render_template('editar_perfil.html', paciente=current_user)


# ==================== GESTIÓN DE CITAS ====================

@app.route('/citas')
@login_required
def mis_citas():
    """Ver todas las citas del paciente"""
    filtro = request.args.get('filtro', 'proximas')
    
    if filtro == 'proximas':
        citas = Cita.query.filter(
            Cita.paciente_id == current_user.id,
            Cita.fecha_hora >= datetime.now()
        ).order_by(Cita.fecha_hora).all()
    elif filtro == 'pasadas':
        citas = Cita.query.filter(
            Cita.paciente_id == current_user.id,
            Cita.fecha_hora < datetime.now()
        ).order_by(Cita.fecha_hora.desc()).all()
    else:  # todas
        citas = Cita.query.filter(
            Cita.paciente_id == current_user.id
        ).order_by(Cita.fecha_hora.desc()).all()
    
    return render_template('citas.html', citas=citas, filtro=filtro)


@app.route('/citas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_cita():
    """Agendar nueva cita"""
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        fecha_hora = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
        
        # Verificar que la fecha sea futura
        if fecha_hora <= datetime.now():
            flash('La fecha de la cita debe ser futura.', 'danger')
            return redirect(url_for('nueva_cita'))
        
        cita = Cita(
            paciente_id=current_user.id,
            medico_id=request.form.get('medico_id', type=int),
            fecha_hora=fecha_hora,
            tipo_consulta=request.form.get('tipo_consulta'),
            motivo=request.form.get('motivo'),
            estado='pendiente'
        )
        
        db.session.add(cita)
        
        # Crear recordatorio automático (1 día antes)
        recordatorio = Recordatorio(
            paciente_id=current_user.id,
            tipo='cita',
            titulo=f'Recordatorio: Cita de {cita.tipo_consulta}',
            descripcion=f'Tienes una cita mañana a las {hora}',
            fecha_recordatorio=fecha_hora - timedelta(days=1)
        )
        db.session.add(recordatorio)
        
        db.session.commit()
        flash('Cita agendada correctamente.', 'success')
        return redirect(url_for('mis_citas'))
    
    medicos = Medico.query.filter_by(activo=True).all()
    tipos_consulta = TipoConsulta.query.filter_by(activo=True).all()
    
    return render_template('nueva_cita.html', medicos=medicos, tipos_consulta=tipos_consulta)


@app.route('/citas/<int:cita_id>')
@login_required
def ver_cita(cita_id):
    """Ver detalle de una cita"""
    cita = Cita.query.get_or_404(cita_id)
    if cita.paciente_id != current_user.id:
        flash('No tienes permiso para ver esta cita.', 'danger')
        return redirect(url_for('mis_citas'))
    
    return render_template('ver_cita.html', cita=cita)


@app.route('/citas/<int:cita_id>/cancelar', methods=['POST'])
@login_required
def cancelar_cita(cita_id):
    """Cancelar una cita"""
    cita = Cita.query.get_or_404(cita_id)
    if cita.paciente_id != current_user.id:
        flash('No tienes permiso para cancelar esta cita.', 'danger')
        return redirect(url_for('mis_citas'))
    
    if cita.estado in ['completada', 'cancelada']:
        flash('Esta cita no puede ser cancelada.', 'warning')
        return redirect(url_for('mis_citas'))
    
    cita.estado = 'cancelada'
    db.session.commit()
    flash('Cita cancelada correctamente.', 'success')
    return redirect(url_for('mis_citas'))


# ==================== HISTORIAL MÉDICO ====================

@app.route('/historial')
@login_required
def historial_medico():
    """Ver historial médico"""
    historiales = HistorialMedico.query.filter(
        HistorialMedico.paciente_id == current_user.id
    ).order_by(HistorialMedico.fecha_consulta.desc()).all()
    
    return render_template('historial.html', historiales=historiales)


@app.route('/historial/<int:historial_id>')
@login_required
def ver_historial(historial_id):
    """Ver detalle de una consulta en el historial"""
    historial = HistorialMedico.query.get_or_404(historial_id)
    if historial.paciente_id != current_user.id:
        flash('No tienes permiso para ver este registro.', 'danger')
        return redirect(url_for('historial_medico'))
    
    return render_template('ver_historial.html', historial=historial)


# ==================== RECORDATORIOS ====================

@app.route('/recordatorios')
@login_required
def mis_recordatorios():
    """Ver recordatorios"""
    recordatorios = Recordatorio.query.filter(
        Recordatorio.paciente_id == current_user.id
    ).order_by(Recordatorio.fecha_recordatorio.desc()).all()
    
    return render_template('recordatorios.html', recordatorios=recordatorios)


@app.route('/recordatorios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_recordatorio():
    """Crear nuevo recordatorio"""
    if request.method == 'POST':
        fecha = request.form.get('fecha')
        hora = request.form.get('hora', '09:00')
        fecha_recordatorio = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
        
        recordatorio = Recordatorio(
            paciente_id=current_user.id,
            tipo=request.form.get('tipo'),
            titulo=request.form.get('titulo'),
            descripcion=request.form.get('descripcion'),
            fecha_recordatorio=fecha_recordatorio
        )
        
        db.session.add(recordatorio)
        db.session.commit()
        flash('Recordatorio creado correctamente.', 'success')
        return redirect(url_for('mis_recordatorios'))
    
    return render_template('nuevo_recordatorio.html')


@app.route('/recordatorios/<int:recordatorio_id>/completar', methods=['POST'])
@login_required
def completar_recordatorio(recordatorio_id):
    """Marcar recordatorio como completado"""
    recordatorio = Recordatorio.query.get_or_404(recordatorio_id)
    if recordatorio.paciente_id != current_user.id:
        flash('No tienes permiso para modificar este recordatorio.', 'danger')
        return redirect(url_for('mis_recordatorios'))
    
    recordatorio.estado = 'completado'
    db.session.commit()
    flash('Recordatorio marcado como completado.', 'success')
    return redirect(url_for('mis_recordatorios'))


# ==================== REPORTES Y ESTADÍSTICAS ====================

@app.route('/reportes')
@login_required
def reportes():
    """Ver reportes y estadísticas"""
    # Total de citas
    total_citas = Cita.query.filter_by(paciente_id=current_user.id).count()
    
    # Citas por estado
    citas_pendientes = Cita.query.filter_by(paciente_id=current_user.id, estado='pendiente').count()
    citas_completadas = Cita.query.filter_by(paciente_id=current_user.id, estado='completada').count()
    citas_canceladas = Cita.query.filter_by(paciente_id=current_user.id, estado='cancelada').count()
    
    # Citas por tipo de consulta
    citas_por_tipo = db.session.query(
        Cita.tipo_consulta,
        func.count(Cita.id)
    ).filter(
        Cita.paciente_id == current_user.id
    ).group_by(Cita.tipo_consulta).all()
    
    # Historial por año
    consultas_por_año = db.session.query(
        func.strftime('%Y', HistorialMedico.fecha_consulta),
        func.count(HistorialMedico.id)
    ).filter(
        HistorialMedico.paciente_id == current_user.id
    ).group_by(func.strftime('%Y', HistorialMedico.fecha_consulta)).all()
    
    return render_template('reportes.html',
                         total_citas=total_citas,
                         citas_pendientes=citas_pendientes,
                         citas_completadas=citas_completadas,
                         citas_canceladas=citas_canceladas,
                         citas_por_tipo=citas_por_tipo,
                         consultas_por_año=consultas_por_año)


# ==================== API ENDPOINTS ====================

@app.route('/api/horarios-disponibles')
@login_required
def horarios_disponibles():
    """Obtener horarios disponibles para una fecha y médico"""
    fecha = request.args.get('fecha')
    medico_id = request.args.get('medico_id', type=int)
    
    if not fecha or not medico_id:
        return jsonify({'error': 'Parámetros faltantes'}), 400
    
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    
    # Horarios de trabajo (8:00 - 18:00)
    horarios_trabajo = []
    for hora in range(8, 18):
        for minuto in [0, 30]:
            horarios_trabajo.append(f"{hora:02d}:{minuto:02d}")
    
    # Citas ya agendadas ese día
    citas_dia = Cita.query.filter(
        Cita.medico_id == medico_id,
        func.date(Cita.fecha_hora) == fecha_obj.date(),
        Cita.estado.in_(['pendiente', 'confirmada'])
    ).all()
    
    horas_ocupadas = [cita.fecha_hora.strftime('%H:%M') for cita in citas_dia]
    
    # Filtrar horarios disponibles
    horarios_disponibles = [h for h in horarios_trabajo if h not in horas_ocupadas]
    
    return jsonify({'horarios': horarios_disponibles})


# ==================== MANEJO DE ERRORES ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('500.html'), 500


# ==================== INICIALIZACIÓN ====================

if __name__ == '__main__':
    init_db(app)
    app.run(debug=True, port=5000)
