(function () {
  "use strict";

  var root = document.getElementById("events-root");
  var statusEl = document.getElementById("status");
  var generatedAtEl = document.getElementById("generated-at");
  var filterButtons = document.querySelectorAll("#filters button");

  var allEvents = [];
  var currentFilter = "upcoming";

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
