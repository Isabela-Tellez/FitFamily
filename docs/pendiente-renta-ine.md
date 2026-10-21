# Fase pendiente — Renta neta media por sección censal (INE)

> Estado: **documentado, no implementado**. Preparado para una segunda fase.
> Responsable: Persona 1. Última verificación de metadatos: 21/10/2026 (ver §2).

## 1. Qué desbloquea

El análisis de "identificar oportunidades de negocio" está limitado por una variable
que no está en ninguna fuente municipal: **la capacidad de gasto de los hogares del
entorno**. Con ella se puede:

- Estimar la cuota mensual asumible por hogar (precio del gimnasio con ludoteca).
- Segmentar la clientela por tramos de renta.
- Ponderar la demanda por sección censal en lugar de por barrio.

## 2. Fuente

| Campo | Valor |
|---|---|
| Organismo | Instituto Nacional de Estadística (INE) |
| Conjunto | Atlas de Distribución de Renta de los Hogares (ADRH) |
| Operación | 30325 (`urn:ine:es:OPER:30325`) |
| Acceso | https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736177088&menu=ultiDatos&idp=1254735976608 |
| Catálogo | https://datos.gob.es/es/catalogo/ea0042823-atlas-de-distribucion-de-renta-de-los-hogares-adrh |
| Formatos | HTML y descarga en **pc-axis, Excel y CSV** |
| Cobertura geográfica | España, por **sección censal** (incluye Comunidad de Madrid) |
| Datos | Renta neta y bruta por hogar, por persona y por unidad de consumo; distribución por fuente de ingresos; indicadores de desigualdad monetaria |
| Naturaleza | **Estadística Experimental** (el INE la marca como tal) |
| Periodo | Edición 2024 (datos de 2024) |
| Actualización indicada | 21/10/2025 |
| Licencia | https://www.ine.es/aviso_legal |

## 3. Limitaciones que deben viajar con el dato

1. **Es una estadística experimental**: el INE no garantiza la continuidad metodológica
   entre ediciones. Cualquier serie temporal debe declarar la edición.
2. **La base son datos tributarios**: no todos los hogares con renta media están
   representados, y la renta se asigna al hogar según reglas fiscales, no al lugar de
   residencia de cada persona.
3. **No es un promedio de distrito**: el valor por sección censal no se puede
   agregar "a ojo"; hay que usar la clave geográfica (código de sección censal) y
   documentar la fuente.
4. **Periodo de referencia ≠ fecha de consulta**: los datos son de 2024 aunque la
   descarga se haga en 2026.

## 4. Cómo se integraría

1. Descargar el CSV de la operación 30325 (o el fichero de la sección censal de
   Madrid) y filtrar por los códigos de sección del barrio.
2. Contrastar la cobertura: las 9 secciones de El Cañaveral (19052, 19053, 19054,
   19055, 19056, 19058, 19059, 19060, 19061) deben aparecer todas; si falta alguna,
   el indicador queda `null` con la limitación registrada.
3. Publicar con `reference_period` = "2024" y `consulted_at` = fecha de descarga, en
   clave `verification_status: "verified"` solo si la sección está en la fuente
   oficial.
4. Añadir el cruce con la cohorte 0-4 y 5-9 (ya disponible en el Padrón) para
   obtener "renta por niño de 0 a 4 años" como variable de demanda.

## 5. Estado

- Fuentes de renta **no descargadas** ni procesadas: no se ha realizado ninguna
  descarga, por lo que no se afirma ningún valor de renta.
- Pendiente: descarga, comprobación de cobertura de las 9 secciones, y tests de
  regresión del cruce.
