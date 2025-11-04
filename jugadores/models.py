from django.db import models

# Create your models here.
class Jugadores (models.Model):
    idJugador = models.AutoField(primary_key=True)
    nombreJugador = models.CharField(max_length=250, null= False)
    apellidoJugador = models.CharField(max_length=250, null= False)
    numeroCamisetaJugador = models.IntegerField
    posicionJugador = models.CharField(max_length=250,
        choices=[('Delantero', 'Mediocampista', 'Defensa', 'Portero')],
        null= False)
    jugadorActivo = models.BooleanField (default=False)
    
    class Meta:
        db_table = 'Jugador'
        
    def __str__(self):
        return self.nombreJugador
    
    