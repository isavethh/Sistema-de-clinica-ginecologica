"""
Modelos de la base de datos para el Sistema de Gestión de Pacientes Ginecológicos
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Paciente(UserMixin, db.Model):
    """Modelo para pacientes"""
    __tablename__ = 'pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    # Datos de acceso
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Datos personales
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    
    # Datos médicos generales
    tipo_sangre = db.Column(db.String(5))
    alergias = db.Column(db.Text)
    antecedentes_familiares = db.Column(db.Text)
    
    # Datos ginecológicos específicos
    fecha_ultima_menstruacion = db.Column(db.Date)
    embarazos_previos = db.Column(db.Integer, default=0)
    partos = db.Column(db.Integer, default=0)
    cesareas = db.Column(db.Integer, default=0)
    abortos = db.Column(db.Integer, default=0)
    metodo_anticonceptivo = db.Column(db.String(100))
    
    # Metadatos
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    citas = db.relationship('Cita', backref='paciente', lazy=True)
    historiales = db.relationship('HistorialMedico', backref='paciente', lazy=True)
    recordatorios = db.relationship('Recordatorio', backref='paciente', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"
    
    @property
    def edad(self):
        today = datetime.today()
        return today.year - self.fecha_nacimiento.year - (
            (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )


class Medico(db.Model):
    """Modelo para médicos"""
    __tablename__ = 'medicos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    especialidad = db.Column(db.String(100), default='Ginecología')
    cedula_profesional = db.Column(db.String(50))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    citas = db.relationship('Cita', backref='medico', lazy=True)
    historiales = db.relationship('HistorialMedico', backref='medico', lazy=True)
    
    @property
    def nombre_completo(self):
        return f"Dr(a). {self.nombres} {self.apellidos}"


class Cita(db.Model):
    """Modelo para citas médicas"""
    __tablename__ = 'citas'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    
    fecha_hora = db.Column(db.DateTime, nullable=False)
    tipo_consulta = db.Column(db.String(100), nullable=False)  # Control prenatal, Papanicolau, etc.
    motivo = db.Column(db.Text)
    
    # Estados: pendiente, confirmada, completada, cancelada
    estado = db.Column(db.String(20), default='pendiente')
    
    notas = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_modificacion = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    @property
    def fecha_formateada(self):
        return self.fecha_hora.strftime('%d/%m/%Y')
    
    @property
    def hora_formateada(self):
        return self.fecha_hora.strftime('%H:%M')


class HistorialMedico(db.Model):
    """Modelo para historial médico"""
    __tablename__ = 'historiales_medicos'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=False)
    cita_id = db.Column(db.Integer, db.ForeignKey('citas.id'))
    
    fecha_consulta = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_consulta = db.Column(db.String(100))
    
    # Datos de la consulta
    motivo_consulta = db.Column(db.Text)
    sintomas = db.Column(db.Text)
    exploracion_fisica = db.Column(db.Text)
    diagnostico = db.Column(db.Text)
    tratamiento = db.Column(db.Text)
    
    # Signos vitales
    peso = db.Column(db.Float)
    talla = db.Column(db.Float)
    presion_arterial = db.Column(db.String(20))
    temperatura = db.Column(db.Float)
    
    # Estudios y resultados
    estudios_solicitados = db.Column(db.Text)
    resultados_estudios = db.Column(db.Text)
    
    # Seguimiento
    observaciones = db.Column(db.Text)
    proxima_cita = db.Column(db.Date)
    
    cita = db.relationship('Cita', backref='historial')


class Recordatorio(db.Model):
    """Modelo para recordatorios y notificaciones"""
    __tablename__ = 'recordatorios'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    
    tipo = db.Column(db.String(50), nullable=False)  # cita, medicamento, estudio, control
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_recordatorio = db.Column(db.DateTime, nullable=False)
    
    # Estados: activo, enviado, completado
    estado = db.Column(db.String(20), default='activo')
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)


class TipoConsulta(db.Model):
    """Catálogo de tipos de consulta ginecológica"""
    __tablename__ = 'tipos_consulta'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    duracion_minutos = db.Column(db.Integer, default=30)
    activo = db.Column(db.Boolean, default=True)


def init_db(app):
    """Inicializa la base de datos con datos de prueba"""
    with app.app_context():
        db.create_all()
        
        # Verificar si ya hay datos
        if Medico.query.first() is None:
            # Crear médicos de ejemplo
            medicos = [
                Medico(
                    nombres='María Elena',
                    apellidos='García López',
                    especialidad='Ginecología y Obstetricia',
                    cedula_profesional='12345678',
                    telefono='555-0101',
                    email='dra.garcia@clinica.com'
                ),
                Medico(
                    nombres='Ana Patricia',
                    apellidos='Rodríguez Sánchez',
                    especialidad='Ginecología',
                    cedula_profesional='87654321',
                    telefono='555-0102',
                    email='dra.rodriguez@clinica.com'
                )
            ]
            db.session.add_all(medicos)
            
            # Crear tipos de consulta
            tipos = [
                TipoConsulta(nombre='Consulta General', descripcion='Revisión ginecológica general', duracion_minutos=30),
                TipoConsulta(nombre='Control Prenatal', descripcion='Seguimiento de embarazo', duracion_minutos=45),
                TipoConsulta(nombre='Papanicolau', descripcion='Citología cervical', duracion_minutos=30),
                TipoConsulta(nombre='Ultrasonido', descripcion='Ecografía pélvica o transvaginal', duracion_minutos=40),
                TipoConsulta(nombre='Planificación Familiar', descripcion='Asesoría anticonceptiva', duracion_minutos=30),
                TipoConsulta(nombre='Colposcopía', descripcion='Examen del cuello uterino', duracion_minutos=45),
                TipoConsulta(nombre='Control Post-parto', descripcion='Revisión después del parto', duracion_minutos=30),
                TipoConsulta(nombre='Urgencia', descripcion='Consulta de urgencia', duracion_minutos=60),
            ]
            db.session.add_all(tipos)
            
            db.session.commit()
            print("Base de datos inicializada con datos de ejemplo.")
