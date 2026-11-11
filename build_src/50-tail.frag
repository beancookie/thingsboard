<!-- ================= 收尾 ================= -->
<section id="s22">
  <div class="chapter">
    <div class="num">CLOSING</div>
    <h2>价值汇总与下一步</h2>
    <p class="lede">最后四分钟，把五条线收成一张表，然后给一个客户能直接点头的下一步——不谈框架，谈排期。</p>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">22</span><span class="ttl">五条线，一个交付承诺</span><span class="tag">汇总</span></div>
    <div class="body">
      <h3 class="pt">每一页 PPT 背后，都对应一个可验证的事实</h3>
      <table class="tbl">
        <thead><tr><th style="width:150px">主线</th><th>核心结论</th><th style="width:220px">客户得到什么</th></tr></thead>
        <tbody>
          <tr><td><b>信创与可扩展</b></td><td>TDengine 国产时序库，全栈无商业许可费；三层微服务独立扩容；单集群 3 万台已验证</td><td>授权风险归零，扩容可预算</td></tr>
          <tr><td><b>自主可控</b></td><td>源码全量可控、数据全落自有库表、私有仓库 + TKE 可整体迁移</td><td>不被绑定，能进能出</td></tr>
          <tr><td><b>AI 辅助</b></td><td>建模提速、链路排障、OpenAPI 对话式操作，写入必须人工确认</td><td>上线更快，现场少跑</td></tr>
          <tr><td><b>融合终端</b></td><td>一台网关聚合多协议，单跳直连，共用标准物模型</td><td>不加中转，改造量小</td></tr>
          <tr><td><b>腾讯云 IoT</b></td><td>TSL 归一化、双向转换、现网全流程验证</td><td>迁移不改设备端</td></tr>
        </tbody>
      </table>
      <div class="cols c3">
        <div class="cardlet"><h4><span class="ic">省钱</span>无许可费</h4><p>扩容只增算力，不增授权；十年周期成本结构可预测。</p></div>
        <div class="cardlet"><h4><span class="ic">省时</span>AI + 兼容</h4><p>建模从天级到小时级；存量迁移不改设备端。</p></div>
        <div class="cardlet"><h4><span class="ic">省心</span>可控可迁</h4><p>源码、数据、部署三层自主，退出路径清晰。</p></div>
      </div>
      <p class="hint">建议版式：一张五行总表 + 三个"省"字卡；"省"比"先进"更能打动评审会上的决策人。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 40 秒</small></div>
      <div class="say">
        <p>把五条线收一下。这一页每一行，都对应前面一张 PPT 或一段演示，没有新增信息——我想让各位确认的是：<strong>我们讲的每一句，都有落点。</strong></p>
        <p>如果只提炼三个词，是<strong>省钱、省时、省心</strong>。省钱，是没有许可费，扩容只增算力；省时，是建模提速、存量迁移不改设备；省心，是源码数据部署都在自己手里，退出的路也是通的。</p>
        <p>技术汇报做到最后，客户真正要的不是"你们技术很先进"，而是<strong>"选你们，我的风险在哪里、我的收益在哪里"</strong>。这两件事，今天应该都讲到了。</p>
      </div>
    </div>
  </div>

  <div class="slide" id="s23">
    <div class="bar"><span class="pg">23</span><span class="ttl">下一步：三个可选动作</span><span class="tag amber">行动建议</span></div>
    <div class="body">
      <h3 class="pt">不谈框架，谈排期</h3>
      <div class="cols c3">
        <div class="cardlet"><h4><span class="ic">01</span>小范围 PoC</h4><p>选 1 个产品、1 台融合网关、10–50 台设备，跑通"接入 → 校验 → 入湖 → 看板"，2–3 周出结论。</p></div>
        <div class="cardlet"><h4><span class="ic">02</span>迁移评估</h4><p>拿 2–3 个真实腾讯物模型做导入与转换验证，输出字段映射清单与工作量评估。</p></div>
        <div class="cardlet"><h4><span class="ic">03</span>运维共建</h4><p>把 AI 助手接成一线运维入口，梳理高频问答与操作目录，先覆盖 80% 日常查询。</p></div>
      </div>
      <table class="tbl">
        <thead><tr><th style="width:150px">需要贵方提供</th><th>用途</th><th style="width:120px">时间点</th></tr></thead>
        <tbody>
          <tr><td>1 个试点产品 + 设备清单</td><td>确定物模型与接入协议范围</td><td>本周内</td></tr>
          <tr><td>1 台融合网关或现场录屏</td><td>验证多协议接入与子设备建模</td><td>PoC 启动前</td></tr>
          <tr><td>2–3 份腾讯侧物模型</td><td>验证导入、转换与字段映射</td><td>PoC 第一周</td></tr>
          <tr><td>目标集群规格与网络策略</td><td>输出部署清单与迁移步骤</td><td>PoC 第二周</td></tr>
        </tbody>
      </table>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 40 秒</small></div>
      <div class="say">
        <p>最后给三个可选的下一步，不需要现在就定大合同。</p>
        <p>第一，<strong>小范围 PoC</strong>：一个产品、一台融合网关、几十台设备，两三周跑通一条完整链路。第二，<strong>迁移评估</strong>：拿两三份真实的腾讯物模型，我们做导入和转换，给字段映射清单和工作量。第三，<strong>运维共建</strong>：把 AI 助手接成一线入口，先把日常查询覆盖掉。</p>
        <p>这三件事可以并行，也可以只做一件。表里列了需要贵方配合的输入——都是很轻的东西，一份设备清单、一台网关、几份物模型文件。</p>
        <p>我的建议是<strong>从 PoC 开始</strong>，因为它能在最短时间内回答"这套东西在我们的现场到底行不行"。</p>
        <p><span class="beat">收尾</span> 我的汇报到这里。信创打底、自主可控、能演示、能迁移——这四句话，就是今天想留给各位的印象。谢谢大家，下面的时间交给提问。</p>
      </div>
    </div>
  </div>
</section>

<!-- ================= 附录 ================= -->
<section id="s24">
  <div class="chapter">
    <div class="num">APPENDIX / 现场保障</div>
    <h2>附录：演示检查清单与应答库</h2>
    <p class="lede">这一部分不投屏，是给讲者自己看的。上台前 30 分钟过一遍 A1，演示卡住时查 A2，被追问时翻 A4。</p>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">A1</span><span class="ttl">上台前检查清单</span><span class="tag amber">T-30 分钟</span></div>
    <div class="body">
      <h3 class="pt">环境、数据、脚本，三件事各查一遍</h3>
      <table class="tbl">
        <thead><tr><th style="width:70px">类别</th><th>检查项</th><th style="width:150px">通过标准</th></tr></thead>
        <tbody>
          <tr><td rowspan="3">环境</td><td>平台、物模型服务、AI 助手健康检查</td><td>均返回正常</td></tr>
          <tr><td>大屏分辨率与浏览器缩放（建议 100%）</td><td>页面无横向滚动</td></tr>
          <tr><td>网络出口、录屏文件可本地播放</td><td>断网也能兜底</td></tr>
          <tr><td rowspan="4">数据</td><td>演示产品 / 设备已创建，凭证有效</td><td>能查到、能上报</td></tr>
          <tr><td>演示用产品 ID 唯一，避免重复冲突</td><td>准备 1–2 个备用 ID</td></tr>
          <tr><td>非法数据样例已构造（类型错误 / 未知字段）</td><td>可随时重放</td></tr>
          <tr><td>腾讯物模型样例已就位（真实项目文件优先）</td><td>导入可复现</td></tr>
          <tr><td rowspan="3">脚本</td><td>模拟器命令写入便签，路径正确</td><td>一条命令起效</td></tr>
          <tr><td>网关模拟或实物网关已预热在线</td><td>子设备可见</td></tr>
          <tr><td>高危删除用测试租户 / 测试设备</td><td>绝不碰真实数据</td></tr>
        </tbody>
      </table>
      <p class="hint">建议版式：这一页做成可勾选的清单（打印时每行前面留方框），会上不投屏，会后可作为交付物附件。</p>
    </div>
    <div class="note">
      <div class="label">自用提示<small>不投屏</small></div>
      <div class="say">
        <p>演示类汇报，<strong>70% 的准备时间应该花在环境上</strong>。上讲台前 30 分钟，按这张表逐项打勾；任何一项没过，就切到录屏方案，不要现场修。</p>
        <p>特别提醒两条：产品 ID 全系统唯一，重复演示一定要换 ID；高危删除只能用测试租户，现场删真实数据是灾难级事故。</p>
      </div>
    </div>
  </div>

  <div class="slide" id="s25">
    <div class="bar"><span class="pg">A2</span><span class="ttl">故障兜底与话术</span><span class="tag amber">应急</span></div>
    <div class="body">
      <h3 class="pt">出问题时，先稳住节奏，再切方案</h3>
      <table class="tbl">
        <thead><tr><th style="width:190px">现象</th><th>快速判断</th><th>现场动作</th></tr></thead>
        <tbody>
          <tr><td>AI 助手无响应</td><td>模型服务或网络不可达</td><td>切录屏；口播"这是环境问题，能力昨天刚演示过"</td></tr>
          <tr><td>设备一直离线</td><td>凭证 / ClientId / 网关模式</td><td>换预置好的备用设备，不在台上排查</td></tr>
          <tr><td>网关主题报错</td><td>设备未开启网关模式</td><td>展示已开启网关模式的备用网关</td></tr>
          <tr><td>数据不上来</td><td>很可能就是本场要讲的"非法数据"</td><td><b>转成演示素材</b>：正好用它讲链路排障</td></tr>
          <tr><td>腾讯物模型导入失败</td><td>文件或字段版本差异</td><td>切离线转换脚本 + 已完成导入的截图</td></tr>
          <tr><td>投影 / 分辨率异常</td><td>缩放或字体</td><td>浏览器缩放到 90%，或切 PDF 版讲稿</td></tr>
        </tbody>
      </table>
      <div class="spoken">
        现场话术：<b>"这个现象本身很有价值——它正好是我们设计的非法数据通道在起作用。我借这个机会把排障链路讲一下。"</b>　把故障转成内容，比道歉更能建立专业感。
      </div>
      <p class="hint">建议版式：纯表格 + 一句话术；这一页打印出来放在手边，不上大屏。</p>
    </div>
    <div class="note">
      <div class="label">自用提示<small>不投屏</small></div>
      <div class="say">
        <p>演示出故障不可怕，<strong>在台上排查才可怕</strong>。原则：30 秒内没定位，立刻切方案，绝不当着客户面 debug。</p>
        <p>如果恰好是"数据没上来"，恭喜你——这可以直接转成链路排障的现场案例，比准备好的脚本更真实。前提是你对四段链路足够熟。</p>
      </div>
    </div>
  </div>

  <div class="slide" id="s26">
    <div class="bar"><span class="pg">A3</span><span class="ttl">备份资产清单</span><span class="tag">物料</span></div>
    <div class="body">
      <h3 class="pt">上台前把这些放进同一个文件夹</h3>
      <table class="tbl">
        <thead><tr><th style="width:210px">资产</th><th>用途</th><th style="width:130px">形态</th></tr></thead>
        <tbody>
          <tr><td>四段演示录屏（AI / 网关 / 腾讯 / 总览）</td><td>环境不可用时的替代</td><td>MP4，本地可播</td></tr>
          <tr><td>物模型样例（标准 + 腾讯 + 含错版本）</td><td>导入、校验、报错演示</td><td>JSON 文件</td></tr>
          <tr><td>转换前后 diff</td><td>展示字段映射规则</td><td>并排截图 / 文本</td></tr>
          <tr><td>设备与网关清单、凭证 CSV</td><td>快速切换备用设备</td><td>CSV（注意保密）</td></tr>
          <tr><td>现网验证记录（导入 / 校验 / 同步）</td><td>支撑"已验证"的说法</td><td>截图 + 时间戳</td></tr>
          <tr><td>3 万台压测报告</td><td>支撑容量结论</td><td>PDF</td></tr>
          <tr><td>架构图（分层 / 数据流 / 迁移）</td><td>追问时快速展开</td><td>图片或 PPT 页</td></tr>
          <tr><td>讲稿 PDF</td><td>投影异常时照读</td><td>本文件打印版</td></tr>
        </tbody>
      </table>
    </div>
    <div class="note">
      <div class="label">自用提示<small>不投屏</small></div>
      <div class="say">
        <p>录屏不要现场录，<strong>提前录、提前在本机播一遍</strong>。很多事故不是没录，是录了但现场播不出来——编码、路径、声音，任何一个都能让兜底失效。</p>
        <p>凭证 CSV 含明文令牌，演示机上单独放，演示结束删除，不要跟着讲稿一起发出去。</p>
      </div>
    </div>
  </div>

  <div class="slide" id="s27">
    <div class="bar"><span class="pg">A4</span><span class="ttl">Q&amp;A 应答库</span><span class="tag blue">高频 8 问</span></div>
    <div class="body">
      <h3 class="pt">被追问时，先给结论，再给证据，最后给边界</h3>
      <table class="tbl">
        <thead><tr><th style="width:210px">问题</th><th>建议应答（要点）</th></tr></thead>
        <tbody>
          <tr><td><b>为什么不用大厂托管 IoT？</b></td><td>托管方案省运维，但数据与授权受制于人；本方案可私有化、可迁移、无许可费。规模化后成本结构差异会放大。</td></tr>
          <tr><td><b>TDengine 开源版够用吗？</b></td><td>时序写入与聚合查询够用；若需要企业级支持，可另行采购服务，属于运维选项而非架构前提。</td></tr>
          <tr><td><b>3 万台的测试条件？</b></td><td>压测报告含并发连接、上报频率、报文大小与集群规格；本页讲结论，条件可会后提供。</td></tr>
          <tr><td><b>AI 是否会把数据传到外部？</b></td><td>模型服务地址可配置；敏感数据不进模型上下文，完整物模型走服务端 handler，不整包喂给模型。</td></tr>
          <tr><td><b>AI 生成错了怎么办？</b></td><td>生成物是草案，必须过平台结构与业务校验；写操作需人工确认；高危操作二次确认并审计。</td></tr>
          <tr><td><b>迁移要多久？</b></td><td>取决于物模型数量与设备协议；建议先做 2–3 个真实物模型的导入评估，再给整体排期。设备端不改是最大变量消除。</td></tr>
          <tr><td><b>历史数据能迁吗？</b></td><td>时序数据可按时间分区批量导入；建议历史归档 + 新数据双轨一段时间，验证后再切换。</td></tr>
          <tr><td><b>出问题谁负责？</b></td><td>源码、镜像、部署均在交付范围内，问题定位到代码级；运维责任边界在交付协议中明确。</td></tr>
        </tbody>
      </table>
      <div class="cardlet amber" style="margin-bottom:16px"><h4><span class="ic">!</span>三条禁忌</h4><p>不承诺未验证的容量数字；不承诺未排期的功能上线时间；不在客户面前评价友商产品，只对比方案结构。</p></div>
    </div>
    <div class="note">
      <div class="label">自用提示<small>不投屏</small></div>
      <div class="say">
        <p>问答环节的节奏：<strong>结论 → 证据 → 边界</strong>。三步说完就停，不要展开成长篇技术讲座。客户追问细节时再展开第二层。</p>
        <p>遇到不会的，直接说"这个我需要确认后回复"，并当场记下来。<strong>现场编一个答案的代价，远大于承认需要确认。</strong></p>
      </div>
    </div>
  </div>

  <div class="slide" id="s28">
    <div class="bar"><span class="pg">A5</span><span class="ttl">口径与数据说明</span><span class="tag">严谨性</span></div>
    <div class="body">
      <h3 class="pt">哪些是已验证事实，哪些需要客户侧输入</h3>
      <div class="cols c2">
        <div class="cardlet"><h4><span class="ic">✓</span>已在系统中可验证</h4><p>TDengine 作为时序存储；接入 / 规则 / 脚本分层扩容；源码与私有镜像仓库；PostgreSQL 自有库表；网关模式与子设备关系；腾讯格式归一化与双向转换脚本；AI 助手读接口直连、写接口待确认。</p></div>
        <div class="cardlet amber"><h4><span class="ic">?</span>需按客户现场确认</h4><p>3 万台的具体压测口径与集群规格；融合网关的实物型号与协议覆盖清单；腾讯侧物模型版本与字段差异；迁移窗口与历史数据范围。</p></div>
      </div>
      <ul class="pts tight">
        <li><b>数字口径</b>：容量、时长、成本类数字，一律标注"测试条件 / 估算前提"，不在口播中省略定语。</li>
        <li><b>能力口径</b>：说"已实现"的，必须能当场打开；说"规划中"的，明确标注，不混入现状。</li>
        <li><b>对比口径</b>：只比结构（许可模式、部署形态、迁移路径），不比友商具体报价与版本号。</li>
      </ul>
    </div>
    <div class="note">
      <div class="label">自用提示<small>不投屏</small></div>
      <div class="say">
        <p>这一页是给自己的纪律。技术汇报最贵的成本不是讲错一个参数，是<strong>让客户发现你把"规划"讲成了"现状"</strong>——后面所有结论都会被重新打折。</p>
        <p>左边这些，现场都能打开验证；右边这些，坦率说"需要贵方输入才能给准数"。<strong>承认边界不会削弱专业感，反而会增强。</strong></p>
      </div>
    </div>
  </div>
</section>

<footer>
  <p><b>使用说明</b>　本文档为单文件 HTML 讲稿：灰色区块为投屏内容（PPT 页面），虚线分隔的「讲稿」为口播；带绿色标题的区块为现场演示脚本，「兜底」为故障替代方案；附录 A1–A5 建议打印、不投屏。</p>
  <p><b>快捷键</b>　↑ / ↓ 切换页面　·　P 切换演示模式（放大讲稿、淡化屏显）　·　Ctrl+P 打印或导出 PDF（已适配 A4）。</p>
  <p style="margin-top:14px;color:var(--ink-4)">中国中铁物联网平台 · 技术汇报演讲稿 v1.0 · 2026-11　|　文中技术事实以当前代码与文档为准，容量与成本数字请按现场测试口径引用。</p>
</footer>

</div>
</main>

<button class="btn backtop" id="backtop" title="回到顶部">↑ 顶部</button>

<script>
(function(){
  var sections = Array.prototype.slice.call(document.querySelectorAll('main section[id]'));
  var links = {};
  document.querySelectorAll('.side a').forEach(function(a){
    links[a.getAttribute('href').slice(1)] = a;
  });
  var current = null;

  function setActive(id){
    if (current === id) return;
    if (current && links[current]) links[current].classList.remove('active');
    current = id;
    if (links[id]) {
      links[id].classList.add('active');
      var side = document.getElementById('side');
      var r = links[id].getBoundingClientRect(), sr = side.getBoundingClientRect();
      if (r.top < sr.top + 60 || r.bottom > sr.bottom - 40) {
        links[id].scrollIntoView({block:'center'});
      }
    }
  }

  function onScroll(){
    var pos = window.scrollY + 110;
    var active = sections.length ? sections[0].id : null;
    for (var i = 0; i < sections.length; i++) {
      if (sections[i].offsetTop <= pos) active = sections[i].id;
    }
    setActive(active);
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var p = max > 0 ? (window.scrollY / max) * 100 : 0;
    document.getElementById('progress').style.width = p + '%';
  }

  var ticking = false;
  window.addEventListener('scroll', function(){
    if (!ticking) { ticking = true; requestAnimationFrame(function(){ onScroll(); ticking = false; }); }
  }, {passive:true});
  window.addEventListener('resize', onScroll);
  onScroll();

  document.getElementById('btnSpeak').addEventListener('click', function(){
    document.body.classList.toggle('speak');
    this.classList.toggle('on');
    this.textContent = document.body.classList.contains('speak') ? '退出演示模式' : '演示模式';
  });

  document.getElementById('btnPrint').addEventListener('click', function(){ window.print(); });
  document.getElementById('backtop').addEventListener('click', function(){ window.scrollTo({top:0, behavior:'smooth'}); });

  document.addEventListener('keydown', function(e){
    if (e.target && /INPUT|TEXTAREA/.test(e.target.tagName)) return;
    if (e.key === 'p' || e.key === 'P') { document.getElementById('btnSpeak').click(); }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      var pos = window.scrollY + 120, idx = 0;
      for (var i = 0; i < sections.length; i++) if (sections[i].offsetTop <= pos) idx = i;
      var next = e.key === 'ArrowDown' ? Math.min(idx + 1, sections.length - 1) : Math.max(idx - 1, 0);
      sections[next].scrollIntoView({behavior:'smooth', block:'start'});
    }
    if (e.key === 'Home') { e.preventDefault(); window.scrollTo({top:0, behavior:'smooth'}); }
    if (e.key === 'End') { e.preventDefault(); window.scrollTo({top:document.documentElement.scrollHeight, behavior:'smooth'}); }
  });
})();
</script>
</body>
</html>
