import { useMemo, useRef, useState, useEffect, useCallback } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";

// ---- helpers ----------------------------------------------------------

function formatPrice(v) {
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

function formatFullTime(ts) {
  const d = new Date(ts);
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Custom tooltip so it matches the app's tone instead of Recharts' default box
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-sm">
      <div className="text-gray-500">{formatFullTime(label)}</div>
      <div className="font-semibold text-gray-900 font-mono">{formatPrice(payload[0].value)}</div>
    </div>
  );
}

// ---- main component -----------------------------------------------------

// Props:
//   data: [{ timestamp: string | number, price: number }, ...]  (ordered oldest -> newest)
//   symbol: "RELIANCE"
//   changePct: -1.60   (over the visible window, e.g. "100 collected observations")
const ZOOM_LEVELS = [100, 60, 40, 25, 15]; // % of the dataset's most-recent points shown
const MIN_ZOOM_INDEX = 0;
const MAX_ZOOM_INDEX = ZOOM_LEVELS.length - 1;

export default function PriceChart({ data, symbol = "", changePct }) {
  const [zoomIndex, setZoomIndex] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);

  const visibleData = useMemo(() => {
    if (!data || data.length === 0) return [];
    const pct = ZOOM_LEVELS[zoomIndex] / 100;
    const count = Math.max(2, Math.round(data.length * pct));
    return data.slice(data.length - count);
  }, [data, zoomIndex]);

  const { low, high } = useMemo(() => {
    if (visibleData.length === 0) return { low: 0, high: 0 };
    const prices = visibleData.map((d) => d.price);
    return { low: Math.min(...prices), high: Math.max(...prices) };
  }, [visibleData]);

  const yDomain = useMemo(() => {
    const pad = (high - low) * 0.1 || high * 0.02 || 1;
    return [Math.floor(low - pad), Math.ceil(high + pad)];
  }, [low, high]);

  const canZoomIn = zoomIndex < MAX_ZOOM_INDEX;
  const canZoomOut = zoomIndex > MIN_ZOOM_INDEX;

  const handleZoomIn = () => setZoomIndex((z) => Math.min(MAX_ZOOM_INDEX, z + 1));
  const handleZoomOut = () => setZoomIndex((z) => Math.max(MIN_ZOOM_INDEX, z - 1));
  const handleZoomReset = () => setZoomIndex(0);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  }, []);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const isPositive = (changePct ?? 0) >= 0;

  return (
    <div
      ref={containerRef}
      className={`border border-gray-200 rounded-lg bg-white ${
        isFullscreen ? "fixed inset-0 z-50 flex flex-col p-6" : "p-5"
      }`}
    >
      {/* Header row: title + observation count on left, controls on right */}
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h3 className="font-semibold text-gray-900">Price chart</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            {visibleData.length} of {data.length} observations shown
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center border border-gray-200 rounded overflow-hidden">
            <button
              onClick={handleZoomOut}
              disabled={!canZoomOut}
              title="Zoom out"
              className="px-2.5 py-1.5 text-gray-700 hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent border-r border-gray-200"
            >
              −
            </button>
            <button
              onClick={handleZoomReset}
              title="Reset zoom"
              className="px-2.5 py-1.5 text-xs text-gray-500 hover:bg-gray-50 border-r border-gray-200"
            >
              {ZOOM_LEVELS[zoomIndex]}%
            </button>
            <button
              onClick={handleZoomIn}
              disabled={!canZoomIn}
              title="Zoom in"
              className="px-2.5 py-1.5 text-gray-700 hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent"
            >
              +
            </button>
          </div>

          <button
            onClick={toggleFullscreen}
            title={isFullscreen ? "Exit full screen" : "Full screen"}
            className="px-2.5 py-1.5 border border-gray-200 rounded text-gray-700 hover:bg-gray-50 text-sm"
          >
            {isFullscreen ? "Exit full screen" : "Full screen"}
          </button>
        </div>
      </div>

      {/* Range + change, above the chart */}
      <div className="flex items-center justify-between text-sm mt-3 mb-1">
        <span className="text-gray-500 font-mono">
          {visibleData[0] ? formatFullTime(visibleData[0].timestamp) : ""}
          {" → "}
          {visibleData[visibleData.length - 1] ? formatFullTime(visibleData[visibleData.length - 1].timestamp) : ""}
        </span>
        <span className={`font-mono font-medium ${isPositive ? "text-emerald-600" : "text-red-600"}`}>
          {isPositive ? "+" : ""}
          {changePct?.toFixed(2)}%
        </span>
      </div>

      {/* Chart */}
      <div className={isFullscreen ? "flex-1 min-h-0" : "h-72"}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={visibleData} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatTime}
              stroke="#9CA3AF"
              tick={{ fontSize: 11, fill: "#6B7280" }}
              tickLine={false}
              axisLine={{ stroke: "#E5E7EB" }}
              minTickGap={40}
              label={{ value: "Time", position: "insideBottom", offset: -4, fontSize: 11, fill: "#9CA3AF" }}
            />
            <YAxis
              domain={yDomain}
              tickFormatter={formatPrice}
              stroke="#9CA3AF"
              tick={{ fontSize: 11, fill: "#6B7280" }}
              tickLine={false}
              axisLine={{ stroke: "#E5E7EB" }}
              width={80}
              label={{ value: "Price (₹)", angle: -90, position: "insideLeft", fontSize: 11, fill: "#9CA3AF" }}
            />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine y={visibleData[0]?.price} stroke="#D1D5DB" strokeDasharray="2 4" />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#3B5BA5"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Footer: low/high for the visible window */}
      <div className="flex items-center justify-between text-sm mt-2">
        <span className="text-gray-500">
          Low <span className="font-mono text-gray-700">{formatPrice(low)}</span>
        </span>
        <span className="text-gray-500">
          High <span className="font-mono text-gray-700">{formatPrice(high)}</span>
        </span>
      </div>
    </div>
  );
}
