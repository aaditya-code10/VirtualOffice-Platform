/** KPI change indicator.
 *
 * The arrow shows which way the number moved; the colour shows whether that is
 * good news. Rising churn moves up and is red.
 */
import { Minus, TrendingDown, TrendingUp } from "lucide-react";

import type { Kpi } from "../api";

export function Delta({ kpi }: { kpi: Kpi }) {
  const Icon =
    kpi.direction === "up" ? TrendingUp : kpi.direction === "down" ? TrendingDown : Minus;

  return (
    <span className={`delta sentiment-${kpi.sentiment}`}>
      <Icon size={12} />
      {kpi.change_pct === null
        ? "no prior period"
        : `${kpi.change_pct > 0 ? "+" : ""}${kpi.change_pct}%`}
    </span>
  );
}
