"use client";
import * as React from "react";
import { FeedBackground } from "@/components/three/feed-canvas";
import { feedBus } from "@/lib/three/feed-bus";

export function FeedLayer() {
  // Drop the hand-off when the layer goes away so sections never drive a disposed engine.
  React.useEffect(() => () => feedBus.set(null), []);
  return <FeedBackground onReady={(e) => feedBus.set(e)} />;
}
