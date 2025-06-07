const form = document.getElementById('upload-form');
const pdfInput = document.getElementById('pdf-file');
const estadoDelArteDiv = document.getElementById('estado-del-arte');
const fileNameDisplay = document.getElementById('file-name');
const statusMessage = document.getElementById('status-message');
const copiarBoton = document.getElementById('copiar-texto');
const mensajeCopiado = document.getElementById('mensaje-copiado');
const downloadBtn = document.getElementById('btnDescargar');

// Elementos para los detalles del artículo
const articleDetailsSection = document.getElementById('article-details');
const articleTitle = document.getElementById('article-title');
const articleAuthors = document.getElementById('article-authors');
const articleScopus = document.getElementById('article-scopus');

// Mensajes dinámicos
const message = document.getElementById('message');
const instruction = document.getElementById('instruction');
const welcomeMessage = "¿En qué puedo ayudarte?";
const instructionMessage = "Adjuntar el artículo científico del cual se desea obtener el estado del arte.";

let i = 0;
function typeMessage() {
    if (i < welcomeMessage.length) {
        message.textContent += welcomeMessage.charAt(i);
        i++;
        setTimeout(typeMessage, 100);
    } else {
        typeInstruction();
    }
}

function typeInstruction() {
    let j = 0;
    function type() {
        if (j < instructionMessage.length) {
            instruction.textContent += instructionMessage.charAt(j);
            j++;
            setTimeout(type, 50);
        }
    }
    type();
}
window.onload = typeMessage;

pdfInput.addEventListener('change', function () {
    if (pdfInput.files.length > 0) {
        fileNameDisplay.textContent = pdfInput.files[0].name;
    } else {
        fileNameDisplay.textContent = "No se ha seleccionado ningún archivo";
    }
});

const apiUrl = 'https://jofech20-github-io.onrender.com/upload_pdf';

form.addEventListener('submit', async function (e) {
    e.preventDefault();

    estadoDelArteDiv.textContent = '';
    statusMessage.textContent = 'Procesando...';
    downloadBtn.style.display = 'none';
    articleDetailsSection.style.display = 'none'; // Ocultar los detalles hasta recibir la respuesta

    const formData = new FormData();
    formData.append('file', pdfInput.files[0]);

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            estadoDelArteDiv.textContent = `Error: ${data.error}`;
            statusMessage.textContent = '';
        } else {
            // Mostrar el estado del arte generado
            estadoDelArteDiv.innerHTML = marked.parse(data.estado_del_arte || 'No se generó ningún estado del arte.');
            statusMessage.textContent = 'Listo';

            // Mostrar los detalles del artículo
            articleTitle.textContent = data.title || 'Título no disponible';
            articleAuthors.textContent = data.authors || 'Autor no disponible';
            articleScopus.textContent = data.is_scopus || 'No disponible';
            articleDetailsSection.style.display = 'block'; // Mostrar los detalles

            // Mostrar el botón de descarga
            if (data.word_download_url) {
                downloadBtn.style.display = 'block';
                downloadBtn.onclick = () => {
                    window.location.href = data.word_download_url;
                };
            }
        }
    } catch (error) {
        estadoDelArteDiv.textContent = 'Error al procesar la solicitud. Intenta nuevamente.';
        statusMessage.textContent = '';
    }
});

copiarBoton.addEventListener('click', function () {
    const texto = estadoDelArteDiv.textContent;
    if (texto) {
        navigator.clipboard.writeText(texto).then(() => {
            mensajeCopiado.style.display = 'inline';
            setTimeout(() => {
                mensajeCopiado.style.display = 'none';
            }, 2000);
        }).catch(err => {
            console.error('Error al copiar el texto: ', err);
        });
    }
});

