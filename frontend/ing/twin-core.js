/* ============================================================
 * Twin Hospital - Core Player & UI Module
 * 统一的“主角控制 + 场景交互 + 调试可视化 + 病历面板（富/原始）”模块
 * 可在 Lobby / Consultation / Examination / Lab / Pharmacy 五页共用
 *
 * 键位：
 *  移动：WASD / 方向键
 *  交互：E
 *  碰撞开关：O
 *  坐标开关：G
 *  病历：R（支持富/原始视图切换、服务端刷新）
 * =========================================================== */
(function(global){
  const TwinCore = {
    /* ======= 公共配置与状态 ======= */
    cfg: null,
    canvas: null,
    ctx: null,
    imgs: null,
    lastTs: 0,

    // 主角状态
    player: { x:0, y:0, w:74, h:74, speed:2.0, dir:'down', frame:0, frameTimer:0, frameDelay:100 },

    // 输入
    keys: new Set(),

    // 判定结果（每帧刷新）
    nearDoor: null,
    nearTalk: null,

    // 调试与坐标
    debug: { show:false, alpha:0.28 },
    coords: {
      show:false, grid:true, gridSize:32,
      mouse:{x:0,y:0}, hover:null
    },

    // ======== 病历（Medical Record）与 UI ========
    record: null,        // 本地运行时病历（localStorage）
    visitId: null,
    patientId: null,     // 新增：用于服务端拉取聚合病历
    serverRecord: null,  // 新增：/api/patient/<id>/record 的只读聚合
    _recordOpen: false,
    _recordMode: 'rich', // 'rich' | 'json'
    storageKey(){ return `twin_record_${this.visitId || 'default'}`; },

    /* =======================================================
     * init(config): 在每个房间页调用一次
     * config:
     *  - canvas, room, assets, player, baseSize, doors, obstacles, talks
     *  - ui: { toast, coordBtn, debugBtn, coordPanel }
     *  - getUiLocked: ()=>boolean
     *  - onInteract: ({nearTalk, nearDoor})=>void
     *  - sceneEventEndpoint: '/api/scene-event' （可选）
     *  - visitId: 'xxx'（可选）
     *  - patientId: '123'（可选，不传则读 URL ?patient_id=）
     * ======================================================= */
    async init(config){
      this.cfg = config;
      this.canvas = config.canvas;
      this.ctx = this.canvas.getContext('2d');
      this.ctx.imageSmoothingEnabled = false;

      // 初始化主角
      Object.assign(this.player, config.player || {});
      this.player.dir = 'down';
      this.lastTs = 0;

      // UI 绑定
      if (config.ui?.debugBtn)  config.ui.debugBtn.onclick  = ()=>this.toggleDebug();
      if (config.ui?.coordBtn)  config.ui.coordBtn.onclick  = ()=>this.toggleCoords();
      this.canvas.addEventListener('mousemove', (e)=>this.onMouseMove(e));
      this.canvas.addEventListener('click', ()=>this.copyHoverRect());
      addEventListener('keydown', (e)=>this.onKeyDown(e));
      addEventListener('keyup',   (e)=>this.onKeyUp(e));

      // 访问者标识
      this.visitId = config.visitId || this.getOrCreateVisitId();
      this.patientId = config.patientId || this.getQueryParam('patient_id') || null;

      // 本地病历
      this.record = this.loadRecord() || this.createEmptyRecord();

      // 病历 Overlay（新增“富视图”与“刷新服务端”）
      this.ensureRecordOverlay();

      // 资源预载 & 渲染循环
      this.imgs = await this.loadAll(config.assets);
      requestAnimationFrame((ts)=>this.loop(ts));
    },

    /* =============== 资源加载 =============== */
    loadImage(src){ return new Promise(res=>{ const im=new Image(); im.onload=()=>res(im); im.onerror=()=>res(new Image()); im.src=src; }); },
    async loadAll(assets){
      const imgs = {};
      imgs.bg = await this.loadImage(assets.bg);
      for (const d of ['right','left','down','up']) imgs[d] = await Promise.all((assets[d]||[]).map(s=>this.loadImage(s)));
      return imgs;
    },

    /* =============== 输入 =============== */
    onKeyDown(e){
      const k = e.key.toLowerCase();
      if(['w','a','s','d','arrowup','arrowleft','arrowdown','arrowright','e','o','g','r'].includes(k)){
        e.preventDefault();
      }
      this.keys.add(k);

      if (k==='o') this.toggleDebug();
      if (k==='g') this.toggleCoords();
      if (k==='r') this.toggleRecordOverlay();
    },
    onKeyUp(e){ this.keys.delete(e.key.toLowerCase()); },

    /* =============== 坐标/调试 UI =============== */
    toggleDebug(){
      this.debug.show = !this.debug.show;
      if (this.cfg.ui?.debugBtn) this.cfg.ui.debugBtn.textContent = this.debug.show ? "🙈 Hide Colliders (O)" : "👀 Show Colliders (O)";
    },
    toggleCoords(){
      this.coords.show = !this.coords.show;
      if (this.cfg.ui?.coordBtn)   this.cfg.ui.coordBtn.textContent = this.coords.show ? "🧮 Coords ON (G)" : "📐 Coords (G)";
      if (this.cfg.ui?.coordPanel) this.cfg.ui.coordPanel.style.display = this.coords.show ? 'block' : 'none';
    },
    onMouseMove(e){
      const rect = this.canvas.getBoundingClientRect();
      const sx = this.canvas.width / rect.width;
      const sy = this.canvas.height / rect.height;
      this.coords.mouse.x = Math.round((e.clientX - rect.left) * sx);
      this.coords.mouse.y = Math.round((e.clientY - rect.top) * sy);

      this.coords.hover = null;
      const all = [
        ...(this.cfg.talks || []).map((b,i)=>({ type:'talk', base:b, idx:i, scaled:this.scaleRect(b) })),
        ...(this.cfg.doors || []).map((b,i)=>({ type:'door', base:b, idx:i, scaled:this.scaleRect(b) })),
        ...(this.cfg.obstacles || []).map((b,i)=>({ type:'obst', base:b, idx:i, scaled:this.scaleRect(b) })),
      ].reverse();
      for (const it of all){
        if (this.pointInRect(this.coords.mouse.x, this.coords.mouse.y, it.scaled)) { this.coords.hover = it; break; }
      }
      this.updateCoordPanel();
    },
    async copyHoverRect(){
      if (!this.coords.show || !this.coords.hover) return;
      const b = this.coords.hover.base;
      const data = (this.coords.hover.type==='obst')
        ? {x:b.x, y:b.y, w:b.w, h:b.h}
        : {name:b.name, x:b.x, y:b.y, w:b.w, h:b.h, type:this.coords.hover.type};
      const text = JSON.stringify(data);
      try { await navigator.clipboard.writeText(text); this.flashPanel("已复制到剪贴板: " + text); }
      catch { this.flashPanel("无法复制，已打印到控制台"); console.log(text); }
    },
    updateCoordPanel(){
      const p = this.cfg.ui?.coordPanel;
      if (!p) return;
      const baseXY = this.toBaseXY(this.coords.mouse.x, this.coords.mouse.y);
      const h = this.coords.hover;
      let hoverText = '';
      if (h){
        const br = h.base;
        if (h.type==='door') hoverText = `hover: <span class="tag">door:${br.name}</span>  baseRect: {x:${br.x}, y:${br.y}, w:${br.w}, h:${br.h}}`;
        else if (h.type==='talk') hoverText = `hover: <span class="tag">talk:${br.name}</span>  baseRect: {x:${br.x}, y:${br.y}, w:${br.w}, h:${br.h}}`;
        else hoverText = `hover: <span class="tag">obst#${h.idx}</span>  baseRect: {x:${br.x}, y:${br.y}, w:${br.w}, h:${br.h}}`;
      }
      p.innerHTML = `
        <div>mouse canvas: <span class="tag">${this.coords.mouse.x}, ${this.coords.mouse.y}</span></div>
        <div>mouse base:   <span class="tag">${baseXY.x}, ${baseXY.y}</span></div>
        <div class="small">${h ? hoverText : 'hover: —'}</div>
        <div class="small">点击悬停区域可复制其 <b>基准坐标 JSON</b></div>
      `;
      if (this.coords.show) p.style.display = 'block';
    },
    flashPanel(msg){
      const p = this.cfg.ui?.coordPanel; if (!p) return;
      p.innerHTML = `<div>${msg}</div>`;
      p.style.display = 'block';
      clearTimeout(this._panelTimer);
      this._panelTimer = setTimeout(()=>{ if(!this.coords.show) p.style.display='none'; }, 1600);
    },

    /* =============== 几何工具 =============== */
    scaleRect(r){ const sx=this.canvas.width/(this.cfg.baseSize?.w||1152), sy=this.canvas.height/(this.cfg.baseSize?.h||768); return {x:r.x*sx, y:r.y*sy, w:r.w*sx, h:r.h*sy, name:r.name, label:r.label}; },
    toBaseXY(px,py){ const sx=(this.cfg.baseSize?.w||1152)/this.canvas.width, sy=(this.cfg.baseSize?.h||768)/this.canvas.height; return { x: Math.round(px*sx), y: Math.round(py*sy) }; },
    pointInRect(px,py,r){ return px>=r.x && px<=r.x+r.w && py>=r.y && py<=r.y+r.h; },
    rectsOverlap(a,b){ return a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y; },

    /* =============== 碰撞与移动 =============== */
    hitsObstacle(rect){
      if (rect.x < 4 || rect.y < 4 || rect.x+rect.w > this.canvas.width-4 || rect.y+rect.h > this.canvas.height-4) return true;
      for (const ob of (this.cfg.obstacles || [])){
        const r = this.scaleRect(ob);
        if (this.rectsOverlap(rect, r)) return true;
      }
      return false;
    },
    tryMove(dx,dy){
      const p = this.player;
      const next={x:p.x+dx,y:p.y+dy,w:p.w,h:p.h};
      if(!this.hitsObstacle(next)){p.x+=dx;p.y+=dy;return;}
      const xOnly={x:p.x+dx,y:p.y,w:p.w,h:p.h};
      if(!this.hitsObstacle(xOnly)) p.x+=dx;
      const yOnly={x:p.x,y:p.y+dy,w:p.w,h:p.h};
      if(!this.hitsObstacle(yOnly)) p.y+=dy;
    },

    /* =============== 场景判定与提示 =============== */
    updateSceneTouch(){
      const pRect = {x:this.player.x, y:this.player.y, w:this.player.w, h:this.player.h};

      // 对话热点优先
      this.nearTalk = null;
      for (const tb of (this.cfg.talks || [])){
        const R = this.scaleRect(tb);
        if (this.rectsOverlap(pRect, R)){ this.nearTalk = tb.name; break; }
      }

      // 门
      this.nearDoor = null;
      for(const base of (this.cfg.doors || [])){
        const R = this.scaleRect(base);
        if (this.rectsOverlap(pRect, R)){ this.nearDoor = base.name; break; }
      }

      const toast = this.cfg.ui?.toast;
      if (toast){
        if (this.nearTalk){
          toast.innerHTML = '按 <kbd>E</kbd> 对话';
          toast.style.display = 'block';
        } else if (this.nearDoor){
          toast.innerHTML = '按 <kbd>E</kbd> 进入';
          toast.style.display = 'block';
        } else {
          toast.style.display = 'none';
        }
      }
    },

    /* =============== 交互键处理（E） =============== */
    handleInteract(){
      if (!this.cfg.onInteract) return;
      const now = performance.now();
      if (!this._lastInteractAt) this._lastInteractAt = 0;
      if (now - this._lastInteractAt <= 220) return;
      this._lastInteractAt = now;
      this.cfg.onInteract({ nearTalk: this.nearTalk, nearDoor: this.nearDoor });
    },

    /* =============== 主循环 =============== */
    loop(ts){
      const dt = ts - this.lastTs; this.lastTs = ts;

      const uiLocked = (this.cfg.getUiLocked && this.cfg.getUiLocked()) || this._recordOpen === true;

      if (!uiLocked){
        let vx=0, vy=0;
        if (this.keys.has('w')||this.keys.has('arrowup'))    { vy -= this.player.speed; this.player.dir='up'; }
        if (this.keys.has('s')||this.keys.has('arrowdown'))  { vy += this.player.speed; this.player.dir='down'; }
        if (this.keys.has('a')||this.keys.has('arrowleft'))  { vx -= this.player.speed; this.player.dir='left'; }
        if (this.keys.has('d')||this.keys.has('arrowright')) { vx += this.player.speed; this.player.dir='right'; }
        if (vx&&vy){ vx*=0.7071; vy*=0.7071; }
        this.tryMove(vx,vy);

        if (vx||vy){
          this.player.frameTimer += dt;
          const frames = this.imgs[this.player.dir] || [];
          if (this.player.frameTimer > this.player.frameDelay){ this.player.frameTimer=0; this.player.frame=(this.player.frame+1)%Math.max(frames.length,1); }
        } else { this.player.frame=0; this.player.frameTimer=0; }
      }

      this.updateSceneTouch();

      if (!uiLocked && (this.keys.has('e'))) this.handleInteract();

      this.draw();

      requestAnimationFrame((t)=>this.loop(t));
    },

    /* =============== 绘制 =============== */
    draw(){
      const ctx = this.ctx, cvs = this.canvas;
      ctx.drawImage(this.imgs.bg, 0, 0, cvs.width, cvs.height);

      if (this.coords.show && this.coords.grid){
        ctx.save();
        ctx.strokeStyle = "#ffffff18";
        ctx.lineWidth = 1;
        for (let x=0; x<cvs.width; x+=this.coords.gridSize){ ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,cvs.height); ctx.stroke(); }
        for (let y=0; y<cvs.height; y+=this.coords.gridSize){ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(cvs.width,y); ctx.stroke(); }
        ctx.strokeStyle = "#7dd3fcaa";
        ctx.beginPath(); ctx.moveTo(this.coords.mouse.x,0); ctx.lineTo(this.coords.mouse.x,cvs.height); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0,this.coords.mouse.y); ctx.lineTo(cvs.width,this.coords.mouse.y); ctx.stroke();
        ctx.restore();
      }

      const frames = this.imgs[this.player.dir] || [];
      const frameImg = frames[this.player.frame] || frames[0] || this.imgs.down?.[0];
      if (frameImg) ctx.drawImage(frameImg, Math.round(this.player.x), Math.round(this.player.y), this.player.w, this.player.h);

      if (this.debug.show){
        ctx.save();
        ctx.globalAlpha = this.debug.alpha;
        ctx.fillStyle = "#00e5ff";
        ctx.strokeStyle = "#00bcd4";
        ctx.lineWidth = 2;
        (this.cfg.obstacles||[]).forEach((b,i)=>{
          const r = this.scaleRect(b);
          ctx.fillRect(r.x, r.y, r.w, r.h);
          ctx.strokeRect(r.x, r.y, r.w, r.h);
          ctx.globalAlpha = 1;
          ctx.fillStyle = "#021b1e";
          ctx.fillRect(r.x+4, r.y+4, 22, 16);
          ctx.fillStyle = "#a7ffeb";
          ctx.font = "12px monospace";
          ctx.fillText(String(i), r.x+8, r.y+16);
          ctx.globalAlpha = this.debug.alpha;
          ctx.fillStyle = "#00e5ff";
        });

        ctx.globalAlpha = 1;
        ctx.strokeStyle = "#00ff90";
        ctx.lineWidth = 2;
        (this.cfg.doors||[]).forEach(b=>{ const r=this.scaleRect(b); ctx.strokeRect(r.x,r.y,r.w,r.h); });

        ctx.strokeStyle = "#ffd1dc";
        ctx.setLineDash([6,4]);
        (this.cfg.talks||[]).forEach(b=>{ const r=this.scaleRect(b); ctx.strokeRect(r.x,r.y,r.w,r.h); });
        ctx.setLineDash([]);

        ctx.strokeStyle = "#ffd54f";
        ctx.strokeRect(this.player.x, this.player.y, this.player.w, this.player.h);

        ctx.restore();
      }
    },

    /* =============== 病历（本地） =============== */
    createEmptyRecord(){
      return {
        identity: { playerId: 'p-1', visitId: this.visitId, createdAt: Date.now(), patientId: this.patientId },
        triage: null,
        registration: null,
        orders: [],
        exams: [],
        meds: [],
        encounters: [],
        _meta: { version: 1 }
      };
    },
    getOrCreateVisitId(){
      const today = new Date();
      return `v-${today.getFullYear()}${String(today.getMonth()+1).padStart(2,'0')}${String(today.getDate()).padStart(2,'0')}`;
    },
    loadRecord(){ try{ return JSON.parse(localStorage.getItem(this.storageKey())||'null'); }catch{return null;} },
    saveRecord(){ try{ localStorage.setItem(this.storageKey(), JSON.stringify(this.record)); }catch{} },

    /* =============== 病历 Overlay（富/原始） =============== */
    ensureRecordOverlay(){
      if (document.getElementById('recordMask')) return;

      const mask = document.createElement('div');
      mask.id = 'recordMask';
      mask.style.cssText = 'position:fixed;inset:0;display:none;place-items:center;background:rgba(0,0,0,.45);z-index:60;';
      const panel = document.createElement('div');
      panel.style.cssText = 'width:min(860px,92vw);max-height:80vh;overflow:auto;background:#0b1020;border:1px solid #2b3b55;border-radius:12px;padding:14px 16px;box-shadow:0 12px 40px rgba(0,0,0,.6);color:#e6f1ff;font:14px/1.6 system-ui,Segoe UI,Arial;';
      panel.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;position:sticky;top:0;background:#0b1020;padding-bottom:8px;">
          <div style="display:flex;align-items:center;gap:10px">
            <h3 style="margin:0;font:600 16px system-ui">🩺 Medical Record</h3>
            <span id="recTag" style="font:12px/1 system-ui;color:#9fb3c8;">visit: ${this.visitId}${this.patientId?` · patient: ${this.patientId}`:''}</span>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <button id="recModeBtn"  style="background:#172036;color:#e5e7eb;border:1px solid #ffffff22;padding:6px 10px;border-radius:8px;font:12px system-ui;cursor:pointer;" title="切换富视图/原始JSON">切换为 JSON</button>
            <button id="recRefresh"  style="background:#172036;color:#e5e7eb;border:1px solid #ffffff22;padding:6px 10px;border-radius:8px;font:12px system-ui;cursor:pointer;" title="从后端刷新聚合病历">刷新</button>
            <button id="recExport"   style="background:#172036;color:#e5e7eb;border:1px solid #ffffff22;padding:6px 10px;border-radius:8px;font:12px system-ui;cursor:pointer;">导出 JSON</button>
            <button id="recClose"    style="background:#172036;color:#e5e7eb;border:1px solid #ffffff22;padding:6px 10px;border-radius:8px;font:12px system-ui;cursor:pointer;">关闭 (R / Esc)</button>
          </div>
        </div>
        <div id="recBody" style="margin-top:8px;"></div>
      `;
      mask.appendChild(panel);
      document.body.appendChild(mask);

      // 事件
      panel.querySelector('#recClose').onclick = ()=>this.toggleRecordOverlay(false);
      panel.querySelector('#recExport').onclick = ()=>{
        const blob = new Blob([JSON.stringify(this.makeRecordViewPayload(), null, 2)], {type:'application/json'});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${this.storageKey()}_${this._recordMode}.json`;
        a.click();
        URL.revokeObjectURL(a.href);
      };
      panel.querySelector('#recModeBtn').onclick = ()=>{
        this._recordMode = (this._recordMode === 'rich') ? 'json' : 'rich';
        panel.querySelector('#recModeBtn').textContent = (this._recordMode === 'rich') ? '切换为 JSON' : '切换为 富视图';
        this.renderRecord();
      };
      panel.querySelector('#recRefresh').onclick = ()=>this.refreshServerRecord();

      addEventListener('keydown', (e)=>{
        if (!this._recordOpen) return;
        if (e.key === 'Escape') this.toggleRecordOverlay(false);
      });
    },

    toggleRecordOverlay(force){
      const mask = document.getElementById('recordMask'); if (!mask) return;
      const next = (typeof force === 'boolean') ? force : !this._recordOpen;
      this._recordOpen = next;
      mask.style.display = next ? 'grid' : 'none';
      if (next) this.renderRecord();
    },

    // 生成导出视图：把本地 record 与 serverRecord 组合成一个对象供导出/调试
    makeRecordViewPayload(){
      return {
        local: this.record,
        server: this.serverRecord || null,
        mergedForDisplay: this.mergeForDisplay()
      };
    },

    renderRecord(){
      const body = document.getElementById('recBody'); if (!body) return;

      if (this._recordMode === 'json'){
        const pre = document.createElement('pre');
        pre.style.cssText='white-space:pre-wrap;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;margin:0;padding:8px;background:#0a1326;border:1px solid #1b2b4b;border-radius:8px;';
        pre.textContent = JSON.stringify(this.makeRecordViewPayload(), null, 2);
        body.innerHTML = '';
        body.appendChild(pre);
        return;
      }

      // 富视图：把本地与服务端数据进行“并排+合并要点”展示
      const view = this.mergeForDisplay();
      body.innerHTML = this.renderRecordRichHTML(view);
    },

    // ============== 富视图合并策略（轻量、只读） ==============
    mergeForDisplay(){
      // 安全兜底
      const srv = this.serverRecord || {};
      const loc = this.record || {};

      // 头部身份
      const patient = srv.patient || {}; // 服务端聚合更权威
      const visit   = srv.visit   || { id: (loc.identity?.visitId || this.visitId) };

      // 合并四表：服务端聚合优先；若无则用本地轻量事件
      const orders = (srv.orders && srv.orders.length) ? srv.orders : (loc.orders||[]);
      const tests  = (srv.tests  && srv.tests.length ) ? srv.tests  : (loc.exams ||[]);
      const meds   = (srv.prescriptions && srv.prescriptions.length) ? srv.prescriptions : (loc.meds||[]);
      const bills  = (srv.billing&& srv.billing.length) ? srv.billing : [];

      // 备注/笔记：服务端 notes 并入（若将来有）
      const notes  = (srv.notes||[]);

      return { patient, visit, orders, tests, meds, bills, notes };
    },

    // ============== 富视图渲染 HTML ==============
    renderRecordRichHTML(view){
      const fmtTime = (t)=> t ? new Date(t).toLocaleString() : '—';
      const money   = (n)=> (n===0 || n) ? `$${Number(n).toFixed(2)}` : '—';

      const sec = (title, inner)=>`
        <section style="margin:10px 0;padding:10px;border:1px solid #20324e;border-radius:10px;background:#0a1326">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <h4 style="margin:0;font:600 14px system-ui">${title}</h4>
          </div>
          ${inner}
        </section>
      `;

      const table = (headers, rows)=>`
        <div style="overflow:auto">
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
              <tr>
                ${headers.map(h=>`<th style="text-align:left;border-bottom:1px solid #264469;padding:6px 4px;color:#b5c7e5;font-weight:600">${h}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${rows.length ? rows.map(r=>`
                <tr>
                  ${r.map(c=>`<td style="border-bottom:1px dashed #1c2e4f;padding:6px 4px;color:#dce7ff">${c}</td>`).join('')}
                </tr>
              `).join('') : `<tr><td colspan="${headers.length}" style="padding:8px;color:#93a7c6">No data</td></tr>`}
            </tbody>
          </table>
        </div>
      `;

      const header = sec('Patient', `
        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;">
          <div>👤 Name: <b>${view.patient.name ?? '—'}</b></div>
          <div>🆔 ID: <b>${view.patient.id ?? this.patientId ?? '—'}</b></div>
          <div>⚥ Gender: <b>${view.patient.gender ?? '—'}</b></div>
          <div>🎂 Age: <b>${view.patient.age ?? '—'}</b></div>
          <div>🗂️ Visit ID: <b>${view.visit?.id ?? this.visitId}</b></div>
        </div>
      `);

      const orders = sec('Orders', table(
        ['ID','Name','Status','Time'],
        (view.orders||[]).map(o=>[o.id||'—', o.name||'—', o.status||'—', fmtTime(o.ts||o.createdAt)])
      ));

      const tests = sec('Tests / Results', table(
        ['ID','Name','Key / Result','Status','Time'],
        (view.tests||[]).map(t=>[t.id||'—', t.name||'—', (t.key||t.result||'—'), t.status||'—', fmtTime(t.ts||t.time)])
      ));

      const meds = sec('Prescriptions', table(
        ['ID','Medication','SIG','Status','Time'],
        (view.meds||[]).map(m=>[m.id||m.rxId||'—', m.medication||m.name||'—', m.sig||`${m.dosage||''} ${m.usage||''}`.trim(), m.status||'—', fmtTime(m.ts||m.pickedAt)])
      ));

      const bills = sec('Billing', table(
        ['Bill ID','Service','Amount','Insurance','Status','Time'],
        (view.bills||[]).map(b=>[b.id||'—', b.service||'—', money(b.amount), money(b.insurance), b.status||'—', fmtTime(b.ts)])
      ));

      const notes = sec('Notes', `
        <ul style="margin:0;padding-left:18px;color:#dce7ff">
          ${ (view.notes&&view.notes.length) ? view.notes.map(n=>`<li>${fmtTime(n.ts)} · ${n.content||'-'}</li>`).join('') : '<li>No notes</li>' }
        </ul>
      `);

      return header + orders + tests + meds + bills + notes;
    },

    /* =============== 与后端交互（新增） =============== */
    async refreshServerRecord(){
      // 无 patientId 时，仅刷新本地富视图
      if (!this.patientId){
        this.serverRecord = null;
        this.renderRecord();
        return;
      }
      try{
        const url = `/api/patient/${encodeURIComponent(this.patientId)}/record${this.visitId?`?visitId=${encodeURIComponent(this.visitId)}`:''}`;
        const resp = await fetch(url);
        if (!resp.ok) throw new Error('HTTP '+resp.status);
        this.serverRecord = await resp.json();
      }catch(e){
        // 拉取失败不影响渲染：清空 serverRecord，仅用本地显示
        this.serverRecord = null;
      }finally{
        if (this._recordOpen) this.renderRecord();
      }
    },

    /* =============== 场景事件入口（保留 + 附带 patient/visit） =============== */
    async sceneEvent(payload){
      try{
        // 附加 patient/visit 便于后端聚合
        if (this.patientId && !payload.patient_id) payload.patient_id = this.patientId;
        if (this.visitId   && !payload.visit_id)   payload.visit_id   = this.visitId;

        // 1) 写入本地病历（轻量）
        this.appendToRecord(payload);
        this.saveRecord();

        // 2) 可选上传
        if (this.cfg.sceneEventEndpoint){
          try{
            await fetch(this.cfg.sceneEventEndpoint, {
              method:'POST',
              headers:{'Content-Type':'application/json'},
              body: JSON.stringify(payload)
            });
          }catch(e){ /* 忽略 */ }
        }
      }catch(e){ /* 忽略 */ }
    },
    appendToRecord(ev){
      this.record.encounters.push({
        room: ev.room || this.cfg.room,
        action: ev.action || ev.type,
        detail: ev.choice ?? ev.detail ?? ev.orders ?? ev.note ?? null,
        time: Date.now()
      });

      if (ev.type === 'interaction' && ev.target === 'registration' && ev.action === 'dialogue_choice' && ev.choice === 'register'){
        this.record.registration = { time: Date.now(), ticketNo: 'R-'+Math.floor(Math.random()*900+100) };
      }
      if (ev.type === 'interaction' && ev.target === 'triage' && ev.action === 'dialogue_choice' && ev.choice === 'describe'){
        this.record.triage = { time: Date.now(), severity: 'TBD', notes: '简述症状' };
      }
      // 也可在具体页面追加 orders/exams/meds 的本地记录
    },

    /* =============== 小工具 =============== */
    getQueryParam(k){
      try{
        const u = new URL(location.href);
        return u.searchParams.get(k);
      }catch{ return null; }
    },
  };

  // 暴露到全局
  global.TwinCore = TwinCore;
})(window);
