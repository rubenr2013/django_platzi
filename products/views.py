import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Product
import json

# URL base de la API de Platzi
PLATZI_API_URL = "https://api.escuelajs.co/api/v1/products"

def product_list(request):
    """Vista para mostrar la lista de productos con filtro por categoría"""
    
    # Obtener el filtro de categoría de la URL
    category_filter = request.GET.get('category', 'all')
    
    try:
        # Obtener productos de la API de Platzi
        response = requests.get(PLATZI_API_URL, timeout=10)
        if response.status_code == 200:
            api_products = response.json()[:50]  # Más productos para mejor filtro
            
            # Filtrar productos de API por categoría
            if category_filter != 'all':
                api_products = [
                    product for product in api_products 
                    if product.get('category', {}).get('name', '').lower() == category_filter.lower()
                ]
        else:
            api_products = []
            messages.error(request, "Error al cargar productos de la API")
    except requests.RequestException:
        api_products = []
        messages.error(request, "No se pudo conectar con la API de Platzi")
    
    # Obtener productos locales
    if category_filter == 'all':
        local_products = Product.objects.all()
    else:
        local_products = Product.objects.filter(category__icontains=category_filter)
    
    # Obtener IDs de productos de API que ya tienen copia local
    local_api_ids = set(Product.objects.filter(api_id__isnull=False).values_list('api_id', flat=True))
    
    # Marcar productos de API que ya tienen copia local
    for product in api_products:
        product['has_local_copy'] = product.get('id') in local_api_ids
    
    # Obtener todas las categorías disponibles para el filtro
    api_categories = set()
    try:
        all_products_response = requests.get(PLATZI_API_URL, timeout=10)
        if all_products_response.status_code == 200:
            for product in all_products_response.json()[:50]:
                category_name = product.get('category', {}).get('name', '')
                if category_name:
                    api_categories.add(category_name)
    except:
        pass
    
    local_categories = set(Product.objects.exclude(category='').values_list('category', flat=True))
    all_categories = sorted(list(api_categories.union(local_categories)))
    
    context = {
        'api_products': api_products,
        'local_products': local_products,
        'all_categories': all_categories,
        'current_category': category_filter,
        'total_api_products': len(api_products),
        'total_local_products': len(local_products),
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, product_id):
    """Vista para mostrar detalle de un producto de la API"""
    try:
        response = requests.get(f"{PLATZI_API_URL}/{product_id}", timeout=10)
        if response.status_code == 200:
            product = response.json()
        else:
            messages.error(request, "Producto no encontrado")
            return redirect('product_list')
    except requests.RequestException:
        messages.error(request, "Error al cargar el producto")
        return redirect('product_list')
    
    return render(request, 'products/product_detail.html', {'product': product})

def create_product(request):
    """Vista para crear un nuevo producto en la API"""
    if request.method == 'POST':
        data = {
            "title": request.POST.get('title'),
            "price": float(request.POST.get('price', 0)),
            "description": request.POST.get('description'),
            "categoryId": int(request.POST.get('category', 1)),
            "images": [request.POST.get('image', 'https://via.placeholder.com/300')]
        }
        
        try:
            response = requests.post(PLATZI_API_URL, json=data, timeout=10)
            if response.status_code == 201:
                # También guardar localmente
                Product.objects.create(
                    title=data['title'],
                    price=data['price'],
                    description=data['description'],
                    category=f"Category {data['categoryId']}",
                    image=data['images'][0]
                )
                messages.success(request, "Producto creado exitosamente")
                return redirect('product_list')
            else:
                messages.error(request, "Error al crear el producto")
        except requests.RequestException:
            messages.error(request, "No se pudo conectar con la API")
    
    return render(request, 'products/create_product.html')

def update_product(request, product_id):
    """Vista para actualizar un producto local"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.title = request.POST.get('title')
        product.price = request.POST.get('price')
        product.description = request.POST.get('description')
        product.category = request.POST.get('category')
        product.image = request.POST.get('image')
        product.save()
        
        messages.success(request, "Producto actualizado exitosamente")
        return redirect('product_list')
    
    return render(request, 'products/update_product.html', {'product': product})

def edit_api_product(request, api_product_id):
    """Vista para crear una copia local de un producto de la API y editarla"""
    
    # Verificar si ya existe una copia local
    existing_product = Product.objects.filter(api_id=api_product_id).first()
    
    if existing_product:
        # Si ya existe una copia, editamos esa
        if request.method == 'POST':
            existing_product.title = request.POST.get('title')
            existing_product.price = request.POST.get('price')
            existing_product.description = request.POST.get('description')
            existing_product.category = request.POST.get('category')
            existing_product.image = request.POST.get('image')
            existing_product.save()
            
            messages.success(request, "Producto actualizado exitosamente (copia local)")
            return redirect('product_list')
        
        return render(request, 'products/update_product.html', {'product': existing_product})
    
    else:
        # Si no existe, obtenemos el producto de la API y creamos la copia
        try:
            response = requests.get(f"{PLATZI_API_URL}/{api_product_id}", timeout=10)
            if response.status_code == 200:
                api_product = response.json()
                
                if request.method == 'POST':
                    # Crear nueva copia local con los datos editados
                    Product.objects.create(
                        api_id=api_product_id,
                        title=request.POST.get('title'),
                        price=request.POST.get('price'),
                        description=request.POST.get('description'),
                        category=request.POST.get('category', 'Sin categoría'),
                        image=request.POST.get('image')
                    )
                    messages.success(request, "Producto copiado y actualizado exitosamente")
                    return redirect('product_list')
                
                # Preparar datos del producto de la API para mostrar en el formulario
                product_data = {
                    'id': api_product_id,
                    'title': api_product.get('title', ''),
                    'price': api_product.get('price', 0),
                    'description': api_product.get('description', ''),
                    'category': api_product.get('category', {}).get('name', 'Sin categoría'),
                    'image': api_product.get('images', [''])[0] if api_product.get('images') else '',
                    'is_api_product': True  # Marcar que es de la API
                }
                
                return render(request, 'products/update_product.html', {
                    'product': product_data,
                    'is_new_copy': True
                })
            else:
                messages.error(request, "No se pudo obtener el producto de la API")
                return redirect('product_list')
        except requests.RequestException:
            messages.error(request, "Error de conexión con la API")
            return redirect('product_list')

def delete_product(request, product_id):
    """Vista para eliminar un producto local"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        product.delete()
        messages.success(request, "Producto eliminado exitosamente")
    
    return redirect('product_list')

def api_delete_product(request, product_id):
    """Vista para eliminar un producto de la API de Platzi"""
    if request.method == 'POST':
        try:
            response = requests.delete(f"{PLATZI_API_URL}/{product_id}", timeout=10)
            if response.status_code == 200:
                messages.success(request, "Producto eliminado de la API")
            else:
                messages.error(request, "Error al eliminar el producto de la API")
        except requests.RequestException:
            messages.error(request, "No se pudo conectar con la API")
    
    return redirect('product_list')