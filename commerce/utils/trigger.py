import json
from django.http import HttpResponse

def trigger(message, type="info", update=False):
    response = HttpResponse("")

    data = {
        "toast": {
            "message": message,
            "type": type
        }
    }

    if update:
        data["update-cart"] = True

    response["HX-Trigger"] = json.dumps(data)
    return response

