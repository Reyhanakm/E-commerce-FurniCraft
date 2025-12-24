from datetime import datetime, timedelta
from commerce.models import OrderItem
from django.utils.timezone import now

def get_date_range(range_type, start_date, end_date):
    today = now().date()

    if range_type == "daily":
        return today, today

    if range_type == "weekly":
        return today - timedelta(days=7), today

    if range_type == "monthly":
        return today.replace(day=1), today

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            return start, end
        except ValueError:
            return None, None

    return None, None

def get_sold_items(start_date=None, end_date=None):
    qs = OrderItem.objects.filter(
        status="delivered",
        order__payment_status__in=["paid", "partially_refunded"]
    ).select_related("order")

    if start_date and end_date:
        qs = qs.filter(order__created_at__date__range=[start_date, end_date])

    return qs
