from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

urlpatterns = [
    # Login, Logout and Register
    path('login/', views.CustomLoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(next_page='login'), name="logout"),
    path('register/', views.RegisterPage.as_view(), name="register"),
    # Current Weather
    path('', views.current_weather, name='current'),
    # Weather Forecasts
    path('forecasts/', views.forecast, name='forecasts'),
    # Historical Data
    path('historical-data/', views.historical, name='historical-data'),
    # Add to List
    path('add/<str:name>/<str:lat>/<str:lon>/', views.add_to_list, name='add'),
    # Delete from List
    path('delete/<str:name>/<str:lat>/<str:lon>/', views.delete_from_list, name='delete'),
]
