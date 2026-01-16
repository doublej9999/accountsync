"""
URL configuration for accountsync project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework import routers

from syncservice.views import HrPersonViewSet, HrPersonAccountViewSet, SyncConfigViewSet

router = routers.DefaultRouter()
router.register(r"hr-persons", HrPersonViewSet)
router.register(r"hr-person-accounts", HrPersonAccountViewSet)
router.register(r"sync-configs", SyncConfigViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include(router.urls)),
    # --- DRF Spectacular 文档路由 ---
    # 1. Schema 下载接口 (JSON/YAML)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # 2. Swagger UI (交互式文档)
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # 3. ReDoc (更美观的文档)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
