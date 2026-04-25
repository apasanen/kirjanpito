// VAT calculator for expense form
(function () {
  const grossInput = document.getElementById("gross_amount");
  const vatRateInput = document.getElementById("vat_rate");
  const preview = document.getElementById("vat-preview-text");

  function updatePreview() {
    if (!grossInput || !vatRateInput || !preview) return;
    const gross = parseFloat(grossInput.value.replace(",", ".")) || 0;
    const rate = parseFloat(vatRateInput.value.replace(",", ".")) || 0;
    if (gross <= 0) {
      preview.textContent = "Syötä bruttosumma ja ALV-% laskentaa varten.";
      return;
    }
    const vatAmount = (gross * rate) / (100 + rate);
    const netAmount = gross - vatAmount;
    preview.textContent =
      "Netto: " + netAmount.toFixed(2).replace(".", ",") + " €" +
      "  |  ALV (" + rate.toString().replace(".", ",") + " %): " + vatAmount.toFixed(2).replace(".", ",") + " €" +
      "  |  Brutto: " + gross.toFixed(2).replace(".", ",") + " €";
  }

  if (grossInput) grossInput.addEventListener("input", updatePreview);
  if (vatRateInput) vatRateInput.addEventListener("input", updatePreview);

  // Quick-pick VAT rate buttons
  document.querySelectorAll(".vat-quick").forEach(function (btn) {
    btn.addEventListener("click", function () {
      vatRateInput.value = this.dataset.rate;
      updatePreview();
    });
  });

  // Run on page load if editing existing expense
  updatePreview();
})();
