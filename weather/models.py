from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Weather(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    added = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.city

    class Meta:
        ordering = ['-added']
