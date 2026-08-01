import { describe, expect, it } from "vitest";

import { createSerialTaskQueue, raceWithAbort } from "./serialTaskQueue";

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

  it("does not start a waiting task after its signal is aborted", async () => {
    const enqueue = createSerialTaskQueue();
    const controller = new AbortController();
    let finishFirst: (() => void) | undefined;
    let secondStarted = false;
    const firstGate = new Promise<void>((resolve) => {
      finishFirst = resolve;
    });

    const first = enqueue(() => firstGate);
    const second = enqueue(async () => {
      secondStarted = true;
    }, controller.signal);
    const secondResult = second.catch((error: unknown) => error);

    controller.abort();
    finishFirst?.();
    await first;

    const abortError = await secondResult;
    expect(abortError).toBeInstanceOf(DOMException);
    expect((abortError as DOMException).name).toBe("AbortError");
    expect(secondStarted).toBe(false);
  });

  it("runs the next task after an active operation is aborted", async () => {
    const enqueue = createSerialTaskQueue();
    const controller = new AbortController();
    let rejectRecognition: ((error: Error) => void) | undefined;
    let recognitionStarted = false;
    const pendingRecognition = new Promise<void>((_, reject) => {
      rejectRecognition = reject;
    });

    const first = enqueue(async () => {
      recognitionStarted = true;
      await raceWithAbort(pendingRecognition, controller.signal);
    }, controller.signal);
    const firstResult = first.catch((error: unknown) => error);
    const second = enqueue(async () => "next OCR completed");

    await Promise.resolve();
    expect(recognitionStarted).toBe(true);
    controller.abort();

    const abortError = await firstResult;
    expect(abortError).toBeInstanceOf(DOMException);
    expect((abortError as DOMException).name).toBe("AbortError");
    await expect(second).resolves.toBe("next OCR completed");

    rejectRecognition?.(new Error("terminated worker rejected late"));
    await Promise.resolve();
  });
});
