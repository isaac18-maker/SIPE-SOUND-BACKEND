# 06 · Plantilla de Historia de Usuario (HU-prompt)

Cada HU de este repositorio es a la vez **historia de usuario** y **prompt
ejecutable** por un agente de IA. Copie esta plantilla para crear una nueva.

- Identificador: `HU-B-<fase><consecutivo>` → `HU-B-305` (fase 3, consecutivo 05).
- Archivo: `docs/<carpeta-fase>/HU-B-305-titulo-corto.md`.
- Estimación en puntos Fibonacci (1, 2, 3, 5, 8). Si es > 8, se divide.

---

````markdown
# HU-B-XXX · <Título en infinitivo>

| Campo | Valor |
|---|---|
| Fase | 2 · Reestructuración / 3 · Rediseño |
| Prioridad | Must · Should · Could |
| Estimación | N puntos |
| Depende de | HU-B-YYY, HU-F-ZZZ |
| Rama | `hu/HU-B-XXX-<slug>` |

## Historia
**Como** <rol>
**quiero** <capacidad>
**para** <beneficio medible>.

## Contexto
<Estado actual con rutas reales de archivos. Qué problema hay hoy.>

## Alcance
**Incluye**
- ...

**No incluye**
- ...

## Prompt de ejecución
```text
<Instrucción autocontenida para el agente. Debe poder ejecutarse sin leer
nada más que el contrato + esta HU.>
```

## Pasos
1. ...
2. ...

## Criterios de aceptación
```gherkin
Escenario: <nombre>
  Dado ...
  Cuando ...
  Entonces ...
```

## Verificación manual
```bash
<comandos y salida esperada>
```

## Definición de hecho específica
- [ ] ...
(además del DoD general de 07-definicion-de-hecho.md)
````

---

## Buenas prácticas al redactar una HU

- **INVEST**: Independiente, Negociable, Valiosa, Estimable, Pequeña, Testeable (verificable manualmente).
- Rutas de archivo **reales**; nunca "el archivo de rutas".
- Los criterios de aceptación describen **comportamiento observable**, no implementación.
- El *Prompt de ejecución* repite las restricciones críticas (p. ej. "no cambies la forma de la respuesta") aunque estén en el contrato: los agentes priorizan lo cercano.
