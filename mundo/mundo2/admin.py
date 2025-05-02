from django.contrib import admin
from .models import Administrador, Animal, DetCom, Compra, DetVen, Venta, Contacto, Agenda, Documento

# Register your models here.
class AdministradorAdmin(admin.ModelAdmin):
    #DESPLEGAR LOS DATOS DE LA TABLA
    list_display = ("id_adm", "nom_usu", "correo", "finca", "contraseña", "confcontraseña")
admin.site.register(Administrador, AdministradorAdmin)

class AnimalAdmin(admin.ModelAdmin):
    list_display = ("id_ani", "edad", "peso", "raza", "estado", "id_adm")
admin.site.register(Animal, AnimalAdmin)

class DetComAdmin(admin.ModelAdmin):
    list_display = ("cod_detcom", "cod_com", "peso_anicom", "precio_uni")
admin.site.register(DetCom, DetComAdmin)

class CompraAdmin(admin.ModelAdmin):
    list_display = ("cod_com","nom_prov", "cantidad", "fecha", "precio_total", "id_adm")
admin.site.register(Compra, CompraAdmin)

class DetVenAdmin(admin.ModelAdmin):
    list_display = ("cod_detven", "cod_ven", "peso_aniven", "precio_uni")
admin.site.register(DetVen, DetVenAdmin)

class VentaAdmin(admin.ModelAdmin):
    list_display = ("cod_ven", "nom_cli","cantidad", "fecha", "precio_total", "id_adm")
admin.site.register(Venta, VentaAdmin)

class AgendaAdmin(admin.ModelAdmin):
    list_display = ("cod_age", "tipo", "descripcion", "fecha", "hora", "estado", "id_adm")
admin.site.register(Agenda, AgendaAdmin)

class ContactoAdmin(admin.ModelAdmin):
    list_display = ("id_cont", "cargo", "nombre", "correo", "telefono", "id_adm")
admin.site.register(Contacto, ContactoAdmin)

class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("num_doc", "titulo", "categoria", "fecha_doc", "id_adm")
admin.site.register(Documento, DocumentoAdmin)


