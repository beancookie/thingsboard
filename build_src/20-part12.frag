<!-- ================= 01 信创与可扩展 ================= -->
<section id="s05">
  <div class="chapter">
    <div class="num">PART 01 / 信创与可扩展</div>
    <h2>信创与可扩展</h2>
    <p class="lede">这一部分只回答两个问题：<b>技术上有没有商业授权风险，以及业务涨上来之后扩容要付多大代价。</b>三页 PPT，五个要点，讲完直接进自主可控。</p>
    <div class="chips">
      <span class="chip"><b>5 分钟</b></span>
      <span class="chip">形式：纯 PPT</span>
      <span class="chip">关键词：TDengine · 分层扩容 · 3 万台</span>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">05</span><span class="ttl">信创选型：国产时序库 TDengine</span><span class="tag">选型</span></div>
    <div class="body">
      <h3 class="pt">时序数据落在国产库上，全栈不背商业许可费</h3>
      <p class="subpt">信创不是换一个 Logo，而是把"授权"这条风险从架构里拿掉。</p>
      <ul class="pts">
        <li><b>时序库选用国产 TDengine</b>，设备与测点数据按"一设备一子表"组织，天然贴合工业时序场景。
          <span>平台侧只负责产生规范化的遥测与事件消息，入湖由数据入湖服务完成，存储层与业务层解耦。</span></li>
        <li><b>全栈无商业许可费用</b>，不引入按节点、按设备、按核数计费的商业授权组件。
          <span>扩容时增加的是服务器资源，而不是一份新的 License 合同——这条在五年、十年的周期里，差的是数量级。</span></li>
        <li><b>规避授权风险</b>，包括许可到期、审计追溯、版本升级被许可条款反向约束这三类常见问题。
          <span>开源组件的运维责任由我方承担，私有镜像仓库保证版本可追溯、可回滚。</span></li>
      </ul>
      <table class="tbl cmp">
        <thead><tr><th style="width:160px">成本项</th><th>商业时序库方案</th><th>本方案（TDengine + 自研平台）</th></tr></thead>
        <tbody>
          <tr><td>软件许可</td><td class="mark bad">按节点 / 设备规模计费，随扩容递增</td><td class="mark">无商业许可费</td></tr>
          <tr><td>扩容边际成本</td><td>算力 + 新增授权</td><td>仅算力与运维人力</td></tr>
          <tr><td>授权审计</td><td>需长期保留授权凭证与用量台账</td><td>无授权审计事项</td></tr>
          <tr><td>版本升级</td><td>受商业版本生命周期约束</td><td>自主发版，私有仓库可回滚</td></tr>
        </tbody>
      </table>
      <p class="hint">建议版式：左侧「TDengine」技术栈卡（国产·开源·时序专用），右侧成本对比表；不要放厂商 Logo 墙，客户更关心成本结构而不是品牌数量。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 40 秒</small></div>
      <div class="say">
        <p>第一页讲选型。时序数据是物联网平台里增长最快、也最容易把成本拖爆的部分。我们的选择是<strong>国产 TDengine</strong>，按"一设备一子表"来组织，这跟工业场景里"设备多、测点多、写入密集、查询按时间窗"的形态是对得上的。</p>
        <p>更关键的是授权结构。这套栈里<strong>没有按节点、按设备、按核数计费的商业授权组件</strong>。这意味着什么？意味着贵方业务翻一倍，增加的是服务器，不是一份新的 License 合同。</p>
        <p>我把话说得更直白一点：商业库的风险不在于贵，而在于<strong>它会在你最需要扩容的时候，变成一张必须谈的合同</strong>。开源方案把这件事变成了纯技术问题——加机器、加副本，运维责任由我方承担。</p>
        <p><span class="beat">预判追问</span> 如果问"开源库出问题谁兜底"：由我方兜底。我们持有内核源码、维护私有镜像仓库，出问题可以改代码、可以回滚版本，这是下一部分"自主可控"要展开的内容。</p>
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">06</span><span class="ttl">微服务架构：按层独立水平扩容</span><span class="tag blue">架构</span></div>
    <div class="body">
      <h3 class="pt">接入、规则、脚本三层解耦，谁先到瓶颈就扩谁</h3>
      <p class="subpt">扩容不是"整机加配"，而是"按层加副本"——这是架构决定的，不是运维技巧。</p>
      <div class="cols c3">
        <div class="cardlet"><h4><span class="ic">L1</span>接入层</h4><p>MQTT 接入与设备会话。设备数增长、连接数增长时优先横向扩这一层，多副本前置负载均衡。</p></div>
        <div class="cardlet"><h4><span class="ic">L2</span>规则引擎</h4><p>按产品生成规则链，负责遥测校验、事件分流与消息外发。计算密集时独立扩，不牵连接入。</p></div>
        <div class="cardlet"><h4><span class="ic">L3</span>脚本引擎</h4><p>规则链内的脚本与计算逻辑。复杂规则、批量加工时单独扩容，避免拖慢主链路。</p></div>
      </div>
      <pre><span class="c"># 数据主链路（与扩容单元一一对应）</span>
设备 ──MQTT──▶ <span class="k">接入层</span> ──▶ 产品配置 ──▶ <span class="k">规则引擎 / 产品规则链</span> ──▶ 遥测存储
                                              │
                                              ├─▶ Kafka: iot.telemetry.normalized
                                              ├─▶ Kafka: iot.event.normalized
                                              └─▶ Kafka: iot.invalid（非法数据隔离）
                                                        │
                                                        ▼
                                              数据入湖服务 ──▶ <span class="k">TDengine</span>（超级表 / 子表）

<span class="c"># 扩容动作</span>
接入层副本 +N  ← 设备连接数上涨
规则引擎副本 +N ← 校验与转发吞吐上涨
脚本引擎副本 +N ← 复杂计算规则增多
<span class="c"># 以上均为水平扩容，不改业务代码、不改数据模型</span></pre>
      <p class="hint">建议版式：横向三泳道架构图，泳道下方标「扩容单元」箭头；把 Kafka 三条主题画出来，能直接支撑"非法数据不污染时序库"的说法。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 50 秒</small></div>
      <div class="say">
        <p>第二页是架构。很多平台说"支持扩容"，实际是整机加 CPU 内存，或者换一台更大的机器——那不叫可扩展，那叫加预算。</p>
        <p>我们的接入层、规则引擎、脚本引擎是<strong>分层解耦</strong>的。设备连接数先到瓶颈，就扩接入层；校验和转发吞吐不够，就扩规则引擎；某个产品的脚本计算特别重，就单独扩脚本引擎。每一层都是无状态副本，前面挂负载均衡，<strong>加副本即可，不改架构、不改代码</strong>。</p>
        <p>还有一条容易被忽略：非法数据是走独立主题隔离的，不写时序库。所以一条脏数据不会把存储层拖垮，也不会污染历史查询。</p>
        <p><span class="beat">预判追问</span> 如果客户看过部署文档，会问"为什么产品与物模型服务是单副本"。要正面回答：那是<strong>数据库迁移顺序</strong>的部署约束，不是架构限制；把迁移拆成独立 Job 之后就能多副本滚动升级。这个我们已经在设计里，不回避。</p>
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">07</span><span class="ttl">3 万台验证与扩容动作</span><span class="tag green">验证</span></div>
    <div class="body">
      <h3 class="pt">单集群已验证 3 万台设备接入，扩容只加副本</h3>
      <p class="subpt">这一页只讲结论：规模不是靠"规划"支撑的，是靠跑过的集群支撑的。</p>
      <div class="cols c2">
        <div class="cardlet"><h4><span class="ic">∞</span>横向</h4><p><b>3 万台设备 / 单集群</b>已跑通接入、校验、存储全链路。数量继续上涨时，加节点、加副本，架构不变。</p></div>
        <div class="cardlet"><h4><span class="ic">↺</span>纵向</h4><p>单副本资源按需上调，用于吸收突发流量；常态扩容仍以水平副本为主，避免单点规格成为天花板。</p></div>
      </div>
      <table class="tbl">
        <thead><tr><th style="width:150px">场景</th><th>现象</th><th>动作</th><th style="width:120px">架构变更</th></tr></thead>
        <tbody>
          <tr><td>设备数翻倍</td><td>接入连接数与会话数上升</td><td>接入层副本 +N，前置 LB 扩容</td><td class="mark">无</td></tr>
          <tr><td>上报频率提高</td><td>规则链校验与转发吞吐吃紧</td><td>规则引擎副本 +N</td><td class="mark">无</td></tr>
          <tr><td>规则复杂度上升</td><td>脚本执行时间变长</td><td>脚本引擎独立扩容</td><td class="mark">无</td></tr>
          <tr><td>历史数据膨胀</td><td>时序查询变慢</td><td>TDengine 增加节点 / 副本，按时间分区</td><td class="mark">无</td></tr>
        </tbody>
      </table>
      <p class="hint">建议版式：左侧一个「3 万」大数字 + 测试口径小字，右侧四行扩容动作表。数字要大，口径要小——这页的说服力来自"敢把条件写出来"。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 30 秒</small></div>
      <div class="say">
        <p>第三页给结论：<strong>单集群已经验证过 3 万台设备接入</strong>。接入、校验、存储整条链路都跑通了，不是只测了连接数。</p>
        <p>更重要的是扩容动作。设备翻倍，扩接入层；上报频率上去，扩规则引擎；规则变复杂，扩脚本引擎；历史数据膨胀，TDengine 加节点、按时间分区。<strong>四种增长，四种加法，没有一种需要改架构。</strong></p>
        <p>这就是"可扩展"这三个字真正的含义——<strong>增长是可以被预算的，而不是要被重新设计的</strong>。</p>
        <p><span class="beat">预判追问</span> 问"3 万台的测试条件是什么"：详细压测报告可以会后提供，包含并发连接、上报频率、消息大小、集群规格。这一页讲的是结论和扩容路径，条件放在报告里，不藏在话术里。</p>
      </div>
    </div>
  </div>
</section>

<!-- ================= 02 自主可控 ================= -->
<section id="s08">
  <div class="chapter">
    <div class="num">PART 02 / 自主可控</div>
    <h2>自主可控</h2>
    <p class="lede">自主可控常被讲成一句口号。我们把它拆成三层可验证的事实：<b>源码在谁手里、数据落在哪里、整套系统能不能搬走。</b>三层都成立，才叫可控。</p>
    <div class="chips">
      <span class="chip"><b>4 分钟</b></span>
      <span class="chip">形式：纯 PPT</span>
      <span class="chip">关键词：源码 · 自有库表 · 私有仓库 · TKE</span>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">08</span><span class="ttl">第一层：源码可控</span><span class="tag">研发</span></div>
    <div class="body">
      <h3 class="pt">内核源码全量可控，功能定制与版本迭代由我方直接发版</h3>
      <p class="subpt">不需要向原厂提需求、等排期、等版本——这条决定了响应速度。</p>
      <ul class="pts">
        <li><b>内核源码全量可控</b>，包括接入、规则链、物模型、前端在内的完整代码基线，不是只拿到二进制或扩展点。
          <span>客户提出的定制需求，走的是"改代码 + 发版"，不是"提工单 + 等原厂"。</span></li>
        <li><b>功能定制与版本迭代由我方直接发版</b>，版本节奏跟随项目，而不是跟随上游社区日历。
          <span>私有镜像仓库保留每个版本的镜像与制品，升级可灰度、可回滚。</span></li>
        <li><b>依赖边界清晰</b>，平台元数据用 PostgreSQL，时序数据用 TDengine，消息用 Kafka，均为可自主部署的开源组件。
          <span>没有"必须连回厂商云"的隐藏依赖，断网环境同样可交付。</span></li>
      </ul>
      <div class="cols c3">
        <div class="cardlet"><h4><span class="ic">1</span>改得动</h4><p>需求进来，能直接改内核，不依赖第三方排期。</p></div>
        <div class="cardlet"><h4><span class="ic">2</span>发得出</h4><p>自有流水线与镜像仓库，版本由项目节奏决定。</p></div>
        <div class="cardlet"><h4><span class="ic">3</span>退得回</h4><p>镜像与数据库迁移都可回滚，升级不是单向门。</p></div>
      </div>
      <p class="hint">建议版式：一条「需求 → 改码 → 构建 → 私有仓库 → 灰度 → 回滚」的横向流程条，三个卡片压在流程下方，强调闭环。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 20 秒</small></div>
      <div class="say">
        <p>自主可控第一层，源码。这句话很空，我把它翻译成三个动作：<strong>改得动、发得出、退得回。</strong></p>
        <p>改得动，是客户提的需求我们能直接改内核，不用写邮件等原厂排期。发得出，是我们有自己的流水线和私有镜像仓库，版本节奏跟项目走。退得回，是升级出问题能回滚镜像、能回滚数据迁移。</p>
        <p>这三件事合起来，才叫"版本控制权在自己手里"。只给二开接口、不给源码的方案，第一件事就做不到。</p>
        <p><span class="beat">预判追问</span> 如果问"你们改的是社区版，上游升级怎么办"：我们维护自己的基线分支，上游安全补丁按需回合，不强制跟随上游大版本。这是自研平台的标准做法，不是临时方案。</p>
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">09</span><span class="ttl">第二层：数据可控</span><span class="tag">数据主权</span></div>
    <div class="body">
      <h3 class="pt">设备、时序、物模型数据全部落在自有集群、自有库表</h3>
      <p class="subpt">没有任何一类业务数据被托管到第三方，也没有"数据换服务"的结构。</p>
      <table class="tbl">
        <thead><tr><th style="width:150px">数据类型</th><th style="width:190px">落库位置</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>设备与凭证</td><td>自有 PostgreSQL</td><td>设备实例、访问令牌、网关与子设备关系</td></tr>
          <tr><td>时序数据</td><td>自有 TDengine</td><td>一设备一子表，按产品建超级表，可自主备份与归档</td></tr>
          <tr><td>物模型 / 产品</td><td>自有 PostgreSQL（<code class="inl">plat_*</code> 表）</td><td>TSL 原文、版本、属性/事件/行为目录、校验和</td></tr>
          <tr><td>规则与脚本</td><td>自有 PostgreSQL + 规则链</td><td>按产品生成的规则链，随版本一起纳管</td></tr>
          <tr><td>消息总线</td><td>自有 Kafka</td><td>三类主题：遥测、事件、非法数据</td></tr>
        </tbody>
      </table>
      <div class="cols c2">
        <div class="cardlet blue"><h4><span class="ic">✓</span>可审计</h4><p>库表、主题、分区都在贵方集群内，DBA 可直接核对，不需要向厂商申请导出。</p></div>
        <div class="cardlet blue"><h4><span class="ic">✓</span>可带走</h4><p>数据模型开放、备份策略自主，迁移不依赖厂商提供"数据导出服务"。</p></div>
      </div>
      <p class="hint">建议版式：一张「数据类型 → 落库位置」矩阵，右侧放两个"可审计 / 可带走"印章式卡片；避免用云图标，容易让人误会为托管。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 15 秒</small></div>
      <div class="say">
        <p>第二层，数据。这一页我想请各位重点看中间这一列——<strong>每一类数据都写清了落在哪张库表、哪个主题里</strong>。</p>
        <p>设备、凭证、物模型在自有 PostgreSQL；时序在自有 TDengine；消息在自有 Kafka。<strong>没有一类业务数据被托管到第三方</strong>，也不存在"用数据换服务"的结构。</p>
        <p>这件事的价值在审计和退出。贵方的 DBA 可以直接连库核对，不需要向我们申请导出；将来如果要换平台，数据模型是开放的，备份是自主的，<strong>不存在"带不走"的问题</strong>。</p>
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="bar"><span class="pg">10</span><span class="ttl">第三层：部署可控</span><span class="tag amber">可迁移</span></div>
    <div class="body">
      <h3 class="pt">私有镜像仓库 + 自有 TKE 集群，可整体迁移至贵方 IDC</h3>
      <p class="subpt">今天的部署形态不是锁定条件，而是一个可平移的起点。</p>
      <div class="cols c2">
        <div class="cardlet"><h4><span class="ic">A</span>现在：自有 TKE 集群</h4><p>平台、物模型、AI 助手、视频网关均以容器方式部署，镜像来自私有仓库，配置与密钥走 ConfigMap / Secret。</p></div>
        <div class="cardlet"><h4><span class="ic">B</span>目标：贵方自有 IDC</h4><p>Kubernetes 清单、镜像、配置整体平移；只需替换仓库地址、存储类与网络出口，不改应用代码。</p></div>
      </div>
      <ul class="pts tight">
        <li><b>镜像可控</b>：所有组件构建后推送私有仓库，现场按 tag 拉取，不依赖公网镜像源。</li>
        <li><b>配置可控</b>：环境差异收敛在 ConfigMap / Secret，迁移时只改配置层。</li>
        <li><b>依赖可控</b>：PostgreSQL、Kafka、TDengine 均为可自建组件，无强制云服务绑定。</li>
        <li><b>路径清晰</b>：迁移分三步——镜像同步、清单替换、数据迁移演练，可先在测试集群验证。</li>
      </ul>
      <p class="hint">建议版式：左右两个环境框 + 中间一条「同一套镜像与清单」的迁移箭头；箭头下方写三个迁移步骤，强化"可操作"而不是"可迁移"。</p>
    </div>
    <div class="note">
      <div class="label">讲稿<small>约 1 分 20 秒</small></div>
      <div class="say">
        <p>第三层，部署。现在这套系统跑在自有 TKE 集群上，镜像来自私有仓库。这句话的重点不是"我们现在在哪"，而是<strong>"它能不能整体搬走"</strong>。</p>
        <p>答案是能。Kubernetes 清单、镜像、配置是分离的，迁移的时候替换仓库地址、存储类和网络出口，<strong>应用代码一行不用改</strong>。PostgreSQL、Kafka、TDengine 都可以在贵方 IDC 自建，没有强制绑定任何云服务。</p>
        <p>我们把迁移拆成了三步：镜像同步、清单替换、数据迁移演练。可以<strong>先在测试集群跑一遍</strong>，验证通过再动生产——迁移这件事，怕的不是工作量大，是没有演练路径。</p>
        <p><span class="beat">收口</span> 三层合起来：源码在手里、数据在库里、系统能搬走。这就是我们对"自主可控"的定义。</p>
      </div>
    </div>
  </div>
</section>
