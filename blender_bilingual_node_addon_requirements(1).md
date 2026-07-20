# Blender Bilingual Node Names Add-on
## 実装要件定義書

- 文書名: Blender ジオメトリノード／シェーダーノード日英併記・二言語検索アドオン 実装要件定義書
- 仮称: **Bilingual Node Names**
- 文書バージョン: 1.0
- 作成日: 2026-07-20
- 対象読者: Blender Pythonアドオン開発者、UI/UX設計者、翻訳データ作成者、QA担当者
- 実装可否: **実装可能**
- 主要実装方式: Blender標準ノードの `Node.label` を利用した表示名上書き + 独自検索Operator
- 主要表示形式: `English / 日本語`

---

# 1. 結論

本要件は、Blender Python APIを使用して実装可能である。

ただし、Blender標準ノード型のクラス表示名そのものを安全かつ恒久的に書き換えるのではなく、各ノードインスタンスの `label` に `English / 日本語` を設定し、ノードヘッダーへ表示する方式を正式採用する。

検索については、Blender標準の検索データ構造を直接改変せず、英語名、日本語名、別名、用途語から検索できる独自Operatorを実装する。

## 1.1 実装可能な主要機能

- Geometry Nodesのノードヘッダーを `English / 日本語` で表示
- Shader Nodesのノードヘッダーを `English / 日本語` で表示
- 英語名でのノード検索
- 日本語名でのノード検索
- 日本語の同義語・用途語による検索
- 検索結果からノードを追加
- 新規追加ノードへの自動ラベル適用
- 既存ノードへの一括適用
- 元ラベルの保存と復元
- 翻訳未登録ノードの診断
- Blenderバージョン別翻訳定義
- ユーザー翻訳辞書
- 選択ノード、現在のノードツリー、ファイル全体への適用

## 1.2 制約を伴う機能

以下は実装可能だが、Blenderのバージョン変更や標準UIとの競合リスクがある。

- 標準 `Shift + A` を独自検索へ置き換える
- 標準追加メニューの全項目を日英併記へ差し替える
- ノード追加を完全にリアルタイム検知する
- Mathなどの設定依存タイトルを常時同期する
- Blender標準UIをファイル非破壊で直接再描画する

これらは「実験的機能」または第2段階以降とする。

## 1.3 初期版で行わないこと

- Blender内部のノード型IDの変更
- `node.name` を二言語文字列へ一律変更
- 標準ノードクラスの `bl_label` をランタイムで一括改変
- 標準ソケット名の直接書き換え
- AIによる自動翻訳を保存時に実行
- Link元ライブラリデータの強制変更
- ノードエディターの描画処理をC/C++レベルで差し替える

---

# 2. 背景と目的

Blenderのノード学習では、日本語UIを利用する初心者と、英語名を前提とした海外教材・技術情報の間に名称の不一致がある。

本アドオンでは、ノード名を常に次の形式で表示する。

```text
Set Position / 位置を設定
Map Range / 範囲をマッピング
Principled BSDF / プリンシプルBSDF
Separate Color / カラーを分離
```

これにより、ユーザーは日本語で意味を理解しながら、英語の正式名称を同時に学習できる。

## 2.1 製品目的

1. 日本語話者がノードを発見しやすくする
2. 英語チュートリアルとの対応関係を明確にする
3. ノードの正式英語名を自然に習得できるようにする
4. 日本語・英語の両方でノード検索を可能にする
5. Blender標準ノード処理への影響を最小化する
6. `.blend` ファイルを他環境へ渡しても併記ラベルを確認できるようにする

## 2.2 非目的

- Blender全UIの二言語化
- Blender公式翻訳の置換
- ノードの機能説明教材そのものの提供
- ノード接続の自動生成
- 自然言語から完全なノードツリーを生成
- Blender標準検索を内部的に改造すること

---

# 3. 対応環境

## 3.1 必須対応バージョン

MVPの正式対応対象:

- Blender 4.2 LTS
- Blender 4.5 LTS

開発時の互換確認対象:

- Blender 4.3
- Blender 4.4
- Blender 5.x系

## 3.2 対応方針

`bpy.app.version` を使用して実行中バージョンを判定する。

```python
major, minor, patch = bpy.app.version
```

バージョン固有差分は `compat/` モジュールへ隔離する。

## 3.3 対応OS

Blender Python API上で動作するため、原則として以下を対象とする。

- Windows 10/11
- macOS
- Linux

MVPのQA優先環境はWindows 11とする。

---

# 4. 対象ノードツリー

## 4.1 MVP正式対応

### Geometry Nodes

```python
tree.bl_idname == "GeometryNodeTree"
```

対象例:

- Modifier内のGeometry Nodes
- ノードグループ
- Geometry Node Tool
- アセットとして保存されたGeometry Nodesグループ

### Shader Nodes

```python
tree.bl_idname == "ShaderNodeTree"
```

対象例:

- Material
- World
- Light
- Line Style（バージョン・環境に応じて）
- Shader Node Group

## 4.2 将来対応

- Compositor Node Tree
- Texture Node Tree
- Simulation関連の追加ノード環境
- 外部アドオン由来のカスタムノードツリー

## 4.3 対象外

- Animation Nodesなど、独自描画や独自追加処理を強く持つ外部システム
- 読み取り専用のLinkデータ
- Blender側で編集不能な一時ノードツリー

---

# 5. 表示仕様

## 5.1 基本表示

```text
English / 日本語
```

区切り文字は半角スラッシュとし、前後に半角スペースを1つ入れる。

```python
display_label = f"{english} / {japanese}"
```

## 5.2 初期設定

- 表示順: English / 日本語
- 区切り: ` / `
- 英語名: Blender標準英語名
- 日本語名: アドオン辞書の日本語名
- 日本語未登録時: 英語名のみ
- 英語名未取得時: `bl_idname`
- 長いラベルによるノード幅変更: OFF

## 5.3 設定可能な表示モード

```text
English / 日本語
日本語 / English
Englishのみ
日本語のみ
```

MVPのデフォルトと主目的は `English / 日本語` である。

## 5.4 ノード表示への適用方式

`Node.label` を使用する。

```python
node.label = "Set Position / 位置を設定"
```

Blenderではラベルが空でないノードは、ノード型の既定タイトルに代わってラベルが表示される。

## 5.5 変更してはならない値

原則として次を変更しない。

```python
node.name
node.bl_idname
node.type
node.bl_label
```

理由:

- `node.name` はPythonスクリプトや他アドオンから参照される可能性がある
- `bl_idname` は型識別子であり変更対象ではない
- `type` はノード種類を示す
- `bl_label` はノードクラス側の情報であり、個別ノード表示の安全な変更手段ではない

---

# 6. ラベル管理仕様

## 6.1 管理用カスタムプロパティ

アドオンが管理するノードには次を保存する。

```python
node["_bn_managed"] = True
node["_bn_schema_version"] = 1
node["_bn_node_type"] = node.bl_idname
node["_bn_original_label"] = original_label
node["_bn_generated_label"] = generated_label
node["_bn_translation_revision"] = translation_revision
```

実際のキー名は衝突を避けるため、アドオン固有prefixを使用する。

## 6.2 元ラベルの保存

初回適用時のみ元の `node.label` を保存する。

再適用のたびに元ラベルを上書きしてはならない。

```python
if "_bn_original_label" not in node:
    node["_bn_original_label"] = node.label
```

## 6.3 ユーザーラベルとの競合方針

デフォルト:

- ラベルが空の既存ノード: 適用する
- ラベルが空でない既存ノード: 適用しない
- アドオンが以前設定したラベル: 更新可能
- ユーザーがアドオン生成後に編集したラベル: 管理対象から外す
- 強制上書き: 設定で明示的に有効化した場合のみ

## 6.4 ユーザー編集検出

現在の `node.label` と `_bn_generated_label` を比較する。

```python
if node.get("_bn_managed") and node.label != node.get("_bn_generated_label"):
    # ユーザーが編集した可能性
```

デフォルト動作:

1. `_bn_managed` をFalseへ変更
2. ユーザー編集ラベルを保持
3. 診断ログへ「手動編集により管理解除」と記録

## 6.5 強制モード

設定名:

```text
既存のユーザーラベルを上書き
```

デフォルト: OFF

ONの場合も、元ラベルを保存して復元可能にする。

## 6.6 復元

復元Operatorは管理対象ノードのみを処理する。

```python
node.label = node.get("_bn_original_label", "")
```

復元後、管理用カスタムプロパティを削除する。

---

# 7. 翻訳データ仕様

## 7.1 キー

ノードの内部IDで管理する。

例:

```text
GeometryNodeSetPosition
ShaderNodeBsdfPrincipled
ShaderNodeMath
ShaderNodeVectorMath
```

表示名文字列を辞書キーにしてはならない。

## 7.2 JSONスキーマ

```json
{
  "schema_version": 1,
  "translation_revision": "2026.07.20",
  "nodes": {
    "GeometryNodeSetPosition": {
      "english": "Set Position",
      "japanese": "位置を設定",
      "japanese_short": "位置を設定",
      "tree_types": ["GeometryNodeTree"],
      "category_en": "Geometry",
      "category_ja": "ジオメトリ",
      "aliases_en": [
        "move points",
        "change position",
        "offset position"
      ],
      "aliases_ja": [
        "位置",
        "座標",
        "移動",
        "頂点を移動",
        "ポイントを動かす"
      ],
      "description_ja": "選択したポイントの位置を変更します。",
      "min_version": [3, 0, 0],
      "max_version": null,
      "dynamic_title": null
    }
  }
}
```

## 7.3 翻訳優先順位

1. ユーザー辞書
2. バージョン別オーバーライド辞書
3. アドオン標準辞書
4. Blenderから取得した日本語翻訳
5. 英語名のみ

Blender公式翻訳を補助的に取得する場合でも、検索品質を保証するためアドオン標準辞書を主データとする。

## 7.4 辞書ファイル分割

推奨構成:

```text
translations/
├── schema.json
├── geometry_nodes_ja.json
├── shader_nodes_ja.json
├── dynamic_operations_ja.json
├── aliases_ja.json
├── overrides/
│   ├── blender_4_2.json
│   ├── blender_4_5.json
│   └── blender_5_x.json
└── user/
    └── user_translations.json
```

## 7.5 辞書検証

起動時または設定画面から以下を検証する。

- JSON構文
- 必須キー
- 重複ID
- 空文字
- 対応バージョン
- 未知のtree type
- 不正なdynamic_title定義
- 同義語の重複
- 不正な文字コード

辞書エラーがあってもアドオン全体を停止せず、その項目だけ除外する。

---

# 8. 動的ノードタイトル

一部ノードは、ノード種類より現在の設定値がタイトルとして重要になる。

対象例:

- Math
- Vector Math
- Mix
- Compare
- Boolean Math
- Rotate系
- Data Type切替を持つノード
- Input/Store Named Attribute
- Switch
- Function Node群

## 8.1 表示モード

### 型名固定

```text
Math / 数式
```

### 演算名

```text
Multiply / 乗算
```

### 型名 + 演算名

```text
Math: Multiply / 数式：乗算
```

MVP推奨:

- Math: 演算名表示
- Vector Math: 演算名表示
- Boolean Math: 演算名表示
- Compare: 比較演算名表示
- その他: 型名固定

## 8.2 動的定義例

```json
{
  "ShaderNodeMath": {
    "dynamic_title": {
      "property": "operation",
      "mode": "operation_only",
      "values": {
        "ADD": {
          "english": "Add",
          "japanese": "加算"
        },
        "MULTIPLY": {
          "english": "Multiply",
          "japanese": "乗算"
        }
      }
    }
  }
}
```

## 8.3 同期方式

MVP:

- ノード追加時
- ファイル読込時
- 手動「ラベル更新」実行時
- 独自検索から追加した直後

第2段階:

- プロパティ変更検出による自動同期

常時監視は更新頻度と安定性を検証してから有効化する。

---

# 9. 検索機能

## 9.1 基本要件

英語・日本語の両方から検索できる独自検索Operatorを提供する。

検索対象:

- 英語正式名
- 日本語正式名
- 英語短縮名
- 日本語短縮名
- 英語別名
- 日本語別名
- 英語カテゴリー
- 日本語カテゴリー
- ノード内部ID
- 日本語説明文
- 動的演算名
- ノードグループ名
- ユーザー登録名

## 9.2 検索UI

推奨Operator:

```python
class BN_OT_search_add_node(bpy.types.Operator):
    bl_idname = "node.bn_search_add_node"
    bl_label = "Bilingual Node Search"
```

呼び出し:

```python
context.window_manager.invoke_search_popup(self)
```

候補表示:

```text
Set Position / 位置を設定
Map Range / 範囲をマッピング
Vector Math: Dot Product / ベクトル演算：内積
```

## 9.3 検索結果データ

検索候補の内部値には表示名ではなく安定IDを持たせる。

```text
GeometryNodeSetPosition
ShaderNodeMapRange
ShaderNodeMath::MULTIPLY
NODE_GROUP::<node_tree_uuid>
```

## 9.4 検索正規化

- 大文字・小文字を区別しない
- Unicode NFKC正規化
- 全角英数字を半角化
- 連続スペースを1つへ
- 前後空白を除去
- `/`, `-`, `_` を検索上の区切りとして扱う
- カタカナ・ひらがなの検索補助
- 長音符の揺れを補助
- 英語複数形や単純な語尾差を必要に応じて補助

## 9.5 スコアリング

推奨順位:

1. 正式名完全一致
2. 正式名前方一致
3. 正式名単語一致
4. 内部ID一致
5. 別名完全一致
6. 別名前方一致
7. 部分一致
8. 説明文一致
9. あいまい一致
10. 最近使用
11. お気に入り

検索スコア例:

```python
EXACT_NAME = 1000
PREFIX_NAME = 800
TOKEN_NAME = 650
EXACT_ALIAS = 600
PREFIX_ALIAS = 500
SUBSTRING = 350
DESCRIPTION = 150
```

## 9.6 コンテキストフィルタ

現在のノードエディターに追加可能なノードだけ表示する。

判定情報:

- `space.tree_type`
- `space.shader_type`
- 編集中ノードツリーの `bl_idname`
- Blenderバージョン
- ノード型の登録有無
- `Node.poll`相当の利用可否
- Material / World / Lightの文脈

## 9.7 ノード追加

推奨方式:

1. 現在のNode Editorを確認
2. 対象ノード型を検証
3. `nodes.new(type=node_bl_idname)` で追加
4. マウス位置またはビュー中央へ配置
5. 選択状態を更新
6. 二言語ラベルを適用
7. 必要なら動的プロパティを設定
8. Undo対象として記録

標準 `bpy.ops.node.add_node` を利用する方式と、RNA APIで `nodes.new` する方式を比較検証すること。

MVPでは、コンテキスト依存を抑えやすい `nodes.new` を基本とし、標準ノード追加特有の初期化が必要な型のみOperator経由に分岐する。

---

# 10. Shift + Aとの統合

## 10.1 安定モード（MVP）

標準 `Shift + A` は変更しない。

追加方法:

- Nパネルの検索ボタン
- Node Editorのメニュー項目
- 専用ショートカット
- `Shift + A` メニュー末尾に「Bilingual Search / 二言語検索」を追加

推奨専用ショートカット:

```text
Ctrl + Shift + A
```

## 10.2 置換モード（実験的）

ユーザー設定で有効にした場合のみ、Node Editor内の `Shift + A` を独自検索へ割り当てる。

要件:

- 元キーマップを削除しない
- アドオン無効化時に確実に復元
- キーマップ競合を診断
- Blender標準メニューを開く代替操作を残す
- Preferencesに警告を表示

## 10.3 標準メニュー全置換

初期版では実装しない。

理由:

- Blenderバージョンごとのメニュー構成差
- Asset Menuとの統合
- ノードカテゴリーAPIの変化
- 他アドオンが追加した項目との競合
- 標準検索の文脈依存処理を再現するコスト

---

# 11. 新規ノード自動適用

## 11.1 適用対象

- 標準追加メニュー
- 標準検索
- 独自検索
- 複製
- コピー＆ペースト
- Python追加
- Append
- ノードグループ追加
- Asset Browser追加

## 11.2 MVP方式

完全なイベントフックに依存せず、複数の安全なタイミングで差分走査する。

- `load_post`
- Node Editor操作後の明示更新
- 独自Operatorでの追加直後
- Nパネル表示時の軽量確認
- タイマーによる低頻度差分チェック（設定可能）

## 11.3 キャッシュ

ノードツリーごとに次を保持する。

```python
tree_key -> {
    "node_count": int,
    "known_node_pointers": set[int],
    "last_scan_time": float,
    "translation_revision": str
}
```

`node.as_pointer()` は実行セッション内キャッシュ用途に限定し、`.blend` への永続IDとしては使わない。

## 11.4 タイマー

自動検出を有効にする場合:

- 初期値: 0.5〜1.0秒間隔
- Node Editorが存在しない場合は頻度を低下
- 変更がない場合はバックオフ
- ファイル読込・終了中は処理しない
- 1回の処理件数に上限を設ける

## 11.5 禁止事項

- 毎フレーム全ノード走査
- `depsgraph_update_post` ごとの全データ走査
- UI `draw()` 内で全ファイルを走査
- 翻訳JSONを毎回開く
- 全ノードへ無条件にlabelを書き戻す

---

# 12. 一括適用Operator

## 12.1 必須Operator

```text
選択ノードへ適用
現在のノードツリーへ適用
現在のマテリアルへ適用
ファイル全体へ適用
選択ノードを復元
現在のノードツリーを復元
ファイル全体を復元
管理ラベルを更新
```

## 12.2 ファイル全体の列挙対象

- `bpy.data.materials`
- `bpy.data.worlds`
- `bpy.data.lights`
- `bpy.data.node_groups`
- その他対応tree typeを持つID datablock

## 12.3 実行前プレビュー

ファイル全体適用時は確認ダイアログを表示する。

```text
対象ノードツリー: 36
対象ノード: 1,248
変更予定: 1,032
ユーザーラベルにより除外: 184
翻訳未登録: 32
読み取り専用: 5
```

## 12.4 大規模処理

1,000ノード以上ではチャンク処理を検討する。

- 1チャンク: 100〜500ノード
- 進捗表示
- キャンセル対応
- 部分完了ログ
- 再実行可能

---

# 13. ノードグループ

## 13.1 標準ノードグループインスタンス

ノードグループの表示名はユーザー定義名を尊重する。

デフォルト動作:

```text
My Shader Group
```

翻訳登録がある場合:

```text
My Shader Group / マイシェーダーグループ
```

## 13.2 自動翻訳

初期版では行わない。

固有名詞、商品名、プロジェクト名を誤訳する危険があるため。

## 13.3 ユーザー登録

ノードグループ用辞書を別管理する。

識別候補:

- ノードグループ名
- Library path + name
- アドオン付与UUID
- Asset catalog情報

ローカル編集可能グループにはUUIDカスタムプロパティを付与可能。

## 13.4 Group Input / Group Output

標準ノードとして翻訳する。

例:

```text
Group Input / グループ入力
Group Output / グループ出力
```

## 13.5 インターフェースソケット

MVPでは実際のソケット名を書き換えない。

将来的にNパネル上で日英対応を表示する。

---

# 14. LinkデータとLibrary Override

## 14.1 Linkデータ

`id_data.library is not None` などで読み取り専用状態を判定する。

デフォルト:

- 直接変更しない
- スキップ件数を診断表示
- エラーではなく警告扱い

## 14.2 Library Override

デフォルト: 変更しない

Preferencesで明示的に許可した場合のみ適用候補にする。

理由:

- 表示目的の変更がOverride差分として大量記録される
- チーム運用へ影響する
- 外部ライブラリ更新との競合が生じる

## 14.3 Append

Appendされたローカルデータは通常のローカルデータとして処理可能。

---

# 15. Undo / Redo

## 15.1 手動Operator

`bl_options = {'REGISTER', 'UNDO'}` を設定する。

対象:

- ノード追加
- 選択ノード適用
- 現在ツリー適用
- ファイル全体適用
- 復元
- 強制更新

## 15.2 自動処理

自動ラベル変更が独立したUndo履歴を大量生成しないようにする。

MVP方針:

- 独自検索からの追加は追加処理内でラベル設定
- 標準追加後の自動検出はUndo履歴挙動を実機検証
- 不安定な場合、自動検出は「保留変更」としてまとめて適用
- Undo/Redo中は監視を一時停止し、完了後に差分再構築

## 15.3 Undo後のキャッシュ

Undo/Redo後はノードpointerキャッシュを破棄し、現在ツリーを再走査する。

---

# 16. 保存ファイルへの影響

## 16.1 保存される情報

- `node.label`
- 管理用カスタムプロパティ
- 必要に応じてノードグループUUID
- アドオン固有設定（SceneやWindowManagerではなくPreferences中心）

## 16.2 利点

アドオンがない環境でも `English / 日本語` ラベルが表示される。

## 16.3 影響

- `.blend` が更新扱いになる
- Git/LFS差分が発生する
- チーム内で表示方針が共有される
- アセットに管理用プロパティが保存される
- ラベルがスクリプト参照されている特殊環境では影響し得る

## 16.4 非破壊方針

- `node.name` は変更しない
- 元ラベルを保存する
- 一括復元を提供する
- ユーザーラベルをデフォルトで上書きしない
- 読み取り専用データを変更しない

## 16.5 アドオン無効化時

自動復元しない。

理由:

- アドオン無効化だけでユーザーファイルを大量変更するべきではない
- 保存済み表示を残したいユーザーがいる
- 復元は明示Operatorで行う

Preferencesに次を説明する。

```text
アドオンを無効化しても、すでにノードへ保存された二言語ラベルは残ります。
解除する場合は、無効化前に「ファイル全体を復元」を実行してください。
```

---

# 17. UI要件

## 17.1 Nパネル

タブ名:

```text
Bilingual Nodes
```

日本語UI表示:

```text
二言語ノード
```

## 17.2 パネル構成

### 選択ノード

- 英語名
- 日本語名
- 現在の表示ラベル
- ノード内部ID
- ノードツリー型
- 翻訳登録状態
- 管理状態
- 元ラベル
- 適用ボタン
- 復元ボタン
- 管理解除ボタン

### 現在のツリー

- ノード数
- 管理対象数
- 未登録数
- ユーザーラベル数
- 適用
- 更新
- 復元
- 検索

### 診断

- 未登録ノード
- 読み取り専用ノード
- 辞書エラー
- キーマップ競合
- 最終走査時間
- キャッシュ再構築

## 17.3 Preferences

### 表示

- 表示順
- 区切り文字
- 短縮日本語名を使用
- 動的演算名を使用
- ノード幅を自動調整
- 最大自動幅

### 自動適用

- 新規ノードへ自動適用
- ファイル読込時に適用
- 標準追加後の差分監視
- ユーザーラベルを上書き
- 手動編集時に管理解除
- Library Overrideを対象に含む

### 検索

- 英語検索
- 日本語検索
- 同義語検索
- 用途語検索
- あいまい検索
- 最近使用を優先
- お気に入りを優先

### キーマップ

- 専用検索キー
- Shift+A置換モード
- 標準追加メニューへの項目追加

### 翻訳

- ユーザー辞書パス
- 辞書再読込
- 辞書検証
- 未登録ノード書き出し
- ユーザー辞書インポート／エクスポート

---

# 18. モジュール構成

```text
bilingual_node_names/
├── __init__.py
├── addon_info.py
├── preferences.py
├── constants.py
├── properties.py
├── operators/
│   ├── __init__.py
│   ├── search_add.py
│   ├── apply_labels.py
│   ├── restore_labels.py
│   ├── refresh_labels.py
│   ├── diagnostics.py
│   └── translation_io.py
├── services/
│   ├── __init__.py
│   ├── label_service.py
│   ├── search_service.py
│   ├── translation_service.py
│   ├── node_registry.py
│   ├── node_tree_scanner.py
│   ├── dynamic_title_service.py
│   ├── cache_service.py
│   └── diagnostic_service.py
├── handlers/
│   ├── __init__.py
│   ├── load_handlers.py
│   ├── undo_handlers.py
│   └── timer_handlers.py
├── ui/
│   ├── __init__.py
│   ├── panels.py
│   ├── menus.py
│   └── lists.py
├── keymaps/
│   ├── __init__.py
│   └── node_editor_keymap.py
├── translations/
│   ├── geometry_nodes_ja.json
│   ├── shader_nodes_ja.json
│   ├── dynamic_operations_ja.json
│   └── overrides/
├── compat/
│   ├── __init__.py
│   ├── blender_4_2.py
│   ├── blender_4_5.py
│   └── blender_5_x.py
├── schemas/
│   └── translation.schema.json
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

---

# 19. 主要クラスと責務

## 19.1 TranslationService

責務:

- JSON読込
- バージョン適合判定
- ユーザー辞書マージ
- 翻訳取得
- 動的演算翻訳取得
- スキーマ検証
- revision管理

主要メソッド案:

```python
get_node_entry(bl_idname, blender_version)
get_display_names(node, context)
get_aliases(bl_idname)
reload()
validate()
```

## 19.2 LabelService

責務:

- 表示ラベル生成
- 適用可否判定
- 元ラベル保存
- ラベル適用
- ラベル復元
- ユーザー編集検出
- 管理プロパティ整理

主要メソッド案:

```python
build_label(node, preferences)
can_apply(node, policy)
apply(node, policy)
restore(node)
refresh(node)
release_management(node)
```

## 19.3 SearchService

責務:

- 検索インデックス生成
- 入力正規化
- スコアリング
- コンテキストフィルタ
- 最近使用・お気に入り統合
- 検索結果返却

主要メソッド案:

```python
rebuild_index()
normalize_query(text)
search(query, context, limit=50)
record_usage(node_id)
```

## 19.4 NodeRegistry

責務:

- Blenderに登録されているノード型の収集
- `bl_idname` と表示名の対応
- tree type適合情報
- バージョン別ノード存在確認
- 未登録ノード診断

## 19.5 NodeTreeScanner

責務:

- 現在のノードツリー走査
- ファイル全体走査
- 差分検出
- Link/Override判定
- チャンク処理

## 19.6 DynamicTitleService

責務:

- Mathなどの現在値読取
- operation enumから日英名取得
- 動的タイトル生成
- 未知のenum値フォールバック

## 19.7 DiagnosticService

責務:

- 警告・エラー収集
- 未登録ノード一覧
- 辞書エラー
- 読み取り専用スキップ
- キーマップ競合
- ログ書き出し

---

# 20. 主要処理フロー

## 20.1 アドオン登録

1. クラス登録
2. Preferences登録
3. 翻訳辞書読込
4. NodeRegistry構築
5. Search index構築
6. UI登録
7. Keymap登録
8. `load_post` handler登録
9. 必要ならtimer登録
10. 診断状態初期化

## 20.2 ファイル読込

1. キャッシュ破棄
2. Blenderバージョン確認
3. ノードツリー列挙
4. 管理済みラベルの整合性確認
5. ユーザー編集検出
6. 設定がONなら空ラベルへ適用
7. 翻訳revision差分を記録
8. 未登録ノードを診断へ追加

## 20.3 独自検索から追加

1. 検索Popup起動
2. 候補取得
3. 候補選択
4. 編集中tree確認
5. ノード追加
6. 必要な初期プロパティ設定
7. マウス位置へ配置
8. 二言語ラベル適用
9. 使用履歴更新
10. Undo可能な状態で終了

## 20.4 現在ツリー一括適用

1. tree取得
2. 読み取り専用判定
3. 各ノードの適用可否判定
4. 元ラベル保存
5. 表示ラベル生成
6. ラベル書込
7. 管理情報保存
8. 集計表示

## 20.5 復元

1. 管理対象判定
2. 元ラベル取得
3. `node.label` 復元
4. 管理プロパティ削除
5. キャッシュ更新
6. 集計表示

---

# 21. 性能要件

## 21.1 目標

- 100ノードの現在ツリー適用: 体感上即時
- 1,000ノード検索インデックス: 1秒程度を目標
- 検索入力から候補表示: 100ms以下を目標
- 10,000ノード一括適用: UIを長時間完全停止させず、進捗表示可能
- アイドル監視時: CPU使用率を継続的に増加させない

## 21.2 キャッシュ対象

- 翻訳辞書
- 検索正規化済み文字列
- ノード型ごとの表示名
- 動的operation辞書
- tree別既知ノード
- 最近使用履歴
- お気に入り

## 21.3 再構築条件

- 翻訳辞書再読込
- Blenderバージョン変更
- 外部アドオン登録・解除
- ユーザー辞書変更
- Undo/Redo
- ファイル読込
- 診断画面から明示実行

---

# 22. エラー処理

## 22.1 基本方針

単一ノードの失敗で処理全体を停止しない。

## 22.2 想定エラー

- JSON構文エラー
- 翻訳項目不足
- ノード型未登録
- ノード作成失敗
- 不正なtree type
- 読み取り専用
- Linkデータ
- Library Override競合
- Undo中にノード消失
- アドオン解除済みカスタムノード
- Blender終了処理中
- タイマー多重登録
- キーマップ競合
- 長すぎるラベル
- 不正なUnicode

## 22.3 ログレベル

```text
INFO
WARNING
ERROR
DEBUG
```

## 22.4 ユーザー向け通知

- 通常の除外: INFO
- 読み取り専用: WARNING
- 辞書破損: ERROR
- 一部失敗: WARNING + 集計
- 全体失敗: ERROR

---

# 23. セキュリティと安全性

- 翻訳JSONをPythonコードとして評価しない
- `eval()`、`exec()`を使用しない
- ユーザー辞書のパスを検証
- 外部URLから自動更新する場合は明示同意を必要とする
- 任意Pythonコードを辞書に含めない
- ノード型生成前に登録済みIDか検証
- Link元データを強制変更しない
- 元ラベルを復元可能にする

---

# 24. テスト計画

## 24.1 Unit Test

### TranslationService

- 正常JSON読込
- 不正JSON
- バージョン条件
- ユーザー辞書優先
- 未登録ノード
- 動的operation
- 日本語未登録フォールバック

### LabelService

- 空ラベル適用
- ユーザーラベル保持
- 強制上書き
- 元ラベル保存
- 再適用時に元ラベルを破壊しない
- ユーザー編集検出
- 復元
- 管理情報削除

### SearchService

- 英語完全一致
- 日本語完全一致
- 英語前方一致
- 日本語別名
- 全角半角
- 大文字小文字
- 部分一致
- 文脈除外
- 順位
- 未登録ノード

## 24.2 Integration Test

- Geometry Nodesで検索・追加
- Material Shaderで検索・追加
- World Shaderで検索・追加
- 既存ツリー一括適用
- ファイル保存・再読込
- Undo/Redo
- コピー＆ペースト
- ノード複製
- Node Group
- Append
- Link
- Library Override
- アドオン無効化・再有効化
- 翻訳辞書revision更新
- Blender 4.2 / 4.5

## 24.3 Regression Test

- `node.name` が変わらない
- 接続が変わらない
- ノード値が変わらない
- Animation/Driverが変わらない
- ノードグループInterfaceが変わらない
- Link元ファイルが変更されない
- 既存ユーザーラベルがデフォルトで保持される
- アドオン無効化後もBlenderが正常動作する

## 24.4 Performance Test

- 100ノード
- 1,000ノード
- 10,000ノード
- 100ノードツリー
- 外部アドオン由来ノードを含む環境
- 連続Undo/Redo
- 長時間Node Editor操作

---

# 25. MVP受け入れ基準

以下をすべて満たした時点でMVP完成とする。

## 25.1 表示

- Geometry Nodesの主要標準ノードが `English / 日本語` で表示される
- Shader Nodesの主要標準ノードが `English / 日本語` で表示される
- `node.name` と `bl_idname` は変更されない
- 日本語未登録ノードは英語名で安全に表示される

## 25.2 適用

- 選択ノードへ適用できる
- 現在のノードツリーへ一括適用できる
- 新規追加ノードへ独自検索経由で自動適用できる
- ファイル読込後に管理状態を復元できる
- ユーザーラベルをデフォルトで上書きしない

## 25.3 復元

- 選択ノードを元ラベルへ戻せる
- 現在のノードツリーを一括復元できる
- 元ラベルが空の場合は空へ戻る
- ユーザーラベルが失われない

## 25.4 検索

- 英語正式名で検索できる
- 日本語正式名で検索できる
- 日本語別名で検索できる
- 現在のノードツリーに不適切なノードを除外できる
- 検索結果からノードを追加できる

## 25.5 安定性

- Blender 4.2 LTSで有効化・無効化できる
- Blender 4.5 LTSで有効化・無効化できる
- 保存・再読込でクラッシュしない
- Undo/Redoでクラッシュしない
- Linkデータを安全にスキップする
- 1件の翻訳エラーでアドオン全体が停止しない

## 25.6 診断

- 未登録ノードを一覧表示できる
- 辞書エラーを確認できる
- 読み取り専用によるスキップ件数を確認できる

---

# 26. 実装フェーズ

## Phase 0: 技術検証

- `Node.label` の表示挙動確認
- Geometry / Shaderでのノード列挙
- `nodes.new` による追加
- `invoke_search_popup` の候補表示
- Undo挙動
- Link/Override判定
- Blender 4.2 / 4.5 API差分

成果物:

- 最小プロトタイプ
- 技術リスク一覧
- ノード型収集スクリプト

## Phase 1: MVP基盤

- アドオン構成
- Preferences
- TranslationService
- LabelService
- Geometry / Shader辞書
- 選択・現在ツリー適用
- 復元
- Nパネル
- 診断

## Phase 2: 二言語検索

- SearchService
- 検索インデックス
- 独自検索Operator
- ノード追加
- マウス位置配置
- 文脈フィルタ
- 使用履歴

## Phase 3: 自動適用

- load_post
- 差分キャッシュ
- タイマー
- コピー・複製検出
- Undo/Redo整合
- 自動管理解除

## Phase 4: 高度なノード対応

- Math
- Vector Math
- Boolean Math
- Compare
- Mix
- Switch
- データ型依存ノード
- ノードグループ翻訳

## Phase 5: 配布品質

- 全辞書精査
- バージョン別差分
- 大規模性能試験
- エラーログ
- マニュアル
- 翻訳辞書編集ガイド
- Extension形式対応

---

# 27. 実装タスク分解

## Epic A: 基盤

- A01 アドオン雛形
- A02 Register/Unregister
- A03 Preferences
- A04 ログ基盤
- A05 バージョン互換層
- A06 テスト実行環境

## Epic B: 翻訳

- B01 JSON Schema
- B02 Geometry Nodes辞書
- B03 Shader Nodes辞書
- B04 TranslationService
- B05 バージョンオーバーライド
- B06 ユーザー辞書
- B07 辞書診断

## Epic C: ラベル

- C01 表示ラベル生成
- C02 元ラベル保存
- C03 適用ポリシー
- C04 復元
- C05 ユーザー編集検出
- C06 動的タイトル
- C07 Link/Override除外

## Epic D: UI

- D01 Nパネル
- D02 選択ノード情報
- D03 現在ツリー集計
- D04 適用・復元ボタン
- D05 Preferences
- D06 診断画面

## Epic E: 検索

- E01 ノード型収集
- E02 検索インデックス
- E03 正規化
- E04 スコアリング
- E05 文脈フィルタ
- E06 検索Popup
- E07 ノード追加
- E08 マウス位置配置
- E09 使用履歴・お気に入り

## Epic F: 自動化

- F01 load_post
- F02 treeキャッシュ
- F03 差分走査
- F04 timer
- F05 Undo/Redo
- F06 新規ノード検知
- F07 監視停止・再開

## Epic G: QA

- G01 Unit Test
- G02 Blender 4.2
- G03 Blender 4.5
- G04 大規模性能
- G05 Link/Append
- G06 Library Override
- G07 外部アドオン共存
- G08 無効化・再有効化

---

# 28. 既知の制約

1. `Node.label` を使用するため、既存のユーザーラベルと同じ領域を共有する
2. 二言語ラベルは `.blend` に保存される
3. ノード名が長くなり、ヘッダーが省略表示されることがある
4. 標準ソケット名は二言語化されない
5. 標準 `Shift + A` の完全再現はMVP対象外
6. すべてのノード追加経路を完全に即時検知できるとは限らない
7. 動的タイトルの常時同期には追加監視が必要
8. 外部アドオンのカスタムノードは翻訳登録がなければ英語のみになる
9. Linkデータは変更できない
10. Blenderバージョン更新でノードID・enum・カテゴリーが変わる可能性がある
11. ノードラベルを参照する外部スクリプトが存在する場合は挙動確認が必要
12. Blender標準UIの日本語訳とアドオン辞書の訳が一致しない場合がある

---

# 29. エンジニアへの実装判断

本仕様は、Blender Pythonアドオン開発経験を持つエンジニアであれば実装開始できる粒度に達している。

ただし、実装着手前にPhase 0として次の4点を必ず実機検証すること。

1. Blender 4.2・4.5における `Node.label` と動的ノードタイトルの優先関係
2. 独自検索Popupの日本語入力・IME確定挙動
3. ノード追加位置の座標変換
4. 標準追加後の自動検出とUndo履歴の相互作用

この技術検証で問題が出た場合でも、以下のMVPは成立する。

- 手動適用
- 独自検索からの追加
- 追加直後の二言語ラベル
- 一括復元
- ファイル読込時の更新

したがって、プロジェクト全体としての実現可能性は高い。

---

# 30. 公式API上の根拠

実装時は、対象Blenderバージョンの最新公式APIを確認すること。

主要参照項目:

- `bpy.types.Node`
  - `label`
  - `name`
  - `bl_idname`
  - `bl_label`
- `bpy.types.Operator`
- `WindowManager.invoke_search_popup`
- `bpy.app.translations`
- `bpy.app.handlers`
- `bpy.app.timers`
- `bpy.msgbus`
- `bpy.types.NodeTree`
- `bpy.types.NodeSocket`

参考URL:

- https://docs.blender.org/api/current/bpy.types.Node.html
- https://docs.blender.org/api/current/bpy.types.Operator.html
- https://docs.blender.org/api/current/bpy.types.WindowManager.html
- https://docs.blender.org/api/current/bpy.app.translations.html
- https://docs.blender.org/api/current/bpy.app.handlers.html
- https://docs.blender.org/api/current/bpy.app.timers.html
- https://docs.blender.org/api/current/bpy.msgbus.html
- https://docs.blender.org/api/current/bpy.types.NodeTree.html

---

# 31. 最終推奨仕様

MVPでは次の構成を正式採用する。

```text
表示:
Node.label = "English / 日本語"

識別:
Node.bl_idname

検索:
独自Operator + 独自検索インデックス

新規追加:
独自検索から追加した場合は即時適用

標準追加:
低頻度差分検出または手動更新

既存ラベル:
デフォルトでは保持

復元:
元labelをカスタムプロパティから復元

対応:
Geometry Nodes + Shader Nodes

正式対象:
Blender 4.2 LTS / 4.5 LTS

標準Shift+A置換:
実験的オプション

標準メニュー完全再構築:
MVP対象外
```

この設計により、Blender内部のノード型や接続処理を壊さず、ユーザーが実際のノードヘッダーで `English / 日本語` を確認でき、日本語・英語の双方からノードを検索できる。
