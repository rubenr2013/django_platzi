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
        return redirect('products:product_list')
    
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
                            password=user_data['password'],
                            password2=user_data['password2']
                        )
                        messages.success(
                            request, 
                            f'¡Registro exitoso! Bienvenido {user.first_name}. Tu cuenta ha sido creada.'
                        )
                        return redirect('accounts:login')
                    
                    except Exception as e:
                        messages.error(request, 'Error al crear usuario local. Intenta iniciar sesión.')
                        return redirect('accounts:login')
                        
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
        return redirect('products:product_list')
    
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
                        next_url = request.GET.get('next', 'products:product_list')
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
                            
                            next_url = request.GET.get('next', 'products:product_list')
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
    
    return redirect('accounts:login')