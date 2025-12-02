from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from .models import Cart,CartItem
from users.models import User
from product.models import Category,Product,ProductVariant
from .utils.trigger import trigger
from decimal import Decimal

def add_cart_product(request, product_id):

    product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)

    variant = product.variants.filter(is_deleted=False).first()

    return add_to_cart_logic(request, product, variant)

def add_cart_variant(request, variant_id):

    variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
    product = variant.product

    return add_to_cart_logic(request, product, variant)


def add_to_cart_logic(request, product, variant):
    quantity = int(request.POST.get("quantity", 1))

    if variant.stock < 1:
        return trigger("Product is out of stock.", "error")

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item = CartItem.objects.filter(cart=cart, variant=variant).first()

    if item:
        if item.quantity + quantity > variant.stock:
            return trigger("Only limited stock available.", "error")
        item.quantity += quantity
        item.save()
        return trigger("Quantity updated in cart!", "success", update=True)

    CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=quantity)
    return trigger("Product added to cart!", "success", update=True)

    
def cart_page(request):
    if not request.user.is_authenticated:
        return redirect("user_login")

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related("product", "variant").all()

    if request.GET.get("partial"):
        return render(request, "commerce/cart/_cart_content.html", {
            "cart": cart,
            "cart_items": cart_items,
        })

    return render(request, "commerce/cart/cart_page.html", {
        "cart": cart,
        "cart_items": cart_items,
    })

def increase_quantity(request, item_id):
    if not request.user.is_authenticated:
        return HttpResponse("")

    item = CartItem.objects.select_related("product", "variant", "cart").get(id=item_id)
    cart = item.cart

    if item.quantity < item.variant.stock and item.quantity < 5:
        item.quantity += 1
        item.save()

    cart_items = cart.items.all()
    response = render(request, "commerce/cart/_cart_content.html", {
        "cart_items": cart_items
    })
    response["HX-Trigger"] = "update-cart"
    return response



def decrease_quantity(request, item_id):
    if not request.user.is_authenticated:
        return HttpResponse("")

    item = CartItem.objects.select_related("cart").get(id=item_id)
    cart = item.cart

    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    # else:
    #     item.delete()

    cart_items = cart.items.all()
    response = render(request, "commerce/cart/_cart_content.html", {
        "cart_items": cart_items
    })
    response["HX-Trigger"] = "update-cart"
    return response

 


def remove_cart_item(request, item_id):
    if not request.user.is_authenticated:
        return HttpResponse("")

    item = CartItem.objects.filter(id=item_id, cart__user=request.user).first()
    cart = item.cart if item else None

    if item:
        item.delete()

    cart_items = cart.items.all()
    response = render(request, "commerce/cart/_cart_content.html", {
        "cart_items": cart_items
    })
    response["HX-Trigger"] = "update-cart"
    return response


def cart_count(request):
    if not request.user.is_authenticated:
        return HttpResponse("0")  

    cart, created = Cart.objects.get_or_create(user=request.user)
    count = cart.items.count()

    return HttpResponse(count)

def cart_totals(request):
    if not request.user.is_authenticated:
        return HttpResponse("")

    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related("variant", "product")
    if items.count() == 0:
        return HttpResponse("")

    subtotal =Decimal(0)

    for i in items:
        if not i.variant or i.variant.sales_price is None:
            continue
        subtotal += Decimal(i.variant.sales_price) * i.quantity

    if subtotal ==Decimal(0):
        shipping_cost=Decimal("0")
    else:
        shipping_cost = Decimal("0") if subtotal >= 1000 else Decimal("80")

    discount = Decimal("0")
    total = subtotal + shipping_cost - discount

    context = {
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "discount": discount,
        "total": total,
    }

    return render(request, "commerce/cart/_cart_totals.html", context)

