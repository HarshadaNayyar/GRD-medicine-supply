import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { Platform } from "react-native";
import * as Crypto from "expo-crypto";
import type { Data, Me, Network } from "../../shared/types";
import { ApiError, serverOrigin, SessionChanged, Transport } from "./transport";
import { Outbox, type Command } from "./queue";
import { vault } from "./storage";

type Session = {
  data: Data | null;
  network: Network | null;
  product: string;
  setProduct: (p: string) => void;
  origin: string;
  login: (origin: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
  refreshing: boolean;
  busy: boolean;
  error: string;
  setError: (s: string) => void;
  asOf: string;
  synced: string | null;
  refresh: () => Promise<void>;
  pending: Command[];
  post: (path: string, body: unknown, label: string) => Promise<boolean>;
  retry: (command: Command) => Promise<void>;
  discard: (id: string) => Promise<void>;
  api: Transport | null;
};
const Context = createContext<Session | null>(null);
export const useSession = () => useContext(Context)!;
const today = () => new Date().toISOString().slice(0, 10);
async function snapshot(api: Transport): Promise<Data> {
  const me = await api.request<Me>("/me");
  const admin = ["admin", "manager", "steward"].includes(me.role);
  const [
    products,
    locations,
    batches,
    requests,
    plans,
    shipments,
    cases,
    jobs,
    audit,
    datasets,
    reconciliation,
    routes,
  ] = await Promise.all([
    api.all<Data["products"][number]>("/products"),
    api.all<Data["locations"][number]>("/locations"),
    api.all<Data["batches"][number]>("/inventory/batches"),
    api.all<Data["requests"][number]>("/requests"),
    api.all<Data["plans"][number]>("/plans"),
    api.all<Data["shipments"][number]>("/shipments"),
    api.all<Data["cases"][number]>("/cases"),
    api.all<Data["jobs"][number]>("/jobs"),
    admin ? api.all<Data["audit"][number]>("/audit") : [],
    admin ? api.all<Data["datasets"][number]>("/datasets") : [],
    api.request<Data["reconciliation"]>("/inventory/reconciliation"),
    api.request<{ items: Data["routes"] }>("/routes"),
  ]);
  return {
    me,
    products,
    locations,
    batches,
    requests,
    plans,
    shipments,
    cases,
    jobs,
    audit,
    datasets,
    reconciliation,
    routes: routes.items,
  };
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<Data | null>(null);
  const [network, setNetwork] = useState<Network | null>(null);
  const [product, setProduct] = useState("");
  const [origin, setOrigin] = useState(
    serverOrigin(
      process.env.EXPO_PUBLIC_GRD_API_URL ||
        (Platform.OS === "android"
          ? "http://10.0.2.2:8011"
          : "http://127.0.0.1:8011"),
    ),
  );
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [synced, setSynced] = useState<string | null>(null);
  const [pending, setPending] = useState<Command[]>([]);
  const client = useRef<Transport | null>(null);
  const [apiState, setApiState] = useState<Transport | null>(null);
  const outbox = useRef<Outbox | null>(null);
  const locked = useRef(false);
  const refreshSequence = useRef(0);
  const asOf = data?.me.scenario_on || today();

  const expire = useCallback(() => {
    client.current = null;
    outbox.current = null;
    setApiState(null);
    setData(null);
    setNetwork(null);
    setProduct("");
    setPending([]);
    setSynced(null);
    void vault.remove("grd.token");
    setError(
      "Session expired. Reconnect and sign in again. Pending actions remain securely saved for this account.",
    );
  }, []);

  const refresh = useCallback(async () => {
    const api = client.current;
    if (!api) return;
    const sequence = ++refreshSequence.current;
    setRefreshing(true);
    try {
      const next = await snapshot(api);
      if (api !== client.current || sequence !== refreshSequence.current)
        return;
      setData(next);
      setSynced(new Date().toISOString());
      setProduct((p) =>
        next.products.some((x) => x.id === p) ? p : next.products[0]?.id || "",
      );
      if (outbox.current) setPending(await outbox.current.list());
      setError("");
    } catch (e) {
      if (api === client.current && !(e instanceof SessionChanged))
        setError(
          e instanceof Error
            ? e.message
            : "Unable to refresh. Showing the last fetched records.",
        );
    } finally {
      if (sequence === refreshSequence.current) setRefreshing(false);
    }
  }, []);

  const open = useCallback(
    async (base: string, token: string) => {
      const api = new Transport(base, expire);
      client.current?.authenticate(null);
      client.current = api;
      api.authenticate(token);
      const next = await snapshot(api);
      if (client.current !== api) throw new SessionChanged();
      const scope = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        `${base}|${next.me.organisation_id}|${next.me.id}`,
      );
      outbox.current = new Outbox(vault, scope);
      setPending(await outbox.current.list());
      await vault.set("grd.origin", base);
      await vault.set("grd.token", token);
      setApiState(api);
      setOrigin(base);
      setData(next);
      setProduct(next.products[0]?.id || "");
      setSynced(new Date().toISOString());
      setError("");
    },
    [expire],
  );

  useEffect(() => {
    void (async () => {
      try {
        const base = await vault.get("grd.origin");
        const token = await vault.get("grd.token");
        if (base) setOrigin(serverOrigin(base));
        if (base && token) await open(serverOrigin(base), token);
      } catch {
        setError(
          "Connect to the server and sign in. Secure pending actions are retained on this device.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [open]);

  useEffect(() => {
    const api = client.current;
    if (!data || !product || !api) return;
    let current = true;
    setNetwork(null);
    void api
      .request<Network>(
        `/network?product_id=${encodeURIComponent(product)}&as_of=${asOf}&horizon=21`,
      )
      .then((n) => {
        if (current && client.current === api) setNetwork(n);
      })
      .catch((e) => {
        if (current && client.current === api && !(e instanceof SessionChanged))
          setError(e.message);
      });
    return () => {
      current = false;
    };
  }, [data, product, asOf]);

  async function login(base: string, email: string, password: string) {
    base = serverOrigin(base);
    const api = new Transport(base);
    const result = await api.request<{ access_token: string }>(
      "/auth/login",
      "POST",
      { email: email.trim(), password },
    );
    await open(base, result.access_token);
  }
  async function logout() {
    if (pending.length)
      throw new Error("Sync or review pending actions before signing out.");
    const api = client.current;
    try {
      await api?.request("/auth/logout", "POST");
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 401))
        throw new Error("Reconnect to revoke the session before signing out.");
    }
    api?.authenticate(null);
    expire();
    setError("");
  }
  async function post(path: string, body: unknown, label: string) {
    const api = client.current,
      box = outbox.current;
    if (!api || !box || locked.current) return false;
    locked.current = true;
    setBusy(true);
    const command: Command = {
      id: Crypto.randomUUID(),
      path,
      body,
      label,
      created: new Date().toISOString(),
      state: "pending",
    };
    let saved = false;
    try {
      await box.add(command);
      saved = true;
      if (api !== client.current) throw new SessionChanged();
      await box.send(api, command);
      if (api === client.current) {
        await refresh();
      }
      return true;
    } catch (e) {
      if (api === client.current)
        setError(
          saved
            ? `Action retained in Pending actions. ${e instanceof Error ? e.message : "Reconnect to confirm the result."}`
            : e instanceof Error
              ? e.message
              : "Unable to save this action.",
        );
      // Once durably recorded the form closes, preventing a new duplicate key on another tap.
      return saved;
    } finally {
      if (api === client.current) setPending(await box.list());
      locked.current = false;
      setBusy(false);
    }
  }
  async function retry(command: Command) {
    const api = client.current,
      box = outbox.current;
    if (!api || !box || locked.current) return;
    locked.current = true;
    setBusy(true);
    try {
      await box.send(api, command);
      await refresh();
    } finally {
      if (api === client.current) setPending(await box.list());
      locked.current = false;
      setBusy(false);
    }
  }
  async function discard(id: string) {
    await outbox.current?.remove(id);
    setPending((await outbox.current?.list()) || []);
  }
  return (
    <Context.Provider
      value={{
        data,
        network,
        product,
        setProduct,
        origin,
        login,
        logout,
        loading,
        refreshing,
        busy,
        error,
        setError,
        asOf,
        synced,
        refresh,
        pending,
        post,
        retry,
        discard,
        api: apiState,
      }}
    >
      {children}
    </Context.Provider>
  );
}
