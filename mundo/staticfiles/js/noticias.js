class NoticiasGanaderiaCeba {
    constructor() {
        this.urlFuentes = {
            fedegan: 'https://www.fedegan.org.co/',
            contextoGanadero: 'https://www.contextoganadero.com',
            ica: 'https://www.ica.gov.co/home'
        };
        this.noticiasContainer = document.getElementById('noticias-container');
        this.cargarNoticias();
    }

    async cargarNoticias() {
        try {
            const noticias = [
                {
                    titulo: "Fedegán",
                    descripcion: "La Federación Colombiana de Ganaderos es un espacio dedicado a promover la ganadería colombiana. Ofrece información sobre su misión, visión, programas, cifras del sector y eventos relevantes del gremio ganadero.",
                    fuente: "Fedegán",
                    url: "https://www.fedegan.org.co/"
                },
                {
                    titulo: "Contexto Ganadero",
                    descripcion: "Es un periódico digital dedicado a la ganadería y al entorno rural colombiano. Su objetivo es informar, defender los intereses del sector agropecuario y destacar la importancia de la vida rural como un proyecto de paz y desarrollo.",
                    fuente: "Contexto Ganadero",
                    url: "https://www.contextoganadero.com/"
                },
                {
                    titulo: "ICA",
                    descripcion: "La página web del Instituto Colombiano Agropecuario (ICA) es un espacio que ofrece información sobre normativas, servicios, estadísticas y estrategias para garantizar la sanidad y calidad de los productos pecuarios del país.",
                    fuente: "ICA",
                    url: "https://www.ica.gov.co/noticias"
                }
            ];

            this.renderizarNoticias(noticias);
        } catch (error) {
            console.error("Error cargando noticias:", error);
        }
    }

    renderizarNoticias(noticias) {
        this.noticiasContainer.innerHTML = '';
        noticias.forEach(noticia => {
            const noticiaElemento = document.createElement('div');
            noticiaElemento.classList.add('noticia-card');
            noticiaElemento.innerHTML = `
                <div class="noticia-contenido">
                    <h3>${noticia.titulo}</h3>
                    <p>${noticia.descripcion}</p>
                    <div class="noticia-fuente">
                        <span>Fuente: ${noticia.fuente}</span>
                        <a href="${noticia.url}" target="_blank" class="boton-leer-mas">Leer más</a>
                    </div>
                </div>
            `;
            this.noticiasContainer.appendChild(noticiaElemento);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new NoticiasGanaderiaCeba();
});