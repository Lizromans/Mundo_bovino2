from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import User

# Create your models here.

class Administrador(models.Model):
    id_adm = models.AutoField(primary_key=True)
    nom_usu = models.CharField(unique=True, max_length=50)
    finca = models.CharField(max_length=500)
    correo = models.CharField(max_length=70)
    contraseña = models.CharField(max_length=128)
    confcontraseña = models.CharField(max_length=128)

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