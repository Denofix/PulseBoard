<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { X, Plus, LoaderCircle, Info } from "lucide-vue-next";
import { api } from "../api";
import { config } from "../state";

const emit = defineEmits<{ close: []; created: [] }>();
const name = ref(""),
  url = ref(""),
  error = ref(""),
  submitting = ref(false);
const nameInput = ref<HTMLInputElement>();
const dialog = ref<HTMLDialogElement>();
const controller = new AbortController();
onMounted(() => {
  dialog.value?.showModal();
  nameInput.value?.focus();
});
onUnmounted(() => controller.abort());

async function submit() {
  error.value = "";
  try {
    const parsed = new URL(url.value);
    if (
      !["http:", "https:"].includes(parsed.protocol) ||
      parsed.username ||
      parsed.password ||
      parsed.hash
    )
      throw new Error();
  } catch {
    error.value =
      "Enter an HTTP or HTTPS URL without credentials or a fragment.";
    return;
  }
  if (!name.value.trim()) {
    error.value = "Enter a name for this service.";
    return;
  }
  if (!config.value || config.value.read_only) {
    error.value = "Service management is unavailable in this workspace.";
    return;
  }
  submitting.value = true;
  try {
    await api.create(name.value.trim(), url.value.trim(), controller.signal);
    emit("created");
  } catch (cause) {
    if (!controller.signal.aborted)
      error.value =
        cause instanceof Error ? cause.message : "Could not add service";
  } finally {
    submitting.value = false;
  }
}
</script>
<template>
  <dialog
    ref="dialog"
    class="service-dialog"
    aria-labelledby="dialog-title"
    @cancel.prevent="emit('close')"
    @click="
      (event) => {
        if (event.target === dialog) emit('close');
      }
    "
  >
    <div class="dialog-header">
      <div>
        <h2 id="dialog-title">Add a service</h2>
        <p>A simple check. A clearer picture.</p>
      </div>
      <button
        class="icon-button"
        aria-label="Close form"
        @click="emit('close')"
      >
        <X :size="20" />
      </button>
    </div>
    <form @submit.prevent="submit">
      <label for="service-name">Service name</label
      ><input
        id="service-name"
        ref="nameInput"
        v-model="name"
        placeholder="e.g. Production API"
        maxlength="100"
        required
        :disabled="submitting"
      />
      <label for="service-url">Service URL</label
      ><input
        id="service-url"
        v-model="url"
        type="url"
        placeholder="https://example.com/health"
        maxlength="2048"
        required
        :disabled="submitting"
      /><small class="input-help"
        >HTTP and HTTPS. Local network and Docker hostnames are
        supported.</small
      >
      <div class="form-note">
        <Info :size="17" /><span
          >GET every {{ config?.interval_seconds }} seconds. Only HTTP 200–299
          counts as up. Redirects are not followed.</span
        >
      </div>
      <p v-if="error" role="alert" class="form-error">{{ error }}</p>
      <div class="dialog-actions">
        <button type="button" class="button secondary" @click="emit('close')">
          Cancel</button
        ><button type="submit" class="button primary" :disabled="submitting">
          <LoaderCircle v-if="submitting" class="spin" :size="16" /><Plus
            v-else
            :size="16"
          />{{ submitting ? "Adding…" : "Add service" }}
        </button>
      </div>
    </form>
  </dialog>
</template>
