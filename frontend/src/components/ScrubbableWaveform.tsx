// ScrubbableWaveform.tsx
"use client";

import { useEffect, useRef, useState } from "react";

interface ScrubbableWaveformProps {
  audioUrl: string;
  currentTime: number;
  duration: number;
  onScrub: (time: number) => void;
  className?: string; 
}

export function ScrubbableWaveform({
  audioUrl,
  currentTime,
  duration,
  onScrub,
  className = "",
}: ScrubbableWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [peaks, setPeaks] = useState<number[]>([]);
  const [computed, setComputed] = useState(false);

  useEffect(() => {
    // Only compute if duration > 0
    if (duration <= 0) return;

    async function computePeaks() {
      try {
        const resp = await fetch(audioUrl);
        const arrayBuffer = await resp.arrayBuffer();

        // Fallback to 1 second if duration is extremely short
        const offlineDuration = Math.max(duration, 1);
        const sampleRate = 44100;
        const offlineCtx = new OfflineAudioContext(1, sampleRate * offlineDuration, sampleRate);
        const audioBuffer = await offlineCtx.decodeAudioData(arrayBuffer);
        const channelData = audioBuffer.getChannelData(0);

        // Use a smaller binCount to avoid large computations
        const binCount = 150;
        const samplesPerBin = Math.floor(channelData.length / binCount);
        const localPeaks: number[] = [];
        for (let i = 0; i < binCount; i++) {
          const start = i * samplesPerBin;
          const end = start + samplesPerBin;
          let max = 0;
          for (let j = start; j < end && j < channelData.length; j++) {
            const val = Math.abs(channelData[j]);
            if (val > max) max = val;
          }
          localPeaks.push(max);
        }
        setPeaks(localPeaks);
        setComputed(true);
      } catch (err) {
        console.error("Error computing waveform:", err);
      }
    }

    computePeaks();
  }, [audioUrl, duration]);

  // Draw the waveform whenever peaks or currentTime changes
  useEffect(() => {
    if (!computed || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear the fixed 600x50 region
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw the waveform
    ctx.strokeStyle = "#4A5568"; // gray-700
    ctx.lineWidth = 1;
    ctx.beginPath();
    const binCount = peaks.length;
    const binWidth = canvas.width / binCount;
    for (let i = 0; i < binCount; i++) {
      const x = i * binWidth;
      const peak = peaks[i];
      const y = canvas.height - peak * canvas.height; // scale [0,1] => canvas height
      ctx.moveTo(x, canvas.height);
      ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Overlay the played portion
    const progress = Math.min(currentTime / duration, 1);
    ctx.fillStyle = "rgba(74,85,104,0.5)";
    ctx.fillRect(0, 0, canvas.width * progress, canvas.height);
  }, [peaks, currentTime, duration, computed]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = clickX / rect.width;
    onScrub(ratio * duration);
  };

  return (
    <div className={`relative ${className}`}>
      {/* A fixed 600x50 internal size. Style the container with w-full h-?? */}
      <canvas
        ref={canvasRef}
        width={600}
        height={50}
        className="w-full h-full cursor-pointer"
        onClick={handleClick}
      />
    </div>
  );
}
