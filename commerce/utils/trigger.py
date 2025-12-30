import json
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib import messages

def trigger(message, type="info", update=False, wishlist_update=False):
    response = HttpResponse("") 
    
    if update or wishlist_update:
        response.status_code = 204
    
    data = {
        "toast": {
            "message": message,
            "type": type
        }
    }
    if update:
        data["update-cart"] = True

    if wishlist_update:
        data["wishlistUpdated"] = True 

    response["HX-Trigger"] = json.dumps(data)
    return response


def attach_trigger(response, message, type="info", update=False, wishlist_update=False):
    data = {
        "toast": {
            "message": message,
            "type": type
        }
    }
    if update:
        data["update-cart"] = True
    if wishlist_update:
        data["wishlistUpdated"] = True

    response["HX-Trigger"] = json.dumps(data)
    return response

def notify(request,*,message,level="info",response=None,update=False,wishlist_update=False,):
    if request.headers.get("HX-Request"):
        if response:
            return attach_trigger(response,message,type=level,update=update,wishlist_update=wishlist_update,)
        return trigger(message,type=level,update=update,wishlist_update=wishlist_update,)
    getattr(messages, level)(request, message)
    return redirect("checkout")

