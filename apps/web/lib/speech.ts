import { API, transcribe } from "./api";
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
/** True while any of our own voice is playing (browser voice or the offline audio). */
export function isSpeaking(): boolean {
  if (typeof window === "undefined") return false;
  return !!window.speechSynthesis?.speaking || (!!audio && !audio.paused && !audio.ended);
}

/** Half-duplex: resolve only after 600 ms of continuous silence from our own voice (max 60 s), so the mic never hears us. */
export function waitSilence(): Promise<void> {
  return new Promise((done) => {
    let quiet = 0;
    const t0 = Date.now();
    const t = setInterval(() => {
      quiet = isSpeaking() ? 0 : quiet + 100;
      if (quiet >= 600 || Date.now() - t0 > 60000) { clearInterval(t); done(); }
    }, 100);
  });
}

export async function listen(lang: Lang, onStop?: (stop: () => void) => void): Promise<string> {
  await waitSilence();
  return listenNow(lang, onStop);
}

function listenNow(lang: Lang, onStop?: (stop: () => void) => void): Promise<string> {
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
  return navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } }).then((stream) => new Promise<string>((resolve, reject) => {
    const rec = new MediaRecorder(stream); const chunks: Blob[] = [];
    rec.ondataavailable = (e) => chunks.push(e.data);
    rec.onstop = () => { stream.getTracks().forEach((t) => t.stop()); transcribe(new Blob(chunks, { type: rec.mimeType })).then(resolve, reject); };
    const timer = setTimeout(() => rec.state === "recording" && rec.stop(), 15000);
    onStop?.(() => { clearTimeout(timer); if (rec.state === "recording") rec.stop(); });
    rec.start();
  }));
}

let audio: HTMLAudioElement | null = null;

/** Speak and resolve when done (so the hands-free loop can listen again). Browser voice first (instant); if the device has no
 *  voice for this language (common for Hindi/Marathi on Windows), use the backend's offline Piper voice; else stay silent. */
export function speak(text: string, lang: Lang): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  window.speechSynthesis?.cancel();
  audio?.pause();
  const voices = window.speechSynthesis?.getVoices() ?? [];
  const v = voices.find((x) => x.lang.replace("_", "-") === BCP47[lang]) ?? voices.find((x) => x.lang.toLowerCase().startsWith(lang));
  if (v) {
    return new Promise((done) => {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = BCP47[lang]; u.voice = v; u.rate = 1.05;
      let finished = false;
      const end = () => { if (!finished) { finished = true; setTimeout(done, 350); } }; // short gap so the mic never catches our own last word
      u.onend = end; u.onerror = end;
      window.speechSynthesis.speak(u);
      // onend sometimes never fires (Chrome): poll the real speaking state instead of guessing from the text length
      const t0 = Date.now();
      const poll = setInterval(() => {
        if (finished) return clearInterval(poll);
        if ((!window.speechSynthesis.speaking && Date.now() - t0 > 800) || Date.now() - t0 > 60000) { clearInterval(poll); end(); }
      }, 250);
    });
  }
  return fetch(`${API}/api/voice/speak`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, lang }) })
    .then((r) => (r.ok ? r.blob() : Promise.reject()))
    .then((b) => new Promise<void>((done) => { audio = new Audio(URL.createObjectURL(b)); audio.onended = () => setTimeout(done, 400); audio.onerror = () => done(); audio.play().catch(() => done()); }))
    .catch(() => undefined);
}

/** True when what the mic heard is mostly our own last reply (speaker echo), so it must not be sent as the farmer's answer. */
const recent: string[] = []; // our last few replies: an echo can be of any of them

export function rememberReply(text: string) {
  if (text) { recent.push(text); if (recent.length > 4) recent.shift(); }
}

/** Echo of our own voice: most of the heard words come from one of our recent replies (short echoes count too). */
export function isEchoOfRecent(heard: string): boolean {
  const norm = (x: string) => x.toLowerCase().replace(/[^\p{L}\p{M}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
  const h = norm(heard);
  if (!h) return false;
  return recent.some((r) => {
    const rr = norm(r);
    if (rr.includes(h) && h.split(" ").length >= 2) return true;
    const hw = h.split(" ").filter((w) => w.length > 1), rw = new Set(rr.split(" "));
    return hw.length >= 2 && hw.filter((w) => rw.has(w)).length / hw.length >= 0.6;
  });
}

export function isEcho(heard: string, lastReply: string): boolean {
  const words = (x: string) => x.toLowerCase().replace(/[^\p{L}\p{M}\p{N}\s]/gu, " ").split(/\s+/).filter((w) => w.length > 1);
  const h = words(heard), r = new Set(words(lastReply));
  if (h.length < 4 || r.size === 0) return false;
  return h.filter((w) => r.has(w)).length / h.length >= 0.7;
}

export const stopSpeaking = () => { if (typeof window !== "undefined") { window.speechSynthesis?.cancel(); audio?.pause(); } };
