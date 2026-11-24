// The Audit trail page. Server text is always set with textContent, never as HTML.
(function () {
  "use strict";

  var state = { rows: [], agreement: null };

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

  function get(url) {
    return fetch(url).then(function (response) {
      if (!response.ok) throw new Error("The server answered " + response.status);
      return response.json();
    });
  }

  function tile(label, value, note) {
    return el("div", { class: "tile" }, [
      el("div", { class: "tile-label", text: label }),
      el("div", { class: "tile-value", text: String(value) }),
      note ? el("div", { class: "tile-note", text: note }) : null,
    ]);
  }

  function renderTiles(rows) {
    var s = Logic.stats(rows), tiles = $("tiles"), a = state.agreement;
    tiles.textContent = "";
    tiles.appendChild(tile("Assessments", s.total));
    tiles.appendChild(tile("Awaiting review", s.pending));
    tiles.appendChild(tile("Approved", s.approved));
    tiles.appendChild(tile("Rejected", s.rejected));
    var rate = a && a.accepted_rate !== null && a.accepted_rate !== undefined ? Math.round(a.accepted_rate * 100) + "%" : "—";
    var note = a && a.proposed ? a.accepted_unchanged + " of " + a.proposed + " AI answers, from " + a.assessments_with_ai + (a.assessments_with_ai === 1 ? " assessment" : " assessments") : "No assessment used AI proposals yet";
    tiles.appendChild(tile("AI answers kept unchanged", rate, note));
  }

  function badge(text, css) { return el("span", { class: "pill " + css, text: text }); }

  function reviewBadge(review) {
    if (review === "approved") return badge("Approved", "pill-ok");
    if (review === "rejected") return badge("Rejected", "pill-bad");
    return badge("Pending", "pill-warn");
  }

  function detailRow(row) {
    var box = el("div", { class: "detail" });
    row.record.assessment.reasons.concat(row.record.assessment.transparency_duties.filter(function (d) {
      return !row.record.assessment.reasons.some(function (r) { return r.article === d.article && r.text === d.text; });
    })).forEach(function (item) {
      box.appendChild(el("div", { class: "cite" }, [el("b", { text: item.article }), document.createTextNode(item.text)]));
    });
    var line = el("p", { class: "status", text: "Loading AI details…" });
    box.appendChild(line);
    box.appendChild(el("p", { class: "status", text: "Assessment id: " + row.id }));
    if (row.aiUsed) {
      get("/assessments/" + encodeURIComponent(row.id) + "/ai-agreement").then(function (result) {
        line.textContent = Logic.agreementText(result);
      }).catch(function () { line.textContent = "AI details could not be loaded."; });
    } else {
      line.textContent = Logic.agreementText({ ai_used: false });
    }
    return el("tr", { class: "detail-row" }, [el("td", { colspan: "8" }, [box])]);
  }

  function renderRows() {
    var filters = { tier: $("f-tier").value, review: $("f-review").value, search: $("f-search").value };
    var rows = Logic.filterRows(state.rows, filters), body = $("rows");
    body.textContent = "";
    renderTiles(state.rows);
    setStatus(rows.length ? "" : (state.rows.length ? "No assessment matches the filters." : "No assessments yet. Classify a system on the copilot page first."));
    rows.forEach(function (row) {
      var tier = Logic.tierInfo(row.tier);
      var open = el("button", { type: "button", class: "link", "aria-expanded": "false", text: "Open" });
      var tr = el("tr", {}, [
        el("td", { text: Logic.formatTime(row.time) }),
        el("td", { class: "strong", text: row.name }),
        el("td", {}, [el("span", { class: "pill " + tier.css, text: tier.label })]),
        el("td", { text: row.cited.join(", ") }),
        el("td", {}, [reviewBadge(row.review)]),
        el("td", { text: row.reviewer || "—" }),
        el("td", { text: row.aiUsed ? "Yes" : "No" }),
        el("td", {}, [open]),
      ]);
      var detail = null;
      open.addEventListener("click", function () {
        if (detail) { detail.remove(); detail = null; open.textContent = "Open"; open.setAttribute("aria-expanded", "false"); return; }
        detail = detailRow(row);
        tr.after(detail);
        open.textContent = "Close";
        open.setAttribute("aria-expanded", "true");
      });
      body.appendChild(tr);
    });
  }

  function setStatus(message, isError) {
    var node = $("audit-status");
    node.textContent = message || "";
    node.className = "status" + (isError ? " error" : "");
  }

  function download(name, type, text) {
    var url = URL.createObjectURL(new Blob([text], { type: type }));
    var link = el("a", { href: url, download: name });
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function filteredRows() {
    return Logic.filterRows(state.rows, { tier: $("f-tier").value, review: $("f-review").value, search: $("f-search").value });
  }

  function init() {
    fetch("/config").then(function (r) { return r.ok ? r.json() : { demo: false }; }).then(function (c) {
      if (c.demo) { var b = document.getElementById("demo-banner"); b.textContent = Logic.demoNotice; b.hidden = false; }
    }).catch(function () {});
    ["f-tier", "f-review"].forEach(function (id) { $(id).addEventListener("change", renderRows); });
    $("f-search").addEventListener("input", renderRows);
    $("export-json").addEventListener("click", function () {
      download("gatekeeper-audit.json", "application/json", JSON.stringify(filteredRows().map(function (r) { return r.record; }), null, 2));
    });
    $("export-csv").addEventListener("click", function () {
      download("gatekeeper-audit.csv", "text/csv", Logic.toCsv(filteredRows()));
    });
    setStatus("Loading…");
    Promise.all([get("/assessments"), get("/ai-agreement").catch(function () { return null; })]).then(function (results) {
      state.rows = Logic.toRows(results[0]);
      state.agreement = results[1];
      renderRows();
    }).catch(function (error) {
      setStatus("Could not load the audit trail: " + error.message, true);
    });
  }
  init();
})();
