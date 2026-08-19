import { cloneElement, useEffect, useRef, useState } from "react";

/**
 * Measures its own box and renders the Recharts chart with explicit pixel
 * width/height. This avoids Recharts' ResponsiveContainer, which logs
 * "width(-1) and height(-1) of chart should be greater than 0" on its first
 * measuring pass, while keeping the chart fully responsive.
 */
export default function ChartBox({ className = "h-72", children }) {
  const ref = useRef(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      setSize((prev) =>
        Math.abs(prev.w - r.width) > 1 || Math.abs(prev.h - r.height) > 1
          ? { w: Math.floor(r.width), h: Math.floor(r.height) }
          : prev
      );
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={ref} className={`w-full ${className}`}>
      {size.w > 0 && size.h > 0
        ? cloneElement(children, { width: size.w, height: size.h })
        : null}
    </div>
  );
}
