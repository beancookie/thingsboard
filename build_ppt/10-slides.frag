<!-- 01 封面 -->
<section class="slide dark">
  <div class="cover">
    <span class="eyebrow">技术汇报 · 中国中铁物联网平台</span>
    <h1>信创底座<br>与<em>智能化演进</em></h1>
    <p class="desc">国产时序库 · 全栈无商业许可费 · 源码与数据自主可控 · AI 辅助建模与运维 · 融合终端与腾讯云 IoT 平滑接入</p>
    <div class="meta"><span><b>汇报人</b>　（填写）</span><span><b>日期</b>　2026 年 11 月</span><span><b>时长</b>　约 30 分钟</span></div>
    <div class="pillars">
      <div class="p"><div class="n">01</div><h4>信创与可扩展</h4><p>零许可费 · 分层扩容</p></div>
      <div class="p"><div class="n">02</div><h4>自主可控</h4><p>源码 · 数据 · 可迁移</p></div>
      <div class="p"><div class="n">03</div><h4>AI 辅助</h4><p>建模 · 排障 · OpenAPI</p></div>
      <div class="p"><div class="n">04</div><h4>融合终端接入</h4><p>多协议 · 单跳直连</p></div>
      <div class="p"><div class="n">05</div><h4>腾讯云 IoT 兼容</h4><p>TSL 归一化 · 双向转换</p></div>
    </div>
  </div>
</section>

<!-- 02 目录 -->
<section class="slide" data-note="五条主线 · 三个现场演示 · 总时长约 30 分钟">
  <div class="head">
    <span class="kicker">Agenda</span>
    <h2 class="title">五条主线，三个现场演示</h2>
    <p class="sub">前两条讲方案与边界，后三条直接看系统——能跑的东西才值得汇报。</p>
  </div>
  <div class="agenda">
    <div class="ag"><span class="no">01</span><div><h4>信创与可扩展</h4><p>国产时序库、微服务分层、单集群 3 万台验证</p></div><span class="time">5 min</span></div>
    <div class="ag"><span class="no">02</span><div><h4>自主可控</h4><p>源码可控、数据自有、私有仓库 + 可迁移</p></div><span class="time">4 min</span></div>
    <div class="ag demo"><span class="no">03</span><div><h4>AI 辅助</h4><p>生成校验物模型、链路排障、对话式调用 OpenAPI</p></div><span class="time">8 min</span></div>
    <div class="ag demo"><span class="no">04</span><div><h4>融合终端无缝接入</h4><p>一台网关聚合多协议、单跳直连、统一物模型</p></div><span class="time">8 min</span></div>
    <div class="ag demo"><span class="no">05</span><div><h4>腾讯云 IoT 兼容</h4><p>TSL 归一化、双向转换器、现网全流程验证</p></div><span class="time">7 min</span></div>
    <div class="ag"><span class="no">—</span><div><h4>价值汇总与下一步</h4><p>成本结构、迁移路径、PoC 排期建议</p></div><span class="time">4 min</span></div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">02 / 24</span></div>
</section>

<!-- 03 总览 -->
<section class="slide" data-note="零商业许可费 · 单集群 3 万台已验证 · 腾讯迁移设备端零改动">
  <div class="head">
    <span class="kicker">Executive Summary</span>
    <h2 class="title">一页纸看懂这套平台</h2>
  </div>
  <div class="statband" style="margin-bottom:26px">
    <div class="s"><div class="v">5<span class="plus">+</span></div><div class="k">核心交付主题</div></div>
    <div class="s"><div class="v">3<span class="plus">万</span></div><div class="k">单集群已验证接入设备</div></div>
    <div class="s"><div class="v">0</div><div class="k">商业许可费用</div></div>
    <div class="s"><div class="v">0</div><div class="k">设备端改动（腾讯迁移）</div></div>
  </div>
  <table class="cmp">
    <thead><tr><th style="width:150px">维度</th><th>我们做了什么</th><th style="width:280px">对贵方的意义</th></tr></thead>
    <tbody>
      <tr><td>技术底座</td><td>社区版为底座的自主平台，时序库选国产 TDengine，接入 / 规则 / 脚本微服务化</td><td class="ok">零商业许可费，可分层扩容</td></tr>
      <tr><td>自主程度</td><td>内核源码全量可控，私有镜像仓库 + 自有 TKE 集群，数据全部落自有库表</td><td class="ok">不被绑定，可整体迁回自有 IDC</td></tr>
      <tr><td>交付效率</td><td>AI 辅助生成与校验物模型、定位链路问题、直接调用平台 OpenAPI</td><td>上线更快，现场排查往返更少</td></tr>
      <tr><td>现场接入</td><td>融合网关聚合 OPC-UA / S7 / CAN，直连平台，共用一个标准物模型</td><td class="ok">不加中转服务，改造量小</td></tr>
      <tr><td>存量迁移</td><td>物模型按腾讯 TSL 规范归一化，内置双向转换器，现网设备已验证</td><td class="ok">不改设备端协议与上报格式</td></tr>
    </tbody>
  </table>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">03 / 24</span></div>
</section>

<!-- 04 信创选型 -->
<section class="slide" data-note="TDengine · 一设备一子表 · 无按节点 / 设备 / 核数计费的商业授权">
  <div class="head">
    <span class="kicker">01 信创与可扩展</span>
    <h2 class="title">国产时序库 TDengine，全栈不背许可费</h2>
    <p class="sub">信创不是换 Logo，而是把"授权"这条风险从架构里拿掉。</p>
  </div>
  <div class="split">
    <div>
      <ul class="b">
        <li><b>时序库选用国产 TDengine</b><br><span>一设备一子表，按产品建超级表，贴合工业时序场景</span></li>
        <li><b>全栈无商业许可费用</b><br><span>不按节点、设备、核数计费；扩容加服务器，不加合同</span></li>
        <li><b>规避三类授权风险</b><br><span>许可到期、审计追溯、版本升级被条款反向约束</span></li>
      </ul>
    </div>
    <div>
      <table class="cmp">
        <thead><tr><th>成本项</th><th>商业库方案</th><th>本方案</th></tr></thead>
        <tbody>
          <tr><td>许可费</td><td>随规模递增</td><td class="ok">无</td></tr>
          <tr><td>扩容成本</td><td>算力 + 授权</td><td class="ok">仅算力</td></tr>
          <tr><td>授权审计</td><td>长期台账</td><td class="ok">无此事项</td></tr>
          <tr><td>版本升级</td><td>受商业周期约束</td><td class="ok">自主发版</td></tr>
        </tbody>
      </table>
      <div class="card teal" style="margin-top:16px"><p><b>一句话：</b>业务翻倍时增加的是服务器，不是一份新的 License 合同。</p></div>
    </div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">04 / 24</span></div>
</section>

<!-- 05 分层扩容 -->
<section class="slide" data-note="接入 / 规则 / 脚本三层解耦 · 扩容动作只有「副本 +N」一种形态">
  <div class="head">
    <span class="kicker">01 信创与可扩展</span>
    <h2 class="title">三层解耦，谁先到瓶颈就扩谁</h2>
    <p class="sub">扩容不是整机加配，而是按层加副本——架构决定，不是运维技巧。</p>
  </div>
  <div class="stack" style="margin-bottom:22px">
    <div class="layer"><span class="name">接入层</span><span class="desc">MQTT 接入与设备会话，多副本前置负载均衡</span><span class="tag">设备数增长 → 扩</span></div>
    <div class="layer"><span class="name">规则引擎</span><span class="desc">产品规则链，遥测校验、事件分流、消息外发</span><span class="tag">吞吐上涨 → 扩</span></div>
    <div class="layer"><span class="name">脚本引擎</span><span class="desc">规则链内计算逻辑，独立部署</span><span class="tag">计算变重 → 扩</span></div>
  </div>
  <div class="chain">
    <div class="n"><b>DEVICE</b>设备 / 网关</div>
    <div class="n"><b>L1</b>接入层</div>
    <div class="n"><b>L2</b>规则引擎</div>
    <div class="n"><b>KAFKA</b>遥测 / 事件 / 非法</div>
    <div class="n hot"><b>STORE</b>TDengine</div>
  </div>
  <p class="lead" style="margin:0"><b>扩容动作只有一种形态：</b>副本 +N。不改业务代码，不改数据模型。</p>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">05 / 24</span></div>
</section>

<!-- 06 容量验证 -->
<section class="slide" data-note="30,000 台 / 单集群 · 四类增长对应四种加法 · 均不需改架构">
  <div class="head">
    <span class="kicker">01 信创与可扩展</span>
    <h2 class="title">单集群已验证 3 万台设备接入</h2>
    <p class="sub">规模不是靠规划支撑的，是靠跑过的集群支撑的。</p>
  </div>
  <div class="split" style="grid-template-columns:.82fr 1.18fr">
    <div>
      <div class="bignum">30,000<small>台 / 集群</small></div>
      <p class="lead" style="margin-top:14px">接入、校验、存储全链路跑通，不是只测连接数。</p>
      <div class="card" style="margin-top:6px"><p><b>扩张路径：</b>接入层副本 → 规则引擎副本 → 脚本引擎副本 → TDengine 节点与时间分区，四段增长对应四种加法。</p></div>
    </div>
    <div>
      <table class="cmp">
        <thead><tr><th style="width:120px">场景</th><th>动作</th><th style="width:90px">改架构</th></tr></thead>
        <tbody>
          <tr><td>设备数翻倍</td><td>接入层副本 +N，前置 LB 扩容</td><td class="ok">否</td></tr>
          <tr><td>上报频率提高</td><td>规则引擎副本 +N</td><td class="ok">否</td></tr>
          <tr><td>规则复杂度上升</td><td>脚本引擎独立扩容</td><td class="ok">否</td></tr>
          <tr><td>历史数据膨胀</td><td>TDengine 加节点 / 副本 / 时间分区</td><td class="ok">否</td></tr>
        </tbody>
      </table>
      <div class="card amber" style="margin-top:16px"><p><b>口径：</b>压测条件（并发连接、上报频率、报文大小、集群规格）见压测报告，本页只给结论。</p></div>
    </div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">06 / 24</span></div>
</section>

<!-- 07 源码可控 -->
<section class="slide" data-note="内核全量源码 · 私有镜像仓库 · 改得动 / 发得出 / 退得回">
  <div class="head">
    <span class="kicker">02 自主可控</span>
    <h2 class="title">第一层：源码在手里</h2>
    <p class="sub">不需要向原厂提需求、等排期、等版本——这条决定响应速度。</p>
  </div>
  <div class="grid g3" style="margin-bottom:22px">
    <div class="card"><h4><span class="no">01</span>改得动</h4><p>内核全量源码，含接入、规则链、物模型、前端；需求直接改代码，不等第三方排期。</p></div>
    <div class="card"><h4><span class="no">02</span>发得出</h4><p>自有流水线与私有镜像仓库，版本节奏跟项目走，不跟社区日历。</p></div>
    <div class="card"><h4><span class="no">03</span>退得回</h4><p>镜像与数据迁移均可回滚，升级不是单向门。</p></div>
  </div>
  <ul class="b sm">
    <li><b>依赖边界清晰：</b>PostgreSQL 元数据、TDengine 时序、Kafka 消息，全部可自主部署，无强制云依赖。</li>
    <li><b>离线可交付：</b>断网环境同样可部署运行，不依赖厂商云回连。</li>
  </ul>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">07 / 24</span></div>
</section>

<!-- 08 数据可控 -->
<section class="slide" data-note="PostgreSQL + TDengine + Kafka 全部自有 · 可审计 / 可带走">
  <div class="head">
    <span class="kicker">02 自主可控</span>
    <h2 class="title">第二层：数据在自己库里</h2>
    <p class="sub">每一类数据都写清落在哪张库表、哪个主题——不托管、不留后门。</p>
  </div>
  <table class="cmp" style="margin-bottom:20px">
    <thead><tr><th style="width:150px">数据类型</th><th style="width:230px">落库位置</th><th>说明</th></tr></thead>
    <tbody>
      <tr><td>设备与凭证</td><td>自有 PostgreSQL</td><td>设备实例、访问令牌、网关与子设备关系</td></tr>
      <tr><td>时序数据</td><td>自有 TDengine</td><td>一设备一子表，可自主备份、归档、分区</td></tr>
      <tr><td>物模型 / 产品</td><td>自有 PostgreSQL（plat_*）</td><td>TSL 原文、版本、目录、校验和</td></tr>
      <tr><td>规则与脚本</td><td>自有 PostgreSQL + 规则链</td><td>按产品生成，随版本纳管</td></tr>
      <tr><td>消息总线</td><td>自有 Kafka</td><td>遥测 / 事件 / 非法数据三类主题</td></tr>
    </tbody>
  </table>
  <div class="grid g2">
    <div class="card teal"><h4>可审计</h4><p>库表、主题、分区都在贵方集群内，DBA 直接核对，无需向厂商申请导出。</p></div>
    <div class="card teal"><h4>可带走</h4><p>数据模型开放、备份策略自主，迁移不依赖厂商"数据导出服务"。</p></div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">08 / 24</span></div>
</section>

<!-- 09 部署可控 -->
<section class="slide" data-note="私有仓库 + 自有 TKE · 迁移三步：镜像同步 → 清单替换 → 数据演练">
  <div class="head">
    <span class="kicker">02 自主可控</span>
    <h2 class="title">第三层：整套系统搬得走</h2>
    <p class="sub">私有镜像仓库 + 自有 TKE 集群，可整体迁移至贵方 IDC。</p>
  </div>
  <div style="display:flex; align-items:center; gap:18px; margin:10px 0 26px">
    <div class="panel" style="flex:1"><h4><span class="badge">NOW</span>自有 TKE 集群</h4><p>平台、物模型、AI 助手、视频网关均容器化；镜像来自私有仓库，配置与密钥走 ConfigMap / Secret。</p></div>
    <div style="font-family:var(--mono); color:var(--teal); font-size:28px; letter-spacing:-.05em">⟶</div>
    <div class="panel good" style="flex:1"><h4><span class="badge">TARGET</span>贵方自有 IDC</h4><p>Kubernetes 清单、镜像、配置整体平移；只替换仓库地址、存储类与网络出口，<b>应用代码不改</b>。</p></div>
  </div>
  <div class="flow">
    <div class="chip-flow"><span class="n">STEP 1</span><b>镜像同步</b><span>私有仓库镜像批量推送至客户仓库</span><span class="arr">→</span></div>
    <div class="chip-flow"><span class="n">STEP 2</span><b>清单替换</b><span>仓库地址、存储类、Ingress 与出口策略</span><span class="arr">→</span></div>
    <div class="chip-flow"><span class="n">STEP 3</span><b>数据演练</b><span>先在测试集群验证，再切生产</span><span class="arr">✓</span></div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">09 / 24</span></div>
</section>

<!-- 10 AI 总览 -->
<section class="slide" data-note="AI 提建议，平台校验执行 · 只读直连 / 写入确认 / 高危审计">
  <div class="demo-tag"><i></i>现场演示</div>
  <div class="head">
    <span class="kicker">03 AI 辅助</span>
    <h2 class="title">三个场景，一条原则</h2>
    <p class="sub">AI 只提建议，平台负责校验与执行。</p>
  </div>
  <div class="grid g3" style="margin-bottom:22px">
    <div class="card"><h4><span class="no">A</span>生成与校验物模型</h4><p>自然语言描述设备 → TSL 草案 → 平台三道校验 → 保存即生效。</p></div>
    <div class="card"><h4><span class="no">B</span>定位数据链路问题</h4><p>凭证 → 产品 → 规则链 → 主题 → 时序库，逐段排查并指出断点。</p></div>
    <div class="card"><h4><span class="no">C</span>调用平台 OpenAPI</h4><p>搜索并调用平台接口，可扩展为运维问答入口；写操作必须确认。</p></div>
  </div>
  <div class="split">
    <div class="panel good"><h4><span class="badge">CONTROL</span>受控边界</h4><ul><li>只读直连，<b>写入生成待确认动作</b></li><li>高危操作二次确认并记审计</li><li>沿用 JWT 与租户隔离，不绕权限</li></ul></div>
    <div class="panel bad"><h4><span class="badge">LIMIT</span>表述边界</h4><p>生成的是<b>草案</b>，必须过平台校验才落库；"AI 直接改生产数据"这种说法不成立，今天也不讲。</p></div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">10 / 24</span></div>
</section>

<!-- 11 演示 A -->
<section class="slide" data-note="草案必须过平台校验才落库 · 校验失败给出逐条定位">
  <div class="demo-tag"><i></i>演示 A</div>
  <div class="head">
    <span class="kicker">03 AI 辅助</span>
    <h2 class="title">从一段设备描述到一个可用产品</h2>
  </div>
  <div class="split">
    <div>
      <ol class="steps">
        <li>口述需求：属性、单位、范围、告警条件</li>
        <li>AI 产出 <b>TSL 草案</b></li>
        <li>平台三道校验：结构 / 业务 / 运行时就绪</li>
        <li>修正后保存，<b>状态直接为已发布</b></li>
        <li>产品配置、资产、规则链自动生成</li>
      </ol>
    </div>
    <div>
      <div class="panel" style="margin-bottom:14px"><h4>校验不是一句话</h4><p>逐条指出<b>第几个字段、错在哪、期望是什么</b>，而不是笼统的"校验失败"。</p></div>
      <div class="panel good"><h4><span class="badge">KEY</span>要看到的画面</h4><p>故意留一处类型错误 → 问题列表 → 修正 → 全绿。<b>AI 会犯错，但落库前一定被拦住。</b></p></div>
    </div>
  </div>
  <div class="done-row">
    <div class="done"><b>预期结果</b>产品 ID 全系统唯一，保存即发布，平台三件套自动就绪</div>
    <div class="done"><b>兜底</b>模型不稳定时改演示"上传 TSL → 修改 → 校验 → 生效"</div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">11 / 24</span></div>
</section>

<!-- 12 演示 B -->
<section class="slide" data-note="五段可观测链路 · 非法数据隔离在 iot.invalid，可回放、可追溯">
  <div class="demo-tag"><i></i>演示 B</div>
  <div class="head">
    <span class="kicker">03 AI 辅助</span>
    <h2 class="title">一条数据没上来，到底断在哪一段</h2>
  </div>
  <div class="chain" style="margin-bottom:20px">
    <div class="n"><b>①</b>设备凭证</div>
    <div class="n"><b>②</b>产品配置</div>
    <div class="n hot"><b>③</b>规则链校验</div>
    <div class="n"><b>④</b>Kafka 主题</div>
    <div class="n"><b>⑤</b>时序库</div>
  </div>
  <div class="split">
    <div>
      <table class="cmp">
        <thead><tr><th style="width:120px">症状</th><th>断点</th></tr></thead>
        <tbody>
          <tr><td>设备离线</td><td>① 凭证 / 网络</td></tr>
          <tr><td>在线无数据</td><td>② 产品绑定</td></tr>
          <tr><td>数据被丢弃</td><td>③ 类型 / 范围 / 枚举</td></tr>
          <tr><td>主题有、库无</td><td>④ ⑤ 入湖</td></tr>
        </tbody>
      </table>
    </div>
    <div>
      <div class="panel" style="margin-bottom:14px"><h4>现场演示的动作</h4><p>先造一条<b>类型错误</b>的遥测 → 问 AI"设备在线但查不到数据" → 它在<b>非法主题</b>里给出原始报文与字段结论 → 修正后数据入库。</p></div>
      <div class="card amber"><p><b>关键设计：</b>非法数据不是丢弃，是隔离到独立主题，可回放、可追溯——排障的前提是链路留了证据。</p></div>
    </div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">12 / 24</span></div>
</section>

<!-- 13 演示 C -->
<section class="slide" data-note="接口目录解耦「新增接口」与「新增工具」· 执行权始终在人">
  <div class="demo-tag"><i></i>演示 C</div>
  <div class="head">
    <span class="kicker">03 AI 辅助</span>
    <h2 class="title">对话即操作，写入必须人点头</h2>
  </div>
  <div class="split" style="margin-bottom:20px">
    <div class="panel good"><h4><span class="badge">READ</span>读操作直接执行</h4><p>查租户、查产品、查设备、查告警、查网关列表；返回结构化结果，不产生待确认动作。</p></div>
    <div class="panel bad"><h4><span class="badge">WRITE</span>写操作必须确认</h4><p>动作名、参数、风险等级一并展示；确认后才调用平台 REST；<b>高危二次确认并记审计</b>。</p></div>
  </div>
  <div class="grid g3">
    <div class="card"><h4>接口目录可扩展</h4><p>新增接口只补目录配置，不改助手插件——这是"可扩展为运维问答入口"的基础。</p></div>
    <div class="card"><h4>权限不绕过</h4><p>沿用 JWT 与租户隔离，租户管理员看不到其他租户数据。</p></div>
    <div class="card"><h4>复杂动作有 handler</h4><p>建产品要带 TSL、建设备要写服务端属性，不交给模型自由发挥。</p></div>
  </div>
  <p class="lead" style="margin-top:22px">演示要点：<b>点"取消"之后要停两秒</b>——让客户亲眼看到系统什么都没有执行。</p>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">13 / 24</span></div>
</section>

<!-- 14 融合终端 -->
<section class="slide" data-note="OPC-UA / S7 / CAN 在网关内收敛 · 对外只有一条 MQTT 连接">
  <div class="demo-tag"><i></i>现场演示</div>
  <div class="head">
    <span class="kicker">04 融合终端无缝接入</span>
    <h2 class="title">一台边缘网关，聚合多类子设备</h2>
    <p class="sub">协议差异在边缘消化，平台侧只看到"设备 + 物模型"。</p>
  </div>
  <div class="grid g3" style="margin-bottom:20px">
    <div class="card"><h4><span class="no">P1</span>OPC-UA</h4><p>PLC / DCS / 产线控制，按节点读取，结构化工艺参数。</p></div>
    <div class="card"><h4><span class="no">P2</span>S7</h4><p>西门子系列，直接读 DB 块，存量产线低成本改造。</p></div>
    <div class="card"><h4><span class="no">P3</span>CAN</h4><p>车载、工程机械、控制器局域网，高频短帧运行数据。</p></div>
  </div>
  <div class="chain">
    <div class="n"><b>OPC-UA</b>PLC / DCS</div>
    <div class="n"><b>S7</b>西门子设备</div>
    <div class="n"><b>CAN</b>工程机械</div>
    <div class="n hot"><b>GATEWAY</b>融合网关 · 单连接</div>
    <div class="n"><b>MQTT</b>物联网平台</div>
  </div>
  <p class="lead" style="margin:0">平台侧：一个网关设备 + Contains 关系挂载子设备，<b>不感知现场总线类型</b>。</p>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">14 / 24</span></div>
</section>

<!-- 15 单跳直连 -->
<section class="slide" data-note="平台原生网关模式与 v1/gateway/* 主题 · 链路少一跳、运维少一套">
  <div class="head">
    <span class="kicker">04 融合终端无缝接入</span>
    <h2 class="title">无需中转服务：网关直连平台</h2>
    <p class="sub">去掉中间那一段，少一个故障点、少一套运维。</p>
  </div>
  <div class="split" style="margin-bottom:22px">
    <div class="panel bad"><h4><span class="badge">×</span>网关 + 中转服务</h4><ul><li>网关 → 中转 → 平台，多一跳</li><li>中转层要单独部署、监控、扩容</li><li>排障需跨系统，先查中转</li></ul></div>
    <div class="panel good"><h4><span class="badge">✓</span>融合网关直连</h4><ul><li>网关 MQTT 直连平台网关模式</li><li>平台原生支持网关主题与子设备关系</li><li><b>没有中转服务这一层</b></li></ul></div>
  </div>
  <table class="cmp">
    <thead><tr><th style="width:170px">对比项</th><th>网关 + 中转</th><th>融合网关直连</th></tr></thead>
    <tbody>
      <tr><td>部署单元</td><td>网关 + 中转 + 队列</td><td class="ok">仅网关</td></tr>
      <tr><td>故障点</td><td>多一层，跨系统排障</td><td class="ok">单跳</td></tr>
      <tr><td>子设备建模</td><td>中转侧再维护一套映射</td><td class="ok">平台侧标准物模型</td></tr>
      <tr><td>扩容</td><td>中转层跟着扩</td><td class="ok">边缘加终端即可</td></tr>
    </tbody>
  </table>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">15 / 24</span></div>
</section>

<!-- 16 统一物模型 -->
<section class="slide" data-note="同一份 TSL · 同一套规则链校验 · 下游不区分接入方式">
  <div class="head">
    <span class="kicker">04 融合终端无缝接入</span>
    <h2 class="title">网关与子设备共用一套标准物模型</h2>
    <p class="sub">不是"网关一套格式、平台一套格式"，而是同一份 TSL、同一套校验。</p>
  </div>
  <div class="grid g3" style="margin-bottom:22px">
    <div class="card"><h4>同一份 TSL</h4><p>子设备沿用产品物模型，网关只做点位到字段的映射；同型号换网关，模型不重建。</p></div>
    <div class="card"><h4>同一套校验</h4><p>网关上报同样过产品规则链：类型、范围、枚举、必填，一项不少。</p></div>
    <div class="card"><h4>同一条链路</h4><p>与直连设备走同一 Kafka 主题、同一入湖逻辑，下游无需区分接入方式。</p></div>
  </div>
  <div class="split">
    <div class="card flat"><h4>横向：多网关复用</h4><p>同一产品在多个工点、多台网关上复用同一模型，新增工点只加网关实例。</p></div>
    <div class="card flat"><h4>纵向：平台无感</h4><p>规则、告警、看板、API 全部按统一模型工作，不为网关单开分支。</p></div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">16 / 24</span></div>
</section>

<!-- 17 演示 D -->
<section class="slide" data-note="子设备是标准设备对象 · 可检索、可授权、可被规则引用">
  <div class="demo-tag"><i></i>演示 D</div>
  <div class="head">
    <span class="kicker">04 融合终端无缝接入</span>
    <h2 class="title">三步完成融合终端接入</h2>
    <p class="sub">建议用实物网关或现场录屏，比模拟器更有说服力。</p>
  </div>
  <div class="split">
    <div>
      <ol class="steps">
        <li>网关以网关模式上线：<b>在线状态与连接时间刷新</b></li>
        <li>子设备注册并上线，建立 Contains 关系：<b>网关设备页签可见</b></li>
        <li>三类协议数据上报：<b>同一产品下三个子设备均有数据点</b></li>
        <li>平台下发 RPC，网关转发：<b>设备回执、状态变化</b></li>
      </ol>
    </div>
    <div>
      <div class="panel" style="margin-bottom:14px"><h4>要看懂这件事</h4><p>子设备在平台里是<b>标准设备对象</b>：有属性、有关系、有在线状态，能被检索、授权、规则引用。</p></div>
      <div class="card amber"><p><b>反面案例：</b>只把一包数据透传上来，平台无法对子设备做治理——那不叫接入。</p></div>
    </div>
  </div>
  <div class="done-row">
    <div class="done"><b>预期结果</b>子设备与直连设备无差别进入规则链与时序库</div>
    <div class="done"><b>兜底</b>无实物网关时播放 2 分钟接入录屏，或本地模拟脚本复现</div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">17 / 24</span></div>
</section>

<!-- 18 腾讯归一化 -->
<section class="slide" data-note="导入即识别、即归一化 · 标准 TSL 与腾讯格式同一入口">
  <div class="head">
    <span class="kicker">05 腾讯云 IoT 兼容</span>
    <h2 class="title">腾讯侧物模型，可以直接导入</h2>
    <p class="sub">导入即识别、即归一化、即校验，客户不需要先"翻译"一遍。</p>
  </div>
  <div class="split">
    <div>
      <ul class="b">
        <li><b>按腾讯 TSL 规范归一化</b><br><span>属性 / 事件 / 行为映射到标准 TSL，类型、范围、单位、枚举、结构体层级保留</span></li>
        <li><b>自动识别来源</b><br><span>依据腾讯格式的 define 特征判断，不要求操作员先声明</span></li>
        <li><b>标准与兼容格式同一入口</b><br><span>不会导错，也不需要维护两套导入流程</span></li>
      </ul>
    </div>
    <div>
      <div class="panel" style="margin-bottom:14px"><h4>保留</h4><p>数据类型、取值范围、枚举映射、单位、读写模式、事件参数、结构体字段层级。</p></div>
      <div class="card amber"><h4>需显式确认</h4><p>字符串型 min/max 这类源数据元信息，默认按规范丢弃；需要保留时用参数开启，<b>不偷偷改语义</b>。</p></div>
    </div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">18 / 24</span></div>
</section>

<!-- 19 双向转换 -->
<section class="slide" data-note="数值字符串转数字 · stringenum → enum_string · struct.specs → 对象">
  <div class="head">
    <span class="kicker">05 腾讯云 IoT 兼容</span>
    <h2 class="title">双向转换器：迁移不改设备端</h2>
    <p class="sub">既能搬进来，也能导回去——迁移不是单向门。</p>
  </div>
  <table class="cmp" style="margin-bottom:18px">
    <thead><tr><th style="width:150px">转换项</th><th>腾讯 IoT</th><th>平台标准 TSL</th></tr></thead>
    <tbody>
      <tr><td>字段类型</td><td>dataType</td><td class="ok">type</td></tr>
      <tr><td>数值范围</td><td>"0" / "100"（字符串）</td><td class="ok">0 / 100（数值）</td></tr>
      <tr><td>枚举</td><td>stringenum + mapping</td><td class="ok">enum_string，mapping 保留</td></tr>
      <tr><td>结构体</td><td>struct.specs 数组</td><td class="ok">以字段 id 为键的对象</td></tr>
      <tr><td>事件参数</td><td>内嵌 define</td><td class="ok">同步转换为参数定义</td></tr>
    </tbody>
  </table>
  <div class="grid g2">
    <div class="card"><h4>迁移不改设备端协议</h4><p>设备继续按原 MQTT 主题与报文格式上报，平台侧完成格式归一。</p></div>
    <div class="card"><h4>迁移不改上报格式</h4><p>字段名、类型、时间戳口径一致，历史与实时数据语义连续。</p></div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">19 / 24</span></div>
</section>

<!-- 20 演示 E -->
<section class="slide" data-note="导入 / 校验 / 同步已在现网验证 · 设备端协议与上报格式零改动">
  <div class="demo-tag"><i></i>演示 E</div>
  <div class="head">
    <span class="kicker">05 腾讯云 IoT 兼容</span>
    <h2 class="title">导入、校验、同步，全流程跑通</h2>
    <p class="sub">用真实项目的物模型文件演示，比示例文件更有说服力。</p>
  </div>
  <div class="split">
    <div>
      <ol class="steps">
        <li>上传腾讯格式物模型：<b>自动识别并归一化</b></li>
        <li>结构校验 + 业务校验：<b>0 问题</b></li>
        <li>创建产品并同步：<b>配置 / 资产 / 规则链自动生成</b></li>
        <li>用原腾讯格式报文上报：<b>不改字段、正常校验落库</b></li>
      </ol>
    </div>
    <div>
      <div class="panel good"><h4><span class="badge">PROOF</span>第 4 步是全场重点</h4><p>报文截图里字段与腾讯侧一致，平台侧能看到值。<b>这一步走通，"迁移成本"就基本回答了。</b></p></div>
      <div class="done" style="margin-top:14px"><b>已验证</b>导入 / 校验 / 同步三阶段已在现网设备上完整跑过</div>
    </div>
  </div>
  <div class="done-row">
    <div class="done"><b>结论</b>唯一变的是平台，设备端零改动</div>
    <div class="done"><b>兜底</b>环境异常时切离线转换脚本 + 已完成导入的截图</div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">20 / 24</span></div>
</section>

<!-- 21 价值汇总 -->
<section class="slide" data-note="省钱 / 省时 / 省心 · 五条主线均可现场验证">
  <div class="head">
    <span class="kicker">Summary</span>
    <h2 class="title">五条线，一个交付承诺</h2>
    <p class="sub">每一页背后，都对应一个可验证的事实。</p>
  </div>
  <div class="grid g3" style="margin-bottom:20px">
    <div class="card teal"><h4>省钱</h4><p>无许可费，扩容只增算力；十年周期成本结构可预测。</p></div>
    <div class="card teal"><h4>省时</h4><p>建模从天级到小时级；存量迁移不改设备端。</p></div>
    <div class="card teal"><h4>省心</h4><p>源码、数据、部署三层自主，退出路径清晰。</p></div>
  </div>
  <table class="cmp">
    <thead><tr><th style="width:150px">主线</th><th>核心结论</th></tr></thead>
    <tbody>
      <tr><td>信创与可扩展</td><td>TDengine 国产时序库 · 零许可费 · 三层独立扩容 · 单集群 3 万台已验证</td></tr>
      <tr><td>自主可控</td><td>源码全量可控 · 数据全落自有库表 · 私有仓库 + TKE 可整体迁移</td></tr>
      <tr><td>AI 辅助</td><td>建模提速 · 链路排障 · OpenAPI 对话式操作，写入必须人确认</td></tr>
      <tr><td>融合终端</td><td>一台网关聚合多协议 · 单跳直连 · 共用标准物模型</td></tr>
      <tr><td>腾讯云 IoT</td><td>TSL 归一化 · 双向转换 · 现网全流程验证，设备端零改动</td></tr>
    </tbody>
  </table>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">21 / 24</span></div>
</section>

<!-- 22 下一步 -->
<section class="slide" data-note="1 个产品 + 1 台融合网关 + 10–50 台设备 · 2–3 周出 PoC 结论">
  <div class="head">
    <span class="kicker">Next Steps</span>
    <h2 class="title">三个可选动作，从 PoC 开始</h2>
    <p class="sub">不谈框架，谈排期。</p>
  </div>
  <div class="grid g3" style="margin-bottom:24px">
    <div class="card"><h4><span class="no">01</span>小范围 PoC</h4><p>1 个产品 + 1 台融合网关 + 10–50 台设备，跑通接入 → 校验 → 入湖 → 看板，2–3 周出结论。</p></div>
    <div class="card"><h4><span class="no">02</span>迁移评估</h4><p>2–3 个真实腾讯物模型做导入与转换验证，输出字段映射清单与工作量。</p></div>
    <div class="card"><h4><span class="no">03</span>运维共建</h4><p>AI 助手接成一线运维入口，先覆盖 80% 日常查询。</p></div>
  </div>
  <table class="cmp">
    <thead><tr><th style="width:190px">需要贵方提供</th><th>用途</th><th style="width:120px">时间点</th></tr></thead>
    <tbody>
      <tr><td>1 个试点产品 + 设备清单</td><td>确定物模型与接入协议范围</td><td>本周内</td></tr>
      <tr><td>1 台融合网关或现场录屏</td><td>验证多协议接入与子设备建模</td><td>PoC 启动前</td></tr>
      <tr><td>2–3 份腾讯侧物模型</td><td>验证导入、转换与字段映射</td><td>PoC 第一周</td></tr>
    </tbody>
  </table>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">22 / 24</span></div>
</section>

<!-- 23 结束 -->
<section class="slide dark">
  <div class="end">
    <h1>信创打底 · 自主可控<br>能演示 · 能迁移</h1>
    <p class="line">五条主线，一条交付路径</p>
    <div class="grid3">
      <div class="q"><b>01</b><p>零许可费，扩容只增算力</p></div>
      <div class="q"><b>02</b><p>源码 / 数据 / 部署三层自主</p></div>
      <div class="q"><b>03</b><p>AI 辅助，但执行权在人</p></div>
      <div class="q"><b>04</b><p>一块网关接三类协议，不加中转</p></div>
      <div class="q"><b>05</b><p>腾讯物模型直接导入，设备端不改</p></div>
      <div class="q"><b>→</b><p>建议从 2–3 周 PoC 开始</p></div>
    </div>
    <div class="thanks">谢谢，欢迎提问</div>
  </div>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">23 / 24</span></div>
</section>

<!-- 24 附录：一页纸口径 -->
<section class="slide" data-note="容量类数字一律带测试条件 · 未排期功能明确标注「规划中」">
  <div class="head">
    <span class="kicker">Appendix</span>
    <h2 class="title">一页纸口径：事实与待确认</h2>
    <p class="sub">现场被追问时，这一页可以直接投出来。</p>
  </div>
  <div class="split">
    <div class="panel good"><h4><span class="badge">VERIFIED</span>已在系统中可验证</h4><ul><li>TDengine 时序存储、三层分层扩容</li><li>源码可控、私有镜像仓库、自有库表</li><li>网关模式、子设备 Contains 关系</li><li>腾讯格式归一化、双向转换脚本</li><li>AI 读接口直连、写接口待确认</li></ul></div>
    <div class="panel bad"><h4><span class="badge">TBC</span>需现场输入才能定</h4><ul><li>3 万台的压测口径与集群规格</li><li>融合网关型号与协议覆盖清单</li><li>腾讯物模型版本与字段差异</li><li>迁移窗口与历史数据范围</li></ul></div>
  </div>
  <p class="lead" style="margin-top:22px"><b>口径纪律：</b>容量、时长、成本类数字一律带测试条件；未排期功能明确标注"规划中"，不混入现状。</p>
  <div class="foot"><span>中国中铁物联网平台 · 技术汇报</span><span class="bar"><i></i></span><span class="pg">24 / 24</span></div>
</section>

  </div>
</div>

<div class="hint-bar" id="hint"><span><kbd>←</kbd><kbd>→</kbd> 翻页</span><span><kbd>F</kbd> 全屏</span><span><kbd>Home</kbd> 回到首页</span><b>点击任意处隐藏</b></div>

<script>
(function(){
  var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
  var total = slides.length;
  var idx = 0;
  var stage = document.getElementById('stage');
  var hint = document.getElementById('hint');

  // 页码、水印编号与页脚要点条
  var keys = {
    2:'五条主线 · 三个现场演示 · 总时长约 30 分钟',
    3:'零商业许可费 · 单集群 3 万台已验证 · 腾讯迁移设备端零改动',
    4:'TDengine · 一设备一子表 · 无按节点 / 设备 / 核数计费的商业授权',
    5:'接入 / 规则 / 脚本三层解耦 · 扩容动作只有「副本 +N」一种形态',
    6:'30,000 台 / 单集群 · 四类增长对应四种加法 · 均不需改架构',
    7:'内核全量源码 · 私有镜像仓库 · 改得动 / 发得出 / 退得回',
    8:'PostgreSQL + TDengine + Kafka 全部自有 · 可审计 / 可带走',
    9:'私有仓库 + 自有 TKE · 迁移三步：镜像同步 → 清单替换 → 数据演练',
    10:'AI 提建议，平台校验执行 · 只读直连 / 写入确认 / 高危审计',
    11:'草案必须过平台校验才落库 · 校验失败给出逐条定位',
    12:'五段可观测链路 · 非法数据隔离在 iot.invalid，可回放、可追溯',
    13:'接口目录解耦「新增接口」与「新增工具」· 执行权始终在人',
    14:'OPC-UA / S7 / CAN 在网关内收敛 · 对外只有一条 MQTT 连接',
    15:'平台原生网关模式与 v1/gateway/* 主题 · 链路少一跳、运维少一套',
    16:'同一份 TSL · 同一套规则链校验 · 下游不区分接入方式',
    17:'子设备是标准设备对象 · 可检索、可授权、可被规则引用',
    18:'导入即识别、即归一化 · 标准 TSL 与腾讯格式同一入口',
    19:'数值字符串转数字 · stringenum → enum_string · struct.specs → 对象',
    20:'导入 / 校验 / 同步已在现网验证 · 设备端协议与上报格式零改动',
    21:'省钱 / 省时 / 省心 · 五条主线均可现场验证',
    22:'1 个产品 + 1 台融合网关 + 10–50 台设备 · 2–3 周出 PoC 结论',
    24:'容量类数字一律带测试条件 · 未排期功能明确标注「规划中」'
  };

  slides.forEach(function(s, i){
    var pg = s.querySelector('.pg');
    if (pg) pg.textContent = ('0' + (i + 1)).slice(-2) + ' / ' + total;
    var bar = s.querySelector('.foot .bar i');
    if (bar) bar.style.width = ((i + 1) / total * 100) + '%';
    if (!s.classList.contains('dark')) {
      s.setAttribute('data-num', ('0' + (i + 1)).slice(-2));
      if (keys[i + 1]) {
        var kt = document.createElement('div');
        kt.className = 'kt-bar';
        var label = document.createElement('b');
        label.textContent = 'KEY';
        var txt = document.createElement('span');
        txt.textContent = keys[i + 1];
        kt.appendChild(label); kt.appendChild(txt);
        s.appendChild(kt);
      }
    }
  });

  // 自适应缩放
  function fit(){
    var s = Math.min(window.innerWidth / 1280, window.innerHeight / 720) * 0.96;
    stage.style.transform = 'translate(-50%,-50%) scale(' + s + ')';
  }
  window.addEventListener('resize', fit);
  fit();

  function show(n){
    idx = Math.max(0, Math.min(total - 1, n));
    slides.forEach(function(s, i){ s.classList.toggle('on', i === idx); });
    if (hint) hint.classList.add('hide');
    var m = location.hash.match(/^#p(\d+)$/);
    if (!m || +m[1] !== idx + 1) { history.replaceState(null, '', '#p' + (idx + 1)); }
  }

  function go(d){ show(idx + d); }

  document.addEventListener('keydown', function(e){
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); go(1); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); go(-1); }
    else if (e.key === 'Home') { e.preventDefault(); show(0); }
    else if (e.key === 'End') { e.preventDefault(); show(total - 1); }
    else if (e.key === 'f' || e.key === 'F') { e.preventDefault(); toggleFullscreen(); }
    else if (e.key === 'Escape' && document.fullscreenElement) { document.exitFullscreen(); }
  });

  document.addEventListener('click', function(e){
    if (e.target.closest('a')) return;
    go(1);
  });

  function toggleFullscreen(){
    if (!document.fullscreenElement) {
      var el = document.documentElement;
      if (el.requestFullscreen) el.requestFullscreen();
    } else if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }
  if (hint) setTimeout(function(){ hint.classList.add('hide'); }, 6000);

  var m = location.hash.match(/^#p(\d+)$/);
  show(m ? (+m[1] - 1) : 0);
})();
</script>
</body>
</html>
