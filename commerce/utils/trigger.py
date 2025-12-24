import json
from django.http import HttpResponse

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

