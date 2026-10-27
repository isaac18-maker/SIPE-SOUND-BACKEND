# HU-B-415 · Solicitudes de cambio de nombre pendientes de aceptación

| Campo | Valor |
|---|---|
| Fase | 5 · Experiencia y visualización |
| Prioridad | Must |
| Estimación | 5 puntos |
| Depende de | HU-B-407, HU-B-414 |
| Rama | `hu/HU-B-415-solicitudes-de-cambio-de-nombre` |
| Relacionada | HU-F-515 |

## Historia
**Como** administrador
**quiero** ver las solicitudes de cambio de nombre como solicitudes pendientes, separadas entre estudiantes y docentes
**para** saber con precisión a qué persona le voy a habilitar el cambio.

## Alcance
**Incluye**
1. Migración 0031: `solicitudes_nombre` (pendiente, aceptada, rechazada), una pendiente por
   persona; las resueltas quedan como historial.
2. `POST /me/solicitud-nombre` guarda además la solicitud (se conserva el aviso a los admins) y
   `GET /me/solicitud-nombre` devuelve la última para mostrar su estado en la cuenta.
3. `GET /admin/solicitudes-nombre` (filtros `estado` y `rol`, totales por rol y estado) y
   `PATCH /admin/solicitudes-nombre/{id}`: aceptar activa `puede_editar_nombre` de esa cuenta y
   queda en la auditoría de acciones del admin; rechazar solo la cierra.

**No incluye**
- Retirar el aviso por mensajería (se mantiene como segunda vía de aviso).
- Que el permiso se desactive solo tras editar el nombre (sigue manual, como en HU-B-407).

## Criterios de aceptación (Gherkin)
```gherkin
Escenario: Solicitar
  Cuando un estudiante pide cambiar su nombre
  Entonces queda una solicitud pendiente y no puede enviar otra hasta que se resuelva

Escenario: Aceptar
  Cuando un admin la acepta
  Entonces esa cuenta puede editar su nombre y la acción queda auditada

Escenario: Separación
  Cuando el admin filtra por rol
  Entonces ve solo las de estudiantes o solo las de docentes, con sus totales
```

## Definición de hecho específica
- [ ] Migración 0031 aplicada (`uv run alembic upgrade head`).
- [ ] Ninguna respuesta incluye correos.
