"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertSocket } from "@/lib/api/socket";
import { useConsoleStore } from "@/lib/state/console-store";
import { useAlertHistory } from "@/lib/api/console-hooks";

/** One WebSocket per tab. Mounted once by the console shell; seeds the buffer from the alert history. */
export function LiveConnection() {
  const qc = useQueryClient();
  const pushAlert = useConsoleStore((s) => s.pushAlert);
  const markGateTrip = useConsoleStore((s) => s.markGateTrip);
  const setConnection = useConsoleStore((s) => s.setConnection);
  const history = useAlertHistory();
  const seeded = React.useRef(false);

  React.useEffect(() => {
    if (seeded.current || !history.data) return;
    seeded.current = true;
    const list = [...history.data.alerts].reverse();
    for (const a of list) {
      pushAlert({
        type: "ALERT", id: a.id, camera_id: a.camera_id, city: a.city ?? null, event_type: a.event_type, trust_score: a.trust_score,
        action_tier: (["high_trust", "medium_trust", "low_trust"].includes(a.action_tier) ? a.action_tier : "low_trust") as "low_trust",
        contributing_factors: a.contributing_factors ?? [], corroborated_by: a.corroborated_by ?? [], detected_at: a.detected_at,
        probabilistic_score: a.probabilistic_score ?? null, decayed_score: a.decayed_score ?? null,
        integrity_gate_tripped: !!a.integrity_gate_tripped, gate_status: a.gate_status ?? null,
        signal_integrity_score: a.signal_integrity_score ?? null, drift_score: a.drift_score ?? null,
        // is_demo is persisted by the backend; the SIM_ prefix covers rows written before it existed
        demo: !!(a.is_demo ?? a.demo) || a.camera_id.startsWith("SIM_"),
      });
    }
  }, [history.data, pushAlert]);

  React.useEffect(() => {
    const socket = new AlertSocket({
      onMessage: (m) => {
        if (m.type === "ALERT") {
          pushAlert(m);
          void qc.invalidateQueries({ queryKey: ["summary"] });
          void qc.invalidateQueries({ queryKey: ["timeline"] });
        } else {
          markGateTrip();
        }
      },
      onState: (state, info) => setConnection(state, info.retryInMs),
    });
    // One tick later so React StrictMode's throwaway first mount never opens (and then abandons) a socket.
    const boot = setTimeout(() => socket.connect(), 0);
    return () => {
      clearTimeout(boot);
      socket.close();
    };
  }, [pushAlert, markGateTrip, setConnection, qc]);

  return null;
}
