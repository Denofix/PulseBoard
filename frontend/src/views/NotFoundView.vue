<script setup lang="ts">
import EmptyState from "../components/EmptyState.vue";
</script>
<template>
  <EmptyState
    title="This page isn't here"
    description="Your services are one click away."
    ><RouterLink to="/" class="button primary"
      >Back to overview</RouterLink
    ></EmptyState
  >
</template>
