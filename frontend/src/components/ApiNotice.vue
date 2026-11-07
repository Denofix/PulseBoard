<script setup lang="ts">
import { WifiOff, RefreshCw } from "lucide-vue-next";
import { dateTime } from "../format";
defineProps<{ error: string | null; updatedAt?: Date | null }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div v-if="error" class="api-notice" role="alert">
    <WifiOff :size="21" />
    <div>
      <strong>PulseBoard API unavailable</strong>
      <p>{{ error }}</p>
      <small v-if="updatedAt"
        >Showing saved data from {{ dateTime(updatedAt.toISOString()) }}.
        Service states have not been changed.</small
      >
    </div>
    <button class="button secondary small" @click="$emit('retry')">
      <RefreshCw :size="14" />Retry
    </button>
  </div>
</template>
