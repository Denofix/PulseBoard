<script setup lang="ts">
import type { Status } from "../types";
defineProps<{ status: Status }>();
</script>
<template>
  <span class="status-badge" :class="status.toLowerCase()"
    ><span></span
    >{{ status === "UP" ? "Up" : status === "DOWN" ? "Down" : "Unknown" }}</span
  >
</template>
