import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { usePolling } from "../src/composables/usePolling";

afterEach(() => vi.useRealTimers());

describe("polling lifecycle", () => {
  it("retains previous data on API failure and recovers on the next refresh", async () => {
    vi.useFakeTimers();
    let fail = false;
    const loader = vi.fn(async () => {
      if (fail) throw new Error("API unavailable");
      return { status: "UP" };
    });
    const Harness = defineComponent({
      setup: () => usePolling(loader),
      template: "<span />",
    });
    const wrapper = mount(Harness);
    await flushPromises();
    expect(wrapper.vm.data?.status).toBe("UP");
    fail = true;
    await vi.advanceTimersByTimeAsync(5000);
    expect(wrapper.vm.data?.status).toBe("UP");
    expect(wrapper.vm.error).toBe("API unavailable");
    fail = false;
    await vi.advanceTimersByTimeAsync(5000);
    expect(wrapper.vm.error).toBe(null);
    wrapper.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("aborts an unfinished request and prevents further requests after unmount", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | undefined;
    const loader = vi.fn((value: AbortSignal) => {
      signal = value;
      return new Promise<string>(() => {});
    });
    const wrapper = mount(
      defineComponent({
        setup: () => usePolling(loader),
        template: "<span />",
      }),
    );
    wrapper.unmount();
    expect(signal?.aborted).toBe(true);
    await vi.advanceTimersByTimeAsync(20000);
    expect(loader).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });
});
