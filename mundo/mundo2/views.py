from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from .forms import AdministradorRegistroForm
from .models import Administrador, Agenda, Animal, Documento
from django.db import connection
from functools import wraps
from datetime import date, datetime, timedelta, timezone
import calendar

# Create your views here.
def bienvenido(request):
    return render(request, 'paginas/bienvenido.html')

def preguntasfrecuentes(request):
    return render(request, 'paginas/faq.html')

def registro(request):
    # Reiniciar AUTO_INCREMENT si es necesario
    with connection.cursor() as cursor:
        table_administrador = Administrador._meta.db_table
        cursor.execute(f"ALTER TABLE {table_administrador} AUTO_INCREMENT = 1;")
    
    if request.method == 'POST':
        form = AdministradorRegistroForm(request.POST)
        
        if form.is_valid():
            try:
                # Guardar el administrador con ambas contraseñas
                administrador = form.save()
                messages.success(request, "¡Registro exitoso! Ahora puedes iniciar sesión.")
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
        # Buscar eventos para cada fecha de recordatorio que no estén completados
        for periodo, fecha in fechas_recordatorio.items():
            eventos = Agenda.objects.filter(
                id_adm=usuario_id,
                fecha=fecha
            ).exclude(estado='Realizada')
            
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
        
        # 2. Comprobar si estamos cerca del inicio del ciclo (7 días antes)
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
def agenda(request):
    # Filtrar contactos por administrador actual si es necesario
    usuario_id = request.session.get('usuario_id')
    
    return render(request, 'paginas/agenda.html', {
        'current_page_name': 'Agenda'
    })


def logout(request):
    # Clear all session data
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente")
    return redirect('iniciarsesion')