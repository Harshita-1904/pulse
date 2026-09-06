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

function formatPrice(v) {
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatTime(ts) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

function formatFullTime(ts) {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded shadow-sm px-3 py-2 text-sm">
      <div className="text-gray-500">{formatFullTime(label)}</div>
      <div className="font-semibold text-gray-900 font-mono">{formatPrice(payload[0].value)}</div>
    </div>
  );
}

const ZOOM_LEVELS = [100, 60, 40, 25, 15];

export default function PriceChart({ data, points, symbol = "", changePct }) {
  const [zoomIndex, setZoomIndex] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);
  const sourceData = data ?? points ?? [];

  const normalizedData = useMemo(() => sourceData
    .map((point) => ({
      timestamp: point.timestamp ?? point.recorded_at,
      price: Number(point.price),
      volume: point.volume == null ? null : Number(point.volume),
    }))
    .filter((point) => point.timestamp && Number.isFinite(point.price))
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)), [sourceData]);

  const visibleData = useMemo(() => {
    if (!normalizedData.length) return [];
    const pct = ZOOM_LEVELS[zoomIndex] / 100;
    const count = Math.min(normalizedData.length, Math.max(2, Math.round(normalizedData.length * pct)));
    return normalizedData.slice(normalizedData.length - count);
  }, [normalizedData, zoomIndex]);

  const { low, high } = useMemo(() => {
    if (!visibleData.length) return { low: 0, high: 0 };
    const prices = visibleData.map((d) => d.price);
    return { low: Math.min(...prices), high: Math.max(...prices) };
  }, [visibleData]);

  const yDomain = useMemo(() => {
    if (!visibleData.length) return [0, 1];
    const pad = (high - low) * 0.1 || high * 0.02 || 1;
    return [Math.floor(low - pad), Math.ceil(high + pad)];
  }, [low, high, visibleData.length]);

  const calculatedChangePct = useMemo(() => {
    if (visibleData.length < 2 || !visibleData[0].price) return null;
    const first = visibleData[0].price;
    const last = visibleData[visibleData.length - 1].price;
    return ((last - first) / first) * 100;
  }, [visibleData]);

  const effectiveChange = changePct ?? calculatedChangePct;
  const isPositive = (effectiveChange ?? 0) >= 0;

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) containerRef.current?.requestFullscreen?.();
    else document.exitFullscreen?.();
  }, []);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  if (!normalizedData.length) {
    return (
      <div className="border border-gray-200 rounded-lg bg-white p-5">
        <h3 className="font-semibold text-gray-900">Price chart</h3>
        <p className="text-sm text-gray-500 mt-8 text-center">Historical price data is not available yet.</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`border border-gray-200 rounded-lg bg-white ${isFullscreen ? "fixed inset-0 z-50 flex flex-col p-6" : "p-5"}`}>
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h3 className="font-semibold text-gray-900">{symbol ? `${symbol} price chart` : "Price chart"}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{visibleData.length} of {normalizedData.length} observations shown</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center border border-gray-200 rounded overflow-hidden">
            <button onClick={() => setZoomIndex((z) => Math.max(0, z - 1))} disabled={zoomIndex === 0} className="px-2.5 py-1.5 text-gray-700 hover:bg-gray-50 disabled:opacity-30 border-r border-gray-200">−</button>
            <button onClick={() => setZoomIndex(0)} className="px-2.5 py-1.5 text-xs text-gray-500 hover:bg-gray-50 border-r border-gray-200">{ZOOM_LEVELS[zoomIndex]}%</button>
            <button onClick={() => setZoomIndex((z) => Math.min(ZOOM_LEVELS.length - 1, z + 1))} disabled={zoomIndex === ZOOM_LEVELS.length - 1} className="px-2.5 py-1.5 text-gray-700 hover:bg-gray-50 disabled:opacity-30">+</button>
          </div>
          <button onClick={toggleFullscreen} className="px-2.5 py-1.5 border border-gray-200 rounded text-gray-700 hover:bg-gray-50 text-sm">{isFullscreen ? "Exit full screen" : "Full screen"}</button>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm mt-3 mb-1">
        <span className="text-gray-500 font-mono">{formatFullTime(visibleData[0].timestamp)} → {formatFullTime(visibleData[visibleData.length - 1].timestamp)}</span>
        {effectiveChange !== null && <span className={`font-mono font-medium ${isPositive ? "text-emerald-600" : "text-red-600"}`}>{isPositive ? "+" : ""}{effectiveChange.toFixed(2)}%</span>}
      </div>

      <div className={isFullscreen ? "flex-1 min-h-0" : "h-80"}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={visibleData} margin={{ top: 10, right: 16, bottom: 10, left: 8 }}>
            <CartesianGrid stroke="#E5E7EB" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="timestamp" tickFormatter={formatTime} stroke="#9CA3AF" tick={{ fontSize: 11, fill: "#6B7280" }} tickLine={false} axisLine={{ stroke: "#E5E7EB" }} minTickGap={40} />
            <YAxis domain={yDomain} tickFormatter={formatPrice} stroke="#9CA3AF" tick={{ fontSize: 11, fill: "#6B7280" }} tickLine={false} axisLine={{ stroke: "#E5E7EB" }} width={85} />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine y={visibleData[0]?.price} stroke="#D1D5DB" strokeDasharray="2 4" />
            <Line type="monotone" dataKey="price" stroke="#3B5BA5" strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between text-sm mt-2">
        <span className="text-gray-500">Low <span className="font-mono text-gray-700">{formatPrice(low)}</span></span>
        <span className="text-gray-500">High <span className="font-mono text-gray-700">{formatPrice(high)}</span></span>
      </div>
    </div>
  );
}
