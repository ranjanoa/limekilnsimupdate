/**
 * KILN 3 MODULAR FLOWSHEET BUILDER & CAD PROCESS CANVAS
 * Enables interactive drag-and-drop flowsheet modeling, port-to-port stream wiring,
 * real-time component inspection, steady-state solving, and dynamic simulation.
 */

(function () {
  'use strict';

  // State Management
  const state = {
    graph: {
      flowsheet_id: 'kiln_3_pyroprocess',
      name: 'Kiln 3 Full Pyroprocessing Plant (280 TPH)',
      version: '2.0',
      description: '',
      components: [],
      connections: [],
    },
    catalog: [],
    templates: [],
    selectedBlockId: null,
    selectedStreamId: null,
    isDraggingBlock: false,
    dragBlockId: null,
    dragOffset: { x: 0, y: 0 },
    isConnectingPort: false,
    connectingSource: null, // { blockId, portName, portPhase, x, y }
    viewTransform: { scale: 1.0, panX: 40, panY: 40 },
    isPanning: false,
    panStart: { x: 0, y: 0 },
    gridSnapEnabled: true,
    gridSize: 20,
    isSimulating: false,
    simInterval: null,
    simulationTime: 0.0,
    simSpeed: 1.0,
    streamCounter: 1,
    flowsheetTab: 'all',
  };

  // Phase color definitions
  const PHASE_COLORS = {
    SOLID: '#F59E0B',
    GAS: '#EF4444',
    AIR: '#06B6D4',
    FUEL: '#A855F7',
    LIQUID: '#3B82F6',
  };

  // DOM Elements cache
  let dom = {};

  function initDom() {
    dom = {
      wrapper: document.getElementById('builderWrapper'),
      svg: document.getElementById('builderSvg'),
      wiresLayer: document.getElementById('builderWiresLayer'),
      blocksLayer: document.getElementById('builderBlocksLayer'),
      draftWire: document.getElementById('builderDraftWire'),
      graphGroup: document.getElementById('builderGraphGroup'),
      paletteScroll: document.getElementById('paletteItemsScroll'),
      paletteSearch: document.getElementById('paletteSearch'),
      accHeaderFlowsheets: document.getElementById('accHeaderFlowsheets'),
      accHeaderComponents: document.getElementById('accHeaderComponents'),
      accSectionFlowsheets: document.getElementById('accSectionFlowsheets'),
      accSectionComponents: document.getElementById('accSectionComponents'),
      arrowFlowsheets: document.getElementById('arrowFlowsheets'),
      arrowComponents: document.getElementById('arrowComponents'),
      flowsheetsListScroll: document.getElementById('flowsheetsListScroll'),
      flowsheetCountBadge: document.getElementById('flowsheetCountBadge'),
      componentCountBadge: document.getElementById('componentCountBadge'),
      tabBtnAll: document.getElementById('tabBtnAll'),
      tabBtnTemplates: document.getElementById('tabBtnTemplates'),
      tabBtnSaved: document.getElementById('tabBtnSaved'),
      tabCountAll: document.getElementById('tabCountAll'),
      tabCountTpl: document.getElementById('tabCountTpl'),
      tabCountSaved: document.getElementById('tabCountSaved'),
      btnSaveFlowsheet: document.getElementById('btnSaveFlowsheet'),
      btnNewFlowsheet: document.getElementById('btnNewFlowsheet'),
      btnExportFlowsheet: document.getElementById('btnExportFlowsheet'),
      btnImportFlowsheet: document.getElementById('btnImportFlowsheet'),
      fileImportFlowsheet: document.getElementById('fileImportFlowsheet'),
      chkGridSnap: document.getElementById('chkGridSnap'),
      gridSnapIndicator: document.getElementById('gridSnapIndicator'),
      templateSelect: document.getElementById('builderTemplateSelect'),
      inspectorTitle: document.getElementById('builderInspectorTitle'),
      inspectorBody: document.getElementById('builderInspectorBody'),
      toastContainer: document.getElementById('builderToastContainer'),
      kpiMassIn: document.getElementById('bkpiMassIn'),
      kpiMassOut: document.getElementById('bkpiMassOut'),
      kpiClosure: document.getElementById('bkpiClosure'),
      kpiFuelPower: document.getElementById('bkpiFuelPower'),
      coordDisplay: document.getElementById('builderCoordDisplay'),
      btnRunSim: document.getElementById('btnBuilderRunSim'),
      btnSolve: document.getElementById('btnBuilderSolve'),
      btnReset: document.getElementById('btnReset'),
      simStatusPill: document.getElementById('simStatusPill'),
      simStatusText: document.getElementById('simStatusText'),
      simTimeDisplay: document.getElementById('simTimeDisplay'),
      speedBtns: document.querySelectorAll('.speed-btn'),
      btnDeploy: document.getElementById('btnBuilderDeploy'),
      btnSave: document.getElementById('btnBuilderSave'),
      btnNew: document.getElementById('btnBuilderNew'),
      btnExportJson: document.getElementById('btnBuilderExportJson'),
      btnImportJson: document.getElementById('btnBuilderImportJson'),
      importFileInput: document.getElementById('builderImportFileInput'),
      btnExportCsv: document.getElementById('btnBuilderExportCsv'),
      btnZoomIn: document.getElementById('btnBuilderZoomIn'),
      btnZoomOut: document.getElementById('btnBuilderZoomOut'),
      btnZoomReset: document.getElementById('btnBuilderZoomReset'),
      btnFit: document.getElementById('btnBuilderFit'),
      scenarioSelect: document.getElementById('builderScenarioSelect'),
      btnApplyScenario: document.getElementById('btnBuilderApplyScenario'),
      btnVerifyScenarios: document.getElementById('btnBuilderVerifyScenarios'),
      scenarioBanner: document.getElementById('builderScenarioBanner'),
      verifyModal: document.getElementById('modalVerifyScenarios'),
      verifyTableBody: document.getElementById('verifyTableBody'),
      verifyPassRate: document.getElementById('verifyPassRate'),
    };
  }

  // =========================================================================
  // 1. INITIALIZATION & DATA FETCHING
  // =========================================================================

  async function init() {
    initDom();
    setupCanvasEvents();
    setupToolbarEvents();

    try {
      // 1. Fetch catalog
      const catRes = await fetch('/api/flowsheet/builder/components');
      if (catRes.ok) {
        state.catalog = await catRes.json();
        renderPalette(state.catalog);
      }

      // 2. Fetch templates
      const tplRes = await fetch('/api/flowsheet/builder/templates');
      if (tplRes.ok) {
        state.templates = await tplRes.json();
        populateTemplateSelect(state.templates);
      }

      // 2b. Fetch operational scenarios catalog
      const scnRes = await fetch('/api/flowsheet/builder/scenarios');
      if (scnRes.ok) {
        state.scenarios = await scnRes.json();
        populateScenarioSelect(state.scenarios);
      }

      // 3. Render Flowsheets Library in left sidebar
      await renderFlowsheetsLibrary();

      // 4. Check for auto-saved flowsheet layout in localStorage (exact block positions preserved)
      let restoredFromLocal = false;
      const autoSavedStr = localStorage.getItem('prosim_auto_flowsheet');
      if (autoSavedStr) {
        try {
          const autoSaved = JSON.parse(autoSavedStr);
          if (autoSaved && Array.isArray(autoSaved.components) && autoSaved.components.length > 0) {
            loadGraph(autoSaved);
            restoredFromLocal = true;
          }
        } catch (e) {
          console.warn('Auto-save restore notice:', e);
        }
      }

      if (!restoredFromLocal) {
        // 5. Fetch active flowsheet from server or fallback to default template
        const actRes = await fetch('/api/flowsheet/builder/active');
        if (actRes.ok) {
          const actData = await actRes.json();
          if (actData && actData.flowsheet && actData.flowsheet.components && actData.flowsheet.components.length > 0) {
            loadGraph(actData.flowsheet);
            updateAuditDisplays(actData.audit);
          } else {
            await loadTemplate('kiln_3_pyroprocess');
          }
        } else {
          await loadTemplate('kiln_3_pyroprocess');
        }
      }
    } catch (err) {
      console.warn('Builder initialization fallback:', err);
      loadTemplate('kiln_3_pyroprocess');
    }

    updateSimTimeDisplay();
    updateSimStatus('READY');
    renderGlobalInspector();
    setTimeout(fitGraphToView, 150);
  }

  function showToast(message, type = 'info') {
    if (!dom.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `builder-toast toast-${type}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      toast.style.transition = 'all 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  // =========================================================================
  // 2. PALETTE & TEMPLATES RENDERING
  // =========================================================================

  function renderPalette(catalog, filter = '') {
    if (!dom.paletteScroll) return;
    dom.paletteScroll.innerHTML = '';

    const categories = {};
    catalog.forEach((item) => {
      if (filter && !item.type.toLowerCase().includes(filter.toLowerCase()) &&
          !item.category.toLowerCase().includes(filter.toLowerCase())) {
        return;
      }
      categories[item.category] = categories[item.category] || [];
      categories[item.category].push(item);
    });

    const categoryIcons = {
      'Feeding': '📦',
      'Separation': '🌪',
      'Combustion': '🔥',
      'Pyroprocess': '🏭',
      'Cooling': '❄️',
      'Draft / Fans': '💨',
      'Flow Control': '🔀',
      'General': '⚙️',
    };

    Object.entries(categories).forEach(([catName, items]) => {
      const catDiv = document.createElement('div');
      catDiv.className = 'palette-category';

      const catTitle = document.createElement('div');
      catTitle.className = 'palette-category-title';
      catTitle.innerHTML = `<span>${categoryIcons[catName] || '🔹'} ${catName}</span> <span class="count">${items.length}</span>`;
      catDiv.appendChild(catTitle);

      items.forEach((item) => {
        const card = document.createElement('div');
        card.className = 'palette-block-card';
        card.setAttribute('draggable', 'true');
        card.dataset.blockType = item.type;

        const inCount = item.ports.filter(p => p.direction === 'IN').length;
        const outCount = item.ports.filter(p => p.direction === 'OUT').length;

        card.innerHTML = `
          <div class="palette-card-left">
            <div class="palette-card-icon">${getBlockIcon(item.type)}</div>
            <div class="palette-card-name" title="${item.type}">${formatBlockDisplayName(item.type)}</div>
          </div>
          <span class="palette-card-badge" title="${inCount} Inlets, ${outCount} Outlets">${inCount}I / ${outCount}O</span>
        `;

        card.addEventListener('dragstart', (e) => {
          e.dataTransfer.setData('text/plain', item.type);
          e.dataTransfer.effectAllowed = 'copy';
        });

        // Double-click to insert in canvas center
        card.addEventListener('dblclick', () => {
          const pt = getCanvasCenterPoint();
          addBlockToGraph(item.type, pt.x, pt.y);
        });

        catDiv.appendChild(card);
      });

      dom.paletteScroll.appendChild(catDiv);
    });
  }

  function populateTemplateSelect(templates) {
    if (!dom.templateSelect) return;
    dom.templateSelect.innerHTML = '<option value="">-- Load Pre-built Template --</option>';
    templates.forEach((t) => {
      const opt = document.createElement('option');
      opt.value = t.id;
      opt.textContent = `${t.name} (${t.components_count} units)`;
      dom.templateSelect.appendChild(opt);
    });
  }

  function saveAutoFlowsheet() {
    try {
      if (state.graph && Array.isArray(state.graph.components)) {
        localStorage.setItem('prosim_auto_flowsheet', JSON.stringify(state.graph));
      }
    } catch (e) {
      console.warn('Could not auto-save flowsheet:', e);
    }
  }

  async function renderFlowsheetsLibrary() {
    if (!dom.flowsheetsListScroll) return;
    dom.flowsheetsListScroll.innerHTML = '';

    // 1. Get user saved flowsheets from localStorage
    let userFlowsheets = [];
    try {
      userFlowsheets = JSON.parse(localStorage.getItem('prosim_user_flowsheets') || '[]');
    } catch (e) {
      userFlowsheets = [];
    }

    // 2. Fetch server saved flowsheets if available
    try {
      const srvRes = await fetch('/api/flowsheet/builder/list');
      if (srvRes.ok) {
        const serverList = await srvRes.json();
        serverList.forEach((sf) => {
          if (!userFlowsheets.some(uf => uf.filename === sf.filename || (uf.name === sf.name && !uf.filename))) {
            userFlowsheets.push({
              id: sf.flowsheet_id || sf.filename,
              name: sf.name || sf.filename,
              filename: sf.filename,
              blocks_count: sf.blocks_count || 0,
              streams_count: sf.streams_count || 0,
              isServer: true,
            });
          }
        });
      }
    } catch (e) {}

    // Filter out hidden/deleted templates
    let hiddenTemplates = [];
    try {
      hiddenTemplates = JSON.parse(localStorage.getItem('prosim_hidden_templates') || '[]');
    } catch (e) {
      hiddenTemplates = [];
    }
    const visibleTemplates = (state.templates || []).filter(t => !hiddenTemplates.includes(t.id));

    // Update count badges
    const totalCount = visibleTemplates.length + userFlowsheets.length;
    if (dom.flowsheetCountBadge) dom.flowsheetCountBadge.textContent = totalCount;
    if (dom.tabCountAll) dom.tabCountAll.textContent = totalCount;
    if (dom.tabCountTpl) dom.tabCountTpl.textContent = visibleTemplates.length;
    if (dom.tabCountSaved) dom.tabCountSaved.textContent = userFlowsheets.length;

    const currentTab = state.flowsheetTab || 'all';

    // RENDER TEMPLATES (if tab is 'all' or 'templates')
    if (currentTab === 'all' || currentTab === 'templates') {
      const tplHeader = document.createElement('div');
      tplHeader.style.cssText = 'font-size: 9.5px; font-weight: 700; color: #38BDF8; text-transform: uppercase; padding: 4px 2px; margin-top: 2px; margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(56, 189, 248, 0.3);';
      
      let restoreBtnHtml = '';
      if (hiddenTemplates.length > 0) {
        restoreBtnHtml = `<button class="btn-restore-tpls" title="Restore hidden plant templates" style="background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.3); color: #38BDF8; font-size: 8.5px; padding: 1px 5px; border-radius: 3px; cursor: pointer; margin-right: 6px;">↺ Restore</button>`;
      }
      
      tplHeader.innerHTML = `<span>🏭 Plant Templates</span> <div style="display:flex;align-items:center;">${restoreBtnHtml}<span style="font-family: monospace;">${visibleTemplates.length}</span></div>`;
      dom.flowsheetsListScroll.appendChild(tplHeader);

      const restoreBtn = tplHeader.querySelector('.btn-restore-tpls');
      if (restoreBtn) {
        restoreBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          localStorage.removeItem('prosim_hidden_templates');
          showToast('Restored all default plant templates', 'success');
          renderFlowsheetsLibrary();
          populateTemplateSelect(state.templates);
        });
      }

      if (visibleTemplates.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.style.cssText = 'font-size: 10px; color: #64748B; padding: 8px 4px; text-align: center; font-style: italic;';
        emptyDiv.textContent = 'All templates deleted. Click Restore to recover.';
        dom.flowsheetsListScroll.appendChild(emptyDiv);
      } else {
        visibleTemplates.forEach((t) => {
          const card = document.createElement('div');
          const isActive = state.graph && state.graph.flowsheet_id === t.id;
          card.className = `flowsheet-item-card ${isActive ? 'active' : ''}`;
          card.innerHTML = `
            <div class="fs-card-left">
              <div class="fs-card-name" title="${t.name}">${t.name}</div>
              <div class="fs-card-meta">
                <span class="fs-card-type-badge fs-badge-template">TEMPLATE</span>
                <span>${t.components_count} units • ${t.streams_count} streams</span>
              </div>
            </div>
            <div class="fs-card-actions">
              <button class="fs-card-btn btn-del-tpl" title="Delete Template from Library">🗑</button>
            </div>
          `;

          card.addEventListener('click', async (e) => {
            if (e.target.closest('.btn-del-tpl')) return;
            await loadTemplate(t.id);
            renderFlowsheetsLibrary();
          });

          const delBtn = card.querySelector('.btn-del-tpl');
          if (delBtn) {
            delBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              deleteTemplate(t, delBtn);
            });
          }

          dom.flowsheetsListScroll.appendChild(card);
        });
      }
    }

    // RENDER USER SAVED FLOWSHEETS (if tab is 'all' or 'saved')
    if (currentTab === 'all' || currentTab === 'saved') {
      const userHeader = document.createElement('div');
      userHeader.style.cssText = 'font-size: 9.5px; font-weight: 700; color: #F59E0B; text-transform: uppercase; padding: 4px 2px; margin-top: 6px; margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(245, 158, 11, 0.3);';
      userHeader.innerHTML = `<span>⭐ Saved Layouts</span> <span style="font-family: monospace;">${userFlowsheets.length}</span>`;
      dom.flowsheetsListScroll.appendChild(userHeader);

      if (userFlowsheets.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.style.cssText = 'font-size: 10px; color: #64748B; padding: 8px 4px; text-align: center; font-style: italic;';
        emptyDiv.textContent = 'No saved flowsheets yet. Click Save above to save current layout.';
        dom.flowsheetsListScroll.appendChild(emptyDiv);
      } else {
        userFlowsheets.forEach((fs) => {
          const card = document.createElement('div');
          const isActive = state.graph && (state.graph.flowsheet_id === fs.id || state.graph.name === fs.name);
          card.className = `flowsheet-item-card ${isActive ? 'active' : ''}`;
          const countStr = fs.blocks_count !== undefined ? fs.blocks_count : (fs.components ? fs.components.length : 0);
          card.innerHTML = `
            <div class="fs-card-left">
              <div class="fs-card-name" title="${fs.name}">${fs.name}</div>
              <div class="fs-card-meta">
                <span class="fs-card-type-badge fs-badge-custom">SAVED</span>
                <span>${countStr} units</span>
              </div>
            </div>
            <div class="fs-card-actions">
              <button class="fs-card-btn btn-del-fs" title="Delete Saved Flowsheet">🗑</button>
            </div>
          `;

          card.addEventListener('click', (e) => {
            if (e.target.closest('.btn-del-fs')) return;
            loadSavedFlowsheet(fs);
          });

          const delBtn = card.querySelector('.btn-del-fs');
          if (delBtn) {
            delBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              deleteSavedFlowsheet(fs, delBtn);
            });
          }

          dom.flowsheetsListScroll.appendChild(card);
        });
      }
    }
  }

  async function deleteTemplate(t, btnElement) {
    if (btnElement && !btnElement.dataset.confirming) {
      btnElement.dataset.confirming = 'true';
      btnElement.textContent = 'Sure?';
      btnElement.style.background = '#EF4444';
      btnElement.style.color = '#FFF';
      btnElement.style.borderColor = '#DC2626';
      setTimeout(() => {
        if (btnElement && btnElement.dataset.confirming) {
          delete btnElement.dataset.confirming;
          btnElement.textContent = '🗑';
          btnElement.style.background = '';
          btnElement.style.color = '';
          btnElement.style.borderColor = '';
        }
      }, 3500);
      return;
    }

    try {
      let hidden = JSON.parse(localStorage.getItem('prosim_hidden_templates') || '[]');
      if (!hidden.includes(t.id)) {
        hidden.push(t.id);
        localStorage.setItem('prosim_hidden_templates', JSON.stringify(hidden));
      }
      showToast(`Deleted template '${t.name}' from library`, 'info');
      await renderFlowsheetsLibrary();
      const visibleTemplates = (state.templates || []).filter(tpl => !hidden.includes(tpl.id));
      populateTemplateSelect(visibleTemplates);
    } catch (err) {
      showToast(`Template delete error: ${err.message}`, 'error');
    }
  }

  async function loadSavedFlowsheet(fs) {
    if (fs.components) {
      loadGraph(fs);
      saveAutoFlowsheet();
      showToast(`Loaded saved flowsheet '${fs.name}' with block grid coordinates!`, 'success');
      renderFlowsheetsLibrary();
    } else if (fs.filename) {
      try {
        const res = await fetch(`/api/flowsheet/builder/load/${fs.filename}`);
        if (res.ok) {
          const data = await res.json();
          loadGraph(data);
          saveAutoFlowsheet();
          showToast(`Loaded flowsheet '${data.name}' from server!`, 'success');
          renderFlowsheetsLibrary();
        }
      } catch (err) {
        showToast(`Failed loading flowsheet: ${err.message}`, 'error');
      }
    }
  }

  async function deleteSavedFlowsheet(fs, btnElement) {
    if (btnElement && !btnElement.dataset.confirming) {
      btnElement.dataset.confirming = 'true';
      btnElement.textContent = 'Sure?';
      btnElement.style.background = '#EF4444';
      btnElement.style.color = '#FFF';
      btnElement.style.borderColor = '#DC2626';
      setTimeout(() => {
        if (btnElement && btnElement.dataset.confirming) {
          delete btnElement.dataset.confirming;
          btnElement.textContent = '🗑';
          btnElement.style.background = '';
          btnElement.style.color = '';
          btnElement.style.borderColor = '';
        }
      }, 3500);
      return;
    }

    try {
      let userFlowsheets = JSON.parse(localStorage.getItem('prosim_user_flowsheets') || '[]');
      userFlowsheets = userFlowsheets.filter(u => u.name !== fs.name && u.id !== fs.id && u.filename !== fs.filename);
      localStorage.setItem('prosim_user_flowsheets', JSON.stringify(userFlowsheets));

      if (fs.filename) {
        await fetch('/api/flowsheet/builder/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: fs.filename })
        });
      }
      showToast(`Deleted flowsheet '${fs.name}'`, 'info');
      await renderFlowsheetsLibrary();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`, 'error');
    }
  }

  function formatBlockDisplayName(type) {
    return type
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, str => str.toUpperCase())
      .trim();
  }

  function getBlockIcon(type) {
    const icons = {
      GravimetricFeeder: '⚖️',
      FuelFeeder: '🔥',
      SiloStorage: '🛢️',
      CycloneStage: '🌪',
      CalcinerReactor: '⚡',
      RotaryKiln: '🏭',
      GrateCooler: '❄️',
      IDFan: '💨',
      StreamMixer: '🔀',
      FuelMixer: '🔀🔥',
      AirMixer: '🔀💨',
      GasMixer: '🔀♨️',
      StreamSplitter: '🔱',
      DamperValve: '🔘',
    };
    return icons[type] || '📦';
  }

  // =========================================================================
  // 3. GRAPH DATA OPERATIONS
  // =========================================================================

  function loadGraph(graphData, preserveSelection = false) {
    if (!graphData) return;
    const prevBlock = preserveSelection ? state.selectedBlockId : null;
    const prevStream = preserveSelection ? state.selectedStreamId : null;
    state.graph = JSON.parse(JSON.stringify(graphData));
    state.graph.components = state.graph.components || [];
    state.graph.connections = state.graph.connections || [];
    state.selectedBlockId = prevBlock;
    state.selectedStreamId = prevStream;

    // Defensively ensure all blocks have valid ports and state objects
    state.graph.components.forEach((block) => {
      if (!block.state) block.state = {};
      if (!block.parameters) block.parameters = {};
      if (!block.ports || typeof block.ports !== 'object' || Object.keys(block.ports).length === 0) {
        const cat = state.catalog.find(c => c.type === block.type);
        block.ports = {};
        if (cat && cat.ports) {
          cat.ports.forEach((p) => {
            block.ports[p.name] = { ...p, connected_stream_id: null };
          });
        }
      }
    });

    // Populate connected_stream_id on ports from connections
    state.graph.connections.forEach((c) => {
      if (!c.source || !c.target) return;
      const srcBlock = state.graph.components.find(b => b.id === c.source.block);
      const dstBlock = state.graph.components.find(b => b.id === c.target.block);
      if (srcBlock && srcBlock.ports && srcBlock.ports[c.source.port]) {
        srcBlock.ports[c.source.port].connected_stream_id = c.stream_id;
      }
      if (dstBlock && dstBlock.ports && dstBlock.ports[c.target.port]) {
        dstBlock.ports[c.target.port].connected_stream_id = c.stream_id;
      }
    });

    // Determine highest stream ID for counter
    let maxId = 1;
    state.graph.connections.forEach((c) => {
      if (c.stream_id && c.stream_id >= maxId) maxId = c.stream_id + 1;
    });
    state.streamCounter = maxId;

    renderGraph();
    if (prevBlock && state.graph.components.some(b => b.id === prevBlock)) {
      renderBlockInspector(prevBlock);
    } else if (prevStream && state.graph.connections.some(c => c.stream_id === prevStream)) {
      renderStreamInspector(prevStream);
    } else {
      renderGlobalInspector();
    }
    updateLiveMassAudit();
  }

  async function loadTemplate(templateId) {
    if (!templateId) return;
    try {
      const res = await fetch(`/api/flowsheet/builder/template/${templateId}`);
      if (res.ok) {
        const data = await res.json();
        loadGraph(data);
        showToast(`Template '${data.name}' loaded successfully!`, 'success');
      }
    } catch (err) {
      showToast(`Error loading template: ${err.message}`, 'error');
    }
  }

  function addBlockToGraph(blockType, x, y) {
    const catalogItem = state.catalog.find(c => c.type === blockType);
    if (!catalogItem) return;

    // Distinctive, meaningful prefix per equipment type
    const TYPE_PREFIXES = {
      'GravimetricFeeder': 'FEEDER',
      'FuelFeeder': 'FUEL_DOSER',
      'FuelMixer': 'FUEL_MIXER',
      'AirMixer': 'AIR_MIXER',
      'GasMixer': 'GAS_MIXER',
      'StreamMixer': 'MIXER',
      'StreamSplitter': 'SPLITTER',
      'DamperValve': 'DAMPER',
      'CycloneStage': 'CYCLONE',
      'CalcinerReactor': 'CALCINER',
      'RotaryKiln': 'KILN',
      'GrateCooler': 'COOLER',
      'IDFan': 'ID_FAN',
      'SiloStorage': 'SILO'
    };
    const basePrefix = TYPE_PREFIXES[blockType] || blockType.toUpperCase().replace(/[^A-Z0-9]/g, '_');

    // Generate guaranteed unique ID across all existing blocks in the flowsheet
    let idx = 1;
    let newId = `${basePrefix}_01`;
    while (state.graph.components.some(c => c.id === newId)) {
      idx++;
      newId = `${basePrefix}_${idx < 10 ? '0' + idx : idx}`;
    }

    const defaultParams = {};
    Object.entries(catalogItem.parameters || {}).forEach(([pName, pDef]) => {
      defaultParams[pName] = pDef.default;
    });

    const posX = state.gridSnapEnabled ? Math.round(x / state.gridSize) * state.gridSize : Math.round(x);
    const posY = state.gridSnapEnabled ? Math.round(y / state.gridSize) * state.gridSize : Math.round(y);

    const newBlock = {
      id: newId,
      name: `${formatBlockDisplayName(blockType)} ${idx}`,
      type: blockType,
      category: catalogItem.category,
      position: { x: posX, y: posY },
      parameters: defaultParams,
      state: {},
      ports: catalogItem.ports.reduce((acc, p) => {
        acc[p.name] = { ...p, connected_stream_id: null };
        return acc;
      }, {}),
    };

    state.graph.components.push(newBlock);
    selectBlock(newId);
    renderGraph();
    saveAutoFlowsheet();
    renderFlowsheetsLibrary();
    showToast(`Added ${newBlock.name} [${newId}]`, 'info');
  }

  function deleteBlock(blockId) {
    if (!blockId) return;
    // Remove all connected streams
    state.graph.connections = state.graph.connections.filter(
      c => c.source.block !== blockId && c.target.block !== blockId
    );
    // Remove block
    state.graph.components = state.graph.components.filter(c => c.id !== blockId);
    state.selectedBlockId = null;
    renderGraph();
    renderGlobalInspector();
    saveAutoFlowsheet();
    renderFlowsheetsLibrary();
    showToast(`Deleted equipment ${blockId}`, 'info');
  }

  function connectPorts(srcBlockId, srcPortName, dstBlockId, dstPortName) {
    if (srcBlockId === dstBlockId) {
      showToast('Cannot connect a block to itself.', 'error');
      return;
    }

    const srcBlock = state.graph.components.find(c => c.id === srcBlockId);
    const dstBlock = state.graph.components.find(c => c.id === dstBlockId);
    if (!srcBlock || !dstBlock) return;

    const srcPort = srcBlock.ports[srcPortName];
    const dstPort = dstBlock.ports[dstPortName];
    if (!srcPort || !dstPort) return;

    // Remove any existing connection into the destination port
    state.graph.connections = state.graph.connections.filter(
      c => !(c.target.block === dstBlockId && c.target.port === dstPortName)
    );

    const streamId = state.streamCounter++;
    const phase = srcPort.phase || dstPort.phase || 'SOLID';
    const streamName = `${srcBlock.name} → ${dstBlock.name}`;

    const newConnection = {
      stream_id: streamId,
      name: streamName,
      source: { block: srcBlockId, port: srcPortName },
      target: { block: dstBlockId, port: dstPortName },
      phase: phase,
      mass_flow_tph: 0.0,
      temperature_c: 25.0,
      pressure_mbar: 0.0,
      enthalpy_gjh: 0.0,
      composition: {},
    };

    state.graph.connections.push(newConnection);
    srcPort.connected_stream_id = streamId;
    dstPort.connected_stream_id = streamId;

    selectStream(streamId);
    renderGraph();
    showToast(`Stream ${streamId} connected: ${streamName}`, 'success');
  }

  function disconnectStream(streamId) {
    const conn = state.graph.connections.find(c => c.stream_id === streamId);
    if (!conn) return;

    const srcBlock = state.graph.components.find(b => b.id === conn.source.block);
    if (srcBlock && srcBlock.ports[conn.source.port]) {
      srcBlock.ports[conn.source.port].connected_stream_id = null;
    }
    const dstBlock = state.graph.components.find(b => b.id === conn.target.block);
    if (dstBlock && dstBlock.ports[conn.target.port]) {
      dstBlock.ports[conn.target.port].connected_stream_id = null;
    }

    state.graph.connections = state.graph.connections.filter(c => c.stream_id !== streamId);
    state.selectedStreamId = null;
    renderGraph();
    renderGlobalInspector();
    showToast(`Stream ${streamId} disconnected`, 'info');
  }

  // =========================================================================
  // 4. GRAPHICAL RENDERING (SVG)
  // =========================================================================

  function renderGraph() {
    if (!dom.blocksLayer || !dom.wiresLayer) return;

    dom.blocksLayer.innerHTML = '';
    dom.wiresLayer.innerHTML = '';

    // Update Transform Group
    if (dom.graphGroup) {
      dom.graphGroup.setAttribute(
        'transform',
        `translate(${state.viewTransform.panX}, ${state.viewTransform.panY}) scale(${state.viewTransform.scale})`
      );
    }

    // 1. Render Wires (Streams)
    state.graph.connections.forEach((conn) => {
      renderStreamWire(conn);
    });

    // 2. Render Blocks (Equipment)
    state.graph.components.forEach((block) => {
      renderBlockNode(block);
    });
  }

  function getBlockDimensions(block) {
    // Custom sizing per equipment
    if (block.type === 'RotaryKiln') return { width: 170, height: 95 };
    if (block.type === 'GrateCooler') return { width: 155, height: 90 };
    if (block.type === 'CalcinerReactor') return { width: 145, height: 95 };
    if (block.type === 'CycloneStage') return { width: 135, height: 85 };
    if (block.type === 'IDFan') return { width: 125, height: 75 };
    if (block.type === 'FuelMixer') return { width: 145, height: 95 };
    if (block.type === 'AirMixer') return { width: 145, height: 95 };
    if (block.type === 'GasMixer') return { width: 145, height: 95 };
    return { width: 130, height: 80 };
  }

  function getPortPosition(block, portName, portDirection) {
    const dims = getBlockDimensions(block);
    const portsList = block.ports ? (Array.isArray(block.ports) ? block.ports : Object.values(block.ports)) : [];
    const inPorts = portsList.filter(p => p && p.direction === 'IN');
    const outPorts = portsList.filter(p => p && p.direction === 'OUT');

    const x = block.position.x;
    const y = block.position.y;

    if (portDirection === 'IN') {
      const idx = inPorts.findIndex(p => p.name === portName);
      const spacing = dims.height / (inPorts.length + 1);
      return { x: x, y: y + spacing * (idx + 1) };
    } else {
      const idx = outPorts.findIndex(p => p.name === portName);
      const spacing = dims.height / (outPorts.length + 1);
      return { x: x + dims.width, y: y + spacing * (idx + 1) };
    }
  }

  function renderBlockNode(block) {
    const dims = getBlockDimensions(block);
    const isSelected = state.selectedBlockId === block.id;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.className.baseVal = `builder-block ${isSelected ? 'selected' : ''}`;
    g.dataset.blockId = block.id;
    g.setAttribute('transform', `translate(${block.position.x}, ${block.position.y})`);

    // Main Body Box
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.className.baseVal = 'builder-node-rect';
    rect.setAttribute('width', dims.width);
    rect.setAttribute('height', dims.height);
    g.appendChild(rect);

    // Header Background
    const header = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    header.className.baseVal = 'builder-node-header';
    header.setAttribute('width', dims.width);
    header.setAttribute('height', 24);
    g.appendChild(header);

    // Icon + Block ID
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    title.className.baseVal = 'builder-node-title';
    title.setAttribute('x', 8);
    title.setAttribute('y', 16);
    title.textContent = `${getBlockIcon(block.type)} ${block.name}`;
    g.appendChild(title);

    // Tag / ID
    const tag = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    tag.className.baseVal = 'builder-node-id';
    tag.setAttribute('x', dims.width - 8);
    tag.setAttribute('y', 16);
    tag.setAttribute('text-anchor', 'end');
    tag.textContent = block.id;
    g.appendChild(tag);

    // Dynamic Telemetry Readout
    const telem = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    telem.className.baseVal = 'builder-node-telemetry';
    telem.setAttribute('x', dims.width / 2);
    telem.setAttribute('y', dims.height - 12);
    telem.setAttribute('text-anchor', 'middle');
    telem.textContent = getBlockTelemetrySummary(block);
    g.appendChild(telem);

    // Ports
    const nodePorts = block.ports ? (Array.isArray(block.ports) ? block.ports : Object.values(block.ports)) : [];
    nodePorts.forEach((port) => {
      if (!port) return;
      const pos = getPortPosition(block, port.name, port.direction);
      const relX = pos.x - block.position.x;
      const relY = pos.y - block.position.y;

      const portG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      portG.className.baseVal = 'port-group';
      portG.dataset.portName = port.name;
      portG.dataset.portDirection = port.direction;
      portG.dataset.blockId = block.id;
      portG.dataset.phase = port.phase;

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.className.baseVal = `port-circle phase-${(port.phase || 'solid').toLowerCase()}`;
      circle.setAttribute('cx', relX);
      circle.setAttribute('cy', relY);
      portG.appendChild(circle);

      // Port Title tooltip
      const titleEl = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      titleEl.textContent = `${port.name} (${port.direction} | ${port.phase}): ${port.description || ''}`;
      portG.appendChild(titleEl);

      // Click / Drag Port Wiring Events
      portG.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        if (port.direction === 'OUT') {
          startPortWiring(block.id, port.name, port.phase, pos.x, pos.y);
        } else if (state.isConnectingPort) {
          finishPortWiring(block.id, port.name);
        }
      });

      portG.addEventListener('mouseup', (e) => {
        e.stopPropagation();
        if (state.isConnectingPort && port.direction === 'IN') {
          finishPortWiring(block.id, port.name);
        }
      });

      g.appendChild(portG);
    });

    // Block Drag & Click Events
    g.addEventListener('mousedown', (e) => {
      if (e.target.closest('.port-group')) return;
      e.stopPropagation();
      selectBlock(block.id);
      startBlockDrag(block.id, e);
    });

    dom.blocksLayer.appendChild(g);
  }

  function getBlockTelemetrySummary(block) {
    if (block.type === 'GravimetricFeeder') {
      const rate = block.parameters?.nominal_rate_tph !== undefined ? block.parameters.nominal_rate_tph : (block.state?.actual_feed_rate_tph || 280.0);
      const caco3 = block.parameters?.caco3_pct !== undefined ? block.parameters.caco3_pct : (block.state?.caco3_pct || 76.85);
      return `${Number(rate).toFixed(1)} t/h | CaCO3 ${Number(caco3).toFixed(1)}%`;
    }
    if (block.type === 'FuelFeeder') {
      const rate = block.parameters?.nominal_rate_tph !== undefined ? block.parameters.nominal_rate_tph : (block.state?.actual_rate_tph || 10.0);
      return `${Number(rate).toFixed(1)} t/h`;
    }
    if (block.type === 'FuelMixer') {
      const rate = block.state?.total_fuel_rate_tph || 0.0;
      const tsr = block.state?.rdf_alt_fuel_share_pct || 0.0;
      return `${Number(rate).toFixed(1)} t/h | TSR ${Number(tsr).toFixed(1)}%`;
    }
    if (block.type === 'AirMixer') {
      const rate = block.state?.total_air_tph || 0.0;
      const temp = block.state?.blended_temp_c || 25.0;
      return `${Number(rate).toFixed(1)} t/h | ${Number(temp).toFixed(0)}°C`;
    }
    if (block.type === 'GasMixer') {
      const rate = block.state?.total_gas_tph || 0.0;
      const temp = block.state?.blended_temp_c || 25.0;
      return `${Number(rate).toFixed(1)} t/h | ${Number(temp).toFixed(0)}°C`;
    }
    if (block.type === 'CycloneStage') {
      const t = block.state.meal_temp_c || 450.0;
      const dp = block.parameters.dp_mbar || 5.5;
      return `${t.toFixed(0)}°C | ΔP ${dp.toFixed(1)} mbar`;
    }
    if (block.type === 'CalcinerReactor') {
      const t = block.state.calciner_temp_c || block.parameters.target_temp_c || 865.0;
      const dec = block.state.calcination_degree_pct || 92.5;
      return `${t.toFixed(0)}°C | Calc ${dec.toFixed(1)}%`;
    }
    if (block.type === 'RotaryKiln') {
      const bz = block.state.burning_zone_temp_c || 1435.0;
      const clk = block.state.clinker_rate_tph || 175.0;
      return `BZ ${bz.toFixed(0)}°C | ${clk.toFixed(1)} t/h`;
    }
    if (block.type === 'GrateCooler') {
      const sec = block.state.secondary_air_temp_c || 1020.0;
      const clk = block.state.clinker_exit_temp_c || 95.0;
      return `SecAir ${sec.toFixed(0)}°C | Clinker ${clk.toFixed(0)}°C`;
    }
    if (block.type === 'IDFan') {
      const kw = block.state.motor_power_kw || 1845.0;
      const fl = (block.state.actual_flow_nm3h || 268500.0) / 1000.0;
      return `${kw.toFixed(0)} kW | ${fl.toFixed(0)}k Nm³/h`;
    }
    return '';
  }

  function renderStreamWire(conn) {
    const srcBlock = state.graph.components.find(b => b.id === conn.source.block);
    const dstBlock = state.graph.components.find(b => b.id === conn.target.block);
    if (!srcBlock || !dstBlock) return;

    const p1 = getPortPosition(srcBlock, conn.source.port, 'OUT');
    const p2 = getPortPosition(dstBlock, conn.target.port, 'IN');

    const dx = Math.max(50, Math.abs(p2.x - p1.x) * 0.5);
    const pathD = `M ${p1.x} ${p1.y} C ${p1.x + dx} ${p1.y}, ${p2.x - dx} ${p2.y}, ${p2.x} ${p2.y}`;

    const isSelected = state.selectedStreamId === conn.stream_id;
    const isRunning = state.isSimulating;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.className.baseVal = `stream-wire-group ${isSelected ? 'selected' : ''} ${isRunning ? 'animating' : ''}`;
    g.dataset.streamId = conn.stream_id;

    // Invisible thick wire for easy clicking
    const clickPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    clickPath.setAttribute('d', pathD);
    clickPath.setAttribute('stroke', 'transparent');
    clickPath.setAttribute('stroke-width', '16');
    clickPath.setAttribute('fill', 'none');
    clickPath.style.cursor = 'pointer';
    g.appendChild(clickPath);

    // Visible Wire
    const wirePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    wirePath.className.baseVal = `stream-wire-path phase-${(conn.phase || 'solid').toLowerCase()}`;
    wirePath.setAttribute('d', pathD);
    g.appendChild(wirePath);

    // Midpoint Stream Badge
    const midX = (p1.x + p2.x) / 2;
    const midY = (p1.y + p2.y) / 2;

    const badgeW = 68;
    const badgeH = 18;
    const badgeRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    badgeRect.className.baseVal = 'stream-badge-rect';
    badgeRect.setAttribute('x', midX - badgeW / 2);
    badgeRect.setAttribute('y', midY - badgeH / 2);
    badgeRect.setAttribute('width', badgeW);
    badgeRect.setAttribute('height', badgeH);
    g.appendChild(badgeRect);

    const badgeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    badgeText.className.baseVal = 'stream-badge-text';
    badgeText.setAttribute('x', midX);
    badgeText.setAttribute('y', midY);
    const flowStr = conn.mass_flow_tph > 0 ? `${conn.mass_flow_tph.toFixed(1)} t/h` : `#${conn.stream_id}`;
    badgeText.textContent = flowStr;
    g.appendChild(badgeText);

    // Wire Click Event
    g.addEventListener('click', (e) => {
      e.stopPropagation();
      selectStream(conn.stream_id);
    });

    dom.wiresLayer.appendChild(g);
  }

  // =========================================================================
  // 5. INTERACTION & EVENT HANDLERS
  // =========================================================================

  function setupCanvasEvents() {
    if (!dom.canvasContainer) {
      dom.canvasContainer = document.querySelector('.builder-canvas-container');
    }
    const container = dom.canvasContainer;
    if (!container) return;

    // Drag-and-drop from palette onto canvas
    container.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    });

    container.addEventListener('drop', (e) => {
      e.preventDefault();
      const blockType = e.dataTransfer.getData('text/plain');
      if (blockType) {
        const svgCoords = screenToSvgCoords(e.clientX, e.clientY);
        addBlockToGraph(blockType, svgCoords.x - 60, svgCoords.y - 40);
      }
    });

    // Canvas Background Click -> deselect
    container.addEventListener('click', (e) => {
      if (!e.target.closest('.builder-block') && !e.target.closest('.stream-wire-group')) {
        state.selectedBlockId = null;
        state.selectedStreamId = null;
        renderGraph();
        renderGlobalInspector();
      }
    });

    // Panning & Cursor Tracking
    container.addEventListener('mousedown', (e) => {
      if (e.target === dom.svg || e.target === container) {
        state.isPanning = true;
        state.panStart = { x: e.clientX - state.viewTransform.panX, y: e.clientY - state.viewTransform.panY };
        container.style.cursor = 'grabbing';
      }
    });

    window.addEventListener('mousemove', (e) => {
      // 1. Panning canvas
      if (state.isPanning) {
        state.viewTransform.panX = e.clientX - state.panStart.x;
        state.viewTransform.panY = e.clientY - state.panStart.y;
        renderGraph();
        return;
      }

      // 2. Dragging block
      if (state.isDraggingBlock && state.dragBlockId) {
        const coords = screenToSvgCoords(e.clientX, e.clientY);
        const block = state.graph.components.find(b => b.id === state.dragBlockId);
        if (block) {
          let posX = coords.x - state.dragOffset.x;
          let posY = coords.y - state.dragOffset.y;
          if (state.gridSnapEnabled) {
            posX = Math.round(posX / state.gridSize) * state.gridSize;
            posY = Math.round(posY / state.gridSize) * state.gridSize;
          }
          block.position.x = Math.round(posX);
          block.position.y = Math.round(posY);
          renderGraph();
        }
        return;
      }

      // 3. Drafting elastic connection wire
      if (state.isConnectingPort && state.connectingSource && dom.draftWire) {
        const coords = screenToSvgCoords(e.clientX, e.clientY);
        const p1 = state.connectingSource;
        const dx = Math.max(40, Math.abs(coords.x - p1.x) * 0.5);
        const d = `M ${p1.x} ${p1.y} C ${p1.x + dx} ${p1.y}, ${coords.x - dx} ${coords.y}, ${coords.x} ${coords.y}`;
        dom.draftWire.setAttribute('d', d);
      }

      // 4. Coordinates display
      if (dom.coordDisplay) {
        const svgPt = screenToSvgCoords(e.clientX, e.clientY);
        dom.coordDisplay.textContent = `X: ${Math.round(svgPt.x)} | Y: ${Math.round(svgPt.y)}`;
      }
    });

    window.addEventListener('mouseup', () => {
      if (state.isPanning) {
        state.isPanning = false;
        container.style.cursor = 'default';
      }
      if (state.isDraggingBlock) {
        const block = state.graph.components.find(b => b.id === state.dragBlockId);
        if (block && state.gridSnapEnabled) {
          block.position.x = Math.round(block.position.x / state.gridSize) * state.gridSize;
          block.position.y = Math.round(block.position.y / state.gridSize) * state.gridSize;
        }
        state.isDraggingBlock = false;
        state.dragBlockId = null;
        renderGraph();
        saveAutoFlowsheet();
      }
      if (state.isConnectingPort) {
        cancelPortWiring();
      }
    });

    // Zoom via mouse wheel
    container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
      applyZoom(zoomFactor, e.clientX, e.clientY);
    }, { passive: false });

    // Keyboard Shortcuts (Delete, Escape)
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (state.selectedBlockId) {
          deleteBlock(state.selectedBlockId);
        } else if (state.selectedStreamId) {
          disconnectStream(state.selectedStreamId);
        }
      } else if (e.key === 'Escape') {
        cancelPortWiring();
        state.selectedBlockId = null;
        state.selectedStreamId = null;
        renderGraph();
        renderGlobalInspector();
      }
    });
  }

  function screenToSvgCoords(screenX, screenY) {
    if (!dom.svg) return { x: screenX, y: screenY };
    const rect = dom.svg.getBoundingClientRect();
    const x = (screenX - rect.left - state.viewTransform.panX) / state.viewTransform.scale;
    const y = (screenY - rect.top - state.viewTransform.panY) / state.viewTransform.scale;
    return { x, y };
  }

  function getCanvasCenterPoint() {
    if (!dom.svg) return { x: 300, y: 300 };
    const rect = dom.svg.getBoundingClientRect();
    return screenToSvgCoords(rect.left + rect.width / 2, rect.top + rect.height / 2);
  }

  function applyZoom(factor, clientX, clientY) {
    const newScale = Math.min(2.5, Math.max(0.35, state.viewTransform.scale * factor));
    if (clientX !== undefined && clientY !== undefined && dom.svg) {
      const rect = dom.svg.getBoundingClientRect();
      const mouseX = clientX - rect.left;
      const mouseY = clientY - rect.top;
      state.viewTransform.panX = mouseX - (mouseX - state.viewTransform.panX) * (newScale / state.viewTransform.scale);
      state.viewTransform.panY = mouseY - (mouseY - state.viewTransform.panY) * (newScale / state.viewTransform.scale);
    }
    state.viewTransform.scale = newScale;
    renderGraph();
  }

  function startBlockDrag(blockId, mouseEvent) {
    state.isDraggingBlock = true;
    state.dragBlockId = blockId;
    const block = state.graph.components.find(b => b.id === blockId);
    if (block) {
      const coords = screenToSvgCoords(mouseEvent.clientX, mouseEvent.clientY);
      state.dragOffset = { x: coords.x - block.position.x, y: coords.y - block.position.y };
    }
  }

  function startPortWiring(blockId, portName, portPhase, startX, startY) {
    state.isConnectingPort = true;
    state.connectingSource = { blockId, portName, portPhase, x: startX, y: startY };
    if (dom.draftWire) {
      dom.draftWire.setAttribute('d', `M ${startX} ${startY} L ${startX} ${startY}`);
      dom.draftWire.style.display = 'block';
    }
  }

  function finishPortWiring(targetBlockId, targetPortName) {
    if (!state.isConnectingPort || !state.connectingSource) return;
    const src = state.connectingSource;
    cancelPortWiring();
    connectPorts(src.blockId, src.portName, targetBlockId, targetPortName);
  }

  function cancelPortWiring() {
    state.isConnectingPort = false;
    state.connectingSource = null;
    if (dom.draftWire) {
      dom.draftWire.style.display = 'none';
      dom.draftWire.setAttribute('d', '');
    }
  }

  function selectBlock(blockId) {
    state.selectedBlockId = blockId;
    state.selectedStreamId = null;
    renderGraph();
    renderBlockInspector(blockId);
  }

  function selectStream(streamId) {
    state.selectedStreamId = streamId;
    state.selectedBlockId = null;
    renderGraph();
    renderStreamInspector(streamId);
  }

  // =========================================================================
  // 6. INSPECTOR PANELS (BLOCK, STREAM & GLOBAL)
  // =========================================================================

  function renderGlobalInspector() {
    if (!dom.inspectorTitle || !dom.inspectorBody) return;
    dom.inspectorTitle.textContent = 'Flowsheet Overview';

    const compCount = state.graph.components.length;
    const connCount = state.graph.connections.length;

    dom.inspectorBody.innerHTML = `
      <div class="inspector-section">
        <div class="inspector-section-title">PROJECT METADATA</div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Flowsheet Name</span>
          <input type="text" class="inspector-prop-input" style="width: 150px; text-align: left;" id="inpFsName" value="${state.graph.name}">
        </div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Equipment Units</span>
          <strong class="cyan">${compCount}</strong>
        </div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Process Streams</span>
          <strong class="amber">${connCount}</strong>
        </div>
      </div>

      <div class="inspector-section">
        <div class="inspector-section-title">SIMULATION CONTROL</div>
        <p style="font-size: 11px; color: #94A3B8; margin: 0 0 8px 0;">
          Solve mass and thermal balances or run coupled dynamic integration across all connected units.
        </p>
        <button class="btn btn-sm btn-primary" id="btnInspSolve" style="width: 100%; margin-bottom: 6px;">⚡ Solve Balances Now</button>
        <button class="btn btn-sm btn-outline" id="btnInspDeploy" style="width: 100%;">🔌 Bridge to OPC UA Server</button>
      </div>

      <div class="inspector-section">
        <div class="inspector-section-title">INSTRUCTIONS</div>
        <ul style="font-size: 10.5px; color: #94A3B8; padding-left: 16px; margin: 0; line-height: 1.5;">
          <li>Drag equipment from the left palette to canvas.</li>
          <li>Click output ports (right) and drag wire to input ports (left).</li>
          <li>Click any unit or stream to inspect parameters.</li>
          <li>Press Delete or Backspace to remove selected items.</li>
        </ul>
      </div>
    `;

    const inpName = document.getElementById('inpFsName');
    if (inpName) {
      inpName.addEventListener('change', (e) => {
        state.graph.name = e.target.value;
      });
    }

    const btnInspSolve = document.getElementById('btnInspSolve');
    if (btnInspSolve) btnInspSolve.addEventListener('click', solveSteadyState);

    const btnInspDeploy = document.getElementById('btnInspDeploy');
    if (btnInspDeploy) btnInspDeploy.addEventListener('click', deployToOpcUa);
  }

  function renderBlockInspector(blockId) {
    if (!dom.inspectorTitle || !dom.inspectorBody) return;
    const block = state.graph.components.find(b => b.id === blockId);
    if (!block) return renderGlobalInspector();

    dom.inspectorTitle.textContent = `${block.name} (${block.id})`;

    const catalogItem = state.catalog.find(c => c.type === block.type);
    const paramSchema = catalogItem ? catalogItem.parameters : {};

    let presetsHtml = '';
    if (block.type === 'GravimetricFeeder') {
      presetsHtml = `
        <div class="inspector-section">
          <div class="inspector-section-title">🧪 RAW FEED MINERAL ASSAY PRESETS</div>
          <div class="inspector-prop-row">
            <span class="inspector-prop-label">Assay Recipe</span>
            <select class="inspector-prop-input" id="selFeedPreset" style="width: 155px; text-align: left; padding: 2px 4px; font-size: 11px;">
              <option value="" disabled selected>-- Select Mineral Preset --</option>
              <option value="lime_high_ca">💎 High-Purity Limestone (Lime Kiln)</option>
              <option value="cement_std">🏭 Standard Cement Raw Meal</option>
              <option value="lime_dolomitic">🪨 Low-Grade / Dolomitic Stone</option>
              <option value="clay_silica">🌾 Argillaceous Clay / Sandstone</option>
              <option value="iron_ore">⛏️ Iron Ore Corrective</option>
            </select>
          </div>
          <div style="font-size: 10px; color: #94A3B8; margin-top: 4px; line-height: 1.4;">
            Selecting a preset loads CaCO₃, MgCO₃, SiO₂, Al₂O₃, Fe₂O₃ and moisture assays into parameters automatically.
          </div>
        </div>
      `;
    }

    let paramsHtml = '';
    Object.entries(paramSchema).forEach(([pName, pDef]) => {
      const val = block.parameters[pName] !== undefined ? block.parameters[pName] : pDef.default;
      const isStr = (pDef && (pDef.type === 'str' || pDef.type === 'string')) || typeof val === 'string';
      const isBool = (pDef && (pDef.type === 'bool' || pDef.type === 'boolean')) || typeof val === 'boolean';
      let inputEl;
      if (isBool) {
        inputEl = `<input type="checkbox" class="inspector-prop-checkbox" data-param="${pName}" ${val ? 'checked' : ''} style="margin-left: auto;">`;
      } else if (isStr) {
        inputEl = `<input type="text" class="inspector-prop-input" data-param="${pName}" value="${val ?? ''}" style="width: 140px; text-align: left;">`;
      } else {
        inputEl = `<input type="number" step="${pDef.type === 'int' ? '1' : 'any'}" class="inspector-prop-input" data-param="${pName}" value="${val ?? 0}">`;
      }
      paramsHtml += `
        <div class="inspector-prop-row">
          <span class="inspector-prop-label" title="${pName}">${pDef.label || pName} (${pDef.unit || '-'})</span>
          ${inputEl}
        </div>
      `;
    });

    let telemHtml = '';
    Object.entries(block.state || {}).forEach(([k, v]) => {
      if (typeof v === 'number') {
        telemHtml += `
          <div class="inspector-stat-box" data-key="${k}">
            <span class="lbl">${k.replace(/_/g, ' ')}</span>
            <span class="val cyan">${v.toFixed(1)}</span>
          </div>
        `;
      }
    });

    let opcTagsHtml = '';
    Object.keys(paramSchema).forEach((pName) => {
      const pDef = paramSchema[pName] || {};
      opcTagsHtml += `
        <div class="inspector-prop-row" style="margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px dashed rgba(255,255,255,0.06);">
          <div style="display: flex; flex-direction: column; overflow: hidden;">
            <span style="font-size: 11px; font-weight: 500; color: #E2E8F0;">${pDef.label || pName} <span style="font-size: 9px; padding: 1px 4px; border-radius: 3px; background: rgba(59, 130, 246, 0.2); color: #60A5FA;">SP</span></span>
            <span style="font-size: 10px; font-family: monospace; color: #38BDF8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="ns=2;s=${block.id}_SP_${pName.toUpperCase()}">ns=2;s=${block.id}_SP_${pName.toUpperCase()}</span>
          </div>
          <span style="font-size: 10px; color: #10B981; font-weight: 600; white-space: nowrap;">Read/Write</span>
        </div>
      `;
    });
    Object.entries(block.state || {}).slice(0, 4).forEach(([k, v]) => {
      if (typeof v === 'number') {
        opcTagsHtml += `
          <div class="inspector-prop-row" style="margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px dashed rgba(255,255,255,0.06);">
            <div style="display: flex; flex-direction: column; overflow: hidden;">
              <span style="font-size: 11px; font-weight: 500; color: #E2E8F0;">${k.replace(/_/g, ' ')} <span style="font-size: 9px; padding: 1px 4px; border-radius: 3px; background: rgba(16, 185, 129, 0.2); color: #34D399;">PV</span></span>
              <span style="font-size: 10px; font-family: monospace; color: #38BDF8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="ns=2;s=${block.id}_${k.toUpperCase()}">ns=2;s=${block.id}_${k.toUpperCase()}</span>
            </div>
            <span style="font-size: 10px; color: #94A3B8; white-space: nowrap;">Read</span>
          </div>
        `;
      }
    });

    dom.inspectorBody.innerHTML = `
      <div class="inspector-section">
        <div class="inspector-section-title">EQUIPMENT INFO</div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Block ID</span>
          <input type="text" class="inspector-prop-input" style="width: 140px; text-align: left; font-family: monospace; font-weight: 700; color: #38BDF8;" id="inpBlockId" value="${block.id}" title="Unique equipment ID - used in OPC UA node addresses and connections">
        </div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Type</span>
          <span>${block.type}</span>
        </div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Name</span>
          <input type="text" class="inspector-prop-input" style="width: 140px; text-align: left;" id="inpBlockName" value="${block.name}">
        </div>
      </div>

      ${presetsHtml}

      <div class="inspector-section">
        <div class="inspector-section-title">CONFIGURABLE PARAMETERS</div>
        ${paramsHtml || '<p style="color: #64748B; font-size: 11px;">No parameters</p>'}
      </div>

      ${telemHtml ? `
        <div class="inspector-section">
          <div class="inspector-section-title">LIVE TELEMETRY</div>
          <div class="inspector-stat-grid">${telemHtml}</div>
        </div>
      ` : ''}

      <div class="inspector-section">
        <div class="inspector-section-title" style="display: flex; justify-content: space-between; align-items: center;">
          <span>OPC UA TAG MAPPINGS</span>
          <span style="font-size: 10px; color: #38BDF8; font-weight: normal;">Digital Twin</span>
        </div>
        ${opcTagsHtml || '<p style="color: #64748B; font-size: 11px;">No tags mapped</p>'}
        <button class="btn btn-sm btn-outline" id="btnInspOpenTagStudio" style="width: 100%; margin-top: 8px;">📡 Open in Tag & OPC Studio</button>
      </div>

      <div class="inspector-section">
        <button class="btn btn-sm btn-danger" id="btnDeleteBlock" style="width: 100%;">🗑 Delete Equipment</button>
      </div>
    `;

    const selPreset = document.getElementById('selFeedPreset');
    if (selPreset) {
      selPreset.addEventListener('change', (e) => {
        const presets = {
          cement_std: { caco3_pct: 76.85, mgco3_pct: 2.15, sio2_pct: 13.50, al2o3_pct: 3.45, fe2o3_pct: 2.10, moisture_pct: 0.8 },
          lime_high_ca: { caco3_pct: 94.50, mgco3_pct: 1.80, sio2_pct: 2.20, al2o3_pct: 0.60, fe2o3_pct: 0.40, moisture_pct: 1.2 },
          lime_dolomitic: { caco3_pct: 78.00, mgco3_pct: 15.00, sio2_pct: 4.50, al2o3_pct: 1.20, fe2o3_pct: 0.80, moisture_pct: 1.0 },
          clay_silica: { caco3_pct: 12.00, mgco3_pct: 1.50, sio2_pct: 58.00, al2o3_pct: 18.50, fe2o3_pct: 6.20, moisture_pct: 3.5 },
          iron_ore: { caco3_pct: 8.00, mgco3_pct: 0.50, sio2_pct: 14.00, al2o3_pct: 5.00, fe2o3_pct: 65.00, moisture_pct: 2.0 },
        };
        const p = presets[e.target.value];
        if (p) {
          Object.assign(block.parameters, p);
          renderBlockInspector(blockId);
          renderGraph();
          fetch('/api/flowsheet/builder/param', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ block_id: block.id, parameters: block.parameters })
          }).catch(() => {});
        }
      });
    }

    const btnInspTagStudio = document.getElementById('btnInspOpenTagStudio');
    if (btnInspTagStudio) {
      btnInspTagStudio.addEventListener('click', () => {
        if (window.openTagStudio) {
          window.openTagStudio(block.id);
        } else {
          document.getElementById('btnTagStudio')?.click();
        }
      });
    }

    // Input Events
    const inpBlockId = document.getElementById('inpBlockId');
    if (inpBlockId) {
      inpBlockId.addEventListener('change', (e) => {
        const rawNewId = e.target.value.trim().toUpperCase().replace(/[^A-Z0-9_]/g, '_');
        if (!rawNewId) {
          showToast('Block ID cannot be empty', 'error');
          e.target.value = block.id;
          return;
        }
        if (rawNewId === block.id) return;

        // Check uniqueness across entire graph
        if (state.graph.components.some(c => c.id === rawNewId)) {
          showToast(`Block ID '${rawNewId}' already in use! Must be unique.`, 'error');
          e.target.value = block.id;
          return;
        }

        const oldId = block.id;
        const newId = rawNewId;
        block.id = newId;

        // Cascade rename across all connected stream wires
        (state.graph.connections || []).forEach(conn => {
          if (conn.source && conn.source.block === oldId) {
            conn.source.block = newId;
          }
          if (conn.target && conn.target.block === oldId) {
            conn.target.block = newId;
          }
        });

        // Update active selection ID
        state.selectedBlockId = newId;

        // Sync with backend active graph
        fetch('/api/flowsheet/builder/rename', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ old_block_id: oldId, new_block_id: newId })
        }).catch(() => {});

        showToast(`Block ID renamed: '${oldId}' ➔ '${newId}'. OPC UA address updated!`, 'success');

        renderGraph();
        renderBlockInspector(newId);
      });
    }

    const inpName = document.getElementById('inpBlockName');
    if (inpName) {
      inpName.addEventListener('change', (e) => {
        block.name = e.target.value;
        renderGraph();
      });
    }

    dom.inspectorBody.querySelectorAll('.inspector-prop-input[data-param], .inspector-prop-checkbox[data-param]').forEach((inp) => {
      const handleParamUpdate = (e) => {
        const paramName = e.target.dataset.param;
        const pDef = paramSchema ? paramSchema[paramName] : null;
        const isBool = (pDef && (pDef.type === 'bool' || pDef.type === 'boolean')) || typeof (block.parameters[paramName]) === 'boolean';
        const isStr = (pDef && (pDef.type === 'str' || pDef.type === 'string')) || typeof (block.parameters[paramName]) === 'string';
        let val;
        if (isBool) {
          val = !!e.target.checked;
          block.parameters[paramName] = val;
        } else if (isStr) {
          val = e.target.value;
          block.parameters[paramName] = val;
        } else if (pDef && pDef.type === 'int') {
          val = parseInt(e.target.value, 10) || 0;
          block.parameters[paramName] = val;
        } else {
          val = parseFloat(e.target.value);
          if (isNaN(val)) val = 0;
          block.parameters[paramName] = val;
        }

        // Live propagate to block state, outgoing streams, and DCS controls
        if (block.type === 'GravimetricFeeder' && paramName === 'nominal_rate_tph') {
          if (!block.state) block.state = {};
          block.state.actual_feed_rate_tph = val;
          // Update outgoing stream #1
          const outConn = (state.graph.connections || []).find(c => c.source.block === block.id);
          if (outConn) outConn.mass_flow_tph = val;
          // Sync with browser global plant & DCS faceplate if available
          if (window.plant) window.plant.rawMealFeed = val;
          const spFeedEl = document.getElementById('sp_feed');
          if (spFeedEl) spFeedEl.value = val;
          const sldFeedEl = document.getElementById('slider_feed');
          if (sldFeedEl) sldFeedEl.value = val;
          if (window.controls && window.controls.ficFeed) {
            window.controls.ficFeed.sp = val;
            window.controls.ficFeed.op = val;
          }
          fetch('/api/setpoint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ loop: 'feed', value: val })
          }).catch(() => {});
        } else if (block.type === 'FuelFeeder' && paramName === 'nominal_rate_tph') {
          if (!block.state) block.state = {};
          block.state.actual_rate_tph = val;
          const outConn = (state.graph.connections || []).find(c => c.source.block === block.id);
          if (outConn) outConn.mass_flow_tph = val;
        } else if (block.type === 'GrateCooler' && paramName === 'cooling_air_total_tph') {
          if (!block.state) block.state = {};
          block.state.actual_cooling_air_tph = val;
        }

        // Notify server modular engine manager of parameter update and sync live solved telemetry
        fetch('/api/flowsheet/builder/param', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ block_id: block.id, param_name: paramName, value: val })
        })
        .then(res => res.json())
        .then(data => {
          if (data && data.status === 'success') {
            applyServerResults(data.telemetry, data.stream_table, data.audit);
            // Update live inspector card of currently selected block
            const currentBlock = state.graph.components.find(c => c.id === blockId);
            if (currentBlock && currentBlock.state) {
              Object.entries(currentBlock.state).forEach(([k, v]) => {
                if (typeof v === 'number') {
                  const valEl = dom.inspectorBody.querySelector(`.inspector-stat-box[data-key="${k}"] .val`);
                  if (valEl) valEl.textContent = v.toFixed(1);
                }
              });
            }
            updateLiveMassAudit();
            renderGraph();
          }
        })
        .catch(() => {});
      };

      inp.addEventListener('input', handleParamUpdate);
      inp.addEventListener('change', handleParamUpdate);
    });

    const btnDel = document.getElementById('btnDeleteBlock');
    if (btnDel) {
      btnDel.addEventListener('click', () => deleteBlock(blockId));
    }
  }

  function renderStreamInspector(streamId) {
    if (!dom.inspectorTitle || !dom.inspectorBody) return;
    const conn = state.graph.connections.find(c => c.stream_id === streamId);
    if (!conn) return renderGlobalInspector();

    dom.inspectorTitle.textContent = `Stream ${conn.stream_id}: ${conn.name}`;

    const compRows = Object.entries(conn.composition || {}).map(([k, v]) => `
      <div class="inspector-prop-row">
        <span class="inspector-prop-label">${k}</span>
        <span class="cyan font-mono">${typeof v === 'number' ? v.toFixed(2) + '%' : v}</span>
      </div>
    `).join('');

    dom.inspectorBody.innerHTML = `
      <div class="inspector-section">
        <div class="inspector-section-title">STREAM ROUTE</div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Stream ID</span>
          <strong class="amber">#${conn.stream_id}</strong>
        </div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Phase</span>
          <span class="badge-sm phase-${(conn.phase || 'solid').toLowerCase()}">${conn.phase}</span>
        </div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Source</span>
          <span>${conn.source.block} : ${conn.source.port}</span>
        </div>
        <div class="inspector-prop-row">
          <span class="inspector-prop-label">Target</span>
          <span>${conn.target.block} : ${conn.target.port}</span>
        </div>
      </div>

      <div class="inspector-section">
        <div class="inspector-section-title">THERMODYNAMIC PROPERTIES</div>
        <div class="inspector-stat-grid">
          <div class="inspector-stat-box">
            <span class="lbl">MASS FLOW</span>
            <span class="val cyan">${(conn.mass_flow_tph || 0).toFixed(2)} t/h</span>
          </div>
          <div class="inspector-stat-box">
            <span class="lbl">TEMPERATURE</span>
            <span class="val amber">${(conn.temperature_c || 25).toFixed(1)} °C</span>
          </div>
          <div class="inspector-stat-box">
            <span class="lbl">PRESSURE / DRAFT</span>
            <span class="val">${(conn.pressure_mbar || 0).toFixed(1)} mbar</span>
          </div>
          <div class="inspector-stat-box">
            <span class="lbl">ENTHALPY FLOW</span>
            <span class="val purple">${(conn.enthalpy_gjh || 0).toFixed(2)} GJ/h</span>
          </div>
        </div>
      </div>

      ${compRows ? `
        <div class="inspector-section">
          <div class="inspector-section-title">CHEMICAL ASSAY / SPECIES</div>
          ${compRows}
        </div>
      ` : ''}

      <div class="inspector-section">
        <button class="btn btn-sm btn-danger" id="btnDelStream" style="width: 100%;">🔌 Disconnect Stream</button>
      </div>
    `;

    const btnDel = document.getElementById('btnDelStream');
    if (btnDel) {
      btnDel.addEventListener('click', () => disconnectStream(streamId));
    }
  }

  /**
   * Merges solver telemetry + stream table returned by the backend into the local graph.
   * Telemetry entries are envelopes {block_id, state: {...}, parameters: {...}} — only the
   * inner state/parameters are merged so canvas cards and inspector see the solved values.
   */
  function applyServerResults(telemetry, streamTable, audit) {
    if (telemetry) {
      Object.entries(telemetry).forEach(([bId, telem]) => {
        const comp = state.graph.components.find(c => c.id === bId);
        if (!comp || !telem) return;
        const innerState = telem.state || {};
        comp.state = { ...(comp.state || {}), ...innerState };
        if (telem.parameters) {
          comp.parameters = { ...(comp.parameters || {}), ...telem.parameters };
        }
      });
    }
    if (streamTable) {
      streamTable.forEach(s => {
        const conn = (state.graph.connections || []).find(c => c.stream_id === s.stream_id);
        if (conn) {
          conn.mass_flow_tph = s.mass_flow_tph;
          conn.temperature_c = s.temperature_c;
          conn.pressure_mbar = s.pressure_mbar;
          if (s.enthalpy_gjh !== undefined) conn.enthalpy_gjh = s.enthalpy_gjh;
          if (s.composition) conn.composition = s.composition;
        }
      });
    }
    if (audit) updateAuditDisplays(audit);
  }

  // =========================================================================
  // OPERATIONAL SCENARIOS
  // =========================================================================

  function populateScenarioSelect(scenarios) {
    if (!dom.scenarioSelect || !Array.isArray(scenarios)) return;
    dom.scenarioSelect.innerHTML = '<option value="">-- Operational Scenario --</option>';
    const groups = {};
    scenarios.forEach(s => { (groups[s.category] = groups[s.category] || []).push(s); });
    Object.entries(groups).forEach(([cat, items]) => {
      const og = document.createElement('optgroup');
      og.label = cat;
      items.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = `${s.icon} ${s.name}`;
        og.appendChild(opt);
      });
      dom.scenarioSelect.appendChild(og);
    });
  }

  function showScenarioBanner(scn, validation) {
    if (!dom.scenarioBanner || !scn) return;
    const sev = (scn.severity || 'NORMAL').toLowerCase();
    const borderColors = { normal: '#38BDF8', optimized: '#34D399', warning: '#FBBF24', critical: '#F87171' };
    document.getElementById('scenarioBannerIcon').textContent = scn.icon || '⚖️';
    document.getElementById('scenarioBannerTitle').textContent = scn.name;
    document.getElementById('scenarioBannerDesc').textContent = scn.description;
    document.getElementById('scenarioCatBadge').textContent = scn.category;
    const sevBadge = document.getElementById('scenarioSeverityBadge');
    sevBadge.textContent = scn.severity;
    sevBadge.className = `scenario-severity-badge severity-${sev}`;
    const valBadge = document.getElementById('scenarioValidationBadge');
    const passed = validation ? validation.all_passed : true;
    const n = validation ? validation.checks_count : 0;
    valBadge.textContent = passed ? `✓ ${n}/${n} Physics Checks Met` : '✕ Physics Check Deviation';
    valBadge.className = `scenario-validation-badge ${passed ? 'badge-pass' : 'badge-fail'}`;
    dom.scenarioBanner.style.borderLeftColor = borderColors[sev] || '#38BDF8';
    dom.scenarioBanner.style.display = 'flex';
  }

  async function applySelectedScenario() {
    const scenarioId = dom.scenarioSelect ? dom.scenarioSelect.value : '';
    if (!scenarioId) {
      showToast('Select an operational scenario first.', 'error');
      return;
    }
    if (dom.btnApplyScenario) dom.btnApplyScenario.innerHTML = '⏳ Applying...';
    try {
      const res = await fetch('/api/flowsheet/builder/scenarios/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_id: scenarioId }),
      });
      const data = await res.json();
      if (data.status !== 'success') {
        showToast(`Scenario error: ${data.message || 'unknown'}`, 'error');
        return;
      }
      applyServerResults(data.telemetry, data.stream_table, data.audit);
      renderGraph();
      if (state.selectedBlockId) renderBlockInspector(state.selectedBlockId);
      else if (state.selectedStreamId) renderStreamInspector(state.selectedStreamId);
      else renderGlobalInspector();
      updateLiveMassAudit();
      showScenarioBanner(data.scenario, data.validation);
      const calc = data.telemetry?.CALC_01?.state || {};
      const kiln = data.telemetry?.KILN_01?.state || {};
      showToast(`${data.scenario.name}: PC ${calc.calciner_temp_c}°C · BZT ${kiln.burning_zone_temp_c}°C · f-CaO ${kiln.free_lime_pct}%`, data.validation?.all_passed ? 'success' : 'error');
    } catch (err) {
      showToast(`Scenario request failed: ${err.message}`, 'error');
    } finally {
      if (dom.btnApplyScenario) dom.btnApplyScenario.innerHTML = '🎯 Apply';
    }
  }

  async function verifyAllScenarios() {
    if (dom.btnVerifyScenarios) dom.btnVerifyScenarios.innerHTML = '⏳ Verifying...';
    try {
      const res = await fetch('/api/flowsheet/builder/scenarios/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      const report = await res.json();
      if (!report || !Array.isArray(report.results)) {
        showToast(`Verification failed: ${report?.message || 'unknown'}`, 'error');
        return;
      }
      if (dom.verifyPassRate) {
        dom.verifyPassRate.textContent = `${report.passed_scenarios} / ${report.total_scenarios} PASSED (${report.success_rate_pct}%)`;
        dom.verifyPassRate.style.color = report.all_passed ? '#34D399' : '#F87171';
      }
      if (dom.verifyTableBody) {
        const fmt = (v, d = 1) => (typeof v === 'number' ? v.toFixed(d) : '—');
        dom.verifyTableBody.innerHTML = report.results.map(r => {
          const t = r.telemetry_sample || {};
          const failed = (r.validation_details || []).filter(v => !v.passed).map(v => `${v.metric}: ${v.actual} (exp ${v.expected})`).join('; ');
          const badge = r.passed
            ? '<span class="status-badge-pass">PASS</span>'
            : `<span class="status-badge-pass" style="background:rgba(248,113,113,.2);color:#F87171;border-color:#DC2626;" title="${failed}">FAIL</span>`;
          return `<tr>
            <td style="font-family:inherit;">${r.name}</td>
            <td style="font-family:inherit;color:#94A3B8;">${r.category || ''}</td>
            <td>${fmt(t.calciner_temp_c)} °C</td>
            <td>${fmt(t.decarb_pct)}</td>
            <td>${fmt(t.bzt_c)}</td>
            <td>${fmt(t.free_lime_pct, 2)}</td>
            <td>${fmt(r.mass_closure_pct, 2)}%</td>
            <td>${badge}</td>
          </tr>`;
        }).join('');
      }
      if (dom.verifyModal) dom.verifyModal.style.display = 'flex';

      // Server restores nominal baseline after the sweep — resync canvas
      const actRes = await fetch('/api/flowsheet/builder/active');
      if (actRes.ok) {
        const act = await actRes.json();
        applyServerResults(act.telemetry, act.stream_table, act.audit);
        renderGraph();
        renderGlobalInspector();
      }
      if (dom.scenarioBanner) dom.scenarioBanner.style.display = 'none';
    } catch (err) {
      showToast(`Verification request failed: ${err.message}`, 'error');
    } finally {
      if (dom.btnVerifyScenarios) dom.btnVerifyScenarios.innerHTML = '🧪 Verify All';
    }
  }

  function updateAuditDisplays(audit) {
    if (!audit) return;
    if (dom.kpiMassIn) dom.kpiMassIn.textContent = `${(audit.mass_in_tph || 0).toFixed(1)} t/h`;
    if (dom.kpiMassOut) dom.kpiMassOut.textContent = `${(audit.mass_out_tph || 0).toFixed(1)} t/h`;
    if (dom.kpiClosure) dom.kpiClosure.textContent = `${(audit.mass_closure_pct || 100).toFixed(1)}%`;
    if (dom.kpiFuelPower) {
      const mw = (audit.heat_in_gjh || 0) / 3.6;
      dom.kpiFuelPower.textContent = `${mw.toFixed(1)} MW`;
    }
  }

  function updateLiveMassAudit() {
    let massIn = 0.0;
    let massOut = 0.0;
    let fuelEnergyGj = 0.0;

    (state.graph.components || []).forEach((b) => {
      if (b.type === 'GravimetricFeeder') {
        const rate = parseFloat(b.parameters?.nominal_rate_tph) || 0.0;
        massIn += rate;
      } else if (b.type === 'FuelFeeder') {
        const rate = parseFloat(b.parameters?.nominal_rate_tph) || 0.0;
        const lhv = parseFloat(b.parameters?.lhv_mj_kg) || 27.5;
        massIn += rate;
        fuelEnergyGj += rate * lhv;
      } else if (b.type === 'GrateCooler') {
        const air = parseFloat(b.parameters?.cooling_air_total_tph) || 348.5;
        massIn += air;
      } else if (b.type === 'SiloStorage') {
        const inConn = (state.graph.connections || []).find(c => c.target.block === b.id);
        if (inConn) massOut += inConn.mass_flow_tph || 0.0;
      } else if (b.type === 'IDFan') {
        const inConn = (state.graph.connections || []).find(c => c.target.block === b.id);
        if (inConn) massOut += inConn.mass_flow_tph || 0.0;
      }
    });

    if (dom.kpiMassIn) dom.kpiMassIn.textContent = `${massIn.toFixed(1)} t/h`;
    if (massOut > 0 && dom.kpiMassOut) dom.kpiMassOut.textContent = `${massOut.toFixed(1)} t/h`;
    if (fuelEnergyGj > 0 && dom.kpiFuelPower) {
      dom.kpiFuelPower.textContent = `${(fuelEnergyGj / 3.6).toFixed(1)} MW`;
    }
  }

  // =========================================================================
  // 7. TOOLBAR ACTIONS & SOLVER INTEGRATION
  // =========================================================================

  function setupToolbarEvents() {
    // 1. Template Selector
    if (dom.templateSelect) {
      dom.templateSelect.addEventListener('change', (e) => {
        if (e.target.value) {
          loadTemplate(e.target.value);
        }
      });
    }

    // 1b. Operational Scenarios
    if (dom.btnApplyScenario) dom.btnApplyScenario.addEventListener('click', applySelectedScenario);
    if (dom.btnVerifyScenarios) dom.btnVerifyScenarios.addEventListener('click', verifyAllScenarios);
    const btnDismiss = document.getElementById('btnScenarioDismiss');
    if (btnDismiss) btnDismiss.addEventListener('click', () => { dom.scenarioBanner.style.display = 'none'; });
    const closeVerify = () => { if (dom.verifyModal) dom.verifyModal.style.display = 'none'; };
    const btnVClose = document.getElementById('btnVerifyModalClose');
    if (btnVClose) btnVClose.addEventListener('click', closeVerify);
    const vBackdrop = document.getElementById('modalVerifyScenariosBackdrop');
    if (vBackdrop) vBackdrop.addEventListener('click', closeVerify);

    // 2. Palette Search
    if (dom.paletteSearch) {
      dom.paletteSearch.addEventListener('input', (e) => {
        renderPalette(state.catalog, e.target.value);
      });
    }

    // 3. Solve Steady-State
    if (dom.btnSolve) dom.btnSolve.addEventListener('click', solveSteadyState);

    // 3b. Reset to Nominal Baseline
    if (dom.btnReset) {
      dom.btnReset.addEventListener('click', async () => {
        if (confirm('Reset flowsheet to nominal Kiln 3 steady-state baseline?')) {
          if (state.isSimulating) toggleSimulation();
          await loadTemplate('kiln_3_pyroprocess');
          await solveSteadyState();
          state.simulationTime = 0.0;
          updateSimTimeDisplay();
          updateSimStatus('READY');
          showToast('Reset to nominal baseline steady state', 'info');
        }
      });
    }

    // 3c. Dynamic Speed Buttons
    if (dom.speedBtns && dom.speedBtns.length > 0) {
      dom.speedBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          dom.speedBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const spd = parseFloat(btn.getAttribute('data-speed')) || 1.0;
          state.simSpeed = spd;
          if (state.isSimulating) {
            clearInterval(state.simInterval);
            const intervalMs = Math.max(60, Math.round(500 / state.simSpeed));
            state.simInterval = setInterval(runDynamicStep, intervalMs);
          }
          showToast(`Simulation speed set to ${spd}x`, 'info');
        });
      });
    }

    // 4. Run / Pause Dynamic Simulation
    if (dom.btnRunSim) dom.btnRunSim.addEventListener('click', toggleSimulation);

    // 5. Deploy to OPC UA
    if (dom.btnDeploy) dom.btnDeploy.addEventListener('click', deployToOpcUa);

    // 6. Save Flowsheet
    if (dom.btnSave) dom.btnSave.addEventListener('click', saveFlowsheet);

    // 7. New Flowsheet
    if (dom.btnNew) {
      dom.btnNew.addEventListener('click', () => {
        if (confirm('Create a new blank flowsheet? Unsaved changes will be discarded.')) {
          state.graph = {
            flowsheet_id: 'new_flowsheet',
            name: 'New Custom Flowsheet',
            version: '2.0',
            description: '',
            components: [],
            connections: [],
          };
          loadGraph(state.graph);
          showToast('New flowsheet created', 'info');
        }
      });
    }

    // 8. Export JSON
    if (dom.btnExportJson) {
      dom.btnExportJson.addEventListener('click', () => {
        const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(state.graph, null, 2));
        const a = document.createElement('a');
        a.href = dataStr;
        a.download = `${state.graph.flowsheet_id || 'flowsheet'}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Exported flowsheet JSON file', 'success');
      });
    }

    // 9. Import JSON
    if (dom.btnImportJson && dom.importFileInput) {
      dom.btnImportJson.addEventListener('click', () => dom.importFileInput.click());
      dom.importFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (evt) => {
          try {
            const data = JSON.parse(evt.target.result);
            loadGraph(data);
            showToast(`Imported flowsheet '${data.name}'`, 'success');
          } catch (err) {
            showToast(`JSON import error: ${err.message}`, 'error');
          }
        };
        reader.readAsText(file);
      });
    }

    // 10. Export Stream CSV
    if (dom.btnExportCsv) {
      dom.btnExportCsv.addEventListener('click', () => {
        let csv = 'Stream_ID,Name,Phase,From_Block,From_Port,To_Block,To_Port,Mass_Flow_TPH,Temperature_C,Pressure_mbar,Enthalpy_GJH\n';
        state.graph.connections.forEach((c) => {
          csv += `"${c.stream_id}","${c.name}","${c.phase}","${c.source.block}","${c.source.port}","${c.target.block}","${c.target.port}",${c.mass_flow_tph || 0},${c.temperature_c || 0},${c.pressure_mbar || 0},${c.enthalpy_gjh || 0}\n`;
        });
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${state.graph.flowsheet_id || 'streams'}_streams.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Exported stream table CSV', 'success');
      });
    }

    // 11. Zoom Controls
    if (dom.btnZoomIn) dom.btnZoomIn.addEventListener('click', () => applyZoom(1.15));
    if (dom.btnZoomOut) dom.btnZoomOut.addEventListener('click', () => applyZoom(0.85));
    if (dom.btnZoomReset) dom.btnZoomReset.addEventListener('click', () => {
      state.viewTransform.scale = 1.0;
      state.viewTransform.panX = 40;
      state.viewTransform.panY = 40;
      renderGraph();
    });
    if (dom.btnFit) dom.btnFit.addEventListener('click', fitGraphToView);

    // 12. Accordion Sections (Flowsheets & Components)
    if (dom.accHeaderFlowsheets) {
      dom.accHeaderFlowsheets.addEventListener('click', () => {
        const pal = document.getElementById('builderPalette');
        const sec = dom.accSectionFlowsheets;
        if (sec) {
          const isCollapsed = sec.classList.toggle('collapsed');
          if (pal) pal.classList.toggle('flow-collapsed', isCollapsed);
          if (dom.arrowFlowsheets) dom.arrowFlowsheets.textContent = isCollapsed ? '▶' : '▼';
        }
      });
    }

    if (dom.accHeaderComponents) {
      dom.accHeaderComponents.addEventListener('click', () => {
        const pal = document.getElementById('builderPalette');
        const sec = dom.accSectionComponents;
        if (sec) {
          const isCollapsed = sec.classList.toggle('collapsed');
          if (pal) pal.classList.toggle('comp-collapsed', isCollapsed);
          if (dom.arrowComponents) dom.arrowComponents.textContent = isCollapsed ? '▶' : '▼';
        }
      });
    }

    // 12b. Flowsheet Filter Subtabs (All, Templates, Saved)
    const subtabBtns = [dom.tabBtnAll, dom.tabBtnTemplates, dom.tabBtnSaved];
    subtabBtns.forEach(btn => {
      if (btn) {
        btn.addEventListener('click', () => {
          subtabBtns.forEach(b => { if (b) b.classList.remove('active'); });
          btn.classList.add('active');
          state.flowsheetTab = btn.getAttribute('data-tab') || 'all';
          renderFlowsheetsLibrary();
        });
      }
    });

    // 13. Grid Snap Toggle Checkbox
    if (dom.chkGridSnap) {
      dom.chkGridSnap.addEventListener('change', (e) => {
        state.gridSnapEnabled = e.target.checked;
        if (dom.gridSnapIndicator) {
          dom.gridSnapIndicator.textContent = state.gridSnapEnabled ? '20px Grid: ON' : 'Grid: OFF';
          dom.gridSnapIndicator.style.color = state.gridSnapEnabled ? '#10B981' : '#94A3B8';
        }
        showToast(`Grid snap ${state.gridSnapEnabled ? 'enabled (20px)' : 'disabled'}`, 'info');
      });
    }

    // 14. Left Flowsheet Library Panel Actions
    if (dom.btnSaveFlowsheet) dom.btnSaveFlowsheet.addEventListener('click', saveFlowsheet);

    if (dom.btnNewFlowsheet) {
      dom.btnNewFlowsheet.addEventListener('click', () => {
        if (confirm('Create a new blank flowsheet? Unsaved changes will be discarded.')) {
          state.graph = {
            flowsheet_id: 'new_flowsheet',
            name: 'New Custom Flowsheet',
            version: '2.0',
            description: '',
            components: [],
            connections: [],
          };
          loadGraph(state.graph);
          saveAutoFlowsheet();
          renderFlowsheetsLibrary();
          showToast('Created new blank flowsheet', 'info');
        }
      });
    }

    if (dom.btnExportFlowsheet) {
      dom.btnExportFlowsheet.addEventListener('click', () => {
        const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(state.graph, null, 2));
        const a = document.createElement('a');
        a.href = dataStr;
        a.download = `${state.graph.flowsheet_id || 'flowsheet'}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Exported flowsheet JSON with block positions', 'success');
      });
    }

    if (dom.btnImportFlowsheet && dom.fileImportFlowsheet) {
      dom.btnImportFlowsheet.addEventListener('click', () => dom.fileImportFlowsheet.click());
      dom.fileImportFlowsheet.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (evt) => {
          try {
            const data = JSON.parse(evt.target.result);
            loadGraph(data);
            saveAutoFlowsheet();
            renderFlowsheetsLibrary();
            showToast(`Imported flowsheet '${data.name}' with block positions`, 'success');
          } catch (err) {
            showToast(`JSON import error: ${err.message}`, 'error');
          }
        };
        reader.readAsText(file);
      });
    }

    // 15. Panel Collapse Toggles
    const btnTogglePal = document.getElementById('btnTogglePalette');
    if (btnTogglePal) {
      btnTogglePal.addEventListener('click', () => {
        const pal = document.getElementById('builderPalette');
        if (pal) {
          const isCollapsed = pal.classList.toggle('collapsed');
          btnTogglePal.textContent = isCollapsed ? '▶' : '◀';
        }
      });
    }

    const btnToggleInsp = document.getElementById('btnToggleInspector');
    if (btnToggleInsp) {
      btnToggleInsp.addEventListener('click', () => {
        const insp = document.getElementById('builderInspector');
        if (insp) {
          const isCollapsed = insp.classList.toggle('collapsed');
          btnToggleInsp.textContent = isCollapsed ? '◀' : '▶';
        }
      });
    }
  }

  function fitGraphToView() {
    if (!state.graph.components.length || !dom.svg) return;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    state.graph.components.forEach((b) => {
      const dims = getBlockDimensions(b);
      minX = Math.min(minX, b.position.x);
      minY = Math.min(minY, b.position.y);
      maxX = Math.max(maxX, b.position.x + dims.width);
      maxY = Math.max(maxY, b.position.y + dims.height);
    });

    const rect = dom.svg.getBoundingClientRect();
    const padding = 60;
    const graphW = (maxX - minX) + padding * 2;
    const graphH = (maxY - minY) + padding * 2;

    const scaleX = rect.width / graphW;
    const scaleY = rect.height / graphH;
    const scale = Math.min(1.4, Math.max(0.4, Math.min(scaleX, scaleY)));

    state.viewTransform.scale = scale;
    state.viewTransform.panX = (rect.width - (maxX - minX) * scale) / 2 - minX * scale;
    state.viewTransform.panY = (rect.height - (maxY - minY) * scale) / 2 - minY * scale;
    renderGraph();
  }

  async function solveSteadyState() {
    if (dom.btnSolve) dom.btnSolve.innerHTML = '⏳ Solving...';
    try {
      const res = await fetch('/api/flowsheet/builder/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state.graph),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success' && data.graph) {
          // Update graph with solved states
          loadGraph(data.graph, true);
          if (data.solve_result && data.solve_result.audit) {
            updateAuditDisplays(data.solve_result.audit);
          }
          const iter = data.solve_result.iterations || 1;
          const closure = data.solve_result.audit ? data.solve_result.audit.mass_closure_pct : 100;
          showToast(`Steady-state converged in ${iter} iterations! Mass closure: ${closure}%`, 'success');
        } else {
          showToast(`Solve error: ${data.message || 'Unknown error'}`, 'error');
        }
      }
    } catch (err) {
      showToast(`Solver request failed: ${err.message}`, 'error');
    } finally {
      if (dom.btnSolve) dom.btnSolve.innerHTML = '⚡ Solve Balances';
    }
  }

  function formatSimTime(totalSec) {
    const hrs = Math.floor(totalSec / 3600);
    const mins = Math.floor((totalSec % 3600) / 60);
    const secs = Math.floor(totalSec % 60);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  function updateSimTimeDisplay() {
    if (dom.simTimeDisplay) {
      dom.simTimeDisplay.textContent = formatSimTime(state.simulationTime || 0);
    }
  }

  function updateSimStatus(status) {
    if (!dom.simStatusPill || !dom.simStatusText) return;
    if (status === 'RUNNING') {
      dom.simStatusPill.className = 'status-pill running';
      dom.simStatusText.textContent = 'RUNNING';
    } else if (status === 'PAUSED') {
      dom.simStatusPill.className = 'status-pill paused';
      dom.simStatusText.textContent = 'PAUSED';
    } else {
      dom.simStatusPill.className = 'status-pill ready';
      dom.simStatusText.textContent = 'READY';
    }
  }

  function toggleSimulation() {
    state.isSimulating = !state.isSimulating;
    if (state.isSimulating) {
      if (dom.btnRunSim) {
        dom.btnRunSim.innerHTML = '⏸ Pause Sim';
        dom.btnRunSim.className = 'builder-toolbar-btn btn-amber';
      }
      updateSimStatus('RUNNING');
      renderGraph();
      const intervalMs = Math.max(60, Math.round(500 / (state.simSpeed || 1.0)));
      state.simInterval = setInterval(runDynamicStep, intervalMs);
      showToast(`Dynamic simulation running (${state.simSpeed || 1}x speed)`, 'info');
    } else {
      if (dom.btnRunSim) {
        dom.btnRunSim.innerHTML = '▶ Run Sim';
        dom.btnRunSim.className = 'builder-toolbar-btn btn-success';
      }
      updateSimStatus('PAUSED');
      clearInterval(state.simInterval);
      renderGraph();
      showToast('Simulation paused', 'info');
    }
  }

  async function runDynamicStep() {
    try {
      const stepDt = 0.5 * (state.simSpeed || 1.0);
      const res = await fetch('/api/flowsheet/builder/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dt: stepDt }),
      });
      if (res.ok) {
        const stepData = await res.json();
        state.simulationTime = stepData.time_s || (state.simulationTime + stepDt);
        updateSimTimeDisplay();
        updateAuditDisplays(stepData.audit);

        // Update streams
        if (stepData.streams) {
          stepData.streams.forEach((s) => {
            const conn = state.graph.connections.find(c => c.stream_id === s.stream_id);
            if (conn) {
              conn.mass_flow_tph = s.mass_flow_tph;
              conn.temperature_c = s.temperature_c;
              conn.pressure_mbar = s.pressure_mbar;
              conn.enthalpy_gjh = s.enthalpy_gjh;
              conn.composition = s.composition;
            }
          });
        }

        // Update block telemetry
        if (stepData.telemetry) {
          Object.entries(stepData.telemetry).forEach(([bId, telem]) => {
            const block = state.graph.components.find(b => b.id === bId);
            if (block && telem.state) {
              block.state = telem.state;
            }
          });
        }

        renderGraph();
        if (state.selectedBlockId) renderBlockInspector(state.selectedBlockId);
        if (state.selectedStreamId) renderStreamInspector(state.selectedStreamId);
      }
    } catch (err) {
      console.warn('Simulation step tick error:', err);
    }
  }

  async function deployToOpcUa() {
    if (dom.btnDeploy) dom.btnDeploy.innerHTML = '⏳ Deploying...';
    try {
      const res = await fetch('/api/flowsheet/builder/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state.graph),
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`Flowsheet deployed! OPC UA nodes registered and active.`, 'success');
        if (typeof window.refreshOpcStudio === 'function') {
          window.refreshOpcStudio();
        }
      } else {
        showToast('Deployment failed', 'error');
      }
    } catch (err) {
      showToast(`Deploy error: ${err.message}`, 'error');
    } finally {
      if (dom.btnDeploy) dom.btnDeploy.innerHTML = '⚡ Deploy to OPC UA';
    }
  }

  async function saveFlowsheet() {
    const currentName = state.graph.name || 'My Plant Flowsheet';
    const name = prompt('Enter a name for this flowsheet (all block grid positions will be preserved):', currentName);
    if (!name || !name.trim()) return;

    state.graph.name = name.trim();
    const safeId = name.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    state.graph.flowsheet_id = safeId;

    // Snapshot complete graph with exact coordinates
    const flowsheetData = JSON.parse(JSON.stringify(state.graph));

    // 1. Save to user saved list in localStorage
    try {
      let userFlowsheets = JSON.parse(localStorage.getItem('prosim_user_flowsheets') || '[]');
      const existingIdx = userFlowsheets.findIndex(u => u.name === name.trim() || u.id === safeId);
      if (existingIdx >= 0) {
        userFlowsheets[existingIdx] = flowsheetData;
      } else {
        userFlowsheets.unshift(flowsheetData);
      }
      localStorage.setItem('prosim_user_flowsheets', JSON.stringify(userFlowsheets));
    } catch (e) {
      console.warn('LocalStorage save error:', e);
    }

    // 2. Persist to auto-save slot
    saveAutoFlowsheet();

    // 3. Save to server backend
    try {
      const res = await fetch('/api/flowsheet/builder/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: safeId, flowsheet: flowsheetData }),
      });
      if (res.ok) {
        showToast(`Flowsheet '${name}' saved! All block coordinates preserved.`, 'success');
      } else {
        showToast(`Flowsheet '${name}' saved locally!`, 'success');
      }
    } catch (err) {
      showToast(`Flowsheet '${name}' saved locally!`, 'success');
    }

    await renderFlowsheetsLibrary();
  }

  // Expose global interface for integration with app.js
  window.FlowsheetBuilder = {
    init,
    loadTemplate,
    loadGraph,
    getGraph: () => state.graph,
    solveSteadyState,
  };

  // Auto-init on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
