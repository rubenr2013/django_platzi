import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Product
import json

# URL base de la API de Platzi
PLATZI_API_URL = "https://api.escuelajs.co/api/v1/products"

def product_list(request):
    """Vista para mostrar la lista de productos"""
    try:
        # Obtener productos de la API de Platzi
        response = requests.get(PLATZI_API_URL, timeout=10)
        if response.status_code == 200:
            api_products = response.json()[:20]  # Limitar a 20 productos
        else:
            api_products = []
            messages.error(request, "Error al cargar productos de la API")
    except requests.RequestException:
        api_products = []
        messages.error(request, "No se pudo conectar con la API de Platzi")
    
    # Obtener productos locales
    local_products = Product.objects.all()
    
    context = {
        'api_products': api_products,
        'local_products': local_products,
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