<script setup lang="ts">
import { Radio } from "lucide-vue-next";
defineProps<{ title: string; description: string }>();
</script>
<template>
  <div class="empty-state">
    <span class="empty-icon"><Radio :size="25" /></span>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>
