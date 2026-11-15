export function formatSeconds(sec: number): string {
  if (sec < 0 || isNaN(sec)) return "00:00";
  const mins = Math.floor(sec / 60);
  const remaining = Math.floor(sec % 60);
  return `${mins.toString().padStart(2, "0")}:${remaining.toString().padStart(2, "0")}`;
}

export function countWords(text: string): number {
  if (!text || !text.trim()) return 0;
  return text.trim().split(/\s+/).length;
}

export function truncateToMaxWords(text: string, maxWords: number): string {
  if (!text) return "";
  const words = text.trim().split(/\s+/);
  if (words.length <= maxWords) return text.trim();
  return words.slice(0, maxWords).join(" ");
}

export function sanitizeText(text: string): string {
  if (!text) return "";
  return text
    .replace(/\u2014/g, ", ")
    .replace(/\u2013/g, ", ")
    .replace(/\s+/g, " ")
    .trim();
}
