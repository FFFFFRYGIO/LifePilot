/** Filter & sort toolbars on every task list (prototype only). */
(function () {
  var FILTER_OPTIONS = [
    { id: "all", label: "All tasks" },
    { id: "active", label: "Active" },
    { id: "completed", label: "Completed" },
    { id: "overdue", label: "Overdue" },
  ];
  var SORT_OPTIONS = [
    { id: "due", label: "Due date" },
    { id: "priority", label: "Priority" },
    { id: "name", label: "Name (A–Z)" },
    { id: "category", label: "Category" },
  ];

  function createPopup(type, options, defaultId) {
    var popup = document.createElement("div");
    popup.className = "task-list-popup task-list-popup--" + type;
    popup.hidden = true;
    popup.setAttribute("role", "menu");

    var title = document.createElement("p");
    title.className = "task-list-popup__title";
    title.textContent = type === "filter" ? "Filter by" : "Sort by";
    popup.appendChild(title);

    options.forEach(function (opt) {
      var optionBtn = document.createElement("button");
      optionBtn.type = "button";
      optionBtn.className =
        "task-list-popup__option" + (opt.id === defaultId ? " is-active" : "");
      optionBtn.setAttribute("role", "menuitemradio");
      optionBtn.setAttribute("aria-checked", opt.id === defaultId ? "true" : "false");
      optionBtn.dataset.value = opt.id;
      optionBtn.textContent = opt.label;
      popup.appendChild(optionBtn);
    });

    return popup;
  }

  function createToolWrap(type, label, options, defaultId) {
    var wrap = document.createElement("div");
    wrap.className = "task-list-tool-wrap";

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "task-list-tool";
    btn.dataset.taskTool = type;
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-haspopup", "true");
    btn.textContent = label;

    wrap.appendChild(btn);
    wrap.appendChild(createPopup(type, options, defaultId));
    return wrap;
  }

  function closePopup(popup) {
    if (!popup || popup.hidden) return;
    popup.hidden = true;
    var trigger = popup.parentElement.querySelector(".task-list-tool");
    if (trigger) {
      trigger.classList.remove("is-open");
      trigger.setAttribute("aria-expanded", "false");
    }
  }

  function closeAllPopups(except) {
    document.querySelectorAll(".task-list-popup").forEach(function (popup) {
      if (popup !== except) closePopup(popup);
    });
  }

  function openPopup(popup) {
    closeAllPopups(popup);
    popup.hidden = false;
    var trigger = popup.parentElement.querySelector(".task-list-tool");
    if (trigger) {
      trigger.classList.add("is-open");
      trigger.setAttribute("aria-expanded", "true");
    }
  }

  function syncAppliedState(toolBtn) {
    var popup = toolBtn.parentElement.querySelector(".task-list-popup");
    var active = popup && popup.querySelector(".task-list-popup__option.is-active");
    var isDefault =
      (toolBtn.dataset.taskTool === "filter" && active && active.dataset.value === "all") ||
      (toolBtn.dataset.taskTool === "sort" && active && active.dataset.value === "due");
    toolBtn.classList.toggle("is-applied", !isDefault);
  }

  function initTaskListToolbars() {
    document.querySelectorAll(".task-list").forEach(function (list) {
      if (list.closest(".task-list-wrap")) return;

      var toolbar = document.createElement("div");
      toolbar.className = "task-list-toolbar";
      toolbar.appendChild(createToolWrap("filter", "Filter", FILTER_OPTIONS, "all"));
      toolbar.appendChild(createToolWrap("sort", "Sort", SORT_OPTIONS, "due"));

      var wrap = document.createElement("div");
      wrap.className = "task-list-wrap";
      list.parentNode.insertBefore(wrap, list);
      wrap.appendChild(toolbar);
      wrap.appendChild(list);
    });

    document.querySelectorAll(".task-list-tool").forEach(syncAppliedState);
  }

  document.addEventListener("click", function (event) {
    var toolBtn = event.target.closest(".task-list-tool");
    if (toolBtn) {
      event.stopPropagation();
      var popup = toolBtn.parentElement.querySelector(".task-list-popup");
      if (popup.hidden) openPopup(popup);
      else closePopup(popup);
      return;
    }

    var optionBtn = event.target.closest(".task-list-popup__option");
    if (optionBtn) {
      var popup = optionBtn.closest(".task-list-popup");
      popup.querySelectorAll(".task-list-popup__option").forEach(function (opt) {
        var selected = opt === optionBtn;
        opt.classList.toggle("is-active", selected);
        opt.setAttribute("aria-checked", selected ? "true" : "false");
      });
      var trigger = popup.parentElement.querySelector(".task-list-tool");
      if (trigger) syncAppliedState(trigger);
      closePopup(popup);
      return;
    }

    if (!event.target.closest(".task-list-popup")) {
      closeAllPopups();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeAllPopups();
  });

  initTaskListToolbars();
})();

/** Toggle done styling on task checkboxes (prototype only). */
(function () {
  function syncDone(item, checkbox) {
    item.classList.toggle("task-item--done", checkbox.checked);
  }

  document.querySelectorAll(".task-item").forEach(function (item) {
    var checkbox = item.querySelector('input[type="checkbox"]');
    if (!checkbox) return;

    syncDone(item, checkbox);
    checkbox.addEventListener("change", function () {
      syncDone(item, checkbox);
      if (typeof window.__syncShoppingHeader === "function") {
        window.__syncShoppingHeader();
      }
    });
  });
})();

/** Shopping list header counts. */
(function () {
  if (!document.body.classList.contains("page-category--shopping")) return;

  var headerSubtitle = document.querySelector(".app-header__text p");
  var sectionTitle = document.querySelector(".section-title");

  function syncShoppingHeader() {
    var toBuy = document.querySelectorAll(
      ".task-list .task-item input[type=checkbox]:not(:checked)"
    ).length;
    if (headerSubtitle) {
      headerSubtitle.textContent =
        toBuy + " to buy · includes missing pantry items automatically";
    }
    if (sectionTitle) {
      sectionTitle.textContent = "To buy · " + toBuy;
    }
  }

  window.__syncShoppingHeader = syncShoppingHeader;
  syncShoppingHeader();
})();

/** Pantry quantity +/- on Pantry category page. */
(function () {
  if (!document.body.classList.contains("page-category--pantry")) return;

  var headerSubtitle = document.querySelector(".app-header__text p");
  var sectionTitle = document.querySelector(".section-title");

  function parseMeta(metaEl) {
    var match = metaEl.textContent.match(/^(.+?) · (\d+) \/ (\d+) required$/);
    if (!match) return null;
    return {
      category: match[1],
      required: parseInt(match[3], 10),
    };
  }

  function formatMeta(category, home, required) {
    return category + " · " + home + " / " + required + " required";
  }

  function countBelowRequired() {
    var count = 0;
    document.querySelectorAll(".pantry-item").forEach(function (item) {
      var qtyEl = item.querySelector(".qty-value");
      var metaEl = item.querySelector(".pantry-item__meta");
      var parsed = parseMeta(metaEl);
      if (parsed && parseInt(qtyEl.textContent, 10) < parsed.required) count++;
    });
    return count;
  }

  function syncPantryHeader() {
    var tracked = document.querySelectorAll(".pantry-item").length;
    var below = countBelowRequired();
    if (headerSubtitle) {
      headerSubtitle.textContent = tracked + " tracked · " + below + " below required";
    }
    if (sectionTitle) {
      sectionTitle.textContent = "At home · " + tracked + " tracked";
    }
  }

  function syncPantryItem(item) {
    var qtyEl = item.querySelector(".qty-value");
    var metaEl = item.querySelector(".pantry-item__meta");
    var minusBtn = item.querySelector('.qty-btn[aria-label="Remove one"]');
    var parsed = parseMeta(metaEl);
    if (!parsed || !qtyEl) return;

    var home = parseInt(qtyEl.textContent, 10);
    metaEl.textContent = formatMeta(parsed.category, home, parsed.required);
    item.classList.toggle("pantry-item--low", home < parsed.required);
    if (minusBtn) minusBtn.disabled = home <= 0;
    syncPantryHeader();
  }

  document.querySelectorAll(".pantry-item").forEach(function (item) {
    var qtyEl = item.querySelector(".qty-value");
    var minusBtn = item.querySelector('.qty-btn[aria-label="Remove one"]');
    var plusBtn = item.querySelector('.qty-btn[aria-label="Add one"]');
    if (!qtyEl || !minusBtn || !plusBtn) return;

    syncPantryItem(item);

    minusBtn.addEventListener("click", function () {
      var home = parseInt(qtyEl.textContent, 10);
      if (home <= 0) return;
      qtyEl.textContent = String(home - 1);
      syncPantryItem(item);
    });

    plusBtn.addEventListener("click", function () {
      var home = parseInt(qtyEl.textContent, 10);
      qtyEl.textContent = String(home + 1);
      syncPantryItem(item);
    });
  });
})();
