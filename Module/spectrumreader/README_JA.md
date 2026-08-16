# Energy Graph Scan iPhone v1.7.0

## v1.7.0 Foreground trace isolation
- 複数Channelが重なって表示される場合、色クラスタごとにトレースを分離し、横方向の可視率と連続性から前面トレースを選択します。
- Low/High計算は前面トレース1本だけを使用し、背面トレースを平均・混合しません。
- Channel checkboxが1個だけ検出された場合はそのChannelを最優先します。
- 複数checkboxの場合は候補集合を保持し、foreground traceを解析対象とします。色→CH番号マッピングが十分に確定できない場合は無理にCH番号を断定しません。
- 完全重複区間では前後の同色トレース連続性を優先し、別色トレースへの乗り換えを抑制します。

# Energy Graph Scan iPhone v1.5.0

Mac/XcodeなしでiPhoneから使用できるSafari/PWA版です。

## 機能
- iPhoneカメラから直接撮影
- 写真ライブラリから画像選択
- 撮影時のEnergy per Bandガイド枠
- Energy per BandのAuto ROI
- ROIの手動位置調整
- Auto / Gain / Noise切替
- Low = Sample#0–270、High = Sample#270以降
- Channel未検出でもUnknownとして解析継続
- 複数Channel候補でも解析継続
- Gainは小数2桁、Noiseは小数4桁
- Gain High 1.00–1.50、Noise Low 0–0.015 / High 0.001–0.02のSpec判定
- 数値と同じ座標モデルでSample#270線・Low/High検出ラインを描画
- PWAキャッシュ対応。ホーム画面追加後はアプリ風に起動可能

## iPhoneでの使い方
1. GitHub Pages等のHTTPSサイトへこのフォルダを公開します。
2. iPhone SafariでURLを開きます。
3. 「共有」→「ホーム画面に追加」でアプリとして登録できます。
4. 「写真を撮る」でカメラを起動し、Channel欄とEnergy per Bandが入るよう撮影します。
5. 撮影後、自動ROIと解析が実行されます。
6. ROIがずれている場合は「ROI調整」を押し、赤枠をドラッグします。
7. 「Analyze」で再解析します。

## GitHub Pages
`.github/workflows/deploy-pages.yml`を同梱しています。GitHubのSettings → PagesでSourceをGitHub Actionsに設定後、workflowを実行してください。

## Windows v1.4.0との共通仕様 / iPhone v1.5.0 algorithm update
解析ロジックはWindows v1.4.0と同じ考え方で整理しています。ただしブラウザCanvas実装のためpixel extractionは別実装です。今後、実画像でWindows/iPhone双方の期待値を比較しながら閾値を揃える前提です。


## v1.5.0 解析アルゴリズム改善
- UI/撮影フローはv1.4.0から変更せず、解析エンジンを重点的に更新。
- Auto ROIを固定位置・固定サイズ中心の探索から、ダウンサンプル画像の黒背景連結領域検出へ変更。
- Energy per Band内の緑グリッドを検出できる場合、plotのleft/right/top/bottomを画像ごとに推定。
- Sample#270の分割線、Low/High表示線、数値換算が同じplot geometryを使用。
- 信号pixel抽出は各列独立のquantileだけでなく、前列の信号位置との連続性を使ってtraceを追跡。
- Low/High値はMAD外れ値除去に加え、10–90 percentileで極端値を抑制。
- ConfidenceはLow/Highのsample coverageと信号分離度の両方から算出。
- Channel検出はgraphからの固定320px位置依存を廃止し、graph相対領域から8候補を探索。
- Channel不明/複数候補の場合でも解析継続。
- Auto Gain/Noise判定はファイル名ではなくhorizontal green grid group数を利用。

### 重要
本版は解析アルゴリズムの構造改善版です。実際の失敗写真群を使ってROI、Channel、Low/High期待値を回帰検証すると、さらに精度を詰められます。


## iPhoneでオフラインアプリとして使う（v1.7.0）

1. GitHub PagesなどHTTPSの公開URLをSafariで一度オンラインで開きます。
2. 画面が完全に表示されたら、Safariの共有ボタンから「ホーム画面に追加」を選びます。
3. ホーム画面の **Energy Scan** アイコンから一度起動します。これでアプリ本体がiPhone内へキャッシュされます。
4. 以後は機内モードなど通信が無い状態でも、ホーム画面から起動して「写真を撮る」「写真を選ぶ」「解析」を利用できます。解析は端末内JavaScriptのみで実行され、画像をサーバーへ送信しません。

### 更新方法
新しいSOURCE ZIPをGitHubへアップロードしてPagesが更新された後、iPhoneをオンラインにしてEnergy Scanを一度起動してください。Service Workerが新しいアプリファイルを取得します。その後は再びオフライン利用できます。

### 注意
初回インストール/初回キャッシュだけはオンライン接続が必要です。Safariの通常タブより、ホーム画面に追加したアイコンからの起動を推奨します。iOSがWebサイトデータを削除した場合は、再度オンラインで開いてキャッシュし直す必要があります。


## v1.7.0 analysis fixes
- Auto mode does not use grid count. It uses the isolated foreground trace baseline/step/value-shape features.
- Auto ROI: prioritizes the compact green Energy per Band grid instead of generic black chart regions.
- Manual ROI: four corner handles resize the ROI; dragging inside moves it.
- Plot geometry: derives top/bottom/left/right from long green grid lines rather than green text pixels.
- Foreground trace scoring now requires coverage on both sides of Sample#270 and follows overexposed white centers near the same trace.
- Existing offline PWA behavior is preserved.


## v1.7.0 Auto mode
- Gain/Noise の判定にグリッド本数を使用しません。
- 前面トレースを0–1正規化してから Low/High の相対位置、段差、ベースライン形状で判定します。
- 判定が曖昧な場合は誤判定を避けるため Unknown とし、Gain/Noise の手動選択を求めます。
- Noise の縦軸換算はグリッド本数に依存せず 0.04 を基準にします。


## v1.7.0 fixes
- Auto ROI now uses multi-cue compact-chart scoring (dark plot + green grid + warm foreground signal) to avoid Raw Data/Spectrum.
- Plot geometry selects long, near-even major grid lines and ignores green text labels.
- Foreground color tracks are re-ranked after Gain/Noise is known; only the selected foreground trace is used.
- Auto mode uses the foreground step/baseline pattern; grid count is not used.
- Overlay now marks the actually tracked foreground trace and draws Low/High lines from the same geometry/value model.


## v1.7.0 変更点
- 撮影ボタンはアプリ内カメラを優先し、撮影中だけ3x3グリッドを表示。通常の解析画面には撮影グリッドを表示しません。
- Auto ROIの右上位置ボーナスを削除。Energy per Bandの見た目（黒背景、緑グリッド、色トレース、コンパクト形状）だけで全画面を探索します。
- Gain/Noise判定にグリッド本数は使用しません。
- Mode確定後、主要横グリッド間隔からY軸を校正し、同じ校正を数値計算とLow/High表示ラインに使用します。
- foreground trace / Channel優先ルール / オフラインPWAは維持。


## v1.7.0 camera fix
- 撮影経路をアプリ内カメラへ一本化。撮影中のみ3x3グリッド表示。
- 撮影画像はfile inputへ戻さず直接Imageとして読み込み、撮影後に選択が消えるiOS問題を回避。
- PWAのCSS/JSをnetwork-first + version queryにし、旧版キャッシュ混在を防止。
- カメラ許可/起動失敗時はモーダル内で状態を表示し再試行可能。


## v1.7.0
- 撮影時の3x3グリッドを廃止し、Energy per Band + Channel用の外枠だけを表示。
- Auto ROIを画面位置非依存の構造スコア方式へ再実装。
- Y軸校正はplot内部の長い横グリッドだけを使用。
- Low/Highラインは解析トレースの実pixel位置を直接表示し、その同じpixel位置を数値へ変換。
- グリッド本数はGain/Noise判定には使用しない。


## v1.7.0
- 横向き撮影時にガイド枠も横向き・実グラフ比率に追従。
- Auto ROIは細い横方向トレースを強く評価し、Raw Data/Spectrumの誤選択を抑制。
- Autoモードが不確実でもProvisional Autoとして解析を継続。


## v1.7.0 統合解析コア
Windows v1.9.0 と `analysis_contract_v2.json` を共有します。Auto ROI / plot / foreground / mode / Y軸校正のいずれかが成立しない場合、推測値やSPEC結果を出しません。Gainは横方向固定分割を使用せず、Low安定区間・遷移区間・High安定区間を自動認識します。NoiseのみSample#270境界を維持します。


## v1.7.1 撮影後フリーズ対策
- iPhoneカメラ撮影後、フル解像度の画面全体を解析しない。
- 黄色の撮影ガイド枠をカメラのintrinsic pixel座標へ変換し、枠内だけを直接切り出す。
- `object-fit: cover` による画面表示時のcrop量も補正する。
- 黄色枠自体が画像へ入らないように小さな内側marginを設ける。
- 切り出し画像は最大幅1400pxへ縮小してからJPEG化し、Auto ROI / Channel / foreground解析へ渡す。
- これにより撮影後のメモリ使用量と全画面走査量を大幅に削減する。


## 1.7.2 Y軸数値ラベル校正
- 最下段major gridline=0 の仮定を廃止。
- Energy per Band左Y軸で実際に見えている数値ラベルだけをアンカーとして使用。
- 2個以上のラベル: pixel Y ↔ 実値を回帰して傾き/切片を決定。
- 1個だけのラベル: 読み取った実値をアンカーにし、major grid spacingから傾きだけ補完。
- 0個: 数値とSPECを出さない。
- ラベルが一部隠れていても、見えているアンカーだけで処理。
- グリッド本数をGain/Noise判定には使用しない。
- Gain Low/High横範囲は自動認識、NoiseのみSample#270。
- デバッグ情報にY-axis anchorsを表示。

## v1.7.3 ROI Rescue
- Auto ROIは確定値ではなく候補表示に変更。画像ロード直後に自動解析しない。
- 撮影枠切り出し画像ではEnergy per Bandの上側小グラフを優先し、Raw Data/Spectrum候補を抑制。
- ROI表示座標をcanvasの実表示offset込みで計算し、下方向へ動かせない問題を修正。
- ROI操作中のiOSテキスト選択/長押しメニューを無効化。
- perspective/moire向けrelaxed-grid geometryを追加。
- Auto modeが曖昧でもLow/HighはProvisionalとして計算。モード確定までSPECは表示しない。


## v1.7.4 Camera Return Freeze Fix
- 撮影後/写真読込直後の `detectGraph()` 自動実行を完全停止。
- 撮影後は画像を即表示し、編集可能な初期ROIを置いてUIを返す。
- Auto ROIはボタンを押した時だけ実行。
- Auto ROI実行前にstatusを描画し、終了までボタンを一時disable。
- 撮影枠切り出し画像ではAuto ROI探索範囲を上側72%・右側72%へ限定し、downsampleを強化。
- カメラ切り出し画像は最大1400pxへ縮小してメモリ負荷を抑制。


## v1.7.5 Default Auto Analyze Flow
- iPhone撮影後の基本フローを `撮影 → 撮影枠crop → Auto ROI → Analyze` に統一。
- 撮影直後に同期処理せず、画像を先に描画してから requestAnimationFrame + setTimeout で段階実行。
- Auto ROI失敗時は初期editable ROIでAnalyzeを試行し、失敗した場合のみ手動ROI調整へ移行。
- ユーザーがROI調整/Auto ROI/Analyzeを手動操作した場合は実行中の自動パイプラインをキャンセル。


## v1.7.6 Post-Capture Runtime Fix
- 撮影後の `Can't find variable: isGreen` を修正。
- ROI/grid/foreground解析で共通使用する `isGreen()` を復元。
- 撮影後 `useImage()` の直後にstatusを上書きしていた処理を削除。
- 自動Analyzeの例外内容を画面へ表示し、無反応/フリーズに見えないよう改善。
- `check_runtime_helpers.py` を追加し、必須JS helperの欠落を配布前に検出。

## v1.7.7 Channel-first / No Plot Hard-Stop
- Channel checkbox判定をplot確定より先に実行。
- Channelルール:
  - 1個チェック: そのCHを確定。
  - 複数チェック: foreground hueが選択済みの既知Channel色と一致した時だけ確定。
  - 一致しない/未知色: Channel=Unknown。
  - Unknownでも解析継続。
- `Energy per Band plot could not be confirmed` をhard stopから削除。
- geometry fallback: major-grid -> relaxed-grid -> dark-plot -> ROI-estimate。
- Y軸数値ラベル校正が失敗した場合も、Channel/Mode/Trace結果は保持し、Low/High数値とSPECだけ保留。
- 確定していない複数Channel候補を結果欄に `CH3/CH4/...` と表示せず、明確に `Unknown` と表示。

## v1.7.8 Y-axis Label Sequence OCR
- Y軸OCRをMode依存から分離。AutoがNoiseと誤判定していてもGainの3.0/2.0/1.0を探索する。
- 各ラベルを単独閾値で捨てず、複数ラベルを上下位置・単調減少・grid spacingと合わせて系列認識。
- Arial/Helvetica/Tahoma/Verdana/Courier/monospace/sans-serif、複数font sizeのテンプレートを比較。
- iPhone写真のぼけ/モアレに合わせ、Y軸緑文字抽出を緩和。
- 2個以上の可視ラベルからpixel-value一次式を直接fit。最下段grid=0の仮定は使用しない。
- 読み取った値のfamilyがGain/NoiseのAuto判定と矛盾した場合、Y軸ラベルを優先してAuto modeを補正。
- デバッグ表示にanchor値・pixel Y・個別confidenceを表示。

## v1.7.9 Noise Low/High Robust Split
- NoiseはLow/Highの振幅差で境界判定しない。
- Noise Low/HighはSample#270を意味上の境界として左右を独立集計。
- 270近傍は遷移/重なり帯として除外し、サンプル不足時のみmarginを段階的に縮小。
- Low/Highの値がほぼ同じ、または完全に同じでも正常に計算する。
- Noise confidenceからLow/High separation依存を削除。左右coverage + 各区間のstabilityだけで評価。
- 外れ値/MAD/10–90 percentile処理を左右別々に適用。
- Gainのtransition検出が弱い場合も、左右外側のstable plateauを低confidenceで採用して解析停止を回避。

## v1.8.0 Vision-style Axis Reasoning
- Manual Gain/Noiseを絶対優先。Manual GainでNoise familyを使う経路を禁止。
- AutoはGain/NoiseのY軸仮説を別々に作成し、trace shape + label series + grid step + numeric scaleを統合評価。
- `3.0/2.0/1.0` を `0.10/0.04/0.02` と誤採用しにくいよう、1 major gridあたりの数値step整合を厳格化。
- OCR単独winnerではなく、複数ラベル系列の整合性を優先。
- OCRが曖昧なら、弱い反対familyで明瞭なtrace-modeを上書きしない。
- Axis reasoningのGain/Noise scoreを結果messageに表示。

## iPhone v1.8.1 Pixel-primary Measurement
- foreground traceの実pixelを一次測定値として保存。
- Low/High代表高さはrobust median。平均値による下振れを抑制。
- Gainの表示X範囲はstable subsetのmin/maxではなく、transition前後のplateau全体。
- 数値は同じ代表pixelをY軸校正へ入力して算出。
- overlayも同じ代表pixelとplateau範囲を直接使用。
- 値からpixelへ逆変換してoverlayを作らない。

## v1.8.2 Axis Contradiction Guard
- yAxisCalibrationのOCR候補を確定Mode familyへロック。Gain指定時にNoise候補を混ぜない。
- 単一ラベルだけで数値確定しない。隣接major-grid rowに予測値の弱いOCR裏取りが必要。
- 3.0/2.0/1.0等のカメラ撮影文字に合わせ、緑＋anti-aliased明色をY-label strip内だけ許容。
- GainでHigh<Lowになる校正を棄却。
- 可視major-gridの数値spanから大きく外れるLow/Highを棄却。
- 校正矛盾時はTrace/Channel/Mode/overlayを保持し、Low/High/SPECのみ保留。
- Y軸anchor数/fit qualityをConfidenceへ反映し、弱い1-anchorで90%超にならないよう修正。

## v1.8.3 Direct Glyph Evidence
- Gain OCR候補を0.0〜4.0、Noiseを0.000〜0.050へ制約。
- 正規化前の文字aspect ratio / ink density / X-Y projectionを保持。
- IoUだけでなく文字列形状・横長さ・密度をtemplate照合へ反映。
- weak OCR候補を数学的系列補完へ使わない。
- direct strong glyph anchor 2個以上を必須化。
- one-anchor numeric calibrationを廃止。

## v1.8.4 Major-grid Zero Baseline
- Y軸OCRを数値定規から外し、major horizontal gridを数値定規として使用。
- 最下段major grid=0。
- Gainは上へ1 grid=1.0、Noiseは上へ1 grid=0.01。
- OCRはfamily/confidence補助のみ。`4,3,3,2` のような誤系列でscale全体をずらさない。

## v1.8.5 Zero-row Label/Grid Consensus
- 最下段major grid=0という仮定を撤廃。
- major gridは間隔の測定に使用。
- Y軸ラベルは「どのgrid rowが何の値か」のordinal投票に使用。
- 2つ以上の独立ラベルが同じzero-row offsetを支持した場合のみ数値校正。
- Gain 3.0/2.0/1.0なら1.0の1段下を0として復元。
- Noise 0.04/0.03/0.02/0.01も同じ方式で0位置を復元。

## v1.8.7 Exact Visible ROI Pixels
- Auto ROIのサイズ/位置アルゴリズムは変更しない。
- Analyze開始時、赤枠をcanvas整数pixelへ1回だけ確定。
- Channel / plot geometry / foreground trace / Y-axis / Low-High / overlayが同じanalysisROIを共有。
- DOM表示ROIとcanvas pixel ROIの変換をcanvasDisplayTransformへ一本化。
- 各処理が独立にROI外周をfloor/ceilする経路を廃止。
- 実際に解析したcropのx/y/w/hと軽量hashをdiagnosticsへ保存。

## v1.8.8 Y-axis Family Geometry
- ROI / Exact Analysis ROIは変更なし。
- Y軸ラベルの実画像aspect/widthを保持。
- 長い `0.04000 / 0.03000 / 0.02000` 型ラベルをNoise familyの直接証拠として使用。
- 短い `3.0 / 2.0 / 1.0` 型ラベルをGain familyの証拠として使用。
- AutoではY軸文字形状を波形形状より優先してGain/Noiseを補正。
- `4,3,2,0` のような欠落系列はcompletedAnchorsで `1` を補間するが、補間だけでzero位置は決めない。

# v2.0.0 Analysis Core v2

旧v1.xの補正積み上げから解析順序を再構成。

- 赤ROI = 探索範囲。ROIそのものをEnergy per Band plotとはみなさない。
- ROI内からgreen major-grid / dark chart rectangleで実plotを独立検出。
- 実plotからY-axis labels + plot + Sample/Bandsだけのanalysis contextを生成。
- Channel checkboxは元画面/ROIで判定。
- Gain/Noise Auto判定は、Y軸文字列の見た目を優先:
  - 長い `0.04000 / 0.03000 ...` = Noise
  - 短い `3.0 / 2.0 / 1.0` = Gain
- foreground trace / Y calibration / Low-Highは同じanalysis contextを共有。
- plotやY軸が不確かな場合は誤数値を出さずLow/Highだけ保留。

今回の目的は補正係数追加ではなく、
ROI / plot / axis / trace / numeric calibration の責務分離。

## v2.0.1 Noise Y-axis Major-grid Series
- Noise確定時はY軸数値OCRを主経路から外す。
- plot内の横major-gridを直接検出し、上から0.04 / 0.03 / 0.02 / 0.01 / 0へ系列化。
- 4本しか見えない場合のみzero rowを1 grid下へ補外。
- trace pixel Yをこの系列でEnergy値へ変換。
- Low/High横範囲はSample# 0–270 / 270–500。

## v2.0.2 Structural Noise Grid Detection
- v2.0.1の「緑色pixel数が一定以上」という条件を廃止。
- 横方向の線連続性、green成分、明暗edgeを合成してhorizontal grid候補を検出。
- 4〜6本の候補から等間隔性が最も高いmajor-grid latticeを選択。
- camera moire / 色褪せ / 黄色foregroundがあってもgridを候補化。
- Noise axis candidateはGain/Noise family判定より前に常時作成。
- Mode=Noise確定後、prepare時に失敗していても再度Noise grid seriesを試行。

## v2.0.3 Direct Noise Numeric Path
- Noise数値化を汎用calibrated.trackから分離。
- plot内の明るいyellow/orange/green foreground traceを直接抽出。
- Sample# 270/500でLow/Highを分割。
- 各column代表YをNoise major-gridへ直接変換。
- MAD外れ値除外 + median。
- 新Noise経路失敗時のみ旧trackへfallback。
- 0.04/0.03/0.02/0.01/0.00 gridを水色、Lowを白、Highを橙、270境界を黄点線でoverlay。

## v2.0.4 ROI / Noise structural correction
- 赤枠（解析パネル）と数値用inner gridを分離。
- 赤枠はEnergy per Band全体（Y軸ラベル、タイトル、X軸ラベル）を含むよう拡張。
- 数値計算はinner gridだけを使用。
- Noise Y軸はOCR/再検出をやめ、plot localizationで既に得た同一horizontal latticeを再利用。
- Noise固定major grid 0.04/0.03/0.02/0.01/0.00へ直接対応。
- 4本しか見えない場合だけ0.00を1 step下へ推定。
- 赤=解析パネル、水色点線=数値用gridとして表示を分離。

## v3.0.1 Shared Auto ROI
- Auto ROI独自のstructureScore探索を廃止。
- Auto ROIはmanual ROI成功時と同じ `plotFromGrid()` を候補窓に適用して探索。
- 採用ROIは検出plotから生成したnormalized contextそのもの。
- Auto ROIボタンとAnalyze時の自動復旧は同じ `autoPanelDetect()` を使用。
- 手動ROIはAnalyze時に絶対に移動しない。
- Auto ROI失敗時のみ同一detectorで1回再探索する。

## v3.0.2 Black-frame-first Auto ROI
- まず右側の黒いEnergy per Bandグラフ枠をdark connected componentで検出。
- dark fill / 横長aspect / green-grid / foreground / 右側位置でスコア化。
- 黒枠を軽く拡張した一次crop内だけでshared `plotFromGrid()` を実行。
- 黒枠が取れない場合だけ従来のshared full-image searchへfallback。
- Channels / Raw Data / Spectrumを一次cropから極力除外。

## v3.0.3 Dark Rectangle Boundary
- v3.0.2のdark connected-component方式を廃止。
- Energy per Bandを「黒い連結塊」ではなく「横長の黒い矩形面」として検出。
- 内部dark率、4辺dark率、green grid、foreground、aspect、位置を統合して候補選択。
- coarse rectangle取得後、左/右/上/下を pale→dark の境界変化から個別refine。
- 黒領域の内部fragmentation（grid/trace/文字）で外周が縮む問題を回避。

## v3.0.4 Guide-first / Grid-first
- v3.0.3の全画面黒矩形探索を撮影経路から完全に外した。
- iPhoneカメラでは、撮影時点で既にガイド枠内だけをsource imageへ切り出している。
- そのguide crop内の右上付近だけでregular green gridを探索。
- gridを確定してから、そのgrid周辺だけで黒panelの4辺を局所探索。
- 全画面のdark connected component / dark rectangleを撮影画像には使用しない。
- ファイル選択画像のみgeneric autoPanelDetectをfallbackとして残す。

## v4.0.0 Canonical Screen Registration
- Energy per Bandを写真内で毎回探索する方式を主経路から外した。
- 画面全体のUI構造を検出し、4点homographyで1600x1000 canonical画面へ正規化。
- canonical画面ではEnergy per Band ROI / inner plotを固定座標化。
- 撮影位置・拡大率・傾き・台形歪みをROI抽出より前に吸収。
- registration失敗時のみ旧Auto ROIへfallback。
- manual 4-point homography APIも実装。

## v4.0.2 Geometry-first Noise Y-axis
- 手動ROI時のY軸校正をOCR依存から分離。
- ROI内部の水平major-grid候補を structural rows + direct sampling から統合。
- 4〜5本の等間隔rowを選び、0.04 / 0.03 / 0.02 / 0.01 / 0.00へ直接割当。
- 0.00が見えない場合は4本のgrid spacingから1 step下へ推定。
- plot top/bottomとの整合性と全高spanをスコア化し、内側の誤grid列を拒否。
- Y軸文字はこのNoise数値化の必須条件ではない。

## v4.0.6 Noise lower dense-band estimator
- ROI / Y-axis / Channel判定は変更なし。
- 各X列の黄色foreground全体中央値を廃止。
- 各列の画像Y 72%点で下側高密度帯を追跡し、上方向の孤立スパイクを除外。
- X方向±6px rolling medianで孤立列・モアレを抑制。
- Low/High各領域ではMAD core + 10% trimmed mean。
- Sample# splitは0–270 / 270–500のまま。

## v4.0.7 Noise axis authoritative
- NoiseのY軸grid校正を最終基準として固定。
- 0.00/0.01/0.02/0.03/0.04の幾何が成立したらtrace値で軸校正をrejectしない。
- axis anchorsからvisible rangeを決定。
- visible range外のtrace pixelだけを個別除外。
- 残ったin-scale traceにY72 + rolling median + MAD + 10% trimmed meanを適用。
- `Noise measured values exceed displayed Energy scale` による全結果破棄を廃止。

## v4.0.8 ROI invariance
- 手動ROIの四辺を数値座標系として使う設計を廃止。
- 手動ROIは「Energy per Bandを指している」ことを示すヒントだけに使用。
- 実解析は画像全体から検出したEnergy-per-Band panelへsnap。
- Y軸、X軸、Sample#270境界、trace抽出はsnap後の同一plot座標で実行。
- ROIを少し上下左右に動かしても同じ画像ならLow/Highが原則同一になる。

## v4.1.0 Deterministic Analysis Frame
根本修正:
- Canonical Registration後に`redrawSource()`が元写真をcanonical canvasへ再描画していた座標系混在を修正。
- 画像ロード時またはcanonical変換完了時に、解析用pixel画像を`analysisBaseCanvas`へ1回だけsnapshot。
- Analyze/overlay/redrawは常に同じ`analysisBaseCanvas`から再描画。
- Energy per Band panelは1画像につき1回だけ検出し`stablePanelCache`へ固定。
- 手動ROIを動かしてもpanel/plot/Y-axis/Sample#270は再探索しない。
- Canonical成功時は手動/自動を問わずcanonical fixed panel/plotを使用。

## v4.1.1 Manual ROI fail-safe
- 手動ROI解析の前にglobal detectorへ依存しない。
- 手動ROI内のprepareを最初に試し、失敗時はprepareManualROIへ必ず進む。
- stable/global panel snapはoptional。失敗しても手動解析を止めない。
- Analyze開始時に前回の結果カードを消去。
- 例外時に古いAuto結果を表示したままにしない。
- stableEnergyPanelのredrawを含む全処理を例外保護。

## v4.1.2 Noise region-cloud extraction
- ROI / Y軸 / Channel判定は変更なし。
- Noise Low/Highを同じY72方式で追跡する設計を廃止。
- 各領域ごとに黄色のnear-zero baselineとelevated cloudを分離。
- elevated cloudが十分なX幅とpixel密度を持つ場合、そのcloud中心を採用。
- sparseな上方向spikeやEnergy per Band文字はcloud support条件で除外。
- cloudが存在しない側だけbaselineを使用。
- Highに実クラウドがあるのに連続baselineを拾って0.0000になる問題を修正。

## v5.0.0 Signal Geometry Core
- 長い水平信号をbaseline/zero扱いするロジックを削除。
- Noise Y軸は水平major-gridだけで0.00/0.01/0.02/0.03/0.04を確定。
- signal-derived zero helperをコードから完全削除。
- Low(0–270)/High(270–500)を独立解析。
- dominant foreground hueを推定し、各領域でY方向populationを構築。
- X coverage / density / compactnessで最も支持の強い実信号populationを採用。
- Low/Highはそのpopulationのrobust medianをY軸へ投影。

## v5.0.1 Safari stable pixel lifecycle
- iPhone/SafariでObject URL revoke後のHTMLImageElementを再drawしていた経路を廃止。
- `useImage()`内で最初にcanvasへpixelを完全コピー。
- 以後Auto ROI / 手動ROI / Analyze / redrawは`analysisBaseCanvas`だけを参照。
- Object URLはpixel copy完了後にrevoke。
- canonical変換後もcanonical canvasを再snapshotし、同じstable pixel bufferへ統一。
- `InvalidStateError`の原因になり得るrevoked ImageのdrawImage fallbackを削除。

## v5.0.2 Safari ImageData Analysis
- 解析元をCanvasからImageDataへ変更。
- 画像ロード/Canonical完了時にRGBAを一度だけsnapshot。
- Analyze/Auto ROI/Manual ROI再解析前はputImageDataのみで原画復元。
- Analyze中のCanvas->Canvas drawImage依存を廃止。
- 例外表示に `Stage <工程名>` を追加し、Safari DOMExceptionの発生工程を特定可能。

## v5.0.2 20方向検証
`verify_20_angles.js` を追加。
現在のv5仕様に対し20項目を独立検証し、20/20 PASS。
検証対象はImageData固定、Safari lifecycle、manual/auto ROI経路、Sample#270、
Noise同値/非ゼロLow、外れ値、幅依存性、sampling密度、grid-only Y軸、
signal population経路。

旧世代テストは `LEGACY_TEST_MATRIX.json` に別管理。
旧baseline/zero方式など、v5で意図的に廃止した仕様を要求するテストは
current acceptance testとして扱わない。

## v5.0.3
- Manual ROI is hard boundary; no global/canonical snap.
- Strong distributed horizontal major-grid required for Noise Y-axis.
- Compressed Y-axis lattices rejected.

## v5.1.0 Auto ROI Ensemble
- Auto ROIを探索window返却方式から、confirmed grid plot → local panel boundary方式へ変更。
- guide / dark-frame / broad right-side scopes の複数仮説を作成。
- grid規則性、dark interior、signal color、aspect、title-band green supportで採点。
- 上位候補が僅差の場合はconfidenceを下げる。
- 手動ROIも同じdetectorを赤枠内だけで実行。Auto/Manualでplot detectorを共通化。
- 手動の固定percentage plotはemergency fallbackへ降格。

## v5.1.1 Unified Input + Known Plot
- CameraとLibraryの主解析経路を統一。
- Cameraだけ先にCanonical Registrationへ入る設計を廃止。Registrationはfallbackのみ。
- Auto ROI detectorがpanel+plotを見つけたら、そのplot geometryを`activeDetectedPanel`へ固定。
- Analyze時にplotを再探索しない。`prepareKnownPanel()`でaxis/signal解析だけを実行。
- Auto recoveryでも同様にknown plotを再利用。
- Manualは赤ROI内の同じstructural detectorを使用し、検出plotを直接解析。
- diagnosticsへ実際のnumeric panel / numeric plot / input pathを記録。

## v5.1.2 Axis Consensus
- 黒いEnergy per Band領域に沿った手動ROIを基準ケースとして改善。
- major-gridは2本観測できれば周期latticeから残りを再構成。
- signal pixelをY軸校正に使用しない。
- 0はNoise grid系列から外挿し、signal底辺・plot底を0扱いしない。
- Manualは赤ROI内だけでplotFromGridを実行し、known plotを直接解析。

## v5.1.3 Auto Geometry + High Population Fix
### Auto ROI後のInvalidStateError
`prepareKnownPanel()` のinsetsがpixel値なのに `EGSCore.geometry()` が割合として解釈していた。
v5.1.3ではknown plotのinsetsを必ず0..1の割合で保存。
core側にもlegacy pixel insetを防御的に正規化するguardを追加。

### Noise High
High領域にLowから続く細い水平線と上側の実signal cloudが共存する場合、
X coverageだけでは水平線が勝ってしまっていた。
Low/Highを独立population化し、HighではLowより0.28 major-step以上上にあり
十分なcoverage/densityを持つpopulationを実High候補として優先する。
水平Low信号自体は0扱いしない。

### Manual
Manualは `prepareManualROI()` を最初に使用。
赤枠外global geometryへ先に入らない。

## v5.1.4 Rotation-aware Grid Compensation
- Energy per Band plot内のmajor-grid傾きを -8°〜+8°、0.25°刻みで探索。
- 元画像や表示ROI自体は回転せず、grid samplingだけを仮想deskew。
- 傾いた水平gridをdeskew後のcenter-Yへ投影してNoise Y-axis latticeへ投入。
- Auto/Manualとも同じ補正を使用。
- diagnosticsにRotation compensation angle/confidenceを表示。

## v6.0.0 12-stage Canonical Pipeline

1. Energy per Bandの直線gridから回転角を推定し、Auto時はworking frameをdeskewして再検出。
2. Channel欄の有無を判定。存在時は専用cropを表示。
3. Energy per Band黒領域を境界から再cropし表示。
4. 複数Channel選択時はforeground markerのdominant hueで選択済みChannel候補と照合。
5. 左Y軸数値を読み、major-grid間隔と組み合わせてpixel→value校正。最下線=0とは仮定しない。
6. 隣接major-gridの数値差 >=0.5 をGain、<0.5をNoise。
7. 下X軸ラベルとvertical-gridからSample scaleを校正。構造fallbackは0..500。
8. Gain: Low 0..330 / High 340..500。Noise: Low 0..260 / High 270..500。
9-11. 各領域のmarker populationを抽出し、median/MADでspikeを除外した後に平均値を算出。
12. Energy crop上へLow/High平均ラインと数値を描画。

Manual ROIは解析アルゴリズムを変更せず、探索範囲を限定するだけ。

## v6.1.0 Manual Geometry / Ordered Previews
表示順を固定:
1. Original
2. 回転補正後の全体画像
3. Channel detection crop（検出Channelを赤枠）
4. Energy per Band crop（Low/High平均ライン+数値）

Manual geometry:
- Rotationを-12°〜+12°で手動補正可能。
- 補正後working frame上でEnergy ROIとChannel ROIを独立保存・編集。
- Manual ROIは探索範囲のみを変更し、解析coreはAutoと共通。

## v6.1.1 Immutable Original / Rotation ROI Remap
- カメラ枠内cropの保存幅を1400px→最大2800px、JPEG quality 0.90→0.98。
- `useImage()`でも最大2800pxを保持。
- 撮影/Library読込直後の枠内画像をImmutable Originalとして一度だけ保存。
- Original previewはworking/rotation canvasから作らず、Immutable Originalを直接表示。
- 回転は毎回Immutable Originalから再生成。回転補正の重ね掛けによる画質劣化を禁止。
- 回転canvasは外接矩形へ拡張し、回転後の画像四隅を切らない。
- 回転角変更時、Energy ROI / Channel ROI / 編集ROIを
  old rotation → Original → new rotation座標へ再投影。
- Auto restoreも必ずImmutable Originalへ戻してから再検出。

## v6.2.0 Rotation / ROI Lock / Channel Anchors
- 撮影直後・Library読込直後の自動回転を禁止。
- 「自動傾き補正」ボタンを追加。ユーザーが押した時のみgrid直線から角度推定→回転。
- Analyze開始時の赤Energy ROIをロックし、解析中/解析後に変更しない。
- Channel ROIは文字アンカー方式:
  - `Channels` 左端 - 10px = 左端
  - `Channels` 文字中心Y = 上端
  - `Select All` 右端 = 右端
  - `Select All` 下端 = 下端
- Channel ROI内のcheckbox輪郭を検出し、内部ink量があるcheckboxだけをcheckedと判定。
- checked channelだけをChannel crop上で赤枠表示し、そのchannelだけを候補として解析へ渡す。

## v6.2.1 Manual ROI Authority / Channel Recognition
- Manual Energy ROI / Channel ROIをpreviewとanalysisの両方でauthoritativeに変更。
- Manual ROI設定後にauto cropへ戻す処理を禁止。
- Channel checkbox認識をconnected-component方式から既知2行layout方式へ変更。
- 上段 CH0..CH8、下段 CH9..CH15。
- disabled/薄灰色checkboxを先に除外し、enabledかつ内部check-mark inkがあるものだけchecked。
- Channel anchorが取れない場合は全chを推測せずUnknown。
- Channel crop下にFinal Channel selectorを追加。Auto/UnknownまたはCH0..CH15を手動選択可能。

## v6.3.0 ROI Editor Repair + Grid/Anchor Y Calibration

### ROI logic re-audit
以前は `roi`, `manualEnergyROI`, `manualChannelROI`, `manualEditTarget` が個別に更新され、
Channel編集後にEnergyへ戻すとmain ROI/crop preview/analysis ROIが異なる経路が残っていた。

v6.3.0では `roiEditorState` を唯一のeditor stateにした。
Target切替時は必ず「現在target保存 -> target変更 -> target ROIロード -> main赤枠更新 -> crop preview更新」。
pointermove / pointerup / pointercancelも同じcommit関数だけを通る。

### Y Axis
canonical v6 pathから `Gain専用OCR` / `Noise専用OCR` の先行判定を削除。
1. horizontal green gridを検出
2. periodic latticeを作り、欠落gridもgeometryから復元
3. 左の文字列は各grid rowのnumeric anchor候補としてのみ使う
4. 2 anchor以上ならgrid一段の値差を直接推定
5. 1 anchorの場合は3本以上のcoherent gridがある場合だけinterval候補とconsensus
6. zeroYは anchor value + grid index から外挿
7. 最下grid=0という仮定は禁止
8. adjacent-grid interval >=0.5: Gain / <0.5: Noise

## v6.3.1 Recognition + Processing Visibility
- `rgbToHue` 未定義によるAnalyze停止を修正。
- Channelは固定位置だけでなくcheckbox square outlineをROI内から検出し、
  2-row gridへcluster。enabled box群の内部ink分布に対する相対判定でcheckedを決定。
- disabled/薄灰色はlocal contrastと明度で先に除外。
- checkbox gridが成立しない場合だけv6.2.1 fixed layoutをfallback。
- Y-axisはv6.3.0 grid-firstを維持し、numeric anchor候補にdirect template matchingを追加。
- Analyze中は Processing panel を表示:
  Preparing → ROI/geometry → Energy per Band → Channel → Y-grid →
  Y anchors → X-axis → Low/High markers → Rendering → Complete。
- Analyzeボタンも処理中は `Processing…` と表示して二重実行を防止。

## v6.3.2 Energy / Channel ROI Isolation
- `roi` を Energy/Channel 共通fallbackとして使う経路を削除。
- Energy ROIのseedは Energy専用:
  `roiEditorState.energy -> manualEnergyROI -> last Energy crop -> activeDetectedPanel`
- Channel ROIのseedは Channel専用:
  `roiEditorState.channel -> manualChannelROI -> last Channel crop -> Channels/Select All detector -> channel-from-energy derivation`
- Auto ROIはEnergy ROIだけを更新し、Channel ROIには触れない。
- target切替時に前targetを保存してから次target固有ROIをロード。
- Energy/Channelがほぼ同じ矩形になった場合はalias guardが発火し、
  target固有seedから復旧。相手ROIの矩形をコピーしない。
- Preview/Analyzeも `roiEditorState.energy` / `roiEditorState.channel`
  をそれぞれ直接参照。

## v6.3.3 Y Bottom / X Line Alignment

- Y-axis値変換を `zeroYからの距離` 中心から、numeric anchorの実pixel位置を使う
  `value = slope * pixelY + intercept` へ変更。
- 2 anchor以上はweighted direct regression。1 anchor時のみgrid spacingをslopeに使用。
- `Math.max(0, value)` を削除。底辺を0へ強制しない。
- 最下gridのY位置と推定値をdiagnosticsに保存。
- X軸fallbackを `plot left/right = 0/500` から変更。
  実際に検出したvertical gridのleftmost/rightmostをSample 0/500として使う。
- OCRでXラベルが読めた場合はそのaffineを優先。
- Low/High marker抽出と、crop上のLow/High表示ラインが同じ `v6SampleX()` 校正を共有。

## v6.3.4 Module/spectrumreader deployment
- PWA本体を `Module/spectrumreader/` 配下へ移動可能な完全相対URL構成。
- Service Worker scopeは `./` = このmodule directoryのみ。
- `analysis_core_v2.js`, `robust_core_v3.js`, `canonical_registration_v4.js`
  を含む実行時assetをinstall時にprecache。
- Navigation offline fallbackもmodule-local `index.html`。
- 同一GitHub Pages上の他moduleをservice workerがinterceptしないようscope pathを明示チェック。
