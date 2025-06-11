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
CORS(app, origins="https://jofech20.github.io")

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
API_KEY = os.environ.get('ELSEVIER_API_KEY')

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
        print(f"Texto extraído del PDF: {text[:500]}...")
        return text
    except Exception as e:
        print(f"Error al extraer texto: {e}")
        return None

def extract_doi_from_text(text):
    match = re.search(r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.IGNORECASE)
    if match:
        doi = match.group(0).strip().replace(' ', '').split('RESEARCH')[0]
        print(f"DOI encontrado: {doi}")
        return doi
    return None

def generate_estado_del_arte(text):
    prompt = f"""
Redacta un **estado del arte** a partir del siguiente texto de un artículo científico, siguiendo **estrictamente** esta estructura, con subtítulos en negrita usando Markdown (doble asterisco `**`):

**Fase Inicial – Introducción contextual del tema**  
(Explica brevemente el contexto general del tema del artículo.)

**Fase Analítica – Síntesis crítica y comparativa**  
(Compara hallazgos, enfoques o metodologías clave en la literatura.)

**Fase Final – Identificación de vacíos y proyecciones**  
(Señala lo que falta en la literatura y posibles líneas futuras de investigación.)

Texto base del artículo:
{text[:5000]}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al generar estado del arte: {str(e)}"

def save_to_word(text, filename):
    doc = Document()
    for line in text.split('\n'):
        doc.add_paragraph(line)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    doc.save(path)
    return path

def get_article_details(doi):
    url = f"https://api.elsevier.com/content/article/doi/{doi}"
    headers = {'Accept': 'application/json', 'X-ELS-APIKey': API_KEY}
    response = requests.get(url, headers=headers)

    try:
        data = response.json()
        print("Respuesta completa de Elsevier:", data)

        coredata = data.get('full-text-retrieval-response', {}).get('coredata', {})
        title = coredata.get('dc:title', '')
        authors_list = coredata.get('dc:creator', [])

        if isinstance(authors_list, list):
            authors = ', '.join(author.get('$', '') for author in authors_list)
        else:
            authors = authors_list.get('$', '')

        is_scopus = "Sí" if 'scopus-id' in data.get('full-text-retrieval-response', {}) else "No"

        return {
            "title": title,
            "authors": authors,
            "is_scopus": is_scopus
        }

    except Exception as e:
        print("Error parseando respuesta:", e)
        return {"title": "", "authors": "", "is_scopus": "No"}

def extraer_titulo_y_autores(texto):
    lineas = texto.strip().split("\n")
    titulo = ""
    autores = ""

    for i, linea in enumerate(lineas):
        if 50 < len(linea) < 200 and not titulo:
            titulo = linea.strip()
            if i + 1 < len(lineas):
                posibles_autores = lineas[i + 1].strip()
                if 5 < len(posibles_autores) < 200:
                    autores = posibles_autores
            break
    return titulo or "Título no disponible", autores or "Autores no disponibles"

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No se ha enviado ningún archivo'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Archivo inválido. Solo se permiten PDFs.'}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    texto = extract_text_from_pdf(path)
    if not texto:
        return jsonify({'error': 'No se pudo extraer texto del PDF.'}), 400

    estado = generate_estado_del_arte(texto)
    doi = extract_doi_from_text(texto)
    metadatos = get_article_details(doi) if doi else {"title": "", "authors": "", "is_scopus": "No"}

    # Si no hay metadatos válidos desde Elsevier, extraer del texto
    if not metadatos["title"] or not metadatos["authors"]:
        titulo_alt, autores_alt = extraer_titulo_y_autores(texto)
        metadatos["title"] = titulo_alt
        metadatos["authors"] = autores_alt
        metadatos["is_scopus"] = "Desconocido"

    nombre_word = f"estado_arte_{uuid.uuid4().hex[:8]}.docx"
    ruta_word = save_to_word(estado, nombre_word)

    return jsonify({
        "title": metadatos["title"],
        "authors": metadatos["authors"],
        "is_scopus": metadatos["is_scopus"],
        "estado_del_arte": estado,
        "word_download_url": f"/download/{nombre_word}"
    }), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({'error': 'Archivo no encontrado.'}), 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
