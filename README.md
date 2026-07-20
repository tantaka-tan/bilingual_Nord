# Bilingual Node Names for Blender

BlenderのGeometry Nodes／Shader Nodesを、英語と日本語の両方で扱いやすくするアドオンです。

ノードヘッダーを `English / 日本語` 形式で表示し、Blender標準のShift+A検索から英語名・日本語名のどちらでもノードを追加できます。表示を通常状態へ戻しても、二言語検索はそのまま利用できます。

## ダウンロード

[最新バージョンをGitHub Releasesからダウンロード](https://github.com/tantaka-tan/bilingual_Nord/releases/latest)

配布ファイル名:

```text
bilingual_node_names-0.2.0.zip
```

## 主な機能

- Geometry NodesとShader Nodesの主要ノードを `English / 日本語` で表示
- 標準Shift+Aメニューから英語名・日本語名で検索
- 日本語の別名・用途語に対応した独自検索
- 通常表示と日英表示の切替
- 通常表示中も二言語検索を維持
- 新規ノードへの自動適用
- 選択ノード、現在のノードツリーへの一括適用・復元
- 既存ユーザーラベルをデフォルトで保持
- Linkデータを変更しない非破壊設計

## 対応環境

- Blender 4.2以降
- Geometry Node Tree
- Shader Node Tree
- Windows／macOS／Linux

実機テスト済み:

- Blender 4.5.10 LTS
- Blender 5.2.0 LTS

## インストール

1. [Releases](https://github.com/tantaka-tan/bilingual_Nord/releases/latest)からZIPをダウンロードします。
2. Blenderで「編集 > プリファレンス」を開きます。
3. 「エクステンション」または「アドオン」画面のメニューから「ディスクからインストール」を選択します。
4. ダウンロードしたZIPを選択します。
5. `Bilingual Node Names`を有効にします。

ZIPは展開せず、そのまま選択してください。

## 使い方

### ノード名を日英表示する

Node Editorのサイドバーを`N`キーで開き、`Bilingual Nodes`タブから適用します。

- `Apply`: 選択ノードへ適用
- `Apply tree`: 現在のノードツリー全体へ適用
- `Restore`: 元のラベルへ復元

### 通常表示と切り替える

`Bilingual Nodes`パネル上部のボタンを使用します。

- `Use Standard Display / 通常表示へ`
- `Use Bilingual Display / 日英表示へ`

通常表示へ切り替えても、英語・日本語検索は無効になりません。

### ノードを検索する

- 標準Shift+Aメニュー上部の検索欄
- `Ctrl + Shift + A`の独自検索
- Shift+Aメニュー末尾の`Bilingual Search / 二言語検索`

例:

```text
Set Position
位置を設定
Noise Texture
ノイズテクスチャ
```

## 非破壊方針

本アドオンは表示のために`Node.label`のみを管理します。`node.name`、`bl_idname`、ノード接続、ソケット値は変更しません。

- 適用前のラベルをカスタムプロパティへ保存
- ユーザーが設定したラベルはデフォルトで上書きしない
- 手動編集を検出した場合は管理対象から解除
- Linkデータは読み取り専用としてスキップ

## 開発とテスト

通常テスト:

```powershell
.\blender.exe --background --factory-startup --python tests\run_blender_tests.py
```

実ノード生成、Operator、データ不変性、全辞書エントリ、破損辞書、1,000ノード性能を含む厳格テスト:

```powershell
.\blender.exe --background --factory-startup --python tests\run_strict_integration.py -- --scenario core
```

GUI検索とUndoのテストスクリプトも`tests/`へ収録しています。

## ライセンス

GPL-3.0-or-later
