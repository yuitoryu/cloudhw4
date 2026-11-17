const form = document.querySelector("#predict-form");
const input = document.querySelector("#image-id");
const button = form.querySelector("button");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const preview = document.querySelector("#sample");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (button.disabled) return;

  result.hidden = true;
  status.classList.remove("error");
  input.removeAttribute("aria-invalid");

  const imageId = input.valueAsNumber;
  if (!input.validity.valid || !Number.isInteger(imageId)) {
    input.setAttribute("aria-invalid", "true");
    status.textContent = "Enter a valid image ID between 0 and 9,999.";
    status.classList.add("error");
    input.focus();
    return;
  }

  button.disabled = true;
  input.readOnly = true;
  status.textContent = "Loading prediction…";

  try {
    const signal = AbortSignal.timeout(10000);
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_id: imageId }),
      signal,
    });
    if (!response.ok) throw new Error(`Prediction failed (HTTP ${response.status}).`);

    const prediction = await response.json();
    const sample = await fetch(`/sample/${prediction.image_id}`, { signal });
    if (!sample.ok) throw new Error(`Sample failed (HTTP ${sample.status}).`);

    const sampleUrl = URL.createObjectURL(await sample.blob());
    preview.src = sampleUrl;
    preview.alt = `Handwritten MNIST digit in test image ${prediction.image_id}`;
    try {
      await preview.decode();
    } finally {
      URL.revokeObjectURL(sampleUrl);
    }

    document.querySelector("#caption").textContent = `Test image ${prediction.image_id}`;
    document.querySelector("#prediction").textContent = prediction.predicted_digit;
    document.querySelector("#actual").textContent = prediction.actual_digit;
    document.querySelector("#version").textContent = prediction.model_version;
    result.hidden = false;
    status.textContent = "";
  } catch {
    status.textContent = "Could not load the prediction. Try again in a moment.";
    status.classList.add("error");
  } finally {
    button.disabled = false;
    input.readOnly = false;
  }
});

form.requestSubmit();
