<script setup lang="ts">
import { computed } from "vue";
import type { Check } from "../types";
import { checkDescription, duration } from "../format";

const props = withDefaults(
  defineProps<{ checks: Check[]; stale?: boolean; compact?: boolean }>(),
  { stale: false, compact: false },
);
const recent = computed(() =>
  [...props.checks].sort((a, b) => a.id - b.id).slice(-30),
);
</script>
<template>
  <div class="heartbeat-area">
    <div v-if="!recent.length" class="no-observations">No observations yet</div>
    <div
      v-else
      class="heartbeat-strip"
      :class="{ compact }"
      aria-label="Recent checks, oldest to newest"
    >
      <template v-for="check in recent" :key="check.id">
        <span
          v-if="check.gap_before_seconds > 0"
          class="heartbeat-gap"
          tabindex="0"
          :aria-label="`No observations for ${duration(check.gap_before_seconds)} before check ${check.id}`"
          ><span class="beat-tooltip"
            >No observations for {{ duration(check.gap_before_seconds) }}</span
          ></span
        >
        <RouterLink
          :to="`/services/${check.service_id}?check=${check.id}#check-evidence`"
          class="heartbeat"
          :class="check.status.toLowerCase()"
          :data-check-id="check.id"
          :aria-label="checkDescription(check)"
          ><span class="beat-tooltip">{{
            checkDescription(check)
          }}</span></RouterLink
        >
      </template>
      <span
        v-if="stale"
        class="heartbeat-gap trailing"
        tabindex="0"
        aria-label="No recent observations"
        ><span class="beat-tooltip"
          >No recent observations. The last service state is historical.</span
        ></span
      >
    </div>
  </div>
</template>
