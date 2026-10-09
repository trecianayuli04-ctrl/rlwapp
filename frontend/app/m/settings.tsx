import { useEffect, useState } from "react";
import { Switch, Text, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, num, useApi } from "@/src/api";
import { TicketPreview } from "@/src/ticket-preview";
import { Btn, Card, Chips, Field, Header, Page, sp, StateView, useStyles, useToast } from "@/src/ui";

const SAMPLE = {
  number: "RLW-CONTOH-0001", date: "2026-01-01", time: "19:30", cashier_name: "Andi", customer: "Budi", customer_id: "x",
  items: [
    { name: "French Fries", qty: 1, price: 18000, subtotal: 18000, station: "kitchen" },
    { name: "Coklat Panas", qty: 2, price: 20000, subtotal: 40000, station: "bar" },
  ],
  subtotal: 58000, discount: 0, service: 0, tax: 5800, tax_name: "PB1", tax_percent: 10, total: 63800,
  payment_method: "Cash", cash_received: 70000, points_earned: 1, points_balance: 12, status: "paid",
};

export default function Settings() {
  const s = useStyles();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { data, loading, error, reload } = useApi<any>("/settings");
  const [f, setF] = useState<any>(null);
  const [preview, setPreview] = useState<"customer" | "bar" | "kitchen">("customer");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (data) setF({ ...data, tax_percent: String(data.tax_percent), service_percent: String(data.service_percent), points_per_nota: String(data.points_per_nota), points_min_purchase: String(data.points_min_purchase), points_per_amount: String(data.points_per_amount), late_tolerance_min: String(data.late_tolerance_min), late_penalty_fixed: String(data.late_penalty_fixed), late_penalty_per_minute: String(data.late_penalty_per_minute) });
  }, [data]);
  const set = (k: string) => (v: any) => setF({ ...f, [k]: v });
  const setR = (k: string) => (v: any) => setF({ ...f, receipt: { ...f.receipt, [k]: v } });

  const save = async () => {
    setBusy(true);
    try {
      await api("/settings", { method: "PUT", body: { ...f, tax_percent: num(f.tax_percent), service_percent: num(f.service_percent), points_per_nota: Math.round(num(f.points_per_nota)), points_min_purchase: num(f.points_min_purchase), points_per_amount: num(f.points_per_amount), late_tolerance_min: Math.round(num(f.late_tolerance_min)), late_penalty_fixed: num(f.late_penalty_fixed), late_penalty_per_minute: num(f.late_penalty_per_minute) } });
      toast("Pengaturan disimpan");
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  const Toggle = ({ label, value, onChange, testID }: any) => (
    <View style={[s.row, { justifyContent: "space-between", marginBottom: sp.md }]}>
      <Text style={[s.title, { flex: 1, fontSize: 15 }]}>{label}</Text>
      <Switch testID={testID} value={value} onValueChange={onChange} />
    </View>
  );

  return (
    <Page>
      <Header back title="Pengaturan Kasir" subtitle="Pajak, poin loyalti & tampilan struk" />
      {!f ? <StateView loading={loading} error={error} onRetry={reload} /> : (
        <KeyboardAwareScrollView bottomOffset={24} keyboardShouldPersistTaps="handled" contentContainerStyle={[s.list, { paddingBottom: insets.bottom + sp.xl }]}>
          <Card>
            <Text style={[s.title, { marginBottom: sp.md }]}>Pajak & Service</Text>
            <Toggle label="Aktifkan pajak" value={f.tax_enabled} onChange={set("tax_enabled")} testID="tax-enabled-switch" />
            <Toggle label="Tombol pajak di kasir default ON" value={f.tax_default_on} onChange={set("tax_default_on")} testID="tax-default-switch" />
            <View style={s.row}>
              <View style={{ flex: 1 }}><Field label="Nama pajak" testID="tax-name-input" value={f.tax_name} onChangeText={set("tax_name")} /></View>
              <View style={{ flex: 1 }}><Field label="Persen pajak (%)" testID="tax-percent-input" keyboardType="numeric" value={f.tax_percent} onChangeText={set("tax_percent")} /></View>
            </View>
            <Field label="Service charge (%) — 0 bila tidak dipakai" testID="service-percent-input" keyboardType="numeric" value={f.service_percent} onChangeText={set("service_percent")} />
          </Card>
          <Card>
            <Text style={[s.title, { marginBottom: sp.md }]}>Poin Loyalti Pelanggan</Text>
            <Toggle label="Aktifkan poin" value={f.loyalty_enabled} onChange={set("loyalty_enabled")} testID="loyalty-enabled-switch" />
            <Field label="Poin per nota" testID="points-per-nota-input" keyboardType="numeric" value={f.points_per_nota} onChangeText={set("points_per_nota")} />
            <Field label="Minimal belanja agar dapat poin (Rp)" testID="points-min-input" keyboardType="numeric" value={f.points_min_purchase} onChangeText={set("points_min_purchase")} />
            <Field label="Bonus +1 poin setiap kelipatan (Rp, 0 = nonaktif)" testID="points-amount-input" keyboardType="numeric" value={f.points_per_amount} onChangeText={set("points_per_amount")} />
          </Card>
          <Card>
            <Text style={[s.title, { marginBottom: sp.md }]}>Absensi & Keterlambatan</Text>
            <Field label="Toleransi telat (menit)" testID="late-tolerance-input" keyboardType="numeric" value={f.late_tolerance_min} onChangeText={set("late_tolerance_min")} />
            <View style={s.row}>
              <View style={{ flex: 1 }}><Field label="Potongan per kali telat (Rp)" testID="late-fixed-input" keyboardType="numeric" value={f.late_penalty_fixed} onChangeText={set("late_penalty_fixed")} /></View>
              <View style={{ flex: 1 }}><Field label="Potongan per menit telat (Rp)" testID="late-minute-input" keyboardType="numeric" value={f.late_penalty_per_minute} onChangeText={set("late_penalty_per_minute")} /></View>
            </View>
            <Text style={s.sub}>Telat dihitung dari jam masuk tiap karyawan (atur di Payroll → Atur Gaji). Bila melewati toleransi, gaji otomatis terpotong.</Text>
          </Card>
          <Card>
            <Text style={[s.title, { marginBottom: sp.md }]}>Tampilan Struk</Text>
            <Field label="Nama cafe" testID="receipt-name-input" value={f.receipt.cafe_name} onChangeText={setR("cafe_name")} />
            <Field label="Alamat" testID="receipt-address-input" value={f.receipt.address} onChangeText={setR("address")} multiline />
            <Field label="No. telepon" testID="receipt-phone-input" value={f.receipt.phone} onChangeText={setR("phone")} />
            <Field label="Catatan atas (header)" testID="receipt-header-input" value={f.receipt.header_note} onChangeText={setR("header_note")} multiline />
            <Field label="Password WiFi" testID="receipt-wifi-input" value={f.receipt.wifi} onChangeText={setR("wifi")} />
            <Field label="Catatan bawah (footer)" testID="receipt-footer-input" value={f.receipt.footer_note} onChangeText={setR("footer_note")} multiline />
            <Toggle label="Tampilkan nama kasir" value={f.receipt.show_cashier} onChange={setR("show_cashier")} testID="receipt-cashier-switch" />
            <Toggle label="Tampilkan nama pelanggan" value={f.receipt.show_customer} onChange={setR("show_customer")} testID="receipt-customer-switch" />
            <Toggle label="Tampilkan poin" value={f.receipt.show_points} onChange={setR("show_points")} testID="receipt-points-switch" />
          </Card>
          <Text style={s.section}>Pratinjau Struk</Text>
          <View style={{ marginHorizontal: -sp.lg }}>
            <Chips testPrefix="settings-preview" value={preview} onChange={setPreview} options={[{ label: "Customer", value: "customer" }, { label: "Bar / Checker", value: "bar" }, { label: "Dapur", value: "kitchen" }]} />
          </View>
          <TicketPreview sale={{ ...SAMPLE, tax: f.tax_enabled ? SAMPLE.tax : 0, tax_name: f.tax_name, tax_percent: num(f.tax_percent) }} settings={f} station={preview} />
          <Btn title="Simpan Pengaturan" icon="save-outline" testID="settings-save-button" loading={busy} onPress={save} />
        </KeyboardAwareScrollView>
      )}
    </Page>
  );
}
