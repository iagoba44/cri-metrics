# PLAN DE MEJORA EJECUTABLE - CRI Metrics System

## Fecha: Julio 2026
## Estado: EN EJECUCION

---

## MEJORA 1: Migrar datetime.utcnow() a timezone-aware (Eliminar warnings)

**Impacto:** Elimina 46 warnings de pytest.
**Archivos:** 8 archivos a modificar.

## MEJORA 2: Reemplazar @app.on_event por lifespan events (FastAPI moderno)

**Impacto:** Elimina DeprecationWarning de FastAPI.
**Archivo:** app/main.py

## MEJORA 3: Migrar pydantic BaseSettings a ConfigDict

**Impacto:** Elimina DeprecationWarning de pydantic.
**Archivo:** app/config.py

## MEJORA 4: Agregar retry con backoff en fuentes externas

**Impacto:** Reduce fallos por timeouts temporales.
**Archivos:** app/external/*.py

## MEJORA 5: Agregar endpoint de simulacion de alerta CRITICAL

**Impacto:** Permite testear el dashboard en zona CRITICAL sin esperar al mercado.
**Archivo:** app/api/v1/endpoints.py

---

## ORDEN DE EJECUCION

1. MEJORA 1: datetime (config, models, services, tests)
2. MEJORA 2: lifespan events (main.py)
3. MEJORA 3: ConfigDict (config.py)
4. MEJORA 4: retry (vast_ai_live, coingecko, binance)
5. MEJORA 5: simulacion CRITICAL (endpoints.py)
6. Tests completos
7. Relanzar servidor
