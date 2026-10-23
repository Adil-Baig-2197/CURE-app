import { ChangeEvent, useEffect, useState } from "react";
import { request } from "./api";

type Report = { id: string; original_filename: string; status: string; raw_extraction: { limitations?: string[] } | null; verified_information: object | null };
export function ReportsPanel({ token, onMessage }: { token: string; onMessage: (message: string) => void }) {
  const [reports, setReports] = useState<Report[]>([]);
  const load = async () => setReports(await request<Report[]>("/reports", {}, token));
  useEffect(() => { void load().catch((e) => onMessage(e.message)); }, []);
  async function upload(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; if (!file) return; try { await request<Report>("/reports", { method: "POST", body: (() => { const data = new FormData(); data.append("upload", file); return data; })() }, token); await load(); onMessage("Report uploaded. Review extraction before confirming it."); } catch (e) { onMessage(e instanceof Error ? e.message : "Upload failed"); } }
  async function verify(id: string) { try { await request(`/reports/${id}/verification`, { method: "PUT", body: JSON.stringify({ verified_information: { patient_note: "Reviewed by patient", diagnoses: [], medications: [], laboratory_results: [] } }) }, token); await load(); } catch (e) { onMessage(e instanceof Error ? e.message : "Verification failed"); } }
  return <section><h2>Medical reports</h2><label>Upload PDF, JPG, or PNG<input type="file" accept="application/pdf,image/jpeg,image/png" onChange={upload} /></label><ul>{reports.map((report) => <li key={report.id}>{report.original_filename} — {report.status} {report.status !== "verified" && <button onClick={() => void verify(report.id)}>Confirm reviewed</button>} {report.raw_extraction?.limitations?.join(" ")}</li>)}</ul></section>;
}
