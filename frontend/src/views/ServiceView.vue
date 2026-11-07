<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowLeft,
  ExternalLink,
  Trash2,
  RefreshCw,
  Clock3,
  ArrowRight,
  AlertTriangle,
  X,
} from "lucide-vue-next";
import { api } from "../api";
import type { Check } from "../types";
import { config } from "../state";
import { usePolling } from "../composables/usePolling";
import { clock, dateTime, latency, percent, checkDescription } from "../format";
import StatusBadge from "../components/StatusBadge.vue";
import ApiNotice from "../components/ApiNotice.vue";
import HeartbeatStrip from "../components/HeartbeatStrip.vue";
import LatencyChart from "../components/LatencyChart.vue";
import IncidentTimeline from "../components/IncidentTimeline.vue";

const route = useRoute(),
  router = useRouter(),
  id = Number(route.params.id);
const historyBefore = ref<number>(),
  incidentBefore = ref<number>();
const { data, loading, error, updatedAt, refresh } = usePolling(
  async (signal) => {
    const [service, history, chart, incidents] = await Promise.all([
      api.service(id, signal),
      api.checks(id, signal, historyBefore.value),
      api.checks(id, signal, undefined, 200),
      api.serviceIncidents(id, signal, incidentBefore.value),
    ]);
    return { service, history, chart, incidents, fetchedAt: Date.now() };
  },
);
const evidence = ref<Check | null>(null),
  evidenceError = ref(""),
  deleteError = ref(""),
  deleting = ref(false);
const confirmDelete = ref(false);
const deleteController = new AbortController();
onUnmounted(() => deleteController.abort());
watch(
  () => route.query.check,
  async (value, _old, onCleanup) => {
    evidence.value = null;
    evidenceError.value = "";
    if (!value) return;
    const checkId = Number(value);
    if (!Number.isSafeInteger(checkId) || checkId < 1) {
      evidenceError.value = "Invalid check identifier";
      return;
    }
    const controller = new AbortController();
    onCleanup(() => controller.abort());
    try {
      const check = await api.check(checkId, controller.signal);
      if (check.service_id !== id)
        throw new Error("This check belongs to a different service");
      evidence.value = check;
    } catch (cause) {
      if (!controller.signal.aborted)
        evidenceError.value =
          cause instanceof Error ? cause.message : "Could not load this check";
    }
  },
  { immediate: true },
);
const chartChecks = computed(() => data.value?.chart.items || []);
async function olderHistory() {
  historyBefore.value = data.value?.history.next_cursor || undefined;
  await refresh();
}
async function latestHistory() {
  historyBefore.value = undefined;
  await refresh();
}
async function olderIncidents() {
  incidentBefore.value = data.value?.incidents.next_cursor || undefined;
  await refresh();
}
async function remove() {
  if (!config.value || config.value.read_only) return;
  deleting.value = true;
  deleteError.value = "";
  try {
    await api.remove(id, deleteController.signal);
    await router.push("/services");
  } catch (cause) {
    if (!deleteController.signal.aborted)
      deleteError.value =
        cause instanceof Error ? cause.message : "Could not delete service";
  } finally {
    deleting.value = false;
  }
}
</script>
<template>
  <RouterLink to="/services" class="back-link"
    ><ArrowLeft :size="15" />All services</RouterLink
  >
  <ApiNotice :error="error" :updated-at="updatedAt" @retry="refresh" />
  <div v-if="loading" class="loading-state" role="status">
    <RefreshCw class="spin" :size="20" />Loading service observations…
  </div>
  <template v-if="data">
    <div class="page-heading detail-heading">
      <div>
        <div class="eyebrow">SERVICE DETAILS</div>
        <h1>
          {{ data.service.name }}<StatusBadge :status="data.service.status" />
        </h1>
        <a
          :href="data.service.url"
          class="service-external"
          target="_blank"
          rel="noopener noreferrer"
          >{{ data.service.url }}<ExternalLink :size="13"
        /></a>
      </div>
      <button
        v-if="config && !config.read_only"
        class="button secondary danger-button"
        @click="confirmDelete = !confirmDelete"
      >
        <Trash2 :size="15" />Delete service
      </button>
    </div>
    <div v-if="confirmDelete" class="delete-confirm" role="alert">
      <AlertTriangle :size="20" /><span
        >Delete this service and all its checks and incidents?</span
      ><button class="button danger small" :disabled="deleting" @click="remove">
        {{ deleting ? "Deleting…" : "Delete permanently" }}</button
      ><button
        class="icon-button"
        aria-label="Cancel deletion"
        @click="confirmDelete = false"
      >
        <X :size="18" /></button
      ><span v-if="deleteError">{{ deleteError }}</span>
    </div>
    <div v-if="data.service.stale" class="stale-notice">
      <Clock3 :size="17" />No recent observations. {{ data.service.status }} is
      the last observed state, not a current availability guarantee.
    </div>
    <div class="metric-grid detail-metrics">
      <div class="metric-card">
        <div class="metric-label">Latest response</div>
        <strong>{{
          latency(data.service.latest_check?.response_time_ms)
        }}</strong
        ><small>{{
          data.service.latest_check?.http_status
            ? `HTTP ${data.service.latest_check.http_status}`
            : data.service.latest_check?.error_type || "No response yet"
        }}</small>
      </div>
      <div class="metric-card">
        <div class="metric-label">Successful checks</div>
        <strong>{{ percent(data.service.availability_percent) }}</strong
        ><small
          >{{ data.service.success_count }} of
          {{ data.service.check_count }} observations</small
        >
      </div>
      <div class="metric-card">
        <div class="metric-label">Last checked</div>
        <strong class="time-metric"
          >{{
            data.service.latest_check
              ? clock(data.service.latest_check.checked_at)
              : "—"
          }}<span>UTC</span></strong
        ><small>{{
          data.service.latest_check
            ? dateTime(data.service.latest_check.checked_at).split(",")[0]
            : "Waiting for the first check"
        }}</small>
      </div>
      <div class="metric-card">
        <div class="metric-label">Check interval</div>
        <strong
          >{{ config?.interval_seconds ?? "—" }}<span>seconds</span></strong
        ><small
          >{{ config?.timeout_seconds ?? "—" }}s total timeout · GET</small
        >
      </div>
    </div>
    <section class="panel chart-panel">
      <div class="panel-heading">
        <div class="panel-title">
          <h2>Response time</h2>
          <span class="subtle-label">Time to HTTP response headers · ms</span>
        </div>
        <span class="subtle-label"
          >Latest {{ chartChecks.length }} observations</span
        >
      </div>
      <LatencyChart
        :checks="chartChecks"
        :interval="config?.interval_seconds || 15"
        :gap-threshold="config?.gap_threshold_seconds || 23"
        :now="data.fetchedAt"
      />
      <div class="chart-footer">
        <div class="legend">
          <span><i class="up"></i>HTTP 200–299</span
          ><span><i class="down"></i>Failed check</span
          ><span><i class="gap"></i>No observations</span>
        </div>
        <span>No HTTP response = no latency value</span>
      </div>
    </section>
    <section class="panel heartbeat-detail">
      <div class="panel-heading">
        <h2>Recent heartbeat</h2>
        <span class="subtle-label"
          >Oldest → newest · Hover or focus for details</span
        >
      </div>
      <HeartbeatStrip
        :checks="data.service.recent_checks"
        :stale="data.service.stale"
      />
    </section>
    <section
      v-if="route.query.check"
      id="check-evidence"
      class="panel evidence-panel"
    >
      <div class="panel-heading">
        <h2>Check evidence</h2>
        <RouterLink :to="`/services/${id}`" class="text-link"
          >Dismiss<X :size="13"
        /></RouterLink>
      </div>
      <p v-if="evidenceError" class="form-error" role="alert">
        {{ evidenceError }}
      </p>
      <div v-else-if="evidence" class="evidence-body">
        <StatusBadge :status="evidence.status" /><strong
          >Check #{{ evidence.id }}</strong
        ><span>{{ dateTime(evidence.checked_at) }}</span
        ><span class="mono"
          >HTTP {{ evidence.http_status ?? "no response" }} ·
          {{ latency(evidence.response_time_ms) }}</span
        >
        <p v-if="evidence.error_type">
          {{ evidence.error_type }}: {{ evidence.error_message }}
        </p>
      </div>
      <p v-else class="evidence-body">Loading the exact observation…</p>
    </section>
    <section class="panel">
      <div class="panel-heading">
        <div class="panel-title">
          <h2>Check history</h2>
          <span class="subtle-label">Individual observations · UTC</span>
        </div>
        <button v-if="historyBefore" class="text-link" @click="latestHistory">
          Back to latest
        </button>
      </div>
      <div v-if="data.history.items.length" class="table-scroll">
        <table class="history-table">
          <thead>
            <tr>
              <th>Check / Time</th>
              <th>Result</th>
              <th>HTTP status</th>
              <th>Response time</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="check in data.history.items"
              :id="`check-${check.id}`"
              :key="check.id"
            >
              <td>
                <RouterLink
                  :to="`/services/${id}?check=${check.id}#check-evidence`"
                  class="mono text-link"
                  >#{{ check.id }} · {{ clock(check.checked_at) }}</RouterLink
                ><small class="micro muted">{{
                  dateTime(check.checked_at)
                }}</small>
              </td>
              <td><StatusBadge :status="check.status" /></td>
              <td class="mono">{{ check.http_status ?? "—" }}</td>
              <td class="mono">{{ latency(check.response_time_ms) }}</td>
              <td class="history-reason" :title="checkDescription(check)">
                {{ check.error_type || "Responded successfully"
                }}<small v-if="check.gap_before_seconds > 0" class="gap-label"
                  >Observation gap before this check</small
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="no-results">
        No checks yet. The backend will start automatically.
      </div>
      <div class="pagination">
        <span>Up to 50 checks per page</span
        ><button
          v-if="data.history.next_cursor"
          class="button secondary small"
          @click="olderHistory"
        >
          Older checks<ArrowRight :size="14" />
        </button>
      </div>
    </section>
    <section class="panel">
      <div class="panel-heading">
        <h2>Incidents</h2>
        <span class="subtle-label">First failure → first recovery</span>
      </div>
      <IncidentTimeline
        v-if="data.incidents.items.length"
        :incidents="data.incidents.items"
        :show-service="false"
      />
      <div v-else class="no-results">
        No incidents recorded for this service.
      </div>
      <div class="pagination">
        <span
          >Observed spans exclude recorded gaps and end at the latest
          observation.</span
        ><button
          v-if="incidentBefore"
          class="text-link"
          @click="
            incidentBefore = undefined;
            refresh();
          "
        >
          Latest incidents</button
        ><button
          v-if="data.incidents.next_cursor"
          class="button secondary small"
          @click="olderIncidents"
        >
          Older incidents<ArrowRight :size="14" />
        </button>
      </div>
    </section>
  </template>
</template>
