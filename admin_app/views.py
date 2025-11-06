from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth import login,logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import inlineformset_factory

from .models import Category,Product,ProductVariant,ProductImage
from .forms import CategoryForm,ProductForm,ProductVariantForm,ProductImageForm



def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')# Create your views here.
        password = request.POST.get('password')
        user = authenticate(request,email=email,password=password)
        if user is not None:
            if user.is_admin:
                login(request,user)
                return redirect('admin_dashboard')
            else:
                messages.error(request,"You are not autherized to access admin panel.")
        else:
            messages.error(request,"Invalid email or password.")
    return render(request,'admin/admin_login.html')


@login_required(login_url='admin_login')
def admin_dashboard(request):
    if not request.user.is_admin:
        messages.error(request,"Unautherized access!")
        return redirect('admin_login')
    return render(request,'admin/base_admin.html')


@login_required(login_url='admin_login')
def admin_logout(request):
    logout(request)
    return redirect('admin_login')




def admin_category_list(request):
    categories = Category.objects.all_with_deleted().order_by('-created_at')


    paginator = Paginator(categories, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories':categories,
    }

    return render(request,'admin/category_list.html',context)


def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_category_list')
    else:
        form = CategoryForm()
    return render(request, 'admin/category_form.html', {'form': form})


def edit_category(request,id):
    category = Category.objects.all_with_deleted().get(id=id)
    form = CategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        form.save()
        return redirect('admin_category_list')
    return render(request, 'admin/category_form.html', {'form': form})


def delete_category(request, id):
    Category.objects.soft_delete(id)
    return redirect('admin_category_list')

VariantFormSet= inlineformset_factory(Product,ProductVariant,form=ProductVariantForm,extra=1,can_delete=True)

def admin_product_list(request):

    if request.GET.get('clear'):
        return redirect('admin_product_list')
    
    search_query= request.GET.get('q','').strip()
    products = Product.objects.all_with_deleted().order_by('-created_at')

    if search_query:
        products=Product.objects.filter(Q(name__icontains=search_query))


    paginator= Paginator(products,10)
    page_number= request.GET.get('page')
    page_obj= paginator.get_page(page_number)


    context={
        'page_obj':page_obj,
        'products':page_obj.object_list,
        'search_query':search_query
    }

    return render(request, 'admin/product_list.html',context)


def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        variant_formset=VariantFormSet(request.POST,prefix='variants')
        image_urls=request.POST.getlist('images')

        if len(image_urls)<3:
            messages.error(request,"Upload minimum 3 images")
            return render(request,'admin/product_form.html',{
                'form':form,
                'variant_formset':variant_formset
            })
        
        if form.is_valid() and variant_formset.is_valid():
            product=form.save()
            variant_formset.instance=product
            variant_formset.save()

            for idx,url in enumerate(image_urls):
                ProductImage.objects.create(
                    product=product,
                    image=url,
                    is_primary=(idx == 0)
                )
            messages.success(request, 'Product added successfully.')
            return redirect('admin_product_list')
        
    else:
        form = ProductForm()
        variant_formset=VariantFormSet(prefix='variants')

    return render(request, 'admin/product_form.html', {
        'form': form,
        'variant_formset':variant_formset
        })

def edit_product(request,id):
    product =Product.objects.all_with_deleted().get(id=id)
    variant_qs = ProductVariant.objects.all_with_deleted().filter(product=product)
    image_qs=ProductImage.objects.filter(product=product)


    if request.method == 'POST':

        form = ProductForm(request.POST, instance=product)
        variant_formset= VariantFormSet(request.POST,instance=product,prefix='Variants')
        image_urls=request.POST.getlist('images')

        if len(image_urls)<3:
            messages.error(request,"Upload minimum 3 images")
            return render(request,'admin/product_form.html',{
                'form':form,
                'variant_formset':variant_formset,
                'product':product,
                'existing_images':image_qs,

            })

        if form.is_valid() and variant_formset.is_valid():
            product=form.save()
            variant_formset.save()

        # delete old images and re-add
        ProductImage.objects.filter(product=product).delete()
        
        for idx, url in enumerate(image_urls):
            ProductImage.objects.create(
                product=product,
                image=url,
                is_primary=(idx==0)
            )

        messages.success(request, 'Product updated successfully.')
        return redirect('admin_product_list')
    else:
        form = ProductForm(instance=product)
        variant_formset=VariantFormSet(instance=product,prefix='variants')

    return render(request, 'admin/product_form.html', {
        'form': form,
         'variant_formset':variant_formset,
           'product': product,
           'existing_image':image_qs,
           })

def delete_product(request,id):
    if Product.objects.soft_delete(id)==None:
        messages.error(request,"Product already deleted.")
    else:
        messages.success(request, 'Product deleted successfully.')
    return redirect('admin_product_list')


def add_variant(request):
    product=ProductForm(request.POST.get('product_name'))
    if request.method=='POST':
        form=ProductVariantForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Variant added Successfully.")
            return redirect(admin_product_list)
    else:
        form = ProductVariantForm()
        return render(request,'admin/variant_form.html',{'form':form,'product':product})
    

def edit_variant(request,id):
    variant=ProductVariant.objects.all_with_deleted().get(id=id)
    if request.method=='POST':
        form=ProductVariantForm(request.POST,instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request,"Variant updated successfully.")
            return redirect('admin_product_list')
    else:
        form=ProductVariantForm(instance=variant)
        return render(request,'admin/variant_form.html',{'form':form,'variant':variant})
        

def delete_variant(request,id): 
    variant=ProductVariant.objects.soft_delete(id)
    if variant:
        messages.success(request,"Variant deleted Successfully.")
    return redirect('admin_product_list')




