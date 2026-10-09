import { useState } from "react";
import { FlatList, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, num, useApi } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Badge, Btn, Card, Chips, Field, Header, Page, Sheet, sp, StateView, useStyles, useToast } from "@/src/ui";

const LABEL: Record<string, string> = { clock_in: "Clock In", clock_out: "Clock Out", izin: "Izin", sakit: "Sakit", libur: "Libur", lembur: "Lembur" };

export default function Attendance() {
  const s = useStyles();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { can } = useAuth();
  const [scope, setScope] = useState("me");
  const { data, loading, error, reload } = useApi<any[]>(`/attendance?all=${scope === "all"}`);
  const pending = useApi<any[]>(can("overtime_approve") ? "/attendance?pending=true" : null);
  const decide = async (id: string, approve: boolean) => {
    try {
      await api(`/attendance/${id}/decide`, { body: { approve } });
      toast(approve ? "Lembur di-ACC, masuk ke gaji" : "Lembur ditolak");
      pending.reload();
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    }
  };
  const [form, setForm] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [hours, setHours] = useState("");
  const [busy, setBusy] = useState(false);

  const send = async (type: string) => {
    setBusy(true);
    try {
      await api("/attendance", { body: { type, note, hours: num(hours) } });
      toast(`${LABEL[type]} tercatat`);
      setForm(null);
      setNote("");
      setHours("");
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <Header back title="Absensi" subtitle="Clock in/out, izin, sakit, libur, lembur" />
      {can("attendance_all") && <Chips testPrefix="att-scope" value={scope} onChange={setScope} options={[{ label: "Saya", value: "me" }, { label: "Semua Karyawan", value: "all" }]} />}
      <FlatList
        data={data || []}
        keyExtractor={(a) => a.id}
        contentContainerStyle={[s.list, { paddingBottom: insets.bottom + sp.xl }]}
        ListHeaderComponent={
          <View style={{ gap: sp.md }}>
            {(pending.data || []).length > 0 && (
              <Card testID="overtime-pending-card">
                <Text style={[s.title, { marginBottom: sp.sm }]}>Lembur menunggu ACC ({pending.data!.length})</Text>
                {pending.data!.map((a) => (
                  <View key={a.id} style={[s.row, { justifyContent: "space-between", paddingVertical: 4 }]}>
                    <Text style={[s.sub, { flex: 1 }]}>{a.user_name} · {a.date} · {a.hours} jam {a.note ? `· ${a.note}` : ""}</Text>
                    <Btn small title="ACC" variant="success" testID={`overtime-approve-${a.id}`} onPress={() => decide(a.id, true)} />
                    <Btn small title="Tolak" variant="ghost" testID={`overtime-reject-${a.id}`} onPress={() => decide(a.id, false)} />
                  </View>
                ))}
              </Card>
            )}
            <View style={s.row}>
              <Btn title="Clock In" icon="log-in-outline" style={{ flex: 1 }} testID="att-clock-in-button" loading={busy} onPress={() => send("clock_in")} />
              <Btn title="Clock Out" icon="log-out-outline" variant="secondary" style={{ flex: 1 }} testID="att-clock-out-button" loading={busy} onPress={() => send("clock_out")} />
            </View>
            <View style={s.row}>
              {["izin", "sakit", "libur", "lembur"].map((t) => (
                <Btn key={t} small title={LABEL[t]} variant="ghost" style={{ flex: 1 }} testID={`att-${t}-button`} onPress={() => setForm(t)} />
              ))}
            </View>
            {!data && <StateView loading={loading} error={error} onRetry={reload} />}
          </View>
        }
        ListEmptyComponent={data ? <StateView empty="Belum ada absensi bulan ini" /> : null}
        renderItem={({ item: a }) => (
          <Card style={[s.row, { justifyContent: "space-between" }]}>
            <View style={{ flex: 1 }}>
              <Text style={s.title}>{a.user_name}</Text>
              <Text style={s.sub}>{a.date} · {a.time}{a.hours ? ` · ${a.hours} jam` : ""}{a.note ? ` · ${a.note}` : ""}</Text>
            </View>
            <Badge label={`${LABEL[a.type]}${a.type === "lembur" && a.status ? ` · ${a.status === "pending" ? "MENUNGGU" : a.status === "approved" ? "ACC" : "DITOLAK"}` : ""}${a.is_late ? " · TELAT" : ""}`} tone={a.is_late ? "error" : a.type === "clock_in" ? "success" : a.type === "lembur" ? "brand" : a.type === "clock_out" ? "info" : "warning"} />
          </Card>
        )}
      />
      <Sheet visible={!!form} onClose={() => setForm(null)} title={form ? LABEL[form] : ""} testID="att-sheet">
        {form === "lembur" && <Field label="Jumlah jam lembur" testID="att-hours-input" keyboardType="numeric" value={hours} onChangeText={setHours} />}
        <Field label="Keterangan" testID="att-note-input" value={note} onChangeText={setNote} />
        <Btn title="Kirim" testID="att-submit-button" loading={busy} disabled={form === "lembur" && !num(hours)} onPress={() => form && send(form)} />
      </Sheet>
    </Page>
  );
}
