/** City views, from backend/config.py CITIES. */
export const CITY_VIEW: Record<string, { center: [number, number]; zoom: number }> = {
  Mumbai: { center: [72.8777, 19.076], zoom: 11 },
  Delhi: { center: [77.209, 28.6139], zoom: 11 },
  Bangalore: { center: [77.5946, 12.9716], zoom: 11 },
  Hyderabad: { center: [78.4867, 17.385], zoom: 11 },
  Chennai: { center: [80.2707, 13.0827], zoom: 11 },
  Kolkata: { center: [88.3639, 22.5726], zoom: 11 },
  Pune: { center: [73.8567, 18.5204], zoom: 11 },
  Ahmedabad: { center: [72.5714, 23.0225], zoom: 11 },
  "All India": { center: [78.9629, 20.5937], zoom: 4.1 },
};
