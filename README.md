# EPUB OCR API

EPUB ファイルからテキストを抽出するための REST API です。テキストベースおよび画像ベースの EPUB ファイルに対応しており、OCR 機能により画像内のテキストも抽出できます。

## 特徴

- **FastAPI** による高速な REST API
- **PaddleOCR** による画像内テキストの OCR 抽出
- **ebooklib** による EPUB ファイルの解析
- **非同期処理** による大容量ファイルのパフォーマンス最適化
- **自動クリーンアップ** による一時ファイルの管理
- **50MB** までのファイルサイズ制限

## 環境要件

### Python 環境
- **Python 3.10 以降**
- **pip** パッケージマネージャー

### システム依存関係

#### Ubuntu/Debian の場合
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv
sudo apt install -y libgl1-mesa-glx libgthread-2.0-0 libsm6 libxext6 libxrender-dev libgomp1
sudo apt install -y libglib2.0-0 libgtk-3-0 libgdk-pixbuf2.0-0
```

#### CentOS/RHEL/Fedora の場合
```bash
sudo yum install -y python3-pip python3-venv
sudo yum install -y mesa-libGL glib2 gtk3 gdk-pixbuf2
```

#### macOS の場合
```bash
# Homebrewがインストールされている必要があります
brew install python3
```

### GPU サポート（オプション）
GPU を使用する場合は、CUDA ツールキットのインストールが必要です：

```bash
# CUDA 11.2 の例（PaddlePaddle との互換性を確認してください）
# NVIDIA の公式サイトから CUDA ツールキットをダウンロードしてインストール
```

## セットアップ手順

### 1. リポジトリのクローン
```bash
git clone https://github.com/rswisteria/epub_ocr.git
cd epub_ocr
```

### 2. 仮想環境の作成・有効化（推奨）
```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
# Linux/macOS の場合
source venv/bin/activate

# Windows の場合
venv\Scripts\activate
```

### 3. 依存関係のインストール
```bash
# 基本依存関係
pip install -r requirements.txt

# 開発・テスト用依存関係（開発者向け）
pip install -r requirements-dev.txt
```

## 実行方法

### 開発サーバーの起動
```bash
# 方法1: Pythonから直接実行
python main.py

# 方法2: uvicornから実行
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

サーバーが起動すると、以下の URL でアクセスできます：
- API エンドポイント: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs
- ReDoc ドキュメント: http://localhost:8000/redoc

## API 使用例

### エンドポイント

#### 1. ヘルスチェック
```bash
curl -X GET http://localhost:8000/
```

#### 2. EPUB ファイルのアップロードとテキスト抽出
```bash
curl -X POST "http://localhost:8000/upload-epub" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/your/book.epub"
```

### Python での使用例
```python
import requests

# EPUB ファイルをアップロード
with open('example.epub', 'rb') as file:
    response = requests.post(
        'http://localhost:8000/upload-epub',
        files={'file': file}
    )

if response.status_code == 200:
    result = response.json()
    print(f"ファイル名: {result['filename']}")
    print(f"抽出されたテキスト: {result['text']}")
else:
    print(f"エラー: {response.status_code} - {response.text}")
```

### JavaScript/Node.js での使用例
```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const form = new FormData();
form.append('file', fs.createReadStream('example.epub'));

axios.post('http://localhost:8000/upload-epub', form, {
    headers: {
        ...form.getHeaders(),
    },
})
.then(response => {
    console.log('ファイル名:', response.data.filename);
    console.log('抽出されたテキスト:', response.data.text);
})
.catch(error => {
    console.error('エラー:', error.response?.data || error.message);
});
```

## テスト実行

### 全テストの実行
```bash
pytest
```

### カバレッジ付きテスト実行
```bash
pytest --cov=. --cov-report=html
```

### 並列テスト実行
```bash
pytest -n auto
```

### 特定のテストファイルの実行
```bash
pytest tests/test_main.py
pytest tests/test_epub_processor.py
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. PaddleOCR のインストールエラー
```bash
# エラー: No module named 'paddle'
pip install paddlepaddle==2.5.2
pip install paddleocr==2.7.3
```

#### 2. 画像処理ライブラリのエラー
```bash
# エラー: libGL.so.1: cannot open shared object file
sudo apt install -y libgl1-mesa-glx libglib2.0-0
```

#### 3. OCR の精度が低い場合
- 高解像度の画像を使用してください
- 画像のコントラストと明度を調整してください
- PaddleOCR の言語設定を確認してください（現在は英語設定）

#### 4. メモリ不足エラー
```bash
# 大きなファイルの処理時
export PADDLEOCRXFLAGS=--max_text_length=2048
```

#### 5. ポート番号の競合
```bash
# 別のポートを使用する場合
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

#### 6. 仮想環境の問題
```bash
# 仮想環境をリセットする場合
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ログレベルの調整
詳細なログが必要な場合：
```bash
export LOG_LEVEL=DEBUG
python main.py
```

### パフォーマンスの最適化
- **GPU の使用**: CUDA が利用可能な環境では GPU が自動的に使用されます
- **並列処理**: 複数の画像がある場合、ThreadPool で並列処理されます
- **メモリ管理**: 大容量ファイルは自動的にチャンク処理されます

## プロジェクト構造

```
epub_ocr/
├── main.py                 # FastAPI アプリケーション
├── epub_processor.py       # EPUB 処理とOCR機能
├── requirements.txt        # 基本依存関係
├── requirements-dev.txt    # 開発用依存関係
├── CLAUDE.md              # Claude Code 用の指示書
├── README.md              # このファイル
└── tests/                 # テストファイル
    ├── __init__.py
    ├── conftest.py
    ├── test_epub_processor.py
    ├── test_integration.py
    ├── test_main.py
    └── test_performance.py
```

## 技術仕様

- **ファイルサイズ制限**: 50MB
- **対応フォーマット**: EPUB ファイル (.epub)
- **OCR 言語**: 英語（設定変更で他言語対応可能）
- **API フレームワーク**: FastAPI
- **OCR エンジン**: PaddleOCR
- **非同期処理**: asyncio ベース

## 開発者向け情報

### 新機能の追加
1. `epub_processor.py` で新しい処理ロジックを実装
2. `tests/` ディレクトリに対応するテストを追加
3. API エンドポイントが必要な場合は `main.py` を更新

### コントリビューション
1. フォークしてブランチを作成
2. 変更を実装してテストを追加
3. `pytest` でテストが通ることを確認
4. プルリクエストを作成

## ライセンス

このプロジェクトのライセンス情報については、リポジトリ内の LICENSE ファイルを参照してください。