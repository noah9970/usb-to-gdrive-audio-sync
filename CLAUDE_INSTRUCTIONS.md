# 🤖 CLAUDE_INSTRUCTIONS.md - Claude Desktop開発ガイドライン

## ⚠️ 重要：このファイルは必ず最初に読んでください

このプロジェクトは**100% Claude Desktop + GitHub**で開発されます。
ローカル環境は使用しません。全ての作業はClaude DesktopからGitHub APIを通じて行います。

---

## 🎯 開発の基本原則

### 1. 開発環境
- **開発場所**: Claude Desktopのチャットのみ
- **コード管理**: GitHub（直接API経由で操作）
- **ローカル環境**: 使用しない
- **ターミナル**: 使用しない

### 2. 開発フロー
```
1. Claude Desktopで新しいチャットを開始
2. このファイル（CLAUDE_INSTRUCTIONS.md）を確認
3. README.mdから現在の開発状態を確認
4. GitHub APIで直接ファイルを作成・編集
5. 進捗をREADMEに記録
```

### 3. 必須確認事項
新しいチャットセッションを開始したら、必ず以下を実行：

1. **このファイルの内容を確認**
2. **README.mdの現在のフェーズを確認**
3. **最新のコミット履歴を確認**
4. **開発履歴セクションを確認**

---

## 📋 Claudeへの標準指示

### 開発開始時の動作

1. **リポジトリ情報の確認**
```python
# Claudeが自動的に実行すること：
- github:get_file_contents でこのファイルを読む
- github:get_file_contents でREADME.mdを読む
- github:list_commits で最新の状態を確認
```

2. **開発状態の把握**
```python
# README.mdから以下を確認：
- 現在の開発フェーズ
- 完了済みタスク
- 次のタスク
- 開発履歴
```

3. **作業の継続**
```python
# 前回の続きから開発：
- 未完了タスクから作業開始
- GitHub APIで直接ファイル操作
- 進捗をREADMEに更新
```

---

## 🚫 やってはいけないこと

1. **ローカル環境の使用を前提とした指示を出さない**
   - ❌ 「ターミナルで実行してください」
   - ❌ 「ローカルにcloneしてください」
   - ❌ 「venvを有効化してください」

2. **GitHub以外での作業を提案しない**
   - ❌ 「ファイルをダウンロードして編集」
   - ❌ 「エディタで開いて修正」

3. **手動作業を要求しない**
   - ✅ 全てGitHub API経由で自動実行

---

## ✅ 標準的な作業パターン

### ファイル作成
```python
# 常にGitHub APIを使用
github:create_or_update_file(
    owner="noah9970",
    repo="usb-to-gdrive-audio-sync",
    path="ファイルパス",
    content="内容",
    message="コミットメッセージ"
)
```

### ファイル確認
```python
# GitHubから直接読み込み
github:get_file_contents(
    owner="noah9970",
    repo="usb-to-gdrive-audio-sync",
    path="ファイルパス"
)
```

### 進捗更新
```python
# README.mdの開発履歴を更新
# 完了したタスクにチェック
# 次のフェーズへの移行を記録
```

---

## 📝 コミットメッセージ規約

必ず以下の形式を使用：
- `feat:` 新機能追加
- `fix:` バグ修正
- `docs:` ドキュメント更新
- `test:` テスト追加・修正
- `refactor:` リファクタリング
- `chore:` その他の変更

---

## 🔄 セッション開始テンプレート

ユーザーが新しいチャットで言うべきこと：
```
usb-to-gdrive-audio-syncプロジェクトの開発を続けます。
CLAUDE_INSTRUCTIONS.mdとREADME.mdを確認して、
現在のフェーズから開発を進めてください。
```

Claudeの応答：
```
承知しました。開発を続けます。
1. CLAUDE_INSTRUCTIONS.mdを確認中...
2. README.mdから現在の状態を確認中...
3. 現在のフェーズ: [Phase X]
4. 次のタスク: [タスク名]
開発を開始します。
```

---

## 📊 プロジェクト情報

- **リポジトリ**: https://github.com/noah9970/usb-to-gdrive-audio-sync
- **オーナー**: noah9970
- **開発方式**: Claude Desktop + GitHub API
- **ローカル環境**: 不要

---

## 🎯 このファイルの目的

このファイルは、Claudeが新しいチャットセッションでも一貫した開発方法を維持するための「永続的な指示書」です。
**必ず最初に読み、この方法に従って開発を進めてください。**

---

最終更新: 2025-09-19
バージョン: 1.0.0
