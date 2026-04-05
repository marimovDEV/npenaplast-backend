from django.db import models

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)

    def __str__(self):
        return self.name
