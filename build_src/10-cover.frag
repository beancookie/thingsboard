<aside class="side" id="side">
  <h4>开场</h4>
  <a href="#s01"><span class="no">01</span>封面</a>
  <a href="#s02"><span class="no">02</span>议程与时间分配</a>
  <a href="#s03"><span class="no">03</span>一句话摘要</a>
  <a href="#s04"><span class="no">04</span>本次主线：从选型到落地</a>

  <h4>01 信创与可扩展</h4>
  <a href="#s05"><span class="no">05</span>信创选型：TDengine</a>
  <a href="#s06"><span class="no">06</span>分层扩容架构</a>
  <a href="#s07"><span class="no">07</span>3 万台验证与扩容</a>

  <h4>02 自主可控</h4>
  <a href="#s08"><span class="no">08</span>源码可控</a>
  <a href="#s09"><span class="no">09</span>数据可控</a>
  <a href="#s10"><span class="no">10</span>部署可控</a>

  <h4>03 AI 辅助</h4>
  <a href="#s11"><span class="no">11</span>能力总览</a>
  <a href="#s12"><span class="no">12</span>演示 A · 物模型</a>
  <a href="#s13"><span class="no">13</span>演示 B · 链路</a>
  <a href="#s14"><span class="no">14</span>演示 C · OpenAPI</a>

  <h4>04 融合终端</h4>
  <a href="#s15"><span class="no">15</span>聚合多协议</a>
  <a href="#s16"><span class="no">16</span>单跳直连</a>
  <a href="#s17"><span class="no">17</span>同一物模型</a>
  <a href="#s18"><span class="no">18</span>演示 D · 三步接入</a>

  <h4>05 腾讯云 IoT</h4>
  <a href="#s19"><span class="no">19</span>TSL 归一化</a>
  <a href="#s20"><span class="no">20</span>双向转换器</a>
  <a href="#s21"><span class="no">21</span>演示 E · 导入同步</a>

  <h4>收尾</h4>
  <a href="#s22"><span class="no">22</span>价值汇总</a>
  <a href="#s23"><span class="no">23</span>结尾与下一步</a>

  <h4>附录 · 现场保障</h4>
  <a href="#s24"><span class="no">A1</span>演示检查清单</a>
  <a href="#s25"><span class="no">A2</span>故障兜底</a>
  <a href="#s26"><span class="no">A3</span>备份资产</a>
  <a href="#s27"><span class="no">A4</span>Q&amp;A 应答库</a>
  <a href="#s28"><span class="no">A5</span>口径与数据说明</a>

  <div class="meta">
    <div><b>总时长</b>　约 40 分钟（含 3 分钟缓冲）</div>
    <div><b>演示</b>　5 段：AI ×3 · 融合终端 · 腾讯迁移</div>
    <div><b>版本</b>　v1.0 · 2026-11</div>
  </div>
</aside>

<main>
<div class="wrap">

<!-- ================= 封面 ================= -->
<section class="cover" id="s01">
  <span class="kicker">技术汇报 · 内部评审版</span>
  <h1>中国中铁物联网平台<br><em>信创底座</em>与智能化演进</h1>
  <p class="sub">围绕信创可扩展、自主可控、AI 辅助、融合终端接入、腾讯云 IoT 兼容五条主线，说明平台在当前交付约束下的技术选择、已验证能力与下一步落地路径。</p>
  <div class="meta-row">
    <span><b>汇报对象</b>　客户技术团队</span>
    <span><b>汇报人</b>　（填写）</span>
    <span><b>日期</b>　2026 年 11 月</span>
  </div>
  <div class="pillars">
    <div class="pillar"><div class="n">01</div><h3>信创与可扩展</h3><p>国产时序库 · 全栈无商业许可费 · 分层扩容</p></div>
    <div class="pillar"><div class="n">02</div><h3>自主可控</h3><p>源码可控 · 数据自有 · 可整体迁移</p></div>
    <div class="pillar demo"><div class="n">03</div><h3>AI 辅助</h3><p>生成物模型 · 定位链路 · 调用 OpenAPI</p></div>
    <div class="pillar demo"><div class="n">04</div><h3>融合终端接入</h3><p>多协议聚合 · 单跳直连 · 同一物模型</p></div>
    <div class="pillar demo"><div class="n">05</div><h3>腾讯云 IoT 兼容</h3><p>TSL 归一化 · 双向转换 · 现网验证</p></div>
  </div>
</section>

<div class="note" style="margin-top:0; border:1px solid var(--line); border-radius:10px; background:var(--card)">
  <div class="label">开场口播<small>约 50 秒</small></div>
  <div class="say">
    <p>各位领导、各位专家，上午好。</p>
    <p>今天这场汇报，我不打算从功能清单讲起。我更想回答一个问题：<strong>这套平台在贵方的建设和运维约束下，为什么可以放心用、放心扩、放心交</strong>。</p>
    <p>围绕这个目标，我用五条线展开——信创与可扩展、自主可控、AI 辅助、融合终端接入、腾讯云 IoT 兼容。前两条以方案和架构为主，后三条我会直接打开系统做演示，讲完您看到的就是能跑的东西。</p>
  </div>
</div>

<!-- ================= 02 议程 ================= -->
<section id="s02">
  <div class="chapter">
    <div class="num">AGENDA</div>
    <h2>议程与时间分配</h2>
    <p class="lede">约 40 分钟，留 10 分钟问答。三段现场演示集中在后半程，前半程把架构讲透，避免演示时反复解释背景。</p>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">02</span><span class="ttl">议程与时间分配</span><span class="tag">总览</span></div>
    <div class="body">
      <h3 class="pt">五条主线，前两条讲清楚，后三条直接看</h3>
      <table class="tbl">
        <thead><tr><th style="width:64px">序号</th><th>议题</th><th style="width:110px">形式</th><th style="width:90px">时长</th><th>客户关注点</th></tr></thead>
        <tbody>
          <tr><td class="num">01</td><td><b>信创与可扩展</b><br><span style="color:var(--ink-4);font-size:12.5px">国产时序库、微服务分层、3 万台验证</span></td><td>PPT</td><td class="num">5 min</td><td>授权风险、扩容成本</td></tr>
          <tr><td class="num">02</td><td><b>自主可控</b><br><span style="color:var(--ink-4);font-size:12.5px">源码、数据、部署三层可控</span></td><td>PPT</td><td class="num">4 min</td><td>是否被绑定、能否迁移</td></tr>
          <tr><td class="num">03</td><td><b>AI 辅助</b><br><span style="color:var(--ink-4);font-size:12.5px">生成校验物模型、定位链路、调用 OpenAPI</span></td><td><b>演示</b></td><td class="num">8 min</td><td>是否真能用、是否可控</td></tr>
          <tr><td class="num">04</td><td><b>融合终端无缝接入</b><br><span style="color:var(--ink-4);font-size:12.5px">多协议聚合、单跳直连、统一物模型</span></td><td><b>演示</b></td><td class="num">8 min</td><td>现场改造量、是否加中转</td></tr>
          <tr><td class="num">05</td><td><b>腾讯云 IoT 兼容</b><br><span style="color:var(--ink-4);font-size:12.5px">TSL 归一化、双向转换、现网验证</span></td><td><b>演示</b></td><td class="num">7 min</td><td>迁移是否要改设备</td></tr>
          <tr><td class="num">—</td><td>价值汇总与下一步</td><td>PPT</td><td class="num">4 min</td><td>怎么开始</td></tr>
        </tbody>
      </table>
      <p class="hint">建议版式：左侧纵向时间轴 + 右侧五段色块；演示段落用高亮底色，并在右上角标注「现场演示」角标。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 40 秒</small></div>
      <div class="say">
        <p>先交代节奏。前两条是方案层，我会把架构和边界讲清楚；后三条我直接开系统演示，因为这三件事——AI 好不好用、融合网关接不接得进、腾讯物模型能不能导——<strong>光看 PPT 是说服不了人的</strong>。</p>
        <p>每段演示我都会先给结论，再给操作，最后切回一页 PPT 做收口。中间如果网络或环境出问题，我准备了录屏和离线样例，不会卡在现场。</p>
      </div>
    </div>
  </div>
</section>

<!-- ================= 03 一句话摘要 ================= -->
<section id="s03">
  <div class="slide">
    <div class="bar"><span class="pg">03</span><span class="ttl">一句话摘要</span><span class="tag green">执行摘要</span></div>
    <div class="body">
      <h3 class="pt">一页纸看懂这套平台</h3>
      <p class="subpt">如果今天只记一页，请记这一页。</p>
      <table class="tbl cmp">
        <thead><tr><th style="width:130px">维度</th><th>我们做了什么</th><th style="width:210px">对贵方的意义</th></tr></thead>
        <tbody>
          <tr><td>技术底座</td><td>以社区版为底座的自研平台，时序库选国产 TDengine，接入层 / 规则引擎 / 脚本引擎微服务化</td><td><span class="mark">零商业许可费</span>，可分层水平扩容</td></tr>
          <tr><td>自主程度</td><td>内核源码全量可控，私有镜像仓库 + 自有 TKE 集群，数据全部落自有库表</td><td>不被厂商绑定，<span class="mark">可整体迁回自有 IDC</span></td></tr>
          <tr><td>交付效率</td><td>AI 助手辅助生成与校验物模型、定位数据链路问题，并可直接调用平台 OpenAPI</td><td>新产品上线更快，现场排查往返更少</td></tr>
          <tr><td>现场接入</td><td>一台融合网关聚合 OPC-UA / S7 / CAN 子设备，直连平台，共用一个标准物模型</td><td>现场不改架构，<span class="mark">不加中转服务</span></td></tr>
          <tr><td>存量迁移</td><td>物模型按腾讯 TSL 规范归一化，内置双向格式转换器，现网设备已验证全流程</td><td>迁移<span class="mark">不改设备端协议和上报格式</span></td></tr>
        </tbody>
      </table>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 45 秒</small></div>
      <div class="say">
        <p>这一页是全文摘要，后面每一段都是在为它提供证据。</p>
        <p>请注意右边这一列——<strong>技术选择本身不是目的</strong>。选国产库，是为了没有授权风险；源码可控，是为了不被绑定；AI 和融合网关，是为了让现场少跑几趟；腾讯物模型兼容，是为了让存量设备平稳搬过来。</p>
        <p>五件事其实指向同一个目标：这套平台要能<strong>长期留在贵方手里，并且越用越省</strong>。</p>
      </div>
    </div>
  </div>
</section>

<!-- ================= 04 主线 ================= -->
<section id="s04">
  <div class="slide">
    <div class="bar"><span class="pg">04</span><span class="ttl">本次主线：从选型到落地</span><span class="tag">过渡页</span></div>
    <div class="body">
      <h3 class="pt">五个问题，一次回答</h3>
      <div class="cols c3">
        <div class="cardlet"><h4><span class="ic">Q1</span>能不能自主选型</h4><p>不用商业授权组件，扩容不受许可条款约束。</p></div>
        <div class="cardlet"><h4><span class="ic">Q2</span>会不会被绑定</h4><p>源码、数据、部署三件事都握在自己手里。</p></div>
        <div class="cardlet"><h4><span class="ic">Q3</span>能不能提效</h4><p>AI 介入物模型与排障，缩短上线与定位时间。</p></div>
        <div class="cardlet"><h4><span class="ic">Q4</span>现场怎么接</h4><p>融合网关聚合多协议，单跳直连，统一物模型。</p></div>
        <div class="cardlet"><h4><span class="ic">Q5</span>存量怎么搬</h4><p>腾讯 TSL 直接导入，设备端协议不动。</p></div>
        <div class="cardlet amber"><h4><span class="ic">!</span>今天的边界</h4><p>只讲已验证的能力；规划项会明确标注，不和现状混在一起。</p></div>
      </div>
      <p class="hint">建议版式：五个问题做成编号卡片，右下角用对比色放「边界声明」——这一条会明显提升技术可信度。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 40 秒</small></div>
      <div class="say">
        <p>进入正题之前，我先声明一个原则：<strong>今天讲到的每一项能力，都对应一个可验证的对象</strong>——要么是一段代码，要么是一张截图，要么是现场能跑的操作。还在规划里的东西，我会明确说"这是下一步"，不和现状混着讲。</p>
        <p>因为技术汇报最怕两件事：一是讲得太满，验收时对不上；二是讲得太虚，客户没法判断风险。我们尽量把这两件事都避开。</p>
      </div>
    </div>
  </div>
</section>
