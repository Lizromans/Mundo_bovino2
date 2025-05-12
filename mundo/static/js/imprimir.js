document.addEventListener('DOMContentLoaded', function() {
    // Button to download PDF
    const descargaPdfBtn = document.getElementById('descarga-pdf');
    
    if (descargaPdfBtn) {
        descargaPdfBtn.addEventListener('click', function() {
            const compraId = this.getAttribute('data-compra-id');
            window.location.href = `/compra/${compraId}/pdf/`;
        });
    }
});