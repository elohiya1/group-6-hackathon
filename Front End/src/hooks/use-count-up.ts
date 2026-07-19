import { useEffect, useState } from "react";

/**
 * Animate a numeric value from 0 to `target` over `duration` ms.
 * Respects prefers-reduced-motion (jumps to target immediately).
 */
export function useCountUp(target: number | null | undefined, duration = 500) {
  const [value, setValue] = useState<number>(target ?? 0);

  useEffect(() => {
    if (target === null || target === undefined) {
      setValue(0);
      return;
    }
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce || duration <= 0) {
      setValue(target);
      return;
    }
    const start = performance.now();
    const from = 0;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(from + (target - from) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
      else setValue(target);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return value;
}
