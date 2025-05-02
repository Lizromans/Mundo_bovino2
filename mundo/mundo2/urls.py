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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)