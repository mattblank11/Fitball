from django.contrib import admin
from django.urls import path, include
from django.views.static import serve
from django.conf.urls import url, handler404, handler500, url, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('fitball_app.urls')),
]

urlpatterns += [
    url(r'media/(?P<path>.*)$', serve, { 'document_root': settings.MEDIA_ROOT, }),
]

admin.site.site_header = 'Fitball Admin'