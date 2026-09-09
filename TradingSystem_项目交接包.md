TradingSystem 完整项目交接包
第1部分：项目基本信息 + 用户最终需求
1. 项目基本信息
1.1 项目名称
TradingSystem
状态：
- 标记：聊天中确认
- GitHub 实际内容：待核对
1.2 项目最终目标
已确认目标
构建一个完整的高频量化交易研究与执行系统：
核心目标：
CME MDP 3.0 MBO (Level 3)

        ↓

Market Data Replay

        ↓

Order Book Reconstruction

        ↓

Microstructure Feature Engine

        ↓

Trading Strategy

        ↓

Risk Management

        ↓

Execution Engine

        ↓

Portfolio / PnL

        ↓

Backtest

        ↓

Paper Trading

        ↓

Live Trading
最终支持：
- ESU6 高频剥头皮
- L3 Order Book 研究
- Tick 级回放
- 策略回测
- 模拟交易
- 实盘接口扩展
- Web DOM 可视化
状态：
- 架构目标：聊天中确认
- 当前完整实现：待核对
1.3 GitHub 仓库地址
用户提供：
https://github.com/panlin520/TradingSystem
以及：
https://github.com/panlin520/TradingSystem.git
状态：
待核对
原因：
当前窗口没有完成 GitHub 仓库内容读取验证。
之前讨论：
- 用户表示其他窗口可以访问 GitHub 插件。
- 当前窗口曾尝试访问。
- 未形成可靠仓库文件读取结果。
因此：
不能写：
GitHub 已同步
只能写：
仓库地址已知，但当前窗口未完成仓库验证。
1.4 本地项目目录
用户环境：
D:\TradingSystem
状态：
已验证。
依据：
用户执行：
(.venv) PS D:\TradingSystem>
以及测试输出：
rootdir: D:\TradingSystem
1.5 开发环境
操作系统
Windows
状态：
已验证。
Python
版本：
Python 3.12.5
状态：
已验证。
测试输出：
platform win32 -- Python 3.12.5
虚拟环境
路径：
D:\TradingSystem\.venv
运行：
D:\TradingSystem\.venv\Scripts\python.exe
状态：
已验证。
1.6 测试框架
使用：
pytest
版本：
pytest-9.1.1
状态：
已验证。
1.7 主要依赖
已确认使用
Databento
用途：
读取：
DBN
DBN.zst
MBO 数据。
相关：
databento.common.dbnstore.DBNStore
状态：
聊天中确认 + 测试验证。
pytest
用途：
运行系统契约测试。
状态：
已验证。
PyQt
用途：
未来 DOM 可视化。
状态：
聊天中确认。
未完成。
C++
用途：
未来性能优化。
状态：
聊天中确认。
未实现。
1.8 运行方式
当前：
测试：
python -m pytest tests/test_full_runtime_engine.py -v -s
以及：
python -m pytest tests/test_execution_runtime_contract.py -v -s
状态：
已验证。
未来目标：
统一入口：
main.py
根据模式：
BACKTEST

PAPER

LIVE
运行。
状态：
聊天中确认。
2. 用户最终需求
2.1 最初核心需求
需求1：ESU6 高频剥头皮系统
原始方向：
用户希望：
使用量化高频交易在 ESU6 中进行剥头皮。

需要：
- L3 数据
- Tick 数据
- Order Book
- Trade Flow
- 微观结构指标
状态：
聊天中确认。
2.2 L3 MBO 数据需求
用户确认：
需要：
CME MDP 3.0 MBO
不是：
L1
L2
原因：
需要：
- Queue Position
- Order Add
- Modify
- Cancel
- Trade
- Liquidity变化
状态：
聊天中确认。
2.3 数据格式要求
用户指定：
Databento MBO schema：
字段：
ts_recv

ts_event

rtype

publisher_id

instrument_id

action

side

price

size

channel_id

order_id

flags

ts_in_delta

sequence

symbol
Action：
A

M

C

R

T

F

N
状态：
聊天中确认。
2.4 系统必须模块化
用户明确要求：
不要：
所有代码放一个文件
不要：
全部塞一个文件夹
要求：
模块分离。
状态：
聊天中确认。
2.5 必须支持三种运行状态
最终确认：
必须区分：
BACKTEST

PAPER

LIVE
原因：
避免：
- 回测代码污染实盘
- 模拟代码污染真实交易
状态：
聊天中确认。
2.6 数据添加方式要求
用户要求：
不能：
添加一个CSV
然后手动运行多个程序
希望：
统一系统入口。
目标：
main.py

选择模式

加载数据

运行系统
状态：
聊天中确认。
2.7 策略系统要求
用户要求：
添加策略不能修改核心系统。
需要：
插件设计。
目标：
类似：
strategy/
    base.py
    xxx_strategy.py
状态：
聊天中确认。
2.8 可视化要求
最终需求：
Web 用户可视化和交互。
包括：
DOM：
左：
Depth Of Market
右：
Time & Sales
颜色：
Bid：
蓝色
Ask：
红色
成交：
主动买：
红色背景
主动卖：
蓝色背景
中间：
Last Price 白线。
必须：
增量刷新。
禁止：
全量刷新。
状态：
聊天中确认。
未实现。
2.9 代码输出要求
用户多次确认：
代码修改：
必须：
完整文件
不要：
代码片段
状态：
聊天中确认。
2.10 注释要求
要求：
详细注释。
包括：
中文解释。
状态：
聊天中确认。
2.11 Python + C++要求
用户询问：
Python+C 是否可行。
最后确认：
采用：
Python + C++
原因：
性能：
- OrderBook
- Replay
- Feature
状态：
聊天中确认。
3. 明确禁止或取消方案
禁止1：
单文件交易系统
例如：
main.py
里面全部逻辑
原因：
无法维护。
状态：
聊天中确认。
禁止2：
Fake 行情作为核心测试
禁止：
随机：
price
volume
orderbook
测试。
必须：
真实：
Databento MBO
状态：
聊天中确认。
禁止3：
DOM 全量刷新
禁止：
setRowCount()
或者：
每次重建整个表。
要求：
只更新变化单元格。
状态：
聊天中确认。
禁止4：
策略写死在 Engine
禁止：
if strategy == xxx
要求：
插件。
状态：
聊天中确认。
禁止5：
Python+C
最终选择：
Python+C++
状态：
聊天中确认。
（第1部分结束）
回复：
继续
继续输出：
第2部分：系统架构 + 目录结构 + 数据流 + 技术选择




  来源





继续输出













TradingSystem 完整项目交接包
第2部分：系统架构 + 目录结构 + 数据流 + 技术选择
4. 已确认系统架构
4.1 总体架构
状态：
- 架构设计：聊天中确认
- GitHub 实际代码结构：待核对
最终设计：
TradingSystem

│
├── Data Layer
│
│   Databento MBO
│
│
├── Replay Engine
│
│
├── Market State
│
│
├── OrderBook Reconstruction
│
│
├── Feature Engine
│
│
├── Strategy Layer
│
│
├── Risk Layer
│
│
├── Execution Layer
│
│
├── Portfolio Layer
│
│
├── Reporting
│
│
└── Visualization
5. 核心交易数据流
5.1 当前已经跑通的数据路径
已验证：
Real Databento MBO

        ↓

DatabentoFeed

        ↓

TradingEngine

        ↓

OrderBookBuilder

        ↓

Strategy

        ↓

RiskManagerV2

        ↓

Order

        ↓

ExecutionEngine

        ↓

Fill

        ↓

Portfolio
状态：
已验证。
依据：
测试：
python -m pytest tests/test_full_runtime_engine.py -v -s
结果：
5 passed
6. Engine 生命周期设计
6.1 TradingEngine
核心：
TradingEngine
文件：
core/engine.py
状态：
聊天中确认 + 测试验证。
生命周期：
initialize

↓

start

↓

run

↓

process event

↓

stop
事件处理：
on_event(event)
负责：
1. Clock Update

2. State Update

3. OrderBook Update

4. Event Counter

5. F_LAST判断

6. Strategy

7. Risk

8. Execution

9. Portfolio
7. MBO 数据处理原则
7.1 不允许重新排序
确认规则：
必须保持：
Databento sequence
顺序。
原因：
MBO 是事件流。
不能：
sort(price)
sort(time)
重新排列。
状态：
聊天中确认。
7.2 OrderBook 重建原则
必须：
订单级：
order_id
维护。
不是：
只维护：
price -> volume
结构：
Order

↓

Price Level

↓

OrderBook
同价：
FIFO：
First In First Out
状态：
聊天中确认。
8. 模块职责设计
8.1 Data Layer
职责：
读取市场数据。
不负责：
- 策略
- 交易
- 风控
输入：
DBN

DBN.zst

CSV
输出：
MarketEvent
8.2 Core Layer
目录：
core/
职责：
系统核心。
包括：
event

clock

state

engine
8.3 OrderBook Layer
目录：
orderbook/
职责：
L3盘口重建。
负责：
Add

Modify

Cancel

Reset

Trade

Fill
不负责：
- 策略
- 下单
8.4 Strategy Layer
目录：
strategy/
职责：
产生交易信号。
输入：
Market State

Feature

OrderBook
输出：
Signal
禁止：
策略直接修改：
Portfolio

OrderBook

Execution
8.5 Risk Layer
目录：
risk/
职责：
交易前检查。
例如：
position limit

max loss

exposure

kill switch
不负责：
产生策略。
8.6 Execution Layer
目录：
execution/
职责：
订单执行。
流程：
Order

↓

ExecutionEngine

↓

Fill
支持：
BACKTEST

PAPER

LIVE
8.7 Portfolio Layer
目录：
portfolio/
职责：
账户状态。
管理：
Position

PnL

Equity

Trade History
原则：
所有仓位变化来自：
Fill
不是：
Order
9. 已确认目录结构
注意：
以下为：
“设计目标结构”
不是 GitHub 已验证结构。
状态：
聊天中确认。
D:\TradingSystem

│
├── main.py
│
├── config/
│
├── core/
│   ├── __init__.py
│   ├── event.py
│   ├── clock.py
│   ├── state.py
│   └── engine.py
│
│
├── data/
│   ├── databento_feed.py
│   ├── csv_feed.py
│   └── ESU6_2026-06-15_MBO.dbn.zst
│
│
├── order/
│   └── order.py
│
│
├── orderbook/
│   ├── order.py
│   ├── level.py
│   ├── book.py
│   └── builder.py
│
│
├── feature/
│   └── feature_engine.py
│
│
├── strategy/
│   ├── base.py
│   ├── registry.py
│   └── strategies/
│
│
├── risk/
│   ├── limits.py
│   ├── exposure.py
│   ├── kill_switch.py
│   └── risk_manager.py
│
│
├── execution/
│   ├── execution_engine.py
│   ├── fill.py
│   └── broker.py
│
│
├── portfolio/
│   ├── position.py
│   ├── pnl.py
│   ├── portfolio.py
│   └── account.py
│
│
├── tests/
│
└── visualization/
    └── web_dom/
10. 技术选择
10.1 Python
用途：
系统控制层。
负责：
- Engine
- Strategy
- Risk
- Portfolio
- 测试
原因：
开发效率高。
状态：
聊天中确认。
10.2 C++
用途：
性能核心。
计划：
未来替换：
OrderBook

Feature Calculation

Replay Hot Path
架构：
Python

   ↓

C++ Extension

   ↓

High Performance Core
原因：
ES MBO 数据量巨大。
Python 单线程可能成为瓶颈。
状态：
聊天中确认。
未实现。
10.3 为什么不是 Python + C
用户曾询问：
Python+C 是否可以。
最终决定：
Python+C++。
原因：
- 更成熟生态
- 面向对象能力更强
- 更适合大型交易系统
状态：
聊天中确认。
11. 三种运行模式设计
确认：
必须支持：
BACKTEST
用途：
历史数据回放。
数据：
Databento DBN
PAPER
用途：
模拟交易。
数据：
实时行情。
执行：
模拟成交。
LIVE
用途：
真实交易。
连接：
Broker
三、已经确认的运行模式设计（补充）
系统必须明确区分三种运行状态：
BACKTEST
PAPER
LIVE
三个模式共用同一套核心交易逻辑：
Market Data
      |
      v
TradingEngine
      |
      v
Strategy
      |
      v
RiskManager
      |
      v
Order
      |
      v
Execution
      |
      v
Portfolio
区别只在：
- 数据来源
- 成交方式
- 资金环境
- 外部连接
1. BACKTEST 模式
用途
历史数据回测。
目标：
验证：
- 策略逻辑
- 信号质量
- 风险控制
- 执行模型
- PnL结果
数据
来源：
历史 MBO 数据。
例如：
Databento
    |
    |
ESU6_2026-06-15_MBO.dbn.zst
流程：
DBN File
    |
    v
DatabentoFeed
    |
    v
MarketEvent
    |
    v
TradingEngine
执行
模拟成交。
例如：
Market Order:
BUY ESU6 1
ExecutionEngine:
last_price = 6000.00
生成：
Fill
{
 symbol: ESU6
 side: BUY
 quantity:1
 price:6000.00
}
然后：
Fill
 |
 v
Portfolio.on_fill()
 |
 v
Position
 |
 v
PnL
不连接
BACKTEST 不连接：
- Broker
- Exchange
- Real Account
2. PAPER 模式
用途
模拟交易。
目的：
在真实行情环境验证：
- 策略
- 风控
- 下单逻辑
- 执行速度
- 系统稳定性
数据
实时行情。
例如：
CME Market Data
        |
        v
Market Data Feed
        |
        v
TradingEngine
区别：
BACKTEST:
历史行情
PAPER:
实时行情
执行
模拟成交。
不会发送真实订单。
流程：
Strategy
    |
    v
Signal
    |
    v
Risk
    |
    v
Order
    |
    v
Paper Execution Engine
    |
    v
Simulated Fill
    |
    v
Portfolio
例如：
策略：
BUY ESU6 1
Paper Execution:
根据：
- Bid
- Ask
- Last
- Spread
- Queue Position
- Latency
模拟：
Fill price
生成：
Paper Fill
PAPER 不连接
不连接：
Broker
Exchange Account
Real Money
3. LIVE 模式
用途
真实交易。
数据
实时行情。
来源：
Exchange
   |
   v
Broker Data API
   |
   v
Live Market Feed
执行
真实成交。
流程：
Strategy
      |
      v
Signal
      |
      v
RiskManager
      |
      v
Order
      |
      v
Live Execution Engine
      |
      v
Broker API
      |
      v
Exchange
      |
      v
Real Fill
      |
      v
Portfolio
LIVE 连接
连接：
Broker
例如：
未来：
Interactive Brokers
CQG
Rithmic
Tradovate
CME Direct
（具体 Broker 待选择）
三种模式核心区别
项目	BACKTEST	PAPER	LIVE
数据	历史MBO	实时行情	实时行情
账户	虚拟	虚拟	真实
Order	模拟	模拟	真实
Fill	回放模型	模拟撮合	Broker返回
Broker	❌	❌	✅
Exchange	❌	❌	✅
风险模块	✅	✅	✅
Strategy	同一套	同一套	同一套
Portfolio	模拟	模拟	实盘同步


四、代码架构要求
不能：
strategy_backtest.py
strategy_live.py
这种复制方式。
必须：
同一个 Strategy：
strategy/
    base.py
    mean_reversion.py
    scalper.py
运行模式控制：
EngineMode
例如：
class EngineMode(Enum):

    BACKTEST = "BACKTEST"

    PAPER = "PAPER"

    LIVE = "LIVE"
Execution 层设计
必须分离：
execution/

    base.py

    backtest_execution.py

    paper_execution.py

    live_execution.py
接口统一：
class ExecutionEngine:

    def submit(order):

        pass
不同实现：
BACKTEST:
Historical Fill Model
PAPER:
Simulation Fill Model
LIVE:
Broker API
Portfolio 层设计
保持统一：
Fill
 |
 v
Portfolio
 |
 v
Position
 |
 v
PnL
区别：
BACKTEST:
模拟资金
PAPER:
模拟账户
LIVE:
Broker Account Sync
当前确认结论
状态：
✅ 已确认：
- 三模式架构
- Strategy 不区分模式
- Execution 根据模式切换
- Portfolio 接收 Fill
- LIVE 才连接 Broker
待实现：
1. core/mode.py
统一管理：
BACKTEST
PAPER
LIVE
2. execution/base.py
统一接口。
3. execution/paper_execution.py
模拟成交。
4. execution/live_execution.py
Broker接口。
5. broker/
未来：
broker/
    ibkr.py
    rithmic.py
    cqg.py
下一步应继续补充：
“数据层设计：BACKTEST/PAPER/LIVE 三种 Feed 如何统一接口”。




  来源





继续













五、数据层设计：BACKTEST / PAPER / LIVE 三种 Feed 统一接口
状态：
聊天中确认
目标：
无论运行：
- BACKTEST
- PAPER
- LIVE
上层：
TradingEngine
Strategy
RiskManager
Execution
Portfolio
都不能感知数据来源区别。
数据层负责隐藏差异。
1. 核心原则
禁止：
if mode == BACKTEST:
    read_csv()

elif mode == PAPER:
    connect_market()

elif mode == LIVE:
    connect_broker()
写在：
- Strategy
- TradingEngine
- RiskManager
内部。
原因：
后期维护困难。
必须：
统一 Feed 接口：
MarketFeed
      |
      |
 -------------------------
 |           |            |
 v           v            v

HistoricalFeed
RealtimePaperFeed
LiveFeed
2. 数据流架构
BACKTEST
00_data
   |
   |
DBN / CSV
   |
   v
HistoricalFeed
   |
   v
MarketEvent
   |
   v
TradingEngine
例如：
当前：
data/
 |
 └── ESU6_2026-06-15_MBO.dbn.zst
使用：
DatabentoFeed
产生：
MarketEvent
PAPER
CME Market Data
        |
        v
RealtimeFeed
        |
        v
MarketEvent
        |
        v
TradingEngine
区别：
不是历史时间。
而是：
实时事件。
例如：
ts_event = now
LIVE
Exchange
    |
    v
Broker Market API
    |
    v
LiveFeed
    |
    v
MarketEvent
    |
    v
TradingEngine
3. 统一 MarketFeed 接口
建议新建：
data/
    base.py
职责：
定义所有行情源必须实现的接口。
接口：
from abc import ABC, abstractmethod


class MarketFeed(ABC):


    @abstractmethod
    def __iter__(self):
        pass



    @abstractmethod
    def start(self):
        pass



    @abstractmethod
    def stop(self):
        pass
上层只知道：
for event in feed:

    engine.on_event(event)
不知道：
- 文件
- Socket
- Broker
4. BACKTEST Feed
当前已有：
data/databento_feed.py
作用：
读取：
.dbn.zst
转换：
Databento Record
        |
        v
MarketEvent
当前状态：
✅ 已验证
测试：
tests/test_full_runtime_engine.py
结果：
FULL RUNTIME REAL FEED

events: 20000

F_LAST: 13566

PASSED
需要调整：
建议：
继承：
MarketFeed
变成：
class DatabentoFeed(MarketFeed):
5. PAPER Feed
未来新增：
data/paper_feed.py
用途：
实时行情模拟。
例如：
连接：
CME Data
或者：
Databento Live API
输出：
一样：
MarketEvent
结构：
class PaperFeed(MarketFeed):


    def __iter__(self):

        while self.running:

            event = self.receive()

            yield event
6. LIVE Feed
未来：
data/live_feed.py
用途：
实盘行情。
来源：
可能：
Rithmic
CQG
IBKR
CME
统一输出：
MarketEvent
例如：
Broker返回：
{
"symbol":"ESU6",
"price":6000.25,
"size":5
}
转换：
MarketEvent(
    symbol="ESU6",
    price=6000.25,
    size=5
)
7. MarketEvent 统一
当前：
core/event.py
职责：
所有行情最终转换成：
MarketEvent
字段：
当前确认：
ts_event

ts_recv

sequence

action

side

price

size

symbol

order_id

flags
来源不同：
不会改变：
MarketEvent
8. 数据目录设计
最终建议：
TradingSystem

│
├── 00_data
│
│   ├── historical
│   │
│   │    └── ESU6_2026-06-15_MBO.dbn.zst
│   │
│   │
│   ├── live
│   │
│   └── cache
│


├── data
│
│   ├── base.py
│   │
│   ├── databento_feed.py
│   │
│   ├── paper_feed.py
│   │
│   └── live_feed.py
9. TradingEngine 调用关系
最终：
main.py


选择模式


EngineMode.BACKTEST


        |
        v


DataFactory


        |
        v


DatabentoFeed



======================



EngineMode.PAPER


        |
        v


DataFactory


        |
        v


PaperFeed



======================



EngineMode.LIVE


        |
        v


DataFactory


        |
        v


LiveFeed

10. 建议新增 DataFactory
新文件：
data/factory.py
作用：
根据模式自动创建 Feed。
例如：
class FeedFactory:


    @staticmethod
    def create(mode):


        if mode == EngineMode.BACKTEST:

            return DatabentoFeed(
                file_path="..."
            )


        elif mode == EngineMode.PAPER:

            return PaperFeed()


        elif mode == EngineMode.LIVE:

            return LiveFeed()
11. 当前状态总结
已完成
✅ DatabentoFeed
✅ DBN MBO读取
✅ MarketEvent生成
✅ TradingEngine接收
已验证
Real MBO
 |
DatabentoFeed
 |
TradingEngine
 |
OrderBookBuilder
 |
Strategy
 |
Risk
 |
Execution
 |
Portfolio
测试：
test_full_runtime_engine.py

5 passed
12. 尚未完成
优先级 P0
新建：
data/base.py
完成：
统一 Feed Interface。
修改：
data/databento_feed.py
改：
class DatabentoFeed(MarketFeed)
优先级 P1
新增：
data/factory.py
完成：
模式自动选择 Feed。
优先级 P2
新增：
data/paper_feed.py

data/live_feed.py
下一部分继续：
“Execution 层最终设计：BacktestExecution / PaperExecution / LiveExecution，以及 Broker 接入方式”




  来源





继续













六、Execution 执行层最终设计
状态：
- 三模式隔离：聊天中确认
- ExecutionEngine 当前部分实现：已验证
- Paper / Live Execution 尚未实现：待完成
1. Execution 层设计目标
核心原则：
Strategy 不关心订单如何成交。

Strategy 只负责：
Market Data
      |
      v
Signal
      |
      v
Order Intent
Execution 负责：
Order
   |
   v
成交
   |
   v
Fill
最终结构：
execution/

├── base.py

├── backtest_execution.py

├── paper_execution.py

├── live_execution.py

├── execution_engine.py

└── models.py
2. 当前已有文件
execution/execution_engine.py
状态：
✅ 已存在
✅ 已测试
当前职责：
统一执行入口。
核心类：
ExecutionEngine
当前接口：
submit(
    order,
    market_price
)
流程：
Order
 |
 v
ExecutionEngine.submit()
 |
 v
execute()
 |
 v
Fill
当前支持：
ExecutionMode.BACKTEST
测试：
文件：
tests/test_execution_runtime_contract.py
结果：
13 passed
验证：
Order
 |
ExecutionEngine
 |
Fill
 |
Portfolio Callback
3. Order 与 Fill 职责分离
这是当前重要修改方向。
原设计问题
之前：
Order
    |
    保存成交价格
例如：
Order.average_fill_price
存在问题。
原因：
Order 是交易意图。
成交属于 Execution。
最终确定：
Order 不保存成交价格
Order:
负责：
- symbol
- side
- quantity
- order_id
- status
例如：
Order(
    symbol="ESU6",
    side=BUY,
    quantity=1
)
Fill:
负责：
- 成交价格
- 成交数量
- 成交时间
例如：
Fill(
    symbol="ESU6",
    side=BUY,
    quantity=1,
    price=6000.25
)
数据关系：
Strategy

   |
   v

Order
(没有价格)


   |
   v

Execution


   |
   v

Fill
(有价格)


   |
   v

Portfolio
4. BACKTEST Execution
文件：
execution/backtest_execution.py
状态：
待创建。
职责：
历史回测成交模拟。
输入：
Order
市场状态：
MarketState
输出：
Fill
例如：
Order:
BUY ESU6 1
市场：
last_price=6000
生成：
Fill(
    price=6000
)
未来可以加入：
简单模型
Last Price Fill
高级模型
用于 ES MBO：
Bid Ask
Spread
Queue Position
Latency
Liquidity
5. PAPER Execution
文件：
execution/paper_execution.py
状态：
待创建。
用途：
模拟实盘。
数据：
实时行情。
流程：
Real Market Data

       |

       v

Paper Execution

       |

       v

Simulated Fill

       |

       v

Portfolio
区别 BACKTEST：
BACKTEST:
历史事件
+
立即成交
PAPER:
实时事件
+
模拟撮合
需要考虑：
延迟
例如：
latency_ms=50
滑点
例如：
slippage_ticks=1
深度
例如：
买：
Bid:
6000.00 100
5999.75 200
卖：
Ask:
6000.25 50
模拟：
是否可以成交。
6. LIVE Execution
文件：
execution/live_execution.py
状态：
待创建。
职责：
真实交易。
流程：
Order

 |

 v

LiveExecution

 |

 v

Broker API

 |

 v

Exchange

 |

 v

Broker Fill

 |

 v

Portfolio
LIVE 不自己生成 Fill。
而是：
Broker 返回：
{
 "order_id":"xxx",
 "status":"filled",
 "price":6000.25,
 "quantity":1
}
转换：
Fill()
7. Broker 层设计
新增：
broker/
结构：
broker/

├── base.py

├── ibkr.py

├── rithmic.py

├── cqg.py

└── tradovate.py
统一接口：
class Broker:

    def submit_order(self, order):
        pass


    def cancel_order(self, order_id):
        pass


    def get_position(self):
        pass
LIVE:
LiveExecution

       |

       v

Broker Interface

       |

       v

具体Broker
8. ExecutionFactory
建议新增：
execution/factory.py
职责：
根据模式创建执行器。
例如：
class ExecutionFactory:


    @staticmethod
    def create(mode):


        if mode == BACKTEST:

            return BacktestExecution()


        elif mode == PAPER:

            return PaperExecution()


        elif mode == LIVE:

            return LiveExecution()
9. TradingEngine 最终调用关系
当前：
TradingEngine

    |
    |
    +---- Strategy

    |
    |
    +---- RiskManager

    |
    |
    +---- ExecutionEngine

    |
    |
    +---- Portfolio
最终：
TradingEngine

       |

       v

Strategy


       |

       v


Signal


       |

       v


RiskManager


       |

       v


Order


       |

       v


ExecutionFactory


       |

       +----------------+
       |                |
       v                v

Backtest          Paper          Live
Execution        Execution      Execution


       |

       v


Fill


       |

       v


Portfolio
10. 当前 Execution 已验证内容
测试一
文件：
tests/test_execution_runtime_contract.py
结果：
13 passed
覆盖：
Order initial state

Order submit

Order accept

Order fill

Execution submit

Market execution

Limit execution

Cancel

Snapshot

Statistics

Reset
测试二
文件：
tests/test_trading_pipeline.py
结果：
1 passed
验证：
Signal

↓

Risk

↓

Order

↓

Execution

↓

Fill

↓

Portfolio
测试三
文件：
tests/test_full_runtime_engine.py
结果：
5 passed
验证：
Real MBO

↓

DatabentoFeed

↓

TradingEngine

↓

OrderBook

↓

Strategy

↓

Risk

↓

Execution

↓

Portfolio
11. 当前未完成 Execution 任务
P0
修改：
execution/execution_engine.py
目标：
进一步拆分：
目前：
ExecutionEngine
承担：
- 模式判断
- 成交逻辑
- Broker预留
建议：
拆：
ExecutionEngine

+

ExecutionHandler
P1
新增：
execution/base.py
定义：
class BaseExecution:
    
    submit(order):
        pass
P2
新增：
execution/backtest_execution.py
迁移：
当前 BACKTEST 成交逻辑。
P3
新增：
execution/paper_execution.py
P4
新增：
execution/live_execution.py
12. 禁止重新设计事项
新窗口必须避免：
❌ Strategy 自己生成 Fill
❌ Order 保存成交价格
❌ Portfolio 直接调用 Execution
❌ LIVE / BACKTEST 写两套 Strategy
❌ 每个模式复制一套系统
下一部分继续：
“Portfolio / Position / PnL / Account 最终设计，以及当前已有代码状态”




  





继续













七、Portfolio / Position / PnL / Account 最终设计
状态：
- Portfolio 架构：聊天中确认
- Position / PnL 基础实现：已完成（根据当前窗口历史记录）
- Account 模块：曾出现语法错误，已修正方向
- LIVE Account Sync：未实现
1. Portfolio 层设计目标
核心原则：
所有仓位变化必须来自 Fill。

禁止：
Strategy
    |
    v
直接修改 Position
禁止：
Risk
    |
    v
直接修改 Portfolio
正确：
Order

 |

 v

Execution

 |

 v

Fill

 |

 v

Portfolio

 |

 v

Position

 |

 v

PnL
2. Portfolio 职责
文件：
portfolio/portfolio.py
职责：
负责：
- Position 管理
- Fill 管理
- Realized PnL
- Unrealized PnL
- Equity 状态
- 成交统计
- 市场价格状态
不负责：
- Order
- Execution
- Strategy
- Market Data
- Risk
3. 当前 Portfolio 结构
portfolio/

├── position.py

├── pnl.py

├── portfolio.py

└── account.py
4. portfolio/position.py
状态：
✅ 已实现
职责：
管理单个品种仓位。
核心类：
Position
方向：
PositionSide
当前：
FLAT

LONG

SHORT
Position 数据
例如：
Position(
    symbol="ESU6",
    quantity=1,
    avg_price=6000
)
5. Position 更新逻辑
所有变化来自：
Position.update()
接口：
update(
    side,
    quantity,
    price
)
支持：
开仓
例如：
BUY ES 1
结果：
FLAT

↓

LONG 1
加仓
LONG 1

+

BUY 1

=

LONG 2
减仓
LONG 2

SELL 1

=

LONG 1
平仓
LONG 1

SELL 1

=

FLAT
反手
例如：
LONG 1

SELL 2

=

SHORT 1
返回：
{
"realized_quantity":,

"entry_price":,

"exit_price":,

"action":
}
动作：
REDUCE_LONG

CLOSE_LONG

REVERSE_TO_SHORT


REDUCE_SHORT

CLOSE_SHORT

REVERSE_TO_LONG
6. portfolio/pnl.py
状态：
✅ 已实现
核心类：
PnL
职责：
计算：
Realized PnL
已实现盈亏。
Unrealized PnL
浮动盈亏。
Equity
账户权益。
7. ES 合约计算
默认：
point_value=50
ES:
1 point = $50
例如：
多单：
BUY ES

6000

SELL

6002
盈利：
2 points

×

50

=

$100
支持：
多品种：
point_values={
    "ES":50,
    "MES":5,
    "NQ":20,
    "MNQ":2
}
8. PnL 接口
更新已实现
update_realized(
    side,
    entry_price,
    exit_price,
    quantity,
    symbol
)
更新浮动
update_position(
    position,
    market_price,
    symbol
)
9. portfolio/portfolio.py
状态：
✅ 已实现基础版本
核心类：
Portfolio
初始化：
Portfolio(
    initial_capital=100000
)
内部：
self.positions={}

self.pnl=PnL()

self.fills=[]

self.market_prices={}
10. Fill 接入
核心接口：
on_fill(fill)
流程：
Fill

 |

 v

Portfolio.on_fill()

 |

 v

Position.update()

 |

 v

PnL.update_realized()

执行：
portfolio.on_fill(
    fill
)
返回：
Position
11. 市场价格更新
接口：
update_market_price(
    symbol,
    price
)
用途：
计算：
Unrealized PnL
批量：
update_market_prices(
    prices
)
全部更新：
update_all_positions()
12. Equity
公式：
Equity

=

Initial Capital

+

Realized PnL

+

Unrealized PnL
注意：
当前：
不包含：
- Commission
- Fee
- Exchange Cost
13. portfolio/account.py
状态：
⚠️ 曾修改
问题：
出现：
SyntaxError
错误：
def is solvent(self) -> bool:
原因：
函数名存在空格。
正确：
def is_solvent(self) -> bool:
当前用途：
账户状态管理。
未来职责：
负责：
- Capital
- Margin
- Buying Power
- Risk Limits
- Broker Account Sync
14. Portfolio 与 LIVE
未来 LIVE：
当前：
Broker

 |

 v

Portfolio
不建议。
应该：
Broker

 |

 v

Account Sync


 |

 v

Portfolio
原因：
Broker Account:
包含：
- Cash
- Margin
- Position
- Orders
Portfolio:
负责：
策略内部状态。
15. 三模式下 Portfolio
BACKTEST
模拟资金

模拟仓位

模拟PnL
PAPER
模拟资金

实时行情

模拟成交
LIVE
Broker Account

真实Position

真实PnL
16. 当前验证链路
已通过：
Real MBO

↓

DatabentoFeed

↓

TradingEngine

↓

Strategy

↓

Risk

↓

Execution

↓

Fill

↓

Portfolio
测试：
tests/test_full_runtime_engine.py
结果：
5 passed
17. 当前 Portfolio 风险点
风险1
Fill 数据模型需要统一。
需要确认：
execution.Fill

↓

portfolio.on_fill()
字段一致：
symbol

side

quantity

price

order_id
风险2
LIVE 模式账户同步。
未完成。
风险3
手续费。
未来增加：
commission.py
例如：
ES:
exchange fee

broker fee
18. 禁止重新设计
新窗口不要：
❌ Strategy 直接修改 Position
❌ Execution 直接修改 PnL
❌ Portfolio 生成 Order
❌ PnL 保存交易逻辑
❌ Position 保存订单状态
19. 下一阶段任务
优先级：
P0
完善：
portfolio/account.py
完成：
- AccountState
- Balance
- Margin
- Buying Power
P1
增加：
portfolio/fill.py
统一 Fill 数据结构。
P2
增加：
portfolio/commission.py
手续费模型。
P3
LIVE Account Sync：
broker/

↓

account sync

↓

portfolio
下一部分继续：
“Risk 风控系统最终设计：limits.py / exposure.py / kill_switch.py / risk_manager.py 当前状态与后续规划”




  来源





继续













八、Risk 风控系统最终设计
状态：
- Risk 模块拆分方向：聊天中确认
- RiskManagerV2 基础接口：已存在（根据测试记录）
- limits / exposure / kill_switch 独立模块：建议实现，尚未确认完成
- LIVE 风控增强：未实现
1. Risk 层设计目标
核心原则：
所有 Signal 必须经过 Risk 检查后才能生成 Order。

禁止：
Strategy

   |

   v

Order
正确：
Strategy

   |

   v

Signal

   |

   v

RiskManager

   |

   +------------+

   |            |

 PASS        REJECT

   |            |

   v            v

Order       Ignore
2. Risk 模块职责
Risk 不负责：
- 生成交易信号
- 创建 Order
- 执行成交
- 修改 Position
Risk 负责：
- 是否允许交易
- 风险限制检查
- 仓位限制
- 资金限制
- 紧急停止
3. 当前 Risk 架构目标
最终目录：
risk/

├── limits.py

├── exposure.py

├── kill_switch.py

├── risk_manager.py

└── models.py
4. risk/models.py
状态：
建议新增。
用途：
统一 Risk 返回结果。
例如：
class RiskDecision:

    approved: bool

    reason: str

    risk_name: str
返回：
允许：
RiskDecision(
    approved=True,
    reason="OK"
)
拒绝：
RiskDecision(
    approved=False,
    reason="MAX_POSITION_EXCEEDED"
)
5. RiskManagerV2
状态：
✅ 已存在
已通过：
tests/test_full_runtime_engine.py
验证：
真实链路：
MBO

↓

Strategy

↓

RiskManagerV2

↓

Execution
当前接口：
信号检查
check_signals(
    signal,
    portfolio
)
作用：
检查：
- Signal 是否允许执行
- 当前 Portfolio 是否满足条件
测试中：
decision = risk_manager.check_signals(
    signal,
    portfolio
)
要求：
assert decision.approved is True
6. RiskManager 生命周期接口
当前 TradingEngine 已调用：
risk.on_event(
    event,
    state
)
之前错误：
AttributeError:

'RiskManagerV2'
object has no attribute
'on_event'
已修复。
原因：
TradingEngine 设计要求：
每个 F_LAST：
MarketEvent

↓

RiskManager.on_event()
最终：
RiskManager 应支持：
on_event(
    event,
    state
)
用途：
实时监控：
- 市场状态
- 波动
- 流动性
- 风险状态
7. risk/limits.py
状态：
建议新增。
职责：
定义硬限制。
例如：
最大仓位
max_position = 5
检查：
当前:

ES LONG 5


Signal:

BUY 1


结果:

REJECT
最大订单数量
max_orders = 10
最大亏损
例如：
max_daily_loss = 2000
接口：
建议：
class RiskLimits:


    def check_position_limit(
        self,
        portfolio,
        signal
    ):
        pass



    def check_loss_limit(
        self,
        portfolio
    ):
        pass
8. risk/exposure.py
状态：
建议新增。
职责：
计算风险暴露。
包括：
当前持仓
例如：
ES LONG 3
名义价值
例如：
ES Price

6000

×

50

×

3
多品种暴露
例如：
ES
NQ
MES
统一计算。
接口：
建议：
class Exposure:


    def calculate(
        self,
        portfolio
    ):
        pass
输出：
例如：
{
"ES":30000,
"NQ":10000
}
9. risk/kill_switch.py
状态：
建议新增。
用途：
紧急停止交易。
触发：
手动
例如：
STOP
自动
条件：
Daily Loss > Limit
或者：
Execution Error Too Many
接口：
class KillSwitch:


    def activate(
        self,
        reason
    ):
        pass



    def is_active(self):
        pass
交易流程：
Signal

 |

 v

RiskManager

 |

检查 KillSwitch


 |

ACTIVE

 |

Reject
10. RiskManager 最终结构
建议：
class RiskManagerV2:


    def __init__(self):

        self.limits = RiskLimits()

        self.exposure = Exposure()

        self.kill_switch = KillSwitch()
检查流程：
Signal

 |

 v

RiskManager


 |

检查 KillSwitch


 |

检查 Limits


 |

检查 Exposure


 |

返回 Decision
11. TradingEngine 中的位置
当前：
TradingEngine

      |

      v

Strategy

      |

      v

Signal

      |

      v

RiskManager

      |

      v

Execution

      |

      v

Fill
最终：
TradingEngine


      |

      v


Strategy


      |

      v


Signal


      |

      v


RiskManager


      |

      +----------------+

      |                |

      v                v


Limits          KillSwitch


      |

      v


Decision


      |

      v


Order
12. 当前测试验证
文件：
tests/test_full_runtime_engine.py
验证：
Risk
指标：
risk.total_checks
要求：
==1
批准：
risk.total_approved
要求：
==1
拒绝：
risk.total_rejected
要求：
==0
执行：
engine.risk_reject_count
要求：
==0
13. 已发生错误
错误
AttributeError:

'RiskManagerV2'
object has no attribute
'on_event'
原因：
TradingEngine 已设计：
risk.on_event()
但是 RiskManager 没有实现。
修复：
增加：
on_event()
14. 风控与三模式关系
BACKTEST
使用：
历史风险计算。
例如：
最大回撤

最大仓位
PAPER
增加：
实时：
波动

流动性

延迟
LIVE
增加：
强制：
Kill Switch

Daily Loss Limit

Broker Risk Check
15. 禁止重新设计事项
新窗口不要：
❌ Strategy 自己检查风险
❌ Execution 判断是否允许交易
❌ Portfolio 判断是否停止交易
❌ Risk 直接发送 Order
❌ 每个策略写自己的 Risk
16. 当前未完成任务
P0
整理 Risk 文件结构：
创建：
risk/

limits.py

exposure.py

kill_switch.py

risk_manager.py
完成标准：
RiskManagerV2
=
Limits
+
Exposure
+
KillSwitch
P1
增加测试：
tests/test_risk_runtime.py
覆盖：
- 超仓拒绝
- 最大亏损拒绝
- KillSwitch停止
- 正常通过
P2
LIVE 风控：
连接：
Broker Account
检查：
- Margin
- Buying Power
- Real Position
下一部分继续：
“Order / Signal / Strategy 插件系统最终设计，以及当前交易策略接入方式”




  来源





继续













九、Order / Signal / Strategy 插件系统最终设计
状态：
- Strategy 插件化设计：聊天中确认
- Order 生命周期：已实现并通过测试
- Signal 模型：已有使用记录，完整文件状态待核对
- 策略库：尚未正式建立
1. Strategy 层设计目标
核心原则：
策略只负责产生交易意图，不负责执行、不负责风控、不负责账户管理。

禁止：
Strategy

 |

直接创建 Fill


或者


Strategy

 |

直接修改 Position
正确：
MarketEvent

      |

      v

Strategy

      |

      v

Signal

      |

      v

RiskManager

      |

      v

Order

      |

      v

Execution

      |

      v

Fill

      |

      v

Portfolio
2. Strategy 目录设计
最终建议：
strategy/

├── base.py

├── mean_reversion.py

├── scalper.py

├── imbalance.py

└── registry.py
3. Strategy Base 接口
建议新增：
strategy/base.py
定义所有策略统一接口。
示例：
from abc import ABC, abstractmethod


class StrategyBase(ABC):


    def __init__(self):

        self.name = self.__class__.__name__



    def on_start(self):

        pass



    @abstractmethod
    def on_market_event(
        self,
        event,
        state
    ):

        pass



    def generate_signal(
        self,
        state
    ):

        return None



    def on_stop(self):

        pass
4. Strategy 生命周期
TradingEngine 调用：
engine.start()

        |

        v

strategy.on_start()



事件循环



        |

        v


strategy.on_market_event()



结束



        |

        v


strategy.on_stop()
当前测试已经验证：
文件：
tests/test_full_runtime_engine.py
要求：
strategy.started == 1

strategy.stopped == 1
5. Signal 设计
状态：
聊天中确认。
Signal 是：
Strategy 与 RiskManager 之间的数据对象。

流程：
Strategy

产生：

Signal

↓

RiskManager

检查

↓

Order
Signal 不包含：
- 成交价格
- Fill
- Position
建议结构：
@dataclass
class Signal:


    symbol: str


    side: OrderSide


    quantity: int


    strategy_name: str


    reason: str
例如：
Signal(

symbol="ESU6",

side=BUY,

quantity=1,

reason="mean_reversion"

)
6. 当前 OneShotStrategy
状态：
测试中使用。
文件：
待核对。
作用：
测试完整交易链。
行为：
第一次满足：
F_LAST
产生：
Signal
之后：
不重复产生。
测试：
tests/test_full_runtime_engine.py
验证：
strategy.generate_signal_count == 1
以及：
engine.signal_count == 1
7. 高频 ES Scalper 策略设计方向
项目最终目标：
CME ESU6 MBO 高频剥头皮。
策略需要使用：
L3 OrderBook
输入：
OrderBook

↓

Features
可能特征：
Order Book Imbalance
OBI：
(Bid Volume - Ask Volume)

/

(Bid Volume + Ask Volume)
Micro Price
公式：
micro_price =
(
ask_price * bid_volume
+
bid_price * ask_volume
)

/

(
bid_volume
+
ask_volume
)
Queue
L3：
- order add
- modify
- cancel
- trade
Trade Flow
包括：
- aggressive buy
- aggressive sell
- volume delta
8. Strategy 不直接读取数据文件
禁止：
strategy.py

open(
"ESU6.dbn.zst"
)
正确：
DatabentoFeed

↓

MarketEvent

↓

OrderBook

↓

FeatureEngine

↓

Strategy
十、Feature Engine 设计
状态：
- FeatureEngine 曾讨论
- 文件状态待核对
目标：
将：
OrderBook
转换：
Features
结构建议：
feature/

├── engine.py

├── imbalance.py

├── microprice.py

├── trade_flow.py

└── volatility.py
1. FeatureEngine
接口：
update(
    orderbook,
    event
)
输出：
FeatureState
例如：
{
"obi":0.65,

"micro_price":6000.125,

"trade_delta":25
}
2. Strategy 输入
最终：
不是：
Strategy(event)
而是：
Strategy(
    event,
    state,
    features
)
数据流：
MBO

↓

OrderBookBuilder

↓

OrderBook

↓

FeatureEngine

↓

FeatureState

↓

Strategy

↓

Signal
十一、Order 系统最终设计
状态：
✅ 已实现
✅ 测试通过
文件：
order/order.py
1. Order 职责
Order 表示：
交易请求。
保存：
- symbol
- side
- quantity
- status
- order_id
不保存：
❌ 成交价格
这是已确认修改。
2. Order 生命周期
状态：
OrderStatus
流程：
CREATED

 |

 v

SUBMITTED

 |

 v

ACCEPTED

 |

 v

PARTIAL_FILLED

 |

 v

FILLED

取消：
CANCELLED
3. Order 方法
当前测试验证：
submit()

accept()

fill()

cancel()
之前错误：
TypeError:

Order.fill()
missing price
原因：
Execution 调用：
order.fill(
    quantity=fill.quantity
)
但是旧接口：
fill(
    quantity,
    price
)
修改方向：
删除：
price
参数。
最终：
fill(
    quantity
)
验证：
命令：
python -c "from order.order import Order; import inspect; print(inspect.signature(Order.fill))"
结果：
(self, quantity: int)
十二、Strategy 与 Engine 集成
当前：
core/engine.py
负责：
MarketEvent

↓

State Update

↓

OrderBook Update

↓

F_LAST

↓

Strategy

↓

Risk

↓

Execution

↓

Portfolio
关键：
不是所有 MBO 都触发策略。
当前设计：
_is_last(event)
判断：
F_LAST
原因：
MBO：
大量：
- Add
- Modify
- Cancel
策略不需要每条都交易。
十三、禁止重新设计
新窗口不要：
❌ 每个策略复制 Engine
❌ Strategy 直接调用 Execution
❌ Strategy 保存 Position
❌ Strategy 修改 Portfolio
❌ Order 保存 Fill Price
❌ 用随机行情替代真实 MBO 测试
十四、当前未完成任务
P0
建立 Strategy 基础接口：
新增：
strategy/base.py
完成：
所有策略插件统一。
P1
建立 Feature 层：
涉及：
feature/
完成：
- OBI
- MicroPrice
- TradeFlow
- Volatility
P2
接入 ES Scalper 策略：
strategy/scalper.py
输入：
L3 Feature
输出：
Signal
P3
策略回测框架：
支持：
多策略

多参数

优化
下一部分继续：
“OrderBook / L3 MBO 数据重建 / Feature 数据流设计，以及当前 Databento 实现状态”




  来源





继续













十五、OrderBook / L3 MBO 数据重建 / Feature 数据流设计
状态：
- L3 MBO 重建方向：已确认
- Databento MBO 数据格式：已确认
- OrderBookBuilder：已存在并通过 Runtime 测试
- FIFO OrderBook：聊天中确认
- Feature 层：待完善
1. 项目核心目标（重新确认）
本项目最终目标：
使用：
CME MDP 3.0 MBO Level 3 数据
构建：
L3 Replay Engine

↓

OrderBook Reconstruction

↓

Microstructure Features

↓

ESU6 Scalping Strategy

↓

Backtest / Paper / Live
2. 数据源设计
当前确认数据：
提供商：
Databento
数据类型：
CME MDP 3.0 MBO
主要合约：
ESU6
文件：
data/ESU6_2026-06-15_MBO.dbn.zst
3. Databento MBO 字段
当前确认字段：
ts_recv

ts_event

rtype

publisher_id

instrument_id

action

side

price

size

channel_id

order_id

flags

ts_in_delta

sequence

symbol
4. Action 类型
Databento MBO：
A
M
C
R
T
F
N
含义：
A
Add
新增订单。
流程：
Exchange

↓

新增 Order

↓

OrderBook
M
Modify
修改订单。
例如：
数量变化：
100

↓

80
或者：
价格变化。
C
Cancel
撤销。
删除：
Order ID
R
Replace
替换。
T
Trade
成交。
表示：
市场发生交易。
F
Fill / Last
项目中重点：
F_LAST
用于：
触发：
- Strategy
- Risk
- Execution
N
其他通知事件。
5. MarketEvent 统一格式
文件：
core/event.py
状态：
已存在。
作用：
将：
Databento Record
转换：
MarketEvent
结构：
MarketEvent(
    ts_event,

    ts_recv,

    sequence,

    action,

    side,

    price,

    size,

    order_id,

    symbol
)
所有后续模块：
只处理：
MarketEvent
6. 数据流完整路径
当前已验证：
DBN MBO File


        |

        v


DatabentoFeed


        |

        v


MarketEvent


        |

        v


TradingEngine


        |

        v


OrderBookBuilder


        |

        v


OrderBook


        |

        v


FeatureEngine


        |

        v


Strategy


        |

        v


Signal


        |

        v


Risk


        |

        v


Order


        |

        v


Execution


        |

        v


Fill


        |

        v


Portfolio
7. OrderBookBuilder
文件：
orderbook/builder.py
状态：
✅ 已实现
✅ Runtime 测试通过
职责：
接收：
MarketEvent
维护：
OrderBook
核心接口：
on_event(event)
处理：
if action == A:

    add_order()


elif action == M:

    modify_order()


elif action == C:

    cancel_order()


elif action == T:

    process_trade()
8. OrderBook
文件：
orderbook/book.py
状态：
已实现基础版本。
职责：
维护：
Bid Side

Ask Side

Orders
核心结构：
bids

asks

orders
价格：
使用：
price -> PriceLevel
例如：
BID

6000.00

 |

100 orders
9. PriceLevel FIFO
文件：
orderbook/level.py
状态：
已实现。
目的：
模拟真实交易所：
价格优先：
Price Priority
时间优先：
FIFO
结构：
PriceLevel


head

 |

Order

 |

Order

 |

tail
支持：
append()

pop()

remove()
10. Order
文件：
orderbook/order.py
状态：
已存在。
注意：
这里是：
盘口订单。
不是：
交易订单。
容易混淆：
项目有两个 Order：
OrderBook Order
路径：
orderbook/order.py
表示：
交易所挂单。
包含：
order_id

price

size

side
Trading Order
路径：
order/order.py
表示：
策略下单。
包含：
symbol

side

quantity

status
禁止合并。
原因：
职责完全不同。
11. Best Bid / Ask
OrderBook 提供：
best_bid()

best_ask()
输出：
例如：
Bid:

6000.00


Ask:

6000.25
Spread：
Ask-Bid
12. Microstructure Features
目标：
将盘口状态：
转换：
策略可以使用的数据。
目录：
建议：
feature/

├── engine.py

├── imbalance.py

├── microprice.py

├── trade_flow.py

└── volatility.py
13. Order Book Imbalance
OBI：
公式：
OBI =

(Bid Volume - Ask Volume)

/

(Bid Volume + Ask Volume)
例：
Bid:
100
Ask:
50
结果：
(100-50)/(150)

=0.33
解释：
正：
买方压力。
负：
卖方压力。
14. Micro Price
公式：
MicroPrice =


Ask Price × Bid Size

+

Bid Price × Ask Size


-------------------------


Bid Size + Ask Size
用途：
预测：
短期价格方向。
15. Trade Flow
记录：
主动买：
Aggressive Buy
主动卖：
Aggressive Sell
计算：
Delta Volume
例如：
Buy Volume

-

Sell Volume
16. 大单检测
目标：
Jigsaw DOM 类似效果。
检测：
Large Order
例如：
ES：
超过：
100 contracts
标记。
17. 吸收检测
目标：
发现：
Absorption
例如：
盘口：
大量卖单
但是：
价格不上跌。
说明：
买方吸收。
需要：
组合：
Trade Volume

+

OrderBook Change

+

Price Movement
18. 当前测试验证
测试：
tests/test_full_runtime_engine.py
结果：
5 passed
其中验证：
Real MBO

↓

DatabentoFeed

↓

TradingEngine

↓

OrderBookBuilder
19. 已出现的问题
crossed_book
早期：
出现：
bid > ask
原因：
OrderBook 更新顺序问题。
后续：
修复。
现在：
正常：
spread:

250000000

500000000
20. 性能问题
早期：
Python 全量处理：
问题：
KeyboardInterrupt
位置：
dbn_feed.py
原因：
长时间：
逐条 Python 解析。
后续方案：
采用：
Python + C++
21. Python + C++ 架构决定
已确认：
采用：
Python + C++
不是：
Python + C。
原因：
C++：
- 性能
- 内存控制
- 高频事件处理
Python：
- 策略
- 分析
- UI
- 调试
未来：
C++ Core

        |

        v

L3 Replay Engine

        |

        v

Python Strategy Layer
22. 当前 OrderBook 未完成任务
P0
完善：
orderbook/book.py
增加：
bid_volume()

ask_volume()

depth()

snapshot()
原因：
FeatureEngine 需要。
P1
完善：
orderbook/builder.py
增加：
- sequence validation
- recovery
- snapshot loading
P2
增加：
feature/
23. 禁止重新设计
新窗口不要：
❌ 用随机盘口替代 MBO
❌ Strategy 直接读取 CSV
❌ 跳过 OrderBook 重建直接算指标
❌ 使用 L1/L2 模型代替 L3
❌ 合并 order/order.py 与 orderbook/order.py
下一部分继续：
“UI / DOM 可视化设计、Jigsaw 风格盘口、Web 用户界面，以及当前未完成开发计划”




  来源





继续













二十四、DOM 可视化系统设计（Jigsaw 风格）
状态：
- 需求：聊天中确认
- PyQt DOM 原型：曾经测试
- 正式 UI：尚未完成
- 架构方向：已确认
1. UI 最终目标
项目最终需要：
CME MBO L3 数据

        |

        v

Replay Engine

        |

        v

OrderBook State

        |

        v

DOM UI

        |

        v

Trader / Quant Researcher
目标：
实现类似：
- Jigsaw Trading DOM
- Sierra Chart DOM
- Bookmap 类盘口观察
2. UI 技术方向
当前建议：
第一阶段
桌面：
PyQt / PySide
原因：
- 开发速度快
- 与 Python Engine 集成容易
- 适合回测研究
第二阶段
Web：
Backend

FastAPI


+

Frontend

React / Vue
最终：
Trading Engine

        |

        v

WebSocket


        |

        v


Browser UI
3. 原始 DOM 设计需求
用户最初要求：
从左往右解释 Jigsaw 风格 DOM 每个区域。

确认布局：
+------------------------------------------------+

|                Price Ladder                    |

+------------------------------------------------+

| Bid DOM          | Time & Sales                |

|                  |                            |

|                  |                            |

+------------------------------------------------+

4. 左侧 DOM
Bid Side
颜色：
蓝色
表示：
买方挂单。
显示：
Price

Bid Size

Queue

Orders
例如：
6000.00    150

5999.75    80

5999.50    300
5. Ask Side
颜色：
红色
表示：
卖方挂单。
例如：
6000.25    120

6000.50    90
6. 中间价格线
要求：
白色。
表示：
Last Trade Price。
不是：
Mid Price。
区别：
Mid：
(Bid+Ask)/2
Last：
最后成交价格
7. Time & Sales
右侧：
逐笔成交。
显示：
Time

Price

Size

Aggressor
颜色：
主动买：
红色背景
主动卖：
蓝色背景
8. 大单高亮
需求：
识别：
Large Order
显示：
例如：
6000.25

500 contracts
特殊标记。
9. 吸收成交 Block
需求：
显示：
Absorption
例如：
卖方持续成交：
Sell Volume:

5000
但是：
价格：
没有下降。
UI：
显示：
特殊 Block。
10. 原始 PyQt 原型问题
曾存在：
PyQt DOM mock
问题：
问题 1
随机数据。
错误：
random()
替代：
必须：
Real MBO
问题 2
全量刷新。
旧：
table.clear()
或者：
setRowCount()
导致：
闪烁。
正确：
增量更新：
只更新变化 Cell
问题 3
mid_price 固定。
错误：
static mid_price
必须：
来自：
OrderBook.best_bid

+

OrderBook.best_ask
11. UI 数据接口设计
不要：
UI 读取：
.dbn.zst
正确：
OrderBook


↓

DOM Snapshot


↓

UI
建议：
新增：
ui/
结构：
ui/

├── dom/

│
├── timesales/

│
├── websocket/

│
└── app.py

二十五、Web 用户可视化系统设计
状态：
- 用户明确增加需求
- 尚未开发
目标：
除了桌面 DOM：
还需要：
浏览器交互。
1. Web 架构
最终：
Trading Engine


        |

        v


FastAPI


        |

        v


WebSocket


        |

        v


React/Vue


        |

        v


Browser
2. Web 显示内容
包括：
Dashboard
显示：
- 当前模式
- 当前合约
- PnL
- Position
- Risk 状态
DOM
显示：
实时盘口。
Chart
显示：
- Price
- Volume
- Indicators
Strategy
显示：
当前：
- 策略名称
- Signal
- 状态
Execution
显示：
- Order
- Fill
- Latency
3. 模式切换 UI
必须支持：
BACKTEST

PAPER

LIVE
例如：
页面顶部：
Mode:

[ BACKTEST ▼ ]

禁止：
运行时混淆。
二十六、BACKTEST / PAPER / LIVE 三模式设计
状态：
已确认。
1. BACKTEST
用途：
历史回测。
数据：
DBN MBO File
流程：
Historical Data

↓

Replay Engine

↓

Strategy

↓

Sim Execution

↓

Portfolio
执行：
模拟。
2. PAPER
用途：
模拟交易。
数据：
实时行情。
来源：
例如：
Databento Live

Broker Feed
执行：
模拟成交。
流程：
Live Market Data


↓

Engine


↓

Strategy


↓

Risk


↓

Paper Execution


↓

Paper Portfolio
3. LIVE
用途：
真实交易。
连接：
Broker。
例如：
Broker API
流程：
Live Data


↓

Strategy


↓

Risk


↓

Execution


↓

Broker


↓

Real Fill


↓

Portfolio
4. 三模式禁止事项
禁止：
BACKTEST：
连接真实 Broker。
禁止：
LIVE：
使用假成交。
禁止：
PAPER：
修改真实账户。
二十七、Execution 系统最终状态
状态：
✅ 已实现
✅ 测试通过
测试：
tests/test_execution_runtime_contract.py
结果：
13 passed
1. Execution 职责
负责：
Order

↓

Fill
不负责：
- Strategy
- Risk
- Portfolio
2. ExecutionEngine
文件：
待核对。
接口：
submit_order()

cancel_order()

snapshot()

reset()
3. Execution Mode
已有：
ExecutionMode.BACKTEST
未来：
增加：
PAPER

LIVE
4. Execution 测试验证
输出：
EXECUTION RUNTIME DIAGNOSTIC

mode = BACKTEST

fills = 1

volume = 1

callback fills = 1
二十八、Risk 系统最终状态
状态：
✅ 基础版本完成
✅ Runtime 已接入
目录：
risk/
文件：
risk/

├── limits.py

├── exposure.py

├── kill_switch.py

└── risk_manager.py
1. Risk 职责
检查：
Signal。
输入：
Signal
输出：
Approve

Reject
不能：
生成订单。
2. Risk 流程
Signal


↓

RiskManager


↓

Approved


↓

Order
3. 当前 Runtime 测试验证
要求：
risk.total_checks == 1

risk.total_approved == 1

risk.total_rejected == 0
4. 曾出现错误
错误：
AttributeError:

'RiskManagerV2'

object has no attribute

'on_event'
原因：
Engine 调用了：
risk.on_event()
但是 Risk 没有接口。
修复：
增加接口。
二十九、Portfolio 最终设计
状态：
聊天确认。
部分测试通过。
目录：
portfolio/
文件：
portfolio/

├── position.py

├── pnl.py

├── portfolio.py

└── account.py
1. 数据流
Fill

↓

Portfolio

↓

Position

↓

PnL
2. Position
负责：
仓位。
状态：
FLAT

LONG

SHORT
支持：
- Open
- Add
- Reduce
- Close
- Reverse
3. PnL
负责：
Realized:
已实现盈亏。
Unrealized:
浮动盈亏。
Equity：
initial_capital

+

realized

+

unrealized
4. 合约点值
已确认：
ES

50


MES

5


NQ

20


MNQ

2
5. Portfolio 原则
所有仓位变化：
必须来自：
Fill
禁止：
Strategy：
直接：
position += 1
下一部分继续：
“项目目录最终版、全部文件交接表、已完成/未完成任务清单、给新窗口执行指令”




  





继续













三十、项目最终目录结构（交接版本）
状态：
- 已确认：部分目录
- 来源：聊天中确认
- GitHub 仓库实际结构：待新窗口验证
- 不可视为 GitHub 当前真实目录
推荐最终结构：
TradingSystem
│
├── main.py
│
├── config/
│   ├── settings.py
│   ├── symbols.py
│   └── modes.py
│
├── core/
│   ├── __init__.py
│   ├── engine.py
│   ├── event.py
│   ├── state.py
│   ├── clock.py
│   └── mode.py
│
├── data/
│   ├── __init__.py
│   ├── databento_feed.py
│   ├── csv_feed.py
│   └── realtime_feed.py
│
├── orderbook/
│   ├── __init__.py
│   ├── order.py
│   ├── level.py
│   ├── book.py
│   └── builder.py
│
├── feature/
│   ├── __init__.py
│   ├── engine.py
│   ├── imbalance.py
│   ├── microprice.py
│   ├── trade_flow.py
│   └── volatility.py
│
├── strategy/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   └── scalping/
│
├── signal/
│   ├── __init__.py
│   └── signal.py
│
├── risk/
│   ├── __init__.py
│   ├── limits.py
│   ├── exposure.py
│   ├── kill_switch.py
│   └── risk_manager.py
│
├── order/
│   ├── __init__.py
│   └── order.py
│
├── execution/
│   ├── __init__.py
│   ├── execution_engine.py
│   ├── fill.py
│   └── simulator.py
│
├── portfolio/
│   ├── __init__.py
│   ├── position.py
│   ├── pnl.py
│   ├── portfolio.py
│   └── account.py
│
├── ui/
│   ├── dom/
│   ├── timesales/
│   ├── websocket/
│   └── app.py
│
├── cpp/
│   ├── replay_engine/
│   ├── orderbook/
│   └── bindings/
│
├── tests/
│   ├── test_full_runtime_engine.py
│   ├── test_execution_runtime_contract.py
│   └── ...
│
├── data/
│   └── ESU6_2026-06-15_MBO.dbn.zst
│
├── requirements.txt
├── pytest.ini
├── README.md
└── .gitignore
三十一、核心模块职责关系
1. core
核心调度层。
负责：
Event Flow
State
Clock
Engine Lifecycle
核心：
TradingEngine
调用：
Feed

↓

Engine

↓

Modules
2. data
行情输入。
负责：
不同数据源统一输出：
MarketEvent
支持：
BACKTEST

PAPER

LIVE
3. orderbook
盘口重建。
负责：
MBO:
A/M/C/R/T/F/N
转换：
OrderBook State
4. feature
盘口特征。
输入：
OrderBook
输出：
Feature Vector
例如：
OBI

MicroPrice

Delta

Depth

Liquidity
5. strategy
策略层。
不允许：
直接访问：
DBN

CSV

Broker
只能：
读取：
State

Feature

Market Data
输出：
Signal
6. signal
策略意图。
例如：
Signal(
    symbol="ESU6",
    side="BUY",
    quantity=1
)
7. risk
风险控制。
输入：
Signal
输出：
Approve

Reject
8. order
交易订单。
注意：
与：
orderbook/order.py
不同。
9. execution
执行。
流程：
Order

↓

Execution

↓

Fill
10. portfolio
账户状态。
流程：
Fill

↓

Position

↓

PnL
三十二、已经完成工作记录
状态分类：
A. 已验证完成
1. Execution Runtime
测试：
python -m pytest tests/test_execution_runtime_contract.py -v -s
结果：
13 passed
验证：
- Order 生命周期
- Submit
- Accept
- Fill
- Cancel
- Snapshot
- Statistics
- Reset
2. Full Runtime Engine
测试：
python -m pytest tests/test_full_runtime_engine.py -v -s
结果：
5 passed
验证链：
Real MBO

↓

DatabentoFeed

↓

TradingEngine

↓

OrderBookBuilder

↓

Strategy

↓

Risk

↓

Order

↓

Execution

↓

Portfolio
3. MBO 文件
已验证存在：
D:\TradingSystem\data\ESU6_2026-06-15_MBO.dbn.zst
4. F_LAST
测试输出：
events: 20000

F_LAST: 13566
说明：
真实 MBO 中存在成交事件。
三十三、历史错误记录
错误 1
Order.fill
错误：
NameError:

name 'price' is not defined
位置：
order/order.py
原因：
函数：
fill(
    quantity:int
)
内部使用：
price
但是参数不存在。
修复：
已完成。
结果：
test_trading_pipeline.py

PASSED
错误 2
MBO 文件路径
错误：
FileNotFoundError:

D:\TradingSystem\data\ESU6_2026-06-15_MBO.dbn.zst
原因：
测试路径与实际数据位置不一致。
修复：
调整数据路径。
结果：
通过。
错误 3
RiskManagerV2
错误：
AttributeError:

'RiskManagerV2'

object has no attribute

'on_event'
原因：
Engine 调用：
risk.on_event()
Risk 没有实现。
修复：
增加：
on_event()
错误 4
Execution Fail
错误：
Execution failed after Risk approval

execution_failures=1
原因：
Execution 接口：
Order → Fill
参数不匹配。
修复：
完成。
结果：
Full Runtime:
PASSED
三十四、当前未完成任务列表
优先级排序：
P0：仓库状态核对
涉及：
全部文件。
完成标准：
新窗口：
1. 拉取 GitHub
2. 对比本交接包
3. 输出差异
状态：
待完成。
P1：Feature Engine 完善
涉及：
feature/
以及：
orderbook/book.py
需要增加：
bid_volume()

ask_volume()

depth()

snapshot()
完成标准：
可以实时计算：
OBI

MicroPrice

Delta
P2：Strategy Plugin
涉及：
strategy/base.py
strategy/registry.py
目标：
支持：
策略插件
例如：
MeanReversion

OrderFlowScalping

LiquidityScalping
P3：回测框架完善
涉及：
core/engine.py
data/
portfolio/
要求：
支持：
BACKTEST
完整报告：
- Trades
- PnL
- Drawdown
- Sharpe
- Win Rate
P4：PAPER 模式
涉及：
execution/
portfolio/
data/
目标：
实时行情：
模拟成交。
P5：LIVE 模式
涉及：
execution/
broker/
目标：
连接：
Broker API
P6：C++ 加速
涉及：
cpp/
目标：
迁移：
高频部分：
- Replay
- OrderBook
- Feature
保持：
Python：
策略层。
三十五、明确禁止重新采用的方案
1.
禁止：
随机盘口。
原因：
之前 PyQt Demo：
random()
不符合真实交易。
2.
禁止：
直接 CSV 计算策略。
必须：
MBO

↓

OrderBook

↓

Feature
3.
禁止：
跳过 L3。
原因：
目标就是：
CME MDP 3.0 L3 Scalping。
4.
禁止：
合并两个 Order。
必须保持：
order/order.py

交易订单


orderbook/order.py

盘口订单
5.
禁止：
BACKTEST/PAPER/LIVE 混合。
必须：
模式隔离。
三十六、给新 ChatGPT 窗口执行指令
复制以下内容：
你现在接手 TradingSystem 项目。

请先完整阅读《TradingSystem_项目交接包》。

不要立即修改代码。

第一步：

连接并检查 GitHub:

https://github.com/panlin520/TradingSystem

确认：

- branch
- commit
- directory structure
- existing files


第二步：

将：

交接包

vs

GitHub 当前代码

逐项比较。


输出：

1. 已一致部分
2. 已缺失文件
3. 文件重复
4. 功能冲突
5. 未提交修改风险


不要：

删除文件。

不要：

重新设计架构。

不要：

替换已经通过测试的模块。


等待我确认后继续。


继续开发时：

从：

P0 仓库核对

开始。

然后：

P1 Feature Engine

P2 Strategy Plugin

P3 Backtest Framework


保持：

BACKTEST/PAPER/LIVE 三模式。

保持：

L3 MBO → OrderBook → Feature → Strategy → Risk → Execution → Portfolio 架构。

三十七、证据附录
GitHub
用户提供：
https://github.com/panlin520/TradingSystem
状态：
当前窗口：
未完成 GitHub 实际读取验证。
标记：
待核对
本地目录
已确认：
D:\TradingSystem
Python
已验证：
Python 3.12.5
环境：
D:\TradingSystem\.venv
pytest
版本：
pytest-9.1.1
测试结果
Full Runtime:
5 passed
Execution Contract:
13 passed
Trading Pipeline:
1 passed
共享链接记录
用户提供：
https://chatgpt.com/share/6aa171a7-f1f8-83ea-916b-143e0a76acfc
交接包结束
新窗口继续前：
必须先：
1. GitHub 核对
2. 文件差异报告
3. 用户确认
4. 再修改代码
禁止直接覆盖当前通过测试版本。