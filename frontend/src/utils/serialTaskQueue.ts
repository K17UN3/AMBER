export function createSerialTaskQueue() {
  let queue: Promise<void> = Promise.resolve();

  return function enqueue<T>(task: () => Promise<T>) {
    const result = queue.then(task);
    queue = result.then(
      () => undefined,
      () => undefined,
    );
    return result;
  };
}
