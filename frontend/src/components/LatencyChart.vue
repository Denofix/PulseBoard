<script setup lang="ts">
import { computed } from "vue";
import type { Check } from "../types";
import { checkDescription, clock } from "../format";

const props = defineProps<{
  checks: Check[];
  interval: number;
  gapThreshold: number;
  now: number;
}>();
const ordered = computed(() => [...props.checks].sort((a, b) => a.id - b.id));
const start = computed(() =>
  ordered.value.length ? Date.parse(ordered.value[0]!.checked_at) : props.now,
);
const end = computed(() =>
  Math.max(
    start.value + props.interval * 1000,
    props.now,
    ...ordered.value.map((c) => Date.parse(c.checked_at)),
  ),
);
const maxLatency = computed(
  () =>
    Math.max(10, ...ordered.value.map((c) => c.response_time_ms ?? 0)) * 1.2,
);
const x = (time: number) =>
  52 + ((time - start.value) / (end.value - start.value)) * 888;
const y = (latency: number) => 160 - (latency / maxLatency.value) * 134;
const points = computed(() =>
  ordered.value.map((check) => ({
    check,
    x: x(Date.parse(check.checked_at)),
    y: check.response_time_ms == null ? 177 : y(check.response_time_ms),
  })),
);
const segments = computed(() => {
  const groups: string[] = [];
  let segment = "";
  for (let i = 0; i < points.value.length; i++) {
    const point = points.value[i]!;
    const previous = points.value[i - 1];
    const gap =
      previous &&
      (point.check.gap_before_seconds > 0 ||
        Date.parse(point.check.checked_at) -
          Date.parse(previous.check.checked_at) >
          props.gapThreshold * 1000);
    if (point.check.response_time_ms == null || gap) {
      if (segment) groups.push(segment);
      segment = "";
    }
    if (point.check.response_time_ms != null)
      segment += `${point.x},${point.y} `;
  }
  if (segment) groups.push(segment);
  return groups;
});
const gaps = computed(() => {
  const result: { x: number; width: number }[] = [];
  for (let i = 0; i < ordered.value.length; i++) {
    const current = Date.parse(ordered.value[i]!.checked_at);
    const next = ordered.value[i + 1]
      ? Date.parse(ordered.value[i + 1]!.checked_at)
      : props.now;
    const recordedGap = ordered.value[i + 1]?.gap_before_seconds || 0;
    if (recordedGap > 0 || next - current > props.gapThreshold * 1000) {
      const from = x(
        recordedGap > 0
          ? next - recordedGap * 1000
          : current + props.interval * 1000,
      );
      result.push({ x: from, width: Math.max(0, x(next) - from) });
    }
  }
  return result;
});
</script>
<template>
  <div v-if="!checks.length" class="chart-empty">
    The first real check will appear here. No measurements yet.
  </div>
  <div v-else class="latency-chart">
    <svg
      viewBox="0 0 960 220"
      role="img"
      aria-label="Response time in milliseconds, time in UTC. Gaps are not connected."
    >
      <defs>
        <pattern
          id="gap-pattern"
          width="7"
          height="7"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line
            x1="0"
            y1="0"
            x2="0"
            y2="7"
            stroke="currentColor"
            stroke-opacity="0.13"
            stroke-width="2"
          />
        </pattern>
      </defs>
      <g v-for="fraction in [0, 0.5, 1]" :key="fraction">
        <line
          x1="52"
          x2="940"
          :y1="y(maxLatency * fraction)"
          :y2="y(maxLatency * fraction)"
          class="chart-grid"
        />
        <text x="40" :y="y(maxLatency * fraction) + 4" text-anchor="end">
          {{ Math.round(maxLatency * fraction) }}
        </text>
      </g>
      <text x="16" y="13">ms</text>
      <rect
        v-for="(gap, i) in gaps"
        :key="`gap-${i}`"
        :x="gap.x"
        y="24"
        :width="gap.width"
        height="163"
        fill="url(#gap-pattern)"
        data-gap="true"
      >
        <title>No observations</title>
      </rect>
      <polyline
        v-for="(segment, i) in segments"
        :key="i"
        :points="segment"
        fill="none"
        class="chart-line"
      />
      <a
        v-for="point in points"
        :key="point.check.id"
        :href="`?check=${point.check.id}#check-evidence`"
        :aria-label="checkDescription(point.check)"
      >
        <circle
          :cx="point.x"
          :cy="point.y"
          :r="point.check.response_time_ms == null ? 3.5 : 3"
          :class="['chart-point', point.check.status.toLowerCase()]"
          :data-check-id="point.check.id"
        >
          <title>{{ checkDescription(point.check) }}</title>
        </circle>
      </a>
      <text x="52" y="211">{{ clock(new Date(start).toISOString()) }}</text>
      <text x="496" y="211" text-anchor="middle">
        {{ clock(new Date((start + end) / 2).toISOString()) }}
      </text>
      <text x="940" y="211" text-anchor="end">
        {{ clock(new Date(end).toISOString()) }} UTC
      </text>
    </svg>
  </div>
</template>
