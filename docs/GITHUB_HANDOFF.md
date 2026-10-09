# GitHub 上传与两人整合

## 应使用哪个目录

最终整合仓库是 `D:\ntu\104\group\SC6104-Cryptography-Coursework`，本地分支为 `b-integration`。它基于队友的 `main` 提交 `9352086`，B 实验真正调用 A 的 `rsa_audit.scan_keys`。上一级 `D:\ntu\104\group` 中的早期 B 独立版本、环境和安装包继续作为本地备份，不应整体上传。

此文档提供提交步骤，不表示已经推送或建立 PR。推送前先检查 Git 状态；若队友又更新 main，应先拉取并检查差异，在整合分支处理，避免覆盖队友的新内容。

## 要传到仓库的内容

| 内容 | 用途 |
|---|---|
| `rsa_lab/` | B 的完整数据、恢复、OAEP、评估、实验、对照与命令入口 |
| `tests/test_ab_handoff.py` 及新增 B 测试 | 验证接口交接和完整流程，共 70 项 Python 测试 |
| `presentation/final.html`、`assets/final-*`、`embed/` | 全英文 8 页离线总展示；嵌入 A 动画 |
| `artifacts/` 整个目录 | 实测 CSV、图表、公开 demo、验证结果、环境与完整性哈希 |
| `scripts/`、`run_demo.cmd` | 安装、运行、验证、实验和结果导出入口 |
| `docs/` 中新增和更新的文档 | 英文讲稿、B 代码理解、接口整合、交接和 PR 描述 |
| `README.md`、`START_HERE.md`、依赖与配置文件 | 新机器使用与跨平台行尾配置 |

A 的 `rsa_audit/` 源码、原有测试、固定样本和原动画资产保留在最终仓库中。这次整合没有改写 A 的算法。使用 Git 的差异列表提交新增与修改文件即可，无需重新手工拼接目录。

不用传 `.venv/`、`vendor/`、`data/`、`results/`、`work/`、`__pycache__/`、私钥 PEM、`ground_truth.json`、`new_private_parameters.json` 和本地安装包。`.gitignore` 已配置相应排除。`artifacts/` 是特意挑选的轻量公开结果，应该上传；不要将它与本地 `results/` 混淆。

## 推送前与队友确认

先一起查看 `START_HERE.md`、`docs/INTEGRATION.md` 和 `presentation/final.html`。A 重点检查扫描状态、去重、回退、计时适配和原动画；B 重点检查数据真值隔离、私钥恢复、OAEP 参数、对照实验及图表含义。两人都要能回答对方模块的基本问题。

确认后在上述仓库内执行：

```powershell
git status --short
git diff --cached --stat
git diff --cached --check
# 如果又修改了文件，先查看差异，然后更新暂存区。
git add .
..\.venv\Scripts\python.exe -X utf8 scripts/verify_showcase.py --git-index
git commit -m "Integrate B RSA recovery experiments and English showcase"
git push -u origin b-integration
```

在 GitHub 创建 `b-integration` → `main` 的草稿 PR，标题与正文可直接参考 `docs/PR_DESCRIPTION.md`。队友复查后再合并；整合阶段推荐先推分支。不要使用强制推送。

上面的验证命令使用本机上一层已有的环境；其他目录使用仓库自己的 `.\.venv\Scripts\python.exe`。`verify_showcase.py` 检查全部归档哈希，并只用归档公钥、扫描结果和密文重新解密 6 条消息；`--git-index` 还检查暂存后的文件字节，避免换行转换破坏归档。

## 队友在另一台电脑复现

```powershell
git fetch origin
git switch --track origin/b-integration
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 -m rsa_lab demo
.\.venv\Scripts\python.exe -X utf8 -m rsa_lab validate
```

若已存在本地同名分支，切换已有分支后普通拉取即可。直接打开 `presentation/final.html` 就能看保存的展示证据，无需运行服务器。新克隆的首次 demo 会生成受控随机样本；结构和预期结果相同，素数与时间不保证逐字相同。

正式性能复测按 README 的 `prepare-bench → benchmark → plot → pool-experiment → run_tests.ps1 → report → export_showcase.py` 顺序；先执行 `demo → validate`。`run_tests.ps1` 同时保存导出所需的成功测试日志。不要只重新生成数据，却继续把旧实测数字说成新输入的结果。每次完整导出会更新 `artifacts/` 和网页数据，提交前再次查看差异。

## 合并后一起准备

1. 按 `docs/PRESENTATION.md` 排练完整 8 分钟，包括真实 Python demo 和切回浏览器的时间。主页面中的演示按钮展示已保存记录；现场攻击由 `run_demo.cmd` 执行。
2. B 讲第 1、5、6、8 页；A 讲第 2、3、4、7 页，并在第 6 页解释 OAEP。代码学习顺序见 `docs/B_CODE_GUIDE.md`。
3. 两人互问：为什么模数平方、为何要去重、全重叠为何回退、`d` 如何求出、OAEP 是否被破解、孤立目标为何恢复失败、超时与计时范围如何解释。
4. 在上课电脑再运行一次 demo，确认离线页面、环境和全屏；准备已保存证据作为现场运行故障时的备用，并明确说明其来源。

最终结论要准确：2048 位不能防止共享素因子攻击；当前集合未检出共享因子只说明这一关系没有被观察到；更换密钥不能挽回旧私钥和旧密文的泄露。
