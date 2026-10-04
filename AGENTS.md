# 工作收尾与保存约定

- 用户已授权：以后每轮工作完成且核验通过后，先更新工作文档，再将本轮已完成的改动提交并推送至本代码仓库 `origin` 的对应目标分支，最后提交云端环境。无需每轮重复询问。
- 仅暂存本轮已完成且核验过的文件；保留其他未完成或用户已有改动。核对目标分支后正常推送，并读取远端分支 SHA 验证结果。
- Git 作者与提交者固定为 `ALIve114514awa <300349280+ALIve114514awa@users.noreply.github.com>`，提交前检查配置。
- 工作记录分别写明验证结果、Git 提交 SHA、推送仓库/分支及远端核验结果、云环境提交结果。文件存在或 Git 推送成功不能作为云环境快照已提交的证据。
- 云环境提供提交/保存快照接口时实际调用并核对结果；没有接口或提交失败时明确记录未提交，保留可恢复备份和未完成事项。
- 云环境中的共享工作文档位于 `/workspace`：`desktop-feature-reproduction-progress.md`、`desktop-feature-reproduction-playbook.md`、`desktop-android-feature-migration-plan.md`。存在时先读取；换环境时核对仓库外文档与未提交文件是否已携带。
