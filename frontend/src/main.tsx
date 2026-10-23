import { FormEvent, StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { request } from "./api";
import { RoleDashboard } from "./RoleDashboard";
import { ReportsPanel } from "./ReportsPanel";
import "./styles.css";

type Profile = { date_of_birth: string | null; sex_at_birth: string | null; phone_number: string | null; no_reports_declared: boolean };
type Question = { id: string; prompt: string; required: boolean; options: string[] | null; multiple?: boolean };
type Screening = { id: string; created_at: string; responses: Record<string, unknown>; missing_fields: string[]; predicted_urgency: string | null; prediction_score: number | null; explanation: Record<string, unknown> | null; emergency_warning: boolean; emergency_reasons: string[]; review_status: string | null };
type SubmissionResult = { screening_id: string; emergency_warning: boolean; emergency_reasons: string[]; message: string };

function App() {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [token, setToken] = useState<string | null>(null); const [role, setRole] = useState(""); const [message, setMessage] = useState("CURE is an academic prototype, not emergency care or a diagnostic system.");
  const [profile, setProfile] = useState<Profile>({ date_of_birth: null, sex_at_birth: null, phone_number: null, no_reports_declared: false });
  const [selected, setSelected] = useState<string[]>([]); const [questions, setQuestions] = useState<Question[]>([]); const [responses, setResponses] = useState<Record<string, unknown>>({}); const [result, setResult] = useState<SubmissionResult | null>(null); const [history, setHistory] = useState<Screening[]>([]); const [loading, setLoading] = useState(false);

  async function auth(register: boolean) { try { const data = await request<{ access_token: string }>(`/auth/${register ? "register" : "login"}`, { method: "POST", body: JSON.stringify({ email, password }) }); const me = await request<{ role: string }>("/auth/me", {}, data.access_token); if (me.role === "patient") { const savedProfile = await request<Profile>("/patients/me/profile", {}, data.access_token); setProfile(savedProfile); } setToken(data.access_token); setRole(me.role); setMessage("Signed in successfully."); } catch (e) { setMessage(e instanceof Error ? e.message : "Request failed"); } }
  async function saveProfile(e: FormEvent) { e.preventDefault(); try { await request("/patients/me/profile", { method: "PUT", body: JSON.stringify(profile) }, token ?? undefined); setMessage("Profile saved."); } catch (e) { setMessage(e instanceof Error ? e.message : "Request failed"); } }
  async function refreshHistory() { if (!token) return; try { setHistory(await request<Screening[]>("/screenings?limit=50&offset=0", {}, token)); } catch (e) { setMessage(e instanceof Error ? e.message : "Unable to load screening history"); } }

  useEffect(() => {
    if (!token || role !== "patient") return;
    const params = new URLSearchParams(); selected.forEach((symptom) => params.append("selected", symptom));
    void request<Question[]>(`/questionnaire/questions?${params.toString()}`, {}, token).then(setQuestions).catch((e) => setMessage(e instanceof Error ? e.message : "Unable to load questionnaire"));
  }, [token, role, selected]);
  useEffect(() => { if (token && role === "patient") void refreshHistory(); }, [token, role]);

  function setAnswer(id: string, value: unknown) { setResponses((current) => ({ ...current, [id]: value })); }
  function toggleAnswerOption(id: string, option: string) { const current = Array.isArray(responses[id]) ? responses[id] as string[] : []; setAnswer(id, current.includes(option) ? current.filter((item) => item !== option) : [...current, option]); }
  function toggleSymptom(value: string) { const updated = selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]; setSelected(updated); setAnswer("symptoms", updated); setResult(null); }
  async function submit(e: FormEvent) {
    e.preventDefault(); setLoading(true); setResult(null);
    try { const data = await request<SubmissionResult>("/questionnaire/submit", { method: "POST", body: JSON.stringify({ responses: { ...responses, symptoms: selected } }) }, token ?? undefined); setResult(data); setMessage(data.message); await refreshHistory(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to submit screening"); }
    finally { setLoading(false); }
  }
  if (!token) return <main><section><p className="eyebrow">Academic decision-support prototype</p><h1>CURE</h1><h2>Clinical Urgency &amp; Risk Evaluation</h2><p role="status">{message}</p><form onSubmit={(e) => { e.preventDefault(); void auth(false); }}><label>Email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label><label>Password<input type="password" minLength={12} required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></label><button>Sign in</button><button type="button" onClick={() => void auth(true)}>Create patient account</button></form><p className="warning">If you believe you are experiencing an emergency, seek emergency help now. Do not wait for CURE.</p></section></main>;
  if (role !== "patient") return <main><section><p className="eyebrow">{role.replaceAll("_", " ")} workspace</p><h1>CURE</h1><p role="status">{message}</p><RoleDashboard role={role} token={token} onMessage={setMessage} /></section></main>;

  return <main><section className="patient-shell"><header><p className="eyebrow">Patient workspace</p><h1>CURE</h1><p role="status">{message}</p></header>
    <form onSubmit={saveProfile}><h2>Profile</h2><label>Date of birth<input type="date" value={profile.date_of_birth ?? ""} onChange={(e) => setProfile({ ...profile, date_of_birth: e.target.value || null })} /></label><label>Sex at birth (optional)<input value={profile.sex_at_birth ?? ""} onChange={(e) => setProfile({ ...profile, sex_at_birth: e.target.value || null })} /></label><label>Phone (optional)<input value={profile.phone_number ?? ""} onChange={(e) => setProfile({ ...profile, phone_number: e.target.value || null })} /></label><label className="inline"><input type="checkbox" checked={profile.no_reports_declared} onChange={(e) => setProfile({ ...profile, no_reports_declared: e.target.checked })} /> No reports available</label><button>Save profile</button></form>
    <ReportsPanel token={token} onMessage={setMessage} />
    <form onSubmit={submit}><h2>Symptom questionnaire</h2><p className="warning">Emergency signs are checked separately from any model. If one applies, seek emergency help immediately; do not wait for CURE or a clinician response.</p>
      {questions.map((question) => <fieldset key={question.id}><legend>{question.prompt}{question.required ? " *" : " (optional)"}</legend>
        {question.id === "symptoms" ? <div className="choices">{(question.options ?? []).map((option) => <label className="inline" key={option}><input type="checkbox" checked={selected.includes(option)} onChange={() => toggleSymptom(option)} /> {option.replaceAll("_", " ")}</label>)}</div>
          : question.multiple ? <div className="choices">{(question.options ?? []).map((option) => <label className="inline" key={option}><input type="checkbox" checked={Array.isArray(responses[question.id]) && (responses[question.id] as string[]).includes(option)} onChange={() => toggleAnswerOption(question.id, option)} /> {option.replaceAll("_", " ")}</label>)}</div>
          : question.options ? <div className="choices">{question.options.map((option) => <label className="inline" key={option}><input type="radio" name={question.id} required={question.required} checked={responses[question.id] === option} onChange={() => setAnswer(question.id, option)} /> {option.replaceAll("_", " ")}</label>)}</div>
          : <input aria-label={question.prompt} required={question.required} value={String(responses[question.id] ?? "")} onChange={(e) => setAnswer(question.id, e.target.value)} />}
      </fieldset>)}
      <button disabled={loading}>{loading ? "Submitting…" : "Submit screening"}</button>
    </form>
    {result && <section className={result.emergency_warning ? "result urgent" : "result"} aria-live="polite"><h2>{result.emergency_warning ? "Urgent warning" : "Screening recorded"}</h2><p>{result.message}</p>{result.emergency_reasons.length > 0 && <ul>{result.emergency_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}<p>No ML urgency prediction is available until a suitable dataset is evaluated. This screening is not a diagnosis.</p></section>}
    <section><h2>Screening history</h2><button type="button" onClick={() => void refreshHistory()}>Refresh history</button>{history.length ? <ol className="history">{history.map((item) => <li key={item.id}><strong>{new Date(item.created_at).toLocaleString()}</strong><span>{item.emergency_warning ? "Emergency warning flagged" : "No emergency warning flagged"}</span><span>ML prediction: {item.predicted_urgency ?? "Unavailable"}</span><span>Review: {item.review_status ?? "Pending"}</span><small>{item.missing_fields.length ? `Missing or unknown: ${item.missing_fields.join(", ")}` : "No required answers recorded as missing."}</small></li>)}</ol> : <p>No screenings recorded yet.</p>}</section>
  </section></main>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
