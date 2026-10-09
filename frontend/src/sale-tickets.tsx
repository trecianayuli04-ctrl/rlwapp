import { useState } from "react";
import { Text, View } from "react-native";

import { api, rp } from "@/src/api";
import { useAuth } from "@/src/auth";
import { printTickets, Station, STATION_LABEL, stationsFor } from "@/src/receipt";
import { TicketPreview } from "@/src/ticket-preview";
import { Badge, Btn, Chips, Field, sp, STATUS_TONE, useStyles, useToast } from "@/src/ui";

// Shared body for POS "after pay" and Riwayat Nota detail: preview 3 tickets, print, void/cancel
export function SaleTickets({ sale, settings, onVoided }: { sale: any; settings: any; onVoided?: (s: any) => void }) {
  const s = useStyles();
  const toast = useToast();
  const { can } = useAuth();
  const stations = stationsFor(sale);
  const [st, setSt] = useState<Station>("customer");
  const [voidKind, setVoidKind] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const status = sale.status || "paid";
  const voided = status === "void" || status === "cancelled";

  const print = async (list: Station[]) => {
    try {
      await printTickets(sale, settings, list);
    } catch (e: any) {
      toast(e.message || "Gagal print", "error");
    }
  };
  const doVoid = async () => {
    setBusy(true);
    try {
      await api(`/sales/${sale.id}/void`, { body: { kind: voidKind, reason } });
      toast(voidKind === "void" ? "Nota di-void, stok & keuangan dikembalikan" : "Pesanan dibatalkan, stok & keuangan dikembalikan");
      onVoided?.({ ...sale, status: voidKind, void_reason: reason });
      setVoidKind(null);
      setReason("");
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={{ gap: sp.md }}>
      <View style={[s.row, { justifyContent: "space-between" }]}>
        <Text style={s.title} testID="sale-number-text">{sale.number}</Text>
        <Badge label={status === "paid" ? "LUNAS" : status === "void" ? "VOID" : "DIBATALKAN"} tone={voided ? "error" : "success"} />
      </View>
      <Text style={s.sub}>{sale.date} {sale.time} · {sale.cashier_name} · {rp(sale.total)}</Text>
      {voided && <Text style={[s.sub, { color: undefined }]}>Alasan: {sale.void_reason} {sale.void_by ? `· oleh ${sale.void_by}` : ""}</Text>}
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="ticket-tab" value={st} onChange={setSt} options={stations.map((x) => ({ label: STATION_LABEL[x], value: x }))} />
      </View>
      <TicketPreview sale={sale} settings={settings} station={st} />
      <View style={s.row}>
        <Btn title="Print Semua Nota" icon="print-outline" style={{ flex: 1 }} testID="print-all-button" onPress={() => print(stations)} />
        <Btn title="Print Ini" variant="secondary" style={{ flex: 1 }} testID="print-one-button" onPress={() => print([st])} />
      </View>
      {!voided && can("sales_void") && !voidKind && (
        <View style={s.row}>
          <Btn title="Void" variant="ghost" icon="close-circle-outline" style={{ flex: 1 }} testID="void-sale-button" onPress={() => setVoidKind("void")} />
          <Btn title="Batalkan Pesanan" variant="ghost" icon="ban-outline" style={{ flex: 1 }} testID="cancel-sale-button" onPress={() => setVoidKind("cancelled")} />
        </View>
      )}
      {voidKind && (
        <View>
          <Field label={voidKind === "void" ? "Alasan void (salah input, dll)" : "Alasan pembatalan pesanan"} testID="void-reason-input" value={reason} onChangeText={setReason} />
          <View style={s.row}>
            <Btn title="Kembali" variant="ghost" style={{ flex: 1 }} testID="void-back-button" onPress={() => setVoidKind(null)} />
            <Btn title={voidKind === "void" ? "Konfirmasi Void" : "Konfirmasi Batal"} variant="danger" style={{ flex: 1 }} loading={busy} disabled={!reason.trim()} testID="void-confirm-button" onPress={doVoid} />
          </View>
        </View>
      )}
    </View>
  );
}

export { STATUS_TONE };
