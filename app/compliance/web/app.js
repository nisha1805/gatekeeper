// The Compliance copilot page. All text from the server or the user is set with
// textContent, never as HTML, so a description cannot inject markup.
(function () {
  "use strict";

  var SAMPLES = [
    { label: "CV screening", name: "CV screening tool",
      text: "We use an AI tool that reads incoming CVs and ranks candidates for our recruiters. It is used on job applications from people in the EU. We bought it from a vendor." },
    { label: "Support chatbot", name: "Support chatbot",
      text: "Our website has a chatbot that answers customer questions about orders. Customers in Germany and France talk to it directly. We built it ourselves." },
    { label: "Spam filter", name: "Spam filter",
      text: "A spam filter that sorts incoming company email into inbox and junk. It only looks at the email text and is used by our staff in the EU." },
  ];

  var state = { questions: [], areaLabels: {}, extraction: null, answers: {}, assessment: null };

  function $(id) { return document.getElementById(id); }

  function el(tag, props, children) {
    var node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (key) {
      if (key === "text") node.textContent = props[key];
      else if (key === "class") node.className = props[key];
      else node.setAttribute(key, props[key]);
    });
    (children || []).forEach(function (child) { if (child) node.appendChild(child); });
    return node;
  }

  function setStatus(id, message, isError) {
    var node = $(id);
    node.textContent = message || "";
    node.className = "status" + (isError ? " error" : "");
  }

  function request(method, url, body) {
    var options = { method: method, headers: {} };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(url, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          var detail = data && data.detail;
          if (Array.isArray(detail)) detail = detail.map(function (d) { return d.msg; }).join("; ");
          var error = new Error(detail || ("The server answered " + response.status));
          error.status = response.status;
          throw error;
        }
        return data;
      });
    });
  }

  // ---- controls -------------------------------------------------------------

  function renderControl(slot, question) {
    slot.textContent = "";
    var field = question.field;
    if (question.kind === "bool") {
      var box = el("input", { type: "checkbox", "aria-label": question.text });
      box.checked = !!state.answers[field];
      var word = el("span", { text: box.checked ? "Yes" : "No" });
      box.addEventListener("change", function () { state.answers[field] = box.checked; word.textContent = box.checked ? "Yes" : "No"; });
      slot.appendChild(el("label", { class: "switch" }, [box, word]));
    } else if (question.kind === "role") {
      var select = el("select", { "aria-label": question.text });
      ["provider", "deployer"].forEach(function (value) {
        var option = el("option", { value: value, text: value === "provider" ? "Provider (builds or sells it)" : "Deployer (uses it)" });
        if (state.answers[field] === value) option.selected = true;
        select.appendChild(option);
      });
      select.addEventListener("change", function () { state.answers[field] = select.value; });
      slot.appendChild(select);
    } else if (question.kind === "areas") {
      var wrap = el("div", { class: "areas" });
      Object.keys(state.areaLabels).forEach(function (value) {
        var check = el("input", { type: "checkbox", value: value });
        check.checked = state.answers[field].indexOf(value) !== -1;
        check.addEventListener("change", function () {
          var set = state.answers[field].filter(function (v) { return v !== value; });
          if (check.checked) set.push(value);
          state.answers[field] = set;
        });
        wrap.appendChild(el("label", {}, [check, document.createTextNode(" " + state.areaLabels[value])]));
      });
      slot.appendChild(wrap);
    }
  }

  function questionRow(question, extras) {
    var slot = el("div", { class: "control" });
    renderControl(slot, question);
    var left = el("div", {}, [el("div", { class: "card-title", text: question.text })].concat(extras || []));
    return { node: el("div", { class: "row" }, [left, slot]), slot: slot };
  }

  function proposalCard(item) {
    var q = item.question, p = item.proposal;
    var applied = p.applied !== null && p.applied !== undefined;
    var extras = [el("span", { class: "tag" + (applied ? "" : " warn"), text: Logic.confidenceText(p) })];
    if (p.evidence) extras.push(el("div", { class: "quote", text: "From: “" + p.evidence + "”" }));
    if (p.reason) extras.push(el("div", { class: "quote", text: p.reason }));
    var row = questionRow(q, extras);
    var card = el("div", { class: "card" + (applied ? "" : " pending") }, [row.node]);
    if (!applied) {
      var proposedText = "AI proposed: " + Logic.valueText(q, p.value, state.areaLabels);
      var button = el("button", { type: "button", class: "btn btn-small", text: "Use the AI's answer (" + proposedText.slice(13) + ")" });
      button.addEventListener("click", function () {
        state.answers[q.field] = p.value;
        renderControl(row.slot, q);
        card.classList.remove("pending");
        button.remove();
      });
      card.appendChild(button);
    }
    return card;
  }

  function checkCard(item) {
    var row = questionRow(item.question, [el("span", { class: "tag warn", text: "Not clear from the description: please check" }),
      el("div", { class: "quote", text: item.reason })]);
    return el("div", { class: "card pending" }, [row.node]);
  }

  function renderAnswers() {
    var split = Logic.splitQuestions(state.questions, state.extraction);
    var proposed = $("proposed"), check = $("check"), other = $("other");
    proposed.textContent = ""; check.textContent = ""; other.textContent = "";
    if (split.proposed.length) proposed.appendChild(el("h3", { class: "group-title", text: "AI-proposed answers" }));
    split.proposed.forEach(function (item) { proposed.appendChild(proposalCard(item)); });
    if (split.check.length) check.appendChild(el("h3", { class: "group-title", text: "Please check these" }));
    split.check.forEach(function (item) { check.appendChild(checkCard(item)); });
    Logic.groupQuestions(split.other).forEach(function (group) {
      other.appendChild(el("h3", { class: "group-title", text: group.title }));
      group.questions.forEach(function (q) {
        other.appendChild(el("div", { class: "card" }, [questionRow(q).node]));
      });
    });
    $("other-wrap").open = !split.proposed.length;
    $("answers").hidden = false;
  }

  // ---- steps ----------------------------------------------------------------

  function renderNotices(notices) {
    var list = $("read-notes");
    list.textContent = "";
    notices.forEach(function (text) { list.appendChild(el("li", { text: text })); });
  }

  function readDescription() {
    var description = $("description").value.trim();
    if (description.length < 20) { setStatus("read-status", "Please write at least 20 characters.", true); return; }
    var button = $("read");
    button.disabled = true;
    setStatus("read-status", "Reading the description…");
    request("POST", "/extractions", { description: description }).then(function (extraction) {
      state.extraction = extraction;
      state.answers = Logic.initialAnswers(state.questions, extraction);
      var n = extraction.proposals.length;
      setStatus("read-status", n ? n + " answer" + (n === 1 ? "" : "s") + " proposed. Please confirm them below." : "The AI found nothing it could quote. Please answer by hand.");
      renderNotices(Logic.extractionNotices(extraction));
      renderAnswers();
    }).catch(function (error) {
      renderNotices([]);
      state.extraction = null;
      state.answers = Logic.defaults(state.questions);
      var message = error.status === 503 ? "The AI step is not configured on this server. You can still answer by hand." : "The AI step failed: " + error.message.replace(/\.$/, "") + ". You can still answer by hand.";
      setStatus("read-status", message, true);
      renderAnswers();
    }).then(function () { button.disabled = false; });
  }

  function classify() {
    var button = $("classify");
    button.disabled = true;
    setStatus("classify-status", "Applying the written rules…");
    var url = "/assessments" + (state.extraction && state.extraction.extraction_id ? "?extraction_id=" + encodeURIComponent(state.extraction.extraction_id) : "");
    var created;
    request("POST", url, Logic.buildPayload($("name").value, state.answers)).then(function (record) {
      created = record;
      return request("POST", "/assessments/" + record.id + "/explanation").catch(function () { return null; });
    }).then(function (explanation) {
      setStatus("classify-status", "");
      renderResult(created, explanation);
    }).catch(function (error) {
      setStatus("classify-status", "Could not classify: " + error.message, true);
    }).then(function () { button.disabled = false; });
  }

  function renderResult(record, explanation) {
    var a = record.assessment, tier = Logic.tierInfo(a.tier);
    var body = $("result-body");
    body.textContent = "";
    body.appendChild(el("div", { class: "res-head" }, [
      el("span", { class: "tier " + tier.css, text: tier.label }),
      el("span", { class: "hint", text: "Answers confirmed by a person" }),
    ]));

    body.appendChild(el("h2", { text: "Why" }));
    if (explanation) {
      body.appendChild(el("p", { class: "explain" + (explanation.source === "template" ? " template" : ""), text: explanation.text }));
      body.appendChild(el("p", { class: "source-note", text: explanation.source === "ai"
        ? "Explanation written by the AI from the cited articles only. The code checked that it names no other article."
        : "Fixed explanation built from the rules' own text. The AI text was not used (" + explanation.fallback_reason + ")." }));
    } else {
      body.appendChild(el("p", { class: "source-note", text: "The explanation could not be loaded. The cited articles below are the result." }));
    }

    var cited = a.reasons.concat(a.transparency_duties.filter(function (d) {
      return !a.reasons.some(function (r) { return r.article === d.article && r.text === d.text; });
    }));
    body.appendChild(el("h2", { text: "Cited articles" }));
    cited.forEach(function (item) {
      body.appendChild(el("div", { class: "cite" }, [el("b", { text: item.article }), document.createTextNode(item.text)]));
    });

    if (a.notes.length) {
      body.appendChild(el("h2", { text: "Notes" }));
      body.appendChild(el("ul", { class: "notes" }, a.notes.map(function (n) { return el("li", { text: n }); })));
    }

    var reviewer = el("input", { type: "text", id: "reviewer", maxlength: "100", "aria-label": "Your name" });
    var comment = el("input", { type: "text", id: "comment", maxlength: "1000", "aria-label": "Comment (optional)" });
    var approve = el("button", { type: "button", class: "btn btn-ok", text: "Approve" });
    var reject = el("button", { type: "button", class: "btn btn-bad", text: "Reject" });
    var status = el("p", { class: "status", role: "status" });
    function decide(decision) {
      if (!reviewer.value.trim()) { status.textContent = "Please type your name first."; status.className = "status error"; return; }
      approve.disabled = reject.disabled = true;
      request("POST", "/assessments/" + record.id + "/reviews", {
        decision: decision, reviewer: reviewer.value.trim(), comment: comment.value.trim() || null,
      }).then(function () {
        status.className = "status";
        status.textContent = "Recorded: " + decision + " by " + reviewer.value.trim() + ". The audit log keeps every decision.";
      }).catch(function (error) {
        status.className = "status error"; status.textContent = "Could not save the review: " + error.message;
      }).then(function () { approve.disabled = reject.disabled = false; });
    }
    approve.addEventListener("click", function () { decide("approved"); });
    reject.addEventListener("click", function () { decide("rejected"); });
    body.appendChild(el("div", { class: "review" }, [
      el("h2", { text: "Human review: does this classification look right?" }),
      el("label", { class: "field-label", for: "reviewer", text: "Your name (typed, not verified: this prototype has no login)" }), reviewer,
      el("label", { class: "field-label", for: "comment", text: "Comment (optional)" }), comment,
      el("div", { class: "actions" }, [approve, reject]), status,
    ]));
    body.appendChild(el("p", { class: "disclaimer", text: a.disclaimer + " Rules version " + a.rules_version + "." }));

    $("empty").hidden = true;
    body.hidden = false;
    body.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---- start ----------------------------------------------------------------

  function init() {
    var chips = $("samples");
    SAMPLES.forEach(function (sample) {
      var chip = el("button", { type: "button", class: "chip", "aria-pressed": "false", text: sample.label });
      chip.addEventListener("click", function () {
        Array.prototype.forEach.call(chips.children, function (c) { c.setAttribute("aria-pressed", "false"); });
        chip.setAttribute("aria-pressed", "true");
        $("name").value = sample.name;
        $("description").value = sample.text;
      });
      chips.appendChild(chip);
    });
    $("read").addEventListener("click", readDescription);
    $("classify").addEventListener("click", classify);
    request("GET", "/questions").then(function (data) {
      state.questions = data.questions;
      data.annex3_areas.forEach(function (a) { state.areaLabels[a.value] = a.label; });
      state.answers = Logic.defaults(state.questions);
    }).catch(function (error) {
      setStatus("read-status", "Could not load the questions: " + error.message, true);
    });
  }
  init();
})();
