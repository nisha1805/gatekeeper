const test = require("node:test");
const assert = require("node:assert");
const L = require("./logic.js");

const Q = [
  { field: "eu_nexus", kind: "bool", group: "scope", text: "EU" },
  { field: "role", kind: "role", group: "scope", text: "Role" },
  { field: "social_scoring", kind: "bool", group: "prohibited", text: "Scoring" },
  { field: "annex3_areas", kind: "areas", group: "high_risk", text: "Areas" },
  { field: "performs_profiling", kind: "bool", group: "high_risk", text: "Profiling" },
];

const proposal = (field, value, applied, extra) => Object.assign(
  { field: field, kind: "bool", value: value, applied: applied, evidence: "q", confidence: "high",
    evidence_found: true, needs_confirmation: applied === null, reason: null }, extra);

test("defaults match the API defaults", () => {
  assert.deepStrictEqual(L.defaults(Q), { eu_nexus: true, role: "provider", social_scoring: false, annex3_areas: [], performs_profiling: false });
});

test("only applied proposals are pre-filled", () => {
  const extraction = { proposals: [proposal("annex3_areas", ["employment"], ["employment"]), proposal("social_scoring", true, null)], check_these: [] };
  const answers = L.initialAnswers(Q, extraction);
  assert.deepStrictEqual(answers.annex3_areas, ["employment"]);
  assert.strictEqual(answers.social_scoring, false);
});

test("without extraction the answers are the defaults", () => {
  assert.deepStrictEqual(L.initialAnswers(Q, null), L.defaults(Q));
});

test("questions are split into proposed, check and other without overlap", () => {
  const extraction = { proposals: [proposal("annex3_areas", ["employment"], ["employment"])],
    check_these: [{ field: "performs_profiling", reason: "r" }, { field: "annex3_areas", reason: "dup" }] };
  const s = L.splitQuestions(Q, extraction);
  assert.deepStrictEqual(s.proposed.map(x => x.question.field), ["annex3_areas"]);
  assert.deepStrictEqual(s.check.map(x => x.question.field), ["performs_profiling"]);
  assert.deepStrictEqual(s.other.map(x => x.field), ["eu_nexus", "role", "social_scoring"]);
});

test("unknown proposal fields are ignored", () => {
  const s = L.splitQuestions(Q, { proposals: [proposal("made_up", true, true)], check_these: [] });
  assert.strictEqual(s.proposed.length, 0);
  assert.strictEqual(s.other.length, Q.length);
});

test("payload has a trimmed name and a default name", () => {
  assert.strictEqual(L.buildPayload("  CV tool ", { eu_nexus: true }).name, "CV tool");
  assert.strictEqual(L.buildPayload("   ", {}).name, "Unnamed system");
});

test("payload carries exactly the answers and a name", () => {
  const answers = L.defaults(Q);
  assert.deepStrictEqual(Object.keys(L.buildPayload("x", answers)).sort(), ["name"].concat(Object.keys(answers)).sort());
});

test("groups keep the question order", () => {
  const g = L.groupQuestions(Q);
  assert.deepStrictEqual(g.map(x => x.title), ["Scope", "Prohibited practices", "High-risk"]);
});

test("tiers have labels and an unknown tier does not crash", () => {
  assert.strictEqual(L.tierInfo("high_risk").label, "High risk");
  assert.strictEqual(L.tierInfo("something_new").label, "something_new");
});

test("confidence text distinguishes the three cases", () => {
  assert.match(L.confidenceText(proposal("a", true, true)), /high confidence/);
  assert.match(L.confidenceText(proposal("a", true, null)), /needs your confirmation/);
  assert.match(L.confidenceText(proposal("a", true, null, { evidence_found: false })), /Quote not found/);
});

test("value text", () => {
  assert.strictEqual(L.valueText(Q[0], true, {}), "Yes");
  assert.strictEqual(L.valueText(Q[3], ["employment"], { employment: "Employment" }), "Employment");
  assert.strictEqual(L.valueText(Q[3], [], {}), "None");
});

// ---- audit page ----

const rec = (id, time, name, tier, reasons, review, extraction) => ({
  id, created_at: time, extraction_id: extraction || null, review: review || null,
  assessment: { system_name: name, tier, reasons: reasons.map(a => ({ article: a, text: "t" })), transparency_duties: [] },
});
const RECORDS = [
  rec("1", "2026-11-09T21:21:00+00:00", "CV tool", "high_risk", ["Art. 6(2), Annex III point 4"], null, "e1"),
  rec("2", "2026-11-10T08:05:00+00:00", "Scoring app", "prohibited", ["Art. 5(1)(c)"], { decision: "approved", reviewer: "A" }),
  rec("3", "2026-11-08T10:00:00+00:00", "Spam filter", "minimal_risk", ["Art. 5, 6, 50"], { decision: "rejected", reviewer: "B" }),
];

test("rows are newest first and carry review state", () => {
  const rows = L.toRows(RECORDS);
  assert.deepStrictEqual(rows.map(r => r.id), ["2", "1", "3"]);
  assert.strictEqual(rows[1].review, "pending");
  assert.strictEqual(rows[0].reviewer, "A");
  assert.strictEqual(rows[1].aiUsed, true);
  assert.strictEqual(rows[0].aiUsed, false);
});

test("filters by result, review and search", () => {
  const rows = L.toRows(RECORDS);
  assert.deepStrictEqual(L.filterRows(rows, { tier: "prohibited" }).map(r => r.id), ["2"]);
  assert.deepStrictEqual(L.filterRows(rows, { review: "pending" }).map(r => r.id), ["1"]);
  assert.deepStrictEqual(L.filterRows(rows, { search: "annex iii" }).map(r => r.id), ["1"]);
  assert.deepStrictEqual(L.filterRows(rows, { search: "SPAM" }).map(r => r.id), ["3"]);
  assert.strictEqual(L.filterRows(rows, { tier: "all", review: "all", search: "" }).length, 3);
});

test("stats count each review state", () => {
  assert.deepStrictEqual(L.stats(L.toRows(RECORDS)), { total: 3, pending: 1, approved: 1, rejected: 1 });
});

test("time is shown in UTC", () => {
  assert.strictEqual(L.formatTime("2026-11-09T21:21:00+00:00"), "9 Nov, 21:21");
  assert.strictEqual(L.formatTime("2026-11-09T21:21:00+01:00"), "9 Nov, 20:21");
  assert.strictEqual(L.formatTime("garbage"), "garbage");
});

test("cited articles are listed once", () => {
  assert.deepStrictEqual(L.citedArticles({ reasons: [{ article: "Art. 50(1)" }], transparency_duties: [{ article: "Art. 50(1)" }] }), ["Art. 50(1)"]);
});

test("csv cells are quoted and formulas are defused", () => {
  assert.strictEqual(L.csvCell('a "b", c'), '"a ""b"", c"');
  assert.strictEqual(L.csvCell("=HYPERLINK(1)"), "'=HYPERLINK(1)");
  assert.strictEqual(L.csvCell("+1"), "'+1");
  assert.strictEqual(L.csvCell("@x"), "'@x");
  assert.strictEqual(L.csvCell(null), "");
});

test("csv has a header and one line per row", () => {
  const lines = L.toCsv(L.toRows(RECORDS)).trim().split("\n");
  assert.strictEqual(lines.length, 4);
  assert.match(lines[0], /^time_utc,system,result/);
});

test("agreement text", () => {
  assert.match(L.agreementText({ ai_used: false }), /No AI proposals/);
  assert.match(L.agreementText({ ai_used: true, proposed: 3, accepted_unchanged: 2, changed: 1, added_by_person: ["x"] }),
    /proposed 3 answers: 2 kept unchanged, 1 changed\. The person added 1 more/);
});

test("notices tell what was masked and flag instruction-like text", () => {
  assert.deepStrictEqual(L.extractionNotices({ personal_data_masked: {}, instruction_like_text: false }), []);
  const n = L.extractionNotices({ personal_data_masked: { email: 2, phone: 1 }, instruction_like_text: true });
  assert.strictEqual(n.length, 2);
  assert.match(n[0], /3 personal data items \(2 e-mail addresses, 1 phone number\) masked/);
  assert.match(n[1], /looks like instructions/);
});

test("notices work for an old extraction without the new fields", () => {
  assert.deepStrictEqual(L.extractionNotices({}), []);
});

test("provision labels say what is added or missing", () => {
  assert.strictEqual(L.provisionStatus({ status: "added", text: "x" }), "Added by Regulation (EU) 2026/1744");
  assert.strictEqual(L.provisionStatus({ status: "not_included", text: null }), "Exact text not included");
  assert.strictEqual(L.provisionStatus({ status: "original", text: "x" }), "");
});

test("the source line names the date and the legal caveat", () => {
  const line = L.sourceLine({ retrieved: "2026-11-15", not_official: "Only the Official Journal is authentic." });
  assert.match(line, /2026-11-15/);
  assert.match(line, /EUR-Lex/);
  assert.match(line, /authentic/);
});
