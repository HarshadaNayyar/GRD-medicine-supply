import { afterEach, describe, expect, it, vi } from "vitest";
import { api, command, setToken } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  setToken(null);
});

describe("authenticated stock commands", () => {
  it("reuses the command key after a lost response, then creates a new key for a new action", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error("Connection lost"))
      .mockImplementation(
        async () =>
          new Response(JSON.stringify({ ok: true }), {
            headers: { "Content-Type": "application/json" },
          }),
      );
    vi.stubGlobal("fetch", fetcher);
    setToken("session-token");
    await expect(
      command("/test-stock-command", { quantity: 20 }),
    ).rejects.toThrow("Connection lost");
    await command("/test-stock-command", { quantity: 20 });
    await command("/test-stock-command", { quantity: 20 });
    const options = fetcher.mock.calls.map((call) => call[1]);
    expect(options[0].headers["Idempotency-Key"]).toBe(
      options[1].headers["Idempotency-Key"],
    );
    expect(options[2].headers["Idempotency-Key"]).not.toBe(
      options[1].headers["Idempotency-Key"],
    );
    expect(options[0].headers.Authorization).toBe("Bearer session-token");
  });
  it("reports a server conflict without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Stale plan version" }), {
          status: 409,
        }),
      ),
    );
    await expect(
      api("/plans/p/approve", "POST", { version: 1 }),
    ).rejects.toMatchObject({ status: 409, message: "Stale plan version" });
  });
});
