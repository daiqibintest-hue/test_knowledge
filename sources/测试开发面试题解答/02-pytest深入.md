# 二、pytest 深入（Q6–Q10）

---

## Q6：fixture 的作用与使用

fixture 用来管理用例的 **前置/后置**（准备数据、登录、连接 DB、清理脏数据），实现复用和"测试逻辑与准备逻辑解耦"。用例只需把 fixture 名写进参数，pytest 自动注入。

**1. scope 区别**：

- `function`（默认）：每个用例执行一次。
- `class`：每个测试类一次。
- `module`：每个文件一次。
- `session`：整个测试会话只执行一次。

**2. 登录 token 用 `session`**：登录一次全局复用，省时间，也避免频繁登录被风控/触发验证码。

**3. 每条用例都要重新登录**：那就 **不该用 session**，改 `function`；或者参数化不同账号（多账号场景）。session 的前提是"token 可全局共享且有效期够"。

**4. fixture 互相依赖**：可以。一个 fixture 把另一个 fixture 当参数即可，pytest 自动解析依赖顺序。

**5. 返回值传递**：fixture 的返回值（`return` 或 `yield` 的值）通过 **同名参数** 注入用例。

**6. `autouse=True`**：不用显式声明就自动对作用域内所有用例生效，适合全局性前置（环境检查、统一日志上下文）。慎用，会降低可读性。

**7. `yield` vs `return`**：`return` 只能做前置；`yield` 可以在用例结束后继续执行 **后置清理**（teardown）。

**8. 用 `yield` 清理数据**：

```python
@pytest.fixture
def order(login_headers):
    order_id = OrderApi.create(login_headers)   # 前置：造单
    yield order_id
    OrderApi.delete(order_id, login_headers)     # 后置：清理
```

**9. fixture 失败**：依赖它的用例会被标记为 **error（不是 fail）**，并跳过执行——这正是用 fixture 管前置的好处：前置挂了能和"用例本身断言失败"区分开。

**10. 参数化 fixture**：`@pytest.fixture(params=[...])`，配合 `request.param` 取值，让同一前置跑多组配置。

---

## Q7：conftest.py 的作用

`conftest.py` 是 pytest 的 **共享 fixture 和 hook 容器**，同目录及子目录的用例可直接使用，无需 import。

**1. 不需要手动导入**：pytest 自动发现，这是它和普通工具模块最大的区别。

**2. 多级目录多个 conftest**：**就近原则 + 层叠生效**。根目录 conftest 全局可用，子目录 conftest 只对该目录及子目录生效，可覆盖父级同名 fixture。

**3. 哪些公共能力放 conftest**：跨用例共享的 fixture（登录、环境、数据清理）、自定义命令行参数（`pytest_addoption`）、各种 hook。

**4. 不同业务模块不同前置**：各业务目录放各自的 `conftest.py`，互不干扰。

**5/6. 不要放大量业务逻辑**：conftest 只放 **编排级 fixture**，真正的业务实现下沉到 `api`/`common`。否则 conftest 越来越臃肿、难维护。

**7. session 级 fixture** 一般放 **根目录 conftest**。

**8. `test_*.py` vs `conftest.py`**：前者是用例文件会被收集执行；后者是配置/fixture 容器，**不会被当成用例收集**。

---

## Q8：参数化使用

**1. 基本语法**：

```python
@pytest.mark.parametrize("username, expected", [
    ("test01", 0),
    ("", 10001),
])
def test_login(username, expected):
    ...
```

**2. 数据来自 YAML**：先 `yaml.safe_load` 读成 list，再喂给 `parametrize`。

**3. 一条 YAML 10 组数据 → 10 条用例**：list 有几个元素就生成几条用例。

**4. Allure 标题**：用 `ids=[...]` 给每条起名，或在用例内 `allure.dynamic.title(case["name"])` 动态设置标题。

**5. 一组失败其他继续**：参数化的每组是独立用例，互不影响，一组 fail 不影响其余。

**6. 自定义 id**：`ids=[c["name"] for c in cases]`，报告里就显示中文用例名而不是 `case0/case1`。

**7. 多参数组合**：堆叠多个 `parametrize` 装饰器 = **笛卡尔积**。

**8. 笛卡尔积问题**：用例数 **爆炸**（3×4×5=60），执行慢、报告乱。要么显式列组合，要么收敛维度。

**9. 数据量大时控制效率**：抽样/分级（smoke 只跑核心子集）、用 `pytest-xdist` 并发执行（`-n auto`）。

---

## Q9：marker 使用

**1. `@pytest.mark.smoke`**：给用例打 **分类标签**，便于按需挑选执行。

**2. 只跑 smoke**：`pytest -m smoke`。

**3. 排除 smoke**：`pytest -m "not smoke"`。

**4. 需在 pytest.ini 注册**：`markers =` 下声明，否则会有 `PytestUnknownMarkWarning` 告警；严格模式（`--strict-markers`）下会直接报错。

**5. 标签划分**：按用途 `smoke / regression`，按业务 `order / pay / user`，组合使用。

**6. 一条用例多个 marker**：可以叠加。

**7. 结合 Jenkins**：把 `-m` 作为构建参数传入，冒烟流水线传 `smoke`，全量流水线不传或传 `regression`。

**8. 标签过多的问题**：标签泛滥后没人知道该打哪个、组合查询混乱。要有 **统一的标签规范** 并文档化。

---

## Q10：pytest.ini 常配置项

```ini
[pytest]
# 测试文件 / 类 / 方法 的收集命名规则
python_files = test_*.py
python_classes = Test*
python_functions = test_*
# 注册自定义标签，避免 PytestUnknownMarkWarning
markers =
    smoke: 冒烟用例
    regression: 回归用例
# 控制台实时输出日志及级别
log_cli = true
log_cli_level = INFO
# 默认执行参数
addopts = -v --alluredir=./report/allure-results --clean-alluredir
```

- **1/2/3.** `python_files` / `python_classes` / `python_functions` 控制收集规则。
- **4.** `markers` 注册自定义标签。
- **5.** `log_cli_level` 配日志级别。
- **6.** `addopts` 配默认执行参数。
- **7.** `--alluredir` 指定 Allure 结果目录。
- **8. 避免和 Jenkins 命令冲突**：`pytest.ini` 只放 **稳定不变** 的项（命名规则、marker 注册）；**动态项**（环境、`-m` 标签、报告目录）放在 Jenkins 命令行，命令行参数会覆盖 ini，避免两边写死打架。
- **9. `addopts`**：每次执行自动追加的命令行参数，相当于"默认参数"。
- **注意**：注释 **单独成行**（`#` 或 `;` 开头）。**不要在配置值后面写行内注释**——某些解析器会把 `; xxx` 当成值的一部分（比如 `python_files` 的值变成 `test_*.py ; 注释`），导致收集规则失效。面试手写时直接不写注释最稳。
