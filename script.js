const form = document.getElementById('upload-form');
const pdfInput = document.getElementById('pdf-file');
const estadoDelArteDiv = document.getElementById('estado-del-arte');
const fileNameDisplay = document.getElementById('file-name');
const statusMessage = document.getElementById('status-message');

// Mensajes de bienvenida e instrucción
const message = document.getElementById('message');
const instruction = document.getElementById('instruction');
const welcomeMessage = "¿En qué puedo ayudarte?";
const instructionMessage = "Adjuntar el artículo científico del cual se desea obtener el estado del arte.";

// Tipeo de mensaje y bienvenida
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

// Mostrar el nombre del archivo seleccionado
pdfInput.addEventListener('change', function () {
    if (pdfInput.files.length > 0) {
        fileNameDisplay.textContent = pdfInput.files[0].name;
    } else {
        fileNameDisplay.textContent = "No se ha seleccionado ningún archivo";
    }
});

// Configura la URL de la API para el entorno de producción
const apiUrl = 'https://jofech20-github-io.onrender.com/upload_pdf';

// Manejo del formulario para subir el PDF
form.addEventListener('submit', async function (e) {
    e.preventDefault();

    estadoDelArteDiv.textContent = ''; // Limpiar el contenido anterior
    statusMessage.textContent = 'Procesando...'; // Mensaje de carga

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
        } else {
            estadoDelArteDiv.textContent = data.estado_del_arte || 'No se generó ningún estado del arte.';
            statusMessage.textContent = 'Listo'; // Mensaje de éxito
        }
    } catch (error) {
        estadoDelArteDiv.textContent = 'Error al procesar la solicitud. Intenta nuevamente.';
        statusMessage.textContent = ''; // Limpiar mensaje de estado si hay error
    }
});
