# Sistema de Asistencia QR

Sistema web para gestión de asistencia a eventos y charlas mediante códigos QR. Permite registrar participantes, generar códigos QR personalizados, confirmar asistencia mediante escaneo y generar reportes estadísticos.

## Características Principales

- Registro de asistentes con generación automática de códigos QR
- Registro de charlas o actividades dentro del evento
- Confirmación de asistencia general mediante escaneo de códigos QR
- Confirmación de asistencia específica a charlas individuales
- Panel de administración con estadísticas
- Exportación de reportes en Excel (registros, asistentes y estadísticas)

## Requisitos del Sistema

- Python 3.10 o superior
- Flask y dependencias (listadas en requirements.txt)
- SQLite (incluido en Python)
- Navegador web moderno con acceso a cámara (para escaneo de QR)

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/gfxjef/qr_asistencia.git
cd qr_asistencia
```

2. Crear y activar un entorno virtual:
```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En macOS/Linux
python -m venv venv
source venv/bin/activate
```

3. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar la base de datos:
```bash
# Inicializar la base de datos
flask db upgrade

# Si es la primera vez y necesitas crear la estructura desde cero:
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Ejecución

1. Ejecutar la aplicación:
```bash
flask run
```
O con opciones adicionales:
```bash
flask run --host=0.0.0.0 --port=5000
```

2. Acceder a la aplicación:
- Abrir en el navegador: http://localhost:5000

## Uso del Sistema

### 1. Registro de Asistentes
- Acceder a "Registrar Asistente" desde el menú principal
- Completar el formulario con los datos del asistente
- Seleccionar las charlas a las que asistirá
- Al guardar, se generará automáticamente un código QR único

### 2. Confirmación de Asistencia General
- Acceder a "Confirmar Asistencia" desde el menú principal
- Escanear el código QR del asistente con la cámara
- La información del asistente aparecerá en pantalla y su asistencia quedará registrada

### 3. Confirmación de Asistencia a Charlas
- Acceder a la sección "Charlas" y seleccionar la charla específica
- Usar el escáner de QR para registrar la asistencia del participante a esa charla

### 4. Administración
- Acceder al panel de administración desde "Administración" en el menú principal
- Gestionar charlas, asistentes y visualizar estadísticas
- Exportar reportes en Excel:
  - Exportar Registros: Lista completa de asistentes registrados
  - Exportar Asistentes: Asistentes que confirmaron asistencia general y por charlas
  - Reporte General: Estadísticas detalladas con gráficos

## Estructura del Proyecto

- `app.py`: Punto de entrada principal y controladores de la aplicación Flask
- `models.py`: Definición de modelos de datos (Asistentes, Charlas)
- `utils.py`: Funciones auxiliares (generación QR, exportación Excel)
- `templates/`: Plantillas HTML
- `static/`: Archivos estáticos (CSS, imágenes, QR generados)
- `migrations/`: Scripts de migración de la base de datos

## Dependencias Principales

- Flask: Framework web
- Flask-SQLAlchemy: ORM para base de datos
- Flask-Migrate: Gestión de migraciones de base de datos
- qrcode: Generación de códigos QR
- pandas, xlsxwriter: Exportación de reportes Excel
- matplotlib: Generación de gráficos para reportes

## Notas de Desarrollo

- La aplicación utiliza SQLite por defecto para facilitar la instalación
- Para entornos de producción, considere migrar a PostgreSQL o MySQL
- La carpeta `static/qrcodes/` debe tener permisos de escritura para almacenar los códigos QR generados

## Licencia

Este proyecto es de código abierto, disponible bajo la licencia MIT.
