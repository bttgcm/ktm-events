(function () {
  "use strict";

  var root = document.getElementById("events-root");
  var statusEl = document.getElementById("status");
  var generatedAtEl = document.getElementById("generated-at");
  var filterButtons = document.querySelectorAll("#filters button");

  var allEvents = [];
  var currentFilter = "upcoming";

  // Apple/Google/Outlook all treat a webcal:// link as "subscribe to this
  // feed" (auto-refreshing) rather than "download once" - swap the scheme
  // on the same absolute URL so clicking the link offers a subscription.
  (function setupSubscribeLink() {
    var subscribeLink = document.getElementById("subscribe-link");
    var subscribeUrlEl = document.getElementById("subscribe-url");
    if (!subscribeLink) return;
    var absoluteUrl = new URL("events.ics", window.location.href).href;
    subscribeLink.href = absoluteUrl.replace(/^https?:/, "webcal:");
    if (subscribeUrlEl) subscribeUrlEl.textContent = absoluteUrl;
  })();

  var dateFormatter = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  // The source CMS sometimes double-escapes entities (e.g. "&amp;nbsp;"),
  // so decoding once can leave a literal "&nbsp;" behind - decode twice.
  function decodeEntities(text) {
    var el = document.createElement("textarea");
    el.innerHTML = text;
    var once = el.value;
    el.innerHTML = once;
    return el.value;
  }

  function monthKey(isoString) {
    return isoString.slice(0, 7); // "YYYY-MM"
  }

  function monthLabel(isoString) {
    var d = new Date(isoString);
    return new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(d);
  }

  function isPast(event) {
    var end = new Date(event.end || event.start);
    return end.getTime() < Date.now();
  }

  function formatDateRange(event) {
    var start = dateFormatter.format(new Date(event.start));
    if (!event.end) return start;
    var end = dateFormatter.format(new Date(event.end));
    return start === end ? start : start + " – " + end;
  }

  var DEFAULT_EVENT_DURATION_MS = 60 * 60 * 1000; // used when the source gives no end time

  // Compact UTC form required by RFC 5545, e.g. "20260929T091500Z".
  function toICSDateUTC(date) {
    return date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  }

  // Escape TEXT values per RFC 5545 (backslash, comma, semicolon, newline).
  function escapeICSText(text) {
    return String(text)
      .replace(/\\/g, "\\\\")
      .replace(/,/g, "\\,")
      .replace(/;/g, "\\;")
      .replace(/\r?\n/g, "\\n");
  }

  function buildICS(event) {
    var start = new Date(event.start);
    var end = event.end ? new Date(event.end) : new Date(start.getTime() + DEFAULT_EVENT_DURATION_MS);
    var descriptionParts = [];
    if (event.description) descriptionParts.push(decodeEntities(event.description));
    descriptionParts.push(event.source_url);
    var lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Kathmandu Cultural Events//EN",
      "BEGIN:VEVENT",
      "UID:" + event.id + "@ktm-events",
      "DTSTAMP:" + toICSDateUTC(new Date()),
      "DTSTART:" + toICSDateUTC(start),
      "DTEND:" + toICSDateUTC(end),
      "SUMMARY:" + escapeICSText(event.title),
      "DESCRIPTION:" + escapeICSText(descriptionParts.join("\n\n")),
      "URL:" + event.source_url,
    ];
    if (event.location) lines.push("LOCATION:" + escapeICSText(event.location));
    lines.push("END:VEVENT", "END:VCALENDAR");
    return lines.join("\r\n") + "\r\n";
  }

  function slugify(text) {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "event";
  }

  function downloadICS(event) {
    var blob = new Blob([buildICS(event)], { type: "text/calendar;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = slugify(event.title) + ".ics";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function renderCard(event) {
    var card = document.createElement("article");
    card.className = "event-card";

    var dateEl = document.createElement("div");
    dateEl.className = "event-date";
    dateEl.textContent = formatDateRange(event);
    card.appendChild(dateEl);

    var titleEl = document.createElement("h3");
    titleEl.className = "event-title";
    var link = document.createElement("a");
    link.href = event.source_url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = event.title;
    titleEl.appendChild(link);
    card.appendChild(titleEl);

    var metaParts = [event.source_name];
    if (event.location) metaParts.push(event.location);
    var metaEl = document.createElement("p");
    metaEl.className = "event-meta";
    metaEl.textContent = metaParts.join(" · ");
    card.appendChild(metaEl);

    if (event.description) {
      var descEl = document.createElement("p");
      descEl.className = "event-description";
      descEl.textContent = decodeEntities(event.description);
      card.appendChild(descEl);
    }

    if (event.categories && event.categories.length) {
      var tagsEl = document.createElement("div");
      tagsEl.className = "tags";
      event.categories.forEach(function (category) {
        var tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = category;
        tagsEl.appendChild(tag);
      });
      card.appendChild(tagsEl);
    }

    var calendarBtn = document.createElement("button");
    calendarBtn.className = "add-to-calendar";
    calendarBtn.type = "button";
    calendarBtn.textContent = "Add to Calendar";
    calendarBtn.addEventListener("click", function () {
      downloadICS(event);
    });
    card.appendChild(calendarBtn);

    return card;
  }

  function render() {
    root.innerHTML = "";

    var filtered = allEvents.filter(function (event) {
      if (currentFilter === "all") return true;
      if (currentFilter === "past") return isPast(event);
      return !isPast(event);
    });

    if (!filtered.length) {
      var empty = document.createElement("p");
      empty.className = "empty-message";
      empty.textContent = "No events to show.";
      root.appendChild(empty);
      return;
    }

    filtered.sort(function (a, b) {
      return currentFilter === "past"
        ? b.start.localeCompare(a.start)
        : a.start.localeCompare(b.start);
    });

    var currentMonth = null;
    filtered.forEach(function (event) {
      var key = monthKey(event.start);
      if (key !== currentMonth) {
        currentMonth = key;
        var heading = document.createElement("h2");
        heading.className = "month-heading";
        heading.textContent = monthLabel(event.start);
        root.appendChild(heading);
      }
      root.appendChild(renderCard(event));
    });
  }

  filterButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      filterButtons.forEach(function (b) { b.classList.remove("active"); });
      button.classList.add("active");
      currentFilter = button.dataset.filter;
      render();
    });
  });

  fetch("events.json")
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function (data) {
      allEvents = data.events || [];
      statusEl.remove();
      if (data.generated_at) {
        generatedAtEl.textContent =
          "Last updated " + new Date(data.generated_at).toLocaleString();
      }
      render();
    })
    .catch(function (err) {
      statusEl.textContent = "Could not load events: " + err.message;
    });
})();
