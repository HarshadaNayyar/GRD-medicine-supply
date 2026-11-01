import type { Data, Me } from "./types";

let accessToken: string | null = null;
export function setToken(value: string | null) {
  accessToken = value;
}
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  key?: string,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const result = await response
    .json()
    .catch(() => ({ detail: "The service returned an unreadable response." }));
  if (!response.ok) {
    if (response.status === 401) {
      accessToken = null;
      window.dispatchEvent(new Event("grd:unauthorised"));
    }
    throw new ApiError(
      response.status,
      typeof result.detail === "string"
        ? result.detail
        : response.status === 422
          ? "Please check quantities, dates and required fields."
          : "The action could not be completed.",
    );
  }
  return result as T;
}
export async function all<T>(path: string): Promise<T[]> {
  let offset = 0,
    items: T[] = [];
  for (let n = 0; n < 100; n++) {
    const page = await api<{ items: T[]; total: number }>(
      `${path}${path.includes("?") ? "&" : "?"}offset=${offset}&limit=200`,
    );
    items = items.concat(page.items);
    if (items.length >= page.total) return items;
    offset += 200;
  }
  throw new Error("Too many records to load. Narrow the scope.");
}
export async function loadData(): Promise<Data> {
  const me = await api<Me>("/me");
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
  ] = await Promise.all([
    all<Data["products"][number]>("/products"),
    all<Data["locations"][number]>("/locations"),
    all<Data["batches"][number]>("/inventory/batches"),
    all<Data["requests"][number]>("/requests"),
    all<Data["plans"][number]>("/plans"),
    all<Data["shipments"][number]>("/shipments"),
    all<Data["cases"][number]>("/cases"),
    all<Data["jobs"][number]>("/jobs"),
    admin ? all<Data["audit"][number]>("/audit") : Promise.resolve([]),
    admin
      ? api<{ items: Data["datasets"] }>("/datasets").then((x) => x.items)
      : Promise.resolve([]),
    api<Data["reconciliation"]>("/inventory/reconciliation"),
  ]);
  const routes = await api<{ items: Data["routes"] }>("/routes");
  return {
    me,
    products,
    locations,
    routes: routes.items,
    batches,
    requests,
    plans,
    shipments,
    cases,
    jobs,
    audit,
    datasets,
    reconciliation,
  };
}
// Keys remain stable across retry of an identical operation in this browser session.
const pendingKeys = new Map<string, string>();
export async function command<T>(path: string, body: unknown): Promise<T> {
  const identity = path + JSON.stringify(body);
  if (!pendingKeys.has(identity))
    pendingKeys.set(identity, crypto.randomUUID());
  const value = await api<T>(path, "POST", body, pendingKeys.get(identity));
  pendingKeys.delete(identity);
  return value;
}
export async function localDemo() {
  const response = await fetch("/__local-demo", { method: "POST" });
  const value = await response.json();
  if (!response.ok)
    throw new Error(value.detail || "Local demo is unavailable.");
  setToken(value.access_token);
}
export async function upload<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch("/api/v1" + path, {
    method: "POST",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    body,
  });
  const value = await response.json();
  if (!response.ok)
    throw new ApiError(
      response.status,
      typeof value.detail === "string"
        ? value.detail
        : "The file could not be validated.",
    );
  return value as T;
}
