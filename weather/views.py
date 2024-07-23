from datetime import datetime, date, timedelta

import requests
from django.conf import settings

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import FormView

from weather.models import Weather


# Create your views here.


class CustomLoginView(LoginView):
    template_name = 'weather/login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('current')


class RegisterPage(FormView):
    template_name = 'weather/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('current')

    def form_valid(self, form):
        user = form.save()
        if user is not None:
            login(self.request, user)
        return super(RegisterPage, self).form_valid(form)

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('tasks')
        return super(RegisterPage, self).get(*args, **kwargs)


@login_required(login_url=reverse_lazy('login'))
def current_weather(request):
    context = {}

    if request.method == 'POST':
        try:
            openweather = get_openweathermap_data('current', request)
            weatherapi = get_weatherapi_data('current', request)

            weather_data = aggregate_data(openweather, weatherapi)

            objects = Weather.objects.filter(user=request.user)

            add_option = 1

            for obj in objects:
                if weather_data['city'] == obj.city:
                    add_option = 0

            context = {'weather_data': weather_data, 'add_option': add_option}
        except KeyError:
            return render(request, 'weather/current.html', {'error': 1})
    else:
        objects = Weather.objects.filter(user=request.user)

        weather_list = []

        try:
            for obj in objects:
                openweather = get_openweathermap_data('current', obj=obj)
                weatherapi = get_weatherapi_data('current', obj=obj)

                weather_data = aggregate_data(openweather, weatherapi)

                weather_list.append({
                    'city': weather_data['city'],
                    'weather': weather_data
                })

                context = {'weather_list': weather_list}
        except KeyError:
            return render(request, 'weather/current.html', {'error': 2})

    return render(request, 'weather/current.html', context)


@login_required(login_url=reverse_lazy('login'))
def forecast(request):
    context = {}

    if request.method == 'POST':
        try:
            weather_data = get_weatherapi_data('forecast', request)

            objects = Weather.objects.filter(user=request.user)

            add_option = 1

            for obj in objects:
                if weather_data['city'] == obj.city:
                    add_option = 0

            context = {'weather_data': weather_data, 'add_option': add_option}
        except KeyError:
            return render(request, 'weather/forecasts.html', {'error': 1})
    else:
        objects = Weather.objects.filter(user=request.user)

        weather_list = []

        try:
            for obj in objects:
                weather_data = get_weatherapi_data('forecast', obj=obj)

                weather_list.append({
                    'city': weather_data['city'],
                    'weather': weather_data
                })

                context = {'weather_list': weather_list}
        except KeyError:
            return render(request, 'weather/current.html', {'error': 2})

    return render(request, 'weather/forecasts.html', context)


@login_required(login_url=reverse_lazy('login'))
def historical(request):
    if request.method == 'POST':
        try:
            weather_data = get_weatherapi_data('historical', request)
        except KeyError:
            return render(request, 'weather/historical.html', {'error': 1})
    else:
        weather_data = {}

    today = date.today()

    mindate = today - timedelta(days=365)

    today = today.strftime("%Y-%m-%d")
    mindate = mindate.strftime("%Y-%m-%d")

    context = {'weather_data': weather_data, 'today': today, 'mindate': mindate}
    return render(request, 'weather/historical.html', context)


@login_required(login_url=reverse_lazy('login'))
def add_to_list(request, name, lat, lon):
    if request.method == 'POST':
        user = request.user
        city = name
        lat = float(lat)
        lon = float(lon)

        Weather.objects.get_or_create(user=user, city=city, lat=lat, lon=lon)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


# REMEMBER TO ADD DELETE FUNCTION

@login_required(login_url=reverse_lazy('login'))
def delete_from_list(request, name, lat, lon):
    if request.method == 'POST':
        obj = get_object_or_404(Weather, user=request.user, city=name, lat=float(lat), lon=float(lon))
        obj.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def aggregate_data(response1, response2):
    weather_data = {
        'city': response1['city'],  # City
        'lat': response2['lat'],
        'lon': response2['lon'],
        'weather': response1['weather'],  # Weather Title
        'description': response1['description'],  # Weather Description
        'air_temp': round((response1['air_temp'] + response2['air_temp']) / 2, 2),  # Celsius
        'feels_like': round((response1['feels_like'] + response2['feels_like']) / 2, 2),  # Celsius
        'icon': response2['icon'],  # Icon
        'pressure': round((response1['pressure'] + response2['pressure']) / 2, 2),  # hPa/mBars
        'cloud_cover': int((response1['cloud_cover'] + response2['cloud_cover']) / 2),  # %
        'humidity': int((response1['humidity'] + response2['humidity']) / 2),  # %
        'visibility': int((response1['visibility'] + response2['visibility']) / 2),  # km
        'wind_speed': round((response1['wind_speed'] + response2['wind_speed']) / 2, 2),  # km/h
        'wind_gust': response2['wind_gust'],  # km/h
        'wind_degree': int((response1['wind_degree'] + response2['wind_degree']) / 2),  # Degrees
        'wind_direction': response2['wind_direction'],  # Compass (NSEW)
        'precipitation': response2['precipitation'],  # mm
        'hours': response2['hours'],
    }

    return weather_data

def get_weatherapi_data(type_of_request, post=None, obj=None):
    key = settings.BASE_DIR / 'API_KEY2'
    API_KEY = open(key, 'r').read()

    if type_of_request == 'current':

        current_weather = 'http://api.weatherapi.com/v1/forecast.json?key={}&q={}'

        if post:

            if post.POST.get('city'):
                response = requests.get(current_weather.format(API_KEY, post.POST.get('city'))).json()
            elif post.POST.get('lat') and post.POST.get('lon'):
                latlong = post.POST.get('lat') + ',' + post.POST.get('lon')
                response = requests.get(current_weather.format(API_KEY, latlong)).json()

        elif obj:
            if obj.city:
                response = requests.get(current_weather.format(API_KEY, obj.city)).json()
            elif obj.lat and obj.lon:
                latlong = obj.lat + ',' + obj.lon
                response = requests.get(current_weather.format(API_KEY, latlong)).json()
        else:
            raise KeyError

        localtime = response['location']['localtime']
        time = datetime.strptime(localtime, "%Y-%m-%d %H:%M")

        hours = []

        for hour in response['forecast']['forecastday'][0]['hour']:
            hourtime = datetime.strptime(hour['time'], "%Y-%m-%d %H:%M")

            if hourtime.hour >= time.hour:
                temp = hour['temp_c']
                icon = hour['condition']['icon']

                dictionary = {
                    'localtime': time.hour,
                    'hour': hourtime.hour,
                    'temp': temp,
                    'icon': icon,
                }

                hours.append(dictionary)

        weather_data = {
            'city': response['location']['name'],
            'lat': response['location']['lat'],
            'lon': response['location']['lon'],
            'air_temp': response['current']['temp_c'],  # Celsius
            'feels_like': response['current']['feelslike_c'],  # Celsius
            'icon': response['current']['condition']['icon'],  # Icon
            'pressure': response['current']['pressure_mb'],  # mBars/hPa
            'cloud_cover': response['current']['cloud'],  # %
            'humidity': response['current']['humidity'],  # %
            'visibility': response['current']['vis_km'],  # km
            'wind_speed': response['current']['wind_kph'],  # km/h
            'wind_gust': response['current']['gust_kph'],  # km/h
            'wind_degree': response['current']['wind_degree'],  # Degrees
            'wind_direction': response['current']['wind_dir'],  # Compass (NSEW)
            'precipitation': response['current']['precip_mm'],  # mm
            'hours': hours,
        }

    elif type_of_request == 'forecast':

        if post:
            forecast_url = "https://api.weatherapi.com/v1/forecast.json?key={}&q={}&days=7"

            if post.POST.get('city'):
                response = requests.get(forecast_url.format(API_KEY, post.POST.get('city'))).json()
            elif post.POST.get('lat') and post.POST.get('lon'):
                latlong = post.POST.get('lat') + ',' + post.POST.get('lon')
                response = requests.get(forecast_url.format(API_KEY, latlong)).json()
        elif obj:
            forecast_url = "https://api.weatherapi.com/v1/forecast.json?key={}&q={}&days=3"

            if obj.city:
                response = requests.get(forecast_url.format(API_KEY, obj.city)).json()
            elif obj.lat and obj.lon:
                latlong = obj.lat + ',' + obj.lon
                response = requests.get(forecast_url.format(API_KEY, latlong)).json()
        else:
            raise KeyError

        weather_data = {
            'city': response['location']['name'],
            'lat': response['location']['lat'],
            'lon': response['location']['lon'],
            'today': {
                'air_temp': response['current']['temp_c'],  # Celsius
                'icon': response['current']['condition']['icon'],  # Icon
                'pressure': response['current']['pressure_mb'],  # mBars/hPa
                'cloud_cover': response['current']['cloud'],  # %
                'humidity': response['current']['humidity'],  # %
                'visibility': response['current']['vis_km'],  # km
                'wind_speed': response['current']['wind_kph'],  # km/h
                'wind_gust': response['current']['gust_kph'],  # km/h
                'wind_degree': response['current']['wind_degree'],  # Degrees
                'wind_direction': response['current']['wind_dir'],  # Compass (NSEW)
                'precipitation': response['current']['precip_mm']  # mm
            },
        }

        forecast = response['forecast']['forecastday']

        days = []

        for day in forecast:

            if day == forecast[0]:
                word = 'Today'
            else:
                word = day['date']
                word = datetime.strptime(word, '%Y-%m-%d').date()
                word = word.strftime('%A')

            maxtemp = day['day']['maxtemp_c']
            mintemp = day['day']['mintemp_c']
            text = day['day']['condition']['text']
            precip = day['day']['totalprecip_mm']

            for hour in day['hour']:
                if hour['condition']['text'] == day['day']['condition']['text']:
                    icon = hour['condition']['icon']

            if icon is None:
                icon = day['hour'][11]['condition']['icon']

            days.append({
                'day': word,
                'maxtemp': maxtemp,
                'mintemp': mintemp,
                'text': text,
                'precipitation': precip,
                'icon': icon,
            })

        weather_data['days'] = days

    elif type_of_request == 'historical':

        historical_url = "https://api.weatherapi.com/v1/history.json?key={}&q={}&dt={}"

        if post.POST.get('date'):
            if post.POST.get('city'):
                response = requests.get(
                    historical_url.format(API_KEY, post.POST.get('city'), post.POST.get('date'))).json()
            elif post.POST.get('lat') and post.POST.get('lon'):
                latlong = post.POST.get('lat') + ',' + post.POST.get('lon')
                response = requests.get(historical_url.format(API_KEY, latlong, post.POST.get('date'))).json()

            forecastday = response['forecast']['forecastday'][0]

            hours = []

            for hour in forecastday['hour']:
                date_time = hour['time']
                time = datetime.strptime(date_time, "%Y-%m-%d %H:%M").time()

                dictionary = {
                    'hour': time.hour,
                    'temp': hour['temp_c'],
                    'icon': hour['condition']['icon'],
                }

                hours.append(dictionary)

                if hour['condition']['text'] == forecastday['day']['condition']['text']:
                    icon = hour['condition']['icon']

            if icon is None:
                icon = hours[11]['icon']

            weather_data = {
                'city': post.POST.get('city') if post.POST.get('city') else response['location']['name'],
                'maxtemp': forecastday['day']['maxtemp_c'],  # Celsius
                'mintemp': forecastday['day']['mintemp_c'],  # Celsius
                'avgtemp': forecastday['day']['avgtemp_c'],  # Celsius
                'icon': icon,  # Icon
                'weather': forecastday['day']['condition']['text'],  # Weather Title
                'humidity': forecastday['day']['avghumidity'],  # %
                'visibility': forecastday['day']['avgvis_km'],  # km
                'wind_speed': forecastday['day']['maxwind_kph'],  # km/h
                'hours': hours,
            }

        else:
            raise KeyError

    return weather_data


def get_openweathermap_data(type_of_request, post=None, obj=None):
    key = settings.BASE_DIR / 'API_KEY1'
    API_KEY = open(key, 'r').read()

    if type_of_request == 'current':

        if post:
            if post.POST.get('city'):
                current_weather = 'http://api.openweathermap.org/data/2.5/weather?q={}&appid={}'
                response = requests.get(current_weather.format(post.POST.get('city'), API_KEY)).json()
            elif post.POST.get('lat') and post.POST.get('lon'):
                current_weather_url = 'http://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid={}'
                response = requests.get(current_weather_url.format(
                    post.POST.get('lat'),
                    post.POST.get('lon'),
                    API_KEY
                )).json()
        elif obj:
            if obj.city:
                current_weather = 'http://api.openweathermap.org/data/2.5/weather?q={}&appid={}'
                response = requests.get(current_weather.format(obj.city, API_KEY)).json()
            elif obj.lat and obj.lon:
                current_weather = 'http://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&appid={}'
                response = requests.get(current_weather.format(obj.lat, obj.lon, API_KEY)).json()
        else:
            raise KeyError

        weather_data = {
            'city': response['name'],
            'weather': response['weather'][0]['main'],  # Weather Title
            'description': response['weather'][0]['description'].title(),  # Weather Desc.
            'air_temp': response['main']['temp'] - 273.15,  # Celsius
            'feels_like': response['main']['feels_like'] - 273.15,  # Celsius
            'pressure': response['main']['pressure'],  # hPa
            'cloud_cover': response['clouds']['all'],  # %
            'humidity': response['main']['humidity'],  # %
            'visibility': response['visibility'],  # km
            'wind_speed': response['wind']['speed'] * 3.6,  # km/h
            'wind_degree': response['wind']['deg'],  # degrees (meteorological)
        }

    return weather_data
