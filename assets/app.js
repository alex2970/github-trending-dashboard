/* GitHub 热门项目日报：读 data/index.json 拿日期清单，读 data/<日期>.json 渲染。 */

(function () {
  var dateSelect = document.getElementById('dateSelect');
  var searchInput = document.getElementById('search');
  var tabsEl = document.getElementById('tabs');
  var gridEl = document.getElementById('grid');
  var emptyEl = document.getElementById('empty');
  var catTitle = document.getElementById('catTitle');
  var catDesc = document.getElementById('catDesc');
  var updatedEl = document.getElementById('updated');

  var current = null;      // 当天数据
  var activeCat = 'all';   // 当前分类
  var idxData = null;      // index.json 内容（含 alias：某天和上次榜单一样时指向上次文件）

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function fmt(n) { return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : String(n); }

  function renderTabs() {
    tabsEl.innerHTML = '';
    current.categories.forEach(function (c) {
      var b = document.createElement('button');
      b.textContent = c.icon + ' ' + c.name;
      if (c.id === activeCat) b.className = 'active';
      b.onclick = function () { activeCat = c.id; render(); };
      tabsEl.appendChild(b);
    });
  }

  function matchQ(r, q) {
    if (!q) return true;
    return (r.full_name + ' ' + (r.description || '') + ' ' + (r.description_zh || '') + ' ' + (r.language || '')).toLowerCase().indexOf(q) !== -1;
  }

  function cardEl(r, rank) {
    var card = document.createElement('div');
    card.className = 'card';
    var topics = (r.topics || []).map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('');
    var zh = r.description_zh || '';
    var en = r.description || '';
    var descHtml = '<div class="desc">' + esc(zh || en || '（暂无简介）') + '</div>' +
      ((zh && en && zh !== en) ? '<div style="font-size:12px;color:var(--muted);margin-top:2px">' + esc(en) + '</div>' : '');
    card.innerHTML =
      '<div class="rank">#' + rank + ' · 创建于 ' + esc(r.created_at) + '</div>' +
      '<h3><a href="' + esc(r.html_url) + '" target="_blank" rel="noopener">' + esc(r.full_name) + '</a></h3>' +
      descHtml +
      '<div class="topics">' + topics + '</div>' +
      '<div class="meta">' +
        '<span class="star">★ ' + fmt(r.stars) + '</span>' +
        '<span>⑂ ' + fmt(r.forks) + ' forks</span>' +
        (r.language ? '<span class="lang">' + esc(r.language) + '</span>' : '') +
        '<span>最近更新 ' + esc(r.pushed_at) + '</span>' +
        (r.license ? '<span>' + esc(r.license) + '</span>' : '') +
      '</div>';
    return card;
  }

  function render() {
    var cat = null;
    current.categories.forEach(function (c) { if (c.id === activeCat) cat = c; });
    if (!cat) { cat = current.categories[0]; activeCat = cat.id; }
    renderTabs();
    catTitle.textContent = cat.icon + ' ' + cat.name;
    catDesc.textContent = cat.desc + ' · 共 ' + cat.repos.length + ' 个';

    var q = searchInput.value.trim().toLowerCase();

    // 热榜：原样渲染，不动
    var list = cat.repos.filter(function (r) { return matchQ(r, q); });
    gridEl.innerHTML = '';
    list.forEach(function (r, i) { gridEl.appendChild(cardEl(r, i + 1)); });

    // Star 榜：同分类下 Star 最多的 10 个（不限创建时间），在热榜下方单独一段。
    // 老数据没有 star_top 时整段隐藏。
    var starHeadEl = document.getElementById('starHead');
    var starGridEl = document.getElementById('starGrid');
    var starDescEl = document.getElementById('starDesc');
    var starList = (cat.star_top || []).filter(function (r) { return matchQ(r, q); });
    if (starList.length) {
      starHeadEl.style.display = 'block';
      starDescEl.textContent = '本类 Star 最多的 ' + (cat.star_top || []).length + ' 个 · 不限创建时间 · 按 Star 从多到少排';
      starGridEl.innerHTML = '';
      starList.forEach(function (r, i) { starGridEl.appendChild(cardEl(r, i + 1)); });
    } else {
      starHeadEl.style.display = 'none';
      starGridEl.innerHTML = '';
    }

    emptyEl.style.display = (list.length || starList.length) ? 'none' : 'block';
  }

  function fileFor(date) {
    // 某天榜单和上次完全一样时，index.json 里有 alias 指向上一份文件
    return (idxData && idxData.alias && idxData.alias[date]) || date;
  }

  function loadDate(date) {
    return fetch('data/' + fileFor(date) + '.json').then(function (resp) {
      if (!resp.ok) throw new Error('no data for ' + date);
      return resp.json();
    }).then(function (data) {
      current = data;
      updatedEl.textContent = '数据更新于 ' + data.fetched_at + ' · ' + data.date;
      if (current.categories.every(function (c) { return c.id !== activeCat; })) activeCat = 'all';
      render();
    });
  }

  fetch('data/index.json').then(function (resp) { return resp.json(); }).then(function (idx) {
    idxData = idx;
    var dates = idx.dates || [];
    if (!dates.length) throw new Error('no dates');
    dates.slice().reverse().forEach(function (d) {
      var o = document.createElement('option');
      o.value = d; o.textContent = d;
      dateSelect.appendChild(o);
    });
    dateSelect.value = dates[dates.length - 1];
    dateSelect.onchange = function () { loadDate(dateSelect.value); };
    return loadDate(dateSelect.value);
  }).catch(function () {
    // index.json 不可用时直接读 latest.json
    fetch('data/latest.json').then(function (resp) { return resp.json(); }).then(function (data) {
      current = data;
      updatedEl.textContent = '数据更新于 ' + data.fetched_at + ' · ' + data.date;
      render();
    }).catch(function () {
      gridEl.innerHTML = '';
      emptyEl.style.display = 'block';
      emptyEl.textContent = '数据还没生成，稍后再来看看。';
    });
  });

  searchInput.addEventListener('input', render);
})();
