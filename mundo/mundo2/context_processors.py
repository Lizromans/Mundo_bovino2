def user_data(request):
    """
    Agrega datos del usuario a la sesión para todas las plantillas
    """
    context = {}
    if 'id_adm' in request.session:
        context['id_adm'] = request.session.get('id_adm')
        context['nom_usu'] = request.session.get('nom_usu')
        context['finca'] = request.session.get('finca')
    return context