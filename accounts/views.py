import requests
import json
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from .forms import UserRegistrationForm, UserLoginForm

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer
)

# Nuevas importaciones para las funcionalidades adicionales
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count
from django.core.paginator import Paginator

# URL base de tu API (configurable desde settings)
API_BASE_URL = "http://127.0.0.1:8000/api/"

@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    """
    Vista API para el registro de nuevos usuarios.
    
    Endpoint: POST /api/register/
    
    Parámetros esperados:
    - username: nombre de usuario único
    - email: correo electrónico válido
    - password: contraseña (mínimo 8 caracteres)
    - password2: confirmación de contraseña
    - first_name: nombre (opcional)
    - last_name: apellido (opcional)
    
    Respuestas:
    - 201: Usuario creado exitosamente
    - 400: Error en validación de datos
    """
    if request.method == 'POST':
        # Creamos el serializer con los datos recibidos
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            # Guardamos el nuevo usuario
            user = serializer.save()
            
            # Creamos o obtenemos el token de autenticación para el usuario
            token, created = Token.objects.get_or_create(user=user)
            
            # Preparamos la respuesta con los datos del usuario y su token
            response_data = {
                'success': True,
                'message': 'Usuario registrado satisfactoriamente',
                'user': UserSerializer(user).data,
                'token': token.key
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        # Si hay errores de validación, los devolvemos
        return Response({
            'success': False,
            'message': 'Error en el registro',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """
    Vista API para el inicio de sesión de usuarios.
    
    Endpoint: POST /api/login/
    
    Parámetros esperados:
    - username: nombre de usuario
    - password: contraseña
    
    Respuestas:
    - 200: Autenticación exitosa
    - 400: Error en credenciales
    """
    if request.method == 'POST':
        # Creamos el serializer con los datos de login
        serializer = UserLoginSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Obtenemos el usuario validado
            user = serializer.validated_data['user']
            
            # Iniciamos sesión en Django (opcional, para mantener sesión)
            login(request, user)
            
            # Creamos o obtenemos el token de autenticación
            token, created = Token.objects.get_or_create(user=user)
            
            # Preparamos la respuesta exitosa
            response_data = {
                'success': True,
                'message': 'Autenticación satisfactoria',
                'user': UserSerializer(user).data,
                'token': token.key
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        # Si hay errores de autenticación
        return Response({
            'success': False,
            'message': 'Error en la autenticación',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """
    Vista API para cerrar sesión.
    
    Endpoint: POST /api/logout/
    Requiere: Token de autenticación en headers
    
    Respuestas:
    - 200: Sesión cerrada exitosamente
    - 401: No autorizado (sin token válido)
    """
    if request.method == 'POST':
        try:
            # Eliminamos el token del usuario
            request.user.auth_token.delete()
            
            # Cerramos la sesión de Django
            logout(request)
            
            return Response({
                'success': True,
                'message': 'Sesión cerrada exitosamente'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Error al cerrar sesión',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_api(request):
    """
    Vista API para obtener el perfil del usuario actual.
    
    Endpoint: GET /api/profile/
    Requiere: Token de autenticación en headers
    
    Respuestas:
    - 200: Datos del usuario
    - 401: No autorizado (sin token válido)
    """
    if request.method == 'GET':
        # Devolvemos los datos del usuario autenticado
        serializer = UserSerializer(request.user)
        
        return Response({
            'success': True,
            'user': serializer.data
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_username_api(request):
    """
    Vista API para verificar disponibilidad de nombre de usuario.
    
    Endpoint: GET /api/check-username/?username=nombreusuario
    
    Parámetros de query:
    - username: nombre de usuario a verificar
    
    Respuestas:
    - 200: Información sobre disponibilidad
    """
    username = request.GET.get('username', '')
    
    if not username:
        return Response({
            'success': False,
            'message': 'Debe proporcionar un nombre de usuario'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificamos si el username existe
    exists = User.objects.filter(username=username).exists()
    
    return Response({
        'success': True,
        'available': not exists,
        'message': 'Nombre de usuario no disponible' if exists else 'Nombre de usuario disponible'
    }, status=status.HTTP_200_OK)

@csrf_protect
@never_cache
def register_view(request):
    """
    Vista para el registro de usuarios
    """
    if request.user.is_authenticated:
        messages.info(request, 'Ya tienes una sesión activa.')
        return redirect('product_list')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Datos para enviar a la API
            user_data = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'password': form.cleaned_data['password1'],
                'password2': form.cleaned_data['password2'],
            }
            
            try:
                # Llamada a la API de registro
                response = requests.post(
                    f"{API_BASE_URL}register/",
                    json=user_data,
                    headers={
                        'Content-Type': 'application/json'
                    },
                    timeout=10
                )
                
                if response.status_code == 201:
                    # Registro exitoso
                    response_data = response.json()
                    
                    # Crear usuario localmente en Django
                    try:
                        user = User.objects.create_user(
                            username=user_data['username'],
                            email=user_data['email'],
                            first_name=user_data['first_name'],
                            last_name=user_data['last_name'],
                            password=user_data['password']
                        )
                        messages.success(
                            request, 
                            f'¡Registro exitoso! Bienvenido {user.first_name}. Tu cuenta ha sido creada.'
                        )
                        return redirect('login')
                    
                    except Exception as e:
                        messages.error(request, 'Error al crear usuario local. Intenta iniciar sesión.')
                        return redirect('login')
                        
                elif response.status_code == 400:
                    # Error en el registro - procesar errores específicos
                    try:
                        error_data = response.json()
                        if 'username' in error_data:
                            form.add_error('username', error_data['username'][0])
                        elif 'email' in error_data:
                            form.add_error('email', error_data['email'][0])
                        elif 'error' in error_data:
                            form.add_error(None, error_data['error'])
                        else:
                            form.add_error(None, 'Error en el registro. Verifica tus datos.')
                    except:
                        form.add_error(None, 'Error en el servidor. Intenta más tarde.')
                else:
                    form.add_error(None, f'Error del servidor: {response.status_code}')
                        
            except requests.RequestException as e:
                form.add_error(None, 'Error de conexión con el servidor. Verifica tu conexión a internet.')
                
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})


@csrf_protect
@never_cache
def login_view(request):
    """
    Vista para el login de usuarios
    """
    if request.user.is_authenticated:
        messages.info(request, 'Ya tienes una sesión activa.')
        return redirect('product_list')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Datos para enviar a la API
            login_data = {
                'username': username,
                'password': password,
            }
            
            try:
                # Llamada a la API de login
                response = requests.post(
                    f"{API_BASE_URL}login/",
                    json=login_data,
                    headers={
                        'Content-Type': 'application/json'
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    # Login exitoso en la API
                    response_data = response.json()
                    
                    # Intentar autenticar localmente en Django
                    user = authenticate(request, username=username, password=password)
                    
                    if user and user.is_active:
                        # Usuario existe localmente y está activo
                        login(request, user)
                        messages.success(
                            request, 
                            f'¡Bienvenido de nuevo, {user.first_name or user.username}!'
                        )
                        
                        # Guardar token en sesión si está disponible
                        if 'access_token' in response_data:
                            request.session['api_token'] = response_data['access_token']
                            request.session['refresh_token'] = response_data.get('refresh_token', '')
                        
                        # Redirigir a donde el usuario quería ir originalmente
                        next_url = request.GET.get('next', 'product_list')
                        return redirect(next_url)
                    else:
                        # El usuario existe en la API pero no localmente, crearlo
                        try:
                            user_info = response_data.get('user', {})
                            user = User.objects.create_user(
                                username=username,
                                email=user_info.get('email', ''),
                                first_name=user_info.get('first_name', ''),
                                last_name=user_info.get('last_name', '')
                            )
                            user.set_password(password)
                            user.save()
                            
                            # Autenticar al usuario recién creado
                            user = authenticate(request, username=username, password=password)
                            login(request, user)
                            
                            messages.success(
                                request, 
                                f'¡Bienvenido, {user.first_name or user.username}! Tu cuenta ha sido sincronizada.'
                            )
                            
                            # Guardar tokens
                            if 'access_token' in response_data:
                                request.session['api_token'] = response_data['access_token']
                                request.session['refresh_token'] = response_data.get('refresh_token', '')
                            
                            next_url = request.GET.get('next', 'product_list')
                            return redirect(next_url)
                            
                        except Exception as e:
                            form.add_error(None, 'Error al sincronizar usuario. Contacta al administrador.')
                            
                elif response.status_code == 400:
                    # Error en el login
                    try:
                        error_data = response.json()
                        error_message = error_data.get('error', 'Credenciales inválidas')
                        form.add_error(None, error_message)
                    except:
                        form.add_error(None, 'Credenciales inválidas. Verifica tu usuario y contraseña.')
                else:
                    form.add_error(None, f'Error del servidor: {response.status_code}')
                        
            except requests.RequestException as e:
                form.add_error(None, 'Error de conexión con el servidor. Verifica tu conexión a internet.')
                
    else:
        form = UserLoginForm()
    
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """
    Vista para cerrar sesión
    """
    username = request.user.username if request.user.is_authenticated else None
    
    # Opcional: llamar al endpoint de logout de la API
    if 'api_token' in request.session:
        try:
            requests.post(
                f"{API_BASE_URL}logout/",
                json={'refresh_token': request.session.get('refresh_token', '')},
                headers={
                    'Authorization': f'Bearer {request.session["api_token"]}',
                    'Content-Type': 'application/json'
                },
                timeout=5
            )
        except:
            pass  # Si falla, continuar con el logout local
        
        # Limpiar tokens de la sesión
        del request.session['api_token']
        if 'refresh_token' in request.session:
            del request.session['refresh_token']
    
    # Cerrar sesión en Django
    logout(request)
    
    if username:
        messages.success(request, f'Has cerrado sesión exitosamente, {username}. ¡Hasta pronto!')
    else:
        messages.success(request, 'Has cerrado sesión exitosamente.')
    
    return redirect('login')


# NUEVAS VISTAS PARA DASHBOARD, PERFIL Y CONFIGURACIÓN

@login_required
def dashboard(request):
    """
    Vista del dashboard del usuario con estadísticas personalizadas
    """
    try:
        # Intentar importar el modelo de productos
        from products.models import Product
        
        # Buscar productos del usuario - ajustar según tu modelo
        if hasattr(Product, 'created_by'):
            user_products = Product.objects.filter(created_by=request.user)
        elif hasattr(Product, 'user'):
            user_products = Product.objects.filter(user=request.user)
        else:
            # Si no hay campo de usuario, mostrar todos o ninguno
            user_products = Product.objects.none()
        
    except ImportError:
        # Si no existe el modelo Product, usar datos mock
        user_products = []
    
    # Estadísticas básicas
    user_products_count = len(user_products) if hasattr(user_products, '__len__') else user_products.count()
    edited_products_count = user_products_count  # Puedes ajustar esto según tu lógica
    total_views = user_products_count * 15  # Mock data
    favorite_products_count = user_products_count // 2  # Mock data
    
    # Productos recientes (últimos 5)
    recent_products = user_products[:5] if hasattr(user_products, '__getitem__') else list(user_products[:5])
    
    # Estadísticas por categoría
    category_stats = []
    if user_products_count > 0:
        try:
            categories = user_products.values('category').annotate(count=Count('category')).order_by('-count')
            total = user_products_count
            
            for cat in categories:
                percentage = (cat['count'] / total) * 100
                category_stats.append({
                    'category': cat['category'],
                    'count': cat['count'],
                    'percentage': percentage
                })
        except:
            # Mock data si hay error
            category_stats = [
                {'category': 'Electronics', 'count': user_products_count // 2, 'percentage': 50},
                {'category': 'Clothing', 'count': user_products_count // 3, 'percentage': 30},
                {'category': 'Books', 'count': user_products_count // 5, 'percentage': 20},
            ]
    
    context = {
        'user_products_count': user_products_count,
        'edited_products_count': edited_products_count,
        'total_views': total_views,
        'favorite_products_count': favorite_products_count,
        'recent_products': recent_products,
        'category_stats': category_stats,
    }
    
    return render(request, 'accounts/dashboard.html', context)


@login_required
def profile(request):
    """
    Vista del perfil del usuario
    """
    try:
        from products.models import Product
        
        # Productos del usuario
        if hasattr(Product, 'created_by'):
            user_products = Product.objects.filter(created_by=request.user)[:6]
        elif hasattr(Product, 'user'):
            user_products = Product.objects.filter(user=request.user)[:6]
        else:
            user_products = []
        
        user_products_count = len(user_products) if hasattr(user_products, '__len__') else user_products.count()
        
    except ImportError:
        user_products = []
        user_products_count = 0
    
    edited_count = user_products_count  # Ajustar según tu lógica
    
    context = {
        'user_products': user_products,
        'user_products_count': user_products_count,
        'edited_count': edited_count,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_settings(request):
    """
    Vista para configuración del perfil
    """
    try:
        from products.models import Product
        
        if hasattr(Product, 'created_by'):
            user_products_count = Product.objects.filter(created_by=request.user).count()
        elif hasattr(Product, 'user'):
            user_products_count = Product.objects.filter(user=request.user).count()
        else:
            user_products_count = 0
            
    except ImportError:
        user_products_count = 0
    
    if request.method == 'POST':
        # Actualizar información del usuario
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        
        try:
            user.save()
            messages.success(request, 'Tu información ha sido actualizada correctamente.')
        except Exception as e:
            messages.error(request, 'Error al actualizar la información. Intenta nuevamente.')
        
        return redirect('profile_settings')
    
    context = {
        'user_products_count': user_products_count,
    }
    
    return render(request, 'accounts/profile_settings.html', context)


@login_required
def change_password(request):
    """
    Vista para cambiar contraseña
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Importante para mantener la sesión
            messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
            return redirect('profile_settings')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    
    return redirect('profile_settings')