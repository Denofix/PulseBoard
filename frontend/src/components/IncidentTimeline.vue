<script setup lang="ts">
import { CircleAlert, Check, ArrowUpRight } from "lucide-vue-next";
import type { Incident } from "../types";
import { dateTime, duration } from "../format";
withDefaults(defineProps<{ incidents: Incident[]; showService?: boolean }>(), {
  showService: true,
});
</script>
<template>
  <div class="incident-list">
    <article
      v-for="incident in incidents"
      :key="incident.id"
      class="incident-item"
    >
      <span
        class="incident-symbol"
        :class="incident.closed_at ? 'resolved' : 'open'"
        ><Check v-if="incident.closed_at" :size="17" /><CircleAlert
          v-else
          :size="17"
      /></span>
      <div class="incident-content">
        <div class="incident-title">
          <RouterLink :to="`/services/${incident.service_id}`">{{
            showService ? incident.service_name : `Incident #${incident.id}`
          }}</RouterLink
          ><span
            class="incident-state"
            :class="incident.closed_at ? 'resolved' : 'open'"
            >{{ incident.closed_at ? "Resolved" : "Open" }}</span
          >
        </div>
        <p>{{ incident.reason }}</p>
        <div class="incident-times">
          <span>Detected {{ dateTime(incident.opened_at) }}</span
          ><span>{{
            incident.closed_at
              ? `Recovered ${dateTime(incident.closed_at)}`
              : `Last observed ${dateTime(incident.last_observed_at)}`
          }}</span>
        </div>
        <div class="incident-detail">
          <span
            >{{ duration(incident.observed_duration_seconds) }} observed
            span</span
          ><span v-if="incident.observation_gap_seconds > 0" class="gap-label"
            >{{ duration(incident.observation_gap_seconds) }} without
            observations, excluded</span
          ><RouterLink
            :to="`/services/${incident.service_id}?check=${incident.opening_check_id}#check-evidence`"
            >Opening check #{{ incident.opening_check_id
            }}<ArrowUpRight :size="13"
          /></RouterLink>
        </div>
      </div>
    </article>
  </div>
</template>
