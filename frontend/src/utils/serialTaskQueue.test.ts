import { describe, expect, it } from "vitest";

import { createSerialTaskQueue } from "./serialTaskQueue";

describe("createSerialTaskQueue", () => {
  it("does not start the next task until the active task finishes", async () => {
    const enqueue = createSerialTaskQueue();
    const events: string[] = [];
    let finishFirst: (() => void) | undefined;
    const firstGate = new Promise<void>((resolve) => {
      finishFirst = resolve;
    });

    const first = enqueue(async () => {
      events.push("first:start");
      await firstGate;
      events.push("first:end");
    });
    const second = enqueue(async () => {
      events.push("second:start");
    });

    await Promise.resolve();
    expect(events).toEqual(["first:start"]);

    finishFirst?.();
    await Promise.all([first, second]);
    expect(events).toEqual(["first:start", "first:end", "second:start"]);
  });

  it("continues with the next task when the active task fails", async () => {
    const enqueue = createSerialTaskQueue();
    const first = enqueue(async () => {
      throw new Error("OCR failed");
    });
    const second = enqueue(async () => "completed");

    await expect(first).rejects.toThrow("OCR failed");
    await expect(second).resolves.toBe("completed");
  });
});
