const urlInput = document.getElementById("url-input");
const fetchBtn = document.getElementById("fetch-btn");
const statusEl = document.getElementById("status");
const resultEmpty = document.getElementById("result-empty");
const resultContent = document.getElementById("result-content");

function setStatus(message, type) {
  statusEl.textContent = message || "";
  statusEl.className = type || "";
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderResult(data) {
  resultEmpty.classList.add("hidden");
  resultContent.classList.remove("hidden");

  const fields = data.product_fields || {};
  const breadcrumbs = data.breadcrumbs || [];
  let html = "";

  // 1. TOP SECTION: Image Gallery (All images)
  const images = data.all_images || [];
  if (images.length === 0 && data.og_image) {
    images.push(data.og_image);
  }
  
  if (images.length > 0) {
    html += `<div class="image-gallery">`;
    images.forEach(url => {
      html += `<img src="${escapeHtml(url)}" alt="product image" loading="lazy" />`;
    });
    html += `</div>`;
  }

  // 2. MIDDLE SECTION: Title & Links
  html += `<div class="product-title-section">`;
  html += `<h2>${escapeHtml(fields["Product Name"] || data.page_title || "Untitled")}</h2>`;
  if (data.canonical_url) {
    html += `<a href="${escapeHtml(data.canonical_url)}" target="_blank" rel="noopener">${escapeHtml(data.canonical_url)}</a>`;
  }
  html += `</div>`;

  // 3. BREADCRUMBS
  if (breadcrumbs.length) {
    html += `<div class="breadcrumbs">`;
    html += breadcrumbs.map(b => escapeHtml(b.name)).join(" &rsaquo; ");
    html += `</div>`;
  }

  // 4. VARIANTS (Sizes, Prices, Stock)
  if (data.variants && data.variants.length > 0) {
    html += `<h3>Select Size / Variants</h3>`;
    html += `<div class="variants-container">`;
    data.variants.forEach(v => {
      const stockClass = v.in_stock ? "in-stock" : "out-of-stock";
      const priceText = v.price ? `₹${v.price}` : "";
      html += `
        <div class="variant-box ${stockClass}">
            <div class="v-size">${escapeHtml(v.size)}</div>
            <div class="v-price">${escapeHtml(priceText)}</div>
            <div class="v-status">${v.in_stock ? "In Stock" : "Out of Stock"}</div>
        </div>`;
    });
    html += `</div>`;
  }

  // 5. PRODUCT HIGHLIGHTS & DETAILS
  const highlights = data.highlights || {};
  const hKeys = Object.keys(highlights);
  if (hKeys.length > 0) {
    html += `<h3>Product Highlights</h3>`;
    html += `<table class="data-table"><tbody>`;
    for (const key of hKeys) {
      html += `<tr><th>${escapeHtml(key)}</th><td>${escapeHtml(highlights[key])}</td></tr>`;
    }
    html += `</tbody></table><br/>`;
  }

  // 6. OTHER DATA TABLE
  const fieldKeys = Object.keys(fields).filter(k => k !== "Product Name");
  if (fieldKeys.length) {
    html += `<h3>Other Details</h3>`;
    html += `<table class="data-table"><tbody>`;
    for (const key of fieldKeys) {
      html += `<tr><th>${escapeHtml(key)}</th><td>${escapeHtml(fields[key])}</td></tr>`;
    }
    html += `</tbody></table><br/>`;
  }

  // 7. SIMILAR PRODUCTS
  if (data.similar_products && data.similar_products.length > 0) {
    html += `<h3>Similar Products</h3>`;
    html += `<div class="similar-products-grid">`;
    data.similar_products.forEach(sim => {
        html += `
        <div class="similar-card">
            <img src="${escapeHtml(sim.image)}" alt="similar product" loading="lazy" />
            <div class="sim-title">${escapeHtml(sim.name)}</div>
            <div class="sim-price">₹${escapeHtml(sim.price)}</div>
        </div>`;
    });
    html += `</div>`;
  }

  html += `<details class="raw-json"><summary>Raw JSON-LD (debug ke liye)</summary>`;
  html += `<pre>${escapeHtml(JSON.stringify(data.json_ld_raw, null, 2))}</pre></details>`;

  if (data.next_data_raw && Object.keys(data.next_data_raw).length) {
    html += `<details class="raw-json"><summary>Poora __NEXT_DATA__</summary>`;
    html += `<pre>${escapeHtml(JSON.stringify(data.next_data_raw, null, 2))}</pre></details>`;
  }

  resultContent.innerHTML = html;
}

async function handleFetch() {
  const url = urlInput.value.trim();
  if (!url) {
    setStatus("Pehle URL daalo.", "error");
    return;
  }

  fetchBtn.disabled = true;
  setStatus("Fetch ho raha hai...", "");

  try {
    const res = await fetch("/api/fetch", {
      method: "POST",
      headers: { 
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "any_value" 
      },
      body: JSON.stringify({ url }),
    });
    
    // NAYA CODE: Directly json parse karne ki jagah pehle text read karo
    const responseText = await res.text();
    let json;
    try {
        json = JSON.parse(responseText);
    } catch (parseError) {
        // Agar response HTML/Text aaya (e.g. Render 502 Bad Gateway)
        console.error("Raw Server Response:", responseText);
        throw new Error("API ne JSON ke bajaye HTML/Error return kiya. Server crash ya timeout ho gaya (Check Render Logs).");
    }

    if (!json.ok) {
      setStatus(json.error || "Kuch gadbad ho gayi.", "error");
      return;
    }

    setStatus("Fetch ho gaya!", "success");
    renderResult(json.data);
  } catch (err) {
    setStatus("Server issue: " + err.message, "error");
  } finally {
    fetchBtn.disabled = false;
  }
}

fetchBtn.addEventListener("click", handleFetch);
urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleFetch();
});

const pincodeBtn = document.getElementById("pincode-btn");

// Show pincode button only after primary fetch is successful
const originalRenderResult = renderResult;
renderResult = function(data) {
    originalRenderResult(data);
    pincodeBtn.classList.remove("hidden");
};

async function handlePincodeCheck() {
    const url = urlInput.value.trim();
    if (!url) return;

    pincodeBtn.disabled = true;
    pincodeBtn.textContent = "Checking Pincodes (Browser Khulega)...";
    setStatus("Pincodes check ho rahe hain, kripya wait karein...", "");

    try {
        const res = await fetch("/api/check-pincodes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });
        const json = await res.json();

        if (!json.ok) {
            setStatus("Pincode Error: " + (json.error || "Unknown"), "error");
            return;
        }

        setStatus("Pincode check complete!", "success");
        appendPincodeAnalytics(json.data);
    } catch (err) {
        setStatus("Pincode Server Error: " + err.message, "error");
    } finally {
        pincodeBtn.disabled = false;
        pincodeBtn.textContent = "Check Pincodes (Bulk)";
    }
}

function appendPincodeAnalytics(data) {
    if (data.error) {
        alert(data.error);
        return;
    }

    const a = data.analytics;
    let html = `
    <div class="pincode-report" style="margin-top: 40px; padding-top: 20px; border-top: 2px dashed #6c5ce7;">
        <h2>📍 Pincode Pricing Analytics</h2>
        
        <div class="analytics-grid">
            <div class="stat-box success">
                <h4>Lowest Price</h4>
                <div class="stat-price">₹${a.lowest.price}</div>
                <div class="stat-pins">Pincodes: ${a.lowest.pincodes.join(", ")}</div>
            </div>
            
            <div class="stat-box warning">
                <h4>Average Price</h4>
                <div class="stat-price">₹${a.average}</div>
                <div class="stat-pins">Mid-range Pincodes: ${a.mid_range.pincodes.length > 0 ? a.mid_range.pincodes.join(", ") : "None"}</div>
            </div>

            <div class="stat-box danger">
                <h4>Highest Price</h4>
                <div class="stat-price">₹${a.highest.price}</div>
                <div class="stat-pins">Pincodes: ${a.highest.pincodes.join(", ")}</div>
            </div>
        </div>

        <h3>Raw Data</h3>
        <table class="data-table">
            <tbody>
                ${Object.entries(data.raw_results).map(([pin, price]) => `<tr><th>${escapeHtml(pin)}</th><td>₹${escapeHtml(price)}</td></tr>`).join("")}
            </tbody>
        </table>
    </div>`;

    // Append to existing content without clearing it
    resultContent.insertAdjacentHTML('beforeend', html);
    
    // Scroll to the new report
    resultContent.lastElementChild.scrollIntoView({ behavior: "smooth" });
}

pincodeBtn.addEventListener("click", handlePincodeCheck);