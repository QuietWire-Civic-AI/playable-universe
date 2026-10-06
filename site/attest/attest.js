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
const photoCustody = document.querySelector("#photo-custody");
const preservePrivate = document.querySelector("#preserve-private");
const savePhotoCopy = document.querySelector("#save-photo-copy");
const sharePhotoCopy = document.querySelector("#share-photo-copy");
const photoCustodyStatus = document.querySelector("#photo-custody-status");

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

const publishPhotoPanel = document.querySelector("#publish-photo-panel");
const publishSelectedPhoto = document.querySelector("#publish-selected-photo");
const publishPhotoStatus = document.querySelector("#publish-photo-status");

const existingPhotoPanel = document.querySelector("#existing-photo-panel");
const existingPhotoLabel = document.querySelector("#existing-photo-label");
const existingPhotoCandidate = document.querySelector("#existing-photo-candidate");
const existingPhotoSha = document.querySelector("#existing-photo-sha");
const existingPhotoFile = document.querySelector("#existing-photo-file");
const existingPhotoUpload = document.querySelector("#existing-photo-upload");
const existingPhotoPublish = document.querySelector("#existing-photo-publish");
const existingPhotoStatus = document.querySelector("#existing-photo-status");

let photoEvidence = null;
let selectedPhotoFile = null;
let photoObjectUrl = null;
let coarseLocation = null;
let lastPacket = null;
let lastReceipt = null;
let lastPrivateCustody = null;
let existingPrivateReady = false;

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

async function fileSha256(file) {
  return sha256Hex(await file.arrayBuffer());
}

function bytesLabel(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KiB";
  return (n / (1024 * 1024)).toFixed(2) + " MiB";
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  })[ch]);
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

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function durablePhotoFilename(file) {
  const ext = (file.name && file.name.includes("."))
    ? "." + file.name.split(".").pop().replace(/[^A-Za-z0-9]/g, "").slice(0, 8)
    : (file.type === "image/png" ? ".png" : file.type === "image/webp" ? ".webp" : ".jpg");
  return "playable-attestation-photo-" +
    new Date().toISOString().replace(/[:.]/g, "-") + ext;
}

photoEl.addEventListener("change", async () => {
  const file = photoEl.files && photoEl.files[0];
  if (!file) return;
  statusEl.textContent = "Hashing photo locally…";
  try {
    const digest = await fileSha256(file);
    selectedPhotoFile = file;
    lastPrivateCustody = null;
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
    photoSize.textContent =
      bytesLabel(file.size) + " · " + (file.type || "unknown MIME") +
      " · browser-held until you save or preserve it";
    photoState.classList.remove("empty");
    photoCustody.hidden = false;
    photoCustodyStatus.textContent =
      "Important: camera capture inside a browser is not guaranteed to create a gallery copy. Keep private preservation checked, or save/share a copy now.";
    statusEl.textContent =
      "Photo digest ready. No upload has happened yet.";
  } catch (err) {
    statusEl.textContent = "Could not hash photo: " + err.message;
  }
});

savePhotoCopy.addEventListener("click", () => {
  if (!selectedPhotoFile) {
    photoCustodyStatus.textContent = "Choose or take a photo first.";
    return;
  }
  downloadBlob(selectedPhotoFile, durablePhotoFilename(selectedPhotoFile));
  photoCustodyStatus.textContent =
    "A copy was offered to the browser download system. On most phones this lands in Downloads/Files rather than the camera gallery.";
});

sharePhotoCopy.addEventListener("click", async () => {
  if (!selectedPhotoFile) {
    photoCustodyStatus.textContent = "Choose or take a photo first.";
    return;
  }
  if (
    navigator.share &&
    (!navigator.canShare || navigator.canShare({files:[selectedPhotoFile]}))
  ) {
    try {
      await navigator.share({
        title:"Playable Universe attestation photo",
        text:"Save or share this exact photo before leaving the attestation page.",
        files:[selectedPhotoFile]
      });
      photoCustodyStatus.textContent =
        "Phone share sheet opened for the exact selected file.";
      return;
    } catch (err) {
      if (err.name === "AbortError") return;
    }
  }
  downloadBlob(selectedPhotoFile, durablePhotoFilename(selectedPhotoFile));
  photoCustodyStatus.textContent =
    "File sharing was unavailable, so a browser download was offered instead.";
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
      statusEl.textContent =
        "Coarse location attached. Raw precision is not placed in the packet.";
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
  const blob = new Blob(
    [JSON.stringify(obj, null, 2) + "\n"],
    {type:"application/json"}
  );
  downloadBlob(blob, filename);
}

downloadButton.addEventListener("click", () => {
  try {
    const packet = buildPacket();
    lastPacket = packet;
    downloadObject(
      {packet, receipt:lastReceipt, private_custody:lastPrivateCustody},
      "playable-attestation-" +
        new Date().toISOString().replace(/[:.]/g, "-") + ".json"
    );
    statusEl.textContent = "Draft JSON downloaded. This does not submit anything.";
  } catch (err) {
    statusEl.textContent = err.message;
  }
});

async function uploadPrivatePhoto(candidateId, expectedSha, file, statusTarget) {
  if (!file) throw new Error("Choose the exact photo first.");
  const actual = await fileSha256(file);
  if (actual !== expectedSha) {
    throw new Error(
      "This file does not match the SHA-256 sealed into the attestation. Nothing was uploaded."
    );
  }
  statusTarget.textContent =
    "Digest matches. Preserving the exact original in private FC custody…";
  const response = await fetch(
    "../api/v0/attestations/" + encodeURIComponent(candidateId) + "/photo",
    {
      method:"POST",
      headers:{
        "Content-Type": file.type || "image/jpeg",
        "X-Photo-Sha256": expectedSha,
        "X-Evidence-Custody": "private-retain"
      },
      body:file
    }
  );
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || result.error || ("HTTP " + response.status));
  }
  statusTarget.textContent =
    "Exact original preserved privately as " + result.private_media_id +
    ". It is not publicly retrievable.";
  return result;
}

async function requestPublicDerivative(candidateId, expectedSha, statusTarget) {
  statusTarget.textContent =
    "Requesting a metadata-stripped public derivative from the exact private original…";
  const response = await fetch(
    "../api/v0/attestations/" + encodeURIComponent(candidateId) + "/photo/publish",
    {
      method:"POST",
      headers:{
        "X-Photo-Sha256": expectedSha
      }
    }
  );
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || result.error || ("HTTP " + response.status));
  }
  statusTarget.textContent =
    "Derivative " + result.media_id + " is " + result.status +
    ". Local review is required before public display.";
  return result;
}

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
    if (!response.ok) {
      throw new Error(result.detail || result.error || ("HTTP " + response.status));
    }

    lastReceipt = result;
    receiptEmpty.hidden = true;
    receiptCard.hidden = false;
    receiptId.textContent = result.candidate_id;
    receiptTime.textContent = result.received_at;
    packetSha.textContent = result.packet_sha256;
    receiptSha.textContent = result.receipt_sha256;
    receiptPublic.textContent =
      result.public_candidate ? "PUBLIC CANDIDATE" : "RECEIPT ONLY";
    renderGlyph(document.querySelector("#receipt-glyph"), result.receipt_sha256);

    lastPrivateCustody = null;
    publishPhotoPanel.hidden = true;
    publishPhotoStatus.textContent = "";

    if (selectedPhotoFile && photoEvidence && preservePrivate.checked) {
      try {
        lastPrivateCustody = await uploadPrivatePhoto(
          result.candidate_id,
          photoEvidence.sha256,
          selectedPhotoFile,
          photoCustodyStatus
        );
        if (result.public_candidate) {
          publishPhotoPanel.hidden = false;
          publishPhotoStatus.textContent =
            "The exact original is now preserved privately. You may separately request a public derivative.";
        }
        statusEl.textContent =
          "Attest received, receipt created, and exact photo preserved privately.";
      } catch (custodyErr) {
        statusEl.textContent =
          "Attest received, but private photo preservation failed: " +
          custodyErr.message +
          ". The receipt is valid; keep this page open or save the photo before leaving.";
        photoCustodyStatus.textContent = custodyErr.message;
      }
    } else {
      statusEl.textContent = selectedPhotoFile
        ? "Attest received. Photo hash is bound, but the bytes remain only in this browser/device unless you save them."
        : "Attest received. Candidate receipt created.";
    }

    if (result.public_candidate) loadStream();
  } catch (err) {
    statusEl.textContent =
      "Submission failed: " + err.message +
      ". You can still download the draft packet.";
  } finally {
    document.querySelector("#submit-button").disabled = false;
  }
});

publishSelectedPhoto.addEventListener("click", async () => {
  if (!lastReceipt || !photoEvidence) return;
  publishSelectedPhoto.disabled = true;
  try {
    if (!lastPrivateCustody) {
      if (!selectedPhotoFile) {
        throw new Error(
          "The original is not in private custody and is no longer available in this page."
        );
      }
      lastPrivateCustody = await uploadPrivatePhoto(
        lastReceipt.candidate_id,
        photoEvidence.sha256,
        selectedPhotoFile,
        publishPhotoStatus
      );
    }
    await requestPublicDerivative(
      lastReceipt.candidate_id,
      photoEvidence.sha256,
      publishPhotoStatus
    );
    loadStream();
  } catch (err) {
    publishPhotoStatus.textContent = err.message;
  } finally {
    publishSelectedPhoto.disabled = false;
  }
});

copyReceipt.addEventListener("click", async () => {
  if (!lastReceipt) return;
  await navigator.clipboard.writeText(JSON.stringify({
    receipt:lastReceipt,
    private_custody:lastPrivateCustody
  }, null, 2));
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

function photoEvidenceItem(packet) {
  return (packet.evidence || []).find(e => e.kind === "photo_hash") || null;
}

function lifecycleLabel(event) {
  const labels = {
    "candidate.received":"candidate received",
    "evidence.private_custody_received":"exact original preserved privately",
    "evidence.public_derivative_pending":"public derivative pending review",
    "evidence.public_derivative_approved":"public derivative approved",
    "evidence.public_derivative_rejected":"public derivative rejected",
    "evidence.source_unavailable_reported":"source bytes later reported unavailable"
  };
  return labels[event.event_type] || event.event_type;
}

async function loadStream() {
  streamGrid.innerHTML = '<p class="muted">Loading public candidates…</p>';
  try {
    const r = await fetch(
      "../api/v0/attestations/public?limit=30",
      {cache:"no-store"}
    );
    if (!r.ok) throw new Error("HTTP " + r.status);
    const feed = await r.json();
    if (!feed.items.length) {
      streamGrid.innerHTML =
        '<p class="muted">No public field candidates yet. The first one can be made above.</p>';
      return;
    }

    streamGrid.innerHTML = feed.items.map(item => {
      const p = item.packet;
      const who = p.witness.display_name || "Anonymous witness";
      const where = p.location.mode === "coarse"
        ? p.location.latitude.toFixed(3) + ", " +
          p.location.longitude.toFixed(3)
        : "no location";

      const media = item.media || [];
      const photo = media.find(m => m.kind === "public_photo_derivative");
      const evidencePhoto = photoEvidenceItem(p);
      const summary = item.evidence_summary || {};
      const lifecycle = item.lifecycle || [];

      const photoHtml = photo
        ? '<img class="public-photo" loading="lazy" src="' +
          esc(photo.url) +
          '" alt="Published attestation photo derivative">'
        : "";

      let stateHtml = "";
      if ((summary.public_derivative_count || 0) > 0) {
        stateHtml =
          '<span class="evidence-state private">public evidence available</span>';
      } else if ((summary.private_retained_count || 0) > 0) {
        stateHtml =
          '<span class="evidence-state private">exact original preserved privately</span>';
      } else if ((summary.source_unavailable_reported_count || 0) > 0) {
        stateHtml =
          '<span class="evidence-state lost">bound source bytes unavailable</span>';
      } else if (evidencePhoto) {
        stateHtml =
          '<span class="evidence-state">photo hash bound · bytes not retained by FC</span>';
      }

      const attachHtml = (
        !photo &&
        evidencePhoto &&
        (summary.private_retained_count || 0) === 0
      )
        ? '<button class="attach-existing" type="button" data-candidate="' +
          esc(item.candidate_id) +
          '" data-sha="' +
          esc(evidencePhoto.sha256) +
          '">Found the original? Preserve matching photo</button>'
        : "";

      const publishExistingHtml = (
        !photo &&
        evidencePhoto &&
        (summary.private_retained_count || 0) > 0
      )
        ? '<button class="publish-existing-private" type="button" data-candidate="' +
          esc(item.candidate_id) +
          '" data-sha="' +
          esc(evidencePhoto.sha256) +
          '">Request public derivative from private original</button>'
        : "";

      const lifecycleHtml = lifecycle.length
        ? '<div class="lifecycle"><strong>Evidence lifecycle</strong><ul>' +
          lifecycle.slice(-5).map(event =>
            '<li>' +
            esc(new Date(event.recorded_at).toLocaleString()) +
            ' · ' + esc(lifecycleLabel(event)) +
            '</li>'
          ).join("") +
          '</ul></div>'
        : "";

      return '<article class="stream-card">' +
        '<div class="stamp"><span class="unverified">SELF-ATTESTED / UNVERIFIED</span><span>' +
        esc(new Date(item.received_at).toLocaleString()) +
        '</span></div>' +
        photoHtml +
        '<p class="claim">' + esc(p.claim.text) + '</p>' +
        '<p class="meta">' +
        esc(who) + ' · ' +
        esc(p.claim.kind.replaceAll("_"," ")) + ' · ' +
        esc(where) + ' · ' +
        p.evidence.length + ' evidence digest(s)</p>' +
        stateHtml +
        '<code>' + esc(item.candidate_id) + '</code>' +
        attachHtml +
        publishExistingHtml +
        lifecycleHtml +
        '</article>';
    }).join("");
  } catch (err) {
    streamGrid.innerHTML =
      '<p class="muted">Field stream unavailable: ' +
      esc(err.message) + '</p>';
  }
}

streamGrid.addEventListener("click", async event => {
  const publishButton = event.target.closest(".publish-existing-private");
  if (publishButton) {
    publishButton.disabled = true;
    try {
      statusEl.textContent =
        "Requesting public derivative from the privately retained original…";
      await requestPublicDerivative(
        publishButton.dataset.candidate,
        publishButton.dataset.sha,
        statusEl
      );
      await loadStream();
    } catch (err) {
      statusEl.textContent = err.message;
    } finally {
      publishButton.disabled = false;
    }
    return;
  }

  const button = event.target.closest(".attach-existing");
  if (!button) return;
  existingPhotoCandidate.value = button.dataset.candidate;
  existingPhotoSha.value = button.dataset.sha;
  existingPhotoLabel.textContent =
    button.dataset.candidate +
    " · expected SHA-256 " +
    button.dataset.sha;
  existingPhotoFile.value = "";
  existingPhotoStatus.textContent =
    "Choose the exact original photo whose digest was sealed into this candidate.";
  existingPhotoPublish.hidden = true;
  existingPrivateReady = false;
  existingPhotoPanel.hidden = false;
  existingPhotoPanel.scrollIntoView({behavior:"smooth", block:"center"});
});

existingPhotoUpload.addEventListener("click", async () => {
  const candidateId = existingPhotoCandidate.value;
  const expected = existingPhotoSha.value;
  const file = existingPhotoFile.files && existingPhotoFile.files[0];
  existingPhotoUpload.disabled = true;
  try {
    await uploadPrivatePhoto(
      candidateId,
      expected,
      file,
      existingPhotoStatus
    );
    existingPrivateReady = true;
    existingPhotoPublish.hidden = false;
    existingPhotoStatus.textContent +=
      " You can now request a public derivative without uploading the original again.";
    loadStream();
  } catch (err) {
    existingPhotoStatus.textContent = err.message;
  } finally {
    existingPhotoUpload.disabled = false;
  }
});

existingPhotoPublish.addEventListener("click", async () => {
  if (!existingPrivateReady) return;
  existingPhotoPublish.disabled = true;
  try {
    await requestPublicDerivative(
      existingPhotoCandidate.value,
      existingPhotoSha.value,
      existingPhotoStatus
    );
    loadStream();
  } catch (err) {
    existingPhotoStatus.textContent = err.message;
  } finally {
    existingPhotoPublish.disabled = false;
  }
});

refreshStream.addEventListener("click", loadStream);
loadStream();
