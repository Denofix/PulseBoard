import { onMounted, onUnmounted, ref, shallowRef } from "vue";

export function usePolling<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  interval = 5000,
) {
  const data = shallowRef<T | null>(null);
  const loading = ref(true);
  const error = ref<string | null>(null);
  const updatedAt = ref<Date | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;
  let controller: AbortController | undefined;
  let disposed = false;

  async function refresh() {
    if (disposed) return;
    clearTimeout(timer);
    controller?.abort();
    const current = new AbortController();
    controller = current;
    try {
      const result = await loader(current.signal);
      if (!disposed && !current.signal.aborted) {
        data.value = result;
        error.value = null;
        updatedAt.value = new Date();
      }
    } catch (cause) {
      if (!current.signal.aborted && !disposed)
        error.value =
          cause instanceof Error ? cause.message : "API request failed";
    } finally {
      if (!current.signal.aborted && !disposed) {
        loading.value = false;
        timer = setTimeout(refresh, interval);
      }
    }
  }

  onMounted(refresh);
  onUnmounted(() => {
    disposed = true;
    clearTimeout(timer);
    controller?.abort();
  });
  return { data, loading, error, updatedAt, refresh };
}
