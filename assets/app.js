/* KeralaKuri — small, dependency-free. Works without it too (results are plain HTML). */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var BASE = document.documentElement.getAttribute("data-base") || "/";
  var WEEK = [["BT", "Bhagyathara"], ["SS", "Sthree Sakthi"], ["DL", "Dhanalekshmi"], ["KN", "Karunya Plus"], ["SK", "Suvarna Keralam"], ["KR", "Karunya"], ["SM", "Samrudhi"]];
  var KEY = "kk_tickets";

  function rupees(n) {
    if (n >= 10000000) return "₹" + (n / 10000000).toString().replace(/\.0+$/, "") + " Crore";
    if (n >= 100000) return "₹" + (n / 100000).toString().replace(/\.0+$/, "") + " Lakh";
    return "₹" + n.toLocaleString("en-IN");
  }
  function norm(v) { return String(v || "").toUpperCase().replace(/[^A-Z0-9]/g, ""); }
  function ordinal(t) { return t === "consolation" ? "Consolation prize" : t + ({ 1: "st", 2: "nd", 3: "rd" }[t] || "th") + " prize"; }
  function istNow() { var d = new Date(); return new Date(d.getTime() + (d.getTimezoneOffset() + 330) * 60000); }
  function ymd(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
  function store(v) { try { if (v === undefined) return JSON.parse(localStorage.getItem(KEY) || "[]"); localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) { return []; } }

  /* Best prize for one ticket in one draw. Kerala pays only the highest prize per ticket. */
  function check(ticket, draw) {
    var m = norm(ticket).match(/^([A-Z]{2})(\d{6})$/);
    if (!m) return { error: true };
    var best = null, first = null, cons = null;
    draw.tiers.forEach(function (t) {
      if (t.tier === "1" && t.tickets[0]) first = t;
      if (t.tier === "consolation") cons = t;
      var hit = false;
      t.tickets.forEach(function (k) { if (k.series === m[1] && k.number === m[2]) hit = true; });
      if (t.endings && t.endings.indexOf(m[2].slice(2)) > -1) hit = true;
      if (hit && (!best || t.amount > best.amount)) best = t;
    });
    if (!best && first && cons && first.tickets[0].number === m[2]) best = cons;
    return { ticket: m[1] + " " + m[2], tier: best, ending: m[2].slice(2) };
  }

  /* ---------- checker on result pages ---------- */
  var dataEl = $("#kk-draw");
  var draw = dataEl ? JSON.parse(dataEl.textContent) : null;
  var form = $("#check-form");
  if (form && draw) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var out = $("#check-out"), r = check($("#ticket").value, draw);
      $$(".nums span.hit").forEach(function (s) { s.classList.remove("hit"); });
      out.className = "out";
      if (r.error) { out.className = "out bad"; out.textContent = "Type the two letters and six digits from your ticket, like BV 543398."; return; }
      if (r.tier) {
        out.className = "out win";
        out.innerHTML = "<span class='label'></span><strong></strong><span class='msg'></span>";
        out.children[0].textContent = ordinal(r.tier.tier);
        out.children[1].textContent = "You won " + rupees(r.tier.amount);
        out.children[2].textContent = r.ticket + " in " + draw.name + " " + draw.code + "-" + draw.draw_no + ". Verify with the Kerala Gazette and claim within 30 days.";
        $$(".nums span[data-n='" + r.ending + "']").forEach(function (s) { s.classList.add("hit"); var d = s.closest("details"); if (d) d.open = true; });
      } else {
        out.className = "out none";
        out.textContent = r.ticket + " has no prize in " + draw.name + " " + draw.code + "-" + draw.draw_no + ". Better luck next time.";
      }
    });
  }

  /* ---------- copy the 1st prize number ---------- */
  $$("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (navigator.clipboard) navigator.clipboard.writeText(b.getAttribute("data-copy")).then(function () { b.textContent = "Copied"; });
    });
  });

  /* ---------- countdown / auto-refresh around 3–4 PM ---------- */
  var cd = $("#countdown");
  if (cd && draw) {
    var now = istNow(), today = ymd(now), w = WEEK[(now.getDay() + 6) % 7];
    if (draw.date !== today) {
      var mins = 15 * 60 - (now.getHours() * 60 + now.getMinutes());
      cd.classList.add("on");
      if (mins > 0) {
        cd.innerHTML = "<b></b><div class='hint'>Result is usually out by 4 PM. Keep this page open — it refreshes by itself.</div>";
        cd.firstChild.textContent = "Today: " + w[1] + " (" + w[0] + ") draw at 3:00 PM — in " + (mins >= 60 ? Math.floor(mins / 60) + "h " : "") + (mins % 60) + "m";
      } else if (now.getHours() < 19) {
        cd.innerHTML = "<b></b><div class='hint'>We publish as soon as the official result is out. This page refreshes every 2 minutes.</div>";
        cd.firstChild.textContent = "Today's " + w[1] + " draw is done — result coming soon";
        setTimeout(function () { location.reload(); }, 120000);
      } else { cd.classList.remove("on"); }
      if (mins > 0 && mins < 70) setTimeout(function () { location.reload(); }, 120000);
    }
  }

  /* ---------- My tickets: save now, auto-checked when the result is out ---------- */
  var box = $("#my-tickets");
  if (box) {
    var sel = $("#my-draw"), now2 = istNow();
    for (var i = 0; i < 7; i++) {
      var d = new Date(now2.getTime() - i * 864e5), wd = WEEK[(d.getDay() + 6) % 7];
      var o = document.createElement("option");
      o.value = ymd(d);
      o.textContent = (i === 0 ? "Today" : i === 1 ? "Yesterday" : d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })) + " · " + wd[1];
      sel.appendChild(o);
    }
    var list = $("#my-list"), recent = null;
    function render() {
      var items = store();
      list.innerHTML = "";
      items.forEach(function (it, idx) {
        var li = document.createElement("li"), dr = recent && recent.filter(function (x) { return x.date === it.date; })[0];
        var status = "Waiting for result";
        if (dr) { var r = check(it.t, dr); status = r.tier ? "Won " + rupees(r.tier.amount) + " · " + ordinal(r.tier.tier) : "No prize"; if (r.tier) li.className = "won"; }
        li.innerHTML = "<span></span><small></small><button type='button' aria-label='Remove ticket'>Remove</button>";
        li.children[0].textContent = it.t;
        li.children[1].textContent = status;
        li.children[2].onclick = function () { var a = store(); a.splice(idx, 1); store(a); render(); };
        list.appendChild(li);
      });
      $("#my-empty").style.display = items.length ? "none" : "block";
    }
    $("#my-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var m = norm($("#my-ticket").value).match(/^([A-Z]{2})(\d{6})$/);
      if (!m) { $("#my-ticket").focus(); return; }
      var a = store(); a.unshift({ t: m[1] + " " + m[2], date: sel.value }); store(a.slice(0, 30));
      $("#my-ticket").value = ""; render();
    });
    render();
    if (store().length) fetch(BASE + "data/recent.json").then(function (r) { return r.json(); }).then(function (j) { recent = j; render(); }).catch(function () {});
  }
})();
