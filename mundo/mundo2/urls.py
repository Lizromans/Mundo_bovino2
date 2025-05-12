from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.bienvenido, name='bienvenido'),
    path('preguntasfrecuentes/', views.preguntasfrecuentes, name='preguntasfrecuentes'),
    path('iniciarsesion/', views.iniciarsesion, name='iniciarsesion'),
    path('registro/', views.registro, name='registro'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout, name='logout'),
    path('configuraciones/', views.configuraciones, name='configuraciones'),
    path('notificaciones/', views.notificaciones, name='notificaciones'),
    path('privacidad/', views.privacidad, name='privacidad'),
    path('inventario/', views.inventario, name='inventario'),    
    path('registrar_animal/', views.registrar_animal, name='registrar_animal'),
    path('eliminar-animal/<int:animal_id>/', views.eliminar_animal, name='eliminar_animal'),
    path('editar-animal/<int:animal_id>/', views.editar_animal, name='editar_animal'),
    path('calendario/', views.calendario, name='calendario'),
    path('agregar-evento/', views.agregar_evento, name='agregar_evento'),
    path('editar_evento/<int:evento_id>/', views.editar_evento, name='editar_evento'),
    path('eliminar-evento/<int:evento_id>/', views.eliminar_evento, name='eliminar_evento'),
    path('confirmar-vacunacion/', views.confirmar_vacunacion, name='confirmar_vacunacion'),
    path('documento/', views.documento, name='documento'),
    path('agregar/', views.agregar_documento, name='agregar_documento'),
    path('editar_documento/<int:documento_id>/', views.editar_documento, name='editar_documento'),
    path('eliminar-documento/<int:documento_id>/', views.eliminar_documento, name='eliminar_documento'),
    path('compras/', views.compras, name='compras'),
    path('crear_compra/', views.crear_compra, name='crear_compra'),
    path('api/siguiente-codigo-animal/', views.api_siguiente_codigo_animal, name='api_siguiente_codigo_animal'),
    path('eliminar_compra/<int:compra_id>/', views.eliminar_compra, name='eliminar_compra'),
    path('cancelar_compra/', views.cancelar_compra, name='cancelar_compra'), 
    path('compra_pdf/<int:compra_id>/', views.compra_pdf, name='compra_pdf'),
    path('ventas/', views.ventas, name='ventas'),
    path('crear_venta/', views.crear_venta, name='crear_venta'),
    path('eliminar_venta/<int:venta_id>/', views.eliminar_venta, name='eliminar_venta'),
    path('detalle_venta/<int:venta_id>/', views.detalle_venta, name='detalle_venta'),
    path('cancelar_venta/', views.cancelar_venta, name='cancelar_venta'),
    path('descargar_venta/<int:venta_id>/', views.descargar_detalle_venta, name='descargar_venta'),
    path('contacto/', views.contacto, name='contacto'),
    path('registrar_contacto/', views.registrar_contacto, name='registrar_contacto'),
    path('editar-contacto/<int:id_cont>/', views.editar_contacto, name='editar_contacto'),
    path('eliminar-contacto/<int:id_cont>/', views.eliminar_contacto, name='eliminar_contacto'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)