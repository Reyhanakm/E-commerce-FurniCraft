from django.shortcuts import render,redirect,get_object_or_404
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from users.decorators import block_check
from django.contrib import messages
from .models import Cart,CartItem,OrderItem,Orders
from users.models import User,UserAddress
from product.models import Category,Product,ProductVariant
from .utils.trigger import trigger
from decimal import Decimal

@block_check
@login_required
def add_cart_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
    variant = product.variants.filter(is_deleted=False).first()
    return add_to_cart_logic(request, product, variant)

@block_check
@login_required
def add_cart_variant(request, variant_id):

    variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
    product = variant.product

    return add_to_cart_logic(request, product, variant)

@block_check
@login_required
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

@block_check
@login_required    
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
@block_check
@login_required
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


@block_check
@login_required
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

 

@block_check
@login_required
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

@block_check
@login_required
def cart_count(request):
    if not request.user.is_authenticated:
        return HttpResponse("0")  

    cart, created = Cart.objects.get_or_create(user=request.user)
    count = cart.items.count()

    return HttpResponse(count)

@block_check
@login_required
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

@login_required
def checkout(request):
    user=request.user
    cart,_=Cart.objects.get_or_create(user=user)
    
    products=cart.items.select_related("variant",'product').all()
    if not products.exists():
        messages.error(request,"Your cart is empty!")
        return redirect('cart_page')
    
    addresses=user.addresses.filter(is_deleted=False)

    subtotal=sum((i.variant.sales_price * i.quantity) for i in products)
    shipping_cost= 0 if subtotal>=1000 else 80
    total = subtotal + shipping_cost
    request.session["checkout_cart_update_at"]=cart.updated_at.timestamp()
    context={
        "products":products,
        "addresses":addresses,
        "subtotal":subtotal,
        "shipping_cost":shipping_cost,
        "total":total
    }
    return render(request,'commerce/checkout/checkout_page.html',context)

@login_required
def place_order(request):
    if request.method!="POST":
        return redirect('checkout')


    user=request.user
    cart,_=Cart.objects.get_or_create(user=user)

    last_checkout_time=request.session.get("checkout_cart_updated_at")

    if last_checkout_time and float(last_checkout_time)!=float(cart.updated_at.timestamp()):
        messages.error(request,"Your cart was updated. Please review checkout again.")
        return request('checkout')
    
    with transaction.atomic():
        items = cart.items.select_related("variant","product").select_for_update()

        if not items.exists():
            messages.error(request,"Your cart is empty!")
            return redirect("cart_page")

        address_id=request.POST.get('address')
        payment_method=request.POST.get('payment_method')

        address=get_object_or_404(UserAddress,id=address_id,user=user)

        for item in items:
            if item.quantity>item.variant.stock:
                messages.error(request,
                f"Only {item.variant.stock} left for {item.variant.material_type}. Please update your cart.")
                return redirect('cart_page')
            
        subtotal= sum(item.variant.sales_price*item.quantity for item in items)
        delivery_charge= 0 if subtotal >=1000 else 80
        total = subtotal+delivery_charge

        order = Orders.objects.create(
            user=user,
            address=address,
            total_price_before_discount=subtotal,
            total_price=total,
            payment_method=payment_method,
            delivery_charge=delivery_charge,
            
        )
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.variant,
                quantity=item.quantity,
                unit_price=item.variant.sales_price,
                price=item.variant.sales_price * item.quantity,

            )
            item.variant.stock -=item.quantity
            item.variant.save(update_fields=['stock'])
            messages.success(request, "Your order was placed successfully!")

    items.delete()

    request.session.pop('checkout_cart_updated_at',None)
    return redirect("order_success",order_id=order.order_id)

@login_required
def order_success(request,order_id):
    order=get_object_or_404(
        Orders.objects.select_related("address").prefetch_related("items__product"),
        order_id=order_id,
        user=request.user
    )
    return render(request,"commerce/order/order_success.html",{"order":order})

@login_required
def my_orders(request):
    orders=Orders.objects.filter(user=request.user).order_by("-created_at")
    return render(request,"commerce/order/my_orders.html",{"orders":orders})


@login_required
def user_order_detail(request, order_id):
    order = get_object_or_404(Orders, order_id=order_id, user=request.user)
    items = order.items.select_related("product", "product__product")
    return render(request, "commerce/order/order_details.html", {
        "order": order,
        "items": items,
    })
