# Plan: Replace Hardcoded Mappings with Dynamic ArcGIS Metadata

## Context

`apps/reports/mappings.py` (~580 lines) contains hardcoded Python dicts that map ArcGIS coded values to display labels, field names to Italian labels, and define field ordering. These mappings were ported from PHP and duplicate information that already exists in the ArcGIS layer definitions (field aliases and coded value domains). This creates maintenance burden and will multiply as new apps (segnalazioni) need their own mappings.

**Goal:** Fetch `FIELD_LABELS` and `FIELD_VALUES` dynamically from ArcGIS REST API, externalize `FIELD_ORDER` and `DATE_FIELDS` to a config file, and keep the same public API so consumers don't change.

---

## Step 1: Add Layer Settings — `config/settings.py`

Add `ARCGIS_LAYERS` dict and metadata cache TTL:

```python
ARCGIS_LAYERS = {
    'reports': {'main': 0, 'pk_pav': 1, 'imprese': 2, 'foto': 3},
    # 'segnalazioni': {'main': N},  # future
}
ARCGIS_METADATA_CACHE_TTL = int(os.getenv('ARCGIS_METADATA_CACHE_TTL', 86400))  # 24h
```

---

## Step 2: Add `get_layer_definition()` — `apps/core/services/arcgis.py`

Add method to `ArcGISService` that calls `{FEATURE_SERVICE_URL}/{layer_id}?f=json&token=...` to fetch the layer definition JSON (which includes `fields[]` with `name`, `alias`, `type`, and `domain.codedValues`).

Add module-level convenience function matching existing pattern.

---

## Step 3: Create Metadata Registry — `apps/core/services/field_metadata.py` (NEW)

Central module that:
1. Fetches layer definitions via Step 2
2. Parses `fields[].alias` → labels, `fields[].domain.codedValues` → value maps
3. Caches in Django cache with `ARCGIS_METADATA_CACHE_TTL`
4. Provides `get_registry(layer_id)` → `FieldMetadataRegistry` with `.get_label()`, `.get_value()`, `.invalidate_cache()`

**Fallback:** If ArcGIS is unreachable and no cache exists, return empty dicts — labels fall back to title-cased field names, values show raw codes. No 500 errors.

---

## Step 4: Extract Structural Config — `apps/reports/field_config.py` (NEW)

Move `FIELD_ORDER` and `DATE_FIELDS` from `mappings.py` to a standalone Python config file. These are display/structural concerns not available from ArcGIS.

```python
FIELD_ORDER = {
    'main': ['id_report', 'nome_operatore', ...],  # same content
    'pk_pav': ['corsia', ...],
    'impresa': ['nome_impresa', ...],
}

DATE_FIELDS = {
    'data_rilevamento': '%d/%m/%Y',
    'ora_rilevamento': '%H:%M',
    'created_date': '%d/%m/%Y %H:%M',
    'last_edited_date': '%d/%m/%Y %H:%M',
}
```

No new dependencies needed (no YAML).

---

## Step 5: Rewrite `apps/reports/mappings.py`

Replace hardcoded `FIELD_LABELS` and `FIELD_VALUES` with delegation to the metadata registry. The public API stays identical:

- `get_field_label(field_name)` → looks up cached ArcGIS aliases
- `get_field_value(field_name, value)` → looks up cached coded value domains
- `process_attributes()`, `process_features()`, `format_date()` → unchanged logic, just delegate to above

Helper: `_get_merged_metadata()` merges metadata across all report layers (0, 1, 2) for unified lookup. Hits cache (dict lookup), actual HTTP fetch only on cache miss.

---

## Step 6: Update Hardcoded Layer IDs — `apps/reports/services/report_data.py`

Replace `query_feature_layer(0, ...)`, `query_feature_layer(1, ...)`, etc. with:
```python
LAYERS = settings.ARCGIS_LAYERS['reports']
query_feature_layer(LAYERS['main'], ...)
```

Same for `apps/reports/views/api.py` (line 198, 255).

**No import changes needed** in any consumer — the mappings.py public API is preserved.

---

## Step 7: Management Command — `apps/core/management/commands/refresh_field_metadata.py` (NEW)

Pre-fetches and caches metadata for all configured layers. Run at deploy time or via cron to avoid first-request latency.

```
python manage.py refresh_field_metadata
```

---

## Execution Order

| Step | Files | Depends On | Parallelizable |
|------|-------|------------|----------------|
| 1 | `config/settings.py` | — | Yes (with 4) |
| 2 | `apps/core/services/arcgis.py` | 1 | |
| 3 | `apps/core/services/field_metadata.py` | 2 | |
| 4 | `apps/reports/field_config.py` | — | Yes (with 1) |
| 5 | `apps/reports/mappings.py` | 3, 4 | |
| 6 | `report_data.py`, `api.py` | 1 | Yes (with 5) |
| 7 | `refresh_field_metadata.py` | 3 | Yes (with 5, 6) |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ArcGIS aliases differ from current hardcoded labels | Visual check after switch; can override in field_config.py if needed |
| LocMemCache is per-process | Acceptable — metadata is small, fetches rare. Move to Redis later if needed |
| First-request latency on cold cache | Management command warms cache at deploy |
| Multiple layers with overlapping field names | Current code already uses distinct names (e.g. `km_iniz` vs `km_iniz_pav`); verify with live ArcGIS response |

---

## Verification

1. `python manage.py check` — no issues
2. `python manage.py refresh_field_metadata` — prints field counts per layer
3. Start dev server, load report list page — verify labels and coded values display correctly
4. Load a report detail/PDF — verify all fields render with proper labels
5. Compare a few records side-by-side with current production to catch alias mismatches
