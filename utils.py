import qrcode
import os
import tempfile
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime

def generate_qr_code(data, id):
    """
    Generate a QR code with the provided data
    
    Args:
        data (str): Data to encode in QR code
        id (int): ID to use in filename
        
    Returns:
        str: Path to saved QR code image
    """
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    # Add data to QR code
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create an image from the QR Code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Create directory for QR codes if it doesn't exist
    os.makedirs('static/qrcodes', exist_ok=True)
    
    # Generate filename with timestamp to avoid duplicates
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"qr_{id}_{timestamp}.png"
    filepath = os.path.join('static/qrcodes', filename)
    
    # Save QR code image
    img.save(filepath)
    
    return filepath

def export_registros_excel(asistentes):
    """
    Genera un archivo Excel con todos los asistentes registrados
    
    Args:
        asistentes (list): Lista de objetos Asistente
        
    Returns:
        str: Ruta al archivo Excel temporal
    """
    # Crear DataFrame con los datos de todos los asistentes
    data = []
    for asistente in asistentes:
        data.append({
            'ID': asistente.id,
            'Nombres': asistente.nombres,
            'Empresa': asistente.empresa,
            'DNI': asistente.dni,
            'Cargo': asistente.cargo,
            'Correo': asistente.correo,
            'Teléfono': asistente.numero,
            'Fecha Registro': asistente.fecha_registro.strftime('%d/%m/%Y %H:%M') if asistente.fecha_registro else "",
            'Asistencia Confirmada': 'Sí' if asistente.asistencia_confirmada else 'No',
            'Fecha Asistencia': asistente.fecha_asistencia.strftime('%d/%m/%Y %H:%M') if asistente.fecha_asistencia else ""
        })
    
    # Crear DataFrame para exportar a Excel
    df = pd.DataFrame(data)
    
    # Crear archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()
    
    # Exportar a Excel con formato
    with pd.ExcelWriter(temp_file.name, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Registros', index=False)
        
        # Obtener el libro y la hoja
        workbook = writer.book
        worksheet = writer.sheets['Registros']
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Aplicar formato a encabezados
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Auto ajustar columnas
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col) + 2)
            worksheet.set_column(i, i, column_width)
    
    return temp_file.name

def export_asistentes_excel(asistentes, charlas, asistencia_por_charla):
    """
    Genera un archivo Excel con asistentes confirmados,
    con una hoja principal y hojas adicionales para cada charla
    
    Args:
        asistentes (list): Lista de asistentes que confirmaron asistencia general
        charlas (list): Lista de todas las charlas
        asistencia_por_charla (dict): Diccionario con listas de IDs de asistentes que confirmaron
                                     asistencia a cada charla específica
        
    Returns:
        str: Ruta al archivo Excel temporal
    """
    # Crear archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()
    
    # Crear DataFrame para la hoja principal
    data_principal = []
    for asistente in asistentes:
        data_principal.append({
            'ID': asistente.id,
            'Nombres': asistente.nombres,
            'Empresa': asistente.empresa,
            'DNI': asistente.dni,
            'Cargo': asistente.cargo or 'No especificado',
            'Correo': asistente.correo,
            'Teléfono': asistente.numero or 'No especificado',
            'Fecha Asistencia': asistente.fecha_asistencia.strftime('%d/%m/%Y %H:%M') if asistente.fecha_asistencia else ""
        })
    
    # Crear Excel con pandas y xlsxwriter
    with pd.ExcelWriter(temp_file.name, engine='xlsxwriter') as writer:
        # Hoja principal de asistentes generales
        df_principal = pd.DataFrame(data_principal)
        df_principal.to_excel(writer, sheet_name='Asistentes', index=False)
        
        # Formato para hoja principal
        workbook = writer.book
        worksheet = writer.sheets['Asistentes']
        
        # Formato de encabezado
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Aplicar formato a encabezados
        for col_num, value in enumerate(df_principal.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Auto ajustar columnas
        for i, col in enumerate(df_principal.columns):
            column_width = max(df_principal[col].astype(str).map(len).max(), len(col) + 2)
            worksheet.set_column(i, i, column_width)
        
        # Crear una hoja para cada charla
        for charla in charlas:
            # Obtener los IDs de los asistentes que confirmaron asistencia a esta charla específica
            asistentes_ids = asistencia_por_charla.get(charla.id, [])
            
            if not asistentes_ids:
                # Si no hay asistentes confirmados para esta charla, continuar con la siguiente
                continue
            
            # Recolectar los datos de los asistentes que asistieron a esta charla
            asistentes_charla = []
            for asistente in asistentes:
                # Solo incluir si el asistente confirmó asistencia específica a esta charla
                if asistente.id in asistentes_ids:
                    asistentes_charla.append({
                        'ID': asistente.id,
                        'Nombres': asistente.nombres,
                        'Empresa': asistente.empresa,
                        'DNI': asistente.dni,
                        'Cargo': asistente.cargo or 'No especificado',
                        'Correo': asistente.correo,
                        'Teléfono': asistente.numero or 'No especificado'
                    })
            
            # Crear DataFrame para esta charla
            df_charla = pd.DataFrame(asistentes_charla)
            
            # Si hay asistentes, crear la hoja
            if not df_charla.empty:
                # Nombre de la hoja limitado a 31 caracteres (límite de Excel)
                nombre_hoja = f"Charla {charla.id}"
                if len(charla.nombre) <= 25:
                    nombre_hoja = charla.nombre[:25]
                
                df_charla.to_excel(writer, sheet_name=nombre_hoja, index=False)
                
                # Formato para esta hoja
                worksheet_charla = writer.sheets[nombre_hoja]
                
                # Título de la charla
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 14,
                    'align': 'center'
                })
                
                # Insertar fila para título
                worksheet_charla.merge_range('A1:G1', charla.nombre, title_format)
                
                # Descripción de la charla
                desc_format = workbook.add_format({
                    'italic': True,
                    'align': 'center'
                })
                
                # Insertar descripción y fecha
                if charla.descripcion:
                    worksheet_charla.merge_range('A2:G2', charla.descripcion, desc_format)
                
                fecha_str = charla.fecha.strftime('%d/%m/%Y %H:%M') if charla.fecha else "Sin fecha"
                worksheet_charla.merge_range('A3:G3', f"Fecha: {fecha_str}", desc_format)
                
                # Aplicar formato a encabezados (desplazados por las filas de título)
                header_format_charla = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4F81BD',
                    'font_color': 'white',
                    'border': 1,
                    'align': 'center',
                    'valign': 'vcenter'
                })
                
                for col_num, value in enumerate(df_charla.columns.values):
                    worksheet_charla.write(3, col_num, value, header_format_charla)
                
                # Escribir datos desde la fila 4 (después de título, descripción y encabezados)
                for row_num, row_data in enumerate(df_charla.values):
                    for col_num, cell_data in enumerate(row_data):
                        worksheet_charla.write(row_num + 4, col_num, cell_data)
                
                # Auto ajustar columnas
                for i, col in enumerate(df_charla.columns):
                    column_width = max(df_charla[col].astype(str).map(len).max(), len(col) + 2)
                    worksheet_charla.set_column(i, i, column_width)
    
    return temp_file.name

def export_reporte_general(asistentes_total, asistentes_confirmados, asistencia_charlas, charlas):
    """
    Genera un reporte general con estadísticas profesionales
    
    Args:
        asistentes_total (int): Total de asistentes registrados
        asistentes_confirmados (int): Total de asistentes que confirmaron asistencia
        asistencia_charlas (dict): Estadísticas por charla
        charlas (list): Lista de todas las charlas
        
    Returns:
        str: Ruta al archivo Excel temporal
    """
    # Crear archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()
    
    # Crear Excel con pandas y xlsxwriter
    with pd.ExcelWriter(temp_file.name, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Crear hoja de resumen general
        worksheet_resumen = workbook.add_worksheet('Resumen General')
        
        # Formatos
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center'
        })
        
        percent_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'num_format': '0.00%'
        })
        
        # Título
        fecha_actual = datetime.now().strftime('%d/%m/%Y')
        worksheet_resumen.merge_range('A1:D1', 'REPORTE GENERAL DE ASISTENCIA', title_format)
        worksheet_resumen.merge_range('A2:D2', f'Fecha de generación: {fecha_actual}', workbook.add_format({'italic': True, 'align': 'center'}))
        
        # Espacio
        worksheet_resumen.write('A3', '')
        
        # Estadísticas generales
        worksheet_resumen.merge_range('A4:D4', 'ESTADÍSTICAS GENERALES', header_format)
        
        worksheet_resumen.merge_range('A5:C5', 'Descripción', header_format)
        worksheet_resumen.write('D5', 'Valor', header_format)
        
        # Datos
        worksheet_resumen.merge_range('A6:C6', 'Total de asistentes registrados', cell_format)
        worksheet_resumen.write('D6', asistentes_total, cell_format)
        
        worksheet_resumen.merge_range('A7:C7', 'Total de asistentes que confirmaron asistencia', cell_format)
        worksheet_resumen.write('D7', asistentes_confirmados, cell_format)
        
        worksheet_resumen.merge_range('A8:C8', 'Porcentaje de confirmación', cell_format)
        
        # Evitar división por cero
        porcentaje = 0 if asistentes_total == 0 else asistentes_confirmados / asistentes_total
        worksheet_resumen.write('D8', porcentaje, percent_format)
        
        # Espacio
        worksheet_resumen.write('A9', '')
        
        # Estadísticas por charla
        worksheet_resumen.merge_range('A10:E10', 'ESTADÍSTICAS POR CHARLA', header_format)
        
        worksheet_resumen.write('A11', 'ID', header_format)
        worksheet_resumen.write('B11', 'Nombre de Charla', header_format)
        worksheet_resumen.write('C11', 'Registrados', header_format)
        worksheet_resumen.write('D11', 'Asistieron', header_format)
        worksheet_resumen.write('E11', '% Asistencia', header_format)
        
        # Añadir datos por cada charla
        row = 12
        for charla in charlas:
            if charla.id in asistencia_charlas:
                stats = asistencia_charlas[charla.id]
                worksheet_resumen.write(f'A{row}', charla.id, cell_format)
                worksheet_resumen.write(f'B{row}', stats['nombre'], cell_format)
                worksheet_resumen.write(f'C{row}', stats['total_registrados'], cell_format)
                worksheet_resumen.write(f'D{row}', stats['total_asistieron'], cell_format)
                
                # Evitar división por cero
                porcentaje_charla = 0 if stats['total_registrados'] == 0 else stats['total_asistieron'] / stats['total_registrados']
                worksheet_resumen.write(f'E{row}', porcentaje_charla, percent_format)
                
                row += 1
        
        # Auto ajustar columnas
        worksheet_resumen.set_column('A:A', 10)
        worksheet_resumen.set_column('B:B', 40)
        worksheet_resumen.set_column('C:E', 15)
        
        # Crear un gráfico circular para mostrar la relación entre registrados vs. confirmados
        chart_pie = workbook.add_chart({'type': 'pie'})
        
        # Crear una hoja de datos para el gráfico
        data_sheet = workbook.add_worksheet('_Datos')
        data_sheet.write('A1', 'Categoría')
        data_sheet.write('B1', 'Valor')
        data_sheet.write('A2', 'Asistieron')
        data_sheet.write('B2', asistentes_confirmados)
        data_sheet.write('A3', 'No Asistieron')
        data_sheet.write('B3', asistentes_total - asistentes_confirmados)
        
        # Configurar el gráfico
        chart_pie.add_series({
            'name': 'Asistencia',
            'categories': '=_Datos!$A$2:$A$3',
            'values': '=_Datos!$B$2:$B$3',
            'data_labels': {'percentage': True}
        })
        
        chart_pie.set_title({'name': 'Proporción de Asistencia'})
        chart_pie.set_style(10)
        
        # Insertar el gráfico en la hoja de resumen
        worksheet_resumen.insert_chart('A20', chart_pie, {'x_offset': 25, 'y_offset': 10, 'x_scale': 1.5, 'y_scale': 1.5})
        
        # Crear un gráfico de columnas para comparar registros vs. asistencias por charla
        chart_column = workbook.add_chart({'type': 'column'})
        
        # Preparar datos para el gráfico de columnas
        col_data_sheet = workbook.add_worksheet('_DatosCharlas')
        col_data_sheet.write('A1', 'Charla')
        col_data_sheet.write('B1', 'Registrados')
        col_data_sheet.write('C1', 'Asistieron')
        
        row_data = 2
        for charla in charlas:
            if charla.id in asistencia_charlas:
                stats = asistencia_charlas[charla.id]
                col_data_sheet.write(f'A{row_data}', stats['nombre'])
                col_data_sheet.write(f'B{row_data}', stats['total_registrados'])
                col_data_sheet.write(f'C{row_data}', stats['total_asistieron'])
                row_data += 1
        
        # Configurar el gráfico de columnas
        chart_column.add_series({
            'name': 'Registrados',
            'categories': f'=_DatosCharlas!$A$2:$A${row_data-1}',
            'values': f'=_DatosCharlas!$B$2:$B${row_data-1}',
            'fill': {'color': '#4F81BD'}
        })
        
        chart_column.add_series({
            'name': 'Asistieron',
            'categories': f'=_DatosCharlas!$A$2:$A${row_data-1}',
            'values': f'=_DatosCharlas!$C$2:$C${row_data-1}',
            'fill': {'color': '#C0504D'}
        })
        
        chart_column.set_title({'name': 'Registros vs. Asistencias por Charla'})
        chart_column.set_x_axis({'name': 'Charla'})
        chart_column.set_y_axis({'name': 'Cantidad'})
        chart_column.set_style(10)
        
        # Insertar el gráfico en la hoja de resumen (debajo del pie chart)
        worksheet_resumen.insert_chart('G20', chart_column, {'x_offset': 25, 'y_offset': 10, 'x_scale': 1.5, 'y_scale': 1.5})
        
        # Ocultar las hojas de datos
        data_sheet.hide()
        col_data_sheet.hide()
    
    return temp_file.name