from .models import Advertisement
from django.shortcuts import render
def google_adds(request):
    ads = Advertisement.objects.filter(is_active=True)
    
    def get_ad(order):
        return ads.filter(order=order).first()

    context = {
        'ad_1': get_ad(1), 
        'ad_2': get_ad(2), 
        'ad_3': get_ad(3),  
        'ad_4': get_ad(4),  
        'ad_5': get_ad(5), 
        'ad_6': get_ad(6),
        'ad_7': get_ad(7), 
        'ad_8': get_ad(8), 
        'ad_9': get_ad(9), 
        'ad_10': get_ad(10),
    }

    return (context)