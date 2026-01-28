from django import template

register = template.Library()

@register.filter
def get_primary_image(image_queryset):
    """
    Returns the first image object in the queryset where is_primary=True.
    Falls back to the first image if no primary is found.
    """
    try:
        # Attempt to get the image where is_primary is True
        return image_queryset.get(is_primary=True)
    except image_queryset.model.DoesNotExist:
        # If no primary image exists, return the first one available
        return image_queryset.first()
    except:
        # Handle cases where the queryset is empty or other errors
        return None