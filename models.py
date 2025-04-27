from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

db = SQLAlchemy()

# Nueva tabla de asociación para la relación muchos a muchos entre Asistente y Charla
asistente_charla = db.Table('asistente_charla',
    db.Column('asistente_id', db.Integer, db.ForeignKey('asistente.id'), primary_key=True),
    db.Column('charla_id', db.Integer, db.ForeignKey('charla.id'), primary_key=True),
    db.Column('asistio', db.Boolean, default=False),
    db.Column('fecha_confirmacion', db.DateTime)
)

class Charla(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    fecha = db.Column(db.DateTime)
    
    # Relación con asistentes a través de la tabla de asociación
    asistentes = db.relationship('Asistente', 
                                secondary=asistente_charla,
                                backref=db.backref('charlas_rel', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Charla {self.nombre}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fecha': self.fecha.isoformat() if self.fecha else None
        }

class Asistente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100), nullable=False)
    empresa = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(100))
    correo = db.Column(db.String(120), unique=True, nullable=False)
    numero = db.Column(db.String(20))
    dni = db.Column(db.String(20), unique=True, nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    charlas = db.Column(db.Text)  # Mantener para compatibilidad con código existente
    codigoQR = db.Column(db.String(255))  # Ruta al archivo de imagen QR
    
    # Nuevos campos para tracking de asistencia general al evento
    asistencia_confirmada = db.Column(db.Boolean, default=False)
    fecha_asistencia = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Asistente {self.nombres}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombres': self.nombres,
            'empresa': self.empresa,
            'cargo': self.cargo,
            'correo': self.correo,
            'numero': self.numero,
            'dni': self.dni,
            'fecha_registro': self.fecha_registro.isoformat(),
            'charlas': self.charlas,
            'codigoQR': self.codigoQR,
            'asistencia_confirmada': self.asistencia_confirmada,
            'fecha_asistencia': self.fecha_asistencia.isoformat() if self.fecha_asistencia else None
        }