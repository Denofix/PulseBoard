import { describe, expect, it } from "vitest";
import { mount, RouterLinkStub } from "@vue/test-utils";
import ApiNotice from "../src/components/ApiNotice.vue";
import HeartbeatStrip from "../src/components/HeartbeatStrip.vue";
import LatencyChart from "../src/components/LatencyChart.vue";
import IncidentTimeline from "../src/components/IncidentTimeline.vue";
import type { Check, Incident } from "../src/types";

const checks: Check[] = [
  {
    id: 1,
    service_id: 2,
    checked_at: "2026-11-07T12:00:00Z",
    status: "UP",
    http_status: 200,
    response_time_ms: 12,
    error_type: null,
    error_message: null,
    gap_before_seconds: 0,
  },
  {
    id: 2,
    service_id: 2,
    checked_at: "2026-11-07T12:00:15Z",
    status: "DOWN",
    http_status: null,
    response_time_ms: null,
    error_type: "TIMEOUT",
    error_message: "Request timed out",
    gap_before_seconds: 0,
  },
  {
    id: 3,
    service_id: 2,
    checked_at: "2026-11-07T12:02:15Z",
    status: "DOWN",
    http_status: 500,
    response_time_ms: 21,
    error_type: "HTTP_STATUS",
    error_message: "HTTP 500",
    gap_before_seconds: 105,
  },
];
const global = { stubs: { RouterLink: RouterLinkStub } };

describe("API connection state", () => {
  it("distinguishes API unavailability from monitored service status", async () => {
    const wrapper = mount(ApiNotice, {
      props: {
        error: "Connection refused",
        updatedAt: new Date("2026-11-07T12:00:00Z"),
      },
    });
    expect(wrapper.get('[role="alert"]').text()).toContain(
      "PulseBoard API unavailable",
    );
    expect(wrapper.text()).toContain("Service states have not been changed");
    expect(wrapper.find(".status-badge.down").exists()).toBe(false);
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("retry")).toHaveLength(1);
  });
  it("does not announce an error when API is reachable", () => {
    expect(
      mount(ApiNotice, { props: { error: null } })
        .find('[role="alert"]')
        .exists(),
    ).toBe(false);
  });
});

describe("real heartbeat observations", () => {
  it("keeps one entry per check and distinct gap markers with accurate tooltips", () => {
    const wrapper = mount(HeartbeatStrip, {
      props: { checks, stale: true },
      global,
    });
    const beats = wrapper.findAll("[data-check-id]");
    expect(beats).toHaveLength(3);
    expect(beats[1]!.attributes("aria-label")).toContain("Check #2");
    expect(beats[1]!.attributes("aria-label")).toContain(
      "HTTP no response · — · TIMEOUT",
    );
    expect(beats[2]!.attributes("aria-label")).toContain("HTTP 500 · 21 ms");
    expect(wrapper.findAll(".heartbeat-gap")).toHaveLength(2);
    expect(wrapper.findAllComponents(RouterLinkStub)[0]!.props("to")).toContain(
      "check=1",
    );
  });
  it("does not invent checks for an empty service", () => {
    const wrapper = mount(HeartbeatStrip, { props: { checks: [] }, global });
    expect(wrapper.findAll("[data-check-id]")).toHaveLength(0);
    expect(wrapper.text()).toContain("No observations yet");
  });
});

describe("latency gaps", () => {
  it("breaks the line at null latency and monitoring gaps, keeping status markers", () => {
    const wrapper = mount(LatencyChart, {
      props: {
        checks,
        interval: 15,
        gapThreshold: 23,
        now: Date.parse(checks[2]!.checked_at),
      },
    });
    expect(wrapper.findAll("polyline")).toHaveLength(2);
    expect(wrapper.findAll("[data-gap]")).toHaveLength(1);
    expect(wrapper.findAll("circle")).toHaveLength(3);
    expect(wrapper.get('circle[data-check-id="2"]').attributes("cy")).toBe(
      "177",
    );
    expect(wrapper.get('circle[data-check-id="3"]').classes()).toContain(
      "down",
    );
    expect(wrapper.get("svg").attributes("aria-label")).toContain(
      "milliseconds",
    );
  });
  it("shows a short restart gap even below the time threshold", () => {
    const afterRestart = {
      ...checks[0]!,
      id: 2,
      checked_at: "2026-11-07T12:00:02Z",
      gap_before_seconds: 2,
    };
    const wrapper = mount(LatencyChart, {
      props: {
        checks: [checks[0]!, afterRestart],
        interval: 15,
        gapThreshold: 23,
        now: Date.parse(afterRestart.checked_at),
      },
    });
    expect(wrapper.findAll("polyline")).toHaveLength(2);
    expect(wrapper.findAll("[data-gap]")).toHaveLength(1);
  });
});

it("links an incident to its exact opening check", () => {
  const incident: Incident = {
    id: 1,
    service_id: 2,
    service_name: "API",
    opened_at: checks[1]!.checked_at,
    closed_at: null,
    opening_check_id: 2,
    closing_check_id: null,
    reason: "Timeout",
    last_observed_at: checks[2]!.checked_at,
    observation_gap_seconds: 105,
    observed_duration_seconds: 15,
    elapsed_seconds: 120,
  };
  const wrapper = mount(IncidentTimeline, {
    props: { incidents: [incident] },
    global,
  });
  const evidence = wrapper
    .findAllComponents(RouterLinkStub)
    .find((link) => String(link.props("to")).includes("check="));
  expect(evidence?.props("to")).toBe("/services/2?check=2#check-evidence");
  expect(wrapper.text()).toContain("1m 45s without observations, excluded");
});
