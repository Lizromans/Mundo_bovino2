// Funcionalidad de impresión mejorada
document.addEventListener('DOMContentLoaded', function() {
    // Obtener parámetros de la URL
    const urlParams = new URLSearchParams(window.location.search);
    const imprimir = urlParams.get('imprimir');

    // Función de impresión
    function imprimirPagina() {
        console.log('Intentando imprimir página');
        try {
            // Intentar imprimir de múltiples formas
            if (window.print) {
                window.print();
            } else if (document.execCommand) {
                document.execCommand('print', false, null);
            } else {
                console.error('Impresión no soportada');
                alert('Su navegador no soporta impresión directa');
            }
        } catch (error) {
            console.error('Error al imprimir:', error);
            alert('Ocurrió un error al intentar imprimir');
        }
    }

    // Si el parámetro imprimir está presente, intentar imprimir
    if (imprimir === 'true') {
        // Usar setTimeout para asegurar que el DOM esté completamente cargado
        setTimeout(imprimirPagina, 500);
    }

    // Añadir evento al botón de imprimir
    const botonImprimir = document.querySelector('.descargar');
    if (botonImprimir) {
        botonImprimir.addEventListener('click', imprimirPagina);
    }
});

// Soporte adicional para diferentes navegadores
window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);
    const imprimir = urlParams.get('imprimir');
    
    if (imprimir === 'true') {
        setTimeout(function() {
            window.print();
        }, 1000);
    }
};