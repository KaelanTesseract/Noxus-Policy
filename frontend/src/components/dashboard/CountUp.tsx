"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { introState, prefersReducedMotion } from "@/lib/motion";

/** Shows a number; on the first view of the page it counts up to the value once. */
export function CountUp({ value, format }: { value: number; format: (n: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (introState.countUpPlayed || prefersReducedMotion() || value <= 0) {
      el.textContent = format(value);
      return;
    }
    const counter = { n: 0 };
    const tween = gsap.to(counter, {
      n: value,
      duration: 1.1,
      ease: "power2.out",
      onUpdate: () => { el.textContent = format(counter.n); },
      onComplete: () => { el.textContent = format(value); introState.countUpPlayed = true; },
    });
    return () => { tween.kill(); };
    // format is a stable module-level function at the call site
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <span ref={ref}>{format(value)}</span>;
}
