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

function throwIfAborted(signal?: AbortSignal) {
  if (signal?.aborted) {
    throw signal.reason ?? new DOMException("処理を中止しました。", "AbortError");
  }
}
