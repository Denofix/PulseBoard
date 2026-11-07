import { shallowRef } from "vue";
import type { PublicConfig } from "./types";

export const config = shallowRef<PublicConfig | null>(null);
