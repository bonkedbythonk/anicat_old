"use client";

import { useState, useEffect } from "react";

/**
 * Extracts a vibrant ambient color from a banner image URL using
 * canvas pixel sampling. The returned CSS color string is used for
 * decorative glow/blur effects behind media artwork.
 *
 * Falls back to a default pink accent if extraction fails.
 */
export function useAmbientColor(bannerUrl: string | undefined | null): string {
  const [ambientColor, setAmbientColor] = useState<string>(
    "rgba(236, 72, 153, 0.18)"
  );

  useEffect(() => {
    if (!bannerUrl) return;

    // Set fallback immediately so the glow doesn't flash
    setAmbientColor("rgba(236, 72, 153, 0.18)");

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = bannerUrl;

    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        canvas.width = 10;
        canvas.height = 10;
        ctx.drawImage(img, 0, 0, 10, 10);

        const imgData = ctx.getImageData(0, 0, 10, 10).data;
        let r = 0,
          g = 0,
          b = 0,
          count = 0;

        // 1. Extract non-dark vibrant pixels
        for (let i = 0; i < imgData.length; i += 4) {
          const pr = imgData[i];
          const pg = imgData[i + 1];
          const pb = imgData[i + 2];

          if (pr + pg + pb > 120) {
            r += pr;
            g += pg;
            b += pb;
            count++;
          }
        }

        if (count > 0) {
          r = Math.round(r / count);
          g = Math.round(g / count);
          b = Math.round(b / count);
        } else {
          // Fallback to absolute average
          for (let i = 0; i < imgData.length; i += 4) {
            r += imgData[i];
            g += imgData[i + 1];
            b += imgData[i + 2];
          }
          const pixelCount = imgData.length / 4;
          r = Math.round(r / pixelCount);
          g = Math.round(g / pixelCount);
          b = Math.round(b / pixelCount);
        }

        // 2. Brightness boosting if the artwork is too dark to glow
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        if (brightness < 60) {
          const scale = 60 / (brightness || 1);
          r = Math.min(255, Math.round(r * scale));
          g = Math.min(255, Math.round(g * scale));
          b = Math.min(255, Math.round(b * scale));
        }

        // Minimum color threshold (fall back to accent pink)
        if (r < 30 && g < 30 && b < 30) {
          r = 236;
          g = 72;
          b = 153;
        }

        setAmbientColor(`rgba(${r}, ${g}, ${b}, 0.18)`);
      } catch (err) {
        console.warn(
          "[MediaDetail] Artwork color extraction blocked by CORS:",
          err
        );
      }
    };
  }, [bannerUrl]);

  return ambientColor;
}
