import os
import openai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # Importa CORS
from werkzeug.utils import secure_filename
import PyPDF2

app = Flask(__name__)
CORS(app)  # Habilita CORS para toda la aplicación

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear la carpeta de subida si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configurar extensiones permitidas y clave de API de OpenAI
ALLOWED_EXTENSIONS = {'pdf'}
openai.api_key = 'OPENAI_API_KEY'  # Cambia esto por tu clave real

# Función para verificar que el archivo tenga la extensión correcta
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para extraer texto de un archivo PDF
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

# Función para generar el estado del arte utilizando OpenAI
def generate_estado_del_arte(text):
    # Limitar el número de caracteres a 10,000 (ajusta según sea necesario)
    max_length = 10000
    truncated_text = text[:max_length] if len(text) > max_length else text
    
    # Define el mensaje de entrada
    messages = [
        {"role": "user", "content": f"A partir del siguiente texto de un artículo científico, genera un estado del arte:\n\n{truncated_text}"}
    ]
    try:
        # Utiliza el nuevo modelo
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error al generar el estado del arte: {str(e)}"


# Ruta para subir el PDF y procesarlo
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No se ha enviado ningún archivo'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No se ha seleccionado ningún archivo'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        extracted_text = extract_text_from_pdf(pdf_path)
        
        if not extracted_text:
            return jsonify({'error': 'No se pudo extraer texto del PDF.'}), 400
        
        estado_del_arte = generate_estado_del_arte(extracted_text)
        
        return jsonify({'estado_del_arte': estado_del_arte}), 200
    
    return jsonify({'error': 'Tipo de archivo no permitido. Solo se permiten archivos PDF.'}), 400

# Ruta para servir el favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
