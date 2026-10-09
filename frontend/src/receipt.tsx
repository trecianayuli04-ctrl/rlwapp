import * as Print from "expo-print";

// Text-based tickets (32 columns = 58mm thermal). Same lines feed the on-screen preview,
// expo-print today, and can be sent as ESC/POS text to a Bluetooth printer later.
const W = 32;
const money = (n: number) => String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
const center = (t: string) => {
  const s = t.slice(0, W);
  return " ".repeat(Math.max(0, Math.floor((W - s.length) / 2))) + s;
};
const lr = (l: string, r: string) => {
  const left = l.slice(0, W - r.length - 1);
  return left + " ".repeat(Math.max(1, W - left.length - r.length)) + r;
};
const line = (c = "-") => c.repeat(W);
const wrap = (t: string) => (t || "").split("\n").flatMap((p) => p.match(new RegExp(`.{1,${W}}`, "g")) || [""]);

export type Station = "customer" | "bar" | "kitchen";
export const STATION_LABEL: Record<Station, string> = { customer: "Nota Customer", bar: "Nota Bar / Checker", kitchen: "Nota Dapur" };

export function ticketLines(sale: any, settings: any, station: Station): string[] {
  const r = settings?.receipt || {};
  const when = `${sale.date} ${sale.time || ""}`;
  const voided = sale.status === "void" || sale.status === "cancelled";
  if (station !== "customer") {
    const items = sale.items.filter((i: any) => (i.station || "bar") === station);
    if (!items.length) return [];
    return [
      center(station === "bar" ? "*** BAR / CHECKER ***" : "*** DAPUR ***"),
      center(r.cafe_name || "ROLLOW"),
      line("="),
      lr("No", sale.number),
      lr("Waktu", when),
      lr("Nama", sale.customer || "-"),
      lr("Kasir", sale.cashier_name),
      ...(sale.order_note ? wrap(`Catatan: ${sale.order_note}`) : []),
      line(),
      ...items.flatMap((i: any) => [`${i.qty} x ${i.name}`, ...(i.note ? wrap(`  > ${i.note}`) : [])]),
      line(),
      lr("Total item", String(items.reduce((a: number, i: any) => a + i.qty, 0))),
      ...(voided ? [line("="), center(`DIBATALKAN (${sale.status.toUpperCase()})`)] : []),
    ];
  }
  const out = [
    center(r.cafe_name || "ROLLOW"),
    ...wrap(r.address).map(center),
    ...(r.phone ? [center(`Telp ${r.phone}`)] : []),
    ...(r.header_note ? wrap(r.header_note).map(center) : []),
    line("="),
    lr("No", sale.number),
    lr("Waktu", when),
    ...(r.show_cashier !== false ? [lr("Kasir", sale.cashier_name)] : []),
    ...(r.show_customer !== false && sale.customer ? [lr("Pelanggan", sale.customer)] : []),
    line(),
    ...sale.items.flatMap((i: any) => [i.name, lr(`  ${i.qty} x ${money(i.price)}`, money(i.subtotal))]),
    line(),
    lr("Subtotal", money(sale.subtotal)),
    ...(sale.discount ? [lr(`Diskon ${sale.promo_name || ""}`.trim(), `-${money(sale.discount)}`)] : []),
    ...(sale.service ? [lr("Service", money(sale.service))] : []),
    ...(sale.tax ? [lr(`${sale.tax_name} ${sale.tax_percent}%`, money(sale.tax))] : []),
    lr("TOTAL", money(sale.total)),
    lr(`Bayar (${sale.payment_method})`, money(sale.cash_received || sale.total)),
    ...(sale.cash_received > sale.total ? [lr("Kembali", money(sale.cash_received - sale.total))] : []),
    ...(r.show_points !== false && sale.customer_id ? [line(), lr("Poin didapat", `+${sale.points_earned}`), lr("Total poin", String(sale.points_balance ?? "-"))] : []),
    line("="),
    ...(r.wifi ? [center(`WiFi: ${r.wifi}`)] : []),
    ...wrap(r.footer_note).map(center),
  ];
  if (voided) out.push(line("="), center(`*** ${sale.status.toUpperCase()} ***`), ...wrap(`Alasan: ${sale.void_reason || ""}`));
  return out;
}

export const stationsFor = (sale: any): Station[] =>
  (["customer", "bar", "kitchen"] as Station[]).filter((s) => s === "customer" || sale.items.some((i: any) => (i.station || "bar") === s));

export async function printTickets(sale: any, settings: any, stations: Station[]) {
  const pages = stations
    .map((st) => ticketLines(sale, settings, st))
    .filter((l) => l.length)
    .map((l) => `<pre>${l.join("\n").replace(/&/g, "&amp;").replace(/</g, "&lt;")}</pre>`)
    .join('<div style="page-break-after:always"></div>');
  const html = `<html><head><meta name="viewport" content="width=device-width"/><style>@page{size:58mm auto;margin:2mm}body{margin:0}pre{font-family:monospace;font-size:11px;line-height:1.3;margin:0 0 12px}</style></head><body>${pages}</body></html>`;
  await Print.printAsync({ html });
}
