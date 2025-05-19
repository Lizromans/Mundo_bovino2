from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User
import secrets
import datetime
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.utils import timezone

# Create your models here.

class Administrador(models.Model):
    id_adm = models.AutoField(primary_key=True)
    nom_usu = models.CharField(unique=True, max_length=50)
    finca = models.CharField(max_length=500)
    correo = models.CharField(max_length=70)
    token_verificacion = models.CharField(max_length=255, null=True, blank=True)
    token_expira = models.DateTimeField(null=True, blank=True)
    email_verificado = models.BooleanField(default=False)
    contraseña = models.CharField(max_length=128)
    confcontraseña = models.CharField(max_length=128)
    last_login = models.DateTimeField(null=True, blank=True)  

    class Meta:
        managed = False
        db_table = 'administrador'
    def save(self, *args, **kwargs):
    # Hash password if it's not already hashed
        if self.contraseña and not self.contraseña.startswith('pbkdf2_sha256$'):
            self.contraseña = make_password(self.contraseña)
        
        # Also hash confirmation password if present
        if self.confcontraseña and not self.confcontraseña.startswith('pbkdf2_sha256$'):
            self.confcontraseña = make_password(self.confcontraseña)
            
        super().save(*args, **kwargs)
    # Para compatibilidad con el sistema de autenticación de Django
    @property
    def password(self):
        return self.contraseña
        
    @password.setter
    def password(self, value):
        self.contraseña = value
    
    def get_email_field_name(self):
        return 'correo'
        
    def get_username(self):
        return self.nom_usu
        
    @property
    def is_anonymous(self):
        return False
        
    @property
    def is_authenticated(self):
        return True
        
    def get_full_name(self):
        return self.nom_usu
        
    def get_short_name(self):
        return self.nom_usu
    def generar_token_verificacion(self):
        # Crear un token aleatorio
        self.token_verificacion = secrets.token_urlsafe(32)
        # El token expirará en 24 horas
        self.token_expira = timezone.now() + datetime.timedelta(hours=24)
        self.save()
        
    def enviar_email_verificacion(self, request):
        """Envía un correo electrónico con el enlace de verificación"""
        verificacion_url = request.build_absolute_uri(
            reverse('verificar_email', kwargs={'token': self.token_verificacion})
        )
        
        asunto = 'Verifica tu dirección de correo electrónico'
        mensaje = f'''
        Hola {self.nom_usu},
        
        Gracias por registrarte. Por favor, haz clic en el siguiente enlace para verificar tu correo electrónico:
        
        {verificacion_url}
        
        Este enlace expirará en 24 horas.
        
        Si no solicitaste este registro, puedes ignorar este mensaje.
        '''
        
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [self.correo],
            fail_silently=False,
        )

class Agenda(models.Model):
    cod_age = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=220)
    descripcion = models.CharField(max_length=270)
    fecha = models.DateField()
    hora = models.TimeField()
    estado = models.CharField(max_length=245)
    id_adm = models.ForeignKey(Administrador, models.DO_NOTHING, db_column='id_adm')

    class Meta:
        managed = False
        db_table = 'agenda'


class Animal(models.Model):
    id_ani = models.AutoField(primary_key=True)  # ID global (sistema)
    cod_ani = models.IntegerField()  # ID específico por usuario
    fecha = models.DateField()
    edad = models.IntegerField()
    peso = models.FloatField()
    raza = models.CharField(max_length=45)
    estado = models.CharField(max_length=45)
    id_adm = models.ForeignKey(Administrador, models.DO_NOTHING, db_column='id_adm')

    class Meta:
        managed = False
        db_table = 'animal'
        unique_together = ('cod_ani', 'id_adm')  # Asegura unicidad por usuario


class Compra(models.Model):
    cod_com = models.IntegerField(primary_key=True)
    nom_prov = models.CharField(max_length=255)
    cantidad = models.IntegerField()
    fecha = models.DateField()
    precio_total = models.FloatField()
    id_adm = models.ForeignKey(Administrador, models.DO_NOTHING, db_column='id_adm')
    

    class Meta:
        managed = False
        db_table = 'compra'


class Contacto(models.Model):
    id_cont = models.AutoField(primary_key=True)
    cargo = models.CharField(max_length=245)
    nombre = models.CharField(max_length=250)
    correo = models.CharField(max_length=270)
    telefono = models.CharField(max_length=15)
    id_adm = models.ForeignKey(Administrador, models.DO_NOTHING, db_column='id_adm')

    class Meta:
        managed = False
        db_table = 'contacto'


class DetCom(models.Model):
    cod_detcom = models.AutoField(primary_key=True)
    cod_com= models.ForeignKey('Compra', models.DO_NOTHING, db_column='cod_com')
    cod_ani = models.IntegerField(255)
    edad_anicom = models.IntegerField(255)
    peso_anicom = models.FloatField(db_column='peso_aniCom')  # Field name made lowercase.
    precio_uni = models.FloatField()
    
    class Meta:
        managed = False
        db_table = 'det_com'

    def __str__(self):
        return f"Detalle de Compra {self.cod_com.cod_com} - Animal {self.cod_ani}"

class DetVen(models.Model):
    cod_detven = models.AutoField(primary_key=True)
    cod_ven = models.ForeignKey('Venta', models.DO_NOTHING, db_column='cod_ven')
    cod_ani = models.IntegerField(255)
    edad_aniven = models.IntegerField()  # Field name made lowercase.
    peso_aniven = models.FloatField()  # Field name made lowercase.
    precio_uni = models.FloatField()

    class Meta:
        managed = False
        db_table = 'det_ven'


class Documento(models.Model):
    num_doc = models.AutoField(primary_key=True)
    archivo = models.FileField(upload_to='documentos/', null=True)
    titulo = models.CharField(max_length=250)
    categoria = models.CharField(max_length=245)
    fecha_doc = models.DateField()
    id_adm = models.ForeignKey(Administrador, models.DO_NOTHING, db_column='id_adm')

    class Meta:
        managed = False
        db_table = 'documento'
        
    def es_pdf(self):
        if self.archivo and hasattr(self.archivo, 'name'):
            return self.archivo.name.lower().endswith('.pdf')
        return False


class Venta(models.Model):
    cod_ven = models.IntegerField(primary_key=True)
    nom_cli = models.CharField(max_length=255)
    cantidad = models.IntegerField()
    fecha = models.DateField()
    precio_total = models.FloatField()
    id_adm = models.ForeignKey(Administrador, models.DO_NOTHING, db_column='id_adm')
    

    class Meta:
        managed = False
        db_table = 'venta'