import { useState } from "react";
import { FlatList, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, num, rp, useApi } from "@/src/api";
import { PayrollLive } from "@/src/payroll-live";
import { Badge, Btn, Card, Chips, Field, Header, Page, Sheet, sp, StateView, STATUS_TONE, useStyles, useToast } from "@/src/ui";

const month = () => new Date().toISOString().slice(0, 7);

export default function Payroll() {
  const s = useStyles();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { data, loading, error, reload } = useApi<any[]>("/payroll");
  const { data: users } = useApi<any[]>("/users");
  const [open, setOpen] = useState(false);
  const [uid, setUid] = useState("");
  const [bonus, setBonus] = useState("");
  const [ded, setDed] = useState("");
  const [busy, setBusy] = useState(false);
  const staff = (users || []).filter((u) => u.role !== "owner" && u.is_active);

  const submit = async () => {
    setBusy(true);
    try {
      await api("/payroll", { body: { user_id: uid, month: month(), bonus: num(bonus), deduction: num(ded) } });
      toast("Payroll dibuat dari data absensi");
      setOpen(false);
      setBonus("");
      setDed("");
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  const pay = async (id: string) => {
    try {
      await api(`/payroll/${id}/pay`, { body: {} });
      toast("Gaji dibayar & tercatat di pengeluaran");
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    }
  };

  return (
    <Page>
      <Header back title="Payroll" subtitle={`Periode ${month()}`} right={<Btn small title="Buat" icon="add" testID="payroll-add-button" onPress={() => { setUid(staff[0]?.id ?? ""); setOpen(true); }} />} />
      {!data ? <StateView loading={loading} error={error} onRetry={reload} /> : (
        <FlatList
          data={data}
          keyExtractor={(p) => p.id}
          contentContainerStyle={[s.list, { paddingBottom: insets.bottom + sp.xl }]}
          ListHeaderComponent={
            <View style={{ gap: sp.md }}>
              <PayrollLive onCreate={(id) => { setUid(id); setOpen(true); }} />
              <Text style={s.section}>Slip Gaji Bulan Ini</Text>
            </View>
          }
          ListEmptyComponent={<StateView empty="Belum ada payroll bulan ini" />}
          renderItem={({ item: p }) => (
            <Card testID={`payroll-item-${p.id}`}>
              <View style={[s.row, { justifyContent: "space-between" }]}>
                <Text style={[s.title, { flex: 1 }]}>{p.name}</Text>
                <Badge label={p.status.toUpperCase()} tone={STATUS_TONE[p.status]} />
              </View>
              <Text style={s.sub}>{p.hours ?? 0} jam × {rp(p.hourly_rate)} = {rp(p.hourly_pay)} · Gaji {rp(p.base_salary)} · Tunjangan {rp(p.allowance)} · Bonus {rp(p.bonus)}</Text>
              <Text style={s.sub}>Lembur {rp(p.overtime)} ({p.attendance.lembur_hours} jam) · Telat −{rp(p.late_penalty)} · Potongan {rp(p.deduction)}</Text>
              <Text style={s.sub}>Hadir {p.attendance.clock_in} · Izin {p.attendance.izin} · Sakit {p.attendance.sakit} · Libur {p.attendance.libur}</Text>
              <View style={[s.row, { justifyContent: "space-between", marginTop: sp.sm }]}>
                <Text style={s.value}>{rp(p.total)}</Text>
                {p.status !== "paid" && <Btn small title="Bayar" variant="success" testID={`payroll-pay-${p.id}`} onPress={() => pay(p.id)} />}
              </View>
            </Card>
          )}
        />
      )}
      <Sheet visible={open} onClose={() => setOpen(false)} title="Buat Payroll" testID="payroll-sheet">
        <View style={{ marginHorizontal: -sp.lg }}>
          <Chips testPrefix="payroll-user" value={uid} onChange={setUid} options={staff.map((u) => ({ label: u.name, value: u.id }))} />
        </View>
        {(() => {
          const u = staff.find((x) => x.id === uid);
          return u ? <Text style={[s.sub, { marginBottom: sp.md }]}>{u.position} · Gaji {rp(u.base_salary)} · Tunjangan {rp(u.allowance)}</Text> : null;
        })()}
        <Field label="Bonus (Rp)" testID="payroll-bonus-input" keyboardType="numeric" value={bonus} onChangeText={setBonus} />
        <Field label="Potongan lain (Rp)" testID="payroll-deduction-input" keyboardType="numeric" value={ded} onChangeText={setDed} />
        <Text style={[s.sub, { marginBottom: sp.md }]}>Jam kerja, lembur yang sudah di-ACC, dan potongan telat dihitung otomatis dari absensi.</Text>
        <Btn title="Hitung & Simpan" testID="payroll-submit-button" loading={busy} disabled={!uid} onPress={submit} />
      </Sheet>
    </Page>
  );
}
