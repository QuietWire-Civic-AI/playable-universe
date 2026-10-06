const form = document.querySelector("#attest-form");
const claimEl = document.querySelector("#claim");
const kindEl = document.querySelector("#claim-kind");
const nameEl = document.querySelector("#witness-name");
const photoEl = document.querySelector("#photo");
const photoState = document.querySelector("#photo-state");
const photoPreview = document.querySelector("#photo-preview");
const photoName = document.querySelector("#photo-name");
const photoHash = document.querySelector("#photo-hash");
const photoSize = document.querySelector("#photo-size");
const locationButton = document.querySelector("#location-button");
const locationClear = document.querySelector("#location-clear");
const locationState = document.querySelector("#location-state");
const publicEl = document.querySelector("#public-candidate");
const statusEl = document.querySelector("#form-status");
const receiptEmpty = document.querySelector("#receipt-empty");
const receiptCard = document.querySelector("#receipt-card");
const receiptId = document.querySelector("#receipt-id");
const receiptTime = document.querySelector("#receipt-time");
const packetSha = document.querySelector("#packet-sha");
const receiptSha = document.querySelector("#receipt-sha");
const receiptPublic = document.querySelector("#receipt-public");
const copyReceipt = document.querySelector("#copy-receipt");
const shareReceipt = document.querySelector("#share-receipt");
const downloadButton = document.querySelector("#download-button");
const streamGrid = document.querySelector("#stream-grid");
const refreshStream = document.querySelector("#refresh-stream");

let photoEvidence = null;
let photoObjectUrl = null;
let coarseLocation = null;
let lastPacket = null;
let lastReceipt = null;

function newClientId() {
  if (crypto.randomUUID) return "browser:" + crypto.randomUUID();
  const a = new Uint8Array(16);
  crypto.getRandomValues(a);
  return "browser:" + [...a].map(x => x.toString(16).padStart(2, "0")).join("");
}

const clientId = localStorage.getItem("playable-client-id") || newClientId();
localStorage.setItem("playable-client-id", clientId);

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, "0")).join("");
}

function bytesLabel(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KiB";
  return (n / (1024 * 1024)).toFixed(2) + " MiB";
}

function buildPacket() {
  const text = claimEl.value.trim();
  if (!text) throw new Error("Say what you attest first.");
  const name = nameEl.value.trim();
  return {
    schema: "playable.mobile-attestation.v0",
    client_id: clientId,
    created_at: new Date().toISOString(),
    claim: {
      text,
      kind: kindEl.value
    },
    witness: {
      mode: name ? "self_asserted_name" : "anonymous",
      display_name: name || null,
      identity_ref: null
    },
    assurance: {
      class: "browser-self-asserted",
      signature: null
    },
    evidence: photoEvidence ? [photoEvidence] : [],
    location: coarseLocation ? {
      mode: "coarse",
      latitude: coarseLocation.latitude,
      longitude: coarseLocation.longitude,
      accuracy_m: coarseLocation.accuracy_m,
      place_label: null
    } : {
      mode: "none",
      latitude: null,
      longitude: null,
      accuracy_m: null,
      place_label: null
    },
    sharing: {
      candidate_visibility: publicEl.checked ? "public-candidate" : "receipt-only",
      media_disposition: "hash-only-v0"
    },
    refs: [],
    notes: [
      "Created by the public Playable Universe phone/browser field client."
    ]
  };
}

function renderGlyph(el, seed) {
  el.innerHTML = "";
  const clean = (seed || "playable-universe").replace(/[^0-9a-f]/gi, "");
  let bits = "";
  for (const ch of clean || "0123456789abcdef") {
    bits += parseInt(ch, 16).toString(2).padStart(4, "0");
  }
  for (let i = 0; i < 81; i++) {
    const s = document.createElement("span");
    const mirror = i % 9 > 4 ? Math.floor(i / 9) * 9 + (8 - (i % 9)) : i;
    if (bits[mirror % bits.length] === "1") s.className = "on";
    el.appendChild(s);
  }
}

renderGlyph(document.querySelector("#draft-glyph"), "2025playable2026");

photoEl.addEventListener("change", async () => {
  const file = photoEl.files && photoEl.files[0];
  if (!file) return;
  statusEl.textContent = "Hashing photo locally…";
  try {
    const buffer = await file.arrayBuffer();
    const digest = await sha256Hex(buffer);
    photoEvidence = {
      kind: "photo_hash",
      sha256: digest,
      mime: file.type || "application/octet-stream",
      bytes: file.size,
      label: file.name || "phone photo",
      custody: "device-local"
    };
    if (photoObjectUrl) URL.revokeObjectURL(photoObjectUrl);
    photoObjectUrl = URL.createObjectURL(file);
    photoPreview.innerHTML = "";
    const img = document.createElement("img");
    img.src = photoObjectUrl;
    img.alt = "Selected attestation photo preview";
    photoPreview.appendChild(img);
    photoName.textContent = file.name || "Phone photo";
    photoHash.textContent = digest;
    photoSize.textContent = bytesLabel(file.size) + " · " + (file.type || "unknown MIME") + " · photo remains local";
    photoState.classList.remove("empty");
    statusEl.textContent = "Photo digest ready. The photo itself will not be uploaded.";
  } catch (err) {
    statusEl.textContent = "Could not hash photo: " + err.message;
  }
});

locationButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    statusEl.textContent = "This browser does not expose geolocation.";
    return;
  }
  statusEl.textContent = "Waiting for explicit location permission…";
  navigator.geolocation.getCurrentPosition(
    pos => {
      coarseLocation = {
        latitude: Math.round(pos.coords.latitude * 1000) / 1000,
        longitude: Math.round(pos.coords.longitude * 1000) / 1000,
        accuracy_m: Math.round(pos.coords.accuracy)
      };
      locationState.textContent =
        "Coarse location: " + coarseLocation.latitude.toFixed(3) + ", " +
        coarseLocation.longitude.toFixed(3) +
        " · device accuracy reported about " + coarseLocation.accuracy_m + " m";
      locationClear.hidden = false;
      statusEl.textContent = "Coarse location attached. Raw precision is not placed in the packet.";
    },
    err => {
      statusEl.textContent = "Location not attached: " + err.message;
    },
    {enableHighAccuracy:false, timeout:12000, maximumAge:30000}
  );
});

locationClear.addEventListener("click", () => {
  coarseLocation = null;
  locationState.textContent = "No location attached.";
  locationClear.hidden = true;
});

function downloadObject(obj, filename) {
  const blob = new Blob([JSON.stringify(obj, null, 2) + "\n"], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

downloadButton.addEventListener("click", () => {
  try {
    const packet = buildPacket();
    lastPacket = packet;
    downloadObject(
      {packet, receipt:lastReceipt},
      "playable-attestation-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json"
    );
    statusEl.textContent = "Draft JSON downloaded. This does not submit anything.";
  } catch (err) {
    statusEl.textContent = err.message;
  }
});

form.addEventListener("submit", async event => {
  event.preventDefault();
  let packet;
  try {
    packet = buildPacket();
  } catch (err) {
    statusEl.textContent = err.message;
    return;
  }
  lastPacket = packet;
  statusEl.textContent = "Submitting candidate packet…";
  document.querySelector("#submit-button").disabled = true;
  try {
    const response = await fetch("../api/v0/attestations", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(packet)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || result.error || ("HTTP " + response.status));
    lastReceipt = result;
    receiptEmpty.hidden = true;
    receiptCard.hidden = false;
    receiptId.textContent = result.candidate_id;
    receiptTime.textContent = result.received_at;
    packetSha.textContent = result.packet_sha256;
    receiptSha.textContent = result.receipt_sha256;
    receiptPublic.textContent = result.public_candidate ? "PUBLIC CANDIDATE" : "RECEIPT ONLY";
    renderGlyph(document.querySelector("#receipt-glyph"), result.receipt_sha256);
    statusEl.textContent = "Attest received. Candidate receipt created.";
    if (result.public_candidate) loadStream();
  } catch (err) {
    statusEl.textContent = "Submission failed: " + err.message + ". You can still download the draft packet.";
  } finally {
    document.querySelector("#submit-button").disabled = false;
  }
});

copyReceipt.addEventListener("click", async () => {
  if (!lastReceipt) return;
  await navigator.clipboard.writeText(JSON.stringify(lastReceipt, null, 2));
  statusEl.textContent = "Receipt copied.";
});

shareReceipt.addEventListener("click", async () => {
  if (!lastReceipt) return;
  const text = "Playable Universe attestation receipt\n" +
    lastReceipt.candidate_id + "\npacket " + lastReceipt.packet_sha256;
  if (navigator.share) {
    try {
      await navigator.share({title:"Playable Universe attestation", text});
    } catch (_) {}
  } else {
    await navigator.clipboard.writeText(text);
    statusEl.textContent = "Share text copied.";
  }
});

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  })[ch]);
}

async function loadStream() {
  streamGrid.innerHTML = '<p class="muted">Loading public candidates…</p>';
  try {
    const r = await fetch("../api/v0/attestations/public?limit=30", {cache:"no-store"});
    if (!r.ok) throw new Error("HTTP " + r.status);
    const feed = await r.json();
    if (!feed.items.length) {
      streamGrid.innerHTML = '<p class="muted">No public field candidates yet. The first one can be made above.</p>';
      return;
    }
    streamGrid.innerHTML = feed.items.map(item => {
      const p = item.packet;
      const who = p.witness.display_name || "Anonymous witness";
      const where = p.location.mode === "coarse"
        ? p.location.latitude.toFixed(3) + ", " + p.location.longitude.toFixed(3)
        : "no location";
      return '<article class="stream-card">' +
        '<div class="stamp"><span class="unverified">SELF-ATTESTED / UNVERIFIED</span><span>' +
        esc(new Date(item.received_at).toLocaleString()) + '</span></div>' +
        '<p class="claim">' + esc(p.claim.text) + '</p>' +
        '<p class="meta">' + esc(who) + ' · ' + esc(p.claim.kind.replaceAll("_"," ")) +
        ' · ' + esc(where) + ' · ' + p.evidence.length + ' evidence digest(s)</p>' +
        '<code>' + esc(item.candidate_id) + '</code>' +
        '</article>';
    }).join("");
  } catch (err) {
    streamGrid.innerHTML = '<p class="muted">Field stream unavailable: ' + esc(err.message) + '</p>';
  }
}

refreshStream.addEventListener("click", loadStream);
loadStream();
