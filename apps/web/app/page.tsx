"use client";

import { useRef, useState } from "react";
import { Mic, Send, Square, Leaf, Volume2, CheckCircle2, Loader2 } from "lucide-react";

type Message = { role: "assistant" | "farmer"; text: string };
type Profile = { crop?: string | null; variety?: string | null; quality_grade?: string | null; quantity_kg?: number | null; quantity_original?: string | null; location?: string | null; ready_when?: string | null; selling_preference?: string | null; can_store?: boolean | null; preferred_language?: string | null };

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const newSessionId = () => `kx-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function Home() {
  const [sessionId] = useState(newSessionId);
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", text: "Namaste! Welcome to KRISHI-X. I can help you find a better route from your farm to market. You can speak or type. First, which crop have you harvested?" }
  ]);
  const [input, setInput] = useState("");
  const [profile, setProfile] = useState<Profile>({});
  const [missing, setMissing] = useState<string[]>(["crop", "quantity_kg", "location", "ready_when"]);
  const [ready, setReady] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  async function sendMessage(text: string) {
    const clean = text.trim();
    if (!clean) return;
    setMessages(prev => [...prev, { role: "farmer", text: clean }]);
    setInput("");
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: clean })
      });
      if (!res.ok) throw new Error("Could not reach KRISHI-X backend.");
      const data = await res.json();
      setProfile(data.profile || {});
      setMissing(data.missing_fields || []);
      setReady(Boolean(data.ready_for_confirmation));
      setConfirmed(false);
      setMessages(prev => [...prev, { role: "assistant", text: data.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", text: `${err instanceof Error ? err.message : "Something went wrong."} Please check that the backend is running on port 8000.` }]);
    } finally { setBusy(false); }
  }

  async function confirmProfile(ok: boolean) {
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/profile/confirm`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, confirmed: ok })
      });
      const data = await res.json();
      setConfirmed(Boolean(data.confirmed));
      setMessages(prev => [...prev, { role: "assistant", text: data.reply }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", text: "Could not confirm with the server. Please try again." }]);
    } finally { setBusy(false); }
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setMessages(prev => [...prev, { role: "assistant", text: "Microphone access is not available in this browser. Please type your answer instead." }]);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "";
      const media = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      recorder.current = media;
      chunks.current = [];
      media.ondataavailable = e => { if (e.data.size) chunks.current.push(e.data); };
      media.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        const blob = new Blob(chunks.current, { type: media.mimeType || "audio/webm" });
        const form = new FormData();
        form.append("file", blob, "farmer-recording.webm");
        setBusy(true);
        try {
          const response = await fetch(`${API}/api/voice/transcribe`, { method: "POST", body: form });
          const result = await response.json();
          if (!response.ok) throw new Error(result.detail || "Transcription failed.");
          if (result.transcript) {
            setMessages(prev => [...prev, { role: "farmer", text: `🎙 ${result.transcript}` }]);
            await sendMessage(result.transcript);
          } else {
            setMessages(prev => [...prev, { role: "assistant", text: "I could not hear clear speech. Please try again or type your answer." }]);
          }
        } catch (err) {
          setMessages(prev => [...prev, { role: "assistant", text: err instanceof Error ? err.message : "Voice transcription failed." }]);
        } finally { setBusy(false); }
      };
      media.start();
      recorder.current = media;
      setRecording(true);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", text: "Please allow microphone access, or type your answer." }]);
    }
  }

  function stopRecording() {
    if (recorder.current && recorder.current.state !== "inactive") recorder.current.stop();
    setRecording(false);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Leaf size={22} /></div><div><strong>KRISHI-X</strong><span>Farm-to-market intelligence</span></div></div>
        <div className="top-tag">VOICE-FIRST FARMER ASSISTANT</div>
      </header>
      <section className="hero">
        <div className="eyebrow">YOUR HARVEST. YOUR BEST MARKET.</div>
        <h1>Let’s find the <em>right market</em><br />for your harvest.</h1>
        <p>Tell KRISHI-X what you have. We’ll help compare market opportunities and the costs of getting there.</p>
      </section>
      <section className="workspace">
        <div className="chat-panel">
          <div className="chat-head"><div className="assistant-avatar"><Leaf size={19}/></div><div><strong>KRISHI-X Assistant</strong><span><i/> Ready to listen</span></div><div className="language-pill">Multilingual · Voice + text</div></div>
          <div className="messages">
            {messages.map((m, i) => <div key={i} className={`message-row ${m.role}`}><div className="bubble">{m.text}</div></div>)}
            {busy && <div className="message-row assistant"><div className="bubble typing"><Loader2 size={15}/> Working on it…</div></div>}
          </div>
          {ready && !confirmed && <div className="confirm-strip"><div><strong>Review your harvest details</strong><span>Confirm before we search for market options.</span></div><button onClick={() => confirmProfile(true)} disabled={busy}><CheckCircle2 size={16}/> Confirm details</button><button className="edit-btn" onClick={() => sendMessage("I want to correct my details")} disabled={busy}>Edit</button></div>}
          {confirmed && <div className="confirmed-note"><CheckCircle2 size={17}/> Farmer details confirmed. Market discovery will be connected in the next milestone.</div>}
          <form className="composer" onSubmit={e => { e.preventDefault(); sendMessage(input); }}>
            <input value={input} onChange={e => setInput(e.target.value)} placeholder="Type your answer here…" aria-label="Type your answer" />
            <button type="button" className={`mic-btn ${recording ? "recording" : ""}`} onClick={recording ? stopRecording : startRecording} title={recording ? "Stop recording" : "Start voice recording"}>{recording ? <Square size={18}/> : <Mic size={20}/>}</button>
            <button type="submit" className="send-btn" disabled={!input.trim() || busy}><Send size={18}/></button>
          </form>
          <div className="privacy-note"><Volume2 size={13}/> Voice is transcribed for this conversation. Check the transcript before confirming.</div>
        </div>
        <aside className="profile-panel">
          <div className="panel-kicker">LIVE INTAKE</div><h2>Your harvest profile</h2><p className="panel-desc">I’ll fill this in as we talk.</p>
          <ProfileItem label="Crop" value={profile.crop} />
          <ProfileItem label="Variety" value={profile.variety} />
          <ProfileItem label="Quality / grade" value={profile.quality_grade} />
          <ProfileItem label="Quantity" value={profile.quantity_kg ? `${profile.quantity_kg.toLocaleString()} kg${profile.quantity_original ? ` (${profile.quantity_original})` : ""}` : null} />
          <ProfileItem label="Farm location" value={profile.location} />
          <ProfileItem label="Ready for sale" value={profile.ready_when} />
          <ProfileItem label="Selling preference" value={profile.selling_preference?.replaceAll("_", " ")} />
          <ProfileItem label="Can store produce" value={profile.can_store === null || profile.can_store === undefined ? null : profile.can_store ? "Yes" : "No"} />
          <div className="profile-progress"><div className="progress-label"><span>Profile completeness</span><strong>{4 - missing.length}/4</strong></div><div className="progress-track"><div style={{width: `${((4 - missing.length) / 4) * 100}%`}}/></div></div>
          <div className="scope-note"><strong>What happens next?</strong><span>After you confirm, KRISHI-X will compare mandi prices, buyer demand and transport costs to estimate your net realization.</span></div>
          <div className="demo-label">INTAKE PROTOTYPE · LIVE MARKET DATA NOT CONNECTED</div>
        </aside>
      </section>
      <footer>KRISHI-X <span>·</span> AI that finds the most profitable route from farm to market.</footer>
    </main>
  );
}

function ProfileItem({ label, value }: { label: string; value?: string | null }) {
  return <div className="profile-item"><span>{label}</span><strong className={value ? "" : "empty"}>{value || "Waiting for your answer"}</strong></div>;
}
