<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import {
  Plus,
  Search,
  RefreshCw,
  Radio,
  CheckCircle2,
  CircleAlert,
  Activity,
  ArrowUpRight,
  ShieldCheck,
  LockKeyhole,
} from "lucide-vue-next";
import { api } from "../api";
import { config } from "../state";
import { usePolling } from "../composables/usePolling";
import { percent } from "../format";
import ApiNotice from "../components/ApiNotice.vue";
import EmptyState from "../components/EmptyState.vue";
import ServiceRow from "../components/ServiceRow.vue";
import ServiceForm from "../components/ServiceForm.vue";
import IncidentTimeline from "../components/IncidentTimeline.vue";

const route = useRoute();
const { data, loading, error, updatedAt, refresh } = usePolling(
  async (signal) => {
    const [dashboard, services, incidents] = await Promise.all([
      api.dashboard(signal),
      api.services(signal),
      api.incidents(signal),
    ]);
    return { dashboard, services, incidents };
  },
);
const search = ref(""),
  status = ref("ALL"),
  showForm = ref(false);
const filtered = computed(() =>
  (data.value?.services || []).filter(
    (service) =>
      (service.name.toLowerCase().includes(search.value.toLowerCase()) ||
        service.url.toLowerCase().includes(search.value.toLowerCase())) &&
      (status.value === "ALL" || service.status === status.value),
  ),
);
const allHealthy = computed(
  () =>
    !!data.value?.dashboard.total_services &&
    data.value.dashboard.up_services === data.value.dashboard.total_services &&
    !data.value.dashboard.stale_services,
);
const latestIncidents = computed(
  () => data.value?.incidents.items.slice(0, 3) || [],
);
async function created() {
  showForm.value = false;
  await refresh();
}
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">YOUR WORKSPACE, AT A GLANCE</div>
      <h1>{{ route.path === "/services" ? "Services" : "Overview" }}</h1>
      <p>A little peace of mind for everything you ship.</p>
    </div>
    <button
      v-if="config && !config.read_only"
      class="button primary"
      @click="showForm = true"
    >
      <Plus :size="17" />Add service</button
    ><span v-else-if="config?.read_only" class="readonly-label"
      ><LockKeyhole :size="15" />Live data · Read only</span
    >
  </div>
  <ApiNotice :error="error" :updated-at="updatedAt" @retry="refresh" />
  <div v-if="loading" class="loading-state" role="status">
    <RefreshCw class="spin" :size="20" />Connecting to your workspace…
  </div>
  <template v-if="data">
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">Total services<Radio :size="16" /></div>
        <strong>{{ data.dashboard.total_services }}<span>services</span></strong
        ><small>Everything you're keeping an eye on</small>
      </div>
      <div class="metric-card">
        <div class="metric-label">
          Services up<CheckCircle2 :size="16" class="text-up" />
        </div>
        <strong
          >{{ data.dashboard.up_services
          }}<span class="text-up">{{
            data.dashboard.total_services
              ? `${Math.round((data.dashboard.up_services / data.dashboard.total_services) * 100)}% of services`
              : "Waiting for services"
          }}</span></strong
        ><small
          >{{ data.dashboard.down_services }} down
          <span class="metric-divider">/</span>
          {{ data.dashboard.unknown_services }} unknown
          <span v-if="data.dashboard.stale_services"
            >/ {{ data.dashboard.stale_services }} stale</span
          ></small
        >
      </div>
      <div class="metric-card">
        <div class="metric-label">
          Open incidents<CircleAlert
            :size="16"
            :class="{ 'text-down': data.dashboard.open_incidents > 0 }"
          />
        </div>
        <strong
          >{{ data.dashboard.open_incidents
          }}<span
            :class="data.dashboard.open_incidents ? 'text-down' : 'muted'"
            >{{
              data.dashboard.open_incidents
                ? "Needs attention"
                : "No active incidents"
            }}</span
          ></strong
        ><small>From the first failed check</small>
      </div>
      <div class="metric-card">
        <div class="metric-label">Successful checks<Activity :size="16" /></div>
        <strong class="percentage">{{
          percent(data.dashboard.availability_percent)
        }}</strong
        ><small
          >{{ data.dashboard.check_count.toLocaleString() }} real observations ·
          All time</small
        >
      </div>
    </div>
    <div
      class="health-summary"
      :class="{
        healthy: allHealthy,
        attention: data.dashboard.down_services > 0,
      }"
    >
      <span class="summary-dot"></span
      ><strong>{{
        !data.dashboard.total_services
          ? "Your next launch deserves a heartbeat."
          : allHealthy
            ? "All services are responding"
            : data.dashboard.down_services
              ? `${data.dashboard.down_services} service${data.dashboard.down_services === 1 ? " needs" : "s need"} attention`
              : "Waiting for fresh observations"
      }}</strong
      ><span>{{
        config
          ? `Checked every ${config.interval_seconds}s`
          : "Loading settings"
      }}</span>
    </div>
    <section class="panel services-panel" aria-labelledby="services-title">
      <div class="panel-heading">
        <div class="panel-title">
          <h2 id="services-title">Monitored services</h2>
          <span class="count-pill">{{ data.services.length }}</span>
        </div>
        <button
          class="icon-button"
          aria-label="Refresh services"
          @click="refresh"
        >
          <RefreshCw :size="15" />
        </button>
      </div>
      <template v-if="data.services.length">
        <div class="table-toolbar">
          <div class="search-field">
            <Search :size="15" /><input
              v-model="search"
              aria-label="Search services"
              placeholder="Search services…"
            />
          </div>
          <select v-model="status" aria-label="Filter by status">
            <option value="ALL">All statuses</option>
            <option value="UP">Up</option>
            <option value="DOWN">Down</option>
            <option value="UNKNOWN">Unknown</option></select
          ><span class="toolbar-note">Latest 30 checks per service</span>
        </div>
        <div class="table-scroll">
          <table class="services-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>Status</th>
                <th>Recent checks</th>
                <th>Response</th>
                <th>Last checked</th>
                <th><span class="sr-only">Details</span></th>
              </tr>
            </thead>
            <tbody>
              <ServiceRow
                v-for="service in filtered"
                :key="service.id"
                :service="service"
              />
            </tbody>
          </table>
        </div>
        <div v-if="!filtered.length" class="no-results">
          No services match these filters.
        </div>
        <div class="table-footer">
          <span
            >{{ filtered.length }} of {{ data.services.length }} services</span
          >
          <div class="legend">
            <span><i class="up"></i>Up</span
            ><span><i class="down"></i>Down</span
            ><span><i class="gap"></i>No observations</span>
          </div>
        </div>
      </template>
      <EmptyState
        v-else
        title="Give your project a heartbeat"
        description="Add your first HTTP endpoint. We'll watch it from your server, even when you close this tab."
        ><button
          v-if="config && !config.read_only"
          class="button primary"
          @click="showForm = true"
        >
          <Plus :size="16" />Add your first service</button
        ><span v-else class="muted"
          >The owner hasn't configured any demo services yet.</span
        ></EmptyState
      >
    </section>
    <section class="panel" aria-labelledby="incidents-title">
      <div class="panel-heading">
        <div class="panel-title">
          <h2 id="incidents-title">Recent incidents</h2>
          <span class="subtle-label">A clear trail of what happened</span>
        </div>
        <RouterLink to="/incidents" class="text-link"
          >View all<ArrowUpRight :size="14"
        /></RouterLink>
      </div>
      <IncidentTimeline
        v-if="latestIncidents.length"
        :incidents="latestIncidents"
      />
      <div v-else class="quiet-state">
        <ShieldCheck :size="21" />
        <div>
          <strong>No incidents recorded</strong>
          <p>When a service goes down, its story starts here.</p>
        </div>
      </div>
    </section>
    <div class="bottom-note">
      <Activity :size="15" /><span
        >Every heartbeat is a real HTTP check. Gaps mean no observations, never
        assumed uptime.</span
      ><span class="poll-note">Dashboard refreshes every 5s</span>
    </div>
  </template>
  <ServiceForm v-if="showForm" @close="showForm = false" @created="created" />
</template>
