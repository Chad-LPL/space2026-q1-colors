const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface GeocodeResult {
  address: string;
  lat: number;
  lng: number;
  state: string;
  district: number;
  districtLabel: string;
  stateName: string;
  label: string;
}

export interface DistrictInfo {
  state: string;
  district: number;
  districtLabel: string;
  stateName: string;
  label: string;
}

export interface Member {
  id: string;
  bioguideId?: string;
  name: string;
  firstName?: string;
  lastName?: string;
  party?: string;
  state?: string;
  district?: number;
  chamber?: string;
  phone?: string;
  url?: string;
  nextElection?: number;
  firstElected?: number;
  email?: string;
  contactFormUrl?: string;
}

export interface MembersResponse {
  districtInfo: DistrictInfo;
  representative: Member | null;
  senators: Member[];
  /** Set when API key is configured but Congress API returned no members */
  membersError?: string;
}

export interface ContactStats {
  memberId: string;
  issueId?: string | null;
  topic?: string | null;
  last7Days: number;
  last30Days: number;
}

export interface ScriptItem {
  id: number;
  title: string;
  billId?: string | null;
  issueSlug?: string | null;
}

export interface ScriptDetail {
  id: number;
  title: string;
  body: string;
  subject?: string | null;
  billId?: string | null;
  issueSlug?: string | null;
}

export interface ScriptGenerateResponse {
  emailBody: string;
  callScript: string;
  subject?: string;
  message?: string;
}

const GEOCODE_CACHE_MAX = 50;
const GEOCODE_CACHE_TTL_MS = 30 * 60 * 1000;
const geocodeCache = new Map<string, { expires: number; data: GeocodeResult | { error: string; address: string } }>();

function geocodeCacheKey(address: string): string {
  return address.trim().toLowerCase();
}

const API_ERROR_BACKEND_UNREACHABLE =
  "Could not reach the server. Is the backend running on port 8001?";

export async function geocode(address: string): Promise<GeocodeResult | { error: string; address: string }> {
  const key = geocodeCacheKey(address);
  const now = Date.now();
  const cached = geocodeCache.get(key);
  if (cached && cached.expires > now) return cached.data;
  let result: GeocodeResult | { error: string; address: string };
  try {
    const r = await fetch(`${BASE}/geocode?${new URLSearchParams({ address })}`);
    const data = await r.json();
    result = !r.ok
      ? { error: data?.error === "Address not found" ? data.error : API_ERROR_BACKEND_UNREACHABLE, address }
      : data.error
        ? data
        : (data as GeocodeResult);
  } catch {
    result = { error: API_ERROR_BACKEND_UNREACHABLE, address };
  }
  if (geocodeCache.size >= GEOCODE_CACHE_MAX) {
    const firstKey = geocodeCache.keys().next().value;
    if (firstKey != null) geocodeCache.delete(firstKey);
  }
  geocodeCache.set(key, { expires: now + GEOCODE_CACHE_TTL_MS, data: result });
  return result;
}

export interface GeocodeSuggestion {
  address: string;
}

export async function geocodeSuggest(
  query: string,
  limit = 5
): Promise<{ suggestions: GeocodeSuggestion[] }> {
  const r = await fetch(
    `${BASE}/geocode/suggest?${new URLSearchParams({ address: query, limit: String(limit) })}`
  );
  if (!r.ok) return { suggestions: [] };
  return r.json();
}

const API_ERROR_CONGRESS_KEY =
  "Congress API is not configured. Add CONGRESS_API_KEY to backend/.env.";

export async function getMembers(state: string, district: number): Promise<MembersResponse | { error: string }> {
  try {
    const r = await fetch(`${BASE}/members?${new URLSearchParams({ state, district: String(district) })}`);
    const data = await r.json();
    if (!r.ok) return { error: API_ERROR_BACKEND_UNREACHABLE };
    if (data.error) {
      const msg =
        typeof data.error === "string" && data.error.toLowerCase().includes("congress_api_key")
          ? API_ERROR_CONGRESS_KEY
          : data.error;
      return { error: msg };
    }
    return data as MembersResponse;
  } catch {
    return { error: API_ERROR_BACKEND_UNREACHABLE };
  }
}

export async function getMember(id: string): Promise<Member | { error: string }> {
  const r = await fetch(`${BASE}/members/${encodeURIComponent(id)}`);
  const data = await r.json();
  if (!r.ok) return { error: "Failed to load member" };
  if (data.error) return { error: data.error };
  return data as Member;
}

export interface MemberBill {
  number?: string;
  title?: string;
  url?: string;
  introducedDate?: string;
  status?: string | null;
}

export async function getMemberBills(id: string, limit = 20): Promise<{ bills: MemberBill[] }> {
  const r = await fetch(`${BASE}/members/${encodeURIComponent(id)}/bills?limit=${limit}`);
  if (!r.ok) return { bills: [] };
  const data = await r.json();
  return { bills: data.bills || [] };
}

export async function getMemberVotes(id: string, limit = 20): Promise<{ votes: Array<{ position?: string; description?: string; date?: string; url?: string }> }> {
  const r = await fetch(`${BASE}/members/${encodeURIComponent(id)}/votes?limit=${limit}`);
  if (!r.ok) return { votes: [] };
  const data = await r.json();
  return { votes: data.votes || [] };
}

export async function getScripts(): Promise<{ scripts: ScriptItem[] }> {
  const r = await fetch(`${BASE}/scripts`);
  if (!r.ok) return { scripts: [] };
  const data = await r.json();
  return { scripts: data.scripts || [] };
}

export async function getScript(id: number): Promise<ScriptDetail | null> {
  const r = await fetch(`${BASE}/scripts/${id}`);
  if (!r.ok) return null;
  const data = await r.json();
  if (data.error) return null;
  return data as ScriptDetail;
}

export async function generateScript(params: {
  memberId: string;
  issueOrBillId?: string | null;
  issueText?: string | null;
  issueTitle?: string | null;
  scriptId?: number | null;
  format?: string | null;
}): Promise<ScriptGenerateResponse> {
  const r = await fetch(`${BASE}/scripts/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!r.ok) throw new Error("Failed to generate script");
  return r.json();
}

export async function recordContactEvent(params: {
  memberId: string;
  issueId?: string | null;
  topic?: string | null;
  contactType: "email" | "call";
}): Promise<void> {
  await fetch(`${BASE}/contact-events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function getContactStats(
  memberId: string,
  issueId?: string | null,
  topic?: string | null
): Promise<ContactStats | null> {
  const params: Record<string, string> = { memberId };
  if (issueId) params.issueId = issueId;
  if (topic) params.topic = topic;
  const r = await fetch(`${BASE}/contact-stats?${new URLSearchParams(params)}`);
  if (!r.ok) return null;
  return r.json();
}
