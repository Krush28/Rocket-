import { transcribe } from "./api";
import type { Lang } from "./i18n";

const BCP47: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

type Rec = { lang: string; interimResults: boolean; maxAlternatives: number; start(): void; stop(): void;
  onresult: ((e: { results: { 0: { transcript: string } }[] }) => void) | null; onerror: ((e: { error: string }) => void) | null; onend: (() => void) | null };

function recognizer(): (new () => Rec) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: new () => Rec; webkitSpeechRecognition?: new () => Rec };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

/** Browser speech recognition when available; otherwise record up to 15 s and send to the backend transcriber. */
export function listen(lang: Lang, onStop?: (stop: () => void) => void): Promise<string> {
  const R = recognizer();
  if (R) {
    return new Promise((resolve, reject) => {
      const r = new R();
      r.lang = BCP47[lang]; r.interimResults = false; r.maxAlternatives = 1;
      let said = "";
      r.onresult = (e) => { said = e.results[0][0].transcript; };
      r.onerror = (e) => reject(new Error(e.error === "not-allowed" ? "Microphone permission was denied." : "I could not hear that. Please try again."));
      r.onend = () => resolve(said);
      onStop?.(() => r.stop());
      r.start();
    });
  }
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) return Promise.reject(new Error("No microphone here. Please type instead."));
  return navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => new Promise<string>((resolve, reject) => {
    const rec = new MediaRecorder(stream); const chunks: Blob[] = [];
    rec.ondataavailable = (e) => chunks.push(e.data);
    rec.onstop = () => { stream.getTracks().forEach((t) => t.stop()); transcribe(new Blob(chunks, { type: rec.mimeType })).then(resolve, reject); };
    const timer = setTimeout(() => rec.state === "recording" && rec.stop(), 15000);
    onStop?.(() => { clearTimeout(timer); if (rec.state === "recording") rec.stop(); });
    rec.start();
  }));
}

export function speak(text: string, lang: Lang) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = BCP47[lang];
  const v = window.speechSynthesis.getVoices().find((x) => x.lang === BCP47[lang]);
  if (v) u.voice = v;
  window.speechSynthesis.speak(u);
}
