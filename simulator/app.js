/**
 * PROSIM STUDIO APPLICATION COORDINATOR (app.js)
 * Manages OPC UA Connectivity, Tag & OPC Connection Studio, Fullscreen, and UI Paneling.
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // =========================================================================
  // 1. TOP HEADER OPC UA STATUS MONITOR
  // =========================================================================
  const opcStatusPill = document.getElementById('opcStatusPill');
  const opcStatusText = document.getElementById('opcStatusText');

  async function checkOpcStatus() {
    try {
      const res = await fetch('/api/opc/status', { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        const isActive = !!data.opc_active;
        const endpoint = data.server_endpoint || 'opc.tcp://0.0.0.0:4841';
        const tagCount = data.opc_tags ?? 0;

        if (opcStatusPill && opcStatusText) {
          if (isActive) {
            opcStatusPill.className = 'status-pill opc-pill active';
            opcStatusText.textContent = `OPC UA: Online (${tagCount} tags)`;
            opcStatusPill.title = `OPC UA Server Active\nEndpoint: ${endpoint}\nRegistered Nodes: ${tagCount}\nClick to open Tag Studio`;
          } else {
            opcStatusPill.className = 'status-pill opc-pill standby';
            opcStatusText.textContent = `OPC UA: Ready (${tagCount} tags)`;
            opcStatusPill.title = `OPC UA Server Standby / Bridge Mode\nEndpoint: ${endpoint}\nClick to open Tag Studio`;
          }
        }

        // Also update Tag Studio subtext if open
        const tsText = document.getElementById('tagStudioOpcStatusText');
        if (tsText) {
          tsText.textContent = `OPC UA Server: ${endpoint} [${isActive ? 'Online' : 'Standby'}]`;
        }
      }
    } catch (e) {
      if (opcStatusPill && opcStatusText) {
        opcStatusPill.className = 'status-pill opc-pill offline';
        opcStatusText.textContent = 'OPC UA: Offline';
        opcStatusPill.title = 'Simulator backend unreachable or offline';
      }
    }
  }

  // Poll OPC status every 3.5 seconds
  checkOpcStatus();
  setInterval(checkOpcStatus, 3500);

  if (opcStatusPill) {
    opcStatusPill.style.cursor = 'pointer';
    opcStatusPill.addEventListener('click', () => {
      openTagStudio();
    });
  }

  // =========================================================================
  // 2. FULLSCREEN & SIDEBAR TOGGLE UTILITIES
  // =========================================================================
  const btnToggleFullscreen = document.getElementById('btnToggleFullscreen');
  if (btnToggleFullscreen) {
    btnToggleFullscreen.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(() => {
          btnToggleFullscreen.innerHTML = '⛶ Exit Full';
          btnToggleFullscreen.classList.add('active');
        }).catch(err => {
          console.warn('Fullscreen request failed:', err);
        });
      } else {
        document.exitFullscreen().then(() => {
          btnToggleFullscreen.innerHTML = '⛶ Fullscreen';
          btnToggleFullscreen.classList.remove('active');
        }).catch(err => {
          console.warn('Exit fullscreen failed:', err);
        });
      }
    });

    document.addEventListener('fullscreenchange', () => {
      if (!document.fullscreenElement) {
        btnToggleFullscreen.innerHTML = '⛶ Fullscreen';
        btnToggleFullscreen.classList.remove('active');
      } else {
        btnToggleFullscreen.innerHTML = '⛶ Exit Full';
        btnToggleFullscreen.classList.add('active');
      }
    });
  }

  // Sidebar collapse toggles
  const btnTogglePalette = document.getElementById('btnTogglePalette');
  const paletteEl = document.getElementById('builderPalette');
  if (btnTogglePalette && paletteEl) {
    btnTogglePalette.addEventListener('click', () => {
      const isCollapsed = paletteEl.classList.toggle('collapsed');
      btnTogglePalette.textContent = isCollapsed ? '▶' : '◀';
      btnTogglePalette.title = isCollapsed ? 'Expand Component Library' : 'Collapse Component Library';
      // Trigger resize for canvas if needed
      window.dispatchEvent(new Event('resize'));
    });
  }

  const btnToggleInspector = document.getElementById('btnToggleInspector');
  const inspectorEl = document.getElementById('builderInspector');
  if (btnToggleInspector && inspectorEl) {
    btnToggleInspector.addEventListener('click', () => {
      const isCollapsed = inspectorEl.classList.toggle('collapsed');
      btnToggleInspector.textContent = isCollapsed ? '◀' : '▶';
      btnToggleInspector.title = isCollapsed ? 'Expand Inspector' : 'Collapse Inspector';
      window.dispatchEvent(new Event('resize'));
    });
  }

  // =========================================================================
  // 3. TAG & OPC UA CONNECTION STUDIO MODAL
  // =========================================================================
  const btnTagStudio = document.getElementById('btnTagStudio');
  const tagStudioModal = document.getElementById('tagStudioModal');
  const btnCloseTagStudio = document.getElementById('btnCloseTagStudio');
  const btnCloseTagStudioFooter = document.getElementById('btnCloseTagStudioFooter');

  const statTotalTags = document.getElementById('statTotalTags');
  const statSetpoints = document.getElementById('statSetpoints');
  const statMeasurements = document.getElementById('statMeasurements');
  const statOpcTags = document.getElementById('statOpcTags');
  const statLocalTags = document.getElementById('statLocalTags');

  const cntFilterAll = document.getElementById('cntFilterAll');
  const cntFilterSP = document.getElementById('cntFilterSP');
  const cntFilterPV = document.getElementById('cntFilterPV');
  const cntFilterOpc = document.getElementById('cntFilterOpc');
  const cntFilterLocal = document.getElementById('cntFilterLocal');

  const tagSearchInput = document.getElementById('tagSearchInput');
  const btnClearSearch = document.getElementById('btnClearSearch');
  const tagGridTableBody = document.getElementById('tagGridTableBody');

  const btnTestOpc = document.getElementById('btnTestOpc');
  const btnSetAllLocal = document.getElementById('btnSetAllLocal');
  const btnSetAllOpc = document.getElementById('btnSetAllOpc');
  const btnOpenAddTag = document.getElementById('btnOpenAddTag');

  const opcTestBanner = document.getElementById('opcTestBanner');
  const opcTestBannerIcon = document.getElementById('opcTestBannerIcon');
  const opcTestBannerText = document.getElementById('opcTestBannerText');
  const btnCloseTestBanner = document.getElementById('btnCloseTestBanner');

  // Custom Tag Modal Elements
  const customTagModal = document.getElementById('customTagModal');
  const btnCloseCustomTagModal = document.getElementById('btnCloseCustomTagModal');
  const btnCancelCustomTag = document.getElementById('btnCancelCustomTag');
  const btnSaveCustomTag = document.getElementById('btnSaveCustomTag');
  const customTagModalTitle = document.getElementById('customTagModalTitle');
  const customTagStatusMsg = document.getElementById('customTagStatusMsg');
  const tagEditId = document.getElementById('tagEditId');
  const tagEditName = document.getElementById('tagEditName');
  const tagEditHmi = document.getElementById('tagEditHmi');
  const tagEditCategory = document.getElementById('tagEditCategory');
  const tagEditSource = document.getElementById('tagEditSource');
  const tagEditNodeId = document.getElementById('tagEditNodeId');
  const tagEditDirection = document.getElementById('tagEditDirection');
  const tagEditUnit = document.getElementById('tagEditUnit');
  const tagEditMin = document.getElementById('tagEditMin');
  const tagEditMax = document.getElementById('tagEditMax');
  const tagEditDef = document.getElementById('tagEditDef');

  let tagsData = [];
  let currentTagFilter = 'all';
  let tagSearchTerm = '';
  let editingTagId = null;

  function openTagStudio(filterKeyword) {
    if (tagStudioModal) {
      tagStudioModal.classList.add('open');
      if (typeof filterKeyword === 'string' && tagSearchInput) {
        tagSearchInput.value = filterKeyword;
        tagSearchTerm = filterKeyword;
      }
      loadTagsData();
      checkOpcStatus();
    }
  }
  window.openTagStudio = openTagStudio;

  function closeTagStudio() {
    if (tagStudioModal) {
      tagStudioModal.classList.remove('open');
    }
  }

  async function loadTagsData() {
    try {
      const res = await fetch('/api/tags', { cache: 'no-store' });
      if (res.ok) {
        const payload = await res.json();
        tagsData = Array.isArray(payload) ? payload : (payload.tags || []);
        updateTagCounters();
        renderTagTable();
      }
    } catch (e) {
      console.warn("Could not load tag dictionary from backend:", e);
    }
  }

  // Expose for external calls (e.g. after flowsheet deploy)
  window.refreshOpcStudio = loadTagsData;

  function updateTagCounters() {
    const total = tagsData.length;
    const sps = tagsData.filter(t => t.category === 'setpoint').length;
    const pvs = tagsData.filter(t => t.category === 'measurement').length;
    const opcs = tagsData.filter(t => t.source === 'opc_ua').length;
    const locals = tagsData.filter(t => t.source === 'local').length;

    if (statTotalTags) statTotalTags.textContent = total;
    if (statSetpoints) statSetpoints.textContent = sps;
    if (statMeasurements) statMeasurements.textContent = pvs;
    if (statOpcTags) statOpcTags.textContent = opcs;
    if (statLocalTags) statLocalTags.textContent = locals;

    if (cntFilterAll) cntFilterAll.textContent = total;
    if (cntFilterSP) cntFilterSP.textContent = sps;
    if (cntFilterPV) cntFilterPV.textContent = pvs;
    if (cntFilterOpc) cntFilterOpc.textContent = opcs;
    if (cntFilterLocal) cntFilterLocal.textContent = locals;
  }

  function renderTagTable() {
    if (!tagGridTableBody) return;

    const filtered = tagsData.filter(tag => {
      // Category / Source filter
      if (currentTagFilter === 'setpoint' && tag.category !== 'setpoint') return false;
      if (currentTagFilter === 'measurement' && tag.category !== 'measurement') return false;
      if (currentTagFilter === 'opc_ua' && tag.source !== 'opc_ua') return false;
      if (currentTagFilter === 'local' && tag.source !== 'local') return false;

      // Search term
      if (tagSearchTerm) {
        const q = tagSearchTerm.toLowerCase();
        const mId = (tag.tag_id || '').toLowerCase().includes(q);
        const mName = (tag.name || '').toLowerCase().includes(q);
        const mHmi = (tag.hmi_tag || '').toLowerCase().includes(q);
        const mNode = (tag.opc_node_id || '').toLowerCase().includes(q);
        if (!mId && !mName && !mHmi && !mNode) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      tagGridTableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-dim); padding: 28px;">No tags found matching current criteria.</td></tr>`;
      return;
    }

    tagGridTableBody.innerHTML = filtered.map(tag => {
      const isSP = tag.category === 'setpoint';
      const isOpc = tag.source === 'opc_ua';
      const isCustom = !!tag.custom;
      const val = tag.live_value !== undefined
        ? (typeof tag.live_value === 'number' ? (Math.abs(tag.live_value) > 100 ? tag.live_value.toFixed(1) : tag.live_value.toFixed(2)) : tag.live_value)
        : (tag.default ?? '-');

      // Value column
      let valHtml = '';
      const isBoolVal = typeof val === 'boolean' || tag.data_type === 'Boolean' || tag.data_type === 'bool';
      if (isSP) {
        if (!isOpc) {
          if (isBoolVal) {
            valHtml = `
              <div class="sp-edit-box">
                <select class="sp-edit-input" data-tag="${tag.tag_id}" style="width: 70px; padding: 2px 4px; font-size: 11px;">
                  <option value="true" ${val === true || val === 'true' ? 'selected' : ''}>TRUE</option>
                  <option value="false" ${val === false || val === 'false' ? 'selected' : ''}>FALSE</option>
                </select>
                <button class="btn-apply-sp" data-tag="${tag.tag_id}" title="Apply Local Setpoint">✓</button>
              </div>
            `;
          } else {
            valHtml = `
              <div class="sp-edit-box">
                <input type="number" step="any" class="sp-edit-input" data-tag="${tag.tag_id}" value="${val}" />
                <button class="btn-apply-sp" data-tag="${tag.tag_id}" title="Apply Local Setpoint">✓</button>
              </div>
            `;
          }
        } else {
          valHtml = `
            <span class="live-val-badge opc-driven" id="live_tag_${tag.tag_id}">${val}</span>
            <span style="font-size: 8px; color: #6EE7B7; border: 1px solid rgba(16,185,129,0.3); padding: 1px 3px; border-radius: 3px; font-weight: 700; margin-left: 4px;">OPC</span>
          `;
        }
      } else {
        valHtml = `<span class="live-val-badge" id="live_tag_${tag.tag_id}">${val}</span>`;
      }

      const rangeText = (tag.min !== undefined && tag.max !== undefined) ? `[${tag.min}, ${tag.max}]` : '-';

      return `
        <tr data-tag-row="${tag.tag_id}">
          <td>
            <div class="tag-id-box">
              <strong>${tag.tag_id}</strong>
              <span class="tag-name-desc">${tag.name || ''}</span>
            </div>
          </td>
          <td><code style="color: #F8FAFC; font-family: var(--font-mono); font-size: 11px;">${tag.hmi_tag || '-'}</code></td>
          <td>
            <span class="${isSP ? 'badge-cat-sp' : 'badge-cat-pv'}">${isSP ? '🎯 Setpoint' : '📊 Measurement'}</span>
          </td>
          <td>
            <button class="source-btn-toggle ${isOpc ? 'source-opc' : 'source-local'}" data-tag="${tag.tag_id}" data-current="${tag.source}" title="Click to toggle between Local and OPC UA control">
              ${isOpc ? '⚡ OPC UA' : '💻 Local'}
            </button>
          </td>
          <td>${valHtml}</td>
          <td><span style="color: var(--text-muted); font-size: 11px;">${tag.unit || ''}</span></td>
          <td><span class="node-code" title="${tag.opc_node_id || ''}">${tag.opc_node_id || '-'}</span></td>
          <td>
            <span class="direction-badge ${tag.opc_direction === 'write' ? 'write' : 'read'}">
              ${tag.opc_direction === 'write' ? 'WRITE (SP)' : 'READ (PV)'}
            </span>
          </td>
          <td style="color: var(--text-dim); font-family: var(--font-mono); font-size: 10px;">${rangeText}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="tbl-action-btn btn-edit-tag" data-tag="${tag.tag_id}" title="Edit Tag Properties">✎</button>
              ${isCustom ? `<button class="tbl-action-btn btn-del-tag" data-tag="${tag.tag_id}" title="Delete Custom Tag">🗑</button>` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Attach listeners
    tagGridTableBody.querySelectorAll('.source-btn-toggle').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tagId = btn.getAttribute('data-tag');
        const curr = btn.getAttribute('data-current');
        const newSrc = curr === 'local' ? 'opc_ua' : 'local';
        await toggleTagSource(tagId, newSrc);
      });
    });

    tagGridTableBody.querySelectorAll('.btn-apply-sp').forEach(btn => {
      btn.addEventListener('click', () => {
        const tagId = btn.getAttribute('data-tag');
        const input = tagGridTableBody.querySelector(`.sp-edit-input[data-tag="${tagId}"]`);
        if (input) applyLocalSetpoint(tagId, input.value);
      });
    });

    tagGridTableBody.querySelectorAll('.sp-edit-input').forEach(input => {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const tagId = input.getAttribute('data-tag');
          applyLocalSetpoint(tagId, input.value);
        }
      });
    });

    tagGridTableBody.querySelectorAll('.btn-edit-tag').forEach(btn => {
      btn.addEventListener('click', () => {
        const tagId = btn.getAttribute('data-tag');
        const tagObj = tagsData.find(t => t.tag_id === tagId);
        if (tagObj) openTagModal(tagObj);
      });
    });

    tagGridTableBody.querySelectorAll('.btn-del-tag').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tagId = btn.getAttribute('data-tag');
        if (confirm(`Are you sure you want to delete custom tag "${tagId}"?`)) {
          await deleteTag(tagId);
        }
      });
    });
  }

  async function toggleTagSource(tagId, newSource) {
    try {
      const res = await fetch('/api/tags/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_id: tagId, source: newSource })
      });
      if (res.ok) {
        const tag = tagsData.find(t => t.tag_id === tagId);
        if (tag) tag.source = newSource;
        updateTagCounters();
        renderTagTable();
      }
    } catch (e) {
      console.error("Failed to toggle tag source:", e);
    }
  }

  async function applyLocalSetpoint(tagId, valStr) {
    const val = parseFloat(valStr);
    if (isNaN(val)) return;
    try {
      const res = await fetch('/api/tags/value', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_id: tagId, value: val })
      });
      if (res.ok) {
        const tag = tagsData.find(t => t.tag_id === tagId);
        if (tag) tag.live_value = val;
        const input = tagGridTableBody.querySelector(`.sp-edit-input[data-tag="${tagId}"]`);
        if (input) {
          input.style.borderColor = '#00E676';
          input.style.boxShadow = '0 0 8px rgba(0, 230, 118, 0.5)';
          setTimeout(() => {
            input.style.borderColor = '';
            input.style.boxShadow = '';
          }, 800);
        }
      }
    } catch (e) {
      console.error("Failed to set tag value:", e);
    }
  }

  async function setAllTagsSource(targetSource) {
    for (const tag of tagsData) {
      if (tag.category === 'setpoint' && tag.source !== targetSource) {
        await toggleTagSource(tag.tag_id, targetSource);
      }
    }
  }

  async function testOpcServer() {
    if (!opcTestBanner) return;
    opcTestBanner.style.display = 'flex';
    opcTestBanner.className = 'opc-test-banner info';
    if (opcTestBannerIcon) opcTestBannerIcon.textContent = '⏳';
    if (opcTestBannerText) opcTestBannerText.textContent = 'Pinging OPC UA Server endpoint...';

    try {
      const res = await fetch('/api/opc/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (data.status === 'ok') {
        opcTestBanner.className = 'opc-test-banner success';
        if (opcTestBannerIcon) opcTestBannerIcon.textContent = '✓';
        if (opcTestBannerText) {
          opcTestBannerText.textContent = `OPC UA Server Online! Endpoint: ${data.endpoint} | Latency: ${data.latency_ms} ms | Registered Nodes: ${data.nodes_count}`;
        }
      } else {
        opcTestBanner.className = 'opc-test-banner error';
        if (opcTestBannerIcon) opcTestBannerIcon.textContent = '⚠';
        if (opcTestBannerText) opcTestBannerText.textContent = `OPC UA Test Failed: ${data.message || 'Server unresponsive'}`;
      }
    } catch (e) {
      opcTestBanner.className = 'opc-test-banner error';
      if (opcTestBannerIcon) opcTestBannerIcon.textContent = '⚠';
      if (opcTestBannerText) opcTestBannerText.textContent = `Error reaching simulator backend: ${e.message}`;
    }
  }

  function openTagModal(tagObj = null) {
    editingTagId = tagObj ? tagObj.tag_id : null;
    if (customTagModalTitle) {
      customTagModalTitle.textContent = tagObj ? `✎ Edit Process Tag (${tagObj.tag_id})` : '➕ Add Custom Process Tag';
    }
    if (customTagStatusMsg) customTagStatusMsg.textContent = '';

    if (tagObj) {
      tagEditId.value = tagObj.tag_id || '';
      tagEditId.disabled = true;
      tagEditName.value = tagObj.name || '';
      tagEditHmi.value = tagObj.hmi_tag || '';
      tagEditCategory.value = tagObj.category || 'setpoint';
      tagEditSource.value = tagObj.source || 'opc_ua';
      tagEditNodeId.value = tagObj.opc_node_id || '';
      tagEditDirection.value = tagObj.opc_direction || (tagObj.category === 'setpoint' ? 'write' : 'read');
      tagEditUnit.value = tagObj.unit || '';
      tagEditMin.value = tagObj.min ?? '';
      tagEditMax.value = tagObj.max ?? '';
      tagEditDef.value = tagObj.default ?? '';
    } else {
      tagEditId.value = '';
      tagEditId.disabled = false;
      tagEditName.value = '';
      tagEditHmi.value = '';
      tagEditCategory.value = 'setpoint';
      tagEditSource.value = 'opc_ua';
      tagEditNodeId.value = 'ns=2;s=Kiln3.Setpoints.';
      tagEditDirection.value = 'write';
      tagEditUnit.value = '';
      tagEditMin.value = '';
      tagEditMax.value = '';
      tagEditDef.value = '';
    }

    if (customTagModal) customTagModal.classList.add('open');
  }

  async function saveTagModal() {
    const tagId = tagEditId.value.trim();
    if (!tagId) {
      if (customTagStatusMsg) {
        customTagStatusMsg.textContent = 'Please enter a valid tag ID.';
        customTagStatusMsg.className = 'cfg-status-message error';
      }
      return;
    }

    const payload = {
      tag_id: tagId,
      name: tagEditName.value.trim(),
      hmi_tag: tagEditHmi.value.trim(),
      category: tagEditCategory.value,
      source: tagEditSource.value,
      opc_node_id: tagEditNodeId.value.trim(),
      opc_direction: tagEditDirection.value,
      unit: tagEditUnit.value.trim(),
      min: tagEditMin.value !== '' ? parseFloat(tagEditMin.value) : undefined,
      max: tagEditMax.value !== '' ? parseFloat(tagEditMax.value) : undefined,
      default: tagEditDef.value !== '' ? parseFloat(tagEditDef.value) : undefined,
      custom: true
    };

    try {
      const res = await fetch('/api/tags/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        if (customTagStatusMsg) {
          customTagStatusMsg.textContent = '✓ Tag saved successfully!';
          customTagStatusMsg.className = 'cfg-status-message success';
        }
        await loadTagsData();
        setTimeout(() => {
          if (customTagModal) customTagModal.classList.remove('open');
        }, 600);
      } else {
        if (customTagStatusMsg) {
          customTagStatusMsg.textContent = `Error: ${data.message || 'Failed to save tag'}`;
          customTagStatusMsg.className = 'cfg-status-message error';
        }
      }
    } catch (e) {
      if (customTagStatusMsg) {
        customTagStatusMsg.textContent = `Network error: ${e.message}`;
        customTagStatusMsg.className = 'cfg-status-message error';
      }
    }
  }

  async function deleteTag(tagId) {
    try {
      const res = await fetch('/api/tags/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_id: tagId })
      });
      if (res.ok) {
        await loadTagsData();
      }
    } catch (e) {
      console.error("Failed to delete tag:", e);
    }
  }

  // Tag Studio Event Wiring
  if (btnTagStudio) btnTagStudio.addEventListener('click', openTagStudio);
  if (btnCloseTagStudio) btnCloseTagStudio.addEventListener('click', closeTagStudio);
  if (btnCloseTagStudioFooter) btnCloseTagStudioFooter.addEventListener('click', closeTagStudio);

  if (tagSearchInput) {
    tagSearchInput.addEventListener('input', (e) => {
      tagSearchTerm = e.target.value.trim();
      renderTagTable();
    });
  }

  if (btnClearSearch) {
    btnClearSearch.addEventListener('click', () => {
      if (tagSearchInput) tagSearchInput.value = '';
      tagSearchTerm = '';
      renderTagTable();
    });
  }

  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentTagFilter = pill.getAttribute('data-filter') || 'all';
      renderTagTable();
    });
  });

  if (btnTestOpc) btnTestOpc.addEventListener('click', testOpcServer);
  if (btnCloseTestBanner && opcTestBanner) {
    btnCloseTestBanner.addEventListener('click', () => {
      opcTestBanner.style.display = 'none';
    });
  }

  if (btnSetAllLocal) btnSetAllLocal.addEventListener('click', () => setAllTagsSource('local'));
  if (btnSetAllOpc) btnSetAllOpc.addEventListener('click', () => setAllTagsSource('opc_ua'));
  if (btnOpenAddTag) btnOpenAddTag.addEventListener('click', () => openTagModal(null));

  if (btnCloseCustomTagModal) {
    btnCloseCustomTagModal.addEventListener('click', () => {
      if (customTagModal) customTagModal.classList.remove('open');
    });
  }
  if (btnCancelCustomTag) {
    btnCancelCustomTag.addEventListener('click', () => {
      if (customTagModal) customTagModal.classList.remove('open');
    });
  }
  if (btnSaveCustomTag) {
    btnSaveCustomTag.addEventListener('click', saveTagModal);
  }
});
