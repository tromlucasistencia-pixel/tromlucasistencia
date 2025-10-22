
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash, send_file
import mysql.connector
import cv2
import numpy as np
import face_recognition
import base64
import json
import os
import pytz  # ✅ NUEVO IMPORT
from datetime import datetime, date
from pathlib import Path
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'


db_config = {
    "host": "turntable.proxy.rlwy.net",
    "user": "root",
    "password": "MFezbJNQdUFOqpXsUjuENWzVihqMhHcK",
    "database": "railway",
    "port": 39807 
}


def get_db_connection():
    conn = mysql.connector.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        port=db_config["port"],
        charset='utf8mb4',
        use_unicode=True
    )
    conn.set_charset_collation('utf8mb4')
    return conn



# Crear carpetas si no existen
Path("fotos/entrada").mkdir(parents=True, exist_ok=True)
Path("fotos/salida").mkdir(parents=True, exist_ok=True)

# Zona horaria local (CDMX)
tz = pytz.timezone('America/Mexico_City')  # ✅ Zona horaria definida aquí


# PERFILES DE ADMINISTRADORES
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'Tromluc_registroadmin':
            return redirect(url_for('registro'))
        elif password == 'admin2':
            return redirect(url_for('asistencia_html'))
        else:
            return render_template('index.html', error="❌ Contraseña incorrecta.")
    return render_template('index.html')


# ---------------- REGISTRO   ----------------
@app.route('/registro')
def registro():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_tipo, tipo_usuario FROM tipo_usuario")
    tipos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('registro.html', tipos=tipos)


# ---------------- REGISTRAR PERSONA  ----------------
@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    apellido_paterno = request.form['apellido_paterno']
    apellido_materno = request.form['apellido_materno']
    id_tipo = request.form['tipo_usuario']
    foto_base64 = request.form['foto']

    if ',' in foto_base64:
        foto_base64 = foto_base64.split(',')[1]
    imagen_bytes = base64.b64decode(foto_base64)
    nparr = np.frombuffer(imagen_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Redimensionar la imagen antes de pasarla al modelo de reconocimiento facial
    img = cv2.resize(img, (800, 600))

    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 👉 VA AQUÍ ALAN 👇 — intentamos rotaciones si no detecta rostro
    rostros = face_recognition.face_encodings(rgb_img)
    if len(rostros) == 0:
        for angle in [90, 180, 270]:
            rotated = cv2.rotate(rgb_img, {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE
            }[angle])
            rostros = face_recognition.face_encodings(rotated)
            if len(rostros) > 0:
                rgb_img = rotated
                break
    if len(rostros) == 0:
        espejada = cv2.flip(rgb_img, 1)
        rostros = face_recognition.face_encodings(espejada)
        if len(rostros) > 0:
            rgb_img = espejada

    if len(rostros) == 0:
        flash("❌ No se detectó rostro. Asegúrate de estar bien iluminado, de frente y no tan cerca del celular.", "error")

        return redirect(url_for('registro'))
    # 👉 FIN DE CAMBIO ALAN 👆


    vector_rostro = json.dumps(rostros[0].tolist())

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
         INSERT INTO emp_activos (vectores_rostro, nombre, apellido_pa, apellido_ma, id_tipo)
         VALUES (%s, %s, %s, %s, %s)
         ''', (vector_rostro, nombre, apellido_paterno, apellido_materno, id_tipo))
        conn.commit()
        cursor.close()
        conn.close()
        flash("✅ Usuario registrado correctamente", "success")
    except Exception as e:
        flash(f"❌ Error al guardar: {e}", "error")

    return redirect(url_for('registro'))


@app.route('/asistencia')
def asistencia_html():
    return render_template('asistencia.html')

    
# ---------------- ASISTENCIA Y PARA EDITAR LATITUD LONGITUD ----------------
@app.route('/registrar_asistencia', methods=['POST'])
def registrar_asistencia():
    try:
        data = request.get_json()
        foto_base64 = data['foto']
        latitud = data.get('latitud')
        longitud = data.get('longitud')

        if ',' in foto_base64:
            foto_base64 = foto_base64.split(',')[1]
        imagen_bytes = base64.b64decode(foto_base64)
        nparr = np.frombuffer(imagen_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        img = cv2.resize(img, (800, 600))
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Detección de rostro con rotación y espejado
        rostros = face_recognition.face_encodings(rgb)
        if len(rostros) == 0:
            for angle in [90, 180, 270]:
                rotated = cv2.rotate(rgb, {
                    90: cv2.ROTATE_90_CLOCKWISE,
                    180: cv2.ROTATE_180,
                    270: cv2.ROTATE_90_COUNTERCLOCKWISE
                }[angle])
                rostros = face_recognition.face_encodings(rotated)
                if len(rostros) > 0:
                    rgb = rotated
                    break
        if len(rostros) == 0:
            espejada = cv2.flip(rgb, 1)
            rostros = face_recognition.face_encodings(espejada)
            if len(rostros) > 0:
                rgb = espejada

        if len(rostros) == 0:
            return jsonify({'status': 'fail', 'message': '❌ No se detectó rostro. Asegúrate de estar bien iluminado, de frente, y no muy cerca de la cámara.'})

        vector_nuevo = rostros[0]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_emp, vectores_rostro, nombre, apellido_pa FROM emp_activos")
        usuarios = cursor.fetchall()

        matches = []
        for codigo, vector_json, nombre, apellido in usuarios:
            vector_bd = np.array(json.loads(vector_json))
            distancia = face_recognition.face_distance([vector_bd], vector_nuevo)[0]
            if distancia < 0.5:
                matches.append((codigo, nombre, apellido, distancia))

        if not matches:
            cursor.close()
            conn.close()
            return jsonify({'status': 'fail', 'message': '❌ Rostro no reconocido'})

        matches.sort(key=lambda x: x[3])
        codigo_emp, nombre, apellido, _ = matches[0]
        hoy = datetime.now(tz).date()
        hora_actual = datetime.now(tz).time()

        cursor.execute("SELECT id_asistencia FROM asistencia WHERE fecha = %s AND codigo_emp = %s", (hoy, codigo_emp))
        registro = cursor.fetchone()

        nombre_archivo = f"{nombre}_{apellido}_{hoy.strftime('%Y%m%d')}.jpg"

        # === Zona de ubicación ===
        lat = float(latitud)
        lon = float(longitud)

        # Zona AIRES
        aires_lat_min = 20.61193178
        aires_lat_max =  20.61194978
        aires_lon_min = -101.236459205
        aires_lon_max = -101.23644120

        # Zona PINTURA
        pintura_lat_min = 20.60997085
        pintura_lat_max = 20.60998885
        pintura_lon_min = -101.23922558
        pintura_lon_max = -101.23920758

        if aires_lat_min <= lat <= aires_lat_max and aires_lon_min <= lon <= aires_lon_max:
            ubicacion = "Ubicación en zona AIRES"
        elif pintura_lat_min <= lat <= pintura_lat_max and pintura_lon_min <= lon <= pintura_lon_max:
            ubicacion = "Ubicación en zona PINTURA"
        else:
            ubicacion = "Ubicación dentro de la zona de trabajo"

        # === Registro de salida ===
        if registro:
            carpeta = "fotos/salida"
            ruta = os.path.join(carpeta, nombre_archivo)
            cv2.imwrite(ruta, img)
            cursor.execute(
                "UPDATE asistencia SET hora_salida = %s, foto_salida = %s WHERE id_asistencia = %s",
                (hora_actual, foto_base64, registro[0])
            )
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'status': 'ok', 'message': f'🕒 Salida registrada de {nombre}'})

        # === Registro de entrada ===
        else:
            carpeta = "fotos/entrada"
            ruta = os.path.join(carpeta, nombre_archivo)
            cv2.imwrite(ruta, img)
            cursor.execute("""
                INSERT INTO asistencia (codigo_emp, vector, fecha, hora_entrada, latitud, longitud, ubicacion, foto_entrada)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (codigo_emp, json.dumps(vector_nuevo.tolist()), hoy, hora_actual, latitud, longitud, ubicacion, foto_base64))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'status': 'ok', 'message': f'🕐 Entrada registrada de {nombre}'})

    except Exception as e:
        return jsonify({'status': 'fail', 'message': f'❌ Error: {str(e)}'})


        

#MOSTRAR REGISTROS
@app.route('/registros')
def mostrar_registros():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    id_tipo = request.args.get('id_tipo')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query actualizado para traer fotos de entrada y salida
    query = """
        SELECT e.codigo_emp, e.nombre, e.apellido_pa, e.apellido_ma, 
               a.ubicacion, a.foto_entrada, a.foto_salida, 
               a.fecha, a.hora_entrada, a.hora_salida
        FROM asistencia a
        JOIN emp_activos e ON a.codigo_emp = e.codigo_emp
    """
    params = []

    condiciones = []

    if fecha_inicio and fecha_fin:
        condiciones.append("a.fecha BETWEEN %s AND %s")
        params.extend([fecha_inicio, fecha_fin])

    if id_tipo in ['1', '3']:  # Filtra por tipo de usuario si aplica
        condiciones.append("e.id_tipo = %s")
        params.append(id_tipo)

    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)

    query += " ORDER BY a.fecha DESC, a.hora_entrada ASC"

    cursor.execute(query, params)
    registros = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('registros.html', registros=registros)




# ---------------- REGRESAR / DESCARGAR ----------------
@app.route('/regresar')
def regresar_registros():
    return render_template('registro.html')


# ---------------- PARTE DE EXCEL, SE DEBE MODIFICAR PARA LOS FILTROS ----------------
@app.route('/descargar_excel')
def descargar_excel():
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        id_tipo = request.args.get('id_tipo')

        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT 
                e.codigo_emp, 
                e.nombre, 
                e.apellido_pa, 
                e.apellido_ma, 
                a.ubicacion, 
                a.fecha, 
                a.hora_entrada, 
                a.hora_salida,
                a.foto_entrada,
                a.foto_salida
            FROM emp_activos e
            JOIN asistencia a ON e.codigo_emp = a.codigo_emp
        '''

        condiciones = []
        params = []

        if fecha_inicio and fecha_fin:
            condiciones.append("a.fecha BETWEEN %s AND %s")
            params.extend([fecha_inicio, fecha_fin])

        if id_tipo in ['1', '3']:
            condiciones.append("e.id_tipo = %s")
            params.append(id_tipo)

        if condiciones:
            query += " WHERE " + " AND ".join(condiciones)

        query += " ORDER BY a.fecha DESC, a.hora_entrada ASC"

        cursor.execute(query, params)
        registros = cursor.fetchall()

        cursor.close()
        conn.close()

        # ✅ Convertir hora_entrada y hora_salida a HH:MM:SS si son timedelta
        def convertir_hora(valor):
            if not valor:
                return ''
            if isinstance(valor, str):
                return valor
            try:
                total_segundos = int(valor.total_seconds())
                horas = total_segundos // 3600
                minutos = (total_segundos % 3600) // 60
                segundos = total_segundos % 60
                return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
            except Exception:
                return str(valor)

        registros_limpios = []
        for r in registros:
            r = list(r)
            r[6] = convertir_hora(r[6])
            r[7] = convertir_hora(r[7])
            registros_limpios.append(r)

        # Columnas del Excel
        columnas = [
            'Código Empleado', 'Nombre', 'Apellido Paterno', 'Apellido Materno',
            'Ubicación', 'Fecha', 'Hora Entrada', 'Hora Salida',
            'Foto Entrada', 'Foto Salida'
        ]

        df = pd.DataFrame(registros_limpios, columns=columnas)

        # ✅ Crear Excel sin duplicar encabezados
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Asistencia')
            workbook = writer.book
            worksheet = writer.sheets['Asistencia']

            # ✅ Formatos
            formato_titulo = workbook.add_format({
                'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#DCE6F1'
            })
            formato_celda = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            formato_imagen = {'x_scale': 0.35, 'y_scale': 0.35}

            # Ajustar anchos de columna
            worksheet.set_column('A:H', 18, formato_celda)
            worksheet.set_column('I:J', 20)  # columnas de imágenes

            # Aplicar formato a la fila de encabezados
            worksheet.set_row(0, 25, formato_titulo)

            # ✅ Insertar imágenes correctamente alineadas
            for idx, row in enumerate(df.itertuples(index=False), start=1):
                fila_excel = idx  # ya no hay desplazamiento
                if row[8]:  # Foto Entrada
                    try:
                        img_data = base64.b64decode(row[8])
                        img_stream = BytesIO(img_data)
                        worksheet.insert_image(f'I{fila_excel + 1}', 'foto_entrada.png', {
                            'image_data': img_stream, **formato_imagen
                        })
                    except Exception:
                        pass
                if row[9]:  # Foto Salida
                    try:
                        img_data = base64.b64decode(row[9])
                        img_stream = BytesIO(img_data)
                        worksheet.insert_image(f'J{fila_excel + 1}', 'foto_salida.png', {
                            'image_data': img_stream, **formato_imagen
                        })
                    except Exception:
                        pass

        output.seek(0)

        return send_file(
            output,
            download_name='registros_asistencia.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return f"❌ Error al generar Excel: {str(e)}"






    # ---------------- CERRAR SESIÓN DE TODOS LADOS  ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    pass  # o simplemente comenta toda esta sección
    # app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))





