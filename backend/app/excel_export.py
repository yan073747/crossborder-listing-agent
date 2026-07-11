from __future__ import annotations

import html
import io
import zipfile
from datetime import datetime, timezone
from typing import Any


HEADERS = [
    "ID",
    "Product Name",
    "Market",
    "Language",
    "Generation Source",
    "Provider",
    "Recommended Version",
    "Score",
    "Title",
    "Bullet Points",
    "SEO Keywords",
    "Ad Copy",
    "Title Completeness",
    "Keyword Coverage",
    "Benefit Clarity",
    "Localization Quality",
    "Ad Conversion Potential",
    "Optimization Reasons",
    "Created At",
]


def build_listing_runs_xlsx(rows: list[dict[str, Any]]) -> bytes:
    workbook_buffer = io.BytesIO()
    sheet_rows = [HEADERS]
    for row in rows:
        response = row.get("response", {})
        versions = response.get("versions", [])
        best = max(versions, key=lambda item: item.get("score", 0)) if versions else {}
        breakdown = best.get("score_breakdown", {})
        sheet_rows.append(
            [
                row.get("id", ""),
                row.get("product_name", ""),
                row.get("target_market", ""),
                row.get("target_language", ""),
                response.get("generation_source", ""),
                response.get("generation_provider", ""),
                best.get("version", ""),
                best.get("score", ""),
                best.get("title", ""),
                "\n".join(best.get("bullet_points", [])),
                ", ".join(best.get("seo_keywords", [])),
                best.get("ad_copy", ""),
                breakdown.get("title_completeness", ""),
                breakdown.get("keyword_coverage", ""),
                breakdown.get("benefit_clarity", ""),
                breakdown.get("localization_quality", ""),
                breakdown.get("ad_conversion_potential", ""),
                "\n".join(best.get("optimization_reasons", [])),
                row.get("created_at", ""),
            ]
        )

    with zipfile.ZipFile(workbook_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("docProps/app.xml", _app_xml())
        archive.writestr("docProps/core.xml", _core_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(sheet_rows))
    return workbook_buffer.getvalue()


def _worksheet_xml(rows: list[list[Any]]) -> str:
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            style = ' s="1"' if row_index == 1 else ""
            cells.append(f'<c r="{cell_ref}" t="inlineStr"{style}><is><t>{_escape(value)}</t></is></c>')
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    columns = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate([8, 24, 16, 14, 16, 14, 18, 10, 44, 54, 36, 46, 18, 18, 16, 20, 22, 52, 20], start=1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <cols>{columns}</cols>
  <sheetData>{''.join(xml_rows)}</sheetData>
</worksheet>'''


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=False)


def _content_types_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''


def _root_relationships_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def _workbook_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Listing Runs" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>'''


def _workbook_relationships_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''


def _styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" applyFont="1"/></cellXfs>
</styleSheet>'''


def _app_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Listing Optimization Agent</Application>
</Properties>'''


def _core_xml() -> str:
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Listing Optimization Runs</dc:title>
  <dc:creator>Listing Optimization Agent</dc:creator>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
</cp:coreProperties>'''
