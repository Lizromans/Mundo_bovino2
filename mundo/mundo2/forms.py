from django import forms
from .models import Administrador
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.utils import timezone
import secrets
import datetime

class AdministradorRegistroForm(forms.ModelForm):
    class Meta:
        model = Administrador
        fields = ['nom_usu', 'correo', 'finca', 'contraseña', 'confcontraseña']
        widgets = {
            'nom_usu': forms.TextInput(attrs={'class': 'form-control', 'id': 'username'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'id': 'email'}),
            'finca': forms.TextInput(attrs={'class': 'form-control', 'id': 'finca'}),
            'contraseña': forms.PasswordInput(attrs={'class': 'form-control', 'id': 'password'}),
            'confcontraseña': forms.PasswordInput(attrs={'class': 'form-control', 'id': 'confirm-password'}),
        }
        labels = {
            'nom_usu': 'Nombre de Usuario',
            'correo': 'Email',
            'finca': 'Nombre de Finca',
            'contraseña': 'Contraseña',
            'confcontraseña': 'Confirmar Contraseña',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        contraseña = cleaned_data.get('contraseña')
        confcontraseña = cleaned_data.get('confcontraseña')
        
        if contraseña and confcontraseña and contraseña != confcontraseña:
            raise ValidationError("Las contraseñas no coinciden")
        
        return cleaned_data
    
    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if Administrador.objects.filter(correo=correo).exists():
            raise ValidationError("Este correo electrónico ya está registrado")
        return correo

    def clean_nom_usu(self):
        nom_usu = self.cleaned_data.get('nom_usu')
        if Administrador.objects.filter(nom_usu=nom_usu).exists():
            raise ValidationError("Este nombre de usuario ya está en uso")
        return nom_usu

    def clean_contraseña(self):
        contraseña = self.cleaned_data.get('contraseña')
        if len(contraseña) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")
        return contraseña
    
    def clean_finca(self):
        finca = self.cleaned_data.get('finca')
        if len(finca) < 2:
            raise ValidationError("El nombre de la finca debe tener al menos 2 caracteres")
        return finca
    
    def save(self, commit=True):
        administrador = super().save(commit=False)
        
        # No necesitamos hacer ninguna manipulación especial de las contraseñas aquí
        # porque el modelo ya se encarga de hashearlas en su método save()
        
        if commit:
            administrador.save()
        
        return administrador