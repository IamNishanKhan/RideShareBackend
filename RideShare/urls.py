from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rides.views import CompleteRideView

admin.site.site_header = 'Ride Share App Admin'
admin.site.index_title = 'Admin'
admin.site.site_title = 'Ride Share'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/rides/', include('rides.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('api/rides/<int:ride_id>/complete/', CompleteRideView.as_view(), name='complete-ride'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)