export function createSerialTaskQueue() {
  let queue: Promise<void> = Promise.resolve();

  return function enqueue<T>(task: () => Promise<T>, signal?: AbortSignal) {
    const result = queue.then(() => {
      throwIfAborted(signal);
      return task();
    });
    queue = result.then(
      () => undefined,
      () => undefined,
    );
    return result;
  };
}

export function raceWithAbort<T>(
  operation: Promise<T>,
  signal?: AbortSignal,
): Promise<T> {
  if (!signal) {
    return operation;
  }

  // Promise.race keeps a rejection handler on the abandoned operation, and
  // this explicit observer also documents that late worker failures are safe.
  void operation.catch(() => undefined);
  if (signal.aborted) {
    return Promise.reject(getAbortReason(signal));
  }

  let handleAbort: (() => void) | undefined;
  const aborted = new Promise<never>((_, reject) => {
    handleAbort = () => reject(getAbortReason(signal));
    signal.addEventListener("abort", handleAbort, { once: true });
  });

  return Promise.race([operation, aborted]).finally(() => {
    if (handleAbort) {
      signal.removeEventListener("abort", handleAbort);
    }
  });
}

function throwIfAborted(signal?: AbortSignal) {
  if (signal?.aborted) {
    throw getAbortReason(signal);
  }
}

function getAbortReason(signal: AbortSignal) {
  return signal.reason ?? new DOMException("処理を中止しました。", "AbortError");
}
