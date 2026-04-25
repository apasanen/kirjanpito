// Expense line row management + per-line VAT calculator
(function () {
  const container = document.getElementById('lines-container');
  if (!container) return;

  const addBtn = document.getElementById('add-line-btn');
  const totalEl = document.getElementById('lines-total');

  function calcRow(row) {
    const gross = parseFloat((row.querySelector('.line-gross')?.value || '0').replace(',', '.')) || 0;
    const rate = parseFloat((row.querySelector('.line-vat-rate')?.value || '0').replace(',', '.')) || 0;
    let vat = 0, net = gross;
    if (gross > 0 && rate > 0) {
      vat = (gross * rate) / (100 + rate);
      net = gross - vat;
    }
    const preview = row.querySelector('.line-preview');
    if (preview) {
      preview.textContent = gross > 0
        ? 'Netto: ' + net.toFixed(2).replace('.', ',') + ' € | ALV: ' + vat.toFixed(2).replace('.', ',') + ' €'
        : '';
    }
    return gross;
  }

  function updateTotal() {
    let total = 0;
    const rows = container.querySelectorAll('.line-row');
    rows.forEach(function (r) { total += calcRow(r); });
    if (totalEl) totalEl.textContent = 'Yhteensä brutto: ' + total.toFixed(2).replace('.', ',') + ' €';
    // Disable remove button when only 1 row
    rows.forEach(function (r) {
      const btn = r.querySelector('.remove-line-btn');
      if (btn) btn.disabled = rows.length <= 1;
    });
  }

  // Input events
  container.addEventListener('input', function (e) {
    if (e.target.classList.contains('line-gross') || e.target.classList.contains('line-vat-rate')) {
      updateTotal();
    }
  });

  // Clicks: remove row or VAT quick-pick
  container.addEventListener('click', function (e) {
    const removeBtn = e.target.closest('.remove-line-btn');
    if (removeBtn) {
      const row = removeBtn.closest('.line-row');
      if (container.querySelectorAll('.line-row').length > 1) {
        row.remove();
        updateTotal();
      }
      return;
    }
    const quickBtn = e.target.closest('.vat-quick');
    if (quickBtn) {
      const row = quickBtn.closest('.line-row');
      const rateInput = row && row.querySelector('.line-vat-rate');
      if (rateInput) {
        rateInput.value = quickBtn.dataset.rate;
        updateTotal();
      }
    }
  });

  // Add row
  if (addBtn) {
    addBtn.addEventListener('click', function () {
      const rows = container.querySelectorAll('.line-row');
      const newRow = rows[rows.length - 1].cloneNode(true);
      newRow.querySelectorAll('input[type=number], input[type=text]').forEach(function (inp) { inp.value = ''; });
      newRow.querySelectorAll('select').forEach(function (sel) { sel.selectedIndex = 0; });
      newRow.querySelectorAll('.line-preview').forEach(function (el) { el.textContent = ''; });
      const removeBtn = newRow.querySelector('.remove-line-btn');
      if (removeBtn) removeBtn.disabled = false;
      container.appendChild(newRow);
      updateTotal();
      newRow.querySelector('.line-gross')?.focus();
    });
  }

  updateTotal();
})();

// Table sorting
(function () {
  function cellValue(row, col) {
    const cell = row.cells[col];
    return cell ? cell.innerText.trim() : "";
  }

  function compareValues(a, b, numeric) {
    if (numeric) {
      const na = parseFloat(a.replace(",", ".")) || 0;
      const nb = parseFloat(b.replace(",", ".")) || 0;
      return na - nb;
    }
    return a.localeCompare(b, "fi");
  }

  document.querySelectorAll("th[data-sort]").forEach(function (th) {
    th.style.cursor = "pointer";
    th.style.userSelect = "none";
    th.setAttribute("title", "Klikkaa lajitellaksesi");

    th.addEventListener("click", function () {
      const table = th.closest("table");
      const tbody = table.querySelector("tbody");
      const rows = Array.from(tbody.querySelectorAll("tr")).filter(function (r) {
        return r.cells.length > 1; // skip empty/placeholder rows
      });
      const col = th.cellIndex;
      const numeric = th.dataset.sort === "num";
      const currentAsc = th.dataset.dir !== "asc";
      th.dataset.dir = currentAsc ? "asc" : "desc";

      // Reset other headers
      table.querySelectorAll("th[data-sort]").forEach(function (other) {
        if (other !== th) {
          delete other.dataset.dir;
          other.querySelector(".sort-icon") && (other.querySelector(".sort-icon").textContent = " ⇅");
        }
      });
      th.querySelector(".sort-icon").textContent = currentAsc ? " ↑" : " ↓";

      rows.sort(function (a, b) {
        const av = cellValue(a, col);
        const bv = cellValue(b, col);
        const cmp = compareValues(av, bv, numeric);
        return currentAsc ? cmp : -cmp;
      });

      rows.forEach(function (r) { tbody.appendChild(r); });

      // Remove month separator rows after sort – they're only valid in default date order
      tbody.querySelectorAll("tr.month-separator").forEach(function (r) { r.remove(); });
    });

    // Add icon span
    const icon = document.createElement("span");
    icon.className = "sort-icon text-muted";
    icon.textContent = " ⇅";
    th.appendChild(icon);
  });
})();
