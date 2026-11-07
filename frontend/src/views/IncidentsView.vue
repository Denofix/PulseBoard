<script setup lang="ts">
import { computed, ref } from "vue";
import { RefreshCw, ArrowRight } from "lucide-vue-next";
import { api } from "../api";
import { usePolling } from "../composables/usePolling";
import ApiNotice from "../components/ApiNotice.vue";
import EmptyState from "../components/EmptyState.vue";
import IncidentTimeline from "../components/IncidentTimeline.vue";

const before = ref<number>(),
  filter = ref("ALL");
const { data, loading, error, updatedAt, refresh } = usePolling((signal) =>
  api.incidents(signal, before.value),
);
const filtered = computed(() =>
  (data.value?.items || []).filter(
    (i) =>
      filter.value === "ALL" ||
      (filter.value === "OPEN" ? !i.closed_at : !!i.closed_at),
  ),
);
async function older() {
  before.value = data.value?.next_cursor || undefined;
  await refresh();
}
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">THE STORY BEHIND THE SIGNAL</div>
      <h1>Incidents</h1>
      <p>What went down, when we noticed, and when it came back.</p>
    </div>
    <button class="button secondary" @click="refresh">
      <RefreshCw :size="15" />Refresh
    </button>
  </div>
  <ApiNotice :error="error" :updated-at="updatedAt" @retry="refresh" />
  <div v-if="loading" class="loading-state" role="status">
    <RefreshCw class="spin" :size="20" />Loading incidents…
  </div>
  <section v-if="data" class="panel">
    <div class="panel-heading">
      <h2>Incident history</h2>
      <select v-model="filter" aria-label="Filter incidents on this page">
        <option value="ALL">All on this page</option>
        <option value="OPEN">Open on this page</option>
        <option value="RESOLVED">Resolved on this page</option>
      </select>
    </div>
    <IncidentTimeline v-if="filtered.length" :incidents="filtered" /><EmptyState
      v-else
      title="Nothing to report"
      description="No incidents match this view. Failed checks will appear here automatically."
    />
    <div class="pagination">
      <span>Up to 50 incidents per page · Newest first</span
      ><button
        v-if="before"
        class="text-link"
        @click="
          before = undefined;
          refresh();
        "
      >
        Back to latest</button
      ><button
        v-if="data.next_cursor"
        class="button secondary small"
        @click="older"
      >
        Older incidents<ArrowRight :size="14" />
      </button>
    </div>
  </section>
  <p class="footnote">
    Detection and recovery times are observations, not the exact beginning or
    end of an outage. Recorded monitoring gaps are excluded from observed spans.
  </p>
</template>
