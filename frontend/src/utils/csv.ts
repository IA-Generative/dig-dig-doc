/** CSV compatible Excel français : séparateur « ; » et BOM UTF-8. */
export function toCsv(headers: string[], rows: string[][]): string {
  const escape = (cell: string) => (/[;"\n\r]/.test(cell) ? `"${cell.replace(/"/g, '""')}"` : cell);
  return "﻿" + [headers, ...rows].map((r) => r.map(escape).join(";")).join("\r\n");
}

export function downloadCsv(filename: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
