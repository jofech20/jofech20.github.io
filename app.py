import os
import re
import requests
from openai import OpenAI
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import PyPDF2
from docx import Document
import uuid

app = Flask(__name__)

# Configuración de CORS para permitir solicitudes desde https://jofech20.github.io
CORS(app, origins="https://jofech20.github.io")

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf'}

# Inicializar cliente de OpenAI usando el nuevo SDK
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Configura tu API Key de Elsevier usando la variable de entorno
API_KEY = os.environ.get('ELSEVIER_API_KEY')  # Tomar la clave desde la variable de entorno

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
        print(f"Texto completo extraído del PDF: {text[:1000]}...")  # Muestra los primeros 1000 caracteres
        return text
    except Exception as e:
        print(f"Error al extraer texto del PDF: {e}")
        return None

def extract_doi_from_text(text):
    # Expresión regular para encontrar el DOI en el formato más común
    doi_match = re.search(r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.IGNORECASE)
    if doi_match:
        # Limpiar el DOI: quitar espacios adicionales o caracteres incorrectos
        doi = doi_match.group(0).replace(' ', '').replace('-', '')
        print(f"DOI encontrado: {doi}")  # Verifica el DOI encontrado
        return doi
    else:
        print("No se encontró DOI en el texto.")
        return None

def generate_estado_del_arte(text):
    max_length = 5000  # Limitar la longitud del texto base
    truncated_text = text[:max_length] if len(text) > max_length else text

    prompt = f"""
    Redacta un **estado del arte** a partir del siguiente texto de un artículo científico, siguiendo **estrictamente** esta estructura, con subtítulos en negrita usando Markdown (doble asterisco `**`):

    **Fase Inicial – Introducción contextual del tema**  
    (Explica brevemente el contexto general del tema del artículo.)

    **Fase Analítica – Síntesis crítica y comparativa**  
    (Compara hallazgos, enfoques o metodologías clave en la literatura.)

    **Fase Final – Identificación de vacíos y proyecciones**  
    (Señala lo que falta en la literatura y posibles líneas futuras de investigación.)

    Texto base del artículo:
    {truncated_text}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,  # Reducir la cantidad de tokens de la respuesta
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al generar el estado del arte: {str(e)}"

def save_to_word(text, filename):
    doc = Document()
    for line in text.split('\n'):
        doc.add_paragraph(line)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    doc.save(filepath)
    return filepath

# Función para obtener detalles del artículo desde Elsevier
def get_article_details(doi):
    url = f"https://api.elsevier.com/content/article/doi/{doi}"
    headers = {'Accept': 'application/json', 'X-ELS-APIKey': API_KEY}
    
    response = requests.get(url, headers=headers)
    print("Respuesta completa de la API:", response.json())  # Ver la respuesta completa de la API
    
    if response.status_code == 200:
        data = response.json()
        title = data.get('abstracts-retrieval-response', {}).get('entry', [{}])[0].get('dc:title', 'Título no disponible')
        authors = data.get('abstracts-retrieval-response', {}).get('entry', [{}])[0].get('dc:creator', 'Autor no disponible')
        is_scopus = 'Yes' if 'scopus' in data.get('abstracts-retrieval-response', {}).get('entry', [{}])[0].get('prism:publicationName', '').lower() else 'No'
        return title, authors, is_scopus
    else:
        print(f"Error en la API de Elsevier: {response.status_code}")
        return None, None, None

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

        print(f"Archivo recibido: {filename}")  # Verificar que el archivo se guardó correctamente

        extracted_text = extract_text_from_pdf(pdf_path)

        if not extracted_text:
            return jsonify({'error': 'No se pudo extraer texto del PDF.'}), 400

        print(f"Texto extraído: {extracted_text[:1000]}")  # Muestra los primeros 1000 caracteres

        estado_del_arte = generate_estado_del_arte(extracted_text)

        # Extraer DOI del texto (esto es opcional y podría mejorarse)
        doi = extract_doi_from_text(extracted_text) or "10.1016/j.articulo123"  # Usar un valor predeterminado si no se encuentra el DOI
        title, authors, is_scopus = get_article_details(doi)

        # Crear nombre único para el archivo Word
        word_filename = f"estado_arte_{uuid.uuid4().hex[:8]}.docx"
        word_path = save_to_word(estado_del_arte, word_filename)

        print(f"Enviando detalles del artículo: Título - {title}, Autores - {authors}, Scopus - {is_scopus}")

        return jsonify({
            'estado_del_arte': estado_del_arte,
            'word_download_url': f"/download/{word_filename}",
            'title': title,
            'authors': authors,
            'is_scopus': is_scopus
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
