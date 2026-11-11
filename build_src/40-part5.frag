<!-- ================= 05 腾讯云 IoT 兼容 ================= -->
<section id="s19">
  <div class="chapter">
    <div class="num">PART 05 / 腾讯云 IoT 兼容</div>
    <h2>腾讯云 IoT 兼容</h2>
    <p class="lede">这一段针对存量迁移：<b>已有的腾讯侧物模型能不能直接搬、设备端要不要改。</b>三个结论——按 TSL 规范归一化、内置双向转换器、现网设备已验证全流程。</p>
    <div class="chips">
      <span class="chip"><b>7 分钟</b></span>
      <span class="chip">形式：PPT 2 页 + 演示 1 段</span>
      <span class="chip">关键词：TSL 归一化 · 双向转换 · 现网验证</span>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">19</span><span class="ttl">物模型按腾讯 TSL 规范归一化</span><span class="tag">兼容</span></div>
    <div class="body">
      <h3 class="pt">腾讯侧的物模型，可以直接导入</h3>
      <p class="subpt">平台在导入入口就完成格式识别与归一化，客户不需要先"翻译"一遍。</p>
      <ul class="pts">
        <li><b>按腾讯 TSL 规范归一化</b>：属性、事件、行为统一映射到平台标准 TSL，保留类型、范围、单位、枚举、结构体层级。
          <span>归一化发生在导入阶段，落库的是标准模型，后续规则链、看板、API 全部按标准模型工作。</span></li>
        <li><b>腾讯侧物模型可直接导入</b>：不需要先导出成表格、再人工重建；导入即识别、即校验、即生效。
          <span>对存量项目，这一步省掉的是"重建模型 + 重新联调"的整段时间。</span></li>
        <li><b>识别是自动的</b>：平台根据物模型特征（腾讯格式的 <code class="inl">define</code> 定义）判定来源，不要求操作员先声明"这是腾讯格式"。
          <span>标准 TSL 与腾讯格式走同一个导入入口，不会导错。</span></li>
      </ul>
      <div class="cols c2">
        <div class="cardlet blue"><h4><span class="ic">✓</span>保留的信息</h4><p>数据类型、取值范围、枚举映射、单位、读写模式、事件参数、结构体字段层级。</p></div>
        <div class="cardlet amber"><h4><span class="ic">!</span>需要确认的信息</h4><p>字符串型 min/max 这类源数据元信息，默认按规范丢弃；需要保留时用参数显式开启，<b>不偷偷改语义</b>。</p></div>
      </div>
      <p class="hint">建议版式：左侧腾讯 TSL 片段、右侧平台 TSL 片段，中间一个大箭头标「归一化」；下方用两个卡片区分"保留"与"需确认"，体现严谨。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 30 秒</small></div>
      <div class="say">
        <p>最后一部分，腾讯云 IoT 兼容。这一段的背景很实际：贵方已有腾讯侧的平台和物模型，<strong>迁移最大的成本不是平台，是模型重建和设备重联调</strong>。</p>
        <p>我们的做法是：在导入入口做<strong>归一化</strong>。腾讯的物模型进来，自动识别、自动映射到平台标准 TSL，类型、范围、枚举、结构体层级都保留。落库的是标准模型，后面规则链、看板、API 都按标准模型走。</p>
        <p>有一个细节我想说明：识别是<strong>自动判断</strong>的，不要求操作员先声明"这是腾讯格式"，标准 TSL 和腾讯格式走同一个入口，不会导错。</p>
        <p>另外，字符串型 min/max 这种源数据元信息，默认按规范丢弃；要保留就得显式开参数。<strong>我们不改语义，只做显式转换。</strong></p>
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">20</span><span class="ttl">内置腾讯格式转换器</span><span class="tag">双向</span></div>
    <div class="body">
      <h3 class="pt">双向转换，设备端协议与上报格式都不用动</h3>
      <p class="subpt">迁移不是单向的"搬进来"，也包括将来"导回去"——所以转换器做成双向。</p>
      <table class="tbl">
        <thead><tr><th style="width:170px">转换项</th><th>腾讯 IoT 物模型</th><th>平台标准 TSL</th></tr></thead>
        <tbody>
          <tr><td>字段类型</td><td><code class="inl">dataType</code></td><td><code class="inl">type</code></td></tr>
          <tr><td>数值范围</td><td>字符串形式 <code class="inl">"0" / "100"</code></td><td>数值 <code class="inl">0 / 100</code></td></tr>
          <tr><td>枚举</td><td><code class="inl">stringenum</code> + mapping</td><td><code class="inl">enum_string</code>，mapping 保留</td></tr>
          <tr><td>结构体</td><td><code class="inl">struct.specs</code> 数组</td><td>以字段 id 为键的对象</td></tr>
          <tr><td>事件参数</td><td>内嵌 <code class="inl">define</code></td><td>同步转换为参数定义</td></tr>
        </tbody>
      </table>
      <pre><span class="c"># 腾讯侧（节选）</span>
"define": { "dataType": { "type": "int" }, "min": "0", "max": "100", "unit": "%" }

<span class="c"># 平台 TSL（节选）</span>
"type": "int", "min": 0, "max": 100, "unit": "%"</pre>
      <ul class="pts tight">
        <li><b>迁移不改设备端协议</b>：设备继续按原有 MQTT 主题和报文格式上报，平台侧完成格式归一。</li>
        <li><b>迁移不改上报格式</b>：字段名、类型、时间戳口径保持一致，历史数据与实时数据的语义连续。</li>
      </ul>
      <p class="hint">建议版式：上方字段映射表，下方左右两段 JSON 对比（腾讯 / 平台），高亮改动的那两行；不要贴整份 JSON，客户看的是规则不是全文。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 40 秒</small></div>
      <div class="say">
        <p>这一页讲转换器。为什么要强调"双向"？因为迁移不是单向的——今天搬进来，将来也可能要导回腾讯侧做对比或并行，所以两个方向都得有。</p>
        <p>具体规则不复杂，但有三个坑：<strong>数值字符串要转数字、stringenum 要映射成 enum_string、struct 的 specs 数组要转成对象</strong>。这些如果靠人工改，量大了一定出错；做成转换器，规则固定、可回归测试。</p>
        <p>对客户最重要的两句话在下面：<strong>迁移不改设备端协议，也不改上报格式</strong>。设备该发什么还发什么，字段名、类型、时间戳口径保持一致，历史数据和实时数据的语义是连续的。</p>
      </div>
    </div>
  </div>

  <!-- 演示 E -->
  <div class="slide" id="s21">
    <div class="bar"><span class="pg">21</span><span class="ttl">演示 E：导入、校验、同步全流程</span><span class="tag green">现场演示 ⑤</span></div>
    <div class="body">
      <h3 class="pt">一份腾讯物模型，从文件到可用产品</h3>
      <p class="subpt">建议用真实项目里的物模型文件演示，比示例文件更有说服力。</p>
      <table class="tbl">
        <thead><tr><th style="width:52px">阶段</th><th>动作</th><th>成功判据</th></tr></thead>
        <tbody>
          <tr><td class="num">1</td><td>导入腾讯格式物模型文件</td><td>自动识别来源，无需手工声明</td></tr>
          <tr><td class="num">2</td><td>平台校验</td><td>结构校验 + 业务校验全部通过</td></tr>
          <tr><td class="num">3</td><td>创建产品并同步</td><td>产品配置、资产、规则链自动生成</td></tr>
          <tr><td class="num">4</td><td>现网格式报文上报</td><td>不改报文，数据正常校验并落库</td></tr>
        </tbody>
      </table>
    </div>
    <div class="demo">
      <div class="hd"><span class="badge">DEMO E</span><span class="t">导入 → 校验 → 同步 → 现网报文验证</span><span class="dur">约 3 分钟</span></div>
      <div class="bd">
        <p class="goal">演示目标：一条完整证据链，证明 <b>迁移不需要改设备、不需要重建模型</b>。</p>
        <ol class="steps">
          <li>在产品页上传腾讯格式物模型文件，展示<b>自动识别</b>与归一化结果。</li>
          <li>打开校验结果：结构、业务两类问题均为 0；保存后状态变为已发布。</li>
          <li>展示产品详情：产品配置、产品资产、规则链、属性/事件/行为数量已生成。</li>
          <li>用<b>原腾讯格式报文</b>模拟设备上报（不改字段、不改类型），平台正常校验并显示数据点。</li>
        </ol>
        <div class="expect"><div class="k">预期结果</div><div class="v">导入、校验、同步三阶段全部通过；<b>唯一改动是"平台换了"，设备端零改动</b>。</div></div>
        <div class="expect"><div class="k">讲解要点</div><div class="v">第 4 步是全场重点：报文截图里字段与腾讯侧一致，平台侧能看到值。<b>这一步走通，"迁移成本"这个问题就基本回答了。</b></div></div>
      </div>
      <div class="fallback"><span class="k">兜底</span>网络或环境异常时：切到离线转换脚本现场跑一遍（同一套规则），再展示已完成的导入与同步截图；<b>提前准备一份转换前后的 diff 文件</b>。</div>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 3 分钟</small></div>
      <div class="say">
        <p>最后一段演示，腾讯物模型的完整迁移流程。我用一份真实的物模型文件，不走示例。</p>
        <p><span class="beat">操作中</span> 上传——平台自动识别这是腾讯格式，直接给出归一化结果。校验，结构校验和业务校验都是 0 问题。保存，产品发布，产品配置、资产、规则链全部自动生成。</p>
        <p><span class="beat">操作中</span> 最后一步最关键：我用<strong>原腾讯格式的报文</strong>模拟设备上报，字段名、类型一个没改。各位看，平台正常校验、正常落库。</p>
        <p>这就把"迁移成本"这个问题回答清楚了：<strong>唯一变的是平台，设备端零改动。</strong>不需要改固件、不需要改上报格式、不需要重新联调协议。</p>
        <p>这三个阶段——导入、校验、同步——我们已经在现网设备上完整跑过，不是只在测试环境验证过格式。</p>
      </div>
    </div>
  </div>
</section>
