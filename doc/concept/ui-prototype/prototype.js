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
