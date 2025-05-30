import os
import openai
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import PyPDF2
from docx import Document
import uuid

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf'}
openai.api_key = os.environ.get('OPENAI_API_KEY')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text
    except Exception as e:
        print(f"Error al extraer texto del PDF: {e}")
        return None

def generate_estado_del_arte(text):
    max_length = 100000
    truncated_text = text[:max_length] if len(text) > max_length else text

    prompt = f"""
A partir del siguiente texto de un artículo científico, redacta un estado del arte dividido en tres secciones. Cada sección debe comenzar con un subtítulo en negrita utilizando Markdown (es decir, encerrado entre dos asteriscos '**'). Las secciones son:

**Fase Inicial – Introducción contextual del tema**

**Fase Analítica – Síntesis crítica y comparativa**

**Fase Final – Identificación de vacíos y proyecciones**

Texto base del artículo:
{truncated_text}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error al generar el estado del arte: {str(e)}"

def save_to_word(text, filename):
    doc = Document()
    for line in text.split('\n'):
        doc.add_paragraph(line)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    doc.save(filepath)
    return filepath

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
        
        # Crear nombre único para el archivo Word
        word_filename = f"estado_arte_{uuid.uuid4().hex[:8]}.docx"
        word_path = save_to_word(estado_del_arte, word_filename)

        # Retornar estado del arte y URL de descarga
        return jsonify({
            'estado_del_arte': estado_del_arte,
            'word_download_url': f"/download/{word_filename}"
        }), 200

    return jsonify({'error': 'Tipo de archivo no permitido. Solo se permiten archivos PDF.'}), 400

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'error': 'Archivo no encontrado.'}), 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
