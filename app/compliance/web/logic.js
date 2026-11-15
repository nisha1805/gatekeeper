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

  // ---- audit page ----------------------------------------------------------

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  // "9 Nov, 21:21" in UTC, so the table reads the same on every computer.
  function formatTime(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return d.getUTCDate() + " " + MONTHS[d.getUTCMonth()] + ", " + pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes());
  }

  function citedArticles(assessment) {
    var seen = {}, list = [];
    assessment.reasons.concat(assessment.transparency_duties).forEach(function (item) {
      if (!seen[item.article]) { seen[item.article] = true; list.push(item.article); }
    });
    return list;
  }

  // Newest first. "pending" means no review decision yet.
  function toRows(records) {
    return records.map(function (r) {
      return {
        id: r.id, time: r.created_at, name: r.assessment.system_name, tier: r.assessment.tier,
        cited: citedArticles(r.assessment),
        review: r.review ? r.review.decision : "pending",
        reviewer: r.review ? r.review.reviewer : "",
        aiUsed: !!r.extraction_id, record: r,
      };
    }).sort(function (a, b) { return a.time < b.time ? 1 : a.time > b.time ? -1 : 0; });
  }

  function filterRows(rows, filters) {
    var needle = (filters.search || "").trim().toLowerCase();
    return rows.filter(function (row) {
      if (filters.tier && filters.tier !== "all" && row.tier !== filters.tier) return false;
      if (filters.review && filters.review !== "all" && row.review !== filters.review) return false;
      if (needle && (row.name + " " + row.cited.join(" ")).toLowerCase().indexOf(needle) === -1) return false;
      return true;
    });
  }

  function stats(rows) {
    var out = { total: rows.length, pending: 0, approved: 0, rejected: 0 };
    rows.forEach(function (row) { out[row.review] += 1; });
    return out;
  }

  // A cell that starts with = + - or @ would be run as a formula by a spreadsheet.
  function csvCell(value) {
    var text = value === null || value === undefined ? "" : String(value);
    if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
    if (/[",\n\r]/.test(text)) text = '"' + text.replace(/"/g, '""') + '"';
    return text;
  }

  function toCsv(rows) {
    var lines = [["time_utc", "system", "result", "cited", "review", "reviewer", "ai_used", "id"].join(",")];
    rows.forEach(function (row) {
      lines.push([row.time, row.name, row.tier, row.cited.join("; "), row.review, row.reviewer,
        row.aiUsed ? "yes" : "no", row.id].map(csvCell).join(","));
    });
    return lines.join("\n") + "\n";
  }

  function agreementText(result) {
    if (!result || !result.ai_used) return "No AI proposals were used for this assessment.";
    var text = "The AI proposed " + result.proposed + " answer" + (result.proposed === 1 ? "" : "s") + ": " +
      result.accepted_unchanged + " kept unchanged, " + result.changed + " changed.";
    if (result.added_by_person.length) text += " The person added " + result.added_by_person.length + " more.";
    return text;
  }

  var KIND_NAMES = { email: ["e-mail address", "e-mail addresses"], iban: ["IBAN", "IBANs"], card: ["card number", "card numbers"], phone: ["phone number", "phone numbers"] };

  // Notices to show after the AI has read a description.
  function extractionNotices(extraction) {
    var notices = [];
    var counts = extraction.personal_data_masked || {}, parts = [], total = 0;
    Object.keys(counts).forEach(function (kind) {
      total += counts[kind];
      var names = KIND_NAMES[kind] || [kind, kind];
      parts.push(counts[kind] + " " + names[counts[kind] === 1 ? 0 : 1]);
    });
    if (total) {
      notices.push(total + " personal data item" + (total === 1 ? "" : "s") + " (" + parts.join(", ") +
        ") masked before the AI read the text. Names and addresses are not detected, so please do not enter them.");
    }
    if (extraction.instruction_like_text) {
      notices.push("The description contains text that looks like instructions to the AI. It was treated as data, and every proposal needs your confirmation.");
    }
    return notices;
  }

  // The small label next to a provision in the Sources section.
  function provisionStatus(provision) {
    if (provision.status === "added") return "Added by Regulation (EU) 2026/1744";
    if (provision.status === "not_included") return provision.text ? "" : "Exact text not included";
    return "";
  }

  function sourceLine(meta) {
    return "Copied on " + meta.retrieved + " from Regulation (EU) 2024/1689 and its amendment, Regulation (EU) 2026/1744, on EUR-Lex. " +
      meta.not_official;
  }

  var api = { defaults: defaults, initialAnswers: initialAnswers, splitQuestions: splitQuestions,
    groupQuestions: groupQuestions, buildPayload: buildPayload, tierInfo: tierInfo,
    confidenceText: confidenceText, valueText: valueText, extractionNotices: extractionNotices,
    provisionStatus: provisionStatus, sourceLine: sourceLine,
    formatTime: formatTime, citedArticles: citedArticles, toRows: toRows, filterRows: filterRows,
    stats: stats, csvCell: csvCell, toCsv: toCsv, agreementText: agreementText };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Logic = api;
})(this);
