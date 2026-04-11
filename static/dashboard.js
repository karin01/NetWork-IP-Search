const currentHostIpElement = document.getElementById("current-host-ip");
const networkCidrElement = document.getElementById("network-cidr");
const scannedAtElement = document.getElementById("scanned-at");
const onlineCountElement = document.getElementById("online-count");
const offlineCountElement = document.getElementById("offline-count");
const totalCountElement = document.getElementById("total-count");
const deviceTableBodyElement = document.getElementById("device-table-body");
const refreshButtonElement = document.getElementById("refresh-button");
const exportCsvButtonElement = document.getElementById("export-csv-button");
const fingerprintButtonElement = document.getElementById("fingerprint-button");
const errorMessageElement = document.getElementById("error-message");
const warningMessageElement = document.getElementById("warning-message");
const historyChartElement = document.getElementById("history-chart");
const logAnalyzeFormElement = document.getElementById("log-analyze-form");
const logAnalyzeButtonElement = document.getElementById("log-analyze-button");
const logSummaryBoxElement = document.getElementById("log-summary-box");
const automationRunButtonElement = document.getElementById("automation-run-button");
const automationResultBoxElement = document.getElementById("automation-result-box");
const instructionInputElement = document.getElementById("instruction-input");
const inventoryInputElement = document.getElementById("inventory-input");
const dryRunInputElement = document.getElementById("dry-run-input");
const fpTargetCountElement = document.getElementById("fp-target-count");
const fpSuccessCountElement = document.getElementById("fp-success-count");
const fpFailureCountElement = document.getElementById("fp-failure-count");
const fpSuccessRateElement = document.getElementById("fp-success-rate");
const fpFailureReasonsElement = document.getElementById("fp-failure-reasons");
const wifiRefreshButtonElement = document.getElementById("wifi-refresh-button");
const wifiInterfacesElement = document.getElementById("wifi-interfaces");
const wifiMessageElement = document.getElementById("wifi-message");
const wifiNoteElement = document.getElementById("wifi-note");
const wifiIperfButtonElement = document.getElementById("wifi-iperf-button");
const wifiIperfHostElement = document.getElementById("wifi-iperf-host");
const wifiIperfPortElement = document.getElementById("wifi-iperf-port");
const wifiIperfDurationElement = document.getElementById("wifi-iperf-duration");
const wifiIperfResultElement = document.getElementById("wifi-iperf-result");
const wifiAnalyzeButtonElement = document.getElementById("wifi-analyze-button");
const wifiAnalyzeRefreshCheckbox = document.getElementById("wifi-analyze-refresh-netsh");
const wifiAnalyzeMessageElement = document.getElementById("wifi-analyze-message");
const wifiAnalyzeMetaElement = document.getElementById("wifi-analyze-meta");
const wifiAnalyzeSummaryElement = document.getElementById("wifi-analyze-summary");
const wifiAnalyzeTbodyElement = document.getElementById("wifi-analyze-tbody");
const wifiAnalyzeDisclaimerElement = document.getElementById("wifi-analyze-disclaimer");
const wifiChannelChart24Element = document.getElementById("wifi-channel-chart-24");
const wifiChannelChart5Element = document.getElementById("wifi-channel-chart-5");
const wifiChannelChartCaption24Element = document.getElementById("wifi-channel-chart-caption-24");
const wifiChannelChartCaption5Element = document.getElementById("wifi-channel-chart-caption-5");
const wifiSsidFilterInput = document.getElementById("wifi-ssid-filter");
const wifiSsidFilterClearButton = document.getElementById("wifi-ssid-filter-clear");
const wifiSsidDatalistElement = document.getElementById("wifi-ssid-datalist");
const wifiBandFilterSelect = document.getElementById("wifi-band-filter");
const wifiBssidFilterInput = document.getElementById("wifi-bssid-filter");
const wifiAnalyzeCsvButton = document.getElementById("wifi-analyze-csv-button");
const wifiAnalyzeTheadElement = document.getElementById("wifi-analyze-thead");
const wifiAnalyzeKeepFiltersCheckbox = document.getElementById("wifi-analyze-keep-filters");
const wifiAnalyzeFilterConnectedButton = document.getElementById("wifi-analyze-filter-connected");
const wifiAnalyzeJsonButton = document.getElementById("wifi-analyze-json-button");
const wifiAnalyzeCopyTsvButton = document.getElementById("wifi-analyze-copy-tsv-button");
const wifiAnalyzeToastElement = document.getElementById("wifi-analyze-toast");
const historySnapshotSelectElement = document.getElementById("history-snapshot-select");
const historyDiffButtonElement = document.getElementById("history-diff-button");
const historySnapshotsRefreshElement = document.getElementById("history-snapshots-refresh");
const historyDiffResultElement = document.getElementById("history-diff-result");

/** 장치 스캔·테이블이 있는 메인 대시보드(/)인지 — /wifi 는 Wi-Fi 카드만 있어 API 폴링·리스너를 건너뜁니다. */
const isMainDeviceDashboard = Boolean(refreshButtonElement && deviceTableBodyElement);

// WHY: NETWORK_IP_SEARCH_TOKEN 사용 시 브라우저가 API를 호출할 수 있도록 헤더에 실어 보냅니다.
function nwipCaptureTokenFromUrl() {
  try {
    const t = new URLSearchParams(window.location.search).get("token");
    if (t) {
      sessionStorage.setItem("nwip_token", t);
    }
  } catch (e) {
    /* ignore */
  }
}

function nwipToken() {
  try {
    return sessionStorage.getItem("nwip_token") || "";
  } catch (e) {
    return "";
  }
}

function nwipAuthHeaders() {
  const t = nwipToken();
  return t ? { "X-NetWork-IP-Token": t } : {};
}

/** 인증 헤더를 합친 fetch (API 호출용). */
function nwipFetch(url, options = {}) {
  const headers = { ...nwipAuthHeaders(), ...(options.headers || {}) };
  return fetch(url, { ...options, headers });
}

/** 마지막으로 성공한 Wi-Fi 분석 API 응답(필터·차트 재계산용). */
let lastWifiAnalyzePayload = null;
let lastWifiConnectedHint = null;
let wifiAnalyzeFilterDebounceId = 0;
let wifiAnalyzeToastTimerId = 0;
/** 테이블 정렬: text 컬럼은 기본 asc, 숫자는 desc. */
let wifiTableSort = { key: "signal", dir: "desc" };

function showWifiAnalyzeToast(messageText) {
  if (!wifiAnalyzeToastElement) {
    return;
  }
  wifiAnalyzeToastElement.textContent = messageText;
  wifiAnalyzeToastElement.classList.remove("hidden");
  clearTimeout(wifiAnalyzeToastTimerId);
  wifiAnalyzeToastTimerId = window.setTimeout(() => {
    wifiAnalyzeToastElement.classList.add("hidden");
  }, 2200);
}

/** merge=1 응답의 connected_hint로 「연결 SSID로」 버튼 활성화. */
function updateWifiAnalyzeConnectedButton() {
  if (!wifiAnalyzeFilterConnectedButton) {
    return;
  }
  const h = lastWifiConnectedHint;
  const ssid = h && typeof h.ssid === "string" ? h.ssid.trim() : "";
  const usable = Boolean(ssid && ssid !== "—");
  wifiAnalyzeFilterConnectedButton.disabled = !usable;
}

/** 신호 열: 퍼센트 막대 + 숫자. */
function buildWifiSignalCell(ap) {
  const td = document.createElement("td");
  const pct = ap.signal_percent;
  if (pct != null && !Number.isNaN(Number(pct))) {
    const wrap = document.createElement("div");
    wrap.className = "wifi-signal-cell";
    const bar = document.createElement("div");
    bar.className = "wifi-signal-bar";
    bar.style.width = `${Math.min(100, Math.max(0, Number(pct)))}%`;
    const lab = document.createElement("span");
    lab.className = "wifi-signal-label";
    lab.textContent = `${pct}%`;
    wrap.appendChild(bar);
    wrap.appendChild(lab);
    td.appendChild(wrap);
  } else {
    const wrap = document.createElement("div");
    wrap.className = "wifi-signal-cell wifi-signal-cell--empty";
    wrap.textContent = ap.raw_signal || "—";
    td.appendChild(wrap);
  }
  return td;
}

/** netsh 기반 Wi-Fi 상태를 카드에 그립니다. WHY: XSS 방지를 위해 DOM API로만 텍스트를 넣습니다. */
function renderWifiStatus(data) {
  if (!wifiInterfacesElement || !wifiMessageElement || !wifiNoteElement) {
    return;
  }

  wifiInterfacesElement.innerHTML = "";
  wifiMessageElement.textContent = "";
  wifiMessageElement.classList.add("hidden");
  wifiMessageElement.classList.remove("wifi-message--error");
  wifiNoteElement.textContent = "";

  if (!data || !data.ok) {
    wifiMessageElement.textContent = (data && data.message) || "Wi-Fi 정보를 가져오지 못했습니다.";
    wifiMessageElement.classList.remove("hidden");
    wifiMessageElement.classList.add("wifi-message--error");
    if (!(data && data.message)) {
      const emptyHint = document.createElement("p");
      emptyHint.style.cssText = "padding:0 1.2rem;color:var(--tx-dim);font-size:0.82rem;";
      emptyHint.textContent = "Windows에서 netsh를 사용할 수 있는지 확인하세요.";
      wifiInterfacesElement.appendChild(emptyHint);
    }
    return;
  }

  if (data.message) {
    wifiMessageElement.textContent = data.message;
    wifiMessageElement.classList.remove("hidden");
  }

  wifiNoteElement.textContent = data.note || "";

  const ifaceList = data.interfaces || [];
  if (!ifaceList.length && !data.message) {
    const emptyElement = document.createElement("p");
    emptyElement.style.cssText = "padding:0 1.2rem;color:var(--tx-dim);font-size:0.82rem;";
    emptyElement.textContent = "표시할 무선 인터페이스가 없습니다.";
    wifiInterfacesElement.appendChild(emptyElement);
    return;
  }
  if (!ifaceList.length) {
    return;
  }

  for (const iface of ifaceList) {
    const cardElement = document.createElement("div");
    cardElement.className = "wifi-iface";

    const titleElement = document.createElement("div");
    titleElement.className = "wifi-iface-title";
    titleElement.textContent = iface.adapter_name || "Wi-Fi";
    cardElement.appendChild(titleElement);

    const dlElement = document.createElement("dl");
    dlElement.className = "wifi-iface-grid";

    function appendRow(labelText, valueText) {
      const dtElement = document.createElement("dt");
      dtElement.textContent = labelText;
      const ddElement = document.createElement("dd");
      ddElement.textContent = valueText != null && valueText !== "" ? String(valueText) : "—";
      dlElement.appendChild(dtElement);
      dlElement.appendChild(ddElement);
    }

    appendRow("SSID", iface.ssid);
    appendRow("상태", iface.state);
    appendRow(
      "신호",
      iface.signal_percent != null ? `${iface.signal_percent}%` : iface.raw_signal || "—",
    );
    appendRow(
      "수신(Mbps)",
      iface.receive_mbps != null ? String(iface.receive_mbps) : iface.raw_receive || "—",
    );
    appendRow(
      "송신(Mbps)",
      iface.transmit_mbps != null ? String(iface.transmit_mbps) : iface.raw_transmit || "—",
    );
    appendRow("라디오", iface.radio_type);
    appendRow("채널", iface.channel);

    cardElement.appendChild(dlElement);
    wifiInterfacesElement.appendChild(cardElement);
  }
}

async function fetchWifiStatus() {
  if (wifiRefreshButtonElement) {
    wifiRefreshButtonElement.disabled = true;
  }
  try {
    const response = await nwipFetch("/api/wifi/status");
    const payload = await response.json();
    if (!payload.ok) {
      renderWifiStatus({ ok: false, message: payload.error || "API 오류" });
      return;
    }
    renderWifiStatus(payload.data);
  } catch (error) {
    renderWifiStatus({ ok: false, message: error.message || "네트워크 오류" });
  } finally {
    if (wifiRefreshButtonElement) {
      wifiRefreshButtonElement.disabled = false;
    }
  }
}

if (wifiRefreshButtonElement) {
  wifiRefreshButtonElement.addEventListener("click", fetchWifiStatus);
}

if (wifiIperfButtonElement) {
  wifiIperfButtonElement.addEventListener("click", async () => {
    const hostValue = wifiIperfHostElement?.value?.trim() || "";
    const portValue = Number(wifiIperfPortElement?.value) || 5201;
    const durationValue = Number(wifiIperfDurationElement?.value) || 5;

    if (!hostValue) {
      if (wifiIperfResultElement) {
        wifiIperfResultElement.textContent = "iperf3 서버 IP를 입력하세요.";
      }
      return;
    }

    wifiIperfButtonElement.disabled = true;
    if (wifiIperfResultElement) {
      wifiIperfResultElement.textContent = "iperf3 실행 중...";
    }
    try {
      const response = await nwipFetch("/api/wifi/iperf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          host: hostValue,
          port: portValue,
          duration_seconds: durationValue,
        }),
      });
      const payload = await response.json();
      if (!payload.ok) {
        if (wifiIperfResultElement) {
          wifiIperfResultElement.textContent = payload.error || "iperf3 실패";
        }
        return;
      }
      const row = payload.data;
      if (wifiIperfResultElement) {
        wifiIperfResultElement.textContent = [
          `호스트 ${row.host}:${row.port} (${row.duration_seconds}s)`,
          `송신 ${row.send_mbps} Mbps / 수신 ${row.receive_mbps} Mbps`,
          `측정 시각: ${row.measured_at}`,
        ].join("\n");
      }
    } catch (error) {
      if (wifiIperfResultElement) {
        wifiIperfResultElement.textContent = `오류: ${error.message || "iperf3 요청 실패"}`;
      }
    } finally {
      wifiIperfButtonElement.disabled = false;
    }
  });
}

/** 채널 번호에 따른 막대 색 (2.4 / 5 / 기타). */
function wifiChannelBarColor(channelNum) {
  if (channelNum >= 1 && channelNum <= 14) {
    return "#22c55e";
  }
  if (channelNum >= 36 && channelNum <= 177) {
    return "#60a5fa";
  }
  return "#a78bfa";
}

/** AP의 밴드 분류(채널 우선, 없으면 band 문자열). */
function wifiApBandCategory(ap) {
  const ch = ap.channel_int;
  if (ch != null) {
    if (ch >= 1 && ch <= 14) {
      return "2.4";
    }
    if (ch >= 36 && ch <= 177) {
      return "5";
    }
    if (ch > 177 || (ch > 14 && ch < 36)) {
      return "6";
    }
  }
  const b = (ap.band || "").toLowerCase().replace(/\s/g, "");
  if (b.includes("2.4")) {
    return "2.4";
  }
  if (b.includes("6ghz") || b === "6") {
    return "6";
  }
  if (b.includes("5ghz") || (b.includes("5") && !b.includes("2.4"))) {
    return "5";
  }
  return "unknown";
}

/** 스캔된 SSID 목록을 datalist에 채워 자동완성을 돕습니다. */
function updateWifiSsidDatalist(accessPointList) {
  if (!wifiSsidDatalistElement) {
    return;
  }
  wifiSsidDatalistElement.innerHTML = "";
  const seen = new Set();
  for (const ap of accessPointList) {
    const name = ap.ssid;
    if (!name || name === "(숨김 SSID)" || seen.has(name)) {
      continue;
    }
    seen.add(name);
    const opt = document.createElement("option");
    opt.value = name;
    wifiSsidDatalistElement.appendChild(opt);
  }
}

/** 현재 입력된 필터 요약 문자열(캡션·CSV 파일명용). */
function getWifiAnalyzeFilterSummary() {
  const parts = [];
  const ssidQ = (wifiSsidFilterInput?.value || "").trim();
  if (ssidQ) {
    parts.push(`SSID:${ssidQ}`);
  }
  const bssidQ = (wifiBssidFilterInput?.value || "").trim();
  if (bssidQ) {
    parts.push(`BSSID:${bssidQ}`);
  }
  const bandVal = wifiBandFilterSelect?.value || "all";
  if (bandVal !== "all") {
    parts.push(`밴드:${bandVal}`);
  }
  return parts.join(" ");
}

/** SSID·BSSID·밴드 필터를 모두 적용한 AP 목록. */
function getWifiFilteredAccessPoints() {
  if (!lastWifiAnalyzePayload || !lastWifiAnalyzePayload.ok) {
    return [];
  }
  let list = lastWifiAnalyzePayload.access_points || [];

  const ssidQ = (wifiSsidFilterInput?.value || "").trim().toLowerCase();
  if (ssidQ) {
    list = list.filter((ap) => (ap.ssid || "").toLowerCase().includes(ssidQ));
  }

  const bssidRaw = (wifiBssidFilterInput?.value || "").trim().toLowerCase().replace(/[^a-f0-9]/g, "");
  if (bssidRaw) {
    list = list.filter((ap) => {
      const mac = (ap.bssid || "").toLowerCase().replace(/[^a-f0-9]/g, "");
      return mac.includes(bssidRaw);
    });
  }

  const bandSel = wifiBandFilterSelect?.value || "all";
  if (bandSel === "2.4") {
    list = list.filter((ap) => wifiApBandCategory(ap) === "2.4");
  } else if (bandSel === "5") {
    list = list.filter((ap) => wifiApBandCategory(ap) === "5");
  } else if (bandSel === "6") {
    list = list.filter((ap) => {
      const c = wifiApBandCategory(ap);
      return c === "6" || c === "unknown";
    });
  }

  return list;
}

function hasWifiAnalyzeActiveFilters() {
  return getWifiAnalyzeFilterSummary().length > 0;
}

/** 2.4 또는 5 GHz 구간만 집계한 막대 그래프. */
function drawWifiBandHistogram(canvas, captionElement, accessPointList, bandKey, filterSummary) {
  if (!canvas) {
    return;
  }
  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }

  const wrap = canvas.parentElement;
  const logicalWidth = Math.max(260, (wrap && wrap.clientWidth) || 360);
  const logicalHeight = Number(canvas.getAttribute("height")) || 172;
  const dpr = typeof window.devicePixelRatio === "number" && window.devicePixelRatio > 1 ? window.devicePixelRatio : 1;
  canvas.width = Math.floor(logicalWidth * dpr);
  canvas.height = Math.floor(logicalHeight * dpr);
  canvas.style.width = `${logicalWidth}px`;
  canvas.style.height = `${logicalHeight}px`;
  context.setTransform(dpr, 0, 0, dpr, 0, 0);

  context.fillStyle = "#0d1526";
  context.fillRect(0, 0, logicalWidth, logicalHeight);

  const chMin = bandKey === "2.4" ? 1 : 36;
  const chMax = bandKey === "2.4" ? 14 : 177;
  const barColor = bandKey === "2.4" ? "#22c55e" : "#60a5fa";

  const counts = {};
  for (const ap of accessPointList) {
    const ch = ap.channel_int;
    if (ch == null || ch < chMin || ch > chMax) {
      continue;
    }
    counts[ch] = (counts[ch] || 0) + 1;
  }
  const entries = Object.entries(counts)
    .map(([ch, cnt]) => [Number(ch), cnt])
    .sort((a, b) => a[0] - b[0]);

  if (!entries.length) {
    context.fillStyle = "#64748b";
    context.font = "12px system-ui, sans-serif";
    let msg = "먼저 「주변 AP 스캔」을 실행하세요.";
    if (accessPointList.length === 0 && lastWifiAnalyzePayload && lastWifiAnalyzePayload.message) {
      msg = lastWifiAnalyzePayload.message;
    } else if (accessPointList.length === 0 && lastWifiAnalyzePayload && lastWifiAnalyzePayload.ok) {
      msg = "표시할 AP가 없습니다.";
    } else if (hasWifiAnalyzeActiveFilters()) {
      msg = "필터 결과에 이 밴드·채널 데이터가 없습니다.";
    } else {
      msg = bandKey === "2.4" ? "2.4 GHz AP가 없거나 채널 정보가 없습니다." : "5 GHz AP가 없거나 채널 정보가 없습니다.";
    }
    context.fillText(msg, 12, logicalHeight / 2);
    if (captionElement) {
      captionElement.textContent = "";
    }
    return;
  }

  const maxVal = Math.max(...entries.map((e) => e[1]), 1);
  const paddingLeft = 34;
  const paddingRight = 8;
  const paddingTop = 18;
  const paddingBottom = 26;
  const graphWidth = logicalWidth - paddingLeft - paddingRight;
  const graphHeight = logicalHeight - paddingTop - paddingBottom;
  const barGap = 2;
  const n = entries.length;
  const barWidth = Math.max(2, (graphWidth - barGap * Math.max(0, n - 1)) / n);

  context.strokeStyle = "#334155";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(paddingLeft, paddingTop);
  context.lineTo(paddingLeft, paddingTop + graphHeight);
  context.lineTo(logicalWidth - paddingRight, paddingTop + graphHeight);
  context.stroke();

  context.strokeStyle = "rgba(51, 65, 85, 0.5)";
  for (let gi = 1; gi <= 3; gi += 1) {
    const gy = paddingTop + (graphHeight * gi) / 4;
    context.beginPath();
    context.moveTo(paddingLeft, gy);
    context.lineTo(logicalWidth - paddingRight, gy);
    context.stroke();
  }

  context.fillStyle = "#475569";
  context.font = "10px system-ui, sans-serif";
  context.textAlign = "right";
  context.fillText(String(maxVal), paddingLeft - 4, paddingTop + 10);

  entries.forEach(([channelNum, cnt], index) => {
    const x = paddingLeft + index * (barWidth + barGap);
    const barHeight = (cnt / maxVal) * graphHeight;
    const y = paddingTop + graphHeight - barHeight;
    context.fillStyle = barColor;
    context.fillRect(x, y, barWidth, barHeight);
    if (barWidth >= 10 && cnt > 0 && barHeight > 14) {
      context.fillStyle = "#e2e8f0";
      context.font = "bold 9px system-ui, sans-serif";
      context.textAlign = "center";
      context.fillText(String(cnt), x + barWidth / 2, y - 4);
    }
    context.fillStyle = "#94a3b8";
    context.font = "9px system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(String(channelNum), x + barWidth / 2, logicalHeight - 8);
  });

  if (captionElement) {
    const total = accessPointList.length;
    const inBand = accessPointList.filter((ap) => {
      const ch = ap.channel_int;
      return ch != null && ch >= chMin && ch <= chMax;
    }).length;
    const extra = filterSummary ? ` · ${filterSummary}` : "";
    captionElement.textContent = `표시 AP ${total}개 중 이 밴드(채널 표시) ${inBand}개${extra}`;
  }
}

function clearWifiBandCharts() {
  drawWifiBandHistogram(wifiChannelChart24Element, wifiChannelChartCaption24Element, [], "2.4", "");
  drawWifiBandHistogram(wifiChannelChart5Element, wifiChannelChartCaption5Element, [], "5", "");
}

/** 테이블 정렬 적용. */
function sortWifiAccessPoints(list, sortState) {
  const mul = sortState.dir === "asc" ? 1 : -1;
  const key = sortState.key;
  return [...list].sort((a, b) => {
    let cmp = 0;
    switch (key) {
      case "ssid":
        cmp = (a.ssid || "").localeCompare(b.ssid || "", "ko");
        break;
      case "bssid":
        cmp = (a.bssid || "").localeCompare(b.bssid || "", "en");
        break;
      case "signal": {
        const sa = a.signal_percent != null ? a.signal_percent : -1;
        const sb = b.signal_percent != null ? b.signal_percent : -1;
        cmp = sa - sb;
        break;
      }
      case "channel": {
        const ca = a.channel_int != null ? a.channel_int : -1;
        const cb = b.channel_int != null ? b.channel_int : -1;
        cmp = ca - cb;
        break;
      }
      case "band":
        cmp = (a.band || "").localeCompare(b.band || "", "ko");
        break;
      case "radio":
        cmp = (a.radio_type || "").localeCompare(b.radio_type || "", "en");
        break;
      case "auth":
        cmp = (a.authentication || "").localeCompare(b.authentication || "", "ko");
        break;
      default:
        cmp = 0;
    }
    return mul * cmp;
  });
}

function updateWifiAnalyzeSortHeaderStyles() {
  if (!wifiAnalyzeTheadElement) {
    return;
  }
  const heads = wifiAnalyzeTheadElement.querySelectorAll("[data-wifi-sort]");
  heads.forEach((th) => {
    th.classList.remove("wifi-th--active", "wifi-th--asc", "wifi-th--desc");
    if (th.getAttribute("data-wifi-sort") === wifiTableSort.key) {
      th.classList.add("wifi-th--active");
      th.classList.add(wifiTableSort.dir === "asc" ? "wifi-th--asc" : "wifi-th--desc");
    }
  });
}

/** 필터 반영 후 테이블·듀얼 차트를 다시 그립니다. */
function fillWifiAnalyzeTable(accessPointList, filterActive, serverMessage) {
  if (!wifiAnalyzeTbodyElement) {
    return;
  }
  wifiAnalyzeTbodyElement.innerHTML = "";

  if (!accessPointList.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    if (filterActive) {
      cell.textContent = "필터와 일치하는 AP가 없습니다.";
    } else if (serverMessage) {
      cell.textContent = "스캔 결과에 AP 목록이 없습니다.";
    } else {
      cell.textContent = "주변에 보이는 AP가 없습니다.";
    }
    row.appendChild(cell);
    wifiAnalyzeTbodyElement.appendChild(row);
    return;
  }

  for (const ap of accessPointList) {
    const row = document.createElement("tr");

    const ssidTd = document.createElement("td");
    ssidTd.textContent = ap.ssid || "—";
    row.appendChild(ssidTd);

    const bssidTd = document.createElement("td");
    bssidTd.textContent = ap.bssid || "—";
    row.appendChild(bssidTd);

    row.appendChild(buildWifiSignalCell(ap));

    const channelTd = document.createElement("td");
    channelTd.textContent = ap.channel_int != null ? String(ap.channel_int) : ap.raw_channel || "—";
    row.appendChild(channelTd);

    const bandTd = document.createElement("td");
    bandTd.textContent = ap.band || "—";
    row.appendChild(bandTd);

    const radioTd = document.createElement("td");
    radioTd.textContent = ap.radio_type || "—";
    row.appendChild(radioTd);

    const authTd = document.createElement("td");
    authTd.textContent = ap.authentication || "—";
    row.appendChild(authTd);

    wifiAnalyzeTbodyElement.appendChild(row);
  }
}

function applyWifiAnalyzeView() {
  const filtered = getWifiFilteredAccessPoints();
  const sorted = sortWifiAccessPoints(filtered, wifiTableSort);
  const filterSummary = getWifiAnalyzeFilterSummary();
  const serverMessage = lastWifiAnalyzePayload && lastWifiAnalyzePayload.message;
  fillWifiAnalyzeTable(sorted, hasWifiAnalyzeActiveFilters(), serverMessage);
  updateWifiAnalyzeSortHeaderStyles();
  drawWifiBandHistogram(wifiChannelChart24Element, wifiChannelChartCaption24Element, filtered, "2.4", filterSummary);
  drawWifiBandHistogram(wifiChannelChart5Element, wifiChannelChartCaption5Element, filtered, "5", filterSummary);
}

/** 현재 필터·정렬 기준으로 CSV 파일을 내려받습니다. */
function exportWifiAnalyzeCsv() {
  const filtered = sortWifiAccessPoints(getWifiFilteredAccessPoints(), wifiTableSort);
  if (!filtered.length) {
    window.alert("보낼 AP가 없습니다. 스캔 후 필터를 확인하세요.");
    return;
  }
  const headers = ["ssid", "bssid", "signal_percent", "channel_int", "band", "radio_type", "authentication"];
  const esc = (val) => {
    const s = val == null ? "" : String(val);
    if (/[",\n\r]/.test(s)) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };
  const lines = [headers.join(",")];
  for (const ap of filtered) {
    lines.push(headers.map((h) => esc(ap[h])).join(","));
  }
  const blob = new Blob([`\ufeff${lines.join("\n")}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  anchor.href = url;
  anchor.download = `wifi_scan_${stamp}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
  showWifiAnalyzeToast("CSV 파일을 저장했습니다.");
}

/** 필터·정렬이 반영된 AP 목록을 JSON으로 저장합니다. */
function exportWifiAnalyzeJson() {
  const filtered = sortWifiAccessPoints(getWifiFilteredAccessPoints(), wifiTableSort);
  if (!filtered.length) {
    window.alert("저장할 AP가 없습니다. 스캔 후 필터를 확인하세요.");
    return;
  }
  const payload = {
    exported_at: new Date().toISOString(),
    filter_summary: getWifiAnalyzeFilterSummary() || null,
    sort: { ...wifiTableSort },
    measured_at: lastWifiAnalyzePayload?.measured_at ?? null,
    access_points: filtered,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  anchor.href = url;
  anchor.download = `wifi_scan_${stamp}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
  showWifiAnalyzeToast("JSON 파일을 저장했습니다.");
}

/** 표 내용을 탭 구분(TSV)으로 클립보드에 복사합니다. */
async function copyWifiAnalyzeTableTsv() {
  const filtered = sortWifiAccessPoints(getWifiFilteredAccessPoints(), wifiTableSort);
  if (!filtered.length) {
    window.alert("복사할 행이 없습니다.");
    return;
  }
  const headerLine = ["SSID", "BSSID", "신호%", "채널", "밴드", "라디오", "인증"].join("\t");
  const lines = [headerLine];
  for (const ap of filtered) {
    const cells = [
      ap.ssid ?? "",
      ap.bssid ?? "",
      ap.signal_percent != null ? String(ap.signal_percent) : "",
      ap.channel_int != null ? String(ap.channel_int) : "",
      ap.band ?? "",
      ap.radio_type ?? "",
      ap.authentication ?? "",
    ];
    lines.push(cells.join("\t"));
  }
  const text = lines.join("\n");
  try {
    await navigator.clipboard.writeText(text);
    showWifiAnalyzeToast("클립보드에 표를 복사했습니다.");
  } catch {
    window.alert("클립보드 복사에 실패했습니다. 브라우저 권한을 확인하세요.");
  }
}

/** Wi-Fi 분석기: 요약 칩·필터·채널 차트·AP 테이블을 채웁니다. */
function renderWifiAnalyze(data) {
  if (
    !wifiAnalyzeMessageElement ||
    !wifiAnalyzeMetaElement ||
    !wifiAnalyzeSummaryElement ||
    !wifiAnalyzeTbodyElement ||
    !wifiAnalyzeDisclaimerElement
  ) {
    return;
  }

  lastWifiAnalyzePayload = null;
  lastWifiConnectedHint = null;
  updateWifiAnalyzeConnectedButton();
  if (wifiAnalyzeToastElement) {
    wifiAnalyzeToastElement.classList.add("hidden");
  }
  wifiAnalyzeMessageElement.textContent = "";
  wifiAnalyzeMessageElement.classList.add("hidden");
  wifiAnalyzeMessageElement.classList.remove("wifi-analyze-banner--error", "wifi-analyze-banner--ok");
  wifiAnalyzeMetaElement.textContent = "";
  wifiAnalyzeSummaryElement.innerHTML = "";
  wifiAnalyzeTbodyElement.innerHTML = "";
  wifiAnalyzeDisclaimerElement.textContent = "";
  if (wifiSsidDatalistElement) {
    wifiSsidDatalistElement.innerHTML = "";
  }
  clearWifiBandCharts();

  if (!data) {
    wifiAnalyzeMessageElement.textContent = "데이터가 없습니다.";
    wifiAnalyzeMessageElement.classList.remove("hidden");
    wifiAnalyzeMessageElement.classList.add("wifi-analyze-banner--error");
    return;
  }

  if (!data.ok) {
    wifiAnalyzeMessageElement.textContent = data.message || "스캔에 실패했습니다.";
    wifiAnalyzeMessageElement.classList.remove("hidden");
    wifiAnalyzeMessageElement.classList.add("wifi-analyze-banner--error");
    return;
  }

  lastWifiAnalyzePayload = data;
  lastWifiConnectedHint = data.connected_hint || null;
  updateWifiAnalyzeConnectedButton();

  const keepFilters = Boolean(wifiAnalyzeKeepFiltersCheckbox?.checked);
  if (!keepFilters) {
    wifiTableSort = { key: "signal", dir: "desc" };
    if (wifiSsidFilterInput) {
      wifiSsidFilterInput.value = "";
    }
    if (wifiBssidFilterInput) {
      wifiBssidFilterInput.value = "";
    }
    if (wifiBandFilterSelect) {
      wifiBandFilterSelect.value = "all";
    }
  }

  if (data.message) {
    wifiAnalyzeMessageElement.textContent = data.message;
    wifiAnalyzeMessageElement.classList.remove("hidden");
    wifiAnalyzeMessageElement.classList.add("wifi-analyze-banner--ok");
  }

  wifiAnalyzeMetaElement.textContent = [data.note || "", data.measured_at ? `측정: ${data.measured_at}` : ""]
    .filter(Boolean)
    .join(" · ");

  const analysis = data.analysis || {};
  const chip = (label, value) => {
    const wrap = document.createElement("span");
    wrap.className = "wifi-analyze-chip";
    const lb = document.createElement("span");
    lb.textContent = `${label} `;
    const strong = document.createElement("strong");
    strong.textContent = value;
    wrap.appendChild(lb);
    wrap.appendChild(strong);
    wifiAnalyzeSummaryElement.appendChild(wrap);
  };

  chip("탐지 AP", String(analysis.total_aps ?? 0));

  const strongest = analysis.strongest_ap;
  if (strongest && strongest.signal_percent != null) {
    chip("최강 신호", `${strongest.ssid} (${strongest.signal_percent}%)`);
  }

  const rec24 = analysis.recommended_24ghz_channels || [];
  if (rec24.length) {
    const best = rec24[0];
    chip("2.4GHz 추천(참고)", `Ch ${best.channel} (점수 ${best.overlap_score})`);
  }

  const byBand = analysis.by_band || {};
  const bandStr = Object.entries(byBand)
    .map(([k, v]) => `${k} ${v}`)
    .join(" · ");
  if (bandStr) {
    chip("밴드별", bandStr);
  }

  if (data.connected_hint) {
    const h = data.connected_hint;
    const parts = [
      `연결 SSID: ${h.ssid}`,
      h.channel_int != null ? `채널 ${h.channel_int}` : "",
      `동일 채널 AP ${h.access_points_on_same_channel ?? 0}개`,
    ].filter(Boolean);
    chip("내 연결", parts.join(" / "));
    if (h.hint) {
      const hintEl = document.createElement("p");
      hintEl.className = "wifi-footnote";
      hintEl.style.marginTop = "0.35rem";
      hintEl.style.width = "100%";
      hintEl.textContent = h.hint;
      wifiAnalyzeSummaryElement.appendChild(hintEl);
    }
  }

  wifiAnalyzeDisclaimerElement.textContent = analysis.disclaimer || "";

  const aps = data.access_points || [];
  updateWifiSsidDatalist(aps);
  applyWifiAnalyzeView();
}

async function fetchWifiAnalyze() {
  if (!wifiAnalyzeButtonElement) {
    return;
  }
  const useRefresh = Boolean(wifiAnalyzeRefreshCheckbox?.checked);
  wifiAnalyzeButtonElement.disabled = true;
  try {
    const query = new URLSearchParams({ refresh: useRefresh ? "1" : "0", merge: "1" });
    const response = await nwipFetch(`/api/wifi/analyze?${query.toString()}`);
    const payload = await response.json();
    if (!payload.ok) {
      renderWifiAnalyze({ ok: false, message: payload.error || "API 오류" });
      return;
    }
    renderWifiAnalyze(payload.data);
  } catch (error) {
    renderWifiAnalyze({ ok: false, message: error.message || "네트워크 오류" });
  } finally {
    wifiAnalyzeButtonElement.disabled = false;
  }
}

if (wifiAnalyzeButtonElement) {
  wifiAnalyzeButtonElement.addEventListener("click", fetchWifiAnalyze);
}

/** SSID 필터 입력 디바운스(타이핑 중 과도한 canvas 리페인트 방지). */
function scheduleWifiAnalyzeFilterApply() {
  clearTimeout(wifiAnalyzeFilterDebounceId);
  wifiAnalyzeFilterDebounceId = window.setTimeout(() => {
    applyWifiAnalyzeView();
  }, 200);
}

if (wifiSsidFilterInput) {
  wifiSsidFilterInput.addEventListener("input", scheduleWifiAnalyzeFilterApply);
}

if (wifiSsidFilterClearButton) {
  wifiSsidFilterClearButton.addEventListener("click", () => {
    if (wifiSsidFilterInput) {
      wifiSsidFilterInput.value = "";
    }
    if (wifiBssidFilterInput) {
      wifiBssidFilterInput.value = "";
    }
    if (wifiBandFilterSelect) {
      wifiBandFilterSelect.value = "all";
    }
    wifiTableSort = { key: "signal", dir: "desc" };
    applyWifiAnalyzeView();
  });
}

if (wifiBandFilterSelect) {
  wifiBandFilterSelect.addEventListener("change", () => {
    applyWifiAnalyzeView();
  });
}

if (wifiBssidFilterInput) {
  wifiBssidFilterInput.addEventListener("input", scheduleWifiAnalyzeFilterApply);
}

if (wifiAnalyzeCsvButton) {
  wifiAnalyzeCsvButton.addEventListener("click", exportWifiAnalyzeCsv);
}

if (wifiAnalyzeJsonButton) {
  wifiAnalyzeJsonButton.addEventListener("click", exportWifiAnalyzeJson);
}

if (wifiAnalyzeCopyTsvButton) {
  wifiAnalyzeCopyTsvButton.addEventListener("click", copyWifiAnalyzeTableTsv);
}

if (wifiAnalyzeFilterConnectedButton) {
  wifiAnalyzeFilterConnectedButton.addEventListener("click", () => {
    const h = lastWifiConnectedHint;
    const ssid = h && typeof h.ssid === "string" ? h.ssid.trim() : "";
    if (!ssid || ssid === "—") {
      return;
    }
    if (wifiSsidFilterInput) {
      wifiSsidFilterInput.value = ssid;
    }
    applyWifiAnalyzeView();
    showWifiAnalyzeToast("SSID 필터를 현재 연결 이름으로 맞췄습니다.");
  });
}

if (wifiAnalyzeTheadElement) {
  wifiAnalyzeTheadElement.addEventListener("click", (event) => {
    const th = event.target.closest("[data-wifi-sort]");
    if (!th) {
      return;
    }
    const sortKey = th.getAttribute("data-wifi-sort");
    if (!sortKey) {
      return;
    }
    const numericKeys = new Set(["signal", "channel"]);
    if (wifiTableSort.key === sortKey) {
      wifiTableSort.dir = wifiTableSort.dir === "asc" ? "desc" : "asc";
    } else {
      wifiTableSort.key = sortKey;
      wifiTableSort.dir = numericKeys.has(sortKey) ? "desc" : "asc";
    }
    applyWifiAnalyzeView();
  });
}

let wifiChartResizeTimerId = 0;
window.addEventListener("resize", () => {
  if (!lastWifiAnalyzePayload || !lastWifiAnalyzePayload.ok) {
    return;
  }
  clearTimeout(wifiChartResizeTimerId);
  wifiChartResizeTimerId = window.setTimeout(() => {
    applyWifiAnalyzeView();
  }, 150);
});

function buildStatusBadge(statusValue) {
  const badgeElement = document.createElement("span");
  badgeElement.classList.add("status-badge");

  if (statusValue === "online") {
    badgeElement.classList.add("online");
    badgeElement.textContent = "온라인";
    return badgeElement;
  }

  if (statusValue === "offline") {
    badgeElement.classList.add("offline");
    badgeElement.textContent = "오프라인";
    return badgeElement;
  }

  badgeElement.classList.add("unknown");
  badgeElement.textContent = "확인 필요";
  return badgeElement;
}

function updateDeviceTable(deviceList) {
  if (!deviceTableBodyElement) {
    return;
  }
  deviceTableBodyElement.innerHTML = "";

  if (!deviceList.length) {
    const emptyRowElement = document.createElement("tr");
    emptyRowElement.innerHTML = `
      <td colspan="9">탐지된 장치가 없습니다. 네트워크 또는 권한 상태를 확인해주세요.</td>
    `;
    deviceTableBodyElement.appendChild(emptyRowElement);
    return;
  }

  for (const device of deviceList) {
    const rowElement = document.createElement("tr");

    const statusCellElement = document.createElement("td");
    statusCellElement.appendChild(buildStatusBadge(device.status));
    rowElement.appendChild(statusCellElement);

    rowElement.innerHTML += `
      <td>${device.ip}</td>
      <td>${device.mac}</td>
      <td>${device.vendor || "알 수 없음"}</td>
      <td>${(device.open_ports || []).length ? device.open_ports.join(", ") : "-"}</td>
      <td>${device.model || "-"}</td>
      <td>${device.serial_number || "-"}</td>
      <td>${device.hostname}</td>
      <td>${device.last_seen}</td>
    `;

    deviceTableBodyElement.appendChild(rowElement);
  }
}

function setErrorMessage(messageText) {
  if (!errorMessageElement) {
    return;
  }
  if (!messageText) {
    errorMessageElement.textContent = "";
    errorMessageElement.classList.add("hidden");
    return;
  }

  errorMessageElement.textContent = messageText;
  errorMessageElement.classList.remove("hidden");
}

function setWarningMessage(messageText) {
  if (!warningMessageElement) {
    return;
  }
  if (!messageText) {
    warningMessageElement.textContent = "";
    warningMessageElement.classList.add("hidden");
    return;
  }

  warningMessageElement.textContent = messageText;
  warningMessageElement.classList.remove("hidden");
}

function updateFingerprintSummary(summaryData) {
  if (
    !fpTargetCountElement ||
    !fpSuccessCountElement ||
    !fpFailureCountElement ||
    !fpSuccessRateElement ||
    !fpFailureReasonsElement
  ) {
    return;
  }
  if (!summaryData) {
    fpTargetCountElement.textContent = "0";
    fpSuccessCountElement.textContent = "0";
    fpFailureCountElement.textContent = "0";
    fpSuccessRateElement.textContent = "0%";
    fpFailureReasonsElement.textContent = "아직 수집 결과가 없습니다.";
    return;
  }

  fpTargetCountElement.textContent = summaryData.target_online_devices ?? 0;
  fpSuccessCountElement.textContent = summaryData.success_count ?? 0;
  fpFailureCountElement.textContent = summaryData.failure_count ?? 0;
  fpSuccessRateElement.textContent = `${summaryData.success_rate_percent ?? 0}%`;

  const reasonObject = summaryData.failure_reasons || {};
  const reasonEntries = Object.entries(reasonObject);
  if (!reasonEntries.length) {
    fpFailureReasonsElement.textContent = "실패 건이 없습니다.";
    return;
  }
  fpFailureReasonsElement.textContent = reasonEntries
    .map(([reasonKey, countValue]) => `${reasonKey}: ${countValue}`)
    .join("\n");
}

function drawHistoryChart(historyList) {
  if (!historyChartElement) {
    return;
  }

  const context = historyChartElement.getContext("2d");
  if (!context) {
    return;
  }

  const width = historyChartElement.clientWidth || 800;
  const height = Number(historyChartElement.getAttribute("height")) || 180;
  historyChartElement.width = width;
  historyChartElement.height = height;

  context.clearRect(0, 0, width, height);
  /* WHY: 카드 배경색과 맞춰서 캔버스 배경을 통일합니다 */
  context.fillStyle = "#111827";
  context.fillRect(0, 0, width, height);

  if (!historyList || historyList.length < 2) {
    context.fillStyle = "#94a3b8";
    context.font = "14px sans-serif";
    context.fillText("그래프를 위해 2회 이상 스캔 데이터가 필요합니다.", 16, height / 2);
    return;
  }

  const maxValue = Math.max(...historyList.map((point) => point.total), 1);
  const paddingLeft = 42;
  const paddingRight = 16;
  const paddingTop = 16;
  const paddingBottom = 28;
  const graphWidth = width - paddingLeft - paddingRight;
  const graphHeight = height - paddingTop - paddingBottom;

  function drawLine(colorValue, keyName) {
    context.beginPath();
    context.strokeStyle = colorValue;
    context.lineWidth = 2;

    historyList.forEach((point, index) => {
      const x = paddingLeft + (graphWidth * index) / (historyList.length - 1);
      const y = paddingTop + graphHeight - (graphHeight * point[keyName]) / maxValue;
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
    });

    context.stroke();
  }

  context.strokeStyle = "#334155";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(paddingLeft, paddingTop);
  context.lineTo(paddingLeft, height - paddingBottom);
  context.lineTo(width - paddingRight, height - paddingBottom);
  context.stroke();

  drawLine("#22c55e", "online");
  drawLine("#ef4444", "offline");
  drawLine("#60a5fa", "total");

  const latestPoint = historyList[historyList.length - 1];
  context.fillStyle = "#cbd5e1";
  context.font = "12px sans-serif";
  context.fillText(`최신 시각: ${latestPoint.time}`, paddingLeft, height - 8);
  context.fillText(`최대값: ${maxValue}`, width - 90, paddingTop + 10);
}

/** 상단 시스템 요약 카드(/api/dashboard-summary). */
async function fetchDashboardSummary() {
  const buildEl = document.getElementById("summary-build");
  if (!buildEl) {
    return;
  }
  try {
    const response = await nwipFetch("/api/dashboard-summary");
    const payload = await response.json();
    if (!payload.ok) {
      return;
    }
    buildEl.textContent = payload.build_tag || "—";
    const npcapEl = document.getElementById("summary-npcap");
    if (npcapEl) {
      if (payload.npcap_installed === true) {
        npcapEl.textContent = "감지됨";
      } else if (payload.npcap_installed === false) {
        npcapEl.textContent = "없음(ARP는 ping 폴백 가능)";
      } else {
        npcapEl.textContent = "—(비 Windows)";
      }
    }
    const invEl = document.getElementById("summary-inventory");
    if (invEl) {
      const exists = payload.inventory_exists ? "✓" : "✗";
      invEl.textContent = `${exists} ${payload.inventory_path || ""}`;
    }
    const authEl = document.getElementById("summary-auth");
    if (authEl) {
      authEl.textContent = payload.access_token_configured ? "켜짐" : "끔";
    }
    const lastEl = document.getElementById("summary-last-scan");
    if (lastEl) {
      const t = payload.last_scan_at || "—";
      const tot = payload.last_scan_total != null ? ` · 총 ${payload.last_scan_total}대` : "";
      lastEl.textContent = `${t}${tot}`;
    }
    const scanMsEl = document.getElementById("summary-scan-ms");
    if (scanMsEl) {
      const ms = payload.last_scan_duration_ms;
      scanMsEl.textContent = ms != null && !Number.isNaN(Number(ms)) ? `${ms} ms` : "—";
    }
    const histProfEl = document.getElementById("summary-history-profile");
    if (histProfEl) {
      const histOn = payload.history_enabled ? "이력 켜짐" : "이력 꺼짐";
      const lastSnap = payload.history_last_snapshot_at || "저장 없음";
      const prof = payload.active_profile_label || "자동";
      histProfEl.textContent = `${histOn} · 마지막 저장 ${lastSnap} · 프로필 ${prof}`;
    }
    const warnLine = document.getElementById("summary-warning-line");
    if (warnLine) {
      warnLine.textContent = payload.warning_from_last_scan || "";
    }
  } catch (e) {
    /* 요약 실패는 치명적이지 않음 */
  }
}

/** /api/history/snapshots 로 셀렉트 박스 채우기 */
async function loadHistorySnapshots() {
  if (!historySnapshotSelectElement || !historyDiffResultElement) {
    return;
  }
  try {
    const response = await nwipFetch("/api/history/snapshots?limit=80");
    const payload = await response.json();
    if (!payload.ok) {
      historyDiffResultElement.textContent = payload.error || "이력 목록을 불러오지 못했습니다.";
      return;
    }
    const rows = payload.data || [];
    const prevValue = historySnapshotSelectElement.value;
    historySnapshotSelectElement.innerHTML = "";
    if (!rows.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(저장된 스냅샷 없음)";
      historySnapshotSelectElement.appendChild(opt);
      historyDiffResultElement.textContent =
        "아직 스냅샷이 없습니다. 설정에서 이력을 켠 뒤, 최소 간격(기본 60초)마다 자동 저장됩니다.";
      return;
    }
    rows.forEach((row) => {
      const opt = document.createElement("option");
      opt.value = String(row.id);
      const summary = row.summary || {};
      const on = summary.online_count != null ? summary.online_count : "?";
      opt.textContent = `#${row.id} · ${row.scanned_at || ""} · 온라인 ${on} · ${row.network || ""}`;
      historySnapshotSelectElement.appendChild(opt);
    });
    if (prevValue && [...historySnapshotSelectElement.options].some((o) => o.value === prevValue)) {
      historySnapshotSelectElement.value = prevValue;
    }
    historyDiffResultElement.textContent = "스냅샷을 고른 뒤 「현재와 비교」를 누르세요.";
  } catch (err) {
    historyDiffResultElement.textContent = `이력 로드 오류: ${err.message || err}`;
  }
}

async function fetchNetworkScan() {
  if (!refreshButtonElement) {
    return;
  }
  refreshButtonElement.disabled = true;

  try {
    const response = await nwipFetch("/api/scan");
    const payload = await response.json();

    if (!payload.ok) {
      throw new Error(payload.error || "알 수 없는 오류가 발생했습니다.");
    }

    const scanData = payload.data;
    if (currentHostIpElement) {
      currentHostIpElement.textContent = scanData.current_host_ip;
    }
    if (networkCidrElement) {
      networkCidrElement.textContent = scanData.network;
    }
    if (scannedAtElement) {
      scannedAtElement.textContent = scanData.scanned_at;
    }
    if (onlineCountElement) {
      onlineCountElement.textContent = scanData.summary?.online_count ?? 0;
    }
    if (offlineCountElement) {
      offlineCountElement.textContent = scanData.summary?.offline_count ?? 0;
    }
    if (totalCountElement) {
      totalCountElement.textContent = scanData.summary?.total_count ?? 0;
    }
    updateDeviceTable(scanData.devices);
    drawHistoryChart(scanData.history || []);
    setWarningMessage(scanData.warning_message || "");
    // WHY: 주기 스캔마다 핑거프린트 요약을 지우면 「장비 정보」 직후에도 다음 폴링에서 0으로 돌아갑니다.
    setErrorMessage("");
  } catch (error) {
    setWarningMessage("");
    setErrorMessage(error.message || "스캔 중 오류가 발생했습니다.");
  } finally {
    refreshButtonElement.disabled = false;
  }
}

if (isMainDeviceDashboard) {
  nwipCaptureTokenFromUrl();
  refreshButtonElement.addEventListener("click", fetchNetworkScan);
  exportCsvButtonElement.addEventListener("click", () => {
    const t = nwipToken();
    window.location.href = t ? `/api/export/csv?token=${encodeURIComponent(t)}` : "/api/export/csv";
  });

  fingerprintButtonElement.addEventListener("click", async () => {
    fingerprintButtonElement.disabled = true;
    try {
      const response = await nwipFetch("/api/device/fingerprint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inventory_path: inventoryInputElement.value }),
      });
      const payload = await response.json();
      if (!payload.ok) {
        throw new Error(payload.error || "장비 정보 수집 중 오류가 발생했습니다.");
      }

      const scanData = payload.data;
      if (currentHostIpElement) {
        currentHostIpElement.textContent = scanData.current_host_ip;
      }
      if (networkCidrElement) {
        networkCidrElement.textContent = scanData.network;
      }
      if (scannedAtElement) {
        scannedAtElement.textContent = scanData.scanned_at;
      }
      if (onlineCountElement) {
        onlineCountElement.textContent = scanData.summary?.online_count ?? 0;
      }
      if (offlineCountElement) {
        offlineCountElement.textContent = scanData.summary?.offline_count ?? 0;
      }
      if (totalCountElement) {
        totalCountElement.textContent = scanData.summary?.total_count ?? 0;
      }
      updateDeviceTable(scanData.devices || []);
      drawHistoryChart(scanData.history || []);
      setWarningMessage(scanData.warning_message || "");
      updateFingerprintSummary(scanData.fingerprint_summary || null);
      setErrorMessage("");
    } catch (error) {
      setErrorMessage(error.message || "장비 정보 수집 실패");
    } finally {
      fingerprintButtonElement.disabled = false;
    }
  });

  logAnalyzeFormElement.addEventListener("submit", async (event) => {
    event.preventDefault();
    logAnalyzeButtonElement.disabled = true;
    try {
      const formData = new FormData(logAnalyzeFormElement);
      const response = await nwipFetch("/api/log/analyze", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!payload.ok) {
        throw new Error(payload.error || "로그 분석 중 오류가 발생했습니다.");
      }
      const summary = payload.data.summary || {};
      logSummaryBoxElement.textContent = JSON.stringify(summary, null, 2);
    } catch (error) {
      logSummaryBoxElement.textContent = `오류: ${error.message || "로그 분석 실패"}`;
    } finally {
      logAnalyzeButtonElement.disabled = false;
    }
  });

  automationRunButtonElement.addEventListener("click", async () => {
    automationRunButtonElement.disabled = true;
    try {
      const response = await nwipFetch("/api/automation/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instruction: instructionInputElement.value,
          inventory_path: inventoryInputElement.value,
          dry_run: dryRunInputElement.checked,
        }),
      });
      const payload = await response.json();
      if (!payload.ok) {
        throw new Error(payload.error || "자동화 실행 중 오류가 발생했습니다.");
      }
      automationResultBoxElement.textContent = JSON.stringify(payload.data.report, null, 2);
    } catch (error) {
      automationResultBoxElement.textContent = `오류: ${error.message || "자동화 실행 실패"}`;
    } finally {
      automationRunButtonElement.disabled = false;
    }
  });

  // WHY: 설정의 스캔 주기(초)를 반영하고, 요약은 60초마다 갱신합니다.
  (async () => {
    let intervalMs = 10000;
    try {
      const r = await nwipFetch("/api/settings");
      const p = await r.json();
      if (p.ok && p.data && inventoryInputElement && p.data.inventory_path) {
        inventoryInputElement.value = p.data.inventory_path;
      }
      if (p.ok && p.data && p.data.scan_interval_seconds >= 5) {
        intervalMs = p.data.scan_interval_seconds * 1000;
      }
    } catch (e) {
      /* 기본 10초 */
    }
    fetchDashboardSummary();
    fetchNetworkScan();
    loadHistorySnapshots();
    setInterval(fetchNetworkScan, intervalMs);
    setInterval(fetchDashboardSummary, 60000);
  })();

  if (historyDiffButtonElement && historySnapshotSelectElement) {
    historyDiffButtonElement.addEventListener("click", async () => {
      const sid = historySnapshotSelectElement.value;
      if (!sid) {
        if (historyDiffResultElement) {
          historyDiffResultElement.textContent = "비교할 스냅샷을 선택하세요.";
        }
        return;
      }
      historyDiffButtonElement.disabled = true;
      if (historyDiffResultElement) {
        historyDiffResultElement.textContent = "비교 중…";
      }
      try {
        const response = await nwipFetch(`/api/history/diff?from_id=${encodeURIComponent(sid)}`);
        const payload = await response.json();
        if (!payload.ok) {
          throw new Error(payload.error || "diff 실패");
        }
        if (historyDiffResultElement) {
          historyDiffResultElement.textContent = JSON.stringify(payload.data, null, 2);
        }
      } catch (err) {
        if (historyDiffResultElement) {
          historyDiffResultElement.textContent = `오류: ${err.message || err}`;
        }
      } finally {
        historyDiffButtonElement.disabled = false;
      }
    });
  }
  if (historySnapshotsRefreshElement) {
    historySnapshotsRefreshElement.addEventListener("click", () => {
      loadHistorySnapshots();
    });
  }
}

// WHY: Wi-Fi 링크는 스캔과 독립이므로 Wi-Fi 카드가 있을 때만 초기 1회 로드합니다.
nwipCaptureTokenFromUrl();
if (wifiRefreshButtonElement) {
  fetchWifiStatus();
}

/* ──────────────────────────────────────────────────────────
   스위치 포트 현황 — 조회 및 렌더링
   WHY: SNMP Walk는 시간이 걸리므로 버튼 클릭 시에만 실행합니다.
────────────────────────────────────────────────────────── */
const switchPollButtonElement = document.getElementById("switch-poll-button");
const switchPanelsElement     = document.getElementById("switch-panels");

/**
 * 포트 이름을 짧게 줄입니다. (GigabitEthernet0/1 → Gi0/1)
 * WHY: 격자 칩에 긴 이름이 들어가면 레이아웃이 깨집니다.
 */
function shortenPortName(name) {
  return name
    .replace(/GigabitEthernet/gi, "Gi")
    .replace(/FastEthernet/gi,    "Fa")
    .replace(/TenGigabitEthernet/gi, "Te")
    .replace(/HundredGigabitEthernet/gi, "Hu")
    .replace(/Ethernet/gi,        "Et")
    .replace(/Management/gi,      "Mg")
    .replace(/interface/gi,       "")
    .trim();
}

/** 속도(Mbps)를 읽기 좋은 문자열로 변환합니다. */
function formatSpeed(mbps) {
  if (!mbps) return "";
  if (mbps >= 1000) return `${mbps / 1000}G`;
  return `${mbps}M`;
}

/** 포트 칩 하나를 생성합니다. */
function buildPortChip(port) {
  const chip = document.createElement("div");
  const status = port.oper_status;
  chip.className = `port-chip port-chip--${status === "up" ? "up" : status === "down" ? "down" : "other"}`;
  chip.title = `${port.name}\nStatus: ${status} / Admin: ${port.admin_status}\nSpeed: ${port.speed_mbps ? port.speed_mbps + " Mbps" : "-"}`;

  const nameEl  = document.createElement("span");
  nameEl.className   = "port-chip-name";
  nameEl.textContent = shortenPortName(port.name);

  const speedEl = document.createElement("span");
  speedEl.className   = "port-chip-speed";
  speedEl.textContent = formatSpeed(port.speed_mbps);

  chip.appendChild(nameEl);
  chip.appendChild(speedEl);
  return chip;
}

/** 스위치 1대의 블록(IP + 포트 격자)을 생성합니다. */
function buildSwitchBlock(switchData) {
  const block = document.createElement("div");
  block.className = "switch-block";

  // 헤더: IP + 통계
  const header = document.createElement("div");
  header.className = "switch-block-header";

  const ipEl = document.createElement("span");
  ipEl.className   = "switch-block-ip";
  ipEl.textContent = switchData.switch_ip;
  header.appendChild(ipEl);

  if (switchData.source) {
    const srcEl = document.createElement("span");
    srcEl.className = "switch-block-source";
    const srcMap = { snmp: "SNMP", ssh_cisco: "SSH(Cisco)", none: "—", error: "오류" };
    srcEl.textContent = srcMap[switchData.source] || switchData.source;
    header.appendChild(srcEl);
  }

  if (switchData.error) {
    const errEl = document.createElement("p");
    errEl.className   = "switch-block-error";
    errEl.textContent = `오류: ${switchData.error}`;
    block.appendChild(header);
    block.appendChild(errEl);
    return block;
  }

  const summary = switchData.summary || {};
  const statsEl = document.createElement("div");
  statsEl.className = "switch-block-stats";
  statsEl.innerHTML = `
    <span class="stat-up">UP ${summary.up ?? 0}</span>
    <span class="stat-down">DOWN ${summary.down ?? 0}</span>
    <span class="stat-total">/ 총 ${summary.total ?? 0}</span>
  `;
  header.appendChild(statsEl);
  block.appendChild(header);

  // 포트 격자
  const grid = document.createElement("div");
  grid.className = "port-grid";
  (switchData.ports || []).forEach((port) => {
    grid.appendChild(buildPortChip(port));
  });
  block.appendChild(grid);

  return block;
}

/** /api/switch/ports 를 호출하고 결과를 렌더링합니다. */
async function fetchSwitchPorts() {
  if (!switchPollButtonElement || !switchPanelsElement) {
    return;
  }
  switchPollButtonElement.disabled = true;
  switchPanelsElement.innerHTML = "<p class='switch-placeholder'>SNMP Walk 실행 중...</p>";

  try {
    const inventoryPath = document.getElementById("inventory-input")?.value || "devices.example.yaml";
    const response = await nwipFetch(
      `/api/switch/ports?inventory_path=${encodeURIComponent(inventoryPath)}`
    );
    const payload  = await response.json();

    if (!payload.ok) {
      throw new Error(payload.error || "포트 조회 실패");
    }

    const switchList = payload.data || [];
    switchPanelsElement.innerHTML = "";

    if (!switchList.length) {
      switchPanelsElement.innerHTML = "<p class='switch-placeholder'>인벤토리에 스위치가 없습니다. devices.example.yaml 을 확인하세요.</p>";
      return;
    }

    switchList.forEach((sw) => {
      switchPanelsElement.appendChild(buildSwitchBlock(sw));
    });
  } catch (error) {
    switchPanelsElement.innerHTML = `<p class='switch-placeholder' style='color:var(--red)'>오류: ${error.message}</p>`;
  } finally {
    switchPollButtonElement.disabled = false;
  }
}

if (switchPollButtonElement) {
  switchPollButtonElement.addEventListener("click", fetchSwitchPorts);
}

