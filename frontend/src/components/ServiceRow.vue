<script setup lang="ts">
import { Globe, ChevronRight, Clock3 } from "lucide-vue-next";
import type { Service } from "../types";
import { clock, dateTime, latency, percent } from "../format";
import StatusBadge from "./StatusBadge.vue";
import HeartbeatStrip from "./HeartbeatStrip.vue";
defineProps<{ service: Service }>();
</script>
<template>
  <tr>
    <td>
      <div class="service-identity">
        <span class="service-icon"><Globe :size="18" /></span>
        <div>
          <RouterLink class="service-name" :to="`/services/${service.id}`">{{
            service.name
          }}</RouterLink
          ><span class="service-url" :title="service.url">{{
            service.url
          }}</span>
        </div>
      </div>
    </td>
    <td>
      <StatusBadge :status="service.status" />
      <div v-if="service.stale" class="stale-label">
        <Clock3 :size="11" />Stale
      </div>
    </td>
    <td class="heartbeat-cell">
      <HeartbeatStrip
        :checks="service.recent_checks"
        :stale="service.stale"
        compact
      /><span class="muted micro"
        >{{ service.check_count }} checks ·
        {{ percent(service.availability_percent) }} successful</span
      >
    </td>
    <td class="mono response-cell">
      {{ latency(service.latest_check?.response_time_ms)
      }}<span class="muted micro">{{
        service.latest_check?.http_status != null
          ? `HTTP ${service.latest_check.http_status}`
          : service.latest_check?.error_type || "Waiting for a check"
      }}</span>
    </td>
    <td class="mono last-check">
      <span
        v-if="service.latest_check"
        :title="dateTime(service.latest_check.checked_at)"
        >{{ clock(service.latest_check.checked_at) }}<small>UTC</small></span
      ><span v-else class="muted">—</span>
    </td>
    <td class="row-arrow">
      <RouterLink
        :to="`/services/${service.id}`"
        :aria-label="`View ${service.name}`"
        ><ChevronRight :size="17"
      /></RouterLink>
    </td>
  </tr>
</template>
