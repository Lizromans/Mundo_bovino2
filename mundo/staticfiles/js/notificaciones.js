 // Script para activar/desactivar todos los checkboxes de módulos
 document.getElementById('toggle-modulos').addEventListener('change', function() {
    const checkboxes = document.querySelectorAll('[name^="notif_"]');
    const modulosOnly = document.querySelectorAll('[name="notif_inventario"], [name="notif_ventas"], [name="notif_calendario"], [name="notif_documentos"], [name="notif_agenda"]');
    
    if (this.checked) {
        modulosOnly.forEach(checkbox => {
            checkbox.disabled = false;
        });
    } else {
        modulosOnly.forEach(checkbox => {
            checkbox.disabled = true;
            checkbox.checked = false;
        });
    }
});

// Ejecutar al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    const toggleModulos = document.getElementById('toggle-modulos');
    if (!toggleModulos.checked) {
        const modulosOnly = document.querySelectorAll('[name="notif_inventario"], [name="notif_ventas"], [name="notif_calendario"], [name="notif_documentos"], [name="notif_agenda"]');
        modulosOnly.forEach(checkbox => {
            checkbox.disabled = true;
        });
    }
});