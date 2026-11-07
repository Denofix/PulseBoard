import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import DashboardView from "./views/DashboardView.vue";
import ServiceView from "./views/ServiceView.vue";
import IncidentsView from "./views/IncidentsView.vue";
import NotFoundView from "./views/NotFoundView.vue";
import "./style.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: DashboardView },
    { path: "/services", component: DashboardView },
    { path: "/services/:id(\\d+)", component: ServiceView },
    { path: "/incidents", component: IncidentsView },
    { path: "/:pathMatch(.*)*", component: NotFoundView },
  ],
  scrollBehavior(to) {
    return to.hash ? { el: to.hash, top: 100, behavior: "smooth" } : { top: 0 };
  },
});
createApp(App).use(router).mount("#app");
