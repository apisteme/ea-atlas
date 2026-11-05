"""A small Excel (.xlsx) writer using only the Python standard library.

build_xlsx.py uses openpyxl when it is installed. In sandboxes without it (and without a way to install
packages, such as the Copilot Studio and Agent Builder skill sandboxes), it imports these stand-ins instead.
They cover only what build_xlsx.py uses: values, formulas, dates, number formats, bold headers, column
widths, frozen panes and an autofilter per table. Fills, conditional formatting and table styles are
accepted and ignored. Formulas are recalculated by Excel when the file opens.
"""
import datetime as _dt
import re as _re
import zipfile as _zip
from xml.sax.saxutils import escape as _esc

_BAD = _re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def get_column_letter(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def _split(ref):
    m = _re.match(r"^([A-Z]+)(\d+)$", ref)
    return int(m.group(2)), _col_index(m.group(1))


class _Style:
    def __init__(self, *a, **k):
        self.__dict__.update(k)


class Font(_Style):
    pass


class PatternFill(_Style):
    pass


class Alignment(_Style):
    pass


class Border(_Style):
    pass


class Side(_Style):
    pass


class TableStyleInfo(_Style):
    pass


class Table(_Style):
    def __init__(self, displayName="", ref="", **k):
        self.displayName, self.ref = displayName, ref
        self.tableStyleInfo = None


def CellIsRule(*a, **k):
    return None


def FormulaRule(*a, **k):
    return None


class _Cell:
    __slots__ = ("value", "font", "fill", "alignment", "number_format", "row", "column")

    def __init__(self, row, column, value=None):
        self.row, self.column, self.value = row, column, value
        self.font = self.fill = self.alignment = None
        self.number_format = "General"


class _Dim:
    def __init__(self):
        self.width = None


class _Dims(dict):
    def __missing__(self, k):
        v = self[k] = _Dim()
        return v


class _CF:
    def add(self, *a, **k):
        pass


class Worksheet:
    def __init__(self, title):
        self.title = title
        self._cells = {}
        self._max_row = 0
        self._max_col = 0
        self.freeze_panes = None
        self.column_dimensions = _Dims()
        self.conditional_formatting = _CF()
        self._filter = None

    def cell(self, row, column, value=None):
        c = self._cells.get((row, column))
        if c is None:
            c = self._cells[(row, column)] = _Cell(row, column)
            self._max_row = max(self._max_row, row)
            self._max_col = max(self._max_col, column)
        if value is not None:
            c.value = value
        return c

    def append(self, values):
        r = self._max_row + 1
        for i, v in enumerate(values, 1):
            self.cell(r, i, v)
        if not values:
            self._max_row = r

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.cell(key, c) for c in range(1, self._max_col + 1))
        r, c = _split(key)
        return self.cell(r, c)

    def __setitem__(self, key, value):
        r, c = _split(key)
        self.cell(r, c).value = value

    def iter_rows(self, min_row=1, max_row=None):
        for r in range(min_row, (max_row or self._max_row) + 1):
            yield tuple(self.cell(r, c) for c in range(1, self._max_col + 1))

    def add_table(self, t):
        self._filter = t.ref


class Workbook:
    def __init__(self):
        self._sheets = [Worksheet("Sheet")]

    @property
    def active(self):
        return self._sheets[0]

    @property
    def sheetnames(self):
        return [s.title for s in self._sheets]

    def create_sheet(self, title, index=None):
        ws = Worksheet(title)
        if index is None:
            self._sheets.append(ws)
        else:
            self._sheets.insert(index, ws)
        return ws

    def __getitem__(self, name):
        return next(s for s in self._sheets if s.title == name)

    # ---------------------------------------------------------------- writing
    _EPOCH = _dt.date(1899, 12, 30)

    @staticmethod
    def _style(c):
        nf = c.number_format or "General"
        if "yy" in nf:
            return 2 if nf.strip() == "yyyy-mm" else 1
        if "%" in nf:
            return 3 if "0.00" in nf else 4
        if nf.startswith("#,##0.00"):
            return 5
        if nf.startswith("#,##0"):
            return 6
        if c.font is not None and getattr(c.font, "bold", False):
            return 7
        return 0

    def _sheet_xml(self, ws):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">']
        if ws.freeze_panes:
            r, c = _split(ws.freeze_panes)
            xs, ys = c - 1, r - 1
            attrs = (f' xSplit="{xs}"' if xs else "") + (f' ySplit="{ys}"' if ys else "")
            pane = "bottomRight" if xs and ys else ("bottomLeft" if ys else "topRight")
            out.append(f'<sheetViews><sheetView workbookViewId="0"><pane{attrs} topLeftCell="{ws.freeze_panes}" activePane="{pane}" state="frozen"/></sheetView></sheetViews>')
        widths = [(k, v.width) for k, v in ws.column_dimensions.items() if v.width]
        if widths:
            out.append("<cols>" + "".join(f'<col min="{_col_index(k)}" max="{_col_index(k)}" width="{float(w):.1f}" customWidth="1"/>'
                                          for k, w in sorted(widths, key=lambda x: _col_index(x[0]))) + "</cols>")
        out.append("<sheetData>")
        rows = {}
        for (r, c), cell in ws._cells.items():
            rows.setdefault(r, []).append(cell)
        for r in sorted(rows):
            parts = []
            for cell in sorted(rows[r], key=lambda x: x.column):
                v = cell.value
                if v is None or (isinstance(v, str) and v == ""):
                    continue
                ref = f"{get_column_letter(cell.column)}{r}"
                st = self._style(cell)
                sa = f' s="{st}"' if st else ""
                if isinstance(v, bool):
                    parts.append(f'<c r="{ref}" t="b"{sa}><v>{int(v)}</v></c>')
                elif isinstance(v, (int, float)):
                    parts.append(f'<c r="{ref}"{sa}><v>{repr(float(v)) if isinstance(v, float) else v}</v></c>')
                elif isinstance(v, (_dt.datetime, _dt.date)):
                    d = v.date() if isinstance(v, _dt.datetime) else v
                    if not st:
                        sa = ' s="1"'
                    parts.append(f'<c r="{ref}"{sa}><v>{(d - self._EPOCH).days}</v></c>')
                else:
                    s = _BAD.sub("", str(v))
                    if s.startswith("="):
                        parts.append(f'<c r="{ref}"{sa}><f>{_esc(s[1:])}</f></c>')
                    else:
                        parts.append(f'<c r="{ref}" t="inlineStr"{sa}><is><t xml:space="preserve">{_esc(s)}</t></is></c>')
            out.append(f'<row r="{r}">' + "".join(parts) + "</row>")
        out.append("</sheetData>")
        if ws._filter:
            out.append(f'<autoFilter ref="{ws._filter}"/>')
        out.append("</worksheet>")
        return "".join(out)

    def save(self, path):
        n = len(self._sheets)
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
              '<Default Extension="xml" ContentType="application/xml"/>',
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
              '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
        ct += [f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, n + 1)]
        ct.append("</Types>")
        rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
        wb += [f'<sheet name="{_esc(s.title[:31])}" sheetId="{i}" r:id="rId{i}"/>' for i, s in enumerate(self._sheets, 1)]
        wb.append('</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
        wbr = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        wbr += [f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, n + 1)]
        wbr.append(f'<Relationship Id="rId{n + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                  '<numFmts count="3"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/><numFmt numFmtId="165" formatCode="yyyy-mm"/>'
                  '<numFmt numFmtId="166" formatCode="#,##0.00;(#,##0.00);&quot;-&quot;"/></numFmts>'
                  '<fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><name val="Arial"/></font></fonts>'
                  '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
                  '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                  '<cellXfs count="8"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                  '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
                  '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
                  '<xf numFmtId="10" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
                  '<xf numFmtId="9" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
                  '<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
                  '<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
                  '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
                  '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        with _zip.ZipFile(path, "w", _zip.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", "".join(ct))
            z.writestr("_rels/.rels", rels)
            z.writestr("xl/workbook.xml", "".join(wb))
            z.writestr("xl/_rels/workbook.xml.rels", "".join(wbr))
            z.writestr("xl/styles.xml", styles)
            for i, s in enumerate(self._sheets, 1):
                z.writestr(f"xl/worksheets/sheet{i}.xml", self._sheet_xml(s))
