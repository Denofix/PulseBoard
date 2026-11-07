<script setup lang="ts">
import { watch } from "vue";
import { useRoute } from "vue-router";
import {
  Activity,
  LayoutDashboard,
  Radio,
  CircleAlert,
  ChevronRight,
  Github,
  ExternalLink,
  LockKeyhole,
} from "lucide-vue-next";
import { api } from "./api";
import { usePolling } from "./composables/usePolling";
import { config } from "./state";

const route = useRoute();
const settings = usePolling((signal) => api.config(signal), 30000);
watch(settings.data, (value) => {
  if (value) config.value = value;
});
</script>

<template>
  <div class="app-shell">
    <a class="skip-link" href="#main">Skip to content</a>
    <aside class="sidebar">
      <RouterLink to="/" class="brand"
        ><span class="brand-icon"
          ><Activity :size="23" :stroke-width="2.4" /></span
        >PulseBoard<span class="version">BETA</span></RouterLink
      >
      <div class="workspace">
        <span class="workspace-avatar">P</span>
        <div>
          Personal workspace<small>{{
            config?.read_only
              ? "Public demo · Read only"
              : "Self-hosted monitoring"
          }}</small>
        </div>
        <span class="workspace-dot"></span>
      </div>
      <div class="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <RouterLink to="/" :class="{ selected: route.path === '/' }"
          ><LayoutDashboard :size="18" />Overview</RouterLink
        >
        <RouterLink
          to="/services"
          :class="{ selected: route.path.startsWith('/services') }"
          ><Radio :size="18" />Services</RouterLink
        >
        <RouterLink
          to="/incidents"
          :class="{ selected: route.path === '/incidents' }"
          ><CircleAlert :size="18" />Incidents</RouterLink
        >
      </nav>
      <div class="sidebar-bottom">
        <div class="monitor-note">
          <span class="live-dot"></span>
          <div>
            Monitoring runs on your server<small
              >Your browser can take a break.</small
            >
          </div>
        </div>
        <a
          class="source-link"
          href="https://github.com/Denofix"
          target="_blank"
          rel="noopener noreferrer"
          ><Github :size="16" /> Built in the open <ExternalLink :size="13"
        /></a>
        <div class="sidebar-footer">PulseBoard <span>v0.1.0</span></div>
      </div>
    </aside>
    <div class="main-shell">
      <header class="topbar">
        <div class="breadcrumb">
          Workspace <ChevronRight :size="13" /><span>{{
            route.path === "/incidents"
              ? "Incidents"
              : route.path.startsWith("/services")
                ? "Services"
                : "Overview"
          }}</span>
        </div>
        <div class="topbar-right">
          <span v-if="config?.read_only" class="demo-pill"
            ><LockKeyhole :size="12" />Read-only demo</span
          ><span class="environment"
            ><span></span
            >{{
              config?.read_only ? "Public workspace" : "Local workspace"
            }}</span
          ><span class="user-avatar">P</span>
        </div>
      </header>
      <div
        v-if="settings.error.value && !config"
        class="config-error"
        role="alert"
      >
        Cannot load API configuration. Service management is unavailable until
        the connection recovers.
      </div>
      <main id="main" class="main-content">
        <RouterView :key="route.path" />
      </main>
      <footer class="main-footer">
        <span>Small projects. Clear signals.</span
        ><span>HTTP monitoring · All times in UTC</span>
      </footer>
    </div>
  </div>
</template>
