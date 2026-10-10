# A 部分实现与验证记录

验证日期：2026-10-09。

## 实现内容

- 公共 `PublicKey → ScanReport` 接口和 JSONL/JSON 文件接口。
- 两两 GCD 与乘积树／平方模数余数树批量 GCD。
- 按模数去重，保留 ID、每条记录的指数与重复分组。
- 非平凡因子检查与规范化。
- 全重叠结果的回退拆分和全局回退预算。
- 协作式超时与清晰的命令行退出码。
- Python 标准库和可选 gmpy2 后端。
- 各阶段耗时、总扫描耗时和 GCD 调用次数。
- 面向 B 的接口说明和 A 的演讲材料。

## 测试环境

| 项目 | 本次环境 |
|---|---|
| 操作系统 | Windows 11，build 26200 |
| Python | 3.13.3 |
| gmpy2 | 2.3.2 |
| PyCryptodome | 3.24.0 |
| 测试框架 | Python 标准库 unittest |

核心扫描器不需要外部库。缺少 gmpy2 时，加速后端测试跳过；缺少 PyCryptodome 时，OAEP 集成测试跳过。安装 `requirements-validation.txt` 中的版本可复现完整验证环境。

## 运行方式

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m rsa_audit tests/fixtures/rsa2048_public.jsonl --backend gmpy2 --output results/rsa2048_batch.json
.\.venv\Scripts\python.exe -m rsa_audit tests/fixtures/rsa2048_public.jsonl --method pairwise --backend gmpy2 --output results/rsa2048_pairwise.json
```

共 26 个测试方法。随机测试还在内部对 60 组随机半素数集合分别运行两种算法，并用独立的两两比较 oracle 核对，覆盖不同长度、重复关系和全重叠结构。

## 固定 2048-bit 样本

文件：`tests/fixtures/rsa2048_public.jsonl`。

SHA-256：

```text
47f54e41523226931c960e84111cfe1361c976b89d5340b075cb5a1c137003fe
```

测试样本使用 PyCryptodome 生成不同的 1024-bit 素数，再按已知关系组合；检查指数互素，并将素数限制在足够高的区间，保证所有模数实际为 2048 bit。固定文件保存在仓库中，复测不需要重新生成。

| 指标 | 预期且已验证的值 |
|---|---|
| 公钥记录数 | 16 |
| 不同模数数 | 14 |
| 额外重复记录数 | 2 |
| 成功分解的不同模数 | 6 |
| 对应成功分解的原始记录 | 7 |
| 未发现共享因子的不同模数 | 8 |
| batch 初始全重叠模数 | 4 |
| 完成默认回退后的未拆分模数 | 0 |

样本包含双因子分别被其他模数共享的结构、三角共享结构、独立对照和重复记录。测试对 Python/gmpy2、batch/pairwise 组合核对恢复集合及因子乘积。

## OAEP 集成验证

`tests/test_real_size.py` 中的集成测试执行：

1. 读取固定公开密钥集合。
2. 执行检测，获取目标模数的因子。
3. 计算私钥指数，并调用密码库的密钥一致性检查。
4. 解密 `rsa2048_oaep_challenge.json` 中的 OAEP-SHA-256 密文。
5. 核对明文 SHA-256 与预期摘要。

这里的密钥一致性检查由 PyCryptodome 完成。测试不读取生成时的素数或私钥；密文文件只包含公开的算法参数和验证摘要。

## 范围限制

- 26 项测试包含正确性、文件处理和命令行验证，不是一般 RSA 安全性的证明。
- 该固定样本只含 14 个不同模数，不能用于声称批量算法在大规模场景的加速倍数。
- 正式性能比较仍由 B 在控制数据规模、弱密钥比例、后端和回退情况后完成。
- 未进行公网扫描，所有真实尺寸验证均使用本地构造的实验公钥。
- 本机 Codex 沙箱与 Python 3.13 私有临时目录权限存在兼容问题，文件类测试在允许的本地执行环境运行；算法和普通 CLI 也单独完成了执行验证。

测试原始输出保存在本地 `results/unittest.txt`，CLI 扫描报告保存在 `results/`。该目录默认不提交，由团队决定正式实验产物的归档方式。
