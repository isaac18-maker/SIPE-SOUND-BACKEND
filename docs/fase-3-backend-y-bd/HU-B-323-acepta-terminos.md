# HU-B-323 · Exigir la aceptación de términos en el registro

| Campo | Valor |
|---|---|
| Fase | 3 · Backend y BD |
| Prioridad | Must |
| Estimación | 1 punto |
| Depende de | HU-B-322 |
| Rama | `hu/HU-B-323-acepta-terminos` |
| Relacionada | HU-F-313 (casilla de términos en el registro) |

## Historia
**Como** equipo
**quiero** que la API no cree cuentas sin la aceptación de los términos
**para** que el consentimiento del tratamiento de datos (Ley 1581 de 2012) no dependa solo del formulario.

## Alcance
- `RegistroIn.acepta_terminos: StrictBool`, obligatorio; si no es `true`, 400 con
  `"acepta_terminos: Debes aceptar los términos y condiciones."`.
- Contrato 04 §4.1.1 y §7 actualizados.

**No incluye**: guardar la fecha o la versión de los términos aceptados (requiere migración; nueva HU
si el equipo la necesita como evidencia).

## Criterios de aceptación
```gherkin
Escenario: Sin aceptación
  Cuando envío POST /auth/registro sin acepta_terminos o con false
  Entonces recibo 400 VALIDACION con "acepta_terminos: Debes aceptar los términos y condiciones."

Escenario: Con aceptación
  Cuando envío acepta_terminos: true y datos válidos
  Entonces recibo 201 "Te enviamos un correo para confirmar tu cuenta."
```

## Orden de merge
Backend primero: el frontend de HU-F-313 ya envía `acepta_terminos`; el backend anterior lo
rechazaría como campo extra (400).
