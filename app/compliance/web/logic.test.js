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
