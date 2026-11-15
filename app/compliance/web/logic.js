// Pure logic for the Compliance copilot page. No DOM here, so it can be tested with Node.
(function (root) {
  "use strict";

  var GROUP_TITLES = {
    scope: "Scope",
    prohibited: "Prohibited practices",
    high_risk: "High-risk",
    transparency: "Transparency duties",
  };

  function defaultFor(question) {
    if (question.field === "eu_nexus") return true;
    if (question.kind === "role") return "provider";
    if (question.kind === "areas") return [];
    return false;
  }

  function defaults(questions) {
    var answers = {};
    questions.forEach(function (q) { answers[q.field] = defaultFor(q); });
    return answers;
  }

  // Start from the defaults and add only the proposals the code allowed to pre-fill.
  function initialAnswers(questions, extraction) {
    var answers = defaults(questions);
    if (extraction) {
      extraction.proposals.forEach(function (p) {
        if (p.applied !== null && p.applied !== undefined) answers[p.field] = p.applied;
      });
    }
    return answers;
  }

  // Which questions are shown as AI proposals, which as "please check", which as the rest.
  function splitQuestions(questions, extraction) {
    var byField = {};
    questions.forEach(function (q) { byField[q.field] = q; });
    var proposed = [], check = [], used = {};
    if (extraction) {
      extraction.proposals.forEach(function (p) {
        if (byField[p.field]) { proposed.push({ question: byField[p.field], proposal: p }); used[p.field] = true; }
      });
      extraction.check_these.forEach(function (c) {
        if (byField[c.field] && !used[c.field]) { check.push({ question: byField[c.field], reason: c.reason }); used[c.field] = true; }
      });
    }
    var other = questions.filter(function (q) { return !used[q.field]; });
    return { proposed: proposed, check: check, other: other };
  }

  function groupQuestions(questions) {
    var groups = [], index = {};
    questions.forEach(function (q) {
      if (!(q.group in index)) { index[q.group] = groups.length; groups.push({ title: GROUP_TITLES[q.group] || q.group, questions: [] }); }
      groups[index[q.group]].questions.push(q);
    });
    return groups;
  }

  function buildPayload(name, answers) {
    var payload = { name: (name || "").trim() || "Unnamed system" };
    Object.keys(answers).forEach(function (field) { payload[field] = answers[field]; });
    return payload;
  }

  var TIERS = {
    out_of_scope: { label: "Out of scope", css: "tier-none" },
    prohibited: { label: "Prohibited", css: "tier-bad" },
    high_risk: { label: "High risk", css: "tier-high" },
    limited_risk: { label: "Limited risk", css: "tier-limited" },
    minimal_risk: { label: "Minimal risk", css: "tier-minimal" },
  };

  function tierInfo(tier) { return TIERS[tier] || { label: tier, css: "tier-none" }; }

  function confidenceText(p) {
    if (!p.evidence_found) return "Quote not found: please check";
    if (p.needs_confirmation) return "AI proposed, needs your confirmation";
    return "AI proposed, " + p.confidence + " confidence";
  }

  function valueText(question, value, areaLabels) {
    if (question.kind === "bool") return value ? "Yes" : "No";
    if (question.kind === "areas") {
      return value.length ? value.map(function (v) { return areaLabels[v] || v; }).join(", ") : "None";
    }
    return String(value);
  }

  var api = { defaults: defaults, initialAnswers: initialAnswers, splitQuestions: splitQuestions,
    groupQuestions: groupQuestions, buildPayload: buildPayload, tierInfo: tierInfo,
    confidenceText: confidenceText, valueText: valueText };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Logic = api;
})(this);
