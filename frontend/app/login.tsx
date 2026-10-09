import { useState } from "react";
import { Text, View } from "react-native";
import { Image } from "expo-image";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth";
import { Btn, Field, sp, useWide } from "@/src/ui";
import { makeStyles } from "@/src/theme";

const HERO =
  "https://images.unsplash.com/photo-1613274554329-70f997f5789f?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85&w=1200";

export default function Login() {
  const s = useS();
  const insets = useSafeAreaInsets();
  const wide = useWide();
  const { login, loginWithGoogle, googleError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setErr("");
    setBusy(true);
    try {
      await login(email.trim(), password);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={[s.root, wide && { flexDirection: "row" }]}>
      <Image source={{ uri: HERO }} style={wide ? { flex: 1 } : { height: 260 + insets.top }} contentFit="cover" />
      <KeyboardAwareScrollView bottomOffset={24} keyboardShouldPersistTaps="handled" style={{ flex: 1 }} contentContainerStyle={[s.form, { paddingBottom: insets.bottom + sp.xl }]}>
        <Text style={s.brand}>ROLLOW</Text>
        <Text style={s.sub}>Sistem Manajemen Cafe</Text>
        <Field label="Email" testID="login-email-input" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="nama@rollow.id" returnKeyType="next" />
        <Field label="Password" testID="login-password-input" value={password} onChangeText={setPassword} secureTextEntry placeholder="••••••••" returnKeyType="go" onSubmitEditing={submit} />
        {!!err && (
          <Text style={s.err} testID="login-error-text">
            {err}
          </Text>
        )}
        <Btn title="Masuk" testID="login-submit-button" loading={busy} onPress={submit} disabled={!email || !password} />
        <Text style={s.or}>atau</Text>
        <Btn title="Masuk dengan Google" variant="ghost" icon="logo-google" testID="login-google-button" onPress={loginWithGoogle} />
        {!!googleError && (
          <Text style={[s.err, { marginTop: sp.md }]} testID="login-google-error-text">
            {googleError}
          </Text>
        )}
        <Text style={s.hint}>Akun dibuat oleh Owner. Login Google hanya untuk email yang sudah didaftarkan Owner di menu Karyawan.</Text>
        <View style={s.demo} testID="demo-accounts-box">
          <Text style={s.demoTitle}>Akun demo (password: Rollow@2026)</Text>
          {["owner", "manager", "spv", "finance", "marketing", "crew"].map((r) => (
            <Text key={r} style={s.demoItem} onPress={() => { setEmail(`${r}@rollow.id`); setPassword("Rollow@2026"); }} testID={`demo-account-${r}`}>
              {r}@rollow.id  ›
            </Text>
          ))}
        </View>
      </KeyboardAwareScrollView>
    </View>
  );
}

const useS = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  form: { padding: sp.xl, width: "100%", maxWidth: 480, alignSelf: "center" },
  brand: { fontSize: 36, fontWeight: "900", color: c.brandPrimary, letterSpacing: 2 },
  sub: { fontSize: 15, color: c.muted, marginBottom: sp.xl },
  err: { color: c.error, marginBottom: sp.md, fontWeight: "600" },
  hint: { color: c.muted, fontSize: 12, marginTop: sp.lg, textAlign: "center" },
  or: { color: c.muted, textAlign: "center", marginVertical: sp.md },
  demo: { marginTop: sp.lg, padding: sp.md, borderRadius: 12, backgroundColor: c.brandTertiary, gap: sp.xs },
  demoTitle: { fontWeight: "700", color: c.onBrandTertiary, marginBottom: sp.xs },
  demoItem: { color: c.onSurface, fontSize: 14, paddingVertical: 6 },
}));
