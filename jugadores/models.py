from django.db import models

# Create your models here.
class Jugadores (models.Model):
    idjugador = models.AutoField(primary_key=True)
    idbanner = models.CharField(max_length=9, null=False, unique=True, error_messages={
        'unique': "Ya existe un jugador asociado a ese ID Banner."
    })
    nombrejugador = models.CharField(max_length=250, null= False)
    apellidojugador = models.CharField(max_length=250, null= False)
    numerocamisetajugador = models.IntegerField(null= False)
    imagenjugador = models.BinaryField(null=True, blank=True)
    posicionjugador = models.CharField(max_length=250,
        choices=[
            ('Delantero', 'Delantero'),
            ('Mediocampista', 'Mediocampista'),
            ('Defensa', 'Defensa'),
            ('Portero', 'Portero')
            ],
        null= False)
    jugadoractivo = models.BooleanField (default=False)
    
    class Meta:
        db_table = 'jugador'
        
    def __str__(self):
        return self.nombrejugador
    
