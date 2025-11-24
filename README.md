# Student Service (Jugadores) - Microservicio de Gestión de Jugadores

## Descripción

Este microservicio proporciona una API RESTful para la gestión de jugadores (estudiantes) en el sistema UDLAIA-Stats. Permite realizar operaciones CRUD (Crear, Leer, Actualizar, Eliminar) sobre la información de jugadores, incluyendo sus datos personales, posición, número de camiseta y estado de actividad.

## Propósito

El microservicio **Student Service** está diseñado para:
- Gestionar el registro y perfil de jugadores
- Almacenar información como nombre, apellido, ID Banner, número de camiseta y posición
- Controlar el estado de actividad de cada jugador
- Proporcionar endpoints para consultar, crear, actualizar y eliminar jugadores
- Soportar paginación para consultas masivas de jugadores

## Tecnologías

- **Framework**: Django 5.2.7 con Django REST Framework
- **Base de datos**: PostgreSQL
- **Puerto predeterminado**: 8030
- **Python**: 3.x

## Requisitos

- Python 3.x
- PostgreSQL
- Variables de entorno configuradas (ver sección de Configuración)

## Configuración

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
DEBUG=True
POSTGRES_DB=nombre_de_tu_bd
POSTGRES_USER=usuario_postgresql
POSTGRES_PASSWORD=contraseña_postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Instalación

1. Clona el repositorio:
```bash
git clone <url-del-repositorio>
cd studentservice
```

2. Crea un entorno virtual e instala las dependencias:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Ejecuta las migraciones:
```bash
python manage.py migrate
```

4. Inicia el servidor:
```bash
python manage.py runserver
```

El servidor estará disponible en `http://localhost:8030`

## Docker

La imagen Docker del microservicio está disponible en Docker Hub:

**URL**: https://hub.docker.com/repository/docker/dase123/udlaia-stats/tags/

### Uso con Docker

```bash
# Descargar la imagen
docker pull dase123/udlaia-stats:latest

# Ejecutar el contenedor
docker run -p 8030:8030 \
  -e POSTGRES_DB=tu_bd \
  -e POSTGRES_USER=tu_usuario \
  -e POSTGRES_PASSWORD=tu_contraseña \
  -e POSTGRES_HOST=host_bd \
  -e POSTGRES_PORT=5432 \
  dase123/udlaia-stats:latest
```

## Endpoints de la API

Base URL: `http://localhost:8030/api/`

**Nota**: Este servicio NO requiere autenticación para acceder a los endpoints.

### 1. Listar todos los jugadores (con paginación)

**GET** `/api/jugadores/`

Obtiene una lista paginada de todos los jugadores.

**Parámetros opcionales**:
- `page`: Número de página (default: 1)
- `offset`: Cantidad de resultados por página (default: 10)

**Ejemplo con curl**:
```bash
curl -X GET "http://localhost:8030/api/jugadores/?page=1&offset=10"
```

**Respuesta**:
```json
{
  "count": 25,
  "page": 1,
  "offset": 10,
  "pages": 3,
  "results": [
    {
      "idjugador": 1,
      "nombrejugador": "Juan",
      "apellidojugador": "Pérez",
      "numerocamisetajugador": 10,
      "posicionjugador": "Delantero",
      "jugadoractivo": true,
      "idbanner": "B00123456"
    }
  ]
}
```

### 2. Obtener todos los jugadores

**GET** `/api/jugadores/all/`

Similar al endpoint anterior, obtiene todos los jugadores con paginación.

**Ejemplo con curl**:
```bash
curl -X GET "http://localhost:8030/api/jugadores/all/?page=1&offset=20"
```

### 3. Crear un nuevo jugador

**POST** `/api/jugadores/`

Crea un nuevo jugador en el sistema.

**Body (JSON)**:
```json
{
  "nombrejugador": "María",
  "apellidojugador": "González",
  "numerocamisetajugador": 7,
  "posicionjugador": "Mediocampista",
  "jugadoractivo": true,
  "idbanner": "B00789012"
}
```

**Posiciones válidas**:
- `Delantero`
- `Mediocampista`
- `Defensa`
- `Portero`

**Ejemplo con curl**:
```bash
curl -X POST http://localhost:8030/api/jugadores/ \
  -H "Content-Type: application/json" \
  -d '{
    "nombrejugador": "María",
    "apellidojugador": "González",
    "numerocamisetajugador": 7,
    "posicionjugador": "Mediocampista",
    "jugadoractivo": true,
    "idbanner": "B00789012"
  }'
```

**Respuesta exitosa**:
```json
{
  "mensaje": "Jugador creado correctamente",
  "jugador": {
    "idjugador": 2,
    "nombrejugador": "María",
    "apellidojugador": "González",
    "numerocamisetajugador": 7,
    "posicionjugador": "Mediocampista",
    "jugadoractivo": true,
    "idbanner": "B00789012"
  }
}
```

### 4. Obtener detalle de jugador por ID Banner

**GET** `/api/jugadores/<banner>/`

Obtiene información de un jugador específico usando su ID Banner.

**Ejemplo con curl**:
```bash
curl -X GET http://localhost:8030/api/jugadores/B00123456/
```

**Respuesta**:
```json
{
  "idjugador": 1,
  "nombrejugador": "Juan",
  "apellidojugador": "Pérez",
  "numerocamisetajugador": 10,
  "posicionjugador": "Delantero",
  "jugadoractivo": true,
  "idbanner": "B00123456"
}
```

### 5. Obtener detalle de jugador por ID

**GET** `/api/jugadores/id/<id>/`

Obtiene información de un jugador específico usando su ID interno.

**Ejemplo con curl**:
```bash
curl -X GET http://localhost:8030/api/jugadores/id/1/
```

### 6. Actualizar jugador

**PATCH** `/api/jugadores/<id>/update/`

Actualiza parcialmente los datos de un jugador existente.

**Body (JSON)** - Todos los campos son opcionales:
```json
{
  "numerocamisetajugador": 9,
  "jugadoractivo": false
}
```

**Ejemplo con curl**:
```bash
curl -X PATCH http://localhost:8030/api/jugadores/1/update/ \
  -H "Content-Type: application/json" \
  -d '{
    "numerocamisetajugador": 9,
    "jugadoractivo": false
  }'
```

**Respuesta exitosa**:
```json
{
  "mensaje": "Jugador actualizado correctamente",
  "jugador": {
    "idjugador": 1,
    "nombrejugador": "Juan",
    "apellidojugador": "Pérez",
    "numerocamisetajugador": 9,
    "posicionjugador": "Delantero",
    "jugadoractivo": false,
    "idbanner": "B00123456"
  }
}
```

### 7. Eliminar jugador

**DELETE** `/api/jugadores/<banner>/delete/`

Elimina un jugador del sistema usando su ID Banner.

**Ejemplo con curl**:
```bash
curl -X DELETE http://localhost:8030/api/jugadores/B00123456/delete/
```

**Respuesta exitosa**:
```json
{
  "mensaje": "Jugador eliminado correctamente"
}
```

## Manejo de Errores

### Error 400 - Bad Request
```json
{
  "error": "Los parámetros 'page' y 'offset' deben ser enteros positivos."
}
```

### Error 404 - Not Found
Cuando el jugador no existe:
```json
{
  "detail": "No encontrado."
}
```

### Error de validación
```json
{
  "idbanner": ["Ya existe un jugador asociado a ese ID Banner"]
}
```

## Modelo de Datos

### Jugador (Jugadores)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `idjugador` | AutoField | ID único del jugador (PK) |
| `idbanner` | CharField(9) | ID Banner único del estudiante |
| `nombrejugador` | CharField(250) | Nombre del jugador |
| `apellidojugador` | CharField(250) | Apellido del jugador |
| `numerocamisetajugador` | IntegerField | Número de camiseta |
| `posicionjugador` | CharField | Posición: Delantero, Mediocampista, Defensa, Portero |
| `jugadoractivo` | BooleanField | Estado de actividad (default: False) |

## Arquitectura

Este microservicio es parte de la arquitectura de microservicios UDLAIA-Stats:

- **authservice**: Gestión de autenticación y autorización
- **studentservice** (este servicio): Gestión de jugadores/estudiantes
- **teamservice**: Gestión de equipos
- **statsservice**: Gestión de estadísticas

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## Licencia

Este proyecto es parte del sistema UDLAIA-Stats.

## Contacto

Para más información sobre el proyecto, visita:
- Docker Hub: https://hub.docker.com/repository/docker/dase123/udlaia-stats/tags/
