// Contador de llamadas para depuración
let contadorActualizaciones = 0;

// Función para actualizar el formulario de animales basado en la cantidad
function actualizarFormularioAnimales() {
    // Contador para depuración
    contadorActualizaciones++;
    console.log(`Llamada #${contadorActualizaciones} a actualizarFormularioAnimales`);

    const cantidad = parseInt(document.getElementById('cantidad').value) || 0;
    console.log(`Cantidad seleccionada: ${cantidad}`);

    // Identificar el contenedor correcto
    const contenedor = document.getElementById('detalles_animales');
    if (!contenedor) {
        console.error('ERROR: No se encontró el elemento con ID "detalles_animales"');
        // Buscar posibles contenedores alternativos que puedan estar siendo utilizados
        const posiblesContenedores = document.querySelectorAll('[id="animal"],[id="detalle"],[class="animal"],[class="detalle"]');
        if (posiblesContenedores.length > 0) {
            console.warn('Posibles contenedores encontrados:', posiblesContenedores);
        }
        return;
    }

    // Verificar si ya tiene contenido antes de limpiar
    console.log(`Contenido del contenedor antes de limpiar: ${contenedor.children.length} elementos`);

    // Limpiar contenedor completamente - esta es la parte crítica
    contenedor.innerHTML = '';

    console.log(`Contenedor limpio: ${contenedor.children.length} elementos`);

    // Si no hay animales, no hay nada que hacer
    if (cantidad <= 0) {
        console.log('Cantidad es 0 o negativa, no se generan campos');
        return;
    }

    // Generar campos para cada animal
    console.log(`Generando ${cantidad} campos para ventas de animales`);

    for (let i = 1; i <= cantidad; i++) {
        console.log(`Generando campo para animal #${i}`);

        const animalDiv = document.createElement('div');
        animalDiv.classList.add('card', 'mb-3', 'p-3');
        animalDiv.dataset.animal = i; // Añadir data attribute para seguimiento

        animalDiv.innerHTML = `
            <h5 class="card-title">Animal #${i}</h5>
            <div class="row">
                <div class="col-md-4">
                    <label for="cod_ani_${i}">Código:</label>
                    <input type="number" id="cod_ani_${i}" name="cod_ani_${i}" class="form-control" required>
                </div>
                <div class="col-md-8">
                    <label for="edad_aniven_${i}">Edad:</label>
                    <input type="number" id="edad_aniven_${i}" name="edad_aniven_${i}" class="form-control" required>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-6">
                    <label for="peso_ani_${i}">Peso (kg):</label>
                    <input type="number" id="peso_ani_${i}" name="peso_ani_${i}" class="form-control" 
                           step="0.01" min="0" required onchange="calcularPrecioTotal()">
                </div>
                <div class="col-md-6">
                    <label for="precio_uni_${i}">Precio:</label>
                    <div class="input-group">
                        <span class="input-group-text">$</span>
                        <input type="text" id="precio_uni_${i}" name="precio_uni_${i}" class="form-control" 
                               required onchange="formatearPrecioCOP(this); calcularPrecioTotal()">
                    </div>
                </div>
            </div>
        `;
        contenedor.appendChild(animalDiv);
    }

    console.log(`Generación completada. Contenedor ahora tiene ${contenedor.children.length} elementos`);

    // Actualizar formato del campo de precio total
    const precioTotalInput = document.getElementById('precio_total');
    if (precioTotalInput) {
        const precioTotalContainer = precioTotalInput.parentElement;
        const yaFormateado = precioTotalContainer.querySelector('.input-group-text');

        if (!yaFormateado) {
            console.log('Formateando campo de precio total');
            // Envolver el input en un input-group con el símbolo de pesos
            const inputGroup = document.createElement('div');
            inputGroup.className = 'input-group';

            const currencySymbol = document.createElement('span');
            currencySymbol.className = 'input-group-text';
            currencySymbol.textContent = '$';

            precioTotalInput.parentNode.insertBefore(inputGroup, precioTotalInput);
            inputGroup.appendChild(currencySymbol);
            inputGroup.appendChild(precioTotalInput);

            // Actualizar los atributos del input
            precioTotalInput.setAttribute('readonly', true);
        }
    } else {
        console.warn('No se encontró el campo de precio total');
    }
}

// Función para formatear los valores a pesos colombianos
function formatearPrecioCOP(input) {
    let valor = input.value.replace(/[^\d]/g, '');
    if (valor) {
        // Convertir a número
        let numero = parseInt(valor);
        // Formatear con separadores de miles
        input.value = numero.toLocaleString('es-CO');
    }
}

// Función para calcular el precio total basado en los precios unitarios
function calcularPrecioTotal() {
    const cantidad = parseInt(document.getElementById('cantidad').value) || 0;
    let total = 0;

    console.log(`Calculando precio total para ${cantidad} animales`);

    for (let i = 1; i <= cantidad; i++) {
        const precioInput = document.getElementById(`precio_uni_${i}`);

        if (precioInput) {
            // Eliminar formato para obtener el valor numérico
            const precioTexto = precioInput.value.replace(/[^\d]/g, '');
            const precio = parseFloat(precioTexto) || 0;
            total += precio;
            console.log(`Animal #${i}: Precio = ${precio}, Total acumulado = ${total}`);
        } else {
            console.warn(`No se encontró el campo de precio para el animal #${i}`);
        }
    }

    // Actualizar el campo de precio total con formato
    const precioTotalInput = document.getElementById('precio_total');
    if (precioTotalInput) {
        precioTotalInput.value = total.toLocaleString('es-CO');
        console.log(`Precio total actualizado: ${precioTotalInput.value}`);
    } else {
        console.warn('No se encontró el campo de precio total');
    }
}

// Función para verificar la estructura HTML
function verificarEstructuraHTML() {
    console.log('--- Verificando estructura HTML ---');

    // Verificar campo de cantidad
    const cantidadInput = document.getElementById('cantidad');
    if (!cantidadInput) {
        console.error('No se encontró el campo de cantidad (ID: cantidad)');
    } else {
        console.log(`Campo de cantidad encontrado, valor: ${cantidadInput.value}`);
    }

    // Verificar contenedor de detalles
    const contenedor = document.getElementById('detalles_animales');
    if (!contenedor) {
        console.error('No se encontró el contenedor de detalles (ID: detalles_animales)');
        // Buscar posibles contenedores alternativos
        document.querySelectorAll('div').forEach(div => {
            if (div.children && div.children.length > 0 && 
                Array.from(div.children).some(child => 
                    child.textContent && child.textContent.includes('Animal #'))) {
                console.warn('Posible contenedor de animales encontrado:', div);
            }
        });
    } else {
        console.log(`Contenedor de detalles encontrado, contiene ${contenedor.children.length} elementos`);
    }

    // Verificar si hay múltiples elementos con IDs duplicados
    ['cantidad', 'detalles_animales', 'precio_total'].forEach(id => {
        const elementos = document.querySelectorAll(`#${id}`);
        if (elementos.length > 1) {
            console.error(`¡ALERTA! Se encontraron ${elementos.length} elementos con el ID "${id}"`);
        }
    });

    console.log('--- Fin de verificación HTML ---');
}

// Inicializar el formulario
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado. Inicializando formulario de ventas...');

    // Verificar estructura HTML
    verificarEstructuraHTML();

    // Eliminar event listeners existentes para evitar duplicación
    const cantidadInput = document.getElementById('cantidad');
    if (cantidadInput) {
        console.log('Configurando event listener al campo de cantidad');

        // Eliminar eventos anteriores de manera segura
        const nuevoInput = cantidadInput.cloneNode(true);
        cantidadInput.parentNode.replaceChild(nuevoInput, cantidadInput);

        // Agregar event listener al nuevo elemento
        nuevoInput.addEventListener('change', function(event) {
            console.log(`Campo de cantidad cambió a: ${event.target.value}`);
            actualizarFormularioAnimales();
        });
    } else {
        console.error('No se encontró el campo de cantidad');
    }

    // Verificar si hay múltiples scripts de ventas.js
    const scripts = document.querySelectorAll('script');
    let contadorVentasJS = 0;

    scripts.forEach(script => {
        if (script.src && script.src.includes('ventas.js')) {
            contadorVentasJS++;
        }
    });

    if (contadorVentasJS > 1) {
        console.error(`¡ALERTA! Se encontraron ${contadorVentasJS} scripts de ventas.js incluidos`);
    }

    // Ejecutar la actualización inicial del formulario
    console.log('Iniciando actualización inicial del formulario');
    actualizarFormularioAnimales();
});

// --- NUEVA FUNCIONALIDAD PARA EDITAR VENTAS ---
    
    // Escuchar cambios en los precios unitarios para recalcular el precio total en formularios de edición
    document.querySelectorAll('.precio-uni-edit').forEach(input => {
        input.addEventListener('change', function() {
            const ventaId = this.getAttribute('data-venta');
            recalcularPrecioTotal(ventaId);
        });
    });
    
    // Función para recalcular el precio total de una venta en edición
    function recalcularPrecioTotal(ventaId) {
        const modal = document.getElementById('editModal-' + ventaId);
        let total = 0;
        
        // Sumar todos los precios unitarios
        modal.querySelectorAll('.precio-uni-edit').forEach(input => {
            total += parseFloat(input.value || 0);
        });
        
        // Actualizar el precio total
        const precioTotalInput = document.getElementById('precio_total-edit-' + ventaId);
        precioTotalInput.value = total.toFixed(0);
    }
    
    // Inicializar todos los modales de edición con sus totales correctos
    document.querySelectorAll('[id^="editModal-"]').forEach(modal => {
        const ventaId = modal.id.replace('editModal-', '');
        recalcularPrecioTotal(ventaId);
    });
