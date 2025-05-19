from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from .forms import AdministradorRegistroForm
from .models import Administrador, Agenda, Animal, Documento, Compra, DetCom, Venta, DetVen, Contacto
from django.db import connection
from functools import wraps
from datetime import date, datetime, timedelta
from django.utils import timezone  # Importación correcta para timezone
import calendar, re
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


# Create your views here.
def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')

def preguntasfrecuentes(request):
    return render(request, 'paginas/faq.html')

"vistas para registro e inicio de sesión"
def registro(request):
    # Reiniciar AUTO_INCREMENT si es necesario
    with connection.cursor() as cursor:
        table_administrador = Administrador._meta.db_table
        cursor.execute(f"ALTER TABLE {table_administrador} AUTO_INCREMENT = 1;")
    
    if request.method == 'POST':
        form = AdministradorRegistroForm(request.POST)
        
        if form.is_valid():
            try:
                # Guardar el administrador con ambas contraseñas pero como no verificado
                administrador = form.save(commit=False)
                administrador.email_verificado = False
                administrador.save()
                
                # Generar token de verificación y enviar correo
                administrador.generar_token_verificacion()
                administrador.enviar_email_verificacion(request)
                
                messages.success(
                    request, 
                    "¡Registro exitoso! Por favor, verifica tu correo electrónico para activar tu cuenta."
                )
                return redirect('iniciarsesion')
            except Exception as e:
                # Si hay error al guardar, mostrarlo
                messages.error(request, f"Error al registrar usuario: {str(e)}")
        else:
            # Si el formulario tiene errores, se mostrará con los errores
            pass
    else:
        form = AdministradorRegistroForm()
    
    return render(request, 'paginas/registro.html', {
        'form': form,
        'current_page_name': 'Registro'
    })

# Vista para verificar el correo electrónico
def verificar_email(request, token):
    try:
        # Buscar el administrador con este token
        administrador = Administrador.objects.get(token_verificacion=token)
        
        # Verificar si el token ha expirado
        if administrador.token_expira and administrador.token_expira < timezone.now():
            messages.error(request, "El enlace de verificación ha expirado. Por favor, solicita uno nuevo.")
            return redirect('iniciarsesion')
        
        # Marcar como verificado
        administrador.email_verificado = True
        administrador.token_verificacion = None
        administrador.token_expira = None
        administrador.save()
        
        messages.success(request, "¡Tu correo electrónico ha sido verificado correctamente! Ahora puedes iniciar sesión.")
        return redirect('iniciarsesion')
        
    except Administrador.DoesNotExist:
        messages.error(request, "El enlace de verificación no es válido.")
        return redirect('iniciarsesion') 

def iniciarsesion(request):
    error_user = None
    error_password = None
    
    if request.method == 'POST':
        usuario = request.POST.get('username')
        contraseña = request.POST.get('password')
        
        # Formulario de validación
        if not usuario:
            error_user = 'El nombre de usuario es obligatorio'
        if not contraseña:
            error_password = 'La contraseña es obligatoria'
            
        if error_user or error_password:
            return render(request, 'paginas/iniciarsesion.html', {
                'error_user': error_user,
                'error_password': error_password,
                'current_page_name': 'Iniciar Sesión'
            })
        
        try:
            admin = Administrador.objects.get(nom_usu=usuario)
            
            if check_password(contraseña, admin.contraseña):
                request.session['usuario_id'] = admin.id_adm
                request.session['nom_usu'] = admin.nom_usu
                request.session['finca'] = admin.finca
                
                if request.POST.get('recordar'):
                    request.session.set_expiry(1209600)  # 2 semanas
                else:
                    request.session.set_expiry(0)  # no recordar
                    
                messages.success(request, f"¡Bienvenido {admin.nom_usu}!")
                return redirect('home')
            else:
                error_password = 'Contraseña incorrecta'
        except Administrador.DoesNotExist:
            error_user = 'Usuario no encontrado'
        except Exception as e:
            print(f"Error durante inicio de sesión: {e}")
            messages.error(request, "Error de conexión. Intente más tarde.")
    
    return render(request, 'paginas/iniciarsesion.html', {
        'error_user': error_user,
        'error_password': error_password,
        'current_page_name': 'Iniciar Sesión'
    })

def mostrar_recuperar_contrasena(request):
    """
    Esta vista simplemente muestra la misma plantilla de inicio de sesión
    pero con el modal de recuperación de contraseña visible
    """
    return render(request, 'paginas/iniciarsesion.html', {
        'mostrar_modal': True,
        'current_page_name': 'Recuperar Contraseña'
    })

def recuperar_contrasena(request):
    """
    Esta vista procesa el formulario de recuperación de contraseña
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return render(request, 'paginas/iniciarsesion.html', {
                'mostrar_modal': True,
                'email_error': 'El correo electrónico es obligatorio',
                'current_page_name': 'Recuperar Contraseña'
            })
        
        try:
            # Verificar si existe un administrador con ese correo
            admin = Administrador.objects.filter(correo=email).first()
            
            if admin:
                # Generar el token y el uid codificado para el enlace de restablecimiento
                uid = urlsafe_base64_encode(force_bytes(admin.pk))
                token = default_token_generator.make_token(admin)
                
                # Construir el enlace de restablecimiento
                reset_link = f"{request.scheme}://{request.get_host()}/reset-password/{uid}/{token}/"
                
                try:
                    # Preparar y enviar el correo
                    subject = "Restablecimiento de contraseña - Mundo Bovino"
                    message = render_to_string('paginas/reset_password_email.html', {
                        'user': admin,
                        'reset_link': reset_link,
                        'site_name': 'Mundo Bovino'
                    })
                    
                    # Cambiado fail_silently a False para que muestre errores
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [admin.correo],
                        html_message=message,
                        fail_silently=False
                    )
                    print(f"Correo enviado exitosamente a {admin.correo}")
                except Exception as email_error:
                    print(f"Error al enviar correo: {email_error}")
                    # Ahora mostramos el error al usuario para facilitar la depuración
                    messages.error(request, f"Problema al enviar el correo: {email_error}")
                    return redirect('iniciarsesion')
                
            # Por seguridad, mostramos un mensaje genérico independientemente de si el correo existe o no
            messages.success(request, "Si el correo está asociado a una cuenta, recibirás instrucciones para restablecer tu contraseña.")
            return redirect('iniciarsesion')
            
        except Exception as e:
            print(f"Error durante recuperación de contraseña: {e}")
            messages.error(request, f"{str(e)}")
            return redirect('iniciarsesion')
    
    # Si no es POST, redirigir a la página de inicio de sesión
    return redirect('iniciarsesion')

def reset_password(request, uidb64, token):
    """
    Vista para mostrar el formulario de restablecimiento de contraseña
    cuando el usuario hace clic en el enlace del correo
    """
    try:
        # Decodificar el uid para obtener el ID del usuario
        uid = force_str(urlsafe_base64_decode(uidb64))
        admin = Administrador.objects.get(pk=uid)
        
        # Verificar que el token sea válido
        if default_token_generator.check_token(admin, token):
            print(f"Token válido para el usuario: {admin.nom_usu}")
            return render(request, 'paginas/reset_password.html', {
                'valid': True,
                'uidb64': uidb64,
                'token': token,
                'current_page_name': 'Restablecer Contraseña'
            })
        else:
            print("Token inválido o expirado")
            messages.error(request, "El enlace de restablecimiento no es válido o ha expirado.")
            return redirect('iniciarsesion')
            
    except Exception as e:
        print(f"Error en reset_password: {e}")
        messages.error(request, f"Error al procesar el enlace de restablecimiento: {e}")
        return redirect('iniciarsesion')
    
def reset_password_confirm(request):
    """
    Vista para procesar el formulario de restablecimiento de contraseña
    """
    if request.method == 'POST':
        uidb64 = request.POST.get('uidb64')
        token = request.POST.get('token')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validar que ambas contraseñas coincidan
        if password1 != password2:
            return render(request, 'paginas/reset_password.html', {
                'valid': True,
                'uidb64': uidb64,
                'token': token,
                'error': 'Las contraseñas no coinciden',
                'current_page_name': 'Restablecer Contraseña'
            })
        
        try:
            # Decodificar el uid para obtener el ID del usuario
            uid = force_str(urlsafe_base64_decode(uidb64))
            admin = Administrador.objects.get(pk=uid)
            
            # Verificar que el token sea válido
            if default_token_generator.check_token(admin, token):
                # Cambiar la contraseña usando el nombre correcto del campo (contraseña con ñ)
                admin.contraseña = make_password(password1)
                admin.confcontraseña = make_password(password1)  # Actualizar también la confirmación
                admin.save()
                
                messages.success(request, "Tu contraseña ha sido restablecida con éxito. Ahora puedes iniciar sesión.")
                return redirect('iniciarsesion')
            else:
                messages.error(request, "El enlace de restablecimiento no es válido o ha expirado.")
                return redirect('iniciarsesion')
                
        except (TypeError, ValueError, OverflowError, Administrador.DoesNotExist):
            messages.error(request, "El enlace de restablecimiento no es válido.")
            return redirect('iniciarsesion')
    
    # Si no es POST, redirigir a la página de inicio de sesión
    return redirect('iniciarsesion')

def login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'session') or 'usuario_id' not in request.session:
            messages.error(request, "Debes iniciar sesión primero")
            return redirect('iniciarsesion')
        
        # Incluir información de recordatorios en todas las vistas
        usuario_id = request.session.get('usuario_id')
        recordatorios = obtener_recordatorios(usuario_id)
        
        # Contar recordatorios regulares
        hay_recordatorios_regulares = any(len(eventos) > 0 for periodo, eventos in recordatorios.items() if periodo != 'vacunacion')
        total_recordatorios_regulares = sum(len(eventos) for periodo, eventos in recordatorios.items() if periodo != 'vacunacion')
        
        # Contar recordatorios de vacunación
        hay_recordatorios_vacunacion = len(recordatorios.get('vacunacion', [])) > 0
        total_recordatorios_vacunacion = len(recordatorios.get('vacunacion', []))
        
        # Total general
        hay_recordatorios = hay_recordatorios_regulares or hay_recordatorios_vacunacion
        total_recordatorios = total_recordatorios_regulares + total_recordatorios_vacunacion
        
        # Agregar datos de recordatorios a request para acceder en la vista
        request.recordatorios = recordatorios
        request.hay_recordatorios = hay_recordatorios
        request.total_recordatorios = total_recordatorios
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

"Vistas para home y configuraciones"
@login_required
def home(request):
    context = {
        'current_page_name': 'Home',
        'recordatorios': request.recordatorios,
        'hay_recordatorios': request.hay_recordatorios,
        'total_recordatorios': request.total_recordatorios
    }
    return render(request, 'paginas/home.html', context)

@login_required
def configuraciones(request):
    usuario_id = request.session.get('usuario_id')
    
    try:
        admin = Administrador.objects.get(pk=usuario_id)
        
        if request.method == 'POST':
            admin.nom_usu = request.POST.get('nom_usu', admin.nom_usu)
            admin.correo = request.POST.get('email', admin.correo)
            admin.save()
            
            request.session['modulo_inventario'] = 'inventario' in request.POST
            request.session['modulo_ventas'] = 'registroVentas' in request.POST
            request.session['modulo_calendario'] = 'calendario' in request.POST
            request.session['modulo_documentos'] = 'documentos' in request.POST
            request.session['modulo_agenda'] = 'contactos' in request.POST
            
            messages.success(request, "¡Cambios guardados correctamente!")
            return redirect('configuraciones')
        
        perfil = {
            'modulo_inventario': request.session.get('modulo_inventario', True),
            'modulo_ventas': request.session.get('modulo_ventas', True),
            'modulo_calendario': request.session.get('modulo_calendario', True),
            'modulo_documentos': request.session.get('modulo_documentos', True),
            'modulo_agenda': request.session.get('modulo_agenda', True)
        }
        
        return render(request, 'paginas/configuraciones.html', {
            'admin': admin,
            'perfil': perfil,
            'current_page': 'configuraciones',
            'current_page_name': 'Configuraciones'
        })
        
    except Administrador.DoesNotExist:
        messages.error(request, "Usuario no encontrado. Por favor inicie sesión nuevamente.")
        return redirect('iniciarsesion')
    except Exception as e:
        messages.error(request, f"Error al cargar la configuración: {str(e)}")
        return redirect('home')

@login_required
def notificaciones(request):
    notif_settings = {
        'notif_email': request.session.get('notif_email', False),
        'notif_push': request.session.get('notif_push', False),
        'notif_modulos': request.session.get('notif_modulos', True),
        'notif_inventario': request.session.get('notif_inventario', True),
        'notif_ventas': request.session.get('notif_ventas', True),
        'notif_calendario': request.session.get('notif_calendario', True),
        'notif_documentos': request.session.get('notif_documentos', True),
        'notif_agenda': request.session.get('notif_agenda', True),
    }
    
    if request.method == 'POST':
        notif_settings['notif_email'] = 'notif_email' in request.POST
        notif_settings['notif_push'] = 'notif_push' in request.POST
        notif_settings['notif_modulos'] = 'notif_modulos' in request.POST
        
        if notif_settings['notif_modulos']:
            notif_settings['notif_inventario'] = 'notif_inventario' in request.POST
            notif_settings['notif_ventas'] = 'notif_ventas' in request.POST
            notif_settings['notif_calendario'] = 'notif_calendario' in request.POST
            notif_settings['notif_documentos'] = 'notif_documentos' in request.POST
            notif_settings['notif_agenda'] = 'notif_agenda' in request.POST
        else:
            notif_settings['notif_inventario'] = False
            notif_settings['notif_ventas'] = False
            notif_settings['notif_calendario'] = False
            notif_settings['notif_documentos'] = False
            notif_settings['notif_agenda'] = False
        
        for key, value in notif_settings.items():
            request.session[key] = value
        
        messages.success(request, "Preferencias de notificaciones actualizadas correctamente")
        return redirect('notificaciones')
    
    context = {
        'current_page': 'notificaciones',
        'current_page_name': 'Notificaciones',
        **notif_settings
    }
    
    return render(request, 'paginas/notificaciones.html', context)

@login_required
def privacidad(request):
    usuario_id = request.session.get('usuario_id')
    
    try:
        admin = Administrador.objects.get(pk=usuario_id)
        
        if request.method == 'POST':
            contraseña_actual = request.POST.get('contraseña_actual')
            nueva_contraseña = request.POST.get('nueva_contraseña')
            confirmar_contraseña = request.POST.get('confirmar_contraseña')
            
            if not check_password(contraseña_actual, admin.contraseña):
                messages.error(request, "La contraseña actual es incorrecta")
                return redirect('privacidad')
            
            if nueva_contraseña != confirmar_contraseña:
                messages.error(request, "Las contraseñas no coinciden")
                return redirect('privacidad')
            
            if len(nueva_contraseña) < 8:
                messages.error(request, "La contraseña debe tener al menos 8 caracteres")
                return redirect('privacidad')
            
            admin.contraseña = make_password(nueva_contraseña)
            admin.save()
            
            messages.success(request, "Contraseña actualizada correctamente")
            return redirect('configuraciones')
            
    except Administrador.DoesNotExist:
        messages.error(request, "Usuario no encontrado. Por favor inicie sesión nuevamente")
        return redirect('iniciarsesion')
    except Exception as e:
        messages.error(request, f"Error al actualizar la contraseña: {str(e)}")
        return redirect('privacidad')
    
    return render(request, 'paginas/privacidad.html', {
        'current_page': 'privacidad',
        'current_page_name': 'Privacidad'
    })

"Vistas para crud de animales"
@login_required
def inventario(request):
    # Obtener el ID del administrador actual desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    # Iniciar con todos los animales del administrador
    animales = Animal.objects.filter(id_adm=usuario_id)
    
    # Obtener parámetros de búsqueda y filtrado
    busqueda = request.GET.get('busqueda', '')
    tipo_filtro = request.GET.get('tipo_filtro', '')
    valor_filtro = request.GET.get('valor', '')
    
    # Variable para almacenar el tipo de búsqueda detectado
    tipo_busqueda = None
    
    # Aplicar filtros de búsqueda si existe un término
    if busqueda:
        from django.db.models import Q
        import re
        
        # 1. Verificar si la búsqueda es un código de animal (formato numérico)
        if re.match(r'^\d+$', busqueda) and len(busqueda) <= 5:  # Asumiendo que códigos son números menores a 99999
            # Búsqueda exacta por código de animal
            animales = animales.filter(cod_ani=int(busqueda))
            tipo_busqueda = "codigo"
        
        # 2. Verificar si la búsqueda es una fecha (formato yyyy-mm-dd o dd/mm/yyyy)
        elif re.match(r'^(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})$', busqueda):
            # Convertir formato dd/mm/yyyy a yyyy-mm-dd si es necesario
            if '/' in busqueda:
                day, month, year = busqueda.split('/')
                busqueda_fecha = f"{year}-{month}-{day}"
            else:
                busqueda_fecha = busqueda
                
            # Filtrar por fecha de ingreso
            animales = animales.filter(fecha=busqueda_fecha)
            tipo_busqueda = "fecha"
        
        # 3. Verificar si la búsqueda es una edad (número seguido de "años" o solo número)
        elif re.match(r'^\d+(\s*años)?$', busqueda):
            # Extraer solo el número
            edad = re.match(r'^(\d+)', busqueda).group(1)
            # Filtrar por edad
            animales = animales.filter(edad=int(edad))
            tipo_busqueda = "edad"
        
        # 4. Para cualquier otro caso, considerar como búsqueda de texto
        else:
            # Buscar solo en campos de texto
            animales = animales.filter(
                Q(raza__icontains=busqueda) |
                Q(estado__icontains=busqueda)
            )
            tipo_busqueda = "texto"
    
    # Aplicar filtro por estado o edad si se ha seleccionado
    if tipo_filtro == 'Estado' and valor_filtro:
        animales = animales.filter(estado=valor_filtro)
    elif tipo_filtro == 'Edad' and valor_filtro:
        animales = animales.filter(edad=valor_filtro)
    
    # Determinar el siguiente código de animal para este administrador
    proximo_codigo = 1
    ultimo_animal = Animal.objects.filter(id_adm=usuario_id).order_by('-cod_ani').first()
    if ultimo_animal:
        proximo_codigo = ultimo_animal.cod_ani + 1
    
    return render(request, "paginas/inventario.html", {
        "proximo_codigo": proximo_codigo,
        "animales": animales,
        "current_page_name": "Inventario",
        "busqueda": busqueda,
        "tipo_filtro": tipo_filtro,
        "valor_filtro": valor_filtro,
        "tipo_busqueda": tipo_busqueda,  # Pasar el tipo de búsqueda detectado a la plantilla
        'recordatorios': request.recordatorios,
        'hay_recordatorios': request.hay_recordatorios,
        'total_recordatorios': request.total_recordatorios
    })

@login_required
def registrar_animal(request):
    if request.method == "POST":
        # Obtener el ID del administrador actual desde la sesión
        usuario_id = request.session.get('usuario_id')
        
        try:
            # Obtener la instancia del administrador usando el ID
            administrador = Administrador.objects.get(pk=usuario_id)
            
            # Determinar el siguiente código de animal para este administrador específico
            ultimo_animal = Animal.objects.filter(id_adm=usuario_id).order_by('-cod_ani').first()
            siguiente_cod_ani = 1  # Código inicial para nuevos usuarios
            
            if ultimo_animal:
                siguiente_cod_ani = ultimo_animal.cod_ani + 1
            
            # Obtener datos del formulario
            fecha_str = request.POST.get("fecha")
            # Convertir a objeto datetime completo
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d')  # o el formato que uses
            edad = int(request.POST.get("edad"))
            peso = float(request.POST.get("peso"))
            raza = request.POST.get("raza")
            estado = request.POST.get("estado")
            
            # Crear y guardar el nuevo animal
            nuevo_animal = Animal(
                cod_ani=siguiente_cod_ani,
                fecha=fecha,  # Aquí usamos el objeto datetime completo
                edad=edad,
                peso=peso,
                raza=raza,
                estado=estado,
                id_adm=administrador
            )
            nuevo_animal.save()
            
            messages.success(request, f"¡Animal #{siguiente_cod_ani} registrado con éxito!")
            
        except Administrador.DoesNotExist:
            messages.error(request, "Error: No se pudo encontrar el administrador.")
        except ValueError:
            messages.error(request, "Error: Valores inválidos en el formulario. Verifica los datos ingresados.")
        except Exception as e:
            messages.error(request, f"Error al registrar el animal: {str(e)}")
        
        return redirect('inventario')
    
    return redirect('inventario')

@login_required
def eliminar_animal(request, animal_id):
    if request.method == "POST":
        # Obtener el ID del administrador actual desde la sesión
        usuario_id = request.session.get('usuario_id')
        
        try:
            # Obtener el animal asegurándose que pertenezca al administrador actual
            animal = get_object_or_404(Animal, cod_ani=animal_id, id_adm=usuario_id)
            
            # Guardar el código del animal para el mensaje
            codigo_animal = animal.cod_ani
            
            # Eliminar el animal
            animal.delete()
            
            messages.success(request, f"Animal #{codigo_animal} eliminado con éxito!")
            
        except Animal.DoesNotExist:
            messages.error(request, "Error: No se encontró el animal.")
        except Exception as e:
            messages.error(request, f"Error al eliminar el animal: {str(e)}")
        
        return redirect('inventario')
    
    # Si no es un POST, redirigir al inventario
    return redirect('inventario')

@login_required
def editar_animal(request, animal_id):
    # Obtener el ID del administrador actual desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    try:
        # Obtener el animal asegurándose que pertenezca al administrador actual
        animal = get_object_or_404(Animal, cod_ani=animal_id, id_adm=usuario_id)
        
        if request.method == "POST":
            # Procesar el formulario de edición
            try:
                # Obtener datos del formulario
                fecha_str = request.POST.get("fecha")
                # Convertir a objeto datetime
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
                edad = int(request.POST.get("edad"))
                peso = float(request.POST.get("peso"))
                raza = request.POST.get("raza")
                estado = request.POST.get("estado")
                
                # Actualizar los campos del animal
                animal.fecha = fecha
                animal.edad = edad
                animal.peso = peso
                animal.raza = raza
                animal.estado = estado
                
                # Guardar los cambios
                animal.save()
                
                messages.success(request, f"¡Animal #{animal_id} actualizado con éxito!")
                return redirect('inventario')
                
            except ValueError:
                messages.error(request, "Error: Valores inválidos en el formulario. Verifica los datos ingresados.")
            except Exception as e:
                messages.error(request, f"Error al actualizar el animal: {str(e)}")
        
        # Si es GET o hubo error en POST, mostrar el formulario de edición
        return render(request, "paginas/inventario.html", {
            "animal": animal,
            "current_page_name": "Editar Animal"
        })
        
    except Animal.DoesNotExist:
        messages.error(request, "Error: No se encontró el animal.")
        return redirect('inventario')

@login_required
def cancelar_animal(request):
    
    if request.method == 'POST':
        messages.info(request, "Registro de animal cancelado")
        return redirect('inventario')
    else:
        return redirect('inventario')
    
"Vistas para crud de agenda"
@login_required
def calendario(request):
    usuario_id = request.session.get('usuario_id')
    
    # Obtener todos los eventos del administrador actual
    eventos = Agenda.objects.filter(id_adm=usuario_id)
    
    # Obtener recordatorios para eventos próximos
    recordatorios = obtener_recordatorios(usuario_id)
    
    # Comprobar si hay recordatorios para mostrar notificación en la UI
    hay_recordatorios = any(len(eventos) > 0 for eventos in recordatorios.values())
    
    # Contar total de recordatorios
    total_recordatorios = sum(len(eventos) for eventos in recordatorios.values())
    
    # Procesar filtros y búsquedas
    tipo_filtro = request.GET.get('tipo_filtro')
    busqueda = request.GET.get('busqueda')
    
    # Aplicar filtros si están presentes
    resultados_busqueda = None
    if busqueda or tipo_filtro:
        # Crear queryset base para la búsqueda
        resultados = eventos
        
        # Aplicar filtro por tipo o estado solo si se proporciona un filtro
        if tipo_filtro:
            if tipo_filtro in ['Evento', 'Tarea']:  # Filtrar por tipo
                resultados = resultados.filter(tipo=tipo_filtro)
            elif tipo_filtro in ['Pendiente', 'Reprogramada', 'Cancelada', 'Realizada']:  # Filtrar por estado
                resultados = resultados.filter(estado=tipo_filtro)
            # Si el tipo_filtro es "Todos" o un valor no reconocido, no aplicamos ningún filtro adicional
        
        # Aplicar filtro por búsqueda en descripción
        if busqueda:
            resultados = resultados.filter(descripcion__icontains=busqueda)
        
        resultados_busqueda = resultados
    
    # Obtener el evento seleccionado si se proporciona un ID
    evento_seleccionado = None
    evento_id = request.GET.get('evento')
    if evento_id:
        try:
            evento_seleccionado = Agenda.objects.get(pk=evento_id, id_adm=usuario_id)
        except Agenda.DoesNotExist:
            pass
    
    # Obtener fecha actual y construir calendario
    fecha_actual = date.today()
    mes_actual = fecha_actual.month
    año_actual = fecha_actual.year
    
    # Permitir navegación entre meses
    mes_param = request.GET.get('month')
    if mes_param:
        try:
            mes, año = map(int, mes_param.split('-'))
            if 1 <= mes <= 12:
                mes_actual = mes
                año_actual = año
        except:
            pass
    
    # Calcular meses anterior y siguiente para navegación
    if mes_actual == 1:
        mes_anterior = f"12-{año_actual-1}"
    else:
        mes_anterior = f"{mes_actual-1}-{año_actual}"
        
    if mes_actual == 12:
        mes_siguiente = f"1-{año_actual+1}"
    else:
        mes_siguiente = f"{mes_actual+1}-{año_actual}"
    
    # Construir calendario
    cal = calendar.monthcalendar(año_actual, mes_actual)
    
    # Mapear eventos a días específicos con su tipo
    eventos_por_dia = {}
    for evento in eventos:
        if evento.fecha.year == año_actual and evento.fecha.month == mes_actual:
            if evento.fecha.day not in eventos_por_dia:
                eventos_por_dia[evento.fecha.day] = {'ids': [], 'tipos': []}
            eventos_por_dia[evento.fecha.day]['ids'].append(evento.cod_age)
            eventos_por_dia[evento.fecha.day]['tipos'].append(evento.tipo)
    
    # Obtener el día seleccionado para mostrar el formulario o eventos
    dia_seleccionado = request.GET.get('dia')
    mes_seleccionado = request.GET.get('mes')
    año_seleccionado = request.GET.get('año')
    
    fecha_seleccionada = None
    mostrar_formulario = False
    if dia_seleccionado and mes_seleccionado and año_seleccionado:
        try:
            fecha_seleccionada = date(int(año_seleccionado), int(mes_seleccionado), int(dia_seleccionado))
            
            # Verificar si ya hay eventos en este día
            eventos_del_dia_count = Agenda.objects.filter(
                id_adm=usuario_id,
                fecha=fecha_seleccionada
            ).count()
            
            # Mostrar formulario solo si no hay eventos en el día seleccionado
            # y no se ha seleccionado un evento específico
            mostrar_formulario = eventos_del_dia_count == 0 and not evento_seleccionado
            
        except ValueError:
            fecha_seleccionada = None
    
    # Construir matriz del calendario con información de eventos
    calendario_mensual = []
    for semana in cal:
        semana_formateada = []
        for dia in semana:
            if dia == 0:
                # Espacio vacío para días fuera del mes
                semana_formateada.append(None)
            else:
                fecha_dia = date(año_actual, mes_actual, dia)
                datos_dia = eventos_por_dia.get(dia, {'ids': [], 'tipos': []})
                tiene_evento = len(datos_dia['ids']) > 0
                
                # Determinar tipo de evento para el indicador visual
                tipo_evento = None
                tiene_evento_completado = False
                if tiene_evento:
                    # Verificar si hay eventos realizados
                    eventos_dia = Agenda.objects.filter(
                        id_adm=usuario_id,
                        fecha=fecha_dia
                    )
                    for ev in eventos_dia:
                        if ev.estado == 'Realizada':
                            tiene_evento_completado = True
                            break
                            
                    # Si hay varios tipos de eventos en el mismo día
                    if 'Evento' in datos_dia['tipos'] and 'Tarea' in datos_dia['tipos']:
                        if tiene_evento_completado:
                            tipo_evento = 'multiple-realizado'
                        else:
                            tipo_evento = 'multiple'
                    elif 'Evento' in datos_dia['tipos']:
                        if tiene_evento_completado:
                            tipo_evento = 'realizado'
                        else:
                            tipo_evento = 'Evento'
                    elif 'Tarea' in datos_dia['tipos']:
                        if tiene_evento_completado:
                            tipo_evento = 'realizado'
                        else:
                            tipo_evento = 'Tarea'
                
                semana_formateada.append({
                    'fecha': fecha_dia,
                    'tiene_evento': tiene_evento,
                    'evento_ids': datos_dia['ids'],
                    'tipo_evento': tipo_evento,
                    'tiene_evento_completado': tiene_evento_completado
                })
        calendario_mensual.append(semana_formateada)
    
    # Obtener eventos del día seleccionado para mostrar en panel lateral
    eventos_del_dia = None
    if fecha_seleccionada and not evento_seleccionado:
        eventos_del_dia = Agenda.objects.filter(
            id_adm=usuario_id,
            fecha=fecha_seleccionada
        )
    
    # Nombres de los meses en español para mostrar en el calendario
    nombres_meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    return render(request, 'paginas/calendario.html', {
        'current_page_name': 'Calendario',
        'eventos': eventos,
        'evento_seleccionado': evento_seleccionado,
        'eventos_del_dia': eventos_del_dia,
        'fecha_actual': fecha_actual,
        'fecha_seleccionada': fecha_seleccionada,
        'mostrar_formulario': mostrar_formulario,
        'nombre_mes': nombres_meses[mes_actual],
        'año_actual': año_actual,
        'calendario_mensual': calendario_mensual,
        'mes_anterior': mes_anterior,
        'mes_siguiente': mes_siguiente,
        'resultados_busqueda': resultados_busqueda,
        'busqueda': busqueda,
        'tipo_filtro': tipo_filtro,
        'recordatorios': recordatorios,
        'hay_recordatorios': hay_recordatorios,
        'total_recordatorios': total_recordatorios
    })

@login_required
def agregar_evento(request):
    if request.method == 'POST':
        # Obtener el ID del administrador actual
        usuario_id = request.session.get('usuario_id')
        
        try:
            # Obtener la instancia del administrador
            administrador = Administrador.objects.get(pk=usuario_id)
            
            # Procesar los datos del formulario
            fecha = request.POST.get('fecha')
            hora = request.POST.get('hora')
            tipo = request.POST.get('tipo')
            estado = request.POST.get('estado')
            descripcion = request.POST.get('descripcion')
            
            # Crear y guardar el nuevo evento
            nuevo_evento = Agenda(
                fecha=fecha,
                hora=hora,
                tipo=tipo,
                estado=estado,
                descripcion=descripcion,
                id_adm=administrador  # Asignar el administrador al evento
            )
            nuevo_evento.save()
            
            # Obtener los parámetros para redirección
            redirect_dia = request.POST.get('redirect_fecha')
            redirect_mes = request.POST.get('redirect_mes')
            redirect_año = request.POST.get('redirect_año')
            
            # Crear mensaje de éxito
            messages.success(request, f'Se ha agregado un nuevo {tipo.lower()} correctamente.')
            
            # Redireccionar a la página del calendario con el día seleccionado
            return redirect(f'/calendario/?dia={redirect_dia}&mes={redirect_mes}&año={redirect_año}&evento={nuevo_evento.cod_age}')
        
        except Administrador.DoesNotExist:
            messages.error(request, "Error: No se pudo encontrar el administrador.")
        except Exception as e:
            messages.error(request, f"Error al agregar el evento: {str(e)}")
            
    # Si no es POST o hubo un error, redireccionar al calendario
    return redirect('calendario')

@login_required
def editar_evento(request, evento_id):
    evento = get_object_or_404(Agenda, cod_age=evento_id)
    
    if request.method == 'POST':
        # Actualizar los campos del evento
        evento.fecha = request.POST.get('fecha')
        evento.hora = request.POST.get('hora')
        evento.tipo = request.POST.get('tipo')
        evento.estado = request.POST.get('estado')
        evento.descripcion = request.POST.get('descripcion')
        evento.save()
        
        messages.success(request, 'Evento actualizado exitosamente.')
        
        # Redirigir a la fecha correcta en el calendario
        redirect_fecha = request.POST.get('redirect_fecha')
        redirect_mes = request.POST.get('redirect_mes')
        redirect_año = request.POST.get('redirect_año')
        
        if redirect_fecha and redirect_mes and redirect_año:
            return redirect(f'/calendario/?dia={redirect_fecha}&mes={redirect_mes}&año={redirect_año}')
        
        return redirect('calendario')
    
    # Si no es POST, redirigir a la vista del calendario
    return redirect('calendario')

@login_required
def eliminar_evento(request, evento_id):
    if request.method == "POST":
        # Obtener el ID del administrador actual desde la sesión
        usuario_id = request.session.get('usuario_id')
        
        try:
            # Obtener el evento/tarea asegurándose que pertenezca al administrador actual
            evento = get_object_or_404(Agenda, cod_age=evento_id, id_adm=usuario_id)
            
            # Guardar el tipo para el mensaje
            tipo = evento.tipo  # Guarda el tipo antes de eliminar
            
            # Eliminar el evento
            evento.delete()
            
            messages.success(request, f"{tipo} eliminado con éxito!")
            
        except Agenda.DoesNotExist:
            messages.error(request, "Error: No se encontró el evento o tarea.")
        except Exception as e:
            messages.error(request, f"Error al eliminar: {str(e)}")
        
        return redirect('calendario')
    
    # Si no es un POST, redirigir al calendario
    return redirect('calendario')

"vistas para recordatorios"
def obtener_recordatorios(usuario_id):
    # Verificar que usuario_id sea válido
    if usuario_id is None:
        return {
            'siete_dias': [],
            'cuatro_dias': [],
            'dos_dias': [],
            'un_dia': [],
            'hoy': [],
            'vacunacion': []  # Nueva categoría para recordatorios de vacunación
        }
    
    # Fecha actual
    hoy = date.today()
    
    # Fechas para recordatorios (7, 4, 2, 1 día adelante y hoy)
    fechas_recordatorio = {
        'siete_dias': hoy + timedelta(days=7),
        'cuatro_dias': hoy + timedelta(days=4),
        'dos_dias': hoy + timedelta(days=2),
        'un_dia': hoy + timedelta(days=1),
        'hoy': hoy
    }
    
    # Inicializar diccionario de recordatorios
    recordatorios = {
        'siete_dias': [],
        'cuatro_dias': [],
        'dos_dias': [],
        'un_dia': [],
        'hoy': [],
        'vacunacion': []  # Nueva categoría para recordatorios de vacunación
    }
    
    try:
        # Buscar eventos para cada fecha de recordatorio que tengan estado 'Pendiente'
        for periodo, fecha in fechas_recordatorio.items():
            eventos = Agenda.objects.filter(
                id_adm=usuario_id,
                fecha=fecha,
                estado='Pendiente'  # Solo eventos con estado pendiente
            )
            
            # Formatear los datos para mostrarlos en las notificaciones
            eventos_formateados = []
            for evento in eventos:
                eventos_formateados.append({
                    'cod_age': evento.cod_age,
                    'descripcion': evento.descripcion,
                    'hora': evento.hora,
                    'tipo': evento.tipo
                })
            
            # Añadir eventos formateados al periodo correspondiente
            recordatorios[periodo] = eventos_formateados
        
        # ---------- LÓGICA PARA CICLO DE VACUNACIÓN ----------
        
        # Definir fechas del próximo ciclo
        año_actual = hoy.year
        mes_actual = hoy.month
        
        # Ejemplo: ciclos en enero, abril, julio y octubre
        ciclos_meses = [5, 6, 11, 12]
        
        # Encontrar el próximo mes de ciclo
        proximo_mes_ciclo = None
        for mes_ciclo in ciclos_meses:
            if mes_ciclo > mes_actual:
                proximo_mes_ciclo = mes_ciclo
                break
        
        # Si estamos en el último trimestre, el próximo ciclo será en el próximo año
        if proximo_mes_ciclo is None:
            proximo_mes_ciclo = ciclos_meses[0]
            año_proximo_ciclo = año_actual + 1
        else:
            año_proximo_ciclo = año_actual
        
        # Fechas del ciclo
        inicio_ciclo = date(año_proximo_ciclo, proximo_mes_ciclo, 1)  # Primer día del mes
        fin_ciclo = date(año_proximo_ciclo, proximo_mes_ciclo, 15)    # Día 15 del mes
        
        # 2. Comprobar si estamos cerca del inicio del ciclo (2 días antes)
        dias_hasta_ciclo = (inicio_ciclo - hoy).days
        
        # 3. Comprobar si estamos dentro del ciclo
        en_ciclo = inicio_ciclo <= hoy <= fin_ciclo
        
        # 4. Comprobar si terminó el ciclo recientemente (1 día después)
        dia_despues_ciclo = hoy == (fin_ciclo + timedelta(days=1))
        
        # 5. Comprobar si hoy es lunes (para recordatorio semanal)
        es_lunes = hoy.weekday() == 0  # 0 = lunes en Python
        
        # 6. Verificar estado de respuesta del usuario
        # Implementación simple: usamos la sesión para almacenar la respuesta
        # En producción, esto debería guardarse en la base de datos
        from django.contrib.sessions.backends.db import SessionStore
        
        # Intentar obtener la sesión del usuario
        try:
            session = SessionStore(session_key=f'vacunacion_{usuario_id}')
            usuario_confirmo = session.get('confirmo_vacunacion', False)
        except:
            usuario_confirmo = False
        
        # 7. Añadir recordatorios según corresponda
        
        # a. Recordatorio de aproximación al ciclo (2 días antes)
        if 0 < dias_hasta_ciclo <= 2:
            recordatorios['vacunacion'].append({
                'cod_age': 'pre_vacunacion',
                'descripcion': 'El ciclo de vacunación está por llegar, y es fundamental para proteger la salud de tus animales. 💉🐄 ⏳ Agenda tu cita con tiempo y evita riesgos innecesarios. ¡Su bienestar está en tus manos! 🏥',
                'tipo': 'recordatorio_vacunacion',
                'requiere_respuesta': False,
                'fecha_inicio': inicio_ciclo.strftime('%d/%m/%Y'),
                'fecha_fin': fin_ciclo.strftime('%d/%m/%Y')
            })
        
        # b. Recordatorio semanal durante el ciclo (cada lunes)
        if en_ciclo and es_lunes and not usuario_confirmo:
            recordatorios['vacunacion'].append({
                'cod_age': 'ciclo_vacunacion',
                'descripcion': '🐮💉 ¿Ya aseguraste la protección de tus animales? 📅 No esperes más, agenda su vacunación y cuida su bienestar. 🏥 ¡Cada dosis cuenta para su salud!',
                'tipo': 'recordatorio_vacunacion',
                'requiere_respuesta': True,
                'opciones': ['Sí', 'No']
            })
        
        # c. Recordatorio de fin de ciclo (1 día después)
        if dia_despues_ciclo:
            recordatorios['vacunacion'].append({
                'cod_age': 'post_vacunacion',
                'descripcion': '✅ ¡El ciclo de vacunación ha concluido con éxito! ✅ 👏 Si aún no lo hiciste, no esperes más. ¡Cada vacuna es clave para su bienestar! 🏥 Nos vemos en el próximo ciclo para seguir cuidándolos juntos',
                'tipo': 'recordatorio_vacunacion',
                'requiere_respuesta': False
            })
            
    except Exception as e:
        # En caso de error, devolver diccionario vacío
        print(f"Error al obtener recordatorios: {e}")
    
    return recordatorios

@login_required
def confirmar_vacunacion(request):
    """Vista para manejar la respuesta del usuario a los recordatorios de vacunación"""
    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        
        if respuesta == 'Sí':
            # Guardar la confirmación en la sesión
            # En una implementación real, esto debería guardarse en la base de datos
            from django.contrib.sessions.backends.db import SessionStore
            
            usuario_id = request.session.get('usuario_id')
            session = SessionStore(session_key=f'vacunacion_{usuario_id}')
            session['confirmo_vacunacion'] = True
            session.save()
            
            messages.success(request, "¡Gracias por confirmar la vacunación de tus animales!")
        else:
            messages.info(request, "Te seguiremos recordando sobre la importancia de la vacunación.")
        
        # Redirigir a la página desde la que se hizo la solicitud
        referer = request.META.get('HTTP_REFERER', 'home')
        return redirect(referer)
    
    # Si no es POST, redirigir al inicio
    return redirect('home')

"Vistas para crud de compras"
@login_required
def compras(request):
    # Obtener el ID del administrador actual desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    try:
        # Inicializar variables de búsqueda
        busqueda = request.GET.get('busqueda', '')
        tipo_busqueda = request.GET.get('tipo_busqueda', '')
        
        # Obtener la base de compras del administrador actual ordenadas por fecha descendente
        compras = Compra.objects.filter(id_adm=usuario_id).order_by('-fecha')
        
        # Aplicar filtros según los parámetros de búsqueda
        if busqueda:
            # Detectar automáticamente si es una fecha (patrón DD/MM/YYYY)
            es_formato_fecha = True if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', busqueda) else False
            
            # Si parece una fecha o el tipo_busqueda está explícitamente configurado como 'fecha'
            if es_formato_fecha or tipo_busqueda == 'fecha':
                tipo_busqueda = 'fecha'  # Establecer explícitamente como fecha
                try:
                    # Convertir a fecha y filtrar
                    fecha_busqueda = datetime.strptime(busqueda, '%d/%m/%Y').date()
                    compras = compras.filter(fecha=fecha_busqueda)
                except ValueError:
                    # Si el formato de fecha es incorrecto, mostrar mensaje y no aplicar ningún filtro
                    messages.warning(request, "Formato de fecha incorrecto. Use DD/MM/AAAA.")
                    # Mantenemos tipo_busqueda como 'fecha' aunque haya un error
            else:
                # Si no parece una fecha, buscar por proveedor
                tipo_busqueda = 'proveedor'
                compras = compras.filter(nom_prov__icontains=busqueda)
        
        # Determinar el siguiente código de compra para este administrador
        siguiente_cod_com = 1
        ultima_compra = Compra.objects.filter(id_adm=usuario_id).order_by('-cod_com').first()
        if ultima_compra:
            siguiente_cod_com = ultima_compra.cod_com + 1
        
        # Obtener todos los animales disponibles para el selector
        animales = Animal.objects.filter(id_adm=usuario_id)
        
        # Cargar detalles de compras con prefetch para optimizar rendimiento
        compras_con_detalles = []
        for compra in compras:
            # Prefetch relacionados para evitar consultas N+1
            detalles = DetCom.objects.filter(cod_com=compra.cod_com).select_related()
            compra.detalles = detalles
            compras_con_detalles.append(compra)
        
        # Preparar contexto para la plantilla
        context = {
            'compras': compras_con_detalles,
            'animales': animales,
            'proximo_codigo': siguiente_cod_com,
            'busqueda': busqueda,
            'tipo_busqueda': tipo_busqueda,  # Usamos el tipo_busqueda determinado automáticamente
            'current_page_name': 'Registro de Compras',
            'recordatorios': request.recordatorios,
            'hay_recordatorios': request.hay_recordatorios,
            'total_recordatorios': request.total_recordatorios
        }
        
        return render(request, 'paginas/compras.html', context)
    
    except Exception as e:
        messages.error(request, f"Error al cargar las compras: {str(e)}")
        return redirect('home')
    
@login_required
def crear_compra(request):
    """
    Vista para crear una nueva compra con sus detalles
    """
    if request.method == 'POST':
        try:
            # Obtener el ID del administrador actual desde la sesión
            usuario_id = request.session.get('usuario_id')
            
            # Obtener datos del formulario
            fecha = request.POST.get('fecha')
            nom_prov = request.POST.get('nom_prov')
            cantidad = int(request.POST.get('cantidad'))
            
            # Formatear correctamente el precio total
            precio_total_str = request.POST.get('precio_total', '0')
            # Primero eliminamos todos los puntos (separadores de miles)
            precio_total_str = precio_total_str.replace('.', '')
            # Luego reemplazamos la coma decimal por punto (si existe)
            precio_total_str = precio_total_str.replace(',', '.')
            # Convertimos a float
            precio_total = float(precio_total_str)
            
            # Determinar el siguiente código de compra para este administrador
            siguiente_cod_com = 1
            ultima_compra = Compra.objects.filter(id_adm=usuario_id).order_by('-cod_com').first()
            if ultima_compra:
                siguiente_cod_com = ultima_compra.cod_com + 1
            
            # Crear la compra
            compra = Compra.objects.create(
                cod_com=siguiente_cod_com,
                id_adm_id=usuario_id,
                fecha=fecha,
                nom_prov=nom_prov,
                cantidad=cantidad,
                precio_total=precio_total
            )
            
            # Procesar detalles de animales
            for i in range(1, cantidad + 1):
                cod_ani = request.POST.get(f'cod_ani_{i}')  # Cambiado de cod_ani_id a cod_ani
                edad_anicom = request.POST.get(f'edad_aniCom_{i}')
                peso_ani = request.POST.get(f'peso_ani_{i}')
                
                # Formatear correctamente el precio unitario
                precio_uni_str = request.POST.get(f'precio_uni_{i}', '0')
                precio_uni_str = precio_uni_str.replace('.', '')  # Eliminar puntos de miles
                precio_uni_str = precio_uni_str.replace(',', '.')  # Reemplazar coma decimal por punto
                precio_uni = float(precio_uni_str)
                
                # Crear el detalle de compra
                DetCom.objects.create(
                    cod_com=compra,
                    cod_ani=cod_ani,  # Cambiado de cod_ani_id a cod_ani
                    edad_anicom=edad_anicom or 0,  # Asignar 0 si no se proporciona
                    peso_anicom=peso_ani or 0,  # Asignar 0 si no se proporciona
                    precio_uni=precio_uni
                )
            
            messages.success(request, "Compra registrada exitosamente")
            return redirect('compras')
        except Exception as e:
            messages.error(request, f"Error al registrar la compra: {str(e)}")
            return redirect('compras')
    else:
        return redirect('compras')

# Vista API para obtener el siguiente código de animal
@login_required
def api_siguiente_codigo_animal(request):
    """API para obtener el siguiente código de animal disponible"""
    try:
        # Buscar el último animal en la base de datos
        ultimo_animal = Animal.objects.all().order_by('-cod_ani').first()
        siguiente_codigo = 1 if not ultimo_animal else ultimo_animal.cod_ani + 1
        
        # Registrar información de depuración
        print(f"Último código encontrado: {ultimo_animal.cod_ani if ultimo_animal else 'Ninguno'}")
        print(f"Siguiente código asignado: {siguiente_codigo}")
        
        return JsonResponse({'siguiente_codigo': siguiente_codigo})
    except Exception as e:
        # Registrar el error para depuración
        import traceback
        print(f"Error en API siguiente_codigo_animal: {str(e)}")
        print(traceback.format_exc())
        
@login_required
def eliminar_compra(request, compra_id):
    # Obtener el ID del administrador actual desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    try:
        # Buscar la compra asegurándose que pertenezca al administrador actual
        compra = Compra.objects.get(cod_com=compra_id, id_adm=usuario_id)
        
        # Primero, eliminar todos los detalles de compra asociados
        DetCom.objects.filter(cod_com=compra).delete()
        
        # Luego, eliminar la compra principal
        compra.delete()
        
        messages.success(request, f"¡Compra #{compra_id} eliminada con éxito!")
    
    except Compra.DoesNotExist:
        messages.error(request, "Error: La compra no existe o no tienes permiso para eliminarla.")
    except Exception as e:
        messages.error(request, f"Error al eliminar la compra: {str(e)}")
    
    return redirect('compras')

@login_required
def compra_pdf(request, compra_id):
    # Obtener la compra desde la base de datos
    compra = get_object_or_404(Compra, cod_com=compra_id)
    
    # Definir el HTML directamente en el código - solución más sencilla y directa
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>Informe de Compra #{compra.cod_com}</title>
        <style>
            @page {{
                size: letter portrait;
                margin: 1cm 1.5cm; /* Margen reducido */
            }}

            .footer {{
                position: fixed;
                bottom: 0.8cm;
                width: 100%;
                text-align: right;
                font-size: 8pt;
                color: #666666;
            }}

            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 10pt; /* Tamaño de fuente reducido */
                color: #000000;
                margin: 0;
                padding: 0;
            }}

            .header {{
                width: 100%;
                margin-bottom: 8pt; /* Reducido */
                padding-top: 0;
            }}

            .timestamp {{
                font-size: 8pt;
                color: #666666;
                text-align: right;
            }}

            .title {{
                font-size: 16pt; /* Reducido */
                font-weight: bold;
                text-align: center;
                margin-top: 0;
                margin-bottom: 5pt;
            }}

            hr {{
                border: none;
                border-top: 1px solid #333333;
                margin: 3pt 0; /* Reducido */
            }}

            h2 {{
                font-size: 12pt; /* Reducido */
                font-weight: bold;
                margin-top: 12pt; /* Reducido */
                margin-bottom: 6pt; /* Reducido */
                color: #333333;
            }}

            .info-table {{
                width: 98%; /* Ligeramente reducido */
                margin-bottom: 10pt; /* Reducido */
                border-spacing: 0;
                font-size: 9pt; /* Reducido */
            }}

            .info-table .label {{
                font-weight: bold;
                width: 30%; /* Reducido */
                padding: 3pt 6pt 3pt 0; /* Reducido */
                vertical-align: top;
            }}

            .data-table {{
                width: 98%; /* Ligeramente reducido */
                border-collapse: collapse;
                margin-top: 8pt; /* Reducido */
                font-size: 9pt; /* Reducido */
            }}

            .data-table th {{
                background-color: #f2f2f2;
                font-weight: bold;
                text-align: left;
                padding: 2pt 4pt; /* Reducido */
                border-bottom: 1pt solid #dddddd;
            }}
            
            .data-table td {{
                padding: 2pt 4pt; /* Reducido */
                border-bottom: 1pt solid #dddddd;
            }}

            .footer {{
                text-align: center;
                font-size: 8pt; /* Reducido */
                color: #666666;
                margin-top: 8pt; /* Reducido */
            }}

            .page-number:before {{
                content: counter(page);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 class="title">Informe de Compra #{compra.cod_com}</h1>
            <hr>
        </div>

        <div class="section">
            <h2>Información General</h2>
            
            <table class="info-table">
                <tr>
                    <td class="label">Fecha:</td>
                    <td>{compra.fecha.strftime('%d/%m/%Y')}</td>
                </tr>
                <tr>
                    <td class="label">Proveedor:</td>
                    <td>{compra.nom_prov}</td>
                </tr>
                <tr>
                    <td class="label">Cantidad de Animales:</td>
                    <td>{compra.cantidad}</td>
                </tr>
                <tr>
                    <td class="label">Precio Total:</td>
                    <td>${compra.precio_total:,.0f}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Detalles de Animales</h2>
            
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Código Animal</th>
                        <th>Edad</th>
                        <th>Peso</th>
                        <th>Precio Unitario</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Añadir filas para cada animal según tu estructura de datos
    if hasattr(compra, 'detcom_set') and compra.detcom_set.exists():
        for detalle in compra.detcom_set.all():
            html += f"""
                <tr>
                    <td>{detalle.cod_ani}</td>
                    <td>{detalle.edad_anicom} meses</td>
                    <td>{detalle.peso_anicom} kg</td>
                    <td>${detalle.precio_uni:,.0f}</td>
                </tr>
            """
    else:
        html += """
                <tr>
                    <td colspan="4" style="text-align: center;">No hay animales registrados en esta compra.</td>
                </tr>
        """
    
    # Cerrar el HTML
    html += """
                </tbody>
            </table>
        </div>

        <div class="footer">
            Página <pdf:pagenumber> de <pdf:pagecount>
        </div>
    </body>
    </html>
    """
    
    # Configurar la respuesta HTTP para el PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="compra_{compra_id}.pdf"'
    
    # Crear el PDF
    pisa_status = pisa.CreatePDF(
        html,
        dest=response
    )
    
    # Manejar errores
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
    return response

@login_required
@transaction.atomic
def editar_compra(request, cod_com):
    """
    Vista para editar una compra existente y sus detalles asociados.
    """
    compra = get_object_or_404(Compra, cod_com=cod_com)
    
    if request.method == 'POST':
        try:
            # Actualizar datos de la compra
            compra.fecha = request.POST.get('fecha')
            compra.nom_prov = request.POST.get('nom_prov')
            
            # El precio total se calcula a partir de los detalles
            nuevo_precio_total = 0
            
            # Número de detalles en el formulario
            num_detalles = int(request.POST.get('num_detalles', 0))
            
            # Actualizar cada detalle de compra
            for i in range(num_detalles):
                # Usar cod_detcom en lugar de id para identificar el detalle
                detalle_id = request.POST.get(f'detalle_id_{i}')
                
                # Buscar el detalle por cod_detcom en lugar de id
                detalle = get_object_or_404(DetCom, cod_detcom=detalle_id, cod_com=compra)
                
                # Actualizar datos del detalle
                detalle.edad_anicom = request.POST.get(f'edad_anicom_{i}')
                detalle.peso_anicom = request.POST.get(f'peso_anicom_{i}')
                detalle.precio_uni = request.POST.get(f'precio_uni_{i}')
                
                # Acumular para el precio total
                nuevo_precio_total += float(detalle.precio_uni)
                
                # Guardar el detalle actualizado
                detalle.save()
            
            # Actualizar el precio total de la compra
            compra.precio_total = nuevo_precio_total
            compra.save()
            
            messages.success(request, f'Compra #{cod_com} actualizada exitosamente.')
            return redirect('compras')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la compra: {str(e)}')
            return redirect('compras')
    
    # Si la solicitud no es POST, redirigir a la lista de compras
    return redirect('compras')

@login_required
def cancelar_compra(request):
    """
    Vista para manejar la cancelación del formulario de compra
    """
    if request.method == 'POST':
        # No necesitamos hacer nada con los datos del formulario
        # Simplemente redirigimos a la página de compras
        # Django no conservará los datos del formulario en este caso
        messages.info(request, "Registro de compra cancelado")
        return redirect('compras')
    else:
        # Si no es un POST request, redirigir a la página de compras
        return redirect('compras')

"Vistas para crud de ventas"
@login_required
def ventas(request):
    """Vista principal para mostrar todas las ventas del administrador actual."""
    usuario_id = request.session.get('usuario_id')
    
    try:
        # Obtener todas las ventas del administrador actual
        ventas = Venta.objects.filter(id_adm=usuario_id).order_by('-fecha')
        
        # Obtener parámetros de búsqueda y filtrado
        busqueda = request.GET.get('busqueda', '')
        tipo_filtro = request.GET.get('tipo_filtro', '')
        valor_filtro = request.GET.get('valor', '')
        fecha_inicio = request.GET.get('fecha_inicio', '')
        fecha_fin = request.GET.get('fecha_fin', '')
        
        # Aplicar filtros según los parámetros recibidos
        if busqueda:
            # Buscar por cliente
            ventas = ventas.filter(nom_cli__icontains=busqueda)
        
        # Filtrar por rango de fechas si se proporcionan
        if fecha_inicio and fecha_fin:
            ventas = ventas.filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin)
        
        # Obtener detalles para cada venta
        for venta in ventas:
            venta.detalles = DetVen.objects.filter(cod_ven=venta.cod_ven)
        
        context = {
            'ventas': ventas,
            'proximo_codigo': 1,  # Valor por defecto, ajusta según tu lógica
            'busqueda': busqueda,
            'tipo_filtro': tipo_filtro,
            'valor_filtro': valor_filtro,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'current_page_name': 'Registro de Ventas',
        }
        
        return render(request, 'paginas/ventas.html', context)
    
    except Exception as e:
        messages.error(request, f"Error al cargar las ventas: {str(e)}")
        return redirect('home')

@login_required
def crear_venta(request):
    """Vista para crear una nueva venta con sus detalles."""
    if request.method == 'POST':
        try:
            # Obtener el ID del administrador actual desde la sesión
            usuario_id = request.session.get('usuario_id')
            
            # Obtener datos del formulario
            fecha = request.POST.get('fecha')
            nom_cli = request.POST.get('nom_cli')
            cantidad = int(request.POST.get('cantidad'))

            # Formatear correctamente el precio total
            precio_total_str = request.POST.get('precio_total', '0')
            # Primero eliminamos todos los puntos (separadores de miles)
            precio_total_str = precio_total_str.replace('.', '')
            # Luego reemplazamos la coma decimal por punto (si existe)
            precio_total_str = precio_total_str.replace(',', '.')
            # Convertimos a float
            precio_total = float(precio_total_str)
            
            # Determinar el siguiente código de venta para este administrador
            siguiente_cod_ven = 1
            ultima_venta = Venta.objects.filter(id_adm=usuario_id).order_by('-cod_ven').first()
            if ultima_venta:
                siguiente_cod_ven = ultima_venta.cod_ven + 1
            
            # Crear la venta
            venta = Venta.objects.create(
                cod_ven=siguiente_cod_ven,
                id_adm_id=usuario_id,
                fecha=fecha,
                nom_cli=nom_cli,
                cantidad=cantidad,
                precio_total=precio_total
            )
            
            # Procesar detalles de animales
            for i in range(1, cantidad + 1):
                # Obtener valores con validación
                cod_ani = request.POST.get(f'cod_ani_{i}', '')
                edad_aniven = request.POST.get(f'edad_aniven_{i}', '0')
                peso_aniven = request.POST.get(f'peso_aniven_{i}', '0')
                
                # Asegurar que los campos no sean None o cadenas vacías
                if not cod_ani:
                    messages.error(request, f"Código de animal es requerido para el animal {i}")
                    continue
                
                # Formatear correctamente el precio unitario
                precio_uni_str = request.POST.get(f'precio_uni_{i}', '0')
                precio_uni_str = precio_uni_str.replace('.', '')  # Eliminar puntos de miles
                precio_uni_str = precio_uni_str.replace(',', '.')  # Reemplazar coma decimal por punto
                precio_uni = float(precio_uni_str)
                
                # Crear el detalle de venta con valores por defecto si están vacíos
                DetVen.objects.create(
                    cod_ven=venta,
                    cod_ani=cod_ani,
                    edad_aniven=edad_aniven or 0,  # Valor por defecto 0 si está vacío
                    peso_aniven=peso_aniven or 0,  # Valor por defecto 0 si está vacío
                    precio_uni=precio_uni,
                )
            
            messages.success(request, "Venta registrada exitosamente")
            return redirect('ventas')
        except Exception as e:
            messages.error(request, f"Error al registrar la venta: {str(e)}")
            return redirect('ventas')
    else:
        return redirect('ventas')
    
@login_required
@transaction.atomic
def editar_venta(request, cod_ven):
    """
    Vista para editar una compra existente y sus detalles asociados.
    """
    venta = get_object_or_404(Venta, cod_ven=cod_ven)
    
    if request.method == 'POST':
        try:
            # Actualizar datos de la compra
            venta.fecha = request.POST.get('fecha')
            venta.nom_cli = request.POST.get('nom_cli')
            
            # El precio total se calcula a partir de los detalles
            nuevo_precio_total = 0
            
            # Número de detalles en el formulario
            num_detalles = int(request.POST.get('num_detalles', 0))
            
            # Actualizar cada detalle de compra
            for i in range(num_detalles):
                # Usar cod_detcom en lugar de id para identificar el detalle
                detalle_id = request.POST.get(f'detalle_id_{i}')
                
                # Buscar el detalle por cod_detcom en lugar de id
                detalle = get_object_or_404(DetVen, cod_detven=detalle_id, cod_ven=venta)
                
                # Actualizar datos del detalle
                detalle.edad_aniven = request.POST.get(f'edad_aniven_{i}')
                detalle.peso_aniven = request.POST.get(f'peso_aniven_{i}')
                detalle.precio_uni = request.POST.get(f'precio_uni_{i}')
                
                # Acumular para el precio total
                nuevo_precio_total += float(detalle.precio_uni)
                
                # Guardar el detalle actualizado
                detalle.save()
            
            # Actualizar el precio total de la compra
            venta.precio_total = nuevo_precio_total
            venta.save()
            
            messages.success(request, f'Venta #{cod_ven} actualizada exitosamente.')
            return redirect('ventas')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la venta: {str(e)}')
            return redirect('ventas')
    
    # Si la solicitud no es POST, redirigir a la lista de compras
    return redirect('ventas')

@login_required
def eliminar_venta(request, venta_id):
    """Vista para eliminar una venta y sus detalles asociados."""
    usuario_id = request.session.get('usuario_id')
    
    try:
        # Buscar la venta asegurándose que pertenezca al administrador actual
        venta = Venta.objects.get(cod_ven=venta_id, id_adm=usuario_id)
        
        # Primero, eliminar todos los detalles de venta asociados
        DetVen.objects.filter(cod_ven=venta).delete()
        
        # Luego, eliminar la venta principal
        venta.delete()
        
        messages.success(request, f"¡Venta #{venta_id} eliminada con éxito!")
    
    except Venta.DoesNotExist:  # Corregido de Compra.DoesNotExist
        messages.error(request, "Error: La venta no existe o no tienes permiso para eliminarla.")
    except Exception as e:
        messages.error(request, f"Error al eliminar la venta: {str(e)}")
    
    return redirect('ventas')

@login_required
def venta_pdf(request, venta_id):
    # Obtener la venta desde la base de datos
    venta = get_object_or_404(Venta, cod_ven=venta_id)
    
    # Definir el HTML directamente en el código - solución más sencilla y directa
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>Informe de Venta #{venta.cod_ven}</title>
        <style>
            @page {{
                size: letter portrait;
                margin: 1cm 1.5cm; /* Margen reducido */
            }}

            .footer {{
                position: fixed;
                bottom: 0.8cm;
                width: 100%;
                text-align: right;
                font-size: 8pt;
                color: #666666;
            }}

            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 10pt; /* Tamaño de fuente reducido */
                color: #000000;
                margin: 0;
                padding: 0;
            }}

            .header {{
                width: 100%;
                margin-bottom: 8pt; /* Reducido */
                padding-top: 0;
            }}

            .timestamp {{
                font-size: 8pt;
                color: #666666;
                text-align: right;
            }}

            .title {{
                font-size: 16pt; /* Reducido */
                font-weight: bold;
                text-align: center;
                margin-top: 0;
                margin-bottom: 5pt;
            }}

            hr {{
                border: none;
                border-top: 1px solid #333333;
                margin: 3pt 0; /* Reducido */
            }}

            h2 {{
                font-size: 12pt; /* Reducido */
                font-weight: bold;
                margin-top: 12pt; /* Reducido */
                margin-bottom: 6pt; /* Reducido */
                color: #333333;
            }}

            .info-table {{
                width: 98%; /* Ligeramente reducido */
                margin-bottom: 10pt; /* Reducido */
                border-spacing: 0;
                font-size: 9pt; /* Reducido */
            }}

            .info-table .label {{
                font-weight: bold;
                width: 30%; /* Reducido */
                padding: 3pt 6pt 3pt 0; /* Reducido */
                vertical-align: top;
            }}

            .data-table {{
                width: 98%; /* Ligeramente reducido */
                border-collapse: collapse;
                margin-top: 8pt; /* Reducido */
                font-size: 9pt; /* Reducido */
            }}

            .data-table th {{
                background-color: #f2f2f2;
                font-weight: bold;
                text-align: left;
                padding: 2pt 4pt; /* Reducido */
                border-bottom: 1pt solid #dddddd;
            }}
            
            .data-table td {{
                padding: 2pt 4pt; /* Reducido */
                border-bottom: 1pt solid #dddddd;
            }}

            .footer {{
                text-align: center;
                font-size: 8pt; /* Reducido */
                color: #666666;
                margin-top: 8pt; /* Reducido */
            }}

            .page-number:before {{
                content: counter(page);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 class="title">Informe de Venta #{venta.cod_ven}</h1>
            <hr>
        </div>

        <div class="section">
            <h2>Información General</h2>
            
            <table class="info-table">
                <tr>
                    <td class="label">Fecha:</td>
                    <td>{venta.fecha.strftime('%d/%m/%Y')}</td>
                </tr>
                <tr>
                    <td class="label">Cliente:</td>
                    <td>{venta.nom_cli}</td>
                </tr>
                <tr>
                    <td class="label">Cantidad de Animales:</td>
                    <td>{venta.cantidad}</td>
                </tr>
                <tr>
                    <td class="label">Precio Total:</td>
                    <td>${venta.precio_total:,.0f}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Detalles de Animales</h2>
            
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Código Animal</th>
                        <th>Edad</th>
                        <th>Peso</th>
                        <th>Precio Unitario</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # Añadir filas para cada animal según tu estructura de datos
    if hasattr(venta, 'detven_set') and venta.detven_set.exists():
        for detalle in venta.detven_set.all():
            html += f"""
                <tr>
                    <td>{detalle.cod_ani}</td>
                    <td>{detalle.edad_aniven} meses</td>
                    <td>{detalle.peso_aniven} kg</td>
                    <td>${detalle.precio_uni:,.0f}</td>
                </tr>
            """
    else:
        html += """
                <tr>
                    <td colspan="4" style="text-align: center;">No hay animales registrados en esta venta.</td>
                </tr>
        """
    
    # Cerrar el HTML
    html += """
                </tbody>
            </table>
        </div>

        <div class="footer">
            Página <pdf:pagenumber> de <pdf:pagecount>
        </div>
    </body>
    </html>
    """
    
    # Configurar la respuesta HTTP para el PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="venta_{venta_id}.pdf"'
    
    # Crear el PDF
    pisa_status = pisa.CreatePDF(
        html,
        dest=response
    )
    
    # Manejar errores
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)
    return response

@login_required
def cancelar_venta(request):
    """Vista para manejar la cancelación del formulario de venta"""
    if request.method == 'POST':
        messages.info(request, "Registro de venta cancelado")
        return redirect('ventas')
    else:
        # Si no es un POST request, redirigir a la página de compras
        return redirect('ventas')

"Vistas para crud de documentos"
@login_required
def documento(request):
    # Obtener ID del administrador desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    try:
        # Verificar que el usuario es un administrador
        administrador = Administrador.objects.get(pk=usuario_id)
        
        # Verificar si no hay documentos y reiniciar el AUTO_INCREMENT
        documentos_count = Documento.objects.filter(id_adm=administrador).count()
        if documentos_count == 0:
            with connection.cursor() as cursor:
                table_documento = Documento._meta.db_table
                cursor.execute(f"ALTER TABLE {table_documento} AUTO_INCREMENT = 1;")
        
        # Obtener parámetros de búsqueda y filtrado
        busqueda = request.GET.get('busqueda', '')
        tipo_filtro = request.GET.get('tipo_filtro', '')
        valor_filtro = request.GET.get('valor', '')
        
        # Variable para almacenar el tipo de búsqueda detectado
        tipo_busqueda = None
        
        # Consulta base de documentos del administrador actual
        documentos = Documento.objects.filter(id_adm=administrador)
        
        # Aplicar filtros según los parámetros recibidos
        if busqueda:
            import re
            from django.db.models import Q
            
            # Verificar si la búsqueda es una fecha en formato dd/mm/yyyy
            fecha_pattern = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})$')
            match = fecha_pattern.match(busqueda)
            
            if match:
                # Si es una fecha, convertir al formato yyyy-mm-dd para búsqueda en BD
                day, month, year = match.groups()
                # Asegurar formato con ceros a la izquierda
                day = day.zfill(2)
                month = month.zfill(2)
                fecha_formateada = f"{year}-{month}-{day}"
                documentos = documentos.filter(fecha_doc=fecha_formateada)
                tipo_busqueda = "fecha"
            else:
                # Si no es fecha, buscar por título
                documentos = documentos.filter(titulo__icontains=busqueda)
                tipo_busqueda = "titulo"
        
        # Aplicar filtro por categoría si está especificado
        if tipo_filtro == 'Tipo' and valor_filtro:
            documentos = documentos.filter(categoria=valor_filtro)
            
        # Marcar los documentos PDF
        for doc in documentos:
            doc.es_pdf = doc.archivo and doc.archivo.name.lower().endswith('.pdf')
        
        # Renderizar la plantilla con el contexto
        return render(request, 'paginas/documento.html', {
            "documentos": documentos,
            "titulo_pagina": 'Biblioteca de Documentos',
            "busqueda": busqueda,
            "current_page_name": "Documentos",
            "tipo_filtro": tipo_filtro,
            "valor_filtro": valor_filtro,
            "tipo_busqueda": tipo_busqueda,  # Pasar el tipo de búsqueda detectado a la plantilla
            'recordatorios': request.recordatorios,
            'hay_recordatorios': request.hay_recordatorios,
            'total_recordatorios': request.total_recordatorios
        })
        
    except Administrador.DoesNotExist:
        # Manejar el caso donde el usuario no es un administrador
        messages.error(request, 'No tienes permisos para acceder a esta sección')
        return render(request, 'error.html', {'mensaje': 'No tienes permisos para acceder a esta sección'})
    
@login_required
def agregar_documento(request):
    if request.method == 'POST':
        # Obtener los datos del formulario
        titulo = request.POST.get('titulo')
        categoria = request.POST.get('categoria')
        fecha_doc = request.POST.get('fecha_doc')
        archivo = request.FILES.get('archivo')
        
        # Validar que todos los campos requeridos estén presentes
        if not all([titulo, categoria, fecha_doc, archivo]):
            messages.error(request, 'Todos los campos son obligatorios')
            return redirect('documento')
            
        # Validar que el archivo sea PDF
        if archivo and not archivo.name.lower().endswith('.pdf'):
            messages.error(request, 'Solo se permiten archivos PDF')
            return redirect('documento')
        
        try:
            # Obtener el ID del administrador desde la sesión
            usuario_id = request.session.get('usuario_id')
            administrador = Administrador.objects.get(id_adm=usuario_id)
            
            # Crear el nuevo documento
            documento = Documento(
                titulo=titulo,
                categoria=categoria,
                fecha_doc=fecha_doc,
                archivo=archivo,
                id_adm=administrador
            )
            
            # Guardar el documento en la base de datos
            documento.save()
            
            messages.success(request, 'Documento guardado exitosamente')
            return redirect('documento')
            
        except Administrador.DoesNotExist:
            messages.error(request, 'Usuario no autorizado')
            return redirect('error')
        except Exception as e:
            messages.error(request, f'Error al guardar el documento: {str(e)}')
            return redirect('documento')
    
    # Si la solicitud no es POST, redirigir a la página de documentos
    return redirect('documento')

@login_required
def editar_documento(request, documento_id):
    # Obtener el ID del administrador actual desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    try:
        # Obtener el documento asegurándose que pertenezca al administrador actual
        documento = get_object_or_404(Documento, num_doc=documento_id, id_adm=usuario_id)
        
        if request.method == "POST":
            # Procesar el formulario de edición
            try:
                # Obtener datos del formulario
                titulo = request.POST.get("titulo")
                categoria = request.POST.get("categoria")
                fecha_doc = request.POST.get("fecha_doc")
                
                # Actualizar los campos del documento
                documento.titulo = titulo
                documento.categoria = categoria
                documento.fecha_doc = fecha_doc
                
                # Verificar si se subió un nuevo archivo
                nuevo_archivo = request.FILES.get('archivo')
                if nuevo_archivo:
                    # Si el archivo tiene extensión .pdf, actualizarlo
                    if nuevo_archivo.name.lower().endswith('.pdf'):
                        # Si existe un archivo anterior, eliminarlo (opcional)
                        if documento.archivo:
                            import os
                            if os.path.isfile(documento.archivo.path):
                                os.remove(documento.archivo.path)
                        
                        # Actualizar con el nuevo archivo
                        documento.archivo = nuevo_archivo
                    else:
                        messages.error(request, "Solo se permiten archivos PDF.")
                        return redirect('documento')
                
                # Guardar los cambios
                documento.save()
                
                messages.success(request, f"¡Documento '{titulo}' actualizado con éxito!")
                return redirect('documento')
                
            except ValueError:
                messages.error(request, "Error: Valores inválidos en el formulario. Verifica los datos ingresados.")
            except Exception as e:
                messages.error(request, f"Error al actualizar el documento: {str(e)}")
        
        # Si es GET o hubo error en POST, mostrar el modal de edición
        return render(request, "paginas/editar_documento.html", {
            "documento": documento,
            "current_page_name": "Editar Documento"
        })
        
    except Documento.DoesNotExist:
        messages.error(request, "Error: No se encontró el documento.")
        return redirect('documento')
    
@login_required
def eliminar_documento(request, documento_id):
    if request.method == "POST":
        # Obtener el ID del administrador actual desde la sesión
        usuario_id = request.session.get('usuario_id')
        
        try:
            # Obtener el documento asegurándose que pertenezca al administrador actual
            documento = get_object_or_404(Documento, num_doc=documento_id, id_adm=usuario_id)
            
            # Eliminar el documento
            documento.delete()
            
            # Verificar si ya no hay documentos y reiniciar el AUTO_INCREMENT
            documentos_count = Documento.objects.filter(id_adm=usuario_id).count()
            if documentos_count == 0:
                with connection.cursor() as cursor:
                    table_documento = Documento._meta.db_table
                    cursor.execute(f"ALTER TABLE {table_documento} AUTO_INCREMENT = 1;")
            
            messages.success(request, "Documento eliminado con éxito!")
            
        except Documento.DoesNotExist:
            messages.error(request, "Error: No se encontró el documento.")
        except Exception as e:
            messages.error(request, f"Error al eliminar: {str(e)}")
        
        return redirect('documento')
    
    # Si no es un POST, redirigir a documentos
    return redirect('documento')

@login_required
def cancelar_documento(request):
    
    if request.method == 'POST':
        messages.info(request, "Registro de documento cancelado")
        return redirect('documento')
    else:
        return redirect('documento')
    
"Vistas para crud de contactos"
@login_required
def contacto(request):
    # Obtener ID del administrador desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    # Verificar que el usuario es un administrador
    usuario = Administrador.objects.get(pk=usuario_id)

    # Iniciar con todos los contactos del administrador
    contactos = Contacto.objects.filter(id_adm=usuario)

    # Obtener parámetros de búsqueda y filtrado
    busqueda = request.GET.get('busqueda', '')
    tipo_filtro = request.GET.get('tipo_filtro', '')
    valor_filtro = request.GET.get('valor', '')  # Nota: el HTML usa 'valor', no 'valor_filtro'
    
    # Variable para almacenar el tipo de búsqueda detectado
    tipo_busqueda = None
    
    # Aplicar filtros de búsqueda si existe un término
    if busqueda:
        from django.db.models import Q
        
        # Intentar detectar si la búsqueda es por cargo o por nombre
        if any(cargo in busqueda.lower() for cargo in ['proveedor', 'veterinario', 'comprador']):
            contactos = contactos.filter(cargo__icontains=busqueda)
            tipo_busqueda = "cargo"
        else:
            # Buscar en ambos campos con preferencia al nombre
            contactos = contactos.filter(
                Q(nombre__icontains=busqueda)
            )
            tipo_busqueda = "nombre"
    
    # Aplicar filtro por cargo si se ha seleccionado
    if tipo_filtro == 'Cargo' and valor_filtro:
        contactos = contactos.filter(cargo__icontains=valor_filtro)
    
    # Verificar si no hay contactos y reiniciar el AUTO_INCREMENT
    contactos_count = Contacto.objects.filter(id_adm=usuario).count()
    if contactos_count == 0:
        with connection.cursor() as cursor:
            table_documento = Contacto._meta.db_table
            cursor.execute(f"ALTER TABLE {table_documento} AUTO_INCREMENT = 1;")
    
     # Agrega esta función para asignar el cargo a la imagen correspondiente
    def obtener_imagen_cargo(cargo):
            
        cargo = cargo.lower()
        
        if 'proveedor' in cargo:
            return 'img/proveedor.png'
        elif 'veterinario' in cargo:
            return 'img/veterinario.png'
        elif 'cliente' in cargo:
            return 'img/cliente.png'
        # Añade más tipos de cargo según sea necesario
    
    # Enriquecer la consulta de contactos con rutas de imágenes
    for contacto in contactos:
        contacto.imagen = obtener_imagen_cargo(contacto.cargo)

    # Renderizar la plantilla con el contexto
    return render(request, 'paginas/contacto.html', {
        "contactos": contactos,
        "busqueda": busqueda,
        "current_page_name": "Contactos",
        "tipo_filtro": tipo_filtro,
        "valor_filtro": valor_filtro,
        "tipo_busqueda": tipo_busqueda
    })

@login_required
def registrar_contacto(request):
    if request.method == "POST":
        # Obtener el ID del administrador actual desde la sesión
        usuario_id = request.session.get('usuario_id')
        
        try:
            # Obtener la instancia del administrador
            administrador = Administrador.objects.get(pk=usuario_id)

            # Verificar si no hay contactos y reiniciar el AUTO_INCREMENT
            contactos_count = Contacto.objects.filter(id_adm=usuario_id).count()
            if contactos_count == 1:
                with connection.cursor() as cursor:
                    table_contacto = Contacto._meta.db_table
                    cursor.execute(f"ALTER TABLE {table_contacto} AUTO_INCREMENT = 1;")
            
            nombre = request.POST.get("nombre")
            cargo = request.POST.get("cargo")
            correo = request.POST.get("correo")
            telefono = request.POST.get("telefono")
            
            # Crear y guardar el nuevo animal
            nuevo_contacto = Contacto(
                cargo=cargo,
                nombre=nombre,
                correo=correo,
                telefono=telefono,
                id_adm=administrador
            )
            nuevo_contacto.save()
            
            messages.success(request, f"¡Contacto registrado con éxito!")
            
        except Administrador.DoesNotExist:
            messages.error(request, "Error: No se pudo encontrar el administrador.")
        except ValueError:
            messages.error(request, "Error: Valores inválidos en el formulario. Verifica los datos ingresados.")
        except Exception as e:
            messages.error(request, f"Error al registrar el contacto: {str(e)}")
        
        return redirect('contacto')
    
    return redirect('contacto')

@login_required
def editar_contacto(request, id_cont):
    # Obtener el ID del administrador actual desde la sesión
    usuario_id = request.session.get('usuario_id')
    
    # Asumiendo que debes usar un modelo Contacto, no Animal
    contacto = get_object_or_404(Contacto, id_cont=id_cont, id_adm=usuario_id)
    
    if request.method == "POST":
        # Procesar el formulario de edición
        try:
            nombre = request.POST.get("nombre")
            cargo = request.POST.get("cargo")
            correo = request.POST.get("correo")
            telefono = request.POST.get("telefono")
            
            # Actualizar los campos del contacto
            contacto.nombre = nombre
            contacto.cargo = cargo
            contacto.correo = correo
            contacto.telefono = telefono
            
            # Guardar los cambios
            contacto.save()
            
            messages.success(request, f"¡Contacto #{id_cont} actualizado con éxito!")
            return redirect('contacto')
            
        except ValueError:
            messages.error(request, "Error: Valores inválidos en el formulario. Verifica los datos ingresados.")
        except Exception as e:
            messages.error(request, f"Error al actualizar el contacto: {str(e)}")
    
    # Si es GET o hubo error en POST, mostrar el formulario de edición
    return render(request, "paginas/contacto.html", {
        "contacto": contacto,
        "current_page_name": "Editar Contacto"
    })

@login_required
def eliminar_contacto(request, id_cont):
    if request.method == "POST":
        # Obtener el ID del administrador actual desde la sesión
        usuario_id = request.session.get('usuario_id')
        
        try:
            # Obtener el animal asegurándose que pertenezca al administrador actual
            contacto = get_object_or_404(Contacto, id_cont=id_cont, id_adm=usuario_id)
            
            # Guardar el código del animal para el mensaje
            id_contacto= id_cont
            
            # Eliminar el animal
            contacto.delete()
            
            messages.success(request, f"Contacto #{id_contacto} eliminado con éxito!")
            
        except Animal.DoesNotExist:
            messages.error(request, "Error: No se encontró el Contacto.")
        except Exception as e:
            messages.error(request, f"Error al eliminar el Contacto: {str(e)}")
        
        return redirect('contacto')
    
    # Si no es un POST, redirigir al inventario
    return redirect('contacto')

@login_required
def cancelar_contacto(request):
    
    if request.method == 'POST':
        messages.info(request, "Registro de contacto cancelado")
        return redirect('contacto')
    else:
        return redirect('contacto')
    
"vista para cerrar sesión"
def logout(request):
    # Clear all session data
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente")
    return redirect('iniciarsesion')